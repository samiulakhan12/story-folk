#!/usr/bin/env python3
"""Builds ../assets/lineup.svg: the Storyfolk character line-up sheet.

Juniper, Moss, Nib, Captain Ribbit and Bolt stand side by side on a shared ground line,
each with a halftone shadow. All path data is hand-written; Python only places groups,
clip paths and repeated ink texture (rivets, flicks, tufts, braid lobes).

Dependencies: Python 3 standard library only.  Run:  python3 tools/generate-lineup.py
"""
import math
import os
import random
import re

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "lineup.svg")
INK = "#111"
W = "#fff"
DL, DM, DD, HA, CH = ("url(#dots-light)", "url(#dots-mid)", "url(#dots-dark)",
                      "url(#hatch)", "url(#crosshatch)")
GROUND = 650

_n = [0]


def nid():
    _n[0] += 1
    return f"c{_n[0]}"


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


# --- primitives --------------------------------------------------------------
def P(d, fill=W, sw=4.5, extra=""):
    st = f' stroke="{INK}" stroke-width="{n(sw)}"' if sw else ""
    return f'<path d="{d}" fill="{fill}"{st}{" " + extra if extra else ""}/>'


def L(d, sw=2.5, col=INK, extra=""):
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{n(sw)}"{" " + extra if extra else ""}/>'


def F(d, pat):
    return f'<path d="{d}" fill="{pat}"/>'


def S(d, fill=W, sw=4.5, inner=""):
    """filled shape, inner content clipped to it, outline stroked on top"""
    k = nid()
    return (f'<clipPath id="{k}"><path d="{d}"/></clipPath><path d="{d}" fill="{fill}"/>'
            f'<g clip-path="url(#{k})">{inner}</g>'
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(sw)}"/>')


def C(cx, cy, r, fill=W, sw=0):
    st = f' stroke="{INK}" stroke-width="{n(sw)}"' if sw else ""
    return f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}"{st}/>'


def E(cx, cy, rx, ry, fill=W, sw=0, rot=0):
    st = f' stroke="{INK}" stroke-width="{n(sw)}"' if sw else ""
    tr = f' transform="rotate({n(rot)} {n(cx)} {n(cy)})"' if rot else ""
    return f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{fill}"{st}{tr}/>'


def g(content, tr=None, extra=""):
    t = f' transform="{tr}"' if tr else ""
    return f"<g{t}{' ' + extra if extra else ''}>{content}</g>"


def circ(cx, cy, r):
    return f"M{n(cx - r)} {n(cy)}A{n(r)} {n(r)} 0 1 0 {n(cx + r)} {n(cy)}A{n(r)} {n(r)} 0 1 0 {n(cx - r)} {n(cy)}Z"


def ell(cx, cy, rx, ry):
    return f"M{n(cx - rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(cx + rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(cx - rx)} {n(cy)}Z"


def rect(x0, y0, x1, y1):
    return f"M{n(x0)} {n(y0)}L{n(x1)} {n(y0)}L{n(x1)} {n(y1)}L{n(x0)} {n(y1)}Z"


def rrect(x0, y0, x1, y1, r):
    return (f"M{n(x0 + r)} {n(y0)}L{n(x1 - r)} {n(y0)}Q{n(x1)} {n(y0)} {n(x1)} {n(y0 + r)}"
            f"L{n(x1)} {n(y1 - r)}Q{n(x1)} {n(y1)} {n(x1 - r)} {n(y1)}L{n(x0 + r)} {n(y1)}"
            f"Q{n(x0)} {n(y1)} {n(x0)} {n(y1 - r)}L{n(x0)} {n(y0 + r)}Q{n(x0)} {n(y0)} {n(x0 + r)} {n(y0)}Z")


def mir(d):
    """mirror a path (absolute M/L/C/Q/Z only) about x = 0"""
    out, cmd, idx = [], None, 0
    for t in re.findall(r"[MLCQZ]|-?\d*\.?\d+", d):
        if t.isalpha():
            cmd, idx = t, 0
            out.append(t)
            continue
        v = float(t)
        if idx % 2 == 0:
            v = -v
        idx += 1
        out.append(n(v))
    s = ""
    for t in out:
        s += t if t.isalpha() else (" " if s and not s[-1].isalpha() else "") + t
    return s


def T(x0, y0, cx, cy, x1, y1, w, fill=INK):
    """tapered hand-inked stroke: a lens along a quadratic curve, max thickness w"""
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


def sparkle(cx, cy, r, w=2.4):
    return "".join(ray(cx, cy, a, r * 0.35, r, w) for a in (0, 90, 180, 270))


def scallop(pts, bulge=0.32):
    """closed path through pts whose edges bulge outward (moss, fleece, fluff)"""
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


def drop(cx, cy, r, ang=0, fill=INK, sw=0):
    """teardrop whose tip points at angle ang (0 = up)"""
    d = (f"M0 {n(-2.3 * r)}C{n(0.45 * r)} {n(-1.5 * r)} {n(r)} {n(-0.8 * r)} {n(r)} 0"
         f"A{n(r)} {n(r)} 0 1 1 {n(-r)} 0C{n(-r)} {n(-0.8 * r)} {n(-0.45 * r)} {n(-1.5 * r)} 0 {n(-2.3 * r)}Z")
    st = f' stroke="{INK}" stroke-width="{n(sw)}"' if sw else ""
    return f'<path d="{d}" fill="{fill}"{st} transform="translate({n(cx)} {n(cy)}) rotate({n(ang)})"/>'


def flicks(box, count, seed, length=(4, 8), ang=(20, 70), w=1.5):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    out = []
    for _ in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        a = math.radians(rnd.uniform(*ang))
        ln = rnd.uniform(*length)
        ex, ey = x + math.cos(a) * ln, y - math.sin(a) * ln
        out.append(T(x, y, (x + ex) / 2 + 0.6, (y + ey) / 2, ex, ey, w))
    return "".join(out)


def specks(box, count, seed, r=(0.8, 1.6)):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    return "".join(C(rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(*r), INK) for _ in range(count))


def tuft(x, y, s=7, w=1.7):
    return L(f"M{n(x - s * 0.6)} {n(y - s)}Q{n(x - s * 0.2)} {n(y - s * 0.3)} {n(x)} {n(y)}"
             f"Q{n(x + s * 0.15)} {n(y - s * 0.5)} {n(x + s * 0.5)} {n(y - s * 1.1)}", w)


def tufts(box, count, seed, size=7, w=1.6):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    return "".join(tuft(rnd.uniform(x0, x1), rnd.uniform(y0, y1), size * rnd.uniform(0.7, 1.2), w)
                   for _ in range(count))


def grass(x, y, s=1.0, w=2.2):
    """a clump of three blades standing on the ground"""
    return (T(x - 2 * s, y, x - 7 * s, y - 8 * s, x - 11 * s, y - 15 * s, 1.6 * s)
            + T(x, y, x + 1 * s, y - 11 * s, x - 1 * s, y - 21 * s, 1.8 * s)
            + T(x + 2 * s, y, x + 7 * s, y - 7 * s, x + 12 * s, y - 12 * s, 1.5 * s))


def stitches(d, sw=1.4):
    return L(d, sw, extra='stroke-dasharray="2.6 3.2"')


def rivet(x, y, r=2.6):
    return C(x, y, r, W, 1.8) + C(x - r * 0.3, y - r * 0.3, r * 0.32, INK)


def tube(pts, w0, w1):
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
    pts2 = left + right[::-1]
    return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts2) + "Z"


def bez(t, p0, p1, p2, p3):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def ground_marks(x0, x1, seed, y=2):
    """broken hand-inked ground strokes either side of a shadow"""
    rnd = random.Random(seed)
    out = []
    for (a, b) in ((x0 - 70, x0 - 8), (x1 + 8, x1 + 70)):
        x = a
        while x < b:
            ln = rnd.uniform(14, 30)
            e = min(b, x + ln)
            out.append(T(x, y + rnd.uniform(-0.6, 0.6), (x + e) / 2, y + rnd.uniform(-1, 1), e, y, 1.5))
            x = e + rnd.uniform(5, 12)
    return "".join(out)


# =============================================================================
# JUNIPER: aviator cap, braids, spyglass to her eye, hand on hip, map satchel
# local origin = ground point between her feet; about 430 tall
# =============================================================================
def braid(pts, w=8.6):
    path = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        steps = max(1, int(math.hypot(x1 - x0, y1 - y0) / 8.5))
        for k in range(steps):
            t = k / steps
            path.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    path.append(pts[-1])
    out = [L("M" + "L".join(f"{n(x)} {n(y)}" for x, y in path), w * 1.7 + 4.6)]
    for i in range(len(path) - 1):
        x, y = path[i]
        dx, dy = path[i + 1][0] - x, path[i + 1][1] - y
        ln = math.hypot(dx, dy) or 1
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux
        side = 1 if i % 2 else -1
        cx, cy = x + nx * side * w * 0.32 + ux * 4, y + ny * side * w * 0.32 + uy * 4
        a = math.degrees(math.atan2(dy, dx))
        out.append(E(cx, cy, w * 0.92, w * 0.58, INK, 0, a + side * 38))
        hx, hy = cx + nx * side * w * 0.15, cy + ny * side * w * 0.15
        out.append(T(hx - ux * 4 - nx * side * 2, hy - uy * 4 - ny * side * 2, hx, hy,
                     hx + ux * 3 + nx * side * w * 0.5, hy + uy * 3 + ny * side * w * 0.5, 1.4, W))
    (xa, ya), (xb, yb) = path[-2], path[-1]
    a = math.degrees(math.atan2(yb - ya, xb - xa))
    out.append(g(P("M-4 -7L5 -7L5 7L-4 7Z", W, 2.6) + L("M-1 -7L0 7M2.5 -7L3 7", 1.2)
                 + P("M5 -6C10 -9 16 -10 22 -6C17 -5 16 -3 22 0C16 2 17 5 22 7C15 10 9 9 5 6Z", INK, 0)
                 + L("M1 7Q-2 14 -8 16M2 7Q6 15 3 19", 1.6),
                 f"translate({n(xb)} {n(yb)}) rotate({n(a)})"))
    return "".join(out)


