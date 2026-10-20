#!/usr/bin/env python3
"""Builds ../assets/treehouse.svg (Storyfolk "Making it together" illustration): a giant old tree
with a treehouse village in it, Moss reading among the roots, Bolt climbing the ladder and Pip
waving from the cabin window.

Object outlines are hand-written path data. Python assembles the groups, clip paths and the
repeated texture marks (bark grooves, shingles, leaf flicks), and projects the spiral stair treads.

Dependency: shapely 2.x (pip install shapely). It merges trunk, limbs and roots into one tree
silhouette and cuts the lower-right shadow rims out of it.
Run: python3 tools/generate-treehouse.py   (writes ../assets/treehouse.svg next to this folder)
"""
import math
import os
import random
import re

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "treehouse.svg")

INK = "#111"
W = "#fff"
DL, DM, DD, HA, CH = ("url(#dots-light)", "url(#dots-mid)", "url(#dots-dark)",
                      "url(#hatch)", "url(#crosshatch)")

_n = [0]


def nid():
    _n[0] += 1
    return f"t{_n[0]}"


def n(v):
    s = f"{v:.1f}"
    s = s[:-2] if s.endswith(".0") else s
    return "0" if s == "-0" else s


# --------------------------------------------------------------------------- drawing helpers
def P(d, fill=W, sw=4.5, extra=""):
    st = f' stroke="{INK}" stroke-width="{sw}"' if sw else ""
    return f'<path d="{d}" fill="{fill}"{st}{" " + extra if extra else ""}/>'


def L(d, sw=2.5, col=INK, extra=""):
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{n(sw)}"{" " + extra if extra else ""}/>'


def F(d, pat):
    return f'<path d="{d}" fill="{pat}"/>'


def S(d, fill=W, sw=4.5, inner="", rule=""):
    """filled shape, inner content clipped to it, outline stroked last"""
    fr = f' fill-rule="{rule}" clip-rule="{rule}"' if rule else ""
    if not inner:
        st = f' stroke="{INK}" stroke-width="{sw}"' if sw else ""
        return f'<path d="{d}" fill="{fill}"{fr}{st}/>'
    k = nid()
    return (f'<clipPath id="{k}"><path d="{d}"{fr}/></clipPath><path d="{d}" fill="{fill}"{fr}/>'
            f'<g clip-path="url(#{k})">{inner}</g>'
            + (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}"/>' if sw else ""))


def C(cx, cy, r, fill=W, sw=0):
    st = f' stroke="{INK}" stroke-width="{n(sw)}"' if sw else ""
    return f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}"{st}/>'


def E(cx, cy, rx, ry, fill=W, sw=0, rot=0):
    st = f' stroke="{INK}" stroke-width="{n(sw)}"' if sw else ""
    tr = f' transform="rotate({n(rot)} {n(cx)} {n(cy)})"' if rot else ""
    return f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{fill}"{st}{tr}/>'


def circ(cx, cy, r):
    return f"M{n(cx - r)} {n(cy)}A{n(r)} {n(r)} 0 1 0 {n(cx + r)} {n(cy)}A{n(r)} {n(r)} 0 1 0 {n(cx - r)} {n(cy)}Z"


def ell(cx, cy, rx, ry):
    return f"M{n(cx - rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(cx + rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(cx - rx)} {n(cy)}Z"


def rect(x0, y0, x1, y1):
    return f"M{n(x0)} {n(y0)}L{n(x1)} {n(y0)}L{n(x1)} {n(y1)}L{n(x0)} {n(y1)}Z"


def poly_d(pts, close=False):
    return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts) + ("Z" if close else "")


def T(x0, y0, cx, cy, x1, y1, w, fill=INK):
    """tapered, hand-inked stroke: a lens along a quadratic curve, max thickness w"""
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    return (f'<path d="M{n(x0)} {n(y0)}Q{n(cx + nx * w)} {n(cy + ny * w)} {n(x1)} {n(y1)}'
            f'Q{n(cx - nx * w)} {n(cy - ny * w)} {n(x0)} {n(y0)}Z" fill="{fill}"/>')


def ray(cx, cy, ang, r0, r1, w=2.6, fill=INK):
    a = math.radians(ang)
    x0, y0 = cx + math.cos(a) * r0, cy + math.sin(a) * r0
    x1, y1 = cx + math.cos(a) * r1, cy + math.sin(a) * r1
    return T(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2, x1, y1, w, fill)


def scallop(pts, bulge=0.32):
    """closed path through pts whose edges bulge outward (foliage, moss, fluff)"""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    d = f"M{n(pts[0][0])} {n(pts[0][1])}"
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx, dy = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = dy / ln, -dx / ln
        if (mx - cx) * nx + (my - cy) * ny < 0:
            nx, ny = -nx, -ny
        d += f"Q{n(mx + nx * ln * bulge)} {n(my + ny * ln * bulge)} {n(q[0])} {n(q[1])}"
    return d + "Z"


def fuzz(cx, cy, r, k=11, jitter=0.18, seed=1, bulge=0.38):
    rnd = random.Random(seed)
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k + rnd.uniform(-0.12, 0.12)
        rr = r * (1 + rnd.uniform(-jitter, jitter) * 0.5)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return scallop(pts, bulge)


def lens_d(x0, y0, cx, cy, x1, y1, w):
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    return (f"M{n(x0)} {n(y0)}Q{n(cx + nx * w)} {n(cy + ny * w)} {n(x1)} {n(y1)}"
            f"Q{n(cx - nx * w)} {n(cy - ny * w)} {n(x0)} {n(y0)}Z")


def flicks(box, count, seed, length=(4, 8), ang=(20, 70), w=1.6):
    """scattered short hatch flicks (texture) inside a bbox, as one compound path"""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    d = ""
    for _ in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        a = math.radians(rnd.uniform(*ang))
        ln = rnd.uniform(*length)
        ex, ey = x + math.cos(a) * ln, y - math.sin(a) * ln
        d += lens_d(x, y, (x + ex) / 2 + 0.6, (y + ey) / 2, ex, ey, w)
    return f'<path d="{d}" fill="{INK}"/>' if d else ""


def specks(box, count, seed, r=(0.8, 1.6)):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    return "".join(C(rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(*r), INK) for _ in range(count))


def tufts(box, count, seed, size=6, w=1.6):
    """little 'v' grass / moss tufts"""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    out = []
    for _ in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        s = size * rnd.uniform(0.7, 1.2)
        out.append(L(f"M{n(x - s * 0.6)} {n(y - s)}Q{n(x - s * 0.2)} {n(y - s * 0.3)} {n(x)} {n(y)}"
                     f"Q{n(x + s * 0.15)} {n(y - s * 0.5)} {n(x + s * 0.5)} {n(y - s * 1.1)}", w))
    return "".join(out)


def grass(x, y, s=1.0, seed=1):
    """a ground grass tuft: 3-5 tapered blades"""
    rnd = random.Random(seed)
    out = []
    for i in range(rnd.choice((3, 4, 5))):
        a = math.radians(-90 + rnd.uniform(-38, 38))
        ln = s * rnd.uniform(10, 17)
        bx = x + rnd.uniform(-4, 4) * s
        ex, ey = bx + math.cos(a) * ln, y + math.sin(a) * ln
        out.append(T(bx, y, (bx + ex) / 2 + rnd.uniform(-2, 2), (y + ey) / 2, ex, ey, 1.9 * s))
    return "".join(out)


def stitches(d, sw=1.3):
    return L(d, sw, extra='stroke-dasharray="2.4 3"')


def rivet(x, y, r=2.4):
    return C(x, y, r, W, 1.8) + C(x - r * 0.3, y - r * 0.3, r * 0.3, INK)


def g(content, tr=None, extra=""):
    t = f' transform="{tr}"' if tr else ""
    return f"<g{t}{' ' + extra if extra else ''}>{content}</g>"


def poly_tube(pts, w0, w1):
    """tapered rod as a filled polygon along a polyline"""
    left, right = [], []
    total = len(pts) - 1
    for i, (x, y) in enumerate(pts):
        if i < total:
            dx, dy = pts[i + 1][0] - x, pts[i + 1][1] - y
        else:
            dx, dy = x - pts[i - 1][0], y - pts[i - 1][1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        w = (w0 + (w1 - w0) * i / total) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return poly_d(left + right[::-1], True)


def plank(x0, y0, x1, y1, w):
    """straight board of width w from (x0,y0) to (x1,y1) as a closed path"""
    return poly_tube([(x0, y0), (x1, y1)], w, w)


def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def bez_d(p0, p1, p2, p3, t):
    u = 1 - t
    return (3 * u * u * (p1[0] - p0[0]) + 6 * u * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0]),
            3 * u * u * (p1[1] - p0[1]) + 6 * u * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1]))