def juniper():
    o = [E(6, 2, 100, 10, DM), ground_marks(-94, 106, 11)]
    o.append(grass(-108, 1, 1.0) + grass(118, 1, 0.8))

    # tall striped socks
    for s in (-1, 1):
        sock = "M-56 -82L-22 -82L-24 -30L-53 -30Z" if s < 0 else mir("M-56 -82L-22 -82L-24 -30L-53 -30Z")
        stripes = "".join(F(rect(-70, y, 70, y + 7), DD) for y in (-74, -58, -42))
        shade = F(rect(-31, -84, -20, -28) if s < 0 else rect(44, -84, 60, -28), DL)
        o.append(S(sock, W, 3.8, shade + stripes + L(f"M{-52 * s} -66L{-24 * s} -66", 1.2)))
    # sneakers, toes turned out
    shoe_l = ("M-20 -40C-22 -48 -46 -50 -56 -44C-68 -40 -84 -32 -88 -20C-90 -12 -88 -4 -80 -2"
              "L-22 -2C-14 -2 -12 -10 -14 -18Z")
    sole_l = "M-91 -13L-14 -13C-12 -6 -14 0 -21 0L-82 0C-89 0 -92 -6 -91 -13Z"
    for s in (-1, 1):
        sh = shoe_l if s < 0 else mir(shoe_l)
        so = sole_l if s < 0 else mir(sole_l)
        shade = (F("M-34 -54L-10 -54L-10 0L-30 0C-26 -14 -26 -36 -34 -54Z", HA) if s < 0
                 else F("M60 -50L96 -50L96 0L60 0C70 -12 70 -36 60 -50Z", HA))
        o.append(S(sh, W, 4.2, shade
                   + L(f"M{-72 * s} -6C{-78 * s} -18 {-72 * s} -30 {-60 * s} -36", 2.2)
                   + L(f"M{-48 * s} -44L{-30 * s} -30M{-32 * s} -44L{-46 * s} -30"
                       f"M{-48 * s} -36L{-30 * s} -24M{-30 * s} -36L{-44 * s} -24", 1.8)))
        o.append(S(so, W, 3.6, F(rect(-100, -6, 100, 2), DM)
                   + "".join(L(f"M{n(x * s)} -12L{n(x * s - 3 * s)} -7", 1.3) for x in range(-84, -18, 8))))
        o.append(P(f"M{-44 * s} -48C{-44 * s} -56 {-28 * s} -56 {-26 * s} -46Z", W, 2.6))

    # patched trousers with rolled cuffs
    trousers = ("M-40 -190L40 -190C46 -160 52 -124 64 -90L18 -88C14 -104 8 -116 0 -124"
                "C-8 -116 -14 -104 -18 -88L-64 -90C-52 -124 -46 -160 -40 -190Z")
    o.append(S(trousers, W, 4.6,
               F("M10 -194L50 -194C54 -158 62 -122 74 -86L22 -86C20 -100 14 -114 6 -126Z", DM)
               + F("M-8 -132L8 -132L0 -112Z", DD)
               + L("M-34 -176Q-26 -168 -28 -156", 1.8) + L("M28 -176Q34 -170 32 -160", 1.8)
               + L("M-50 -116Q-40 -110 -36 -100", 1.8) + L("M-42 -128Q-34 -124 -30 -116", 1.6)
               + L("M44 -118Q38 -110 36 -100", 1.8)
               + S("M-54 -132L-28 -130L-30 -104L-56 -106Z", DL, 2.4,
                   stitches("M-51 -128L-31 -126.5L-32.5 -107.5L-52.5 -109Z", 1.3))
               + S("M24 -160L46 -164L49 -140L27 -137Z", CH, 2.4,
                   stitches("M27 -157L43 -160L45.5 -142.5L29.5 -140Z", 1.3))
               + L("M-38 -186Q-30 -176 -18 -176", 1.8) + L("M38 -186Q30 -176 18 -176", 1.8)))
    cuff_l = "M-68 -100L-14 -97L-13 -80L-68 -82Z"
    o.append(S(cuff_l, W, 3.8, F(rect(-28, -104, -10, -76), DL) + stitches("M-64 -91L-17 -88.5")))
    o.append(S(mir(cuff_l), W, 3.8, F(rect(44, -104, 72, -76), DM) + stitches("M64 -91L17 -88.5")))

    # shirt
    shirt = ("M-32 -292C-46 -286 -53 -266 -53 -244C-53 -220 -49 -202 -45 -188L45 -188"
             "C49 -202 53 -220 53 -244C53 -266 46 -286 32 -292Z")
    o.append(S(shirt, W, 4.6,
               F("M22 -296C40 -282 46 -262 46 -238C46 -216 42 -200 38 -188L62 -188L62 -296Z", DM)
               + F("M-60 -206L60 -206L60 -186L-60 -186Z", HA)
               + L("M3 -284L3 -194", 2.4) + C(9, -266, 2.3, INK) + C(9, -244, 2.3, INK) + C(9, -222, 2.3, INK)
               + S("M-40 -262L-14 -262L-15 -238L-39 -238Z", W, 2.4, stitches("M-37 -253L-17 -253"))
               + L("M-40 -262L-14 -262L-16 -252L-38 -252Z", 2.2)
               + L("M-30 -222Q-22 -216 -12 -218", 1.6) + L("M24 -236Q30 -226 28 -214", 1.6)))
    collar = "M-28 -296L-2 -268L1 -290Z"
    o.append(P(collar, W, 2.8) + P(mir(collar), W, 2.8))

    # satchel: strap, rolled maps, bag
    o.append(S("M-42 -286L-29 -295L56 -206L43 -197Z", DL, 2.8, stitches("M-35 -291L50 -202")))
    for (x0, y0, x1, y1, rr, a2) in ((60, -204, 76, -252, 7.4, 0), (80, -204, 112, -242, 6.8, 1),
                                     (46, -204, 46, -236, 6.2, 2)):
        o.append(S(tube([(x0, y0), (x1, y1)], rr * 2, rr * 2), W, 2.8,
                   F(tube([(x0 + 4, y0), (x1 + 4, y1)], rr, rr), DL)
                   + L(f"M{n(x0 + (x1 - x0) * 0.3)} {n(y0 + (y1 - y0) * 0.3)}L{n(x0 + (x1 - x0) * 0.7)} "
                       f"{n(y0 + (y1 - y0) * 0.7)}", 1.3, extra='stroke-dasharray="3 3"')))
        a = math.degrees(math.atan2(y1 - y0, x1 - x0))
        o.append(g(E(0, 0, 2.8, rr, W, 2.6) + L(f"M0 {n(-rr * 0.45)}Q2 0 0 {n(rr * 0.45)}", 1.3),
                   f"translate({n(x1)} {n(y1)}) rotate({n(a)})"))
    o.append(L("M58 -224Q70 -222 74 -232", 1.6))  # string round a map roll
    bag = "M38 -210C36 -184 38 -164 44 -150L102 -150C108 -162 108 -188 104 -210Z"
    o.append(S(bag, W, 4.4, F("M36 -172C56 -166 86 -166 110 -174L110 -146L36 -146Z", DM)
               + F("M90 -212L112 -212L112 -146L96 -146C100 -166 98 -192 90 -212Z", HA)
               + stitches("M44 -158L100 -158")))
    flap = "M33 -214L108 -214C110 -197 99 -186 70 -184C45 -186 33 -197 33 -214Z"
    o.append(S(flap, DL, 3.8, P("M30 -240C50 -224 80 -222 112 -232L112 -250L30 -250Z", W, 0)
               + stitches("M38 -208Q70 -186 103 -208")))
    o.append(P("M64 -198L77 -198L77 -180L64 -180Z", W, 2.4) + L("M70.5 -194L70.5 -184", 2))

    # belt
    o.append(P("M-47 -197L47 -197L48 -182L-48 -182Z", INK, 2))
    o.append(P("M-10 -200L10 -200L10 -179L-10 -179Z", W, 2.6) + L("M0 -197L0 -182", 1.8))
    o.append(P("M-34 -198L-28 -198L-28 -181L-34 -181Z", W, 1.6))

    # free arm (her right, viewer left) hangs down holding an unrolled map
    o.append(S("M-34 -296C-56 -300 -72 -282 -75 -254L-48 -250C-46 -262 -44 -270 -42 -278Z", W, 4.4,
               F("M-82 -276L-62 -276L-60 -246L-82 -246Z", DL) + L("M-60 -286Q-56 -278 -58 -268", 1.6)))
    o.append(S("M-76 -252L-49 -250C-51 -236 -55 -222 -57 -210L-79 -211C-80 -226 -79 -240 -76 -252Z", W, 4.2,
               F(rect(-62, -256, -44, -206), DL)))
    o.append(S(rrect(-81, -259, -45, -244, 5), W, 3.2, F(rect(-58, -262, -40, -240), DM)
               + stitches("M-78 -251.5L-48 -251.5", 1.2)))
    mapd = "M-102 -212L-32 -214C-30 -190 -31 -166 -34 -148L-100 -146C-103 -168 -104 -190 -102 -212Z"
    o.append(S(mapd, W, 3.8,
               F("M-58 -220L-24 -220L-24 -140L-52 -140C-50 -166 -52 -194 -58 -220Z", DL)
               + L("M-67 -213L-66 -147", 1.4, extra='stroke-dasharray="5 4"')
               + L("M-92 -198C-80 -194 -84 -180 -72 -176C-60 -172 -62 -162 -50 -160", 1.8,
                   extra='stroke-dasharray="3.5 3.5"')
               + L("M-53 -165L-45 -157M-45 -165L-53 -157", 2.4)
               + P("M-96 -164L-89 -177L-82 -164Z", W, 1.8) + P("M-86 -164L-79 -180L-72 -164Z", W, 1.8)
               + L("M-79 -180L-76 -173", 1.4)
               + ray(-46, -198, -90, 0, 9, 1.6) + ray(-46, -198, 90, 0, 6, 1.4)
               + ray(-46, -198, 0, 0, 6, 1.4) + ray(-46, -198, 180, 0, 6, 1.4)
               + L("M-96 -204Q-90 -206 -84 -204", 1.3) + L("M-40 -180Q-36 -176 -40 -172", 1.3)))
    o.append(P(tube([(-101, -146), (-33, -149)], 13, 12), W, 3.4) + E(-101, -146, 3.4, 6.6, W, 2.6)
             + L("M-101 -149Q-98.5 -146 -101 -143", 1.2) + F(tube([(-80, -143), (-34, -145)], 6, 5), DL))
    fist_l = "M-82 -218C-82 -230 -55 -232 -53 -218C-51 -204 -59 -197 -68 -197C-77 -197 -84 -205 -82 -218Z"
    o.append(S(fist_l, W, 3.8, F("M-60 -234L-46 -234L-46 -194L-64 -194C-58 -202 -56 -220 -60 -234Z", DL)
               + L("M-78 -214Q-73 -211 -69 -214M-78 -206Q-73 -203 -69 -206", 1.5)))
    # spyglass arm (her left) upper sleeve, raised elbow
    o.append(S("M28 -298C50 -314 82 -320 102 -314L108 -290C86 -290 64 -280 44 -266Z", W, 4.4,
               F("M56 -330L120 -330L120 -280L70 -284C66 -300 62 -316 56 -330Z", DM)
               + L("M62 -300Q70 -294 70 -286", 1.6)))

    # braids hanging over the shoulders
    o.append(braid([(-52, -308), (-57, -282), (-56, -256), (-50, -232)]))
    o.append(braid([(58, -308), (63, -282), (62, -256), (56, -234)]))

    # head
    o.append(S(circ(4, -345, 58), W, 4.8, F(circ(4, -345, 58), DL) + P(circ(-3, -351, 58), W, 0)))
    for x in (-32, -18, -4, 10):  # fringe peeking under the fleece trim
        o.append(P(f"M{x - 7} -364Q{x - 3} -350 {x + 4} -346Q{x + 2} -356 {x + 7} -364Z", INK, 0))
    cap = ("M-63 -350C-68 -392 -36 -426 4 -426C44 -426 76 -394 71 -352"
           "C52 -366 28 -370 4 -370C-20 -370 -45 -366 -63 -350Z")
    o.append(S(cap, DL, 5,
               P("M-40 -416C-26 -424 -6 -426 8 -424C-8 -410 -22 -394 -30 -376L-56 -364Z", W, 0)
               + F("M36 -428C62 -416 76 -394 72 -352L52 -364C56 -390 50 -410 36 -428Z", HA)
               + stitches("M6 -424C2 -408 0 -390 2 -372") + stitches("M-34 -410C-44 -396 -50 -382 -54 -368")
               + stitches("M44 -412C52 -400 56 -386 58 -370")
               + L("M-26 -400Q-20 -412 -8 -418", 1.8, W)))
    o.append(S(circ(6, -426, 6.5), W, 3, F(circ(9, -424, 5), DM)))
    trim = scallop([(-62, -346), (-40, -356), (-18, -362), (4, -365), (26, -363), (48, -357), (70, -347),
                    (72, -360), (50, -371), (27, -377), (4, -379), (-19, -377), (-42, -370), (-64, -358)], 0.22)
    o.append(S(trim, W, 3, F("M30 -390L80 -390L80 -340L34 -340Z", DL) + flicks((-56, -376, 64, -356), 9, 5, (2, 4), (40, 80), 1)))
    flap_l = "M-65 -358C-76 -336 -74 -304 -57 -293C-45 -289 -38 -300 -41 -352Z"
    o.append(S(flap_l, DL, 4.4, P("M-80 -360L-58 -360C-66 -340 -68 -318 -64 -298L-80 -298Z", W, 0)
               + stitches("M-61 -348C-69 -330 -68 -310 -58 -300")))
    flap_r = "M73 -360C82 -338 80 -306 63 -295C51 -291 45 -302 49 -354Z"
    o.append(S(flap_r, HA, 4.4, stitches("M69 -350C76 -332 74 -312 64 -302")))
    o.append(L("M-52 -294Q-50 -280 -40 -274", 3.2) + P("M-44 -280L-36 -277L-38 -270L-46 -273Z", W, 2))
    # features: open left eye, brow raised over the eyepiece, grin, blush
    o.append(E(-20, -335, 7.6, 10.2, INK) + C(-22.8, -339, 2.9, W) + C(-16.8, -330.5, 1.2, W))
    o.append(T(-33, -353, -22, -361, -10, -355, 2.7))
    o.append(T(14, -360, 25, -368, 37, -363, 2.5))
    o.append(L("M3 -327Q9 -322 4 -316", 2.6))
    o.append(P("M-16 -307Q2 -284 22 -308Q3 -300 -16 -307Z", INK, 0)
             + P("M-6 -296Q2 -290 11 -297Q4 -300 -6 -296Z", DM, 0))
    o.append(E(-39, -314, 10, 6, DL) + E(42, -316, 8, 5, DL))
    o.append(T(-18, -310, -20, -307, -20, -303, 1.6) + T(22, -310, 25, -308, 25, -304, 1.6))

    # spyglass forearm (bare), rolled cuff at the raised elbow
    o.append(S("M97 -292C84 -310 70 -328 55 -344L69 -356C82 -340 98 -322 112 -306Z", W, 4.2,
               F("M70 -362L90 -362L118 -308L102 -296Z", DL)))
    o.append(g(S("M-14 -7C-14 -10 14 -10 14 -7L14 7C14 10 -14 10 -14 7Z", W, 3.2,
                 F(rect(3, -12, 18, 12), DM) + stitches("M-12 0L12 0", 1.2)),
               "translate(104 -300) rotate(72)"))
    # the spyglass, eyepiece cupped to her left eye, tilted up and out
    sg = (S(rrect(-6, -12, 11, 12, 4), DD, 3.2, L("M-2 -12L-2 12", 1.4, W))
          + S(rect(10, -10.5, 46, 10.5), W, 3.4, F(rect(10, 3, 46, 12), DM) + L("M14 -6L42 -6", 1.6, W)
              + L("M22 -10L22 10M34 -10L34 10", 1.2))
          + P(rect(44, -13, 52, 13), DD, 3)
          + S(rect(52, -12.5, 92, 12.5), W, 3.4, F(rect(52, 4, 92, 14), DM) + L("M56 -7L88 -7", 1.6, W)
              + rivet(62, 0, 2.2) + rivet(84, 0, 2.2))
          + P(rect(90, -15.5, 98, 15.5), DD, 3)
          + S("M98 -15L136 -18L136 18L98 15Z", W, 3.6, F("M98 4L136 4L136 20L98 18Z", DM)
              + L("M102 -9L132 -11", 1.8, W) + L("M110 -14L110 14M124 -16L124 16", 1.2))
          + P(rect(134, -20, 142, 20), DD, 3)
          + E(143, 0, 3.8, 19, DL, 3))
    o.append(g(sg, "translate(28 -338) rotate(-32)"))
    o.append(sparkle(162, -436, 13, 2.4) + T(168, -404, 176, -400, 184, -404, 1.6))
    fist = "M47 -362C49 -374 70 -377 75 -364C79 -351 72 -340 60 -340C49 -340 44 -351 47 -362Z"
    o.append(S(fist, W, 4, F("M64 -380L84 -380L84 -336L62 -336C70 -346 70 -364 64 -380Z", DL)
               + L("M50 -358Q56 -355 61 -360M49 -350Q55 -347 61 -352", 1.6)))
    o.append(T(58, -371, 52, -374, 47, -369, 2.4))  # thumb over the barrel
    return "".join(o)


# =============================================================================
# MOSS: standing forest giant, leaf on a stem, mushrooms, rope sash, acorn charm
# local origin = ground point under his middle; about 620 tall including the leaf
# =============================================================================
def moss():
    o = [E(0, 2, 222, 16, DM), ground_marks(-222, 222, 21)]
    o.append(grass(-238, 1, 1.2) + grass(-206, 2, 0.8) + grass(236, 1, 1.1))
    o.append(E(-252, -3, 8, 5, W, 2.4) + F(ell(-250, -2, 5, 3), HA) + E(248, -4, 6, 4, W, 2.2))

    body = ("M-150 -62C-178 -160 -182 -330 -150 -430C-122 -510 -62 -555 2 -555C68 -555 128 -510 154 -430"
            "C184 -330 180 -160 152 -62C100 -44 -100 -44 -150 -62Z")
    capm = scallop([(-210, -610), (-210, -408), (-172, -418), (-146, -436), (-120, -455), (-92, -469),
                    (-62, -479), (-32, -486), (0, -489), (32, -487), (62, -481), (92, -471), (120, -457),
                    (146, -439), (172, -420), (210, -410), (210, -610)], 0.22)
    lpatch = scallop([(-182, -360), (-150, -372), (-124, -350), (-128, -312), (-150, -296), (-182, -304)], 0.3)
    rpatch = scallop([(186, -200), (152, -186), (128, -150), (138, -112), (168, -104), (190, -130)], 0.3)
    belly = scallop([(-70, -160), (-40, -170), (-10, -164), (-2, -140), (-26, -126), (-62, -132)], 0.28)
    hip = scallop([(-150, -170), (-120, -176), (-104, -150), (-116, -120), (-146, -118)], 0.3)
    chest = scallop([(40, -312), (70, -322), (96, -306), (92, -278), (62, -270), (38, -284)], 0.3)
    side = scallop([(-120, -280), (-92, -290), (-74, -268), (-86, -244), (-114, -240)], 0.3)
    low = scallop([(60, -96), (92, -104), (112, -88), (100, -70), (66, -70)], 0.3)
    lichen = "".join(C(x, y, r, W, 1.6) + C(x, y, r * 0.35, INK) for x, y, r in
                     ((-60, -330, 4), (-46, -322, 2.6), (20, -180, 3.4), (110, -240, 3), (-20, -260, 2.6),
                      (-130, -140, 3), (140, -300, 2.8), (-90, -110, 2.4)))
    stones = (E(-104, -200, 12, 8, W, 2.4) + F(ell(-100, -197, 8.5, 5.2), HA)
              + E(54, -132, 13, 8.5, W, 2.4) + F(ell(58, -129, 9, 5.5), HA)
              + E(96, -300, 9, 6.5, W, 2.2) + E(118, -170, 8, 6, W, 2.2) + F(ell(121, -168, 5.5, 4), HA)
              + E(-30, -96, 9, 6, W, 2.2) + E(-136, -250, 6, 4.5, W, 2) + E(30, -330, 6, 4, W, 2))
    cracks = (L("M-128 -232L-114 -220L-118 -204M-114 -220L-100 -222", 2)
              + L("M70 -116L82 -102L78 -86M82 -102L94 -98", 2)
              + L("M128 -270L116 -254L122 -238", 2) + L("M-50 -110L-38 -102L-42 -90", 1.8)
              + L("M10 -232L22 -222L18 -210", 1.8))
    inner = (F(capm, DL) + F(lpatch, DL) + F(rpatch, DL) + F(belly, DL) + F(hip, DL)
             + F("M110 -540C156 -480 178 -370 174 -240C172 -150 164 -90 148 -40L240 -40L240 -540Z", DM)
             + F("M146 -470C174 -380 178 -240 166 -50L240 -50L240 -470Z", DD)
             + F("M-200 -92C-100 -66 100 -66 200 -92L200 0L-200 0Z", DM)
             + F("M-178 -230C-176 -150 -166 -100 -146 -64L-190 -64Z", DL)
             + F("M40 -560C110 -480 150 -360 150 -240C150 -150 140 -90 120 -50L240 -50L240 -560Z", DL)
             + F(chest, DL) + F(side, DL) + F(low, DL)
             + L(capm, 2.4) + L(lpatch, 2.2) + L(rpatch, 2.2) + L(belly, 2) + L(hip, 2)
             + L(chest, 2) + L(side, 2) + L(low, 2) + lichen
             + tufts((40, -318, 94, -276), 4, 15, 5, 1.4) + tufts((-118, -286, -78, -246), 3, 16, 5, 1.4)
             + stones + cracks
             + tufts((-140, -540, 136, -496), 30, 7, 7, 1.6)
             + tufts((-176, -364, -132, -306), 5, 8, 5, 1.4) + tufts((136, -196, 180, -112), 5, 9, 5, 1.4)
             + tufts((-64, -166, -10, -134), 3, 14, 5, 1.4)
             + specks((-130, -540, 130, -500), 34, 10, (0.8, 1.8))
             + flicks((-150, -420, 150, -90), 70, 12, (4, 9), (25, 70), 1.5)
             + specks((-150, -380, 150, -100), 40, 17, (0.8, 1.5)))
    o.append(S(body, W, 5.6, inner))

    # sprouts and a tiny flower on the crown
    def sprout(x, y, s=1.0, lean=0):
        return g(L("M0 0Q-1 -9 0 -18", 2.6)
                 + S("M0 -17C-5 -25 -15 -27 -21 -22C-15 -15 -6 -14 0 -17Z", W, 2.6, F(rect(-22, -20, 0, -12), DL))
                 + S("M0 -18C4 -27 14 -30 20 -26C15 -18 6 -16 0 -18Z", W, 2.6, F(rect(0, -22, 20, -14), DM)),
                 f"translate({n(x)} {n(y)}) rotate({n(lean)}) scale({n(s)})")
    o.append(sprout(-71, -530, 1.1, -14) + sprout(-120, -480, 0.85, -36) + sprout(50, -543, 0.9, 10))
    flower = g(L("M0 0Q2 -8 0 -16", 2.2) + "".join(E(math.cos(math.radians(a)) * 6, -16 + math.sin(math.radians(a)) * 6,
                                                       5, 3.4, W, 2, a) for a in range(0, 360, 72))
               + C(0, -16, 3, INK), "translate(-22 -553) rotate(-6)")
    o.append(flower)
    o.append(tufts((-110, -552, 100, -540), 7, 13, 8, 2))

    # mushrooms on his left shoulder (viewer right)
    for (mx, my, sc, rot) in ((94, -512, 1.25, 12), (122, -484, 1.0, 30), (142, -452, 0.72, 44)):
        o.append(g(S("M-6 0C-7 -9 -6 -18 -5 -24L5 -24C6 -18 7 -9 6 0Z", W, 2.8, F(rect(0, -26, 9, 2), DL))
                   + S("M-20 -22C-20 -35 -9 -42 0 -42C9 -42 20 -35 20 -22C9 -18 -9 -18 -20 -22Z", W, 3.6,
                       F("M4 -44L24 -44L24 -18L8 -18Z", DM) + C(-9, -31, 3.4, W, 1.6) + C(4, -35, 2.6, W, 1.6)
                       + C(12, -26, 2.2, W, 1.4))
                   + L("M-15 -22Q0 -18 15 -22", 1.4) + L("M-4 -14L-4 -6M2 -16L2 -8", 1.1),
                   f"translate({n(mx)} {n(my)}) rotate({n(rot)}) scale({n(sc)})"))

    # rope sash with acorn charm (clipped to the body)
    p0, p1, p2, p3 = (-190, -386), (-104, -300), (28, -238), (196, -222)
    sash = "M-196 -398C-108 -312 24 -250 198 -234L198 -210C30 -226 -98 -288 -184 -374Z"
    twist = ""
    for i in range(40):
        x, y = bez(i / 39, p0, p1, p2, p3)
        twist += L(f"M{n(x - 5)} {n(y - 10)}Q{n(x + 1)} {n(y - 2)} {n(x + 4)} {n(y + 10)}", 2.1)
    k = nid()
    o.append(f'<clipPath id="{k}"><path d="{body}"/></clipPath>')
    o.append(f'<g clip-path="url(#{k})">'
             + S(sash, W, 3.8, F("M-200 -372C-100 -284 30 -222 200 -208L200 -190L-200 -190Z", DM) + twist) + "</g>")
    cx, cy = bez(0.45, p0, p1, p2, p3)
    o.append(L(f"M{n(cx)} {n(cy + 6)}Q{n(cx - 7)} {n(cy + 18)} {n(cx)} {n(cy + 26)}"
               f"M{n(cx)} {n(cy + 6)}Q{n(cx + 7)} {n(cy + 18)} {n(cx)} {n(cy + 26)}", 2.2))
    ay = cy + 26
    o.append(S(f"M{n(cx - 13)} {n(ay + 8)}C{n(cx - 13)} {n(ay + 26)} {n(cx - 5)} {n(ay + 36)} {n(cx)} {n(ay + 40)}"
               f"C{n(cx + 5)} {n(ay + 36)} {n(cx + 13)} {n(ay + 26)} {n(cx + 13)} {n(ay + 8)}Z", W, 3.2,
               F(rect(cx + 1, ay, cx + 16, ay + 42), DL) + T(cx - 8, ay + 14, cx - 9, ay + 22, cx - 5, ay + 30, 2)))
    o.append(P(f"M{n(cx - 16)} {n(ay + 9)}Q{n(cx)} {n(ay - 12)} {n(cx + 16)} {n(ay + 9)}Z", CH, 3.2)
             + L(f"M{n(cx)} {n(ay - 2)}L{n(cx + 2)} {n(ay - 8)}", 2.8))

    # face
    o.append(P("M-72 -458Q-66 -470 -57 -464Q-50 -472 -42 -465Q-36 -459 -42 -455Q-57 -452 -72 -456Z", DM, 2.4))
    o.append(P("M16 -458Q22 -470 31 -464Q38 -472 46 -465Q52 -459 46 -455Q31 -452 16 -456Z", DM, 2.4))
    o.append(E(-54, -436, 6, 8, INK) + E(32, -436, 6, 8, INK) + C(-55.8, -438.8, 2, W) + C(30.2, -438.8, 2, W))
    o.append(S("M-14 -432C-24 -430 -26 -413 -16 -408C-6 -403 7 -409 7 -418C7 -428 -4 -434 -14 -432Z", W, 3.4,
               F("M-6 -436L12 -436L12 -400L-12 -400C-2 -408 0 -424 -6 -436Z", HA)))
    o.append(L("M-86 -394Q-10 -342 70 -394", 4.2))
    o.append(T(-92, -401, -90, -394, -84, -389, 2.3) + T(75, -401, 72, -394, 73, -387, 2.3))
    o.append(E(-94, -410, 16, 9, DL) + E(80, -410, 15, 9, DL))
    o.append(T(-66, -446, -60, -444, -56, -446, 1.2))

    # stubby arms hanging in front of his sides, mitten hands with thumbs
    larm = ("M-146 -378C-182 -366 -200 -324 -202 -280C-203 -256 -196 -240 -184 -236L-152 -240"
            "C-148 -268 -146 -300 -138 -330C-134 -346 -124 -358 -112 -366C-100 -374 -126 -394 -146 -378Z")
    rarm = mir(larm)
    hand_l = "M-204 -262C-212 -238 -200 -214 -180 -212C-162 -210 -150 -222 -152 -240C-154 -256 -168 -266 -186 -266Z"
    thumb_l = "M-160 -250C-150 -256 -140 -250 -142 -240C-144 -232 -152 -230 -158 -234Z"
    patch = scallop([(-184, -336), (-166, -344), (-152, -324), (-164, -306), (-182, -312)], 0.3)
    o.append(S(larm, W, 5, F("M-210 -390L-130 -390C-160 -360 -176 -320 -180 -280L-210 -280Z", DL)
               + F("M-160 -380C-150 -340 -150 -290 -156 -236L-130 -236L-130 -380Z", DM)
               + F(patch, DL) + L(patch, 1.8)
               + flicks((-196, -360, -156, -270), 8, 31, (3, 6), (30, 70), 1.3)))
    o.append(S(thumb_l, W, 3.6, F(rect(-152, -258, -136, -226), DM)))
    o.append(S(hand_l, W, 4.6, F("M-166 -270L-146 -270L-146 -206L-176 -206C-162 -216 -158 -244 -166 -270Z", DM)
               + L("M-196 -228Q-192 -218 -184 -216M-184 -232Q-180 -222 -172 -220", 2)))
    o.append(S(rarm, W, 5, F("M130 -390L210 -390L210 -236L150 -236C152 -290 148 -340 130 -390Z", DM)
               + F("M178 -390L210 -390L210 -236L192 -236C198 -290 194 -340 178 -390Z", DD)
               + E(178, -330, 8, 6, W, 2) + F(ell(181, -328, 5, 4), HA)
               + flicks((158, -360, 196, -270), 8, 32, (3, 6), (30, 70), 1.3)))
    o.append(S(mir(thumb_l), W, 3.6, F(rect(136, -258, 160, -226), DM)))
    o.append(S(mir(hand_l), W, 4.6, F("M166 -270L214 -270L214 -206L170 -206C182 -220 182 -246 166 -270Z", DM)
               + L("M196 -228Q192 -218 184 -216M184 -232Q180 -222 172 -220", 2)))
    o.append(tufts((-180, -378, -140, -366), 3, 41, 6, 1.5) + tufts((140, -378, 180, -366), 3, 42, 6, 1.5))

    # boulder feet with pebble toes
    foot_l = "M-152 -56C-166 -34 -154 -2 -120 0L-46 0C-24 -2 -20 -32 -34 -52C-58 -72 -128 -72 -152 -56Z"
    for s in (-1, 1):
        fd = foot_l if s < 0 else mir(foot_l)
        shade = (F("M-60 -72C-30 -56 -24 -20 -44 4L0 4L0 -72Z", DM) if s < 0
                 else F("M110 -72C150 -56 160 -20 130 4L170 4L170 -72Z", DM))
        o.append(S(fd, W, 5, shade + F(rect(-170, -14, 170, 4), HA)
                   + flicks((-150 if s < 0 else 40, -60, -40 if s < 0 else 150, -20), 6, 51 + s, (3, 6), (30, 70), 1.4)))
        for tx in (-134, -108, -82):
            tx = tx if s < 0 else -tx
            o.append(S(ell(tx, -14, 12, 9), W, 3, F(ell(tx + 4, -12, 9, 6.5), DL)))
    o.append(tufts((-140, -72, -60, -62), 4, 61, 6, 1.6) + tufts((60, -72, 140, -62), 4, 62, 6, 1.6))

    # stem and the big leaf, growing out of the crown
    o.append(P("M-2 -546C-4 -568 -6 -588 -14 -604L-6 -609C2 -592 8 -570 10 -546Z", W, 3.4))
    o.append(tuft(-6, -546, 9, 2) + tuft(10, -548, 8, 2))
    leaf = "M-10 -604C-40 -640 -130 -646 -180 -604C-130 -584 -50 -584 -10 -604Z"
    o.append(S(leaf, W, 4.6, F("M-190 -604C-130 -606 -60 -606 0 -604L0 -570L-190 -570Z", DM)
               + L("M-10 -604C-60 -610 -120 -612 -176 -604", 2.6)
               + "".join(L(f"M{x} {y}Q{x - 9} {y - 11} {x - 24} {y - 15}", 1.7) for x, y in
                         ((-36, -606), (-70, -609), (-104, -610), (-136, -609)))
               + "".join(L(f"M{x} {y}Q{x - 9} {y + 7} {x - 20} {y + 9}", 1.5) for x, y in
                         ((-50, -607), (-86, -609), (-120, -609)))
               + L("M-40 -626Q-80 -636 -120 -630", 1.8, W)))
    o.append(T(-180, -604, -186, -604, -192, -600, 2.2))
    # a snail exploring his right foot
    snail = g(P("M-18 0C-20 -6 -14 -9 -6 -8L14 -8C22 -8 26 -4 28 0Z", W, 2.6)
              + S(circ(2, -16, 11), W, 3, F(circ(5, -13, 9), DM) + L("M2 -16m-5 0a5 5 0 1 0 5 -5", 1.6))
              + L("M-14 -8L-17 -18M-10 -8L-10 -19", 1.8) + C(-17, -19, 2, INK) + C(-10, -20, 2, INK),
              "translate(94 -64) rotate(-6)")
    o.append(snail)
    return "".join(o)