def qbez(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def path_pts(d, step=3.0):
    """sample an absolute M/L/C/Q/Z path into a point list (for shapely)"""
    toks = re.findall(r"[MLCQZ]|-?\d+(?:\.\d+)?", d)
    pts, i, cmd, cur = [], 0, None, (0.0, 0.0)
    while i < len(toks):
        if toks[i] in "MLCQZ":
            cmd = toks[i]
            i += 1
            if cmd == "Z":
                continue
        if cmd == "M" or cmd == "L":
            cur = (float(toks[i]), float(toks[i + 1]))
            i += 2
            pts.append(cur)
            cmd = "L"
        elif cmd == "C":
            c1 = (float(toks[i]), float(toks[i + 1]))
            c2 = (float(toks[i + 2]), float(toks[i + 3]))
            e = (float(toks[i + 4]), float(toks[i + 5]))
            i += 6
            m = max(4, int(math.dist(cur, e) / step))
            pts += [bez(cur, c1, c2, e, j / m) for j in range(1, m + 1)]
            cur = e
        elif cmd == "Q":
            c1 = (float(toks[i]), float(toks[i + 1]))
            e = (float(toks[i + 2]), float(toks[i + 3]))
            i += 4
            m = max(4, int(math.dist(cur, e) / step))
            pts += [qbez(cur, c1, e, j / m) for j in range(1, m + 1)]
            cur = e
    return pts


def geom_di(geom):
    """integer-precision path data for fill-only shading shapes"""
    if geom.is_empty:
        return ""
    polys = [geom] if geom.geom_type == "Polygon" else [p for p in getattr(geom, "geoms", []) if p.geom_type == "Polygon"]
    out = ""
    for p in polys:
        p = p.simplify(0.8)
        if p.is_empty or p.area < 6:
            continue
        for ring in [p.exterior] + list(p.interiors):
            out += int_d(list(ring.coords)[:-1]) + "Z"
    return out


def geom_d(geom):
    if geom.is_empty:
        return ""
    polys = [geom] if geom.geom_type == "Polygon" else [p for p in getattr(geom, "geoms", []) if p.geom_type == "Polygon"]
    out = ""
    for p in polys:
        p = p.simplify(0.55)
        if p.is_empty or p.area < 4:
            continue
        for ring in [p.exterior] + list(p.interiors):
            out += poly_d(list(ring.coords)[:-1], True)
    return out


def leaf(x, y, ang, s=1.0, fill=W, sw=2.4, shade=DM):
    """almond leaf with a midrib, base at (x,y), pointing along ang (degrees, 0 = right)"""
    body = "M0 0C5 -8 16 -10 26 -3C17 5 6 6 0 0Z"
    half = F("M0 0Q12 -1.5 26 -3C17 5 6 6 0 0Z", shade) if shade else ""
    return g(P(body, fill, 0) + half + L(body, sw / s) + L("M1 -0.5Q12 -2.5 24 -3", 1.5 / s),
             f"translate({n(x)} {n(y)}) rotate({n(ang)}) scale({n(s)})")


def swoosh(x, y, ang, ln=16):
    a = math.radians(ang)
    ex, ey = x + math.cos(a) * ln, y + math.sin(a) * ln
    mx, my = (x + ex) / 2 - math.sin(a) * 4, (y + ey) / 2 + math.cos(a) * 4
    return L(f"M{n(x)} {n(y)}Q{n(mx)} {n(my)} {n(ex)} {n(ey)}", 1.8)


# --------------------------------------------------------------------------- tree geometry
TRUNK = ("M683 225C676 262 667 300 669 340C671 382 651 420 653 462C655 502 649 540 649 580"
         "C649 630 640 672 633 712C626 760 608 802 588 836C570 866 543 886 512 906"
         "L990 906C956 886 926 864 909 834C891 800 885 760 879 716C873 672 881 640 867 600"
         "C853 560 857 520 853 480C849 440 857 400 847 360C839 320 836 270 818 225Z")

# limb / root centre lines (cubic bezier control points), base width, tip width, groove seed
LIMBS = [
    (((708, 285), (640, 230), (520, 165), (350, 125)), 74, 26, 11),   # upper-left limb into the canopy
    (((672, 372), (570, 380), (450, 440), (330, 470)), 60, 42, 12),   # limb under the small platform
    (((342, 472), (262, 478), (222, 400), (210, 262)), 44, 22, 13),   # its elbow rising into the canopy
    (((795, 262), (900, 205), (1040, 150), (1215, 105)), 72, 26, 14),  # right limb
    (((752, 250), (766, 180), (740, 110), (756, 40)), 82, 36, 15),     # leader
    (((1005, 165), (1030, 125), (1018, 95), (1040, 62)), 24, 10, 16),  # twig
    (((655, 612), (600, 606), (540, 602), (476, 596)), 40, 18, 17),    # tire-swing branch
]
# root fingers drawn over the rocks so the roots visibly grip them
FINGERS = [
    (((524, 868), (482, 842), (446, 852), (430, 918)), 19, 7, 29),
    (((498, 872), (486, 880), (474, 896), (472, 918)), 12, 5, 30),
    (((1090, 902), (1108, 874), (1138, 876), (1150, 930)), 16, 6, 31),
]
ROOTS = [
    (((612, 882), (548, 872), (470, 864), (366, 914)), 44, 12, 21),   # runs behind the big left rock
    (((660, 896), (636, 906), (610, 916), (582, 928)), 28, 8, 22),
    (((888, 878), (930, 866), (970, 870), (1002, 910)), 46, 12, 23),
    (((930, 896), (1010, 908), (1090, 904), (1160, 924)), 32, 8, 24),  # snakes behind Moss
    (((700, 900), (684, 912), (668, 922), (646, 931)), 22, 6, 25),
    (((800, 900), (818, 912), (840, 921), (866, 929)), 22, 6, 26),
]


def tube_geom(ctrl, w0, w1, N=44, flare=0.35):
    pts = [bez(*ctrl, i / N) for i in range(N + 1)]
    ws = [(w0 + (w1 - w0) * (i / N)) * (1 + flare * (1 - i / N) ** 5) for i in range(N + 1)]
    parts = []
    for i in range(N):
        a = Point(pts[i]).buffer(ws[i] / 2, 10)
        b = Point(pts[i + 1]).buffer(ws[i + 1] / 2, 10)
        parts.append(a.union(b).convex_hull)
    return unary_union(parts)


def int_d(pts):
    return "M" + "L".join(f"{round(x)} {round(y)}" for x, y in pts)


def batched(strokes):
    """emit (d, width) strokes as one compound path per width class"""
    buckets = {}
    for d, w in strokes:
        k = round(w * 2.5) / 2.5
        buckets.setdefault(k, []).append(d)
    return "".join(L("".join(ds), k) for k, ds in sorted(buckets.items()))


def tube_grooves(ctrl, w0, w1, offs, seed, sw=(1.4, 2.2)):
    rnd = random.Random(seed)
    out = []
    for f in offs:
        t = rnd.uniform(0.0, 0.12)
        while t < 0.93:
            t1 = min(0.97, t + rnd.uniform(0.12, 0.3))
            pts = []
            for j in range(9):
                tt = t + (t1 - t) * j / 8
                x, y = bez(*ctrl, tt)
                dx, dy = bez_d(*ctrl, tt)
                ln = math.hypot(dx, dy) or 1
                nx, ny = -dy / ln, dx / ln
                w = (w0 + (w1 - w0) * tt) / 2
                o = f * w + 1.6 * math.sin(tt * 22 + f * 7)
                pts.append((x + nx * o, y + ny * o))
            out.append((int_d(pts), rnd.uniform(*sw)))
            t = t1 + rnd.uniform(0.04, 0.12)
    return batched(out)


TRUNK_POLY = Polygon(path_pts(TRUNK)).buffer(0)


def trunk_span(y):
    seg = TRUNK_POLY.intersection(LineString([(0, y), (1400, y)]))
    x0, _, x1, _ = seg.bounds
    return x0, x1


def knot(x, y, rx, ry, rot=0):
    """bark knot: dark split with the grain bending round it"""
    return g(P(f"M0 {n(-ry)}C{n(rx * 0.9)} {n(-ry * 0.4)} {n(rx * 0.9)} {n(ry * 0.4)} 0 {n(ry)}"
               f"C{n(-rx * 0.5)} {n(ry * 0.4)} {n(-rx * 0.5)} {n(-ry * 0.4)} 0 {n(-ry)}Z", INK, 0)
             + L(f"M{n(-rx * 0.6)} {n(-ry * 2.2)}C{n(-rx * 2.2)} {n(-ry)} {n(-rx * 2.2)} {n(ry)} {n(-rx * 0.6)} {n(ry * 2.2)}", 2)
             + L(f"M{n(rx * 0.8)} {n(-ry * 2.2)}C{n(rx * 2.6)} {n(-ry)} {n(rx * 2.6)} {n(ry)} {n(rx * 0.8)} {n(ry * 2.2)}", 2)
             + L(f"M{n(-rx * 1.3)} {n(-ry * 3)}C{n(-rx * 3.4)} {n(-ry)} {n(-rx * 3.4)} {n(ry)} {n(-rx * 1.3)} {n(ry * 3)}", 1.5),
             f"translate({n(x)} {n(y)}) rotate({n(rot)})")


# --------------------------------------------------------------------------- canopy
def clump_pts(cx, cy, rx, ry, seed, k=12):
    rnd = random.Random(seed)
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k + rnd.uniform(-0.16, 0.16)
        rr = 1 + rnd.uniform(-0.1, 0.1)
        pts.append((cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr))
    return pts


def leafy(pts, h=0.42, seed=0, closed=True, center=None):
    """outline through pts made of lopsided bumps that end in a leaf point (overlapping-leaf edge)"""
    rnd = random.Random(seed)
    cx, cy = center or (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    m = len(pts) if closed else len(pts) - 1
    d = f"M{n(pts[0][0])} {n(pts[0][1])}"
    for i in range(m):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(dx, dy) or 1
        tx, ty = dx / ln, dy / ln
        nx, ny = ty, -tx
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        if (mx - cx) * nx + (my - cy) * ny < 0:
            nx, ny = -nx, -ny
        hh = h * rnd.uniform(0.8, 1.2)
        c1 = (p[0] + nx * ln * hh * 0.55 + tx * ln * 0.05, p[1] + ny * ln * hh * 0.55 + ty * ln * 0.05)
        c2 = (q[0] + nx * ln * hh * 1.0 - tx * ln * 0.22, q[1] + ny * ln * hh * 1.0 - ty * ln * 0.22)
        d += f"C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(q[0])} {n(q[1])}"
    return d + ("Z" if closed else "")


def leaf_d(x, y, ang, s):
    """small leaf outline as absolute path data (for compound texture paths)"""
    a = math.radians(ang)
    ca, sa = math.cos(a) * s, math.sin(a) * s

    def tp(px, py):
        return f"{round(x + px * ca - py * sa, 1)} {round(y + px * sa + py * ca, 1)}"
    return f"M{tp(0, 0)}C{tp(5, -8)} {tp(16, -10)} {tp(26, -3)}C{tp(17, 5)} {tp(6, 6)} {tp(0, 0)}ZM{tp(2, -0.5)}L{tp(20, -2.6)}"


def leaf_cluster(x, y, s, ang, seed):
    """three-leaf sprig as path data"""
    rnd = random.Random(seed)
    return "".join(leaf_d(x, y, ang + da + rnd.uniform(-8, 8), s * sc) for da, sc in ((-38, 0.85), (0, 1.0), (38, 0.85)))


def sprigs(d, sw=1.5):
    return f'<path d="{d}" fill="{W}" stroke="{INK}" stroke-width="{sw}"/>' if d else ""


def clump(cx, cy, rx, ry, seed, front=True, k=16):
    pts = clump_pts(cx, cy, rx, ry, seed, k)
    d = leafy(pts, 0.45, seed)
    rnd = random.Random(seed + 50)
    out = []
    # a few single leaves poking out of the edge
    for i in rnd.sample(range(k), 7 if front else 3):
        p, q = pts[i], pts[(i + 1) % k]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        a = math.degrees(math.atan2(my - cy, mx - cx))
        ox, oy = math.cos(math.radians(a)), math.sin(math.radians(a))
        out.append(leaf(mx + ox * 6, my + oy * 6, a + rnd.uniform(-25, 25), rnd.uniform(0.75, 1.0)))
    if front:
        # shadow mass on the lower right, edged by a leafy contour, white light patch upper left
        arc = [(cx + rx * 1.15 * math.cos(math.radians(a)) + rx * 0.3, cy + ry * 1.0 * math.sin(math.radians(a)) + ry * 0.5)
               for a in range(150, 300, 15)]
        sh_d = leafy(arc + [(cx + rx * 2, cy + ry * 2), (cx - rx * 2, cy + ry * 2)], 0.5, seed + 1,
                     center=(cx + rx * 0.3, cy + ry * 1.2))
        hl_pts = clump_pts(cx - rx * 0.26, cy - ry * 0.3, rx * 0.5, ry * 0.42, seed + 3, 9)
        inner = (F(sh_d, DM) + L(leafy(arc, 0.5, seed + 1, False, (cx + rx * 0.3, cy + ry * 1.2)), 2.2)
                 + P(leafy(hl_pts, 0.4, seed + 3), W, 0)
                 + flicks((cx - rx * 0.8, cy - ry * 0.6, cx + rx * 0.9, cy + ry * 0.9), int(rx * ry / 300), seed + 9,
                          (3, 6), (40, 80), 1.4))
        sp = ""
        for j in range(int(rx * ry / 1100)):
            a = math.radians(rnd.uniform(-20, 160))
            rr = rnd.uniform(0.35, 0.82)
            sp += leaf_cluster(cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr, rnd.uniform(0.42, 0.55),
                               rnd.uniform(-140, -40), seed * 10 + j)
        for j in range(int(rx * ry / 900)):
            a = math.radians(rnd.uniform(170, 300))
            rr = rnd.uniform(0.2, 0.75)
            sp += leaf_d(cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr, rnd.uniform(-150, -30), 0.4)
        inner += sprigs(sp, 1.4)
        out.append(S(d, DL, 4.5, inner))
    else:
        inner = (F(ell(cx + rx * 0.3, cy + ry * 0.4, rx, ry * 0.8), DD)
                 + flicks((cx - rx * 0.8, cy - ry * 0.7, cx + rx * 0.8, cy + ry * 0.8), int(rx * ry / 500), seed + 7,
                          (3, 6), (40, 80), 1.3))
        sp = ""
        for j in range(int(rx * ry / 2400)):
            a = math.radians(rnd.uniform(0, 360))
            rr = rnd.uniform(0.2, 0.7)
            sp += leaf_cluster(cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr, 0.42,
                               rnd.uniform(-140, -40), seed * 10 + j)
        inner += sprigs(sp, 1.4)
        out.append(S(d, DM, 4.2, inner))
    return "".join(out)


def drip(x, y0, length, seed, w=12):
    """shaggy strand of hanging moss"""
    rnd = random.Random(seed)
    m = max(4, int(length / 9))
    lft, rgt = [], []
    for i in range(m + 1):
        t = i / m
        y = y0 + length * t
        ww = w * (1 - t * 0.82) / 2
        sw = 5 * math.sin(t * 3.2 + seed)
        jag = 3.2 if i % 2 else 0
        lft.append((x + sw - ww - jag + rnd.uniform(-1, 1), y))
        rgt.append((x + sw + ww + (3.2 - jag) + rnd.uniform(-1, 1), y + 2))
    tip = (x + 5 * math.sin(3.2 + seed), y0 + length + 8)
    d = poly_d(lft + [tip] + rgt[::-1], True)
    inner = flicks((x - w, y0, x + w, y0 + length), int(length / 7), seed + 1, (3, 6), (70, 110), 1.2)
    return S(d, DM, 2.4, inner)


def vine(x, y0, length, seed):
    """hanging vine with paired leaves"""
    rnd = random.Random(seed)
    pts = []
    m = 12
    for i in range(m + 1):
        t = i / m
        pts.append((x + 7 * math.sin(t * 5 + seed), y0 + length * t))
    out = [L(poly_d(pts), 2.2)]
    for i in range(2, m + 1, 2):
        px, py = pts[i]
        side = 1 if (i // 2) % 2 else -1
        out.append(leaf(px, py, 90 + side * 55 + rnd.uniform(-10, 10), 0.55 + rnd.uniform(0, 0.12)))
    return "".join(out)


# --------------------------------------------------------------------------- props
def brass_lantern(x, y, s=1.0, glow=True):
    """hanging brass lantern; (x, y) = top of the bail ring"""
    o = []
    if glow:
        o.append("".join(ray(0, 36, a, 24, 31 + (a % 3) * 2, 2.6) for a in (-20, 20, 60, 120, 160, 200, 340)))
    o.append(L("M-8 16Q-8 1 0 0Q8 1 8 16", 2.6))
    o.append(S("M-11 24L11 24L7 17Q0 12 -7 17Z", W, 3, F("M0 11L12 11L12 25L0 25Z", DM)))
    o.append(C(0, 12.5, 2.6, W, 2))
    o.append(P("M-13 24L13 24L13 28L-13 28Z", DD, 2.6))
    o.append(P("M-10 28L10 28L10 46L-10 46Z", W, 3))
    o.append(P("M0 30C5 36 6 40 3 43C1 44.5 -1 44.5 -3 43C-6 40 -5 36 0 30Z", W, 1.8))
    o.append(P("M0 36C2 39 2.4 41 1 42.5C0 43 -1 43 -1.4 42.4C-2.4 41 -2 39 0 36Z", INK, 0))
    o.append(L("M-6 28L-6 46M6 28L6 46", 1.6))
    o.append(P("M-13 46L13 46L10 52L-10 52Z", DM, 2.8))
    return g("".join(o), f"translate({n(x)} {n(y)}) scale({n(s)})")


def paper_lantern(x, y, r, seed, drop=10):
    """round ribbed paper lantern hanging on a short string from (x, y)"""
    cy = y + drop + 4 + r * 0.85
    body = ell(x, cy, r, r * 0.85)
    ribs = "".join(L(f"M{n(x + r * f)} {n(cy - r * 0.8)}Q{n(x + r * f * 1.35)} {n(cy)} {n(x + r * f)} {n(cy + r * 0.8)}", 1.4)
                   for f in (-0.55, 0, 0.55))
    inner = F(ell(x + r * 0.55, cy + r * 0.2, r * 0.7, r * 0.9), DL) + ribs
    return (L(f"M{n(x)} {n(y)}L{n(x)} {n(y + drop)}", 1.6)
            + P(rect(x - r * 0.42, y + drop, x + r * 0.42, y + drop + 5), DD, 2)
            + S(body, W, 2.8, inner)
            + P(rect(x - r * 0.38, cy + r * 0.8, x + r * 0.38, cy + r * 0.8 + 4.5), DD, 2)
            + L(f"M{n(x)} {n(cy + r * 0.8 + 4.5)}L{n(x)} {n(cy + r * 0.8 + 12)}", 1.6)
            + "".join(ray(x, cy, a, r + 5, r + 10, 1.8) for a in (200, 250, 290, 340) if seed % 2 == 0))


def bird(x, y, s=1.0, flip=False):
    """small round perched bird, feet at (x, y)"""
    o = (L("M-2 0L-4 8M4 0L5 8", 2.2) + L("M-7 8L-1 8M2 8L8 8", 1.8)
         + P("M10 -6L26 -18L22 -6L28 -6L16 2Z", DM, 2.6)
         + S("M-16 -8C-18 -22 -6 -30 4 -26C12 -23 15 -14 13 -6C9 2 -10 2 -16 -8Z", W, 3.6,
             F("M0 -30L20 -30L20 4L4 4C10 -6 8 -20 0 -30Z", DM) + F("M-18 -2C-8 4 6 4 16 -2L16 4L-18 4Z", DL))
         + P("M-4 -14C2 -18 10 -14 10 -8C4 -6 -2 -8 -4 -14Z", DL, 2.2)
         + P("M-16 -18L-26 -15L-16 -12Z", W, 2.4)
         + C(-9, -18, 2.4, INK) + C(-9.8, -18.8, 0.8, W) + E(-11, -11, 2.6, 1.6, DL)
         + T(-4, -27, -6, -33, -2, -37, 2.2) + T(0, -26, 2, -33, 6, -35, 2))
    fx = -1 if flip else 1
    return g(o, f"translate({n(x)} {n(y - 8 * s)}) scale({n(s * fx)} {n(s)})")


def flying_bird(x, y, s=1.0, flip=False):
    """the perched bird's design in flight, wings raised; faces right"""
    o = (P("M-4 -8C-8 -20 -4 -32 6 -38C9 -26 8 -16 4 -6Z", DM, 2.6)
         + P("M-15 0L-30 -6L-27 2L-32 9L-14 6Z", DM, 2.6)
         + S("M-18 2C-18 -10 -6 -16 6 -15C16 -14 22 -6 20 3C17 11 -12 12 -18 2Z", W, 3.4,
             F("M-20 3C-6 10 8 10 22 3L22 14L-20 14Z", DL))
         + P("M19 -6L29 -2.5L19 1Z", W, 2.2)
         + C(11, -6, 2.4, INK) + C(10.3, -6.8, 0.8, W) + E(10, 1, 2.6, 1.6, DL)
         + S("M-6 -6C-15 -14 -18 -28 -12 -38C-3 -30 2 -18 2 -7Z", W, 3,
             L("M-8 -12Q-11 -22 -10 -30M-4 -11Q-5 -20 -4 -27", 1.3)))
    fx = -1 if flip else 1
    return g(o, f"translate({n(x)} {n(y)}) scale({n(s * fx)} {n(s)})")


def birdhouse(x, y, s=1.0):
    """birdhouse; (x, y) = bottom centre"""
    o = (P("M-16 0L-16 -30L16 -30L16 0Z", W, 3.4)
         + F("M6 -30L16 -30L16 0L6 0Z", DM)
         + L("M-16 -10L16 -10M-16 -20L16 -20", 1.3)
         + C(0, -18, 5.2, INK) + C(-1.4, -19.4, 1.2, W)
         + L("M0 -8L0 -3", 3) + C(0, -3, 2, INK)
         + S("M-22 -27L0 -48L22 -27L17 -27L0 -42L-17 -27Z", W, 3.2, F("M0 -50L24 -50L24 -26L0 -26Z", HA))
         )
    return g(o, f"translate({n(x)} {n(y)}) scale({n(s)})")


# --------------------------------------------------------------------------- characters
def pip_window():
    """Pip (hero-cast model) leaning at the cabin window, waving; local units of the hero model.
    Returns (inside, outside): inside is clipped to the window opening, outside is drawn over the frame."""
    o = []
    # puffy jacket shoulders
    jacket = "M-30 -60Q-44 -56 -44 -40Q-50 -30 -48 -14L48 -14Q50 -30 44 -40Q44 -56 30 -60Z"
    o.append(S(jacket, W, 5,
               F("M18 -64Q46 -58 46 -40Q52 -30 50 -12L24 -12Q30 -30 24 -40Q28 -54 18 -64Z", DM)
               + L("M-44 -38Q0 -32 44 -38", 2.6) + L("M0 -56L0 -10", 2.6)
               + "".join(L(f"M-2 {y}L2 {y}", 1.3) for y in range(-52, -14, 4))
               + T(-34, -36, -22, -34, -10, -34.5, 1.8)))
    # front scarf tail and wrap
    ftail = "M-25 -52C-27 -44 -26 -34 -24 -18L-9 -19C-10 -30 -10 -42 -10 -52Z"
    o.append(S(ftail, W, 4, F("M-30 -46L-5 -46L-5 -39L-30 -39Z", DD) + F("M-30 -33L-5 -33L-5 -26L-30 -26Z", DD)))
    wrap = "M-31 -63C-14 -55 14 -55 31 -63L31 -49C14 -41 -14 -41 -31 -49Z"
    o.append(S(wrap, W, 4.5, "".join(F(f"M{x} -66L{x + 9} -66L{x + 8} -40L{x - 1} -40Z", DD) for x in (-24, -5, 14))
               + L("M-30 -55C-14 -48 14 -48 30 -55", 1.6)))
    # ears, face
    o.append(S(circ(-29, -79, 6), W, 3.5, F(circ(-29, -79, 6), DL)) + L("M-30 -82Q-26 -79 -30 -76", 1.6))
    o.append(S(circ(29, -79, 6), W, 3.5, F(circ(29, -79, 6), DM)) + L("M30 -82Q26 -79 30 -76", 1.6))
    o.append(S(circ(0, -82, 29), W, 5,
               F(circ(0, -82, 29), DL) + P(circ(-7, -87, 30), W, 0)
               + F("M-34 -96C-12 -100 12 -100 34 -96L34 -85C12 -89 -12 -89 -34 -85Z", DM)))
    o.append(E(-11, -74, 4.6, 6.2, INK) + E(11, -74, 4.6, 6.2, INK))
    o.append(C(-12.6, -76.6, 1.9) + C(9.4, -76.6, 1.9) + C(-9.6, -71.6, 0.8) + C(12.4, -71.6, 0.8))
    o.append(T(-17, -84, -11, -89, -5, -86, 2.4) + T(5, -86, 11, -89, 17, -84, 2.4))
    o.append(L("M-2.5 -67Q0 -64.5 2.5 -67", 2))
    o.append(P("M-9 -61Q0 -47 9 -61Q0 -59 -9 -61Z", INK, 0))
    o.append(P("M-4.5 -56Q0 -52.5 4.5 -56Q0 -58 -4.5 -56Z", W, 0))
    o.append(E(-19.5, -65.5, 6, 3.8, DL) + E(19.5, -65.5, 6, 3.8, DL))
    o.append("".join(C(x, y, 0.95, INK) for x, y in
                     ((-23, -71), (-19.5, -72.5), (-21.5, -68.8), (19.5, -72.5), (23, -71), (21.5, -68.8))))
    o.append(P("M-31 -92L-37 -84L-32 -84.5L-35 -77L-27 -84Z", INK, 0))
    o.append(P("M31 -92L37 -84L32 -84.5L35 -77L27 -84Z", INK, 0))
    o.append(P("M-12 -90Q-7 -81 -2 -90Z", INK, 0) + P("M2 -90Q8 -82 11 -90Z", INK, 0))
    # beanie: pom-pom, dome, goggles, cuff
    pom = fuzz(9, -139, 11.5, 12, seed=4)
    o.append(S(pom, W, 3.6, F(circ(15, -134, 12), DL) + P(circ(6, -142, 9), W, 0)
               + flicks((0, -148, 18, -130), 9, 11, (2.5, 4.5), (0, 180), 1.2)))
    dome = "M-33 -97C-35 -120 -18 -133 2 -134C24 -134 37 -120 34 -97Z"
    o.append(S(dome, W, 5,
               F("M13 -136C32 -130 41 -116 37 -95L22 -95C27 -112 24 -125 13 -136Z", DM)
               + L("M-22 -100C-24 -112 -16 -124 -8 -129", 1.6) + L("M-8 -101C-9 -114 -5 -126 0 -132", 1.6)
               + L("M8 -101C9 -114 8 -126 6 -132", 1.6) + L("M22 -100C24 -112 20 -124 14 -130", 1.6)))
    o.append(P("M-34 -103C-12 -112 14 -112 35 -103L35 -111C14 -120 -12 -120 -34 -111Z", DD, 2.4))
    for gx in (-12, 12):
        o.append(S(circ(gx, -115, 10.5), W, 4.2, F(circ(gx + 4, -111, 9), DL)))
        o.append(L(f"M{gx - 5} -118Q{gx - 3} -121.5 {gx + 1} -121.5", 2, W))
        o.append(C(gx, -115, 7, "none", 1.6))
    o.append(L("M-1.5 -116Q0 -118 1.5 -116", 3.4))
    cuffb = "M-36 -101C-12 -107 12 -107 36 -101L36 -88C12 -94 -12 -94 -36 -88Z"
    o.append(S(cuffb, W, 4.5,
               "".join(L(f"M{x} -110L{x} -84", 1.5) for x in range(-32, 36, 5))
               + F("M22 -112L40 -112L40 -84L22 -84Z", DM)))
    inside = "".join(o)

    u = []
    # waving arm (Pip's left), sleeve up from the shoulder, mitten open
    sleeve = "M24 -54C40 -60 52 -78 58 -100L74 -96C70 -72 56 -48 38 -40Z"
    u.append(S(sleeve, W, 4.5, F("M62 -104L84 -104L80 -60L50 -36L44 -50C60 -62 66 -80 62 -104Z", DM)
               + L("M44 -66Q52 -64 58 -70", 2.2)))
    u.append(S("M56 -100L75 -95L78 -105L58 -111Z", W, 3.4,
               "".join(L(f"M{x} -116L{x - 2} -90", 1.4) for x in (60, 64, 68, 72, 76))))
    mitt = "M57 -110C52 -122 56 -136 66 -139C76 -142 84 -133 82 -121C81 -112 74 -107 66 -108Z"
    u.append(S(mitt, W, 4, F("M72 -142L90 -142L90 -104L70 -104C78 -114 78 -128 72 -142Z", DL)))
    u.append(S("M58 -116C50 -116 46 -124 50 -129C54 -131 58 -127 60 -122Z", W, 3.4))
    u.append(L("M66 -126Q70 -122 70 -116M74 -128Q78 -124 77 -118", 1.6))
    u.append(L("M88 -146Q96 -136 94 -124", 2.2) + L("M95 -152Q106 -138 102 -120", 2.2))
    u.append(L("M48 -146Q50 -152 56 -154", 2))
    # resting mitten on the sill
    u.append(g(S("M-50 -22C-52 -30 -44 -36 -34 -34C-24 -32 -20 -26 -22 -20C-28 -16 -44 -16 -50 -22Z", W, 4,
                 F("M-30 -38L-18 -38L-18 -16L-30 -16Z", DL))
               + L("M-40 -30Q-37 -25 -40 -20M-33 -31Q-30 -26 -32 -20", 1.6), "translate(0 -16)"))
    return inside, "".join(u)


def bolt_climb():
    """Bolt (hero-cast model) on the ladder; local units of the hero model, origin at body centre-top"""
    o = []
    # raised arm (behind head edge) up to the left rail, lower arm out to the right rail
    def arm(pts, seed):
        d = poly_tube(pts, 15, 13)
        bands = ""
        tot = len(pts) - 1
        for i in range(1, 8):
            t = i / 8
            k = min(tot - 1, int(t * tot))
            f = t * tot - k
            x = pts[k][0] + (pts[k + 1][0] - pts[k][0]) * f
            y = pts[k][1] + (pts[k + 1][1] - pts[k][1]) * f
            dx, dy = pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]
            ln = math.hypot(dx, dy) or 1
            nx, ny = -dy / ln * 9, dx / ln * 9
            bands += L(f"M{n(x - nx)} {n(y - ny)}L{n(x + nx)} {n(y + ny)}", 1.6)
        return S(d, W, 3.8, bands + F(poly_tube([(p[0] + 5, p[1] + 3) for p in pts], 8, 7), DM))

    def claw(x, y, ang):
        return g(S("M-9 -2C-11 -12 -4 -16 3 -14C10 -12 12 -4 9 3C6 8 -6 8 -9 -2Z", W, 3.6, F("M2 -16L14 -16L14 8L2 8Z", DM))
                 + S("M-6 -8C-14 -14 -16 -24 -10 -30C-8 -24 -4 -18 0 -14Z", W, 3.2)
                 + S("M6 -8C14 -14 16 -24 10 -30C8 -24 4 -18 0 -14Z", W, 3.2) + rivet(0, -1, 2.2),
                 f"translate({n(x)} {n(y)}) rotate({n(ang)})")

    o.append(arm([(-50, 44), (-70, 20), (-78, -12), (-76, -44)], 1))
    o.append(claw(-76, -50, -4))
    o.append(arm([(50, 52), (66, 60), (74, 72), (76, 86)], 2))
    o.append(claw(76, 92, 180))

    # tank treads standing on a rung
    trk = "M-46 112L46 112A19 19 0 0 1 46 150L-46 150A19 19 0 0 1 -46 112Z"
    lugs = "".join(P(rect(x - 3, 149, x + 3, 155), INK, 0) for x in range(-48, 52, 12))
    o.append(lugs)
    o.append(S(trk, CH, 4.4, ""))
    o.append(P("M-44 119L44 119A12 12 0 0 1 44 143L-44 143A12 12 0 0 1 -44 119Z", W, 2.6))
    for wx in (-40, -13, 13, 40):
        o.append(C(wx, 131, 9.5, W, 2.6) + C(wx, 131, 3.2, DD, 1.6) + C(wx + 4, 134, 9, "none", 0))
    o.append(F("M-60 140L60 140L60 152L-60 152Z", "none"))
    # body box with chest hatch and heart sticker
    body = "M-48 22L48 22Q55 22 55 29L55 104Q55 112 48 112L-48 112Q-55 112 -55 104L-55 29Q-55 22 -48 22Z"
    o.append(S(body, W, 5, F("M34 18L60 18L60 116L34 116Z", DM) + F("M-60 94L60 94L60 116L-60 116Z", HA)
               + rivet(-46, 31) + rivet(46, 31) + rivet(-46, 103) + rivet(46, 103)
               + flicks((-48, 30, 30, 90), 5, 41, (3, 5), (10, 40), 1.1)))
    hatch_d = "M-24 38L24 38Q28 38 28 42L28 84Q28 88 24 88L-24 88Q-28 88 -28 84L-28 42Q-28 38 -24 38Z"
    o.append(S(hatch_d, W, 3.4, F("M14 34L32 34L32 92L14 92Z", DL)))
    o.append(P(rect(-33, 46, -26, 54), DD, 2) + P(rect(-33, 72, -26, 80), DD, 2))
    o.append(C(21, 63, 3, W, 2) + C(21, 63, 1.1, INK))
    heart = "M0 {b}C{n1} {c1} {n2} {c2} {n3} {c3}C{n4} {c4} {n5} {c5} 0 {c6}C{p5} {c5} {p4} {c4} {p3} {c3}C{p2} {c2} {p1} {c1} 0 {b}Z"

    def heart_d(cx, cy, s):
        pts = dict(b=cy + 11 * s, c1=cy + 4 * s, c2=cy - 4 * s, c3=cy - 7 * s, c4=cy - 10 * s, c5=cy - 9 * s, c6=cy - 4 * s,
                   n1=cx - 9 * s, n2=cx - 12 * s, n3=cx - 8 * s, n4=cx - 5 * s, n5=cx - 1 * s,
                   p1=cx + 9 * s, p2=cx + 12 * s, p3=cx + 8 * s, p4=cx + 5 * s, p5=cx + 1 * s)
        return heart.format(**{k: n(v) for k, v in pts.items()})

    o.append(P(heart_d(-3, 63, 1.45), W, 1.8))
    o.append(P(heart_d(-3, 63, 1.0), INK, 0))
    o.append(E(-7, 58, 2.6, 1.6, W, 0, -30))
    o.append(L("M10 74L16 78", 1.4))
    # neck
    o.append(S("M-15 10L15 10L13 26L-13 26Z", DM, 3.4, L("M-16 15L16 15M-16 20L16 20", 1.4)))

    # head (hero model), tilted up toward the deck
    head = []
    head.append(P("M-61 -66L-71 -64L-71 -34L-61 -32Z", DM, 4) + rivet(-66, -49, 2.6))
    head.append(P("M61 -66L71 -64L71 -34L61 -32Z", DM, 4) + rivet(66, -49, 2.6))
    head.append(P("M-1 -89L13 -89L11 -97L1 -97Z", DM, 3))
    head.append(L("M6 -97L8 -113L24 -125", 4))
    head.append(S(circ(27, -128, 7.5), W, 3.6, F(circ(31, -125, 7), DM) + C(24.5, -130.5, 2.2)))
    head.append(ray(27, -128, -150, 12, 19, 2.4) + ray(27, -128, -100, 12, 19, 2.4) + ray(27, -128, -40, 12, 18, 2.4))
    hd = "M-51 -90C-58 -90 -62 -86 -62 -79L-61 2Q-61 12 -51 12L51 12Q61 12 61 2L62 -79C62 -86 58 -90 51 -90Z"
    head.append(S(hd, W, 5,
                  F("M42 -94L70 -94L70 14L46 14Z", DM)
                  + F("M-70 -6C-30 -2 30 -2 70 -6L70 14L-70 14Z", HA)
                  + L("M-61 -77L61 -77", 2.6)
                  + "".join(rivet(x, -83.5, 2.2) for x in (-50, -30, -10, 10, 30, 50))
                  + rivet(-53, -68) + rivet(53, -68) + rivet(-53, -14) + rivet(53, -14)
                  + flicks((-52, -72, 48, -20), 8, 21, (3, 5), (10, 40), 1.1)))
    head.append(C(-14, -44, 27, W, 4.6))
    head.append("".join(C(-14 + 22.5 * math.cos(math.radians(a)), -44 + 22.5 * math.sin(math.radians(a)), 1.7, INK)
                        for a in (45, 135, 225, 315)))
    head.append(C(-14, -44, 19.5, DM, 3))
    head.append(C(-12, -48, 14, INK))
    head.append(C(-17.5, -54, 5, W) + C(-5.5, -41.5, 2.2, W) + C(-9, -57, 1.4, W))
    head.append(C(31, -57, 11.5, W, 4.2) + C(32, -60, 6.4, INK) + C(29.6, -62.4, 2.1, W))
    head.append(E(47, -39, 6, 3.4, DL))
    grille = "M14 -31Q30 -22 46 -31L46 -23Q30 -12 14 -23Z"
    head.append(S(grille, W, 3, "".join(L(f"M{x} -36L{x} -10", 1.6) for x in range(18, 46, 5))))
    o.append(g("".join(head), "rotate(-6 0 -10)"))
    return "".join(o)


def moss_reading():
    """Moss (hero-cast model) sitting among the roots reading a tiny book; origin at seat centre"""
    o = []
    o.append(E(4, -1, 178, 12, DM))
    body = ("M-138 -24C-158 -100 -152 -214 -112 -276C-82 -320 -34 -338 12 -336C66 -334 116 -306 138 -258"
            "C154 -222 158 -150 155 -92C153 -56 148 -32 140 -20C100 -10 -100 -10 -138 -24Z")
    capm = scallop([(-180, -420), (-180, -244), (-150, -252), (-124, -262), (-98, -280), (-70, -284), (-44, -292),
                    (-18, -294), (8, -298), (34, -294), (60, -288), (86, -282), (110, -266), (134, -250), (180, -236),
                    (180, -420)], 0.22)
    lsh = scallop([(-158, -230), (-130, -236), (-112, -214), (-120, -186), (-140, -170), (-162, -180)], 0.3)
    rlow = scallop([(160, -170), (132, -150), (110, -118), (118, -84), (150, -70), (170, -100)], 0.3)
    belly = scallop([(-96, -76), (-70, -84), (-44, -78), (-36, -60), (-58, -48), (-90, -52)], 0.28)
    inner = (F(capm, DL) + F(lsh, DL) + F(rlow, DL) + F(belly, DL)
             + F("M96 -350C140 -300 152 -200 142 -100C138 -60 124 -32 104 -8L210 -8L210 -350Z", DM)
             + F("M136 -270C156 -210 156 -120 144 -34L210 -34L210 -270Z", DD)
             + F("M-200 -44C-100 -26 100 -26 200 -44L200 0L-200 0Z", DM)
             + F("M-160 -110C-150 -60 -138 -38 -120 -26L-170 -26Z", DL)
             + L(capm, 2.4) + L(lsh, 2.2) + L(rlow, 2.2) + L(belly, 2)
             + tufts((-130, -330, 120, -300), 22, 7, 6, 1.5)
             + tufts((-150, -232, -118, -176), 5, 8, 5, 1.4) + tufts((116, -160, 150, -80), 5, 9, 5, 1.4)
             + specks((-120, -320, 110, -296), 26, 10, (0.8, 1.7))
             + E(-104, -150, 11, 7.5, W, 2.4) + F(ell(-100, -147, 8, 5), HA)
             + E(86, -206, 8.5, 6, W, 2.2) + E(108, -128, 9, 7, W, 2.2) + F(ell(111, -126, 6, 4.5), HA)
             + E(64, -58, 7, 5, W, 2) + E(-128, -96, 6, 4.5, W, 2)
             + L("M-122 -126L-110 -116L-114 -100M-110 -116L-97 -118", 2)
             + L("M120 -190L108 -176L114 -160", 2) + L("M-30 -40L-18 -32L-22 -20", 1.8)
             + flicks((-140, -260, 140, -40), 34, 12, (4, 8), (25, 70), 1.5))
    o.append(S(body, W, 5.5, inner))

    def sprout(x, y, s=1.0, lean=0):
        return g(L("M0 0Q-1 -8 0 -16", 2.4)
                 + S("M0 -15C-4 -22 -13 -24 -18 -20C-13 -14 -5 -13 0 -15Z", W, 2.4, F("M-18 -18L0 -18L0 -12L-18 -12Z", DL))
                 + S("M0 -16C3 -24 12 -27 17 -24C13 -17 5 -15 0 -16Z", W, 2.4, F("M0 -20L17 -20L17 -14L0 -14Z", DM)),
                 f"translate({x} {y}) rotate({lean}) scale({s})")
    o.append(sprout(-64, -322, 1.0, -14) + sprout(-24, -332, 0.8, -4) + sprout(66, -326, 0.8, 14)
             + sprout(-104, -292, 0.7, -26))
    o.append(tufts((-90, -330, 40, -326), 6, 13, 7, 2))
    for (mx, my, sc, rot) in ((108, -294, 1.0, 8), (128, -272, 0.75, 18), (92, -290, 0.6, -10)):
        o.append(g(S("M-5 0C-6 -8 -5 -16 -4 -22L4 -22C5 -16 6 -8 5 0Z", W, 2.6, F("M0 -24L8 -24L8 2L0 2Z", DL))
                   + S("M-18 -20C-18 -32 -8 -38 0 -38C8 -38 18 -32 18 -20C8 -17 -8 -17 -18 -20Z", W, 3.4,
                       F("M4 -40L22 -40L22 -16L8 -16Z", DM) + C(-8, -28, 3, W, 1.6) + C(4, -32, 2.4, W, 1.6)
                       + C(11, -24, 2, W, 1.4))
                   + L("M-14 -20Q0 -16 14 -20", 1.4),
                   f"translate({mx} {my}) rotate({rot}) scale({sc})"))

    # rope sash with acorn charm (charm hangs left of the book)
    sash = "M-160 -232C-90 -170 30 -128 170 -118L170 -100C30 -110 -90 -152 -160 -212Z"
    k = nid()
    o.append(f'<clipPath id="{k}"><path d="{body}"/></clipPath>')
    twist = ""
    for i in range(32):
        t = i / 31
        x = (1 - t) ** 3 * -160 + 3 * (1 - t) ** 2 * t * -90 + 3 * (1 - t) * t ** 2 * 30 + t ** 3 * 170
        y = (1 - t) ** 3 * -222 + 3 * (1 - t) ** 2 * t * -161 + 3 * (1 - t) * t ** 2 * -119 + t ** 3 * -109
        twist += L(f"M{n(x - 4)} {n(y - 8)}Q{n(x + 1)} {n(y - 2)} {n(x + 3)} {n(y + 8)}", 2)
    o.append(f'<g clip-path="url(#{k})">' + S(sash, W, 3.6, F("M-170 -200C-90 -146 30 -104 180 -96L180 -80L-170 -80Z", DM)
                                                + twist) + "</g>")
    ax, ay = -96, -176
    o.append(L(f"M{ax} {ay}Q{ax - 6} {ay + 10} {ax} {ay + 16}M{ax} {ay}Q{ax + 6} {ay + 10} {ax} {ay + 16}", 2))
    o.append(S(f"M{ax - 10} {ay + 28}C{ax - 10} {ay + 42} {ax - 4} {ay + 50} {ax} {ay + 52}C{ax + 4} {ay + 50} {ax + 10} {ay + 42} {ax + 10} {ay + 28}Z",
               W, 3, F(f"M{ax} {ay + 26}L{ax + 12} {ay + 26}L{ax + 12} {ay + 54}L{ax} {ay + 54}Z", DL)
               + T(ax - 6, ay + 32, ax - 7, ay + 38, ax - 4, ay + 44, 2, INK)))
    o.append(P(f"M{ax - 13} {ay + 29}Q{ax} {ay + 12} {ax + 13} {ay + 29}Z", CH, 3) + L(f"M{ax} {ay + 18}L{ax + 1} {ay + 12}", 2.6))

    # face: calm eyes lowered to the book
    o.append(P("M-66 -256Q-60 -266 -52 -260Q-46 -268 -38 -261Q-33 -255 -39 -252Q-52 -249 -66 -254Z", DM, 2.2))
    o.append(P("M2 -261Q8 -268 15 -263Q22 -270 30 -262Q35 -256 28 -253Q15 -250 2 -256Z", DM, 2.2))
    for ex, ey in ((-50, -227), (16, -228)):
        # downcast, half-lidded eyes on the page
        o.append(P(f"M{ex - 6} {ey - 1}Q{ex} {ey + 1.5} {ex + 6} {ey - 1}C{ex + 6} {ey + 6} {ex + 3} {ey + 8} {ex} {ey + 8}"
                   f"C{ex - 3} {ey + 8} {ex - 6} {ey + 6} {ex - 6} {ey - 1}Z", INK, 0))
        o.append(L(f"M{ex - 8} {ey - 2}Q{ex} {ey + 1} {ex + 8} {ey - 2}", 2.6))
        o.append(C(ex - 2, ey + 4.5, 1.4))
    o.append(S("M-24 -226C-31 -224 -33 -211 -25 -207C-17 -203 -6 -207 -6 -215C-6 -223 -16 -228 -24 -226Z", W, 3.2,
               F("M-14 -230L0 -230L0 -200L-20 -200C-12 -206 -10 -216 -14 -230Z", HA)))
    o.append(L("M-74 -194Q-16 -158 46 -196", 3.8))
    o.append(T(-80, -201, -78, -195, -73, -190, 2.2) + T(51, -203, 48, -197, 49, -190, 2.2))
    o.append(E(-82, -211, 14, 8, DL) + E(55, -213, 13, 8, DL))

    # tiny open book held up in front of the belly
    bx, by = -14, -116
    o.append(P(f"M{bx - 38} {by - 10}C{bx - 22} {by - 18} {bx - 10} {by - 16} {bx} {by - 8}C{bx + 10} {by - 16} {bx + 22} {by - 18} {bx + 38} {by - 10}"
               f"L{bx + 39} {by + 22}C{bx + 22} {by + 16} {bx + 10} {by + 18} {bx} {by + 26}C{bx - 10} {by + 18} {bx - 22} {by + 16} {bx - 39} {by + 22}Z",
               DD, 3.4))
    o.append(P(f"M{bx - 34} {by - 13}C{bx - 20} {by - 20} {bx - 9} {by - 18} {bx} {by - 11}L{bx} {by + 20}C{bx - 9} {by + 13} {bx - 20} {by + 12} {bx - 34} {by + 17}Z", W, 2.6))
    o.append(P(f"M{bx} {by - 11}C{bx + 9} {by - 18} {bx + 20} {by - 20} {bx + 34} {by - 13}L{bx + 34} {by + 17}C{bx + 20} {by + 12} {bx + 9} {by + 13} {bx} {by + 20}Z", W, 2.6))
    o.append(F(f"M{bx} {by - 11}C{bx + 9} {by - 18} {bx + 20} {by - 20} {bx + 34} {by - 13}L{bx + 34} {by + 17}C{bx + 20} {by + 12} {bx + 9} {by + 13} {bx} {by + 20}Z", DL))
    o.append("".join(L(f"M{bx - 29} {by - 8 + i * 6 + 0.0}Q{bx - 17} {by - 13 + i * 6} {bx - 5} {by - 8 + i * 6}", 1.3) for i in range(4)))
    o.append("".join(L(f"M{bx + 5} {by - 8 + i * 6}Q{bx + 17} {by - 13 + i * 6} {bx + 29} {by - 8 + i * 6}", 1.3) for i in range(3)))

    # stubby arms, paws on the book edges
    larm = ("M-140 -204C-166 -168 -160 -120 -126 -100C-106 -88 -78 -92 -56 -100C-44 -106 -44 -122 -54 -128"
            "C-70 -134 -92 -132 -104 -146C-114 -160 -114 -184 -112 -200Z")
    o.append(S(larm, W, 4.8, F("M-170 -190L-118 -190C-124 -160 -138 -148 -170 -150Z", DL)
               + F("M-150 -112C-120 -94 -90 -92 -60 -98L-60 -80L-150 -80Z", DM)
               + L("M-58 -124Q-52 -118 -56 -110M-66 -126Q-60 -120 -63 -112", 1.8)))
    rarm = ("M120 -210C146 -176 140 -124 108 -104C90 -92 60 -94 36 -100C24 -104 22 -120 32 -126"
            "C50 -134 76 -132 88 -146C98 -158 98 -184 96 -204Z")
    o.append(S(rarm, W, 4.8, F("M112 -206C132 -164 126 -122 100 -104L150 -104L150 -206Z", DM)
               + F("M90 -214L150 -214C136 -190 116 -182 98 -184Z", DL)
               + L("M34 -124Q28 -118 32 -110M42 -126Q36 -120 39 -112", 1.8)))
    # boulder feet
    for (fd, toes, sh) in (
        ("M-130 -60C-144 -40 -138 -6 -108 -2C-80 2 -60 -6 -58 -26C-56 -48 -80 -64 -104 -64C-116 -64 -124 -62 -130 -60Z",
         ((-118, -60), (-100, -64), (-80, -58)), "M-80 -64C-56 -48 -56 -10 -90 0L-50 4L-50 -64Z"),
        ("M30 -62C10 -50 10 -10 40 -2C66 4 92 -6 96 -28C100 -52 76 -66 52 -66C42 -66 36 -64 30 -62Z",
         ((40, -62), (58, -67), (78, -60)), "M72 -66C98 -50 98 -10 64 2L104 4L104 -66Z")):
        o.append(S(fd, W, 4.8, F(sh, DM) + flicks((-140, -50, 100, -6), 6, 33, (3, 6), (30, 70), 1.4)))
        for tx, ty in toes:
            o.append(S(ell(tx, ty, 8, 6), W, 3, F(ell(tx + 3, ty + 2, 6, 4.5), DL)))
    o.append(tufts((-120, -64, -70, -58), 3, 31, 5, 1.6) + tufts((36, -68, 84, -62), 3, 32, 5, 1.6))

    # the big head leaf, grown from the crown on its own stem
    o.append(L("M6 -334C4 -350 10 -366 26 -377", 5))
    o.append(T(8, -336, 9, -352, 20, -370, 1.4, W))
    lf = "M26 -377C38 -420 104 -452 170 -446C150 -404 92 -370 26 -377Z"
    o.append(S(lf, W, 4.4, F("M20 -374C80 -392 130 -420 172 -446L190 -380L20 -360Z", DM)
               + L("M27 -377C70 -398 122 -428 166 -445", 2.4)
               + "".join(L(f"M{x} {y}Q{x + 2} {y - 12} {x + 10} {y - 22}", 1.6) for x, y in
                         ((52, -388), (82, -404), (110, -419), (136, -432)))
               + "".join(L(f"M{x} {y}Q{x + 10} {y + 2} {x + 18} {y - 2}", 1.4) for x, y in
                         ((60, -391), (92, -409), (122, -424)))))
    return "".join(o)


# --------------------------------------------------------------------------- scene
def ground():
    o = []
    gd = ("M30 926C120 912 220 910 330 914C430 917 520 904 620 905C760 907 900 901 1040 905C1180 909 1290 903 1396 909"
          "L1396 946C1300 960 1180 966 1040 970C880 976 720 988 560 990C420 992 260 980 140 966C90 960 50 948 30 938Z")
    o.append(F(gd, DL))
    o.append(L("M30 926C120 912 220 910 330 914C430 917 520 904 620 905", 3))
    o.append(L("M1040 905C1180 909 1290 903 1396 909", 3))
    o.append(E(760, 914, 330, 24, DM))
    # far tufts and pebbles
    for i, (x, y, s) in enumerate(((70, 924, 0.9), (190, 916, 1.0), (300, 918, 0.8), (430, 935, 1.1), (560, 912, 0.9),
                                   (1110, 912, 1.0), (1385, 912, 0.9), (250, 952, 1.0), (880, 950, 1.1), (1000, 958, 0.9),
                                   (1090, 940, 1.0), (360, 962, 0.8), (480, 958, 0.8), (640, 984, 0.9),
                                   (760, 966, 0.8), (1210, 968, 0.9), (1330, 962, 0.8), (110, 950, 0.9))):
        o.append(grass(x, y, s, i + 3))
    o.append(E(150, 938, 6, 3.5, W, 2.2) + E(282, 932, 4, 2.6, W, 2) + E(940, 962, 5, 3, W, 2) + E(820, 974, 4, 2.6, W, 2))
    return "".join(o)


def rocks():
    o = []
    for d, sh, crack in (
        ("M380 918C372 894 386 864 414 856C442 848 478 852 492 872C502 888 500 908 490 918Z",
         "M458 850C494 860 508 888 494 922L520 922L520 850Z", "M402 884L414 894L408 910"),
        ("M1094 932C1088 910 1100 886 1122 880C1144 874 1162 884 1166 902C1169 916 1165 926 1158 932Z",
         "M1140 874C1164 884 1172 904 1160 936L1180 936L1180 874Z", "M1104 902L1114 910L1110 922"),
        ("M1352 948C1348 934 1358 924 1372 924C1386 924 1394 934 1392 948Z",
         "M1378 920C1394 928 1398 940 1390 952L1400 952L1400 920Z", "M1362 936L1368 942"),
    ):
        o.append(S(d, W, 4.4, F(sh, HA) + L(crack, 1.8) + specks((400, 860, 1400, 920), 0, 1)))
    o.append(E(1120, 930, 9, 5, W, 2.6) + F(ell(1123, 932, 6, 3), HA))
    return "".join(o)


def root_fingers():
    o = []
    for c, w0, w1, sd in FINGERS:
        gm = tube_geom(c, w0, w1, flare=0.2)
        d = geom_d(gm)
        rim = gm.difference(affinity.translate(gm, -5, -4))
        o.append(S(d, W, 4, F(geom_d(rim), DD) + tube_grooves(c, w0, w1, (-0.3, 0.35), sd, (1.3, 1.8))))
    return "".join(o)


def tree_silhouette():
    geoms = [TRUNK_POLY] + [tube_geom(c, w0, w1) for c, w0, w1, _ in LIMBS] + \
            [tube_geom(c, w0, w1, flare=0.6) for c, w0, w1, _ in ROOTS]
    sil = unary_union(geoms).buffer(9, join_style=1).buffer(-9, join_style=1).buffer(0)
    return sil


def tree(sil):
    o = []
    d = geom_d(sil)
    # broad shade on the trunk's right side
    side_pts = []
    for y in range(220, 912, 8):
        x0, x1 = trunk_span(min(max(y, 228), 904))
        side_pts.append((x0 + (x1 - x0) * 0.68 + 10 * math.sin(y / 60), y))
    side = Polygon(side_pts + [(1500, 912), (1500, 228)]).intersection(TRUNK_POLY)
    band = sil.difference(affinity.translate(sil, -22, -15))
    rim = sil.difference(affinity.translate(sil, -8, -6))
    inner = [F(geom_di(side), DL), F(geom_di(band), HA), F(geom_di(rim), DD)]
    # bark grooves along the trunk
    rnd = random.Random(5)
    bark = []
    for f in (0.07, 0.17, 0.27, 0.38, 0.5, 0.61, 0.72, 0.82, 0.91):
        y = 900 - rnd.uniform(0, 30)
        while y > 230:
            y1 = max(226, y - rnd.uniform(28, 90))
            pts = []
            for j in range(10):
                yy = y + (y1 - y) * j / 9
                x0, x1 = trunk_span(yy)
                pts.append((x0 + (x1 - x0) * f + 4 * math.sin(yy / 34 + f * 9), yy))
            bark.append((int_d(pts), rnd.uniform(1.5, 2.4) + (0.4 if f > 0.6 else 0)))
            y = y1 - rnd.uniform(10, 34)
    # cross cracks
    for _ in range(26):
        y = rnd.uniform(250, 880)
        x0, x1 = trunk_span(y)
        x = rnd.uniform(x0 + 12, x1 - 12)
        bark.append((f"M{round(x)} {round(y)}q4 2 9 0", 1.5))
    inner.append(batched(bark))
    for c, w0, w1, sd in LIMBS:
        inner.append(tube_grooves(c, w0, w1, (-0.55, -0.12, 0.3, 0.66), sd))
    for c, w0, w1, sd in ROOTS:
        inner.append(tube_grooves(c, w0, w1, (-0.4, 0.15, 0.6), sd, (1.4, 2.0)))
    # knots
    inner.append(knot(690, 752, 4, 9, 8) + knot(842, 690, 3.5, 8, -6) + knot(790, 312, 4, 9, 4)
                 + knot(560, 396, 3, 6, 80) + knot(700, 460, 3.5, 8, 0))
    o.append(S(d, W, 5.2, "".join(inner), rule="evenodd"))
    # junction folds (where limbs leave the trunk)
    o.append(L("M478 596Q462 590 452 576M466 592Q456 598 446 598", 2.4)
             + leaf(452, 576, -120, 0.75) + leaf(446, 598, 170, 0.7) + leaf(462, 588, -170, 0.6))
    o.append(T(690, 300, 700, 330, 690, 368, 2.2) + T(808, 262, 812, 280, 830, 296, 2.2)
             + T(660, 608, 670, 622, 664, 640, 2) + T(588, 872, 600, 880, 616, 884, 2)
             + T(900, 872, 914, 880, 930, 884, 2) + T(318, 470, 330, 462, 352, 462, 2))
    return "".join(o)


def canopy_back():
    return (clump(590, 128, 105, 88, 31, False) + clump(930, 118, 115, 88, 32, False)
            + clump(280, 210, 105, 88, 33, False) + clump(1222, 200, 112, 96, 34, False)
            + clump(640, 205, 66, 44, 35, False, 12) + clump(870, 195, 70, 44, 36, False, 12))


def canopy_front():
    return (clump(150, 228, 112, 98, 41) + clump(425, 150, 108, 92, 42) + clump(720, 115, 100, 82, 43)
            + clump(1070, 128, 108, 88, 44) + clump(1300, 168, 70, 80, 45, True, 14)
            + clump(330, 292, 58, 40, 46, True, 12))


def hanging_moss():
    o = []
    for x, y0, ln, sd in ((72, 300, 120, 1), (118, 318, 80, 2), (168, 318, 140, 3), (205, 306, 70, 4),
                          (262, 292, 92, 5), (300, 318, 64, 6), (372, 300, 70, 7), (470, 236, 72, 8)):
        o.append(drip(x, y0, ln, sd))
    for x, y0, ln, sd in ((95, 300, 150, 11), (232, 300, 98, 12), (345, 310, 80, 13), (520, 225, 90, 14)):
        o.append(vine(x, y0, ln, sd))
    # vine curling round the platform limb
    o.append(L("M600 368Q590 392 572 384Q556 376 548 398Q540 420 522 410", 2.2)
             + leaf(590, 392, 120, 0.55) + leaf(552, 386, 60, 0.5) + leaf(530, 414, 150, 0.55))
    return "".join(o)


def lantern_swag():
    o = []
    p0, c, p1 = (528, 228), (596, 352), (668, 302)
    pts = [qbez(p0, c, p1, i / 20) for i in range(21)]
    o.append(L(poly_d(pts), 1.8))
    o.append(C(668, 302, 3, INK) + C(528, 228, 3, INK))
    for i, t in enumerate((0.2, 0.42, 0.64, 0.85)):
        x, y = qbez(p0, c, p1, t)
        o.append(paper_lantern(x, y, 10.5 - i * 0.5, i, 6 + (i % 2) * 7))
    return "".join(o)


def top_deck():
    o = []
    # knee braces into the trunk
    o.append(P(plank(662, 240, 692, 292, 9), W, 3) + P(plank(880, 240, 826, 294, 9), W, 3))
    # flag pole and swallowtail pennant (blowing right with the smoke)
    o.append(P(rect(646, 80, 654, 226), W, 3) + F(rect(650, 80, 654, 226), DM))
    o.append(C(650, 76, 5.5, W, 3))
    flag = "M654 86C676 78 700 94 736 84L716 104L740 124C704 132 680 116 654 124Z"
    o.append(S(flag, W, 3.6, F("M654 100C676 94 702 108 730 100L726 112C700 120 676 106 654 114Z", HA)
               + F("M700 80L744 80L744 130L700 130Z", DM)))
    star = "M676 94L679 101L686 101L680.5 105.5L682.5 113L676 108.5L669.5 113L671.5 105.5L666 101L673 101Z"
    o.append(S(circ(676, 104, 10), W, 2.6) + P(star, INK, 1.2))
    # telescope on a tripod
    o.append(L("M858 168L838 224M858 168L878 224M858 168L861 224", 3.4))
    tel = g(S("M-34 -6L36 -9L36 9L-34 6Z", W, 3.6, F("M10 -12L40 -12L40 12L10 12Z", DM) + F(rect(-36, 2, 40, 12), DL))
            + P(rect(36, -12, 48, 12), W, 3.4) + F(rect(42, -12, 48, 12), DM)
            + P(rect(-46, -4.5, -33, 4.5), DD, 2.8) + P(rect(-10, -9, -4, 9), DD, 2.2)
            + E(48, 0, 3.4, 12, W, 2.6) + C(0, 8, 3, W, 2.2),
            "translate(864 156) rotate(-24) scale(1.35)")
    o.append(tel)
    # deck boards and railing
    o.append(S("M636 224L904 224L902 243L638 243Z", W, 4.2,
               F(rect(860, 220, 910, 246), DM) + L("M636 233.5L904 233.5", 1.8)
               + "".join(C(x, 229, 1.2, INK) + C(x, 238, 1.2, INK) for x in range(650, 900, 34))
               + flicks((640, 225, 900, 242), 10, 61, (5, 9), (0, 8), 1.2)))
    posts = (642, 700, 760, 820, 898)
    for a, b in zip(posts, posts[1:]):
        o.append(L(f"M{a + 4} 192L{b - 4} 222M{a + 4} 222L{b - 4} 192", 2.6))
    o.append(P("M636 186L904 184L904 193L636 195Z", W, 3.4) + F("M860 184L904 184L904 193L860 193Z", DM))
    for x in posts:
        o.append(P(rect(x - 3.5, 188, x + 3.5, 224), W, 3) + C(x, 190, 1.2, INK))
    return "".join(o)


def knotted_rope():
    o = [L("M808 243C810 300 804 380 808 486", 3.4)]
    for y in range(270, 480, 34):
        o.append(E(808 + 2 * math.sin(y), y, 5.5, 4.2, W, 2.6))
    return "".join(o)


def small_platform():
    o = []
    o.append(S("M220 440L400 440L398 457L222 457Z", W, 4.2,
               F(rect(360, 436, 404, 460), DM) + L("M220 448.5L400 448.5", 1.6)
               + "".join(C(x, 444, 1.1, INK) + C(x, 453, 1.1, INK) for x in range(232, 396, 30))))
    # lashings where it rests on the limb
    o.append(L("M262 457L270 470M272 457L280 470M340 457L346 470M350 457L356 470", 2))
    posts = (228, 282, 336, 394)
    for a, b in zip(posts, posts[1:]):
        o.append(L(f"M{a + 4} 410L{b - 4} 438M{a + 4} 438L{b - 4} 410", 2.4))
    o.append(P("M220 404L400 402L400 410L220 412Z", W, 3.2))
    for x in posts:
        top = 394 if x == 394 else 404
        o.append(P(rect(x - 3.5, top, x + 3.5, 441), W, 3))
    o.append(C(394, 392, 4.5, W, 2.6))
    # birdhouse on a tall pole at the corner
    o.append(P(rect(225, 370, 231, 405), W, 2.8))
    o.append(birdhouse(228, 372, 0.95))
    o.append(bird(234, 327, 0.8))
    return "".join(o)


def rope_bridge():
    o = []
    a, c, b = (400, 446), (492, 542), (586, 524)
    ra, rc, rb = (396, 396), (492, 500), (588, 458)
    # back hand rope
    o.append(L(poly_d([qbez((396, 390), (492, 490), (588, 452), i / 24) for i in range(25)]), 2.2))
    # planks
    for i in range(12):
        t = 0.04 + i * 0.083
        x, y = qbez(a, c, b, t)
        dx = 2 * (1 - t) * (c[0] - a[0]) + 2 * t * (b[0] - c[0])
        dy = 2 * (1 - t) * (c[1] - a[1]) + 2 * t * (b[1] - c[1])
        ang = math.degrees(math.atan2(dy, dx))
        o.append(g(P(rect(-6.5, -4, 6.5, 4), W, 2.6) + F(rect(1, -2.5, 5, 2.5), HA),
                   f"translate({n(x)} {n(y)}) rotate({n(ang)})"))
        hx, hy = qbez(ra, rc, rb, t)
        o.append(L(f"M{n(hx)} {n(hy)}L{n(x)} {n(y - 3)}", 1.5))
    # rope under the planks and front hand rope
    o.append(L(poly_d([(x, y + 5) for x, y in (qbez(a, c, b, i / 24) for i in range(25))]), 1.8))
    o.append(L(poly_d([qbez(ra, rc, rb, i / 24) for i in range(25)]), 3))
    o.append(bird(468, 460, 0.7, True))
    return "".join(o)


def main_platform():
    o = []
    # braces under the deck
    o.append(P(plank(600, 540, 652, 574, 9), W, 3))
    o.append(P(plank(1074, 540, 872, 662, 11), W, 3.4) + F(plank(1074, 543, 872, 665, 4), HA))
    o.append(P(plank(1124, 540, 1100, 590, 8), W, 3))
    return "".join(o)


def deck_front():
    o = []
    o.append(S("M580 519L1128 517L1126 543L582 543Z", W, 4.4,
               F(rect(1080, 514, 1132, 546), DM) + L("M580 531L1128 530", 1.8)
               + "".join(C(x, 524.5, 1.2, INK) + C(x, 537, 1.2, INK) for x in range(596, 1120, 30))
               + flicks((585, 520, 1120, 542), 22, 71, (6, 10), (0, 6), 1.2)))
    for x in (604, 760, 940, 1104):
        o.append(P(rect(x - 6, 543, x + 6, 552), DM, 2.6))
    return o


def railing_main():
    o = []
    posts = (588, 640, 700, 760, 820, 880, 940, 1004)
    for a, b in zip(posts, posts[1:]):
        o.append(L(f"M{a + 4} 494L{b - 4} 517M{a + 4} 517L{b - 4} 494", 2.6))
    o.append(P("M582 488L1010 486L1010 495L582 497Z", W, 3.4))
    for x in posts:
        top = 456 if x == 588 else 490
        o.append(P(rect(x - 4, top, x + 4, 520), W, 3) + C(x, top + 3, 1.2, INK))
    o.append(C(588, 454, 5, W, 2.8))
    return "".join(o)


def cabin():
    o = []
    wall = "M858 521L861 390L1100 388L1098 521Z"
    planks = "".join(L(f"M858 {y}Q980 {y - 1.5} 1100 {y}", 1.6) for y in range(404, 520, 15))
    grain = flicks((866, 395, 1094, 516), 26, 81, (6, 12), (-4, 4), 1.1)
    nails = "".join(C(x, y + 7, 1.1, INK) for y in range(392, 515, 15) for x in (866, 1092))
    o.append(S(wall, W, 4.6, F("M1060 384L1104 384L1104 524L1060 524Z", DM) + F(rect(850, 386, 1110, 404), HA)
               + planks + grain + nails))
    # door on the right
    door = "M1036 521L1036 434C1036 416 1047 406 1062 406C1077 406 1088 416 1088 434L1088 521Z"
    o.append(S(door, W, 4, F("M1068 400L1094 400L1094 524L1068 524Z", DM)
               + "".join(L(f"M{x} 404L{x} 524", 1.6) for x in (1049, 1062, 1075))
               + P(rect(1032, 446, 1060, 452), INK, 0) + P(rect(1032, 494, 1060, 500), INK, 0)))
    o.append(S(circ(1062, 432, 8), DD, 2.6) + C(1059, 429, 2, W))
    o.append(C(1080, 472, 4, W, 2.4) + C(1081, 473, 1.4, INK))
    # left shutter, swung open
    sh = "M866 404L898 404L898 488L866 492Z"
    o.append(S(sh, W, 3.6, "".join(L(f"M{x} 380L{x} 486", 1.5) for x in (874, 882, 890))
               + L("M868 396L896 396M868 468L896 466M868 468L896 396", 2.2) + F(rect(886, 378, 900, 488), DL)))
    return "".join(o)


def cabin_window():
    """window with Pip leaning out over the sill (drawn after the roof so his beanie overlaps the eave)"""
    o = []
    win_open = rect(912, 412, 1002, 484)
    inside, outside = pip_window()
    k = nid()
    o.append(P(win_open, DD, 0))
    o.append(F("M912 412L1002 412L1002 424L912 438Z", INK))
    frame = "M902 404L1012 404L1012 484L1002 484L1002 412L912 412L912 484L902 484Z"
    o.append(P(frame, W, 3.6) + F("M1002 408L1012 408L1012 484L1002 484Z", DM))
    o.append(f'<clipPath id="{k}"><path d="M880 300L1040 300L1040 484L880 484Z"/></clipPath>')
    o.append(f'<g clip-path="url(#{k})">{g(inside, "translate(957 508) scale(0.72)")}</g>')
    o.append(P("M895 482L1019 482L1017 495L897 495Z", W, 3.6) + F("M980 484L1018 484L1018 495L980 495Z", HA))
    o.append(g(outside, "translate(957 508) scale(0.72)"))
    return "".join(o)


def smoke():
    """billowing smoke: a few lobed puffs swelling fast as they drift right, merged into one cloud"""
    puffs = ((1046, 250, 7), (1055, 231, 10.5), (1072, 211, 14.5), (1101, 196, 19), (1139, 186, 23), (1182, 180, 21))
    shapes = [Polygon(path_pts(fuzz(x, y, r, 7 + i, 0.3, 90 + i, 0.4), 2)).buffer(0) for i, (x, y, r) in enumerate(puffs)]
    cloud = unary_union(shapes)
    inner = F(geom_d(cloud.difference(affinity.translate(cloud, -9, -9))), DL)
    # billow edges: each nearer (smaller) puff's rim where it overlaps the next one
    for a, b in zip(shapes, shapes[1:]):
        seg = a.exterior.intersection(b.buffer(-2))
        for part in getattr(seg, "geoms", [seg]):
            if part.geom_type == "LineString" and part.length > 6:
                inner += L(poly_d(list(part.coords)), 2.2)
    for (x, y, r) in puffs[2:]:
        inner += L(f"M{n(x - r * 0.45)} {n(y - r * 0.05)}q{n(r * 0.2)} {n(-r * 0.5)} {n(r * 0.7)} {n(-r * 0.35)}", 1.6)
    return (S(geom_d(cloud), W, 3.4, inner)
            + S(fuzz(1222, 160, 9, 7, 0.3, 99, 0.4), W, 2.8) + S(fuzz(1240, 144, 5.5, 6, 0.3, 98, 0.4), W, 2.4))


def roof():
    o = []
    # crooked chimney in front of the roof slope
    roofd = "M840 398L888 304L1072 298L1118 396Z"
    rows = ""
    for i, y in enumerate(range(306, 400, 14)):
        off = 0 if i % 2 else 11
        x_start = 820 + off - 22
        dd = f"M{x_start} {y + 14}"
        for x in range(x_start, 1140, 22):
            dd += f"Q{x + 11} {y + 24} {x + 22} {y + 14}"
        rows += L(dd, 2)
        rows += L("".join(f"M{x + 22} {y + 14}L{x + 22} {y + 4}" for x in range(x_start, 1140, 22)), 1.3)
    shade = F("M1030 290L1130 290L1130 400L1060 400Z", DM) + F("M820 384L1130 384L1130 400L820 400Z", DL)
    o.append(S(roofd, W, 4.8, shade + rows + flicks((850, 305, 1110, 392), 18, 91, (4, 7), (60, 120), 1.2)))
    o.append(P("M834 396L1124 394L1124 404L834 406Z", W, 3.6) + F("M1070 393L1124 393L1124 404L1070 404Z", DM))
    o.append(P("M884 300Q980 290 1076 295L1076 305Q980 299 884 309Z", W, 3.4)
             + "".join(C(x, 300, 1.4, INK) for x in range(900, 1070, 24)))
    # chimney
    ch = "M1026 352L1031 304L1025 272L1060 266L1068 302L1062 352Z"
    bricks = "".join(L(f"M1020 {y}L1072 {y - 2}", 1.6) for y in (284, 298, 312, 326, 340))
    bricks += "".join(L(f"M{x} {y}L{x} {y + 14}", 1.4) for x, y in ((1040, 270), (1052, 284), (1038, 298),
                                                                   (1050, 312), (1040, 326), (1052, 340)))
    o.append(S(ch, W, 4.4, F("M1048 260L1074 260L1074 356L1050 356Z", DM) + bricks))
    o.append(P("M1018 274L1064 262L1068 272L1022 284Z", W, 3.6) + F("M1050 262L1070 262L1070 276L1050 280Z", DM))
    o.append(P("M1018 352L1068 352L1070 360L1016 360Z", DM, 2.6))
    # weather vane on the ridge
    o.append(L("M956 296L956 226", 3.2) + C(956, 222, 4, W, 2.6))
    o.append(L("M936 262L976 262", 2.4) + C(934, 262, 3, W, 2) + C(978, 262, 3, W, 2))
    o.append(P("M926 240L942 231L940 238L986 238L986 243L940 243L942 249Z", INK, 1.6))
    o.append(P("M982 232L1000 229L996 240L1000 251L982 248Z", W, 2.6) + L("M986 236L996 236M986 244L996 244", 1.3))
    o.append(P("M946 298L966 298L962 292L950 292Z", DD, 2))
    # smoke curls drifting right (with the wind)
    o.append(smoke())
    # eave lantern
    o.append(L("M852 404L852 412", 1.6) + brass_lantern(852, 410, 0.68))
    return "".join(o)


def crane():
    o = []
    o.append(P(rect(1108, 440, 1118, 542), W, 3.4) + F(rect(1114, 440, 1118, 542), DM))
    o.append(P("M1104 440L1196 440L1196 450L1104 450Z", W, 3.4) + F(rect(1170, 440, 1196, 450), DM))
    o.append(P(plank(1116, 490, 1162, 448, 7), W, 2.8))
    o.append(L("M1184 450L1184 458", 2.4))
    o.append(S(circ(1184, 466, 10), W, 3, F(circ(1188, 469, 8), DM)) + C(1184, 466, 2.4, INK))
    o.append(L("M1174 466C1160 470 1140 486 1122 502", 2.2) + P(rect(1118, 498, 1126, 506), DD, 1.6))
    o.append(L("M1194 466L1194 598", 2.2))
    # bucket bringing Moss a fresh book
    o.append(L("M1172 610Q1194 582 1216 610", 2.6) + C(1194, 597, 2.6, W, 1.8))
    o.append(P(rect(1182, 598, 1194, 612), W, 2.4, 'transform="rotate(-12 1188 605)"'))
    o.append(P(rect(1196, 594, 1206, 612), DM, 2.4, 'transform="rotate(10 1201 603)"'))
    bk = "M1170 610L1218 610L1212 650L1176 650Z"
    o.append(S(bk, W, 4, F("M1200 606L1222 606L1214 654L1196 654Z", DM)
               + "".join(L(f"M{x} 606L{x - 1} 654", 1.4) for x in (1182, 1192, 1202, 1210))
               + P("M1166 620L1222 620L1222 626L1166 626Z", DD, 0) + P("M1166 638L1222 638L1222 643L1166 643Z", DD, 0)))
    o.append(E(1194, 610, 24, 4, W, 2.8))
    return "".join(o)


def ladder():
    o = []
    rails = ((1018, 906, 1010, 498), (1100, 906, 1092, 498))
    for i in range(12):
        y = 888 - i * 32
        f = (906 - y) / (906 - 498)
        xa = 1018 + (1010 - 1018) * f
        xb = 1100 + (1092 - 1100) * f
        o.append(P(rect(xa, y - 3, xb, y + 3), W, 2.8) + F(rect(xa, y, xb, y + 3), HA))
    for x0, y0, x1, y1 in rails:
        o.append(S(plank(x0, y0, x1, y1, 8), W, 3.4, F(plank(x0 + 2.5, y0, x1 + 2.5, y1, 3), DM)))
    return "".join(o)


def tire_swing():
    o = []
    o.append(E(522, 906, 36, 6, DM))
    o.append(L("M524 604C526 680 520 740 522 792", 3))
    o.append(E(524, 604, 7, 9, W, 2.6) + L("M518 600L530 608M518 606L530 614", 1.6))
    ring = ell(522, 832, 35, 41) + ell(526, 834, 15, 21)
    o.append(S(ring, INK, 4, L(ell(522, 832, 27, 33), 1.6, W, 'stroke-dasharray="3 5"')
               + T(494, 820, 496, 800, 512, 794, 2.4, W) + T(500, 856, 512, 868, 528, 869, 1.4, W), "evenodd"))
    o.append(L("M516 790Q522 786 528 790L528 800Q522 796 516 800Z", 2.2) + E(522, 795, 8, 5, W, 2.4))
    return "".join(o)


def door():
    o = []
    cx, cy = 745, 842
    k = nid()
    o.append(f'<clipPath id="{k}"><path d="M600 700L900 700L900 897L600 897Z"/></clipPath>')
    ring = circ(cx, cy, 72) + circ(cx, cy, 58)
    blocks = "".join(L(f"M{n(cx + 58 * math.cos(math.radians(a)))} {n(cy + 58 * math.sin(math.radians(a)))}"
                       f"L{n(cx + 72 * math.cos(math.radians(a)))} {n(cy + 72 * math.sin(math.radians(a)))}", 2.4)
                     for a in range(-180, 20, 20))
    disc = circ(cx, cy, 58)
    planks = "".join(L(f"M{x} 780L{x} 900", 1.8) for x in range(703, 790, 14))
    grain = flicks((692, 790, 800, 895), 16, 101, (5, 9), (80, 100), 1.1)
    hinges = (P("M690 818L736 816L738 824L690 826Z", INK, 0) + P("M690 866L736 864L738 872L690 874Z", INK, 0)
              + "".join(C(x, y, 1.3, W) for x, y in ((700, 821), (716, 820), (730, 820), (700, 869), (716, 868), (730, 868))))
    door_g = (S(ring, W, 4, F(circ(cx + 18, cy + 14, 66), HA) + blocks, "evenodd")
              + S(disc, W, 4.4, F("M772 770L812 770L812 900L772 900C784 870 784 810 772 770Z", DM) + planks + grain + hinges))
    o.append(f'<g clip-path="url(#{k})">{door_g}</g>')
    o.append(L("M672 897L818 897", 4.4))
    # porthole
    o.append(C(cx, 814, 18, DM, 3.6) + C(cx, 814, 11.5, W, 3))
    o.append("".join(C(cx + 14.7 * math.cos(math.radians(a)), 814 + 14.7 * math.sin(math.radians(a)), 1.4, W)
                     for a in range(0, 360, 45)))
    o.append(L("M738 816Q739 808 746 806", 1.8) + L("M744 822L752 812", 1.4))
    o.append(C(784, 856, 5, W, 2.6) + C(785, 857, 1.8, INK))
    # doorstep slab and welcome mat of moss
    o.append(S("M668 896L822 896L830 912L660 912Z", W, 3.8, F("M780 890L840 890L840 916L790 916Z", HA)
               + L("M700 904L712 900M760 906L772 902", 1.4)))
    # bracket lantern by the door
    o.append(L("M812 768L840 768Q846 768 846 774", 3.2) + L("M818 768Q822 760 830 762", 2))
    o.append(P(rect(806, 762, 814, 776), DD, 2))
    o.append(brass_lantern(846, 774, 0.8))
    return "".join(o)


STAIR_TH0, STAIR_DTH, STAIR_DY, STAIR_N = 58, 14, 12.6, 28
STAIR_K = 0.2           # slight top-down view: nearer points sit lower
STAIR_LS, STAIR_WP, STAIR_TH = 40, 22, 7


def stair_frame(th):
    """trunk centre, radius and tread height for helix angle th (degrees)"""
    y = 886 - (th - STAIR_TH0) / STAIR_DTH * STAIR_DY
    x0, x1 = trunk_span(min(y, 904))
    return (x0 + x1) / 2, min((x1 - x0) / 2, 158), y


def helix(th, r_out, dy=0.0, t=0.0):
    cx, R, y = stair_frame(th)
    a = math.radians(th)
    sa, ca = math.sin(a), math.cos(a)
    r = R + r_out
    return (cx + r * sa + t * ca, y + STAIR_K * (r * ca - t * sa) + dy)


def ribbon(th_a, th_b, r_out, dy0, dy1, fill, sw):
    ths = [th_a + (th_b - th_a) * i / max(2, int(abs(th_b - th_a) / 2)) for i in range(max(2, int(abs(th_b - th_a) / 2)) + 1)]
    top = [helix(t, r_out, dy0) for t in ths]
    bot = [helix(t, r_out, dy1) for t in ths]
    return P(poly_d(top + bot[::-1], True), fill, sw)


def stairs_layers():
    """spiral stair round the trunk: treads on a curved stringer with a post-and-rail banister"""
    def spans(front):
        out, a = [], None
        th = STAIR_TH0 - STAIR_DTH * 0.25
        end = STAIR_TH0 + STAIR_DTH * (STAIR_N - 0.6)
        while th <= end:
            vis = math.cos(math.radians(th)) > -0.02
            if vis == front and a is None:
                a = th
            if vis != front and a is not None:
                out.append((a, th))
                a = None
            th += 1
        if a is not None:
            out.append((a, end))
        return out

    layers = {}
    for front in (False, True):
        o = []
        for a, b in spans(front):
            o.append(ribbon(a, b, STAIR_LS, STAIR_TH, STAIR_TH + 11, W, 2.8))
            o.append(L(poly_d([helix(a + (b - a) * i / 30, STAIR_LS, STAIR_TH + 5.5) for i in range(31)]), 1.3))
        treads = []
        for i in range(STAIR_N):
            th = STAIR_TH0 + i * STAIR_DTH
            ca = math.cos(math.radians(th))
            if (ca > -0.02) != front:
                continue
            sa = math.sin(math.radians(th))
            r0, r1, hw = -8, STAIR_LS + 3, STAIR_WP / 2
            top = [helix(th, r0, 0, -hw), helix(th, r1, 0, -hw), helix(th, r1, 0, hw), helix(th, r0, 0, hw)]
            t = []
            if ca > 0.05:
                e0, e1 = top[1], top[2]
                t.append(P(poly_d([e0, e1, (e1[0], e1[1] + STAIR_TH), (e0[0], e0[1] + STAIR_TH)], True), W, 2.4))
            side = (top[0], top[1]) if sa > 0 else (top[3], top[2])
            if abs(sa) > 0.05:
                t.append(P(poly_d([side[0], side[1], (side[1][0], side[1][1] + STAIR_TH),
                                   (side[0][0], side[0][1] + STAIR_TH)], True), DM, 2.4))
            t.append(P(poly_d(top, True), W, 2.8))
            t.append(L(poly_d([helix(th, 6, 0, -hw * 0.9), helix(th, 6, 0, hw * 0.9)]), 1.2))
            treads.append((ca, "".join(t)))
        treads.sort(key=lambda it: it[0])
        o += [tx for _, tx in treads]
        # banister: posts on every other tread, rail along the helix
        for i in range(0, STAIR_N, 2):
            th = STAIR_TH0 + i * STAIR_DTH
            if (math.cos(math.radians(th)) > -0.02) != front:
                continue
            b = helix(th, STAIR_LS - 2, 0)
            o.append(P(rect(b[0] - 2.6, b[1] - 34, b[0] + 2.6, b[1] + 2), W, 2.2))
        for a, b in spans(front):
            o.append(ribbon(a, b, STAIR_LS - 2, -38, -32, W, 2.6))
        layers[front] = "".join(o)
    return layers[False], layers[True]


def stepping_stones():
    o = []
    for i, (x, y, rx, ry) in enumerate(((745, 924, 46, 10), (676, 948, 40, 10), (600, 966, 37, 9.5),
                                        (522, 980, 33, 8.5), (448, 988, 28, 7.5))):
        sd = f"M{n(x - rx)} {n(y)}C{n(x - rx)} {n(y - ry * 1.3)} {n(x + rx)} {n(y - ry * 1.4)} {n(x + rx)} {n(y)}C{n(x + rx)} {n(y + ry * 1.1)} {n(x - rx)} {n(y + ry * 1.2)} {n(x - rx)} {n(y)}Z"
        o.append(E(x + 3, y + ry * 0.9, rx * 1.02, ry * 0.6, DD))
        o.append(S(sd, W, 4, F(ell(x + rx * 0.45, y + ry * 0.7, rx * 0.95, ry * 0.85), DM)
                   + specks((x - rx * 0.6, y - ry * 0.5, x + rx * 0.2, y + ry * 0.2), 3, i + 40)))
        o.append(grass(x - rx - 6, y + 4, 0.7, i + 60))
    return "".join(o)


def mailbox():
    o = []
    o.append(grass(370, 936, 1.0, 81) + grass(392, 938, 0.8, 82))
    o.append(S("M374 934L376 856L388 856L390 934Z", W, 3.6, F("M383 850L394 850L394 940L383 940Z", DM)))
    o.append(P("M362 862L402 860L402 868L362 870Z", W, 2.8))
    box = "M338 862L338 836C338 818 354 810 382 810C410 810 424 818 424 836L424 862Z"
    o.append(S(box, W, 4.4, F("M398 806L430 806L430 866L402 866Z", DM) + L("M346 860L346 838C346 824 358 818 372 818", 2)
               + rivet(354, 852, 2) + rivet(410, 852, 2)))
    o.append(L("M338 862L424 862", 4.4))
    # letter poking out of the front
    o.append(g(P(rect(-14, -8, 14, 8), W, 2.4) + L("M-14 -8L0 1L14 -8", 1.6), "translate(346 842) rotate(-18)"))
    # raised flag
    o.append(P("M424 846L429 846L429 812L424 812Z", W, 2.4) + P("M429 812L446 812L446 824L429 824Z", DD, 2.4))
    o.append(bird(380, 812, 0.85, True))
    return g("".join(o), "translate(-84 0)")


def bush(x, y, s=1.0, seed=1):
    """low leafy bush sitting on the ground at (x, y)"""
    pts = [(x - 70 * s, y), (x - 76 * s, y - 26 * s), (x - 56 * s, y - 52 * s), (x - 24 * s, y - 66 * s),
           (x + 10 * s, y - 70 * s), (x + 42 * s, y - 58 * s), (x + 66 * s, y - 36 * s), (x + 72 * s, y - 6 * s),
           (x + 60 * s, y + 2 * s)]
    d = leafy(pts, 0.5, seed, True, (x, y - 10 * s))
    rnd = random.Random(seed)
    inner = F(ell(x + 30 * s, y - 4 * s, 70 * s, 40 * s), DM) + F(ell(x - 20 * s, y - 50 * s, 30 * s, 16 * s), W)
    inner += flicks((x - 60 * s, y - 60 * s, x + 60 * s, y), 16, seed + 2, (3, 6), (40, 80), 1.4)
    inner += sprigs("".join(leaf_cluster(x + rnd.uniform(-50, 50) * s, y + rnd.uniform(-48, -8) * s, 0.45,
                                         rnd.uniform(-140, -40), seed + j) for j in range(6)))
    berries = "".join(C(x + bx * s, y + by * s, 3.2, W, 1.8) + C(x + bx * s + 1, y + by * s + 1, 1.2, INK)
                      for bx, by in ((-30, -30), (-18, -40), (14, -48), (36, -26), (-44, -14)))
    return S(d, DL, 4.2, inner) + berries + grass(x - 66 * s, y + 4, 0.9, seed + 5) + grass(x + 58 * s, y + 4, 0.8, seed + 6)


def rope_ladder():
    """rope ladder dangling from the small platform"""
    o = []
    left = [(296 + 4 * math.sin(i / 3), 457 + i * 10) for i in range(27)]
    right = [(x + 30, y) for x, y in left]
    for i in range(2, 27, 3):
        (x0, y0), (x1, y1) = left[i], right[i]
        o.append(P(rect(x0 - 2, y0 - 3.5, x1 + 2, y0 + 3.5), W, 2.4) + F(rect(x0 + 18, y0 - 2, x1, y0 + 3), HA))
    o.append(L(poly_d(left), 2.6) + L(poly_d(right), 2.6))
    o.append(L(f"M{n(left[-1][0])} {n(left[-1][1])}l-3 10M{n(right[-1][0])} {n(right[-1][1])}l3 10", 2))
    return "".join(o)


def toadstools():
    o = []
    for (mx, my, sc, rot) in ((572, 912, 0.9, -6), (590, 916, 0.65, 10), (1126, 944, 0.7, 4)):
        o.append(g(S("M-5 0C-6 -8 -5 -16 -4 -22L4 -22C5 -16 6 -8 5 0Z", W, 2.6, F("M0 -24L8 -24L8 2L0 2Z", DL))
                   + S("M-18 -20C-18 -32 -8 -38 0 -38C8 -38 18 -32 18 -20C8 -17 -8 -17 -18 -20Z", W, 3.2,
                       F("M4 -40L22 -40L22 -16L8 -16Z", DM) + C(-8, -28, 3, W, 1.6) + C(4, -32, 2.4, W, 1.6))
                   + L("M-14 -20Q0 -16 14 -20", 1.4), f"translate({mx} {my}) rotate({rot}) scale({sc})"))
    return "".join(o)


def falling_leaves():
    o = []
    for x, y, a, s in ((1248, 432, 30, 0.9), (1330, 528, -150, 0.85), (560, 700, 70, 0.8), (420, 540, 10, 0.75),
                       (940, 760, -40, 0.8), (1150, 760, 120, 0.8), (1000, 330, 160, 0.7), (196, 560, -30, 0.8), (640, 470, 40, 0.7)):
        o.append(leaf(x, y, a, s * 1.35) + swoosh(x - 20, y - 18, -60, 16))
    return "".join(o)


def flock():
    return (flying_bird(1300, 376, 0.95, True) + flying_bird(1356, 322, 0.78, True)
            + flying_bird(1226, 424, 0.62, True))


DEFS = """<defs>
<filter id="ink" x="-3%" y="-3%" width="106%" height="106%">
<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<pattern id="dots-light" width="7" height="7" patternUnits="userSpaceOnUse"><rect width="7" height="7" fill="#fff"/><circle cx="3.5" cy="3.5" r="1.05" fill="#111"/></pattern>
<pattern id="dots-mid" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><circle cx="3" cy="3" r="1.55" fill="#111"/></pattern>
<pattern id="dots-dark" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="#fff"/><circle cx="2.5" cy="2.5" r="1.95" fill="#111"/></pattern>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><line x1="0" y1="0" x2="0" y2="6" stroke="#111" stroke-width="1.4"/></pattern>
<pattern id="crosshatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#fff"/><path d="M0 0V7M0 0H7" stroke="#111" stroke-width="1.3"/></pattern>
</defs>"""


def main():
    sil = tree_silhouette()
    st_back, st_front = stairs_layers()
    groups = [
        ("ground", ground()),
        ("canopy-back", canopy_back()),
        ("stairs-back", st_back),
        ("tree", tree(sil)),
        ("rocks", rocks()),
        ("root-fingers", root_fingers()),
        ("hanging-moss", hanging_moss()),
        ("canopy-front", canopy_front()),
        ("lantern-swag", lantern_swag()),
        ("birdhouse", birdhouse(722, 362, 1.0) + bird(728, 314, 0.8)),
        ("top-deck", top_deck()),
        ("knotted-rope", knotted_rope()),
        ("small-platform", small_platform()),
        ("rope-bridge", rope_bridge()),
        ("rope-ladder", rope_ladder()),
        ("tire-swing", tire_swing()),
        ("deck-braces", main_platform()),
        ("cabin", cabin()),
        ("roof-chimney-vane", roof()),
        ("pip-window", cabin_window()),
        ("main-deck", "".join(deck_front())),
        ("railing", railing_main()),
        ("crane-bucket", crane()),
        ("stairs-front", st_front),
        ("front-door", door()),
        ("ladder", ladder()),
        ("bolt", g(bolt_climb(), "translate(1055 709.5) scale(0.55)")),
        ("moss", g(moss_reading(), "translate(1250 950) scale(0.66)")),
        ("stepping-stones", stepping_stones()),
        ("bush", bush(160, 928, 0.95, 3)),
        ("toadstools", toadstools()),
        ("mailbox", mailbox()),
        ("falling-leaves", falling_leaves()),
        ("birds", flock()),
    ]
    body = "".join(f'<!-- {name} --><g id="{name}">{content}</g>' for name, content in groups)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 1000" width="1400" height="1000" role="img">'
           '<title>A cozy treehouse village built into a giant ancient tree: Pip waves from the cabin window, '
           'Bolt climbs the ladder, and Moss sits among the roots reading a tiny book</title>'
           + DEFS
           + '<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">' + body + "</g></svg>")
    with open(OUT, "w") as fh:
        fh.write(svg)
    print(f"wrote {os.path.normpath(OUT)} ({len(svg) / 1024:.0f} KB)")


main()