# =============================================================================
# NIB: floating ink-drop sprite, nib tuft, waving; origin = centre of the drop
# =============================================================================
def nib():
    o = []
    for (x, y, r, a) in ((-62, -64, 6.2, -40), (70, -96, 5.4, 30), (-66, 50, 4.6, -120), (80, 50, 4.2, 115),
                         (-46, -102, 3.8, -20), (40, -124, 3.4, 15), (96, 4, 3.4, 90), (-30, 96, 3, 190)):
        o.append(drop(x, y, r, a))
    o.append(C(-52, 82, 2.6, INK) + C(60, 86, 2.2, INK) + C(-30, -124, 2, INK) + C(100, -40, 2.4, INK)
             + C(-74, -24, 1.8, INK) + C(104, 28, 1.8, INK))
    body = "M0 -80C10 -60 44 -34 44 0C44 28 24 46 0 46C-24 46 -44 28 -44 0C-44 -34 -10 -60 0 -80Z"
    # arms first so the shoulder joins disappear into the body
    o.append(L("M-38 12Q-52 22 -58 12", 7.5) + C(-60, 9, 6.2, INK) + C(-64, 3, 2.8, INK))
    o.append(L("M38 -6Q56 -16 62 -40", 7.5) + C(63, -45, 7, INK) + C(56, -51, 3.4, INK))
    o.append(L("M76 -66Q86 -56 84 -42", 2.2) + L("M84 -72Q96 -58 92 -40", 2) + L("M44 -66Q46 -74 52 -78", 2))
    o.append(P(body, INK, 4.6))
    o.append(T(-34, -4, -36, -30, -15, -52, 6.2, W) + C(-34, 8, 3, W) + C(-30, 17, 1.6, W))
    o.append(T(36, 14, 34, 32, 16, 40, 2.4, W))
    nibd = "M0 -126C5 -116 17 -102 18 -90L15 -76C9 -72 -9 -72 -15 -76L-18 -90C-17 -102 -5 -116 0 -126Z"
    o.append(S(nibd, W, 3.6, F("M1 -130L22 -130L22 -70L1 -70Z", DM) + L("M0 -122L0 -96", 2.4) + C(0, -93, 3.2, INK)
               + L("M-15 -82Q0 -77 15 -82", 2.2) + L("M-12 -100Q-8 -90 -9 -82M12 -100Q8 -90 9 -82", 1.4)
               + L("M-6 -116L-10 -104", 1.6, W)))
    # face
    o.append(C(-16, -4, 15.5, W) + C(17, -4, 15.5, W))
    o.append(C(-12, 0, 7.8, INK) + C(21, 0, 7.8, INK))
    o.append(C(-14.8, -3.2, 3, W) + C(18.2, -3.2, 3, W) + C(-9.6, 3.2, 1.2, W) + C(23.4, 3.2, 1.2, W))
    o.append(T(-28, -26, -18, -32, -7, -27, 2.8, W) + T(8, -27, 18, -33, 29, -26, 2.8, W))
    o.append(P("M-9 16Q2 34 13 16Q2 20 -9 16Z", W, 0) + P("M-3 24Q2 29 7 24Q2 22 -3 24Z", DL, 0))
    for bx in (-33, 30):
        o.append("".join(T(bx + d, 22, bx + d + 2, 17, bx + d + 4, 12, 1.9, W) for d in (0, 5, 10)))
    # floating motion lines
    o.append(L("M-26 62Q0 70 26 62", 2.6) + L("M-16 74Q0 79 16 74", 2.3) + L("M-7 85Q0 87 7 85", 2))
    return "".join(o)


# =============================================================================
# CAPTAIN RIBBIT: frog sailor, sou'wester, slicker, rod over the shoulder, fish
# local origin = ground point between his feet; about 400 tall including the hat
# =============================================================================
def ribbit():
    o = [E(4, 2, 104, 10, DM), ground_marks(-100, 108, 31)]
    o.append(grass(-112, 1, 0.9) + grass(124, 1, 1.0))
    butt, shoulder = (30, -150), (66, -262)
    ux, uy = shoulder[0] - butt[0], shoulder[1] - butt[1]
    ln = math.hypot(ux, uy)
    ux, uy = ux / ln, uy / ln
    tip = (butt[0] + ux * 378, butt[1] + uy * 378)
    tipx, tipy = tip

    # line, bobber, hooked fish (behind everything else)
    hook = (tipx + 5, -432)
    o.append(L(f"M{n(tipx)} {n(tipy)}Q{n(tipx + 6)} {n((tipy + hook[1]) / 2)} {n(hook[0])} {n(hook[1])}", 1.8))
    by = tipy + (hook[1] - tipy) * 0.42
    bx = tipx + 4
    o.append(S(circ(bx, by, 8), W, 3, F(rect(bx - 10, by, bx + 10, by + 10), HA)) + L(f"M{n(bx)} {n(by - 8)}L{n(bx)} {n(by - 14)}", 2.6))
    fish = g(L("M0 -6Q5 -1 2 4", 2)
             + P("M-10 40L-20 58Q-7 52 -1 60L-3 42Z", W, 3.2)
             + S("M0 2C10 4 16 14 15 26C14 36 7 42 -1 44C-9 42 -15 34 -15 24C-15 12 -9 3 0 2Z", W, 4,
                 F("M4 -2L20 -2L20 48L4 48Z", DM)
                 + L("M-8 20Q-3 24 2 20M-7 28Q-2 32 4 28M-4 36Q1 39 6 36", 1.5))
             + C(-5, 13, 3.6, INK) + C(-6.2, 11.8, 1.2, W) + E(2, 6, 3, 2, INK)
             + P("M13 20L23 15L20 28Z", W, 2.6),
             f"translate({n(hook[0])} {n(hook[1])}) rotate(12)")
    o.append(fish)
    fy = hook[1]
    o.append(L(f"M{n(tipx - 22)} {n(fy + 18)}Q{n(tipx - 27)} {n(fy + 28)} {n(tipx - 22)} {n(fy + 38)}", 2.2)
             + L(f"M{n(tipx + 32)} {n(fy + 14)}Q{n(tipx + 37)} {n(fy + 24)} {n(tipx + 32)} {n(fy + 34)}", 2.2)
             + drop(tipx + 24, fy + 62, 3, 160) + drop(tipx - 14, fy + 70, 2.4, 200))

    # rod beyond the shoulder (behind head and hat)
    rod_hi = tube([shoulder, tip], 6.4, 2.4)
    o.append(P(rod_hi, INK, 1.2))
    for t in (0.45, 0.75):
        x, y = shoulder[0] + (tipx - shoulder[0]) * t, shoulder[1] + (tipy - shoulder[1]) * t
        o.append(C(x + 3, y + 1, 2.6, W, 1.6))
    o.append(C(tipx + 1, tipy, 2.4, W, 1.6))

    # stubby legs and webbed feet
    for s in (-1, 1):
        fx = 34 * s
        o.append(S(f"M{fx - 11} -72L{fx + 11} -72L{fx + 10} -18L{fx - 10} -18Z", W, 4,
                   F(rect(fx + 1, -76, fx + 16, -14), DL) + E(fx - 3, -44, 3, 4, DM, 1.3)))
        foot = (f"M{fx - 8} -26C{fx - 24} -24 {fx - 36} -14 {fx - 38} -2Q{fx - 30} -7 {fx - 22} -3"
                f"Q{fx - 14} 3 {fx - 6} -2Q{fx + 2} -7 {fx + 10} -2Q{fx + 18} 3 {fx + 26} -3"
                f"C{fx + 30} -14 {fx + 22} -24 {fx + 8} -26Z")
        if s > 0:
            foot = (f"M{fx + 8} -26C{fx + 24} -24 {fx + 36} -14 {fx + 38} -2Q{fx + 30} -7 {fx + 22} -3"
                    f"Q{fx + 14} 3 {fx + 6} -2Q{fx - 2} -7 {fx - 10} -2Q{fx - 18} 3 {fx - 26} -3"
                    f"C{fx - 30} -14 {fx - 22} -24 {fx - 8} -26Z")
        o.append(S(foot, W, 4, F(rect(fx + (2 if s < 0 else 6), -30, fx + 40, 4), DL)
                   + L(f"M{fx} -22L{fx - 30 * (1 if s < 0 else -1)} -6M{fx} -22L{fx - 6 * (1 if s < 0 else -1)} -4"
                       f"M{fx} -22L{fx + 18 * (1 if s < 0 else -1)} -5", 1.5)))
        for tx in ((-37, -6, 26) if s < 0 else (37, 6, -26)):
            o.append(C(fx + tx, -2.5, 4, W, 2.6))

    # slicker coat
    coat = ("M-58 -264C-74 -240 -84 -190 -88 -120C-90 -96 -92 -80 -96 -64C-60 -54 60 -54 96 -64"
            "C92 -80 90 -96 88 -120C84 -190 74 -240 58 -264Z")
    o.append(S(coat, W, 5.2,
               F("M38 -272C68 -232 84 -170 88 -100L98 -50L140 -50L140 -272Z", HA)
               + F("M-100 -82C-40 -70 40 -70 100 -82L100 -50L-100 -50Z", HA)
               + L("M4 -262C7 -200 9 -120 8 -58", 2.8)
               + L("M-62 -200Q-56 -160 -62 -120", 1.8) + L("M-46 -140Q-42 -110 -48 -76", 1.6)
               + L("M60 -150Q64 -120 58 -86", 1.6)
               + S("M-78 -132L-36 -134L-36 -122L-78 -120Z", W, 2.6, stitches("M-74 -127L-40 -128.5"))
               + S("M40 -134L80 -132L81 -120L40 -122Z", W, 2.6, stitches("M44 -128.5L77 -127"))
               + stitches("M-90 -74Q0 -62 92 -74")))
    for y in (-232, -196, -160, -124, -90):
        o.append(P(f"M13 {y - 4}L28 {y - 4.5}L28 {y + 3}L13 {y + 3.5}Z", W, 2.6) + L(f"M7 {y}L13 {y}", 2))
    # a little anchor stitched on his chest
    o.append(g(L("M0 -9L0 9M-5 -5L5 -5M-8 3Q-7 11 0 11Q7 11 8 3", 2) + C(0, -11, 2.4, W, 1.6), "translate(-40 -210)"))

    # head with the two eye domes in its silhouette
    headd = ("M-86 -296C-90 -316 -80 -326 -66 -332C-68 -354 -54 -368 -38 -368C-22 -368 -10 -356 -10 -340"
             "C-4 -342 4 -342 12 -340C12 -356 24 -368 40 -368C56 -368 70 -354 68 -332"
             "C82 -324 90 -314 86 -296C84 -272 50 -258 0 -258C-50 -258 -84 -272 -86 -296Z")
    o.append(S(headd, W, 5.2,
               F("M70 -380C110 -320 80 -252 0 -250L0 -262C52 -266 80 -288 74 -330L60 -380Z", DL)
               + E(-66, -314, 6, 4.2, DM, 1.8) + E(-52, -324, 3.6, 2.6, DM, 1.6) + E(-74, -298, 3.4, 2.4, DM, 1.5)
               + E(64, -318, 3.4, 2.4, DM, 1.4)
               + C(-7, -316, 2.2, INK) + C(7, -316, 2.2, INK)
               + L("M-72 -298C-34 -268 32 -268 72 -298", 3.8)
               + L("M-20 -281Q0 -275 20 -281", 1.6)))
    o.append(T(-72, -298, -77, -299, -79, -305, 2.3) + T(72, -298, 77, -299, 79, -305, 2.3))
    o.append(E(-58, -288, 11, 6, DL) + E(58, -288, 11, 6, DL))
    # droopy-lidded eyes inside the domes
    for ex, px in ((-38, -33), (40, 45)):
        ey, er = -341, 21
        k = nid()
        o.append(f'<clipPath id="{k}"><path d="{circ(ex, ey, er)}"/></clipPath>')
        o.append(C(ex, ey, er, W))
        o.append(f'<g clip-path="url(#{k})">'
                 + E(px, ey + 8, 8.4, 8.4, INK) + C(px - 2.6, ey + 5.4, 2.6, W) + C(px + 3, ey + 11.2, 1.1, W)
                 + P(f"M{ex - er - 2} {ey - er - 2}L{ex + er + 2} {ey - er - 2}L{ex + er + 2} {ey + 1}"
                     f"Q{ex} {ey + 9} {ex - er - 2} {ey + 1}Z", W, 0)
                 + F(f"M{ex - er - 2} {ey - 6}Q{ex} {ey + 2} {ex + er + 2} {ey - 6}L{ex + er + 2} {ey + 1}"
                     f"Q{ex} {ey + 9} {ex - er - 2} {ey + 1}Z", DL)
                 + F(f"M{ex + 6} {ey - er - 2}L{ex + er + 2} {ey - er - 2}L{ex + er + 2} {ey + 2}L{ex + 10} {ey}Z", HA)
                 + "</g>")
        o.append(L(f"M{ex - er + 1} {ey + 1}Q{ex} {ey + 10} {ex + er - 1} {ey + 1}", 3.6))
        o.append(P(circ(ex, ey, er), "none", 2.6))
    # sou'wester hat pulled down over the eye domes: crown, then the wide brim
    crown = "M-50 -374C-52 -408 -24 -420 2 -420C30 -420 56 -408 54 -374Z"
    o.append(S(crown, W, 4.8, F("M26 -426C48 -414 58 -398 56 -372L38 -372C42 -392 38 -410 26 -426Z", HA)
               + L("M-16 -418C-22 -404 -24 -390 -24 -376M20 -420C24 -406 26 -390 26 -376", 1.8)
               + L("M-32 -404Q-26 -414 -14 -417", 1.8))
             + S(circ(2, -420, 5.5), W, 2.8, F(circ(5, -418, 4.5), DM)))
    brim = ("M-128 -308C-132 -344 -72 -382 2 -382C76 -382 134 -344 130 -308C128 -298 118 -298 114 -306"
            "C102 -332 64 -358 2 -358C-60 -358 -98 -332 -110 -306C-114 -298 -124 -298 -128 -308Z")
    o.append(S(brim, W, 4.8, F("M70 -392C112 -372 136 -340 134 -300L108 -300C100 -330 84 -352 60 -366Z", HA)
               + F("M-134 -312C-128 -300 -118 -298 -110 -306C-100 -330 -60 -356 2 -358L2 -350C-60 -348 -100 -322 -112 -298L-134 -298Z", HA)
               + stitches("M-118 -312C-112 -344 -60 -372 2 -372C64 -372 116 -344 120 -312")
               + L("M-80 -366Q-50 -378 -16 -380", 1.8, W)))
    # collar turned up
    collar_l = "M-64 -264C-62 -286 -32 -288 -2 -272L0 -246C-20 -258 -44 -256 -58 -242Z"
    o.append(S(collar_l, W, 4.2, F("M-70 -290L-30 -290L-30 -240L-70 -240Z", HA)))
    o.append(S(mir(collar_l), W, 4.2, F(rect(-10, -292, 70, -240), HA)))

    # rod in front of the chest: cork grip, reel, then the hands
    nx_, ny_ = -uy, ux
    rod_lo = tube([(butt[0] - ux * 14, butt[1] - uy * 14), shoulder], 8.6, 6.4)
    o.append(P(rod_lo, INK, 1.2))
    o.append(P(tube([(butt[0] - ux * 16, butt[1] - uy * 16), (butt[0] + ux * 30, butt[1] + uy * 30)], 13, 11), DM, 2.8))
    o.append(L(f"M{n(butt[0] - ux * 2 - nx_ * 6)} {n(butt[1] - uy * 2 - ny_ * 6)}L{n(butt[0] - ux * 2 + nx_ * 6)} {n(butt[1] - uy * 2 + ny_ * 6)}", 1.6))
    rx, ry = butt[0] + ux * 12 + nx_ * 15, butt[1] + uy * 12 + ny_ * 15
    o.append(L(f"M{n(butt[0] + ux * 12)} {n(butt[1] + uy * 12)}L{n(rx)} {n(ry)}", 4))
    o.append(S(circ(rx, ry, 11), W, 3.2, F(rect(rx, ry - 12, rx + 12, ry + 12), DL) + C(rx, ry, 3.4, INK))
             + L(f"M{n(rx)} {n(ry)}L{n(rx + 9)} {n(ry + 10)}", 2.6) + C(rx + 10, ry + 11, 3.2, INK))
    # arm holding the rod (viewer right): bent sleeve, cuff, webbed hand
    o.append(S("M48 -266C74 -272 102 -252 106 -216C108 -196 100 -184 88 -184L64 -186L62 -208L82 -212"
               "C82 -228 72 -240 54 -240Z", W, 4.6,
               F("M70 -280C102 -256 112 -220 104 -180L130 -180L130 -280Z", HA)
               + F("M60 -194L100 -194L100 -180L60 -180Z", HA)
               + L("M92 -238Q98 -226 96 -212", 1.6) + L("M86 -204Q80 -198 72 -200", 1.6)))
    o.append(S("M55 -212L68 -213L69 -182L56 -181Z", W, 3.4, F(rect(62, -216, 72, -178), HA)))
    hx, hy = butt[0] + ux * 52, butt[1] + uy * 52
    o.append(S(circ(hx + 2, hy, 13), W, 4, F(rect(hx + 6, hy - 16, hx + 18, hy + 16), DL)))
    o.append(C(hx - 10, hy - 8, 4.2, W, 2.6) + C(hx - 12, hy + 1, 4.2, W, 2.6) + C(hx - 9, hy + 10, 4.2, W, 2.6))
    # arm with hand resting on the belly (viewer left)
    o.append(S("M-48 -266C-76 -272 -104 -246 -106 -208C-107 -184 -96 -166 -78 -164L-50 -162L-48 -186L-74 -190"
               "C-80 -206 -76 -228 -56 -240Z", W, 4.6,
               F("M-110 -200C-104 -176 -90 -166 -60 -166L-60 -150L-110 -150Z", HA)
               + L("M-90 -238Q-96 -224 -94 -210", 1.6) + L("M-84 -180Q-76 -174 -66 -176", 1.6)))
    o.append(S("M-57 -191L-44 -191L-43 -160L-56 -160Z", W, 3.4, F(rect(-50, -194, -40, -156), HA)))
    o.append(S("M-46 -186C-38 -194 -20 -192 -16 -180C-12 -168 -20 -158 -32 -157C-44 -156 -52 -174 -46 -186Z", W, 3.8,
               F("M-26 -196L-10 -196L-10 -152L-30 -152C-22 -162 -20 -180 -26 -196Z", DL)))
    o.append(C(-15, -184, 4.2, W, 2.6) + C(-12, -174, 4.2, W, 2.6) + C(-15, -164, 4.2, W, 2.6))
    return "".join(o)


# =============================================================================
# BOLT: boxy tin robot on treads, big lens eye, heart-sticker hatch, waving claw
# local origin = ground point under his middle; about 300 tall to the antenna ball
# =============================================================================
def claw(open_=1.0):
    """pincer pointing along -y from the wrist at (0, 0)"""
    a = 14 * open_
    fing = "M-4 -14C-12 -24 -12 -36 -6 -44C-3 -36 -1 -26 2 -18Z"
    return (g(S(fing, W, 3.6, F(rect(-2, -48, 6, -10), DM)), f"rotate({n(-a)} 0 -14)")
            + g(S(mir(fing), W, 3.6, F(rect(2, -48, 10, -10), DM)), f"rotate({n(a)} 0 -14)")
            + S("M-14 2C-16 -10 -8 -18 0 -18C8 -18 16 -10 14 2Z", W, 3.8, F(rect(3, -22, 18, 4), DM)
                + L("M-13 -4Q0 -1 13 -4", 1.8))
            + rivet(0, -9, 2.4))


def robot_arm(pts):
    d = "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts)
    out = L(d, 20, INK) + L(d, 12.6, W)
    for i in range(1, len(pts) - 1):
        (xa, ya), (xb, yb) = pts[i - 1], pts[i + 1]
        dx, dy = xb - xa, yb - ya
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln * 7.5, dx / ln * 7.5
        x, y = pts[i]
        out += L(f"M{n(x - nx)} {n(y - ny)}L{n(x + nx)} {n(y + ny)}", 2)
    return out


def bolt():
    o = [E(0, 2, 108, 10, DM), ground_marks(-104, 104, 41)]
    o.append(grass(-120, 1, 0.9) + E(126, -3, 6, 4, W, 2.2))

    # waving arm (viewer right) and hanging arm (viewer left): behind the body
    wave = [(52, -118), (70, -128), (86, -146), (98, -166), (106, -188), (110, -208)]
    o.append(robot_arm(wave))
    o.append(g(S("M-10 -8L10 -8L11 6L-11 6Z", W, 3.4, F(rect(2, -10, 14, 8), DM)), "translate(110 -212) rotate(6)"))
    o.append(g(claw(1.2), "translate(111 -220) rotate(8)"))
    o.append(L("M140 -246Q150 -232 146 -214", 2.4) + L("M152 -258Q166 -238 160 -212", 2.2)
             + L("M84 -252Q78 -240 80 -228", 2.2))
    hang = [(-52, -118), (-68, -116), (-82, -110), (-94, -100), (-102, -88)]
    o.append(robot_arm(hang))
    o.append(g(S("M-10 -8L10 -8L11 6L-11 6Z", W, 3.4, F(rect(2, -10, 14, 8), DM)), "translate(-105 -83) rotate(152)"))
    o.append(g(claw(0.6), "translate(-109 -76) rotate(156)"))

    # tank treads
    belt = "M-52 -60L52 -60C70 -60 82 -46 82 -30C82 -14 70 -1 52 -1L-52 -1C-70 -1 -82 -14 -82 -30C-82 -46 -70 -60 -52 -60Z"
    teeth = "".join(L(f"M{x} -60L{x} -53", 2.2, W) + L(f"M{x} -8L{x} -1", 2.2, W) for x in range(-48, 52, 10))
    o.append(S(belt, INK, 4.6, teeth + L("M-70 -48Q-76 -30 -70 -12", 2.2, W) + L("M70 -48Q76 -30 70 -12", 2.2, W)))
    o.append(S(rrect(-66, -50, 66, -11, 18), W, 3.4, F(rect(-70, -26, 70, -8), DM)
               + F("M30 -52L70 -52L70 -8L40 -8Z", DM)))
    for x in (-46, -16, 16, 46):
        o.append(S(circ(x, -31, 12), W, 3, F(circ(x + 3, -28, 10), DL)) + C(x, -31, 4, INK) + C(x - 1.2, -32.2, 1.2, W))

    # body box with chest hatch and heart sticker
    bodyd = "M-58 -146C-60 -146 -62 -144 -62 -141L-64 -62L64 -62L62 -141C62 -144 60 -146 58 -146Z"
    o.append(S(bodyd, W, 5, F("M34 -150L70 -150L70 -58L40 -58Z", DM)
               + F("M-70 -80L70 -80L70 -58L-70 -58Z", HA)
               + "".join(rivet(x, -138, 2.4) for x in (-50, -30, 30, 50))
               + rivet(-54, -72) + rivet(54, -72)
               + flicks((-56, -136, 50, -86), 6, 61, (3, 5), (10, 40), 1.1)))
    o.append(S(rrect(-30, -130, 30, -80, 6), W, 3.4, F("M18 -132L34 -132L34 -78L22 -78Z", DM)
               + L("M-30 -122L30 -122", 1.4)))
    o.append(P("M-36 -124L-29 -124L-29 -114L-36 -114Z", W, 2.2) + P("M-36 -96L-29 -96L-29 -86L-36 -86Z", W, 2.2))
    o.append(C(24, -105, 3.6, W, 2.2) + C(24, -105, 1.2, INK))
    heart = "M0 -92C-4 -98 -16 -104 -16 -113C-16 -120 -9 -123 -4 -120C-2 -119 -1 -117 0 -115C1 -117 2 -119 4 -120C9 -123 16 -120 16 -113C16 -104 4 -98 0 -92Z"
    o.append(g(P(heart, W, 3.2) + g(F(heart, DM), "translate(0 -1) scale(0.72) translate(0 -41)")
               + P("M7 -121L12 -124L13 -117Z", W, 1.6) + T(-11, -114, -10, -118, -6, -118, 1.4, W),
               "translate(-2 4)"))

    # shoulder joints
    o.append(S(circ(56, -120, 10), W, 3.4, F(circ(60, -117, 8), DM)) + C(56, -120, 2.4, INK))
    o.append(S(circ(-56, -120, 10), W, 3.4, F(circ(-52, -117, 8), DL)) + C(-56, -120, 2.4, INK))

    # neck
    for i, y in enumerate((-152, -160, -168)):
        o.append(P(rrect(-16 + i, y - 6, 16 - i, y + 4, 3), W if i % 2 else DM, 3))

    # head (tilted), antenna
    head = []
    head.append(P("M-86 -232L-74 -234L-74 -190L-86 -192Z", DM, 4) + rivet(-80, -212, 2.6))
    head.append(P("M86 -232L74 -234L74 -190L86 -192Z", DM, 4) + rivet(80, -212, 2.6))
    head.append(P("M6 -258L22 -258L20 -268L8 -268Z", DM, 3))
    head.append(L("M14 -268L12 -284L30 -296", 4.2))
    head.append(S(circ(34, -298, 8.5), W, 3.6, F(circ(38, -295, 8), DM) + C(31, -301, 2.4)))
    head.append(ray(34, -298, -160, 13, 21, 2.4) + ray(34, -298, -110, 13, 21, 2.4) + ray(34, -298, -60, 13, 20, 2.4)
                + ray(34, -298, -10, 13, 19, 2.4))
    hd = "M-64 -258C-70 -258 -74 -254 -74 -248L-72 -180C-72 -175 -68 -172 -63 -172L63 -172C68 -172 72 -175 72 -180L74 -248C74 -254 70 -258 64 -258Z"
    head.append(S(hd, W, 5.2,
                  F("M48 -262L80 -262L80 -168L52 -168Z", DM)
                  + F("M-80 -190C-30 -186 30 -186 80 -190L80 -168L-80 -168Z", HA)
                  + L("M-74 -244L74 -244", 2.6)
                  + "".join(rivet(x, -251, 2.3) for x in (-60, -40, -20, 0, 20, 40, 60))
                  + rivet(-64, -232) + rivet(64, -232) + rivet(-64, -182) + rivet(64, -182)
                  + L("M-58 -184Q-44 -188 -32 -184", 1.6)
                  + flicks((-64, -238, 60, -186), 8, 71, (3, 5), (10, 40), 1.1)))
    lx, ly = -18, -212
    head.append(C(lx, ly, 31, W, 4.8))
    head.append("".join(C(lx + 25.5 * math.cos(math.radians(a)), ly + 25.5 * math.sin(math.radians(a)), 1.9, INK)
                        for a in range(0, 360, 45)))
    head.append(C(lx, ly, 21, DM, 3.2))
    head.append(C(lx, ly, 15, INK))
    head.append(C(lx - 6, ly - 6, 5.4, W) + C(lx + 6, ly + 6, 2.3, W) + C(lx - 2, ly - 10, 1.5, W))
    head.append(C(38, -226, 13, W, 4.2) + C(38, -226, 7.4, INK) + C(35.4, -228.6, 2.4, W))
    head.append(E(56, -200, 6.4, 3.6, DL))
    grille = "M16 -200Q34 -190 52 -200L52 -191Q34 -178 16 -191Z"
    head.append(S(grille, W, 3, "".join(L(f"M{x} -206L{x} -176", 1.7) for x in range(20, 52, 5))))
    o.append(g("".join(head), "rotate(-5 0 -172)"))
    return "".join(o)


# =============================================================================
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
    groups = [
        ("juniper", juniper(), f"translate(215 {GROUND})"),
        ("moss", moss(), f"translate(570 {GROUND})"),
        ("nib-shadow", E(0, 2, 44, 5.5, DL) + ground_marks(-44, 44, 51), f"translate(862 {GROUND})"),
        ("nib", nib(), "translate(862 440)"),
        ("captain-ribbit", ribbit(), f"translate(1080 {GROUND})"),
        ("bolt", bolt(), f"translate(1360 {GROUND})"),
    ]
    body = "".join(f'<!-- {name} --><g id="{name}" transform="{tr}">{content}</g>' for name, content, tr in groups)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 700" width="1600" height="700" role="img">'
           '<title>Storyfolk character line-up: Juniper with her spyglass, Moss the forest giant, Nib the ink '
           'sprite, Captain Ribbit with his fishing rod, and Bolt the tin robot</title>'
           + DEFS
           + '<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">' + body + "</g></svg>")
    with open(OUT, "w") as fh:
        fh.write(svg)
    print(f"wrote {os.path.normpath(OUT)} ({len(svg) / 1024:.0f} KB)")


main()
