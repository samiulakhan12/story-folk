#!/usr/bin/env python3
"""Builds ../assets/caravan.svg ("the snail caravan") for the Storyfolk site.

Standard library only (math, os, random). Run:  python3 tools/generate-caravan.py
The SVG is written to ../assets/caravan.svg relative to this script.

Path data is hand-placed; Python only assembles groups, clip paths and the
repeated marks (rivets, flicks, coil springs, rope twists, the shell spiral).

Composition plan (viewBox 0 0 1000 800, snail faces right, seen a little from the front):
  ground patch ........ y 712-792, x 28-972; halftone cast shadow (490,748) rx 370
  footprint trail ..... x 30-160 behind the snail
  hull / foot ......... tail tip (55,548) -> deck line y 494 -> neck rises x 640-880
  shell ............... centre (360,425) r 175, depth crescent on the right,
                        spiral from porthole (348,410) out to the lower right
  porthole ............ (348,410) r 46 with curtains; door x 452-502, y 405-493
  chimney ............. x 212-242, y 190-318; smoke puffs drift up-left to (30,26)
  NIB ................. sits on the chimney rim, origin (228,168) scale .5
  hanging pot ......... bracket off the shell's left at y 345, pot x 128-176
  crate ............... strapped on the tail, x 85-165, y 452-506
  roof deck ........... x 300-510, y 241-258, struts down to the shell
  PIP ................. origin (385,190) scale .66, hand on the wheel (430,190)
  parasol ............. pole from the wheel hub, canopy x 318-542, y 12-88
  head ................ (820,328); eye stalks to (780,192) and (860,182); headlamp (875,297)
  legs ................ near rear planted (255,572)->(276,735); near front lifted (615,572)->(716,684)
                        far rear (300,565)->(328,718); far front (655,565)->(686,716)
  ladder .............. off the porch (548/566,494) down to y 684
  kettle .............. front deck x 580-652, y 438-492
  bunting ............. parasol tip (540,80) -> near eye stalk (786,232)
"""
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "caravan.svg")

INK = "#111"
W = "#fff"
DL, DM, DD, HA, CH = ("url(#dots-light)", "url(#dots-mid)", "url(#dots-dark)",
                      "url(#hatch)", "url(#crosshatch)")

_n = [0]


def nid():
    _n[0] += 1
    return f"c{_n[0]}"


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def P(d, fill=W, sw=4.5, extra=""):
    st = f' stroke="{INK}" stroke-width="{sw}"' if sw else ""
    return f'<path d="{d}" fill="{fill}"{st}{" " + extra if extra else ""}/>'


def L(d, sw=2.5, col=INK, extra=""):
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw}"{" " + extra if extra else ""}/>'


def F(d, pat):
    return f'<path d="{d}" fill="{pat}"/>'


def S(d, fill=W, sw=4.5, inner=""):
    """filled shape, inner content clipped to it, outline stroked last"""
    k = nid()
    return (f'<clipPath id="{k}"><path d="{d}"/></clipPath><path d="{d}" fill="{fill}"/>'
            f'<g clip-path="url(#{k})">{inner}</g>'
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}"/>')


def C(cx, cy, r, fill=W, sw=0):
    st = f' stroke="{INK}" stroke-width="{sw}"' if sw else ""
    return f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}"{st}/>'


def E(cx, cy, rx, ry, fill=W, sw=0, rot=0):
    st = f' stroke="{INK}" stroke-width="{sw}"' if sw else ""
    tr = f' transform="rotate({n(rot)} {n(cx)} {n(cy)})"' if rot else ""
    return f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{fill}"{st}{tr}/>'


def circ(cx, cy, r):
    return f"M{n(cx - r)} {n(cy)}A{n(r)} {n(r)} 0 1 0 {n(cx + r)} {n(cy)}A{n(r)} {n(r)} 0 1 0 {n(cx - r)} {n(cy)}Z"


def ell(cx, cy, rx, ry):
    return f"M{n(cx - rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(cx + rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(cx - rx)} {n(cy)}Z"


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
    """closed path through pts whose edges bulge outward (smoke, fluff, pom-poms)"""
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


def drop(cx, cy, r, ang=0, fill=INK, sw=0):
    """teardrop whose tip points at angle ang (0 = up)"""
    d = (f"M0 {n(-2.3 * r)}C{n(0.45 * r)} {n(-1.5 * r)} {n(r)} {n(-0.8 * r)} {n(r)} 0"
         f"A{n(r)} {n(r)} 0 1 1 {n(-r)} 0C{n(-r)} {n(-0.8 * r)} {n(-0.45 * r)} {n(-1.5 * r)} 0 {n(-2.3 * r)}Z")
    st = f' stroke="{INK}" stroke-width="{sw}"' if sw else ""
    return f'<path d="{d}" fill="{fill}"{st} transform="translate({n(cx)} {n(cy)}) rotate({n(ang)})"/>'


def flicks(box, count, seed, length=(4, 8), ang=(20, 70), w=1.6):
    """scattered short hatch flicks (texture) inside a bbox"""
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


def tuft(x, y, s=10, seed=1, w=1.8):
    """a little grass tuft: 4-5 tapered blades fanning up from (x,y)"""
    rnd = random.Random(seed)
    out = []
    k = rnd.randint(4, 6)
    for i in range(k):
        a = math.radians(-150 + 120 * i / (k - 1) + rnd.uniform(-8, 8))
        ln = s * rnd.uniform(0.7, 1.25)
        ex, ey = x + math.cos(a) * ln, y + math.sin(a) * ln
        out.append(T(x + (i - k / 2) * 1.2, y, (x + ex) / 2 + rnd.uniform(-2, 2), (y + ey) / 2, ex, ey, w))
    return "".join(out)


def stitches(d, sw=1.3):
    return L(d, sw, extra='stroke-dasharray="2.4 3"')


def rivet(x, y, r=2.4):
    return C(x, y, r, W, 1.8) + C(x - r * 0.3, y - r * 0.3, r * 0.32, INK)


def rivets_line(x0, y0, x1, y1, k, r=2.4):
    return "".join(rivet(x0 + (x1 - x0) * i / (k - 1), y0 + (y1 - y0) * i / (k - 1), r) for i in range(k))


def bolt(x, y, r=4.5, ang=20):
    """hex-ish bolt head with a slot"""
    a = math.radians(ang)
    dx, dy = math.cos(a) * r * 0.7, math.sin(a) * r * 0.7
    return C(x, y, r, W, 2) + L(f"M{n(x - dx)} {n(y - dy)}L{n(x + dx)} {n(y + dy)}", 1.6)


def g(content, tr=None, extra=""):
    t = f' transform="{tr}"' if tr else ""
    return f"<g{t}{' ' + extra if extra else ''}>{content}</g>"


def smooth(pts, closed=False, k=1 / 6):
    """Catmull-Rom spline through pts as cubic Bezier path data"""
    m = len(pts)
    d = f"M{n(pts[0][0])} {n(pts[0][1])}"
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = pts[(i - 1) % m] if (closed or i > 0) else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if (closed or i + 2 < m) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k)
        c2 = (p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k)
        d += f"C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(p2[0])} {n(p2[1])}"
    return d + ("Z" if closed else "")


def taper(segs, w, k=20, bias=0.0):
    """filled brush stroke along a chain of cubic segments [(p0,c1,c2,p1), ...], thick in the middle,
    tapering to points at both ends; bias pushes the weight outward along the left-hand normal"""
    pts = []
    for (p0, c1, c2, p1) in segs:
        for i in range(k + (1 if (p0, c1, c2, p1) == segs[-1] else 0)):
            t = i / k
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            pts.append((a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0], a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1]))
    m = len(pts) - 1
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        x0, y0 = pts[max(0, i - 1)]
        x1, y1 = pts[min(m, i + 1)]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        h = w / 2 * math.sin(math.pi * i / m) ** 0.7
        left.append((x + nx * h * (1 + bias), y + ny * h * (1 + bias)))
        right.append((x - nx * h * (1 - bias), y - ny * h * (1 - bias)))
    return F("M" + "L".join(f"{n(x)} {n(y)}" for x, y in left + right[::-1]) + "Z", INK)


def tube(p0, p1, w0, w1):
    """straight tapered plate between two points (a limb segment)"""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    a, b = w0 / 2, w1 / 2
    return (f"M{n(x0 + nx * a)} {n(y0 + ny * a)}L{n(x1 + nx * b)} {n(y1 + ny * b)}"
            f"L{n(x1 - nx * b)} {n(y1 - ny * b)}L{n(x0 - nx * a)} {n(y0 - ny * a)}Z")


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
    pts2 = left + right[::-1]
    return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts2) + "Z"


def qpts(p0, c, p1, k=16):
    """sample a quadratic curve"""
    out = []
    for i in range(k + 1):
        t = i / k
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]))
    return out


def coil(p0, p1, turns, w, sw=2.2):
    """coil spring between p0 and p1, drawn as looping front strokes"""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    step = ln / turns
    out = []
    for i in range(turns):
        ax, ay = x0 + ux * step * i, y0 + uy * step * i
        bx, by = ax + ux * step, ay + uy * step
        # front loop: from one side to the other, bulging along the axis
        sx, sy = ax + nx * w, ay + ny * w
        ex, ey = bx - nx * w + ux * 0, by - ny * w
        cx, cy = (ax + bx) / 2 + ux * step * 0.9, (ay + by) / 2 + uy * step * 0.9
        out.append(f"M{n(sx)} {n(sy)}Q{n(cx)} {n(cy)} {n(ex)} {n(ey)}")
        # back half, thin
        out.append(f"M{n(ex)} {n(ey)}Q{n(bx - ux * step * 0.2)} {n(by - uy * step * 0.2)} {n(bx + nx * w)} {n(by + ny * w)}")
    front = L("".join(out[0::2]), sw)
    back = L("".join(out[1::2]), sw * 0.6)
    return back + front


def pad(cx, cy, rx, ry, h, rot=0, top=W, side=DM, sw=3.6):
    """round mechanical foot pad: a disc seen slightly from above"""
    side_d = (f"M{n(cx - rx)} {n(cy)}L{n(cx - rx)} {n(cy + h)}A{n(rx)} {n(ry)} 0 0 0 {n(cx + rx)} {n(cy + h)}"
              f"L{n(cx + rx)} {n(cy)}A{n(rx)} {n(ry)} 0 0 1 {n(cx - rx)} {n(cy)}Z")
    out = [P(side_d, side, sw)]
    # tread notches round the rim
    for i in range(1, 8):
        a = math.pi * i / 8
        x = cx - math.cos(a) * rx
        y = cy + math.sin(a) * ry
        out.append(L(f"M{n(x)} {n(y + 1)}L{n(x)} {n(y + h - 1)}", 1.6))
    out.append(P(ell(cx, cy, rx, ry), top, sw))
    out.append(L(f"M{n(cx - rx * 0.62)} {n(cy)}A{n(rx * 0.62)} {n(ry * 0.6)} 0 1 0 {n(cx + rx * 0.62)} {n(cy)}"
                 f"A{n(rx * 0.62)} {n(ry * 0.6)} 0 1 0 {n(cx - rx * 0.62)} {n(cy)}", 1.8))
    out.append(C(cx, cy, 3.2, INK))
    s = g("".join(out), f"rotate({n(rot)} {n(cx)} {n(cy)})" if rot else None)
    return s


def joint(x, y, r, fill=DL):
    """bolted round joint plate"""
    out = [C(x, y, r, fill, 3.4), C(x, y, r * 0.55, W, 2.4), bolt(x, y, r * 0.3)]
    for i in range(6):
        a = math.radians(i * 60 + 15)
        out.append(C(x + math.cos(a) * r * 0.78, y + math.sin(a) * r * 0.78, 1.5, INK))
    return "".join(out)


# ---------------------------------------------------------------------------
# GROUND — patch, cast shadow, footprint trail, pebbles (tufts are drawn last)
# ---------------------------------------------------------------------------
def ground():
    o = []
    top = [(28, 754), (62, 734), (130, 723), (240, 716), (360, 713), (480, 711), (600, 713),
           (720, 716), (830, 721), (922, 731), (972, 750)]
    bot = [(948, 769), (860, 779), (700, 784), (500, 786), (300, 785), (150, 781), (58, 771)]
    o.append(P(smooth(top + bot, True), W, 0))
    o.append(L(smooth(top), 3))
    o.append(L(smooth(bot[1:6]), 2, extra='stroke-dasharray="46 9 18 7"'))
    # cast shadow, densest under the body
    o.append(E(490, 748, 372, 24, DL))
    o.append(E(480, 748, 330, 19, DM))
    o.append(E(470, 747, 210, 12, DD))
    # footprint trail (round pad prints) left behind the snail
    for (x, y, rx, ry, s) in ((44, 764, 16, 4.8, 3), (92, 741, 18, 5.2, 4), (140, 770, 20, 5.6, 5),
                              (190, 735, 20, 5.6, 6)):
        o.append(E(x, y, rx, ry, DM, 0))
        o.append(L(f"M{n(x - rx)} {n(y)}A{n(rx)} {n(ry)} 0 0 1 {n(x + rx)} {n(y)}", 2))
        o.append(E(x + 1, y + 0.8, rx * 0.5, ry * 0.45, W, 0))
        o.append(C(x + 1, y + 0.8, 1.3, INK))
    # pebbles
    for (x, y, rx, ry, rot) in ((868, 772, 9, 5, -10), (892, 764, 5, 3.4, 15), (612, 776, 7, 4, 5),
                                (205, 778, 8, 4.4, -6), (952, 752, 6, 3.6, 0), (395, 777, 5, 3, 10),
                                (760, 779, 6, 3.4, -12)):
        o.append(E(x, y, rx, ry, W, 2, rot))
        o.append(E(x + rx * 0.3, y + ry * 0.35, rx * 0.6, ry * 0.5, DM, 0, rot))
        o.append(E(x - rx * 0.35, y - ry * 0.35, rx * 0.25, ry * 0.2, INK, 0, rot))
    # dirt specks and hatch flicks on the ground
    o.append(specks((80, 772, 930, 782), 26, 31, (0.7, 1.4)))
    o.append(flicks((60, 728, 940, 742), 18, 32, (5, 10), (170, 185), 1.2))
    return "".join(o)


def ground_front():
    o = []
    for i, (x, y, s) in enumerate(((34, 752, 11), (120, 724, 9), (236, 717, 8), (430, 713, 9),
                                   (560, 714, 7), (812, 721, 10), (936, 738, 12), (966, 750, 8),
                                   (310, 762, 9), (240, 760, 10), (300, 783, 9), (655, 783, 10),
                                   (920, 774, 9), (90, 778, 8), (750, 755, 9), (800, 758, 8))):
        o.append(tuft(x, y, s, seed=40 + i))
    return "".join(o)


# ---------------------------------------------------------------------------
# SMOKE — round puffs drifting back (up-left) from the stovepipe
# ---------------------------------------------------------------------------
def smoke():
    o = []
    puffs = ((40, 44, 21, 1), (72, 32, 18, 9), (46, 74, 16, 10), (88, 62, 27, 2),     # old cloud drifting off
             (126, 96, 18, 3), (128, 120, 12, 11), (150, 110, 15, 8),                  # middle cloud
             (180, 140, 11, 4), (198, 161, 8, 5))                                      # fresh puffs
    for (x, y, r, s) in puffs:
        d = fuzz(x, y, r, 9, 0.3, seed=s, bulge=0.42)
        o.append(S(d, W, 3.4, F(circ(x + r * 0.45, y + r * 0.4, r * 0.95), DL) + P(circ(x - r * 0.2, y - r * 0.2, r * 0.95), W, 0)
                   + L(f"M{n(x - r * 0.5)} {n(y - r * 0.1)}Q{n(x - r * 0.3)} {n(y - r * 0.55)} {n(x + r * 0.15)} {n(y - r * 0.55)}", 1.5)))
    o.append(L("M15 80Q9 70 17 62", 1.8) + L("M122 52Q116 44 124 36", 1.6) + C(50, 98, 3, W, 1.8) + C(172, 100, 2.2, W, 1.5)
             + C(118, 128, 1.8, W, 1.4))
    return "".join(o)


# ---------------------------------------------------------------------------
# LEGS
# ---------------------------------------------------------------------------
def leg(hip, knee, ankle, padc, far=False, lifted=False, rot=0):
    o = []
    body = DD if far else W
    shade = INK if far else DM
    sw = 3.6 if far else 4.2
    if not far:
        # hydraulic piston behind the thigh, hull -> shin
        a = (hip[0] - 28, hip[1] + 14)
        b = ((knee[0] + ankle[0]) / 2, (knee[1] + ankle[1]) / 2)
        m = (a[0] + (b[0] - a[0]) * 0.55, a[1] + (b[1] - a[1]) * 0.55)
        o.append(P(tube(m, b, 6, 6), W, 2.6))
        o.append(S(tube(a, m, 13, 13), W, 3, F(tube((a[0] + 4, a[1]), (m[0] + 4, m[1]), 6, 6), DM)))
        o.append(C(a[0], a[1], 5, W, 2.6) + C(a[0], a[1], 1.6, INK) + C(b[0], b[1], 4.5, W, 2.4) + C(b[0], b[1], 1.5, INK))
    # thigh plate
    th = tube(hip, knee, 40 if not far else 34, 28 if not far else 24)
    dx, dy = knee[0] - hip[0], knee[1] - hip[1]
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    inner = F(tube((hip[0] - nx * 12, hip[1] - ny * 12), (knee[0] - nx * 9, knee[1] - ny * 9), 18, 13), shade)
    inner += L(f"M{n(hip[0] - nx * 3)} {n(hip[1] - ny * 3)}L{n(knee[0] - nx * 2)} {n(knee[1] - ny * 2)}", 1.6)
    inner += "".join(rivet(hip[0] + dx * t + nx * 10, hip[1] + dy * t + ny * 10, 1.9) for t in (0.35, 0.55, 0.75))
    inner += T(hip[0] + nx * 15 + dx * 0.3, hip[1] + ny * 15 + dy * 0.3, hip[0] + nx * 15 + dx * 0.5,
               hip[1] + ny * 15 + dy * 0.5, hip[0] + nx * 14 + dx * 0.75, hip[1] + ny * 14 + dy * 0.75, 1.4, W)
    o.append(S(th, body, sw, inner))
    # shin plate
    sh = tube(knee, ankle, 26 if not far else 22, 19 if not far else 16)
    dx, dy = ankle[0] - knee[0], ankle[1] - knee[1]
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    inner = F(tube((knee[0] - nx * 8, knee[1] - ny * 8), (ankle[0] - nx * 6, ankle[1] - ny * 6), 11, 8), shade)
    o.append(S(sh, body, sw, inner))
    if not far:
        o.append(coil((knee[0] + dx * 0.2, knee[1] + dy * 0.2), (knee[0] + dx * 0.8, knee[1] + dy * 0.8), 6, 17, 2.4))
    # ankle ball + pad
    o.append(pad(padc[0], padc[1], 40 if not far else 33, 11.5 if not far else 9.5, 9 if not far else 7, rot,
                 W if not far else DL, DM if not far else DD, 3.6 if not far else 3.2))
    o.append(C(ankle[0], ankle[1], 10 if not far else 8.5, DL if not far else DM, 3))
    o.append(C(ankle[0] - 2, ankle[1] - 2, 2.2, W))
    # knee joint
    o.append(joint(knee[0], knee[1], 18 if not far else 14, DL if not far else DM))
    return "".join(o)


def far_legs():
    o = [leg((318, 566), (368, 638), (346, 701), (344, 714), far=True),
         leg((640, 566), (682, 634), (657, 699), (655, 713), far=True)]
    return "".join(o)


def near_legs():
    o = []
    o.append(leg((255, 574), (306, 650), (280, 716), (278, 731)))
    o.append(joint(255, 574, 24))
    # lifted front leg, mid-step
    o.append(leg((612, 574), (692, 610), (720, 664), (727, 680), lifted=True, rot=-16))
    o.append(joint(615, 574, 24))
    # motion swooshes + dust falling from the lifted pad
    o.append(T(744, 652, 760, 660, 772, 676, 1.8) + T(752, 640, 770, 648, 782, 662, 1.5))
    o.append(C(716, 708, 2.2, INK) + C(732, 718, 1.6, INK) + C(746, 706, 1.8, INK) + C(724, 730, 1.3, INK))
    return "".join(o)


# ---------------------------------------------------------------------------
# HULL — the riveted snail body/foot, rising into the neck
# ---------------------------------------------------------------------------
HULL = ("M55 548C95 515 160 498 240 494L640 492C690 490 712 462 726 412C736 372 752 345 772 330"
        "L860 345C872 382 866 430 880 470C892 508 925 532 925 562C925 588 896 598 860 598"
        "L300 600C190 600 100 586 55 548Z")


def hull():
    inner = []
    # shading: lower flank in shadow, front of the neck turned from the light
    inner.append(F("M0 556L1000 556L1000 610L0 610Z", DL))
    inner.append(F("M0 578L1000 578L1000 610L0 610Z", DM))
    inner.append(F("M0 593L1000 593L1000 610L0 610Z", DD))
    inner.append(F("M848 330C880 380 870 440 890 480C905 515 935 540 935 600L1000 600L1000 330Z", DM))
    inner.append(F("M30 540C70 520 110 540 130 560L130 610L30 610Z", DM))
    # plate seams across the flank, each with a rivet column
    for x in (138, 232, 330, 428, 526, 624):
        inner.append(L(f"M{x} 488Q{x - 4} 545 {x + 2} 602", 2.6))
        inner.append(rivets_line(x - 7, 503, x - 7, 592, 6, 2.1))
    inner.append(L("M40 552C120 536 220 524 400 523L700 522", 2.4))
    inner.append(L("M60 578C200 579 400 579 900 578", 2.6))
    inner.append(rivets_line(150, 589, 870, 589, 37, 1.9))
    # neck rings
    for (a, b) in (((680, 496), (940, 510)), ((690, 456), (920, 470)), ((700, 418), (910, 426)),
                   ((714, 382), (900, 386))):
        inner.append(L(f"M{a[0]} {a[1]}Q{(a[0] + b[0]) / 2} {a[1] + 22} {b[0]} {b[1]}", 2.6))
        inner.append(L(f"M{a[0]} {a[1] + 6}Q{(a[0] + b[0]) / 2} {a[1] + 28} {b[0]} {b[1] + 6}", 1.3))
    # foot lip at the front
    inner.append(L("M860 520C890 528 915 545 925 562", 2.2))
    # texture: scuffs + light glints on the plates
    inner.append(flicks((150, 500, 700, 520), 22, 9, (4, 8), (15, 40), 1.3))
    inner.append(T(250, 503, 300, 499, 352, 502, 1.6, W))
    inner.append(T(450, 503, 500, 500, 560, 502, 1.6, W))
    # rivets on the neck rings
    for (a, b) in (((690, 456), (920, 470)), ((700, 418), (910, 426)), ((714, 382), (900, 386))):
        for i in range(2, 9):
            t = i / 10
            x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * (a[0] + b[0]) / 2 + t * t * b[0]
            y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * (a[1] + 22) + t * t * b[1] + 13
            inner.append(C(x, y, 1.5, INK))
    o = [S(HULL, W, 5, "".join(inner))]
    # heavier ink on the shadow side
    o.append(T(170, 597, 520, 603, 880, 597, 2.6))
    o.append(taper([((862, 350), (874, 388), (868, 432), (882, 472)), ((882, 472), (894, 508), (927, 532), (927, 562)),
                    ((927, 562), (927, 586), (905, 598), (850, 599))], 8))
    # maintenance hatch on the neck front
    o.append(S("M818 486C818 478 824 474 832 474L858 476C866 476 870 482 870 490L868 520C868 528 862 532 854 532"
               "L830 530C822 530 818 524 818 516Z", W, 3.4,
               F("M852 470L880 470L880 540L852 540Z", DM)
               + L("M828 492L860 494M828 502L860 504M828 512L859 514", 2.6)))
    o.append(bolt(823, 480, 2.6) + bolt(865, 481, 2.6) + bolt(823, 526, 2.6) + bolt(863, 528, 2.6))
    # tail fin: a little riveted rudder off the tip
    o.append(S("M58 548C40 536 26 520 22 500C38 504 54 514 66 528Z", W, 3.6,
               F("M20 520L70 520L70 560L20 560Z", DM) + L("M30 507Q45 517 57 532", 1.6)))
    o.append(rivet(52, 528, 2))
    return "".join(o)


def hull_pipe():
    o = []
    d = "M120 541C200 538 300 538 420 539L690 540C730 540 752 520 760 470"
    o.append(L(d, 10) + L(d, 5.4, W) + L("M122 539.5C200 537 300 537 420 538L690 538.5", 1.2, INK, 'stroke-dasharray="6 8"'))
    for x in (180, 300, 560, 668):
        o.append(P(f"M{x - 4} 532L{x + 4} 532L{x + 4} 548L{x - 4} 548Z", DM, 2.2))
        o.append(C(x, 528.5, 1.6, INK) + C(x, 551.5, 1.6, INK))
    # valve wheel on the pipe
    o.append(C(440, 539, 10, W, 2.8))
    o.append("".join(L(f"M{n(440 + math.cos(math.radians(a)) * 3)} {n(539 + math.sin(math.radians(a)) * 3)}"
                       f"L{n(440 + math.cos(math.radians(a)) * 9)} {n(539 + math.sin(math.radians(a)) * 9)}", 2)
                     for a in (0, 60, 120, 180, 240, 300)))
    o.append(C(440, 539, 3.2, INK))
    # pressure gauge on the neck
    gx, gy = 770, 448
    o.append(C(gx, gy, 19, DL, 3.6) + C(gx, gy, 13.5, W, 2.4))
    o.append("".join(ray(gx, gy, a, 9.5, 12.5, 1.1) for a in range(150, 391, 30)))
    o.append(T(gx, gy, gx + 4, gy - 4, gx + 8, gy - 8, 1.6) + C(gx, gy, 2.4, INK))
    o.append(L(f"M{gx - 8} {gy + 6}L{gx + 8} {gy + 6}", 1.4))
    o.append(rivet(gx - 15, gy - 10, 1.8) + rivet(gx + 15, gy - 10, 1.8) + rivet(gx, gy + 17, 1.8))
    return "".join(o)


# ---------------------------------------------------------------------------
# SHELL HOUSE — spiral shell of riveted plates with porthole and door
# ---------------------------------------------------------------------------
SC = (360, 425)
SR = 175
PC = (330, 380)
TURNS = 1.15
TH1 = math.radians(200)                 # spiral merges into the outline here (left side)
TH0 = TH1 - TURNS * 2 * math.pi         # and starts just off the porthole's lower left


def spiral_pt(t, inset=0.0):
    th = TH0 + t * (TH1 - TH0)
    r = 50 + (SR - 50) * t - inset
    cx = PC[0] + (SC[0] - PC[0]) * t
    cy = PC[1] + (SC[1] - PC[1]) * t
    return (cx + math.cos(th) * r, cy + math.sin(th) * r)


def spiral_band(t0, t1, w_of_t, k=120, inset=0.0):
    """filled tapered band centred on the spiral between t0 and t1"""
    left, right = [], []
    for i in range(k + 1):
        t = t0 + (t1 - t0) * i / k
        x, y = spiral_pt(t, inset)
        x2, y2 = spiral_pt(min(1, t + 0.002), inset)
        x1, y1 = spiral_pt(max(0, t - 0.002), inset)
        dx, dy = x2 - x1, y2 - y1
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        w = w_of_t(t) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in left + right[::-1]) + "Z"


def shell():
    o = []
    # depth: the front face of the coil peeking out on the right
    o.append(S(circ(371, 428, 173), DD, 4.5, F(circ(366, 420, 171), DM)))
    inner = []
    # shading crescent lower right
    inner.append(F(circ(SC[0], SC[1], SR + 4), DM))
    inner.append(P(circ(SC[0] - 24, SC[1] - 28, SR + 2), DL, 0))
    inner.append(P(circ(SC[0] - 44, SC[1] - 50, SR - 4), W, 0))
    # suture shadow: hatch on the inner whorl, tucked under the overlapping outer whorl
    inner.append(F(spiral_band(0.04, 0.985, lambda t: 4 + 16 * math.sin(math.pi * t) ** 0.8, inset=10), HA))
    # plate seams across the whorls (staggered like brickwork, so they never line up into spokes)
    turn = 1 / TURNS
    for t in (0.1, 0.22, 0.35, 0.47, 0.6, 0.71, 0.84):
        a = spiral_pt(t, -3)
        t2 = t + turn
        if t2 <= 1:
            b = spiral_pt(t2, 14)
        else:
            th = TH0 + t * (TH1 - TH0)
            b = (SC[0] + math.cos(th) * (SR + 6), SC[1] + math.sin(th) * (SR + 6))
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 18:
            continue
        inner.append(L(f"M{n(a[0])} {n(a[1])}L{n(b[0])} {n(b[1])}", 2.4))
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * 4.5, dx / ln * 4.5
        cnt = max(2, int(ln // 22))
        for s in range(cnt):
            f = (s + 0.6) / (cnt + 0.2)
            inner.append(rivet(a[0] + dx * f + nx, a[1] + dy * f + ny, 1.8))
    # inner whorl seams, from the porthole ring out to the first loop, offset from the outer ones
    for t in (0.16, 0.41, 0.66, 0.9):
        th = TH0 + t * (TH1 - TH0)
        a = (PC[0] + math.cos(th) * 49, PC[1] + math.sin(th) * 49)
        b = spiral_pt(t, 12)
        if math.hypot(b[0] - a[0], b[1] - a[1]) > 16:
            inner.append(L(f"M{n(a[0])} {n(a[1])}L{n(b[0])} {n(b[1])}", 2.2))
            inner.append(rivet((a[0] + b[0]) / 2 + 4, (a[1] + b[1]) / 2 - 3, 1.7))
    # rivets riding along the outer side of the lip
    for i in range(3, 116, 4):
        x, y = spiral_pt(i / 120, -8)
        inner.append(C(x, y, 1.5, INK))
    # the suture itself: a tapered ink line, fattest mid-way, fading into the outline
    inner.append(F(spiral_band(0.0, 1.0, lambda t: 1.5 + 5.5 * math.sin(math.pi * min(1, t * 1.15)) ** 0.6), INK))
    # dents, scratches and highlight glints
    inner.append(T(212, 380, 216, 330, 240, 292, 2.8, W) + T(252, 282, 266, 272, 284, 266, 2, W))
    inner.append(flicks((200, 300, 320, 480), 18, 21, (4, 7), (40, 80), 1.3))
    inner.append(flicks((420, 330, 520, 480), 10, 22, (4, 7), (100, 140), 1.2))
    o.append(S(circ(SC[0], SC[1], SR), W, 5, "".join(inner)))
    cx, cy, r = 371, 428, 174
    arc = []
    for i in range(4):
        a0 = math.radians(-46 + i * 17)
        a1 = math.radians(-46 + (i + 1) * 17)
        kk = 4 / 3 * math.tan((a1 - a0) / 4)
        p0 = (cx + math.cos(a0) * r, cy + math.sin(a0) * r)
        p1 = (cx + math.cos(a1) * r, cy + math.sin(a1) * r)
        c1 = (p0[0] - math.sin(a0) * r * kk, p0[1] + math.cos(a0) * r * kk)
        c2 = (p1[0] + math.sin(a1) * r * kk, p1[1] - math.cos(a1) * r * kk)
        arc.append((p0, c1, c2, p1))
    o.append(taper(arc, 7.5))
    # louvred vent plate under the deck
    o.append(S("M416 300L456 292L462 326L422 334Z", DL, 3,
               L("M422 306L456 299M423 314L458 307M424 322L459 315", 2.4)))
    o.append(rivet(419, 303, 1.6) + rivet(457, 295, 1.6) + rivet(421, 330, 1.6) + rivet(460, 322, 1.6))
    return "".join(o)


def porthole():
    o = []
    x, y = PC
    o.append(C(x, y, 47, DL, 4.6))
    o.append(T(x - 40, y + 8, x - 40, y - 30, x - 12, y - 42, 2.2, W))
    for i in range(8):
        a = math.radians(i * 45 + 22.5)
        o.append(bolt(x + math.cos(a) * 40, y + math.sin(a) * 40, 3.4, i * 37))
    glass = circ(x, y, 32)
    inner = [F(glass, DD)]
    # warm interior: a tiny lamp-glow disc and a sill with a potted sprout
    inner.append(C(x + 3, y - 4, 13, DL) + C(x + 3, y - 4, 7, W))
    inner.append(P(f"M{x - 34} {y + 18}L{x + 34} {y + 18}L{x + 34} {y + 40}L{x - 34} {y + 40}Z", W, 2.4))
    inner.append(P(f"M{x - 4} {y + 18}L{x + 6} {y + 18}L{x + 5} {y + 8}L{x - 3} {y + 8}Z", W, 1.8))
    inner.append(L(f"M{x + 1} {y + 8}Q{x} {y + 2} {x - 4} {y}M{x + 1} {y + 6}Q{x + 3} {y + 1} {x + 7} {y}", 1.6))
    # curtains tied back
    lc = (f"M{x - 34} {y - 30}L{x - 10} {y - 30}C{x - 14} {y - 16} {x - 22} {y - 4} {x - 22} {y + 4}"
          f"C{x - 20} {y + 10} {x - 16} {y + 14} {x - 14} {y + 18}L{x - 34} {y + 18}Z")
    rc = (f"M{x + 34} {y - 30}L{x + 14} {y - 30}C{x + 17} {y - 16} {x + 22} {y - 4} {x + 22} {y + 4}"
          f"C{x + 21} {y + 10} {x + 18} {y + 14} {x + 16} {y + 18}L{x + 34} {y + 18}Z")
    inner.append(P(lc, W, 2.4) + L(f"M{x - 26} {y - 28}Q{x - 30} {y - 6} {x - 28} {y + 16}M{x - 17} {y - 26}Q{x - 24} {y - 6} {x - 20} {y + 4}", 1.4))
    inner.append(P(rc, DL, 2.4) + L(f"M{x + 26} {y - 28}Q{x + 30} {y - 6} {x + 28} {y + 16}M{x + 19} {y - 26}Q{x + 25} {y - 6} {x + 22} {y + 4}", 1.4))
    inner.append(P(f"M{x - 25} {y + 4}Q{x - 20} {y + 1} {x - 17} {y + 5}", "none", 2.2) + C(x - 21, y + 3, 2.2, INK))
    inner.append(P(f"M{x + 25} {y + 4}Q{x + 20} {y + 1} {x + 17} {y + 5}", "none", 2.2) + C(x + 21, y + 3, 2.2, INK))
    # scalloped valance
    val = f"M{x - 34} {y - 34}L{x + 34} {y - 34}L{x + 34} {y - 22}"
    for i in range(6):
        x1 = x + 34 - (i + 1) * 68 / 6
        val += f"Q{n(x1 + 68 / 12)} {y - 14} {n(x1)} {y - 22}"
    val += "Z"
    inner.append(P(val, W, 2.2) + L(f"M{x - 30} {y - 27}L{x + 30} {y - 27}", 1.2, INK, 'stroke-dasharray="2 2.6"'))
    # glass glare
    inner.append(T(x + 6, y + 26, x + 20, y + 14, x + 26, y - 2, 2.4, W) + T(x + 14, y + 28, x + 24, y + 21, x + 28, y + 12, 1.4, W))
    o.append(S(glass, W, 3.6, "".join(inner)))
    return "".join(o)


def door():
    o = []
    # frame trim
    o.append('<g transform="translate(490 0) scale(0.84 1) translate(-477 0)">')
    frame = "M445 494L445 430C445 408 460 397 477 397C494 397 509 408 509 430L509 494Z"
    o.append(S(frame, DL, 4, F("M492 390L520 390L520 500L492 500Z", DM)))
    d = "M453 494L453 432C453 415 464 405 477 405C490 405 501 415 501 432L501 494Z"
    inner = [F("M488 400L510 400L510 500L488 500Z", DM)]
    inner.append(L("M465 404L465 496M477 402L477 496M489 404L489 496", 1.8))
    inner.append(flicks((455, 440, 500, 490), 8, 61, (3, 6), (80, 100), 1.1))
    inner.append(P("M449 436L474 436L474 443L449 443Z", DD, 1.8) + P("M449 474L474 474L474 481L449 481Z", DD, 1.8))
    inner.append(C(468, 439.5, 1.3, W) + C(468, 477.5, 1.3, W))
    o.append(S(d, W, 3.6, "".join(inner)))
    # little round window in the door + knob
    o.append(C(477, 424, 8.5, DD, 2.6) + L("M471.5 424L482.5 424M477 418.5L477 429.5", 1.6, W) + C(477, 424, 8.5, "none", 2.6))
    o.append(C(494, 460, 3.6, W, 2.2) + C(493, 459, 1, INK))
    o.append("</g>")
    return "".join(o)


def saddle():
    o = [P("M186 486L446 486L446 497L186 497Z", DL, 3.2)]
    o.append(rivets_line(196, 491.5, 436, 491.5, 13, 1.7))
    for x in (226, 326, 410):
        o.append(P(f"M{x - 7} 487L{x + 7} 487L{x + 5} 470L{x - 5} 470Z", DM, 2.6) + bolt(x, 476, 2.6))
    return "".join(o)


def porch():
    o = []
    o.append(P("M446 486L574 486L574 496L446 496Z", W, 3.2))
    o.append(L("M462 486L462 496M492 486L492 496M522 486L522 496M552 486L552 496", 1.5))
    o.append(T(446, 491, 470, 490, 500, 491, 0.8) + C(445, 491, 1.2, INK) + C(567, 491, 1.2, INK))
    o.append(P("M560 496L572 496L572 516Z", DM, 2.4))
    return "".join(o)


# ---------------------------------------------------------------------------
# CHIMNEY + gauge on the roof
# ---------------------------------------------------------------------------
def chimney():
    o = []
    # base flange plate on the shell
    o.append(P("M196 322C204 304 236 296 254 304L256 314C236 308 210 314 200 330Z", DM, 3.2))
    pipe = "M212 316L214 198L242 198L242 312Z"
    o.append(S(pipe, W, 4.2, F("M232 190L250 190L250 320L232 320Z", DM) + F("M210 190L217 190L217 320L210 320Z", DL)
               + T(220, 300, 219, 260, 221, 214, 1.4, INK)))
    for y in (232, 276):
        o.append(P(f"M209 {y}L246 {y}L246 {y + 8}L209 {y + 8}Z", DL, 2.6) + rivet(215, y + 4, 1.6) + rivet(240, y + 4, 1.6))
    # damper lever
    o.append(L("M212 254L196 248", 3) + C(194, 247, 3.2, INK))
    # flared rim
    o.append(P("M204 188L252 188L248 200L208 200Z", DL, 3.4))
    o.append(P(ell(228, 188, 24, 4.5), DD, 2.6))
    # little gauge + pipe on the roof beside it
    o.append(L("M242 288C256 288 262 296 266 306", 7) + L("M242 288C256 288 262 296 266 306", 3, W))
    o.append(C(270, 318, 12.5, DL, 3.2) + C(270, 318, 8.5, W, 2))
    o.append(T(270, 318, 266, 314, 263, 311, 1.3) + C(270, 318, 1.8, INK))
    return "".join(o)


# ---------------------------------------------------------------------------
# NIB — on the chimney rim, waving at Pip (local coords from the hero cast)
# ---------------------------------------------------------------------------
def nib():
    o = []
    for (x, y, r, a) in ((-52, -40, 5, -40), (50, -60, 4.2, 35), (-44, -74, 3.2, -25)):
        o.append(drop(x, y, r, a))
    o.append(C(-62, -12, 2.4, INK) + C(60, -26, 2.4, INK))
    body = "M0 -58C8 -42 36 -22 36 4C36 26 20 40 0 40C-20 40 -36 26 -36 4C-36 -22 -8 -42 0 -58Z"
    o.append(P(body, INK, 4.5))
    o.append(T(-27, -2, -29, -24, -12, -38, 5.5, W) + C(-28, 7, 2.6, W))
    o.append(T(30, 12, 30, 28, 14, 35, 2.2, W))
    nibd = "M0 -88C5 -78 13 -68 13 -58C13 -51 8 -48 0 -47C-8 -48 -13 -51 -13 -58C-13 -68 -5 -78 0 -88Z"
    o.append(S(nibd, W, 3.6, F("M0 -90L16 -90L16 -45L0 -45Z", DM) + L("M0 -84L0 -63", 2.2) + C(0, -61, 2.8, INK)
               + L("M-12 -54Q0 -49 12 -54", 2.2)))
    # arms: left hand on the rim, right waving
    o.append(L("M-33 14Q-44 22 -46 34", 6.5) + C(-46, 37, 5.4, INK))
    o.append(L("M33 6Q48 0 54 -16", 6.5) + C(55, -20, 5.4, INK))
    o.append(L("M62 -34Q68 -28 66 -20M70 -40Q78 -30 74 -18", 2.4))
    # face, looking right toward Pip
    o.append(C(-12, -2, 13, W) + C(16, -2, 13, W))
    o.append(C(-7, 0.5, 6.6, INK) + C(21, 0.5, 6.6, INK))
    o.append(C(-9.3, -2.2, 2.5, W) + C(18.7, -2.2, 2.5, W) + C(-5, 3, 1, W) + C(23, 3, 1, W))
    o.append(T(-21, -21, -13, -26, -5, -22, 2.6, W) + T(9, -22, 17, -26, 25, -21, 2.6, W))
    o.append(P("M-4 16Q3 28 10 16Q3 19 -4 16Z", W, 0))
    o.append(E(-24, 13, 5.5, 3.2, DL) + E(27, 13, 5.5, 3.2, DL))
    return "".join(o)


# ---------------------------------------------------------------------------
# HANGING POT, CRATE, KETTLE, LADDER, BUNTING
# ---------------------------------------------------------------------------
def pot():
    o = []
    # bracket arm off the shell
    o.append(P("M212 340L150 334L150 341L212 348Z", DL, 3) + P("M208 372L170 341L178 339L210 362Z", DM, 2.6))
    o.append(rivet(204, 344, 1.8) + rivet(203, 366, 1.8))
    o.append(L("M152 341Q147 346 151 351", 2.6))
    for y in (353, 360):
        o.append(E(151, y, 2.4, 3.8, "none", 1.8))
    # bail handle + pot
    o.append(L("M130 378Q130 362 151 364Q172 362 172 378", 2.6))
    body = "M127 378L175 378C177 400 168 414 151 414C134 414 125 400 127 378Z"
    o.append(S(body, W, 4, F("M156 370L184 370L184 420L156 420Z", DM) + F("M120 404L184 404L184 420L120 420Z", HA)
               + L("M128 388Q151 392 175 388", 1.6)))
    o.append(P("M122 372L180 372L180 380L122 380Z", DL, 3) + C(124, 380, 3, W, 2) + C(178, 380, 3, W, 2))
    o.append(P("M131 372C134 362 168 362 171 372Z", W, 2.8) + C(151, 362, 3, INK))
    # soot drips + a curl of steam
    o.append(L("M160 360Q154 352 160 346Q166 340 160 332", 1.6))
    return "".join(o)


def crate():
    o = []
    inner = []
    inner.append(F("M140 440L170 440L170 512L140 512Z", DM))
    inner.append(L("M84 470L168 470M84 488L168 488", 1.8))
    inner.append(L("M90 506L162 452", 2.2))
    inner.append(flicks((92, 455, 150, 505), 9, 71, (4, 8), (170, 190), 1.1))
    inner.append(C(92, 460, 1.5, INK) + C(160, 460, 1.5, INK) + C(92, 497, 1.5, INK) + C(160, 497, 1.5, INK))
    box = "M86 452L164 452L166 506L84 506Z"
    o.append(g(S(box, W, 4, "".join(inner))
               # straps over the top, buckled
               + P("M103 446L113 446L113 512L103 512Z", DD, 2.4) + P("M139 446L149 446L149 512L139 512Z", DD, 2.4)
               + P("M100 476L116 476L116 488L100 488Z", W, 2.2) + L("M108 476L108 488", 1.6)
               + P("M136 476L152 476L152 488L136 488Z", W, 2.2) + L("M144 476L144 488", 1.6)
               # a rolled bedroll on top
               + S("M90 432C90 424 160 424 160 432L160 446C160 454 90 454 90 446Z", W, 3.4,
                   F("M90 440L160 440L160 456L90 456Z", DL) + L("M108 426L108 452M140 426L140 452", 2.6))
               + P(ell(90, 439, 6, 8.5), W, 3) + L("M88 436Q91 439 88 442", 1.4),
               "rotate(-5 125 506)"))
    # tie-down rings on the hull
    o.append(C(102, 516, 4, "none", 2.2) + C(150, 510, 4, "none", 2.2))
    return "".join(o)


def kettle():
    o = []
    o.append(P("M584 494L644 494L640 488L588 488Z", DM, 2.4))
    # spout
    o.append(S("M630 476C640 474 648 466 654 452L660 455C656 470 648 484 634 488Z", W, 3.2,
               F("M640 450L664 450L664 490L640 490Z", DM)))
    body = "M588 489C584 474 588 462 598 458L630 458C640 462 644 474 640 489Z"
    o.append(S(body, W, 3.8, F("M622 452L648 452L648 492L622 492Z", DM) + T(594, 482, 594, 470, 599, 463, 1.6, INK)))
    o.append(P("M596 460C600 450 628 450 632 460Z", DL, 3) + P("M608 451L620 451L618 446L610 446Z", W, 2.2) + C(614, 444, 3, INK))
    # handle
    o.append(L("M596 459C594 438 634 438 632 459", 4) + L("M596 459C594 438 634 438 632 459", 1.4, W))
    # steam curls drifting back
    o.append(L("M657 446Q652 436 660 430Q668 424 662 414", 2) + L("M668 440Q664 432 670 428", 1.6))
    o.append(C(651, 404, 4, W, 1.8) + C(644, 393, 2.6, W, 1.6))
    return "".join(o)


def ladder():
    o = []
    lft = [(549, 494), (548, 540), (545, 590), (540, 640), (536, 684)]
    rgt = [(567, 494), (566, 540), (563, 590), (558, 640), (554, 684)]

    def at(pts, y):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if y0 <= y <= y1:
                return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
        return pts[-1][0]

    # rungs first, ropes over them
    for y in range(512, 684, 21):
        a, b = at(lft, y), at(rgt, y)
        o.append(P(f"M{n(a - 3)} {y - 3}L{n(b + 3)} {y - 2}L{n(b + 3)} {y + 3}L{n(a - 3)} {y + 3}Z", W, 2.4))
    for pts in (lft, rgt):
        d = smooth(pts)
        o.append(L(d, 3.6))
        for y in range(500, 680, 7):
            x = at(pts, y)
            o.append(L(f"M{n(x - 2)} {y}L{n(x + 2)} {y + 4}", 1.1, W))
    # frayed ends + tie knots at the porch
    for x in (536, 554):
        o.append(L(f"M{x} 684L{x - 3} 694M{x} 684L{x} 696M{x} 684L{x + 3} 693", 1.5))
    o.append(C(549, 496, 3.4, W, 2.2) + C(567, 496, 3.4, W, 2.2))
    return "".join(o)


def bunting():
    o = []
    a, c, b = (553, 92), (668, 240), (786, 233)
    o.append(L(f"M{a[0]} {a[1]}Q{c[0]} {c[1]} {b[0]} {b[1]}", 2.2))
    fills = (W, DM, HA, W, DD, DL, W)
    k = len(fills)
    for i, fl in enumerate(fills):
        t = (i + 0.7) / (k + 0.4)
        x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]
        tx = 2 * (1 - t) * (c[0] - a[0]) + 2 * t * (b[0] - c[0])
        ty = 2 * (1 - t) * (c[1] - a[1]) + 2 * t * (b[1] - c[1])
        ang = math.degrees(math.atan2(ty, tx))
        flag = "M-11 0L11 0L-3 26Z"
        o.append(g(P(flag, fl, 2.6) + L("M-11 1.5L11 1.5", 1.2), f"translate({n(x)} {n(y)}) rotate({n(ang)})"))
    return "".join(o)


# ---------------------------------------------------------------------------
# ROOF DECK + PARASOL
# ---------------------------------------------------------------------------
def deck():
    o = []
    # struts down to the shell
    o.append(P(tube((494, 256), (494, 326), 9, 9), DL, 3) + P(tube((470, 290), (498, 258), 7, 7), DM, 2.6))
    o.append(rivet(494, 300, 1.8) + rivet(474, 287, 1.8))
    o.append(P("M486 322L504 322L504 330L486 330Z", DM, 2.4))
    o.append(P(tube((330, 256), (338, 274), 8, 8), DM, 2.6))
    # deck top and front edge
    o.append(P("M300 248L308 240L514 240L508 248Z", DL, 3))
    o.append(P("M300 248L508 248L508 258L300 258Z", W, 3.6))
    o.append(L("".join(f"M{x} 248L{x} 258" for x in range(316, 508, 16)), 1.5))
    o.append(C(302, 253, 1.3, INK) + C(506, 253, 1.3, INK))
    return "".join(o)


def deck_rail():
    o = []
    for x in (308, 500):
        o.append(P(f"M{x - 3} 218L{x + 3} 218L{x + 3} 248L{x - 3} 248Z", W, 2.6) + C(x, 216, 4, W, 2.4))
    rope = "M308 224Q404 246 500 224"
    o.append(L(rope, 3.2) + L(rope, 1.2, W, 'stroke-dasharray="3 4"'))
    return "".join(o)


def parasol_pole():
    return P(tube((430, 190), (430, 84), 5, 5), DL, 2.4)


def parasol():
    o = []
    ax, ay = 430, 22
    tips = [(318, 78), (372, 85), (430, 89), (488, 85), (542, 78)]
    ctrls = [(326, 28), (386, 30), (430, 50), (474, 30), (534, 28)]
    fills = [W, W, DL, DM]

    def hem(p, q, up=8):
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2 - up
        return f"Q{n(mx)} {n(my)} {n(q[0])} {n(q[1])}"

    for i in range(4):
        p, q = tips[i], tips[i + 1]
        d = (f"M{ax} {ay}Q{n(ctrls[i][0])} {n(ctrls[i][1])} {n(p[0])} {n(p[1])}" + hem(p, q)
             + f"Q{n(ctrls[i + 1][0])} {n(ctrls[i + 1][1])} {ax} {ay}Z")
        inner = ""
        if i == 1:
            inner += (P("M392 52L414 47L418 68L396 72Z", DM, 2) + stitches("M394 55L412 51M398 69L416 66")
                      + L("M390 50L394 48M393 61L389 63M418 58L422 57", 1.3))
        if i == 3:
            inner += P("M500 50L520 56L516 72L498 66Z", W, 2) + stitches("M502 53L518 58M500 63L514 68")
        if i == 0:
            inner += flicks((330, 40, 370, 74), 6, 81, (4, 7), (60, 80), 1.2)
        o.append(S(d, fills[i], 3.6, inner))
    # silhouette outline over the panels
    outline = (f"M{tips[0][0]} {tips[0][1]}Q{ctrls[0][0]} {ctrls[0][1]} {ax} {ay}"
               f"Q{ctrls[4][0]} {ctrls[4][1]} {tips[4][0]} {tips[4][1]}")
    for i in range(4, 0, -1):
        outline += hem(tips[i], tips[i - 1])
    o.append(L(outline + "Z", 4.6))
    # rib tips and finial
    for (x, y) in tips:
        o.append(C(x, y + 1, 2.6, INK))
    o.append(P("M426 22L434 22L432 16L428 16Z", DL, 2.4) + C(430, 14, 3.4, W, 2.4))
    # fringe under the hem flickers in the wind
    o.append(L("M330 80L327 86M344 80L341 87M392 85L389 91M455 86L452 92M512 82L509 89M528 80L525 86", 1.5))
    return "".join(o)


# ---------------------------------------------------------------------------
# PIP — at the helm (local coords match the hero-cast drawing: seat ~ hips at 0,0,
#        boots on the deck at y 88); hand on the wheel, lantern held out to the left
# ---------------------------------------------------------------------------
def pip_body():
    o = []
    o.append(E(4, 86, 46, 5, DM))  # contact shadow on the deck

    # lantern arm (behind torso)
    sleeve = "M-18 -57C-32 -66 -48 -73 -62 -75Q-68 -64 -64 -51C-50 -51 -36 -45 -24 -35Z"
    o.append(S(sleeve, W, 4.5,
               F("M-24 -44C-38 -50 -52 -55 -66 -57L-66 -48C-50 -48 -36 -42 -24 -33Z", DM)
               + L("M-40 -70Q-45 -60 -42 -47", 2.2) + L("M-28 -62Q-32 -54 -30 -42", 1.8)))
    cuff = "M-61 -77Q-69 -64 -63 -50L-72 -49Q-78 -63 -70 -78Z"
    o.append(S(cuff, W, 3.5, "".join(L(f"M{x} -82L{x - 2} -44", 1.4) for x in (-63, -66.5, -70, -73.5))))

    # brass lantern hanging from the fist
    lx = -82
    rays = "".join(ray(lx, -26, a, 21, 29 + (a % 3) * 2, 2.8) for a in (95, 128, 160, 192, 222, 60, 28))
    o.append(rays)
    o.append(L(f"M{lx - 8} -45Q{lx - 8} -60 {lx} -61Q{lx + 8} -60 {lx + 8} -45", 2.6))
    o.append(S(f"M{lx - 11} -37L{lx + 11} -37L{lx + 7} -44Q{lx} -49 {lx - 7} -44Z", W, 3,
               F(f"M{lx} -50L{lx + 12} -50L{lx + 12} -36L{lx} -36Z", DM)))
    o.append(C(lx, -48.5, 2.6, W, 2))
    o.append(P(f"M{lx - 13} -37L{lx + 13} -37L{lx + 13} -33L{lx - 13} -33Z", DD, 2.6))
    o.append(P(f"M{lx - 10} -33L{lx + 10} -33L{lx + 10} -15L{lx - 10} -15Z", W, 3))
    o.append(P(f"M{lx} -31C{lx + 5} -25 {lx + 6} -21 {lx + 3} -18C{lx + 1} -16.5 {lx - 1} -16.5 {lx - 3} -18"
               f"C{lx - 6} -21 {lx - 5} -25 {lx} -31Z", W, 1.8))
    o.append(P(f"M{lx} -25C{lx + 2} -22 {lx + 2.4} -20 {lx + 1} -18.5C{lx} -18 {lx - 1} -18 {lx - 1.4} -18.6"
               f"C{lx - 2.4} -20 {lx - 2} -22 {lx} -25Z", INK, 0))
    o.append(L(f"M{lx - 6} -33L{lx - 6} -15M{lx + 6} -33L{lx + 6} -15", 1.6))
    o.append(P(f"M{lx - 13} -15L{lx + 13} -15L{lx + 10} -9L{lx - 10} -9Z", DM, 2.8))
    o.append(T(lx - 8, -30, lx - 9, -24, lx - 8, -19, 1.6, W))
    o.append(S("M-73 -73C-80 -78 -90 -75 -91 -66C-92 -57 -84 -53 -76 -55C-71 -59 -70 -67 -73 -73Z", W, 4,
               F("M-82 -60C-86 -54 -78 -52 -74 -56L-72 -64Z", DL)))
    o.append(P("M-77 -72C-78 -79 -86 -81 -88 -75C-86 -72 -81 -70 -77 -72Z", W, 3))
    o.append(L("M-86 -66Q-82 -64 -78 -66M-87 -61Q-83 -59 -79 -61", 1.6))

    # legs and big lace-up boots, planted on the deck
    def leg(mirror=1):
        s = mirror
        out = []
        shin = f"M{-27 * s} 9L{-13 * s} 9L{-14 * s} 40L{-26 * s} 40Z"
        out.append(S(shin, W, 4, F(f"M{-18 * s} 6L{-11 * s} 6L{-11 * s} 44L{-18 * s} 44Z", DL) if s < 0 else
                     F(f"M{-27 * s} 6L{-20 * s} 6L{-20 * s} 44L{-27 * s} 44Z", DL)))
        out.append(L(f"M{-24 * s} 14Q{-20 * s} 17 {-16 * s} 14", 2))
        sock = f"M{-29 * s} 33Q{-20 * s} 37 {-11 * s} 33L{-10 * s} 46L{-30 * s} 46Z"
        out.append(S(sock, W, 3.6, L(f"M{-26 * s} 38L{-27 * s} 46M{-20 * s} 39L{-20 * s} 46M{-14 * s} 38L{-13 * s} 46", 1.4)))
        boot = (f"M{-32 * s} 44L{-9 * s} 44C{-7 * s} 54 {-5 * s} 62 {-5 * s} 70C{-5 * s} 81 {-16 * s} 85 {-27 * s} 84"
                f"C{-38 * s} 83 {-42 * s} 75 {-40 * s} 66C{-38 * s} 58 {-34 * s} 52 {-32 * s} 44Z")
        lace = "".join(L(f"M{-27 * s} {y}L{-15 * s} {y + 4}M{-15 * s} {y}L{-27 * s} {y + 4}", 1.6) for y in (48, 54, 60))
        out.append(S(boot, W, 4.5, F(f"M{-14 * s} 40L{4 * s} 40L{4 * s} 90L{-14 * s} 90Z", DM)
                     + lace + L(f"M{-38 * s} 68Q{-22 * s} 74 {-6 * s} 67", 2.2)))
        out.append(P(f"M{-40 * s} 70C{-41 * s} 81 {-35 * s} 88 {-24 * s} 88C{-13 * s} 88 {-5 * s} 83 {-4 * s} 73"
                     f"C{-9 * s} 79 {-17 * s} 81 {-24 * s} 81C{-31 * s} 81 {-37 * s} 77 {-40 * s} 70Z", INK, 2.5))
        out.append(P(f"M{-33 * s} 42L{-8 * s} 42L{-8 * s} 48L{-33 * s} 48Z", W, 3.2))
        return "".join(out)

    o.append(leg(1))
    o.append(leg(-1))

    # cargo shorts
    shorts = "M-33 -8C-36 4 -32 13 -21 14L-5 14C-3 9 3 9 5 14L21 14C32 13 36 4 33 -8Z"
    o.append(S(shorts, W, 4.5,
               F("M12 -10L38 -10L38 16L12 16Z", HA)
               + L("M-13 2Q-8 8 -10 13", 2) + L("M10 3Q6 8 8 13", 2)
               + P("M20 -1L31 -2L31 9L21 9Z", W, 2.4) + L("M20 2L31 1", 2)
               + stitches("M-28 10Q-20 12 -12 11")))

    # puffy jacket
    jacket = "M-26 -59Q-38 -54 -36 -41Q-42 -33 -38 -22Q-42 -12 -34 -2L34 -2Q42 -12 38 -22Q42 -33 36 -41Q38 -54 26 -59Z"
    teeth = "".join(L(f"M-2 {y}L2 {y}", 1.3) for y in range(-52, -4, 4))
    o.append(S(jacket, W, 5,
               F("M17 -62Q40 -55 38 -41Q44 -33 40 -22Q44 -12 36 0L21 0Q28 -12 24 -22Q28 -34 17 -62Z", DM)
               + F("M-40 -10Q0 -4 40 -10L40 0L-40 0Z", DL)
               + L("M-36 -41Q0 -35 36 -41", 2.6) + L("M-38 -22Q0 -16 38 -22", 2.6)
               + T(-30, -38, -18, -36, -8, -36.5, 1.8) + T(10, -19.5, 22, -19, 33, -20, 1.8)
               + L("M0 -56L0 -2", 2.6) + teeth
               + P("M-31 -17L-12 -18L-12 -5Q-21 -3 -31 -5Z", W, 2.4) + L("M-31 -13L-12 -14", 2)
               + stitches("M-29 -10L-14 -11") + C(-21.5, -15.5, 1.5, INK)
               + P("M12 -18L31 -17L31 -5Q21 -3 12 -5Z", W, 2.4) + L("M12 -14L31 -13", 2)
               + stitches("M14 -10L29 -9") + C(21.5, -15.5, 1.5, INK)))
    o.append(P("M-3 -50L3 -50L3 -43L-3 -43Z", W, 1.8))

    # steering arm reaching to the wheel rim
    sl2 = "M23 -57C40 -54 48 -38 49 -18L35 -15C34 -28 31 -38 25 -44Z"
    o.append(S(sl2, W, 4.5, F("M38 -60L56 -60L56 -14L40 -14C42 -30 42 -44 38 -60Z", DM)
               + L("M29 -38Q38 -36 47 -40", 2.2)))
    o.append(S("M34 -20L49 -22L50 -12L35 -10Z", W, 3.4,
               "".join(L(f"M{x} -24L{x + 1} -8", 1.4) for x in (37, 40.5, 44, 47.5))))

    # striped scarf: tail streaming back (left) in the wind, front tail, wrap
    tail = ("M-17 -62C-34 -72 -46 -84 -62 -88C-78 -92 -90 -88 -106 -98L-110 -84C-96 -76 -82 -80 -66 -74"
            "C-50 -68 -40 -56 -26 -48Z")
    bands = "".join(F(f"M{x} -104L{x + 12} -104L{x + 9} -40L{x - 3} -40Z", DD) for x in (-44, -70, -96))
    o.append(S(tail, W, 4, bands + L("M-30 -58C-42 -66 -52 -76 -66 -80", 1.6) + L("M-78 -84Q-90 -84 -100 -90", 1.6)))
    o.append(L("M-108 -96L-117 -101M-109 -91L-119 -93M-110 -86L-118 -85", 2))
    o.append(T(-118, -112, -128, -114, -138, -108, 2.2) + T(-122, -78, -130, -76, -138, -80, 2))
    ftail = "M-25 -52C-29 -40 -29 -28 -29 -15L-14 -17C-14 -29 -12 -41 -10 -52Z"
    o.append(S(ftail, W, 4, F("M-34 -46L-5 -46L-5 -39L-34 -39Z", DD) + F("M-34 -33L-5 -33L-5 -26L-34 -26Z", DD)))
    o.append(L("M-27 -15L-28 -9M-23 -15.5L-23 -9.5M-19 -16L-18 -10", 2))
    wrap = "M-31 -63C-14 -55 14 -55 31 -63L31 -49C14 -41 -14 -41 -31 -49Z"
    o.append(S(wrap, W, 4.5, "".join(F(f"M{x} -66L{x + 9} -66L{x + 8} -40L{x - 1} -40Z", DD) for x in (-24, -5, 14))
               + L("M-30 -55C-14 -48 14 -48 30 -55", 1.6)))

    # ears, face (features nudged right: he is looking where he steers)
    fx = 4
    o.append(S(circ(-29, -79, 6), W, 3.5, F(circ(-29, -79, 6), DL)) + L("M-30 -82Q-26 -79 -30 -76", 1.6))
    o.append(S(circ(29, -79, 6), W, 3.5, F(circ(29, -79, 6), DM)) + L("M30 -82Q26 -79 30 -76", 1.6))
    o.append(S(circ(0, -82, 29), W, 5,
               F(circ(0, -82, 29), DL) + P(circ(-7, -87, 30), W, 0)
               + F("M-34 -96C-12 -100 12 -100 34 -96L34 -85C12 -89 -12 -89 -34 -85Z", DM)))
    o.append(E(-11 + fx, -74, 4.6, 6.2, INK) + E(11 + fx, -74, 4.6, 6.2, INK))
    o.append(C(-12.6 + fx, -76.6, 1.9) + C(9.4 + fx, -76.6, 1.9) + C(-9.6 + fx, -71.6, 0.8) + C(12.4 + fx, -71.6, 0.8))
    o.append(T(-17 + fx, -83, -11 + fx, -87, -5 + fx, -84.5, 2.4) + T(5 + fx, -84.5, 11 + fx, -87, 17 + fx, -83, 2.4))
    o.append(L(f"M{-2.5 + fx} -67Q{fx} -64.5 {2.5 + fx} -67", 2))
    o.append(P(f"M{-8.5 + fx} -61Q{fx} -49 {8.5 + fx} -61Q{fx} -59 {-8.5 + fx} -61Z", INK, 0))
    o.append(P(f"M{-4 + fx} -56.5Q{fx} -53 {4 + fx} -56.5Q{fx} -58.5 {-4 + fx} -56.5Z", W, 0))
    o.append(E(-19.5 + fx, -65.5, 6, 3.8, DL) + E(19.5 + fx, -65.5, 6, 3.8, DL))
    o.append("".join(C(x + fx, y, 0.95, INK) for x, y in
                     ((-23, -71), (-19.5, -72.5), (-21.5, -68.8), (19.5, -72.5), (23, -71), (21.5, -68.8))))
    # hair tufts under the cuff
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
    for gx in (-10, 14):
        o.append(S(circ(gx, -115, 10.5), W, 4.2, F(circ(gx + 4, -111, 9), DL)))
        o.append(L(f"M{gx - 5} -118Q{gx - 3} -121.5 {gx + 1} -121.5", 2, W))
        o.append(C(gx, -115, 7, "none", 1.6))
    o.append(L("M0.5 -116Q2 -118 3.5 -116", 3.4))
    cuffb = "M-36 -101C-12 -107 12 -107 36 -101L36 -88C12 -94 -12 -94 -36 -88Z"
    o.append(S(cuffb, W, 4.5,
               "".join(L(f"M{x} -110L{x} -84", 1.5) for x in range(-32, 36, 5))
               + F("M22 -112L40 -112L40 -84L22 -84Z", DM)))
    return "".join(o)


WHEEL = (68, 0)


def helm_post():
    x, y = WHEEL
    o = [S(f"M{x - 6} {y}L{x + 6} {y}L{x + 10} 82L{x - 10} 82Z", W, 4,
           F(f"M{x + 1} {y - 4}L{x + 14} {y - 4}L{x + 14} 86L{x + 1} 86Z", DM)
           + L(f"M{x - 7} 30L{x + 8} 30M{x - 8} 56L{x + 9} 56", 2))]
    o.append(P(f"M{x - 18} 82L{x + 18} 82L{x + 22} 90L{x - 22} 90Z", DL, 3.6))
    o.append(rivet(x - 12, 86, 2) + rivet(x + 12, 86, 2))
    return "".join(o)


def wheel():
    """ship's wheel seen three-quarter: an ellipse rim with 8 handled spokes"""
    x, y = WHEEL
    rx, ry = 22, 34
    o = []
    angs = [i * 45 + 10 for i in range(8)]
    # handles + spokes (behind the rim)
    for a in angs:
        t = math.radians(a)
        ca, sa = math.cos(t), math.sin(t)
        x0, y0 = x + ca * rx * 0.3, y + sa * ry * 0.3
        x1, y1 = x + ca * rx * 1.0, y + sa * ry * 1.0
        x2, y2 = x + ca * rx * 1.42, y + sa * ry * 1.42
        o.append(L(f"M{n(x0)} {n(y0)}L{n(x1)} {n(y1)}", 5) + L(f"M{n(x0)} {n(y0)}L{n(x1)} {n(y1)}", 1.6, W))
        o.append(P(tube((x1, y1), (x2, y2), 6.5, 4.5), W, 2.6))
        o.append(C(x2, y2, 3.6, W, 2.4))
    # rim: thick ring
    ring = ell(x, y, rx + 4, ry + 4) + ell(x, y, rx - 3, ry - 3)
    o.append(f'<path d="{ring}" fill="{DL}" fill-rule="evenodd" stroke="{INK}" stroke-width="3.4"/>')
    o.append(L(f"M{n(x - rx - 0.5)} {y}A{n(rx + 0.5)} {n(ry + 0.5)} 0 0 1 {n(x + rx * 0.4)} {n(y - ry * 0.95)}", 1.2, W))
    # hub
    o.append(C(x, y, 8, DM, 3) + C(x, y, 3.4, W, 2) + C(x, y, 1.2, INK))
    return "".join(o)


def pip_hand():
    """fist gripping the wheel rim (drawn over it)"""
    o = [S("M34 -11C34 -16 50 -17 53 -10C56 -3 55 5 51 7C47 8 43 4 41 1C37 -2 34 -6 34 -11Z", W, 4,
           F("M47 -14L58 -14L58 9L47 9Z", DL))]
    o.append(L("M46 -2Q48 3 47 6M42 -4Q43 1 41 3", 1.8))
    return "".join(o)


# ---------------------------------------------------------------------------
# HEAD — riveted dome head, goggled eyes on conduit stalks, strapped headlamp
# ---------------------------------------------------------------------------
def stalk(base, ctrl, tip, w0, w1, seed):
    pts = qpts(base, ctrl, tip, 18)
    d = poly_tube(pts, w0, w1)
    inner = []
    # conduit rings
    for i in range(1, 18):
        (x0, y0), (x1, y1) = pts[i - 1], pts[i]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        w = (w0 + (w1 - w0) * i / 18) / 2 + 2
        inner.append(L(f"M{n(x1 + nx * w)} {n(y1 + ny * w)}Q{n(x1 + dx / ln * 2)} {n(y1 + dy / ln * 2)} {n(x1 - nx * w)} {n(y1 - ny * w)}", 1.5))
    shade = poly_tube([(x + 4, y) for x, y in pts], w0 * 0.5, w1 * 0.5)
    return S(d, W, 3.6, F(shade, DM) + "".join(inner))


def eye(cx, cy, r, px, py):
    o = []
    # goggle ring
    ring = circ(cx, cy, r + 9) + circ(cx, cy, r + 1)
    o.append(C(cx, cy, r + 1, W))
    o.append(f'<path d="{ring}" fill="{DL}" fill-rule="evenodd" stroke="{INK}" stroke-width="3.6"/>')
    for i in range(6):
        a = math.radians(i * 60 + 30)
        o.append(C(cx + math.cos(a) * (r + 5), cy + math.sin(a) * (r + 5), 1.6, INK))
    # eyeball
    inner = [F(circ(cx + r * 0.35, cy + r * 0.45, r * 0.9), DL), P(circ(cx - r * 0.15, cy - r * 0.2, r * 0.95), W, 0)]
    inner.append(E(px, py, r * 0.5, r * 0.58, INK))
    inner.append(C(px - r * 0.18, py - r * 0.22, r * 0.17, W) + C(px + r * 0.2, py + r * 0.2, r * 0.07, W))
    # happy lower lid
    inner.append(L(f"M{n(cx - r)} {n(cy + r * 0.62)}Q{n(cx)} {n(cy + r * 0.28)} {n(cx + r)} {n(cy + r * 0.62)}", 2.4))
    o.append(S(circ(cx, cy, r), W, 3.6, "".join(inner)))
    # glass glint across the goggle
    o.append(L(f"M{n(cx - r * 0.75)} {n(cy - r * 0.3)}Q{n(cx - r * 0.6)} {n(cy - r * 0.7)} {n(cx - r * 0.25)} {n(cy - r * 0.8)}", 2.6, W))
    return "".join(o)


HEAD = ("M752 330C750 282 790 256 825 258C870 262 894 300 888 342C884 378 860 400 822 400"
        "C786 400 754 380 752 330Z")


def head():
    o = []
    # stalks behind the head
    o.append(stalk((846, 272), (850, 238), (858, 200), 15, 12, 1))
    o.append(stalk((796, 276), (786, 244), (782, 212), 17, 13, 2))
    # goggle strap linking the eyes
    o.append(P("M806 176L834 168L836 182L808 190Z", DD, 2.4))
    o.append(eye(858, 180, 26, 865, 184))
    o.append(eye(780, 190, 29, 788, 195))
    inner = []
    inner.append(F(circ(838, 345, 70), DM))
    inner.append(P(circ(810, 318, 66), DL, 0))
    inner.append(P(circ(798, 306, 58), W, 0))
    # helmet seam + rivets
    inner.append(L("M790 262C772 300 774 360 800 402", 2.4))
    inner.append("".join(rivet(x, y, 1.8) for x, y in ((786, 280), (779, 306), (778, 332), (783, 358), (792, 382))))
    # collar band at the base
    inner.append(L("M760 360C790 392 850 396 884 364", 2.6))
    inner.append("".join(C(760 + i * 15.5, 372 + math.sin(i / 8 * math.pi) * 22, 1.5, INK) for i in range(9)))
    inner.append(flicks((770, 270, 800, 300), 4, 91, (3, 6), (50, 80), 1.2))
    o.append(S(HEAD, W, 5, "".join(inner)))
    o.append(taper([((889, 318), (891, 372), (862, 400), (822, 401)), ((822, 401), (800, 401), (784, 395), (772, 386))], 8))
    # headlamp strap round the dome
    o.append(P("M755 300C780 286 840 282 884 290L886 302C840 294 780 298 757 312Z", W, 3) + stitches("M762 304C790 292 840 289 880 296"))
    # headlamp
    o.append(S("M858 280L884 276L888 318L860 314Z", W, 3.6, F("M874 270L894 270L894 322L874 322Z", DM)
               + L("M866 280L868 314", 1.6)))
    o.append(P(ell(890, 297, 8.5, 21), W, 3.6) + P(ell(890, 297, 4.5, 14), DL, 1.8))
    o.append(T(887, 286, 886, 292, 887, 299, 1.6, W))
    o.append(rivet(864, 296, 1.8))
    rays = "".join(ray(897, 297, a, 18, 30 + (abs(a) % 4) * 3, 2.4) for a in (-34, -17, 0, 17, 34))
    o.append(rays)
    # face: wide happy smile, cheek
    o.append(P("M812 352Q846 392 878 344Q848 362 812 352Z", INK, 2.6))
    o.append(P("M830 366Q846 378 860 364Q846 368 830 366Z", DM, 0))
    o.append(L("M807 348Q810 352 813 356M875 340Q878 344 879 349", 2.2))
    o.append(E(806, 366, 9, 5.5, DL) + E(882, 356, 5, 4.5, DL))
    return "".join(o)


# ---------------------------------------------------------------------------
DEFS = """<defs>
<filter id="ink" x="-3%" y="-3%" width="106%" height="106%">
<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="halo" x="-4%" y="-4%" width="108%" height="108%">
<feMorphology in="SourceAlpha" operator="dilate" radius="3.2" result="d"/>
<feFlood flood-color="#fff" result="w"/>
<feComposite in="w" in2="d" operator="in" result="wd"/>
<feMerge><feMergeNode in="wd"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<pattern id="dots-light" width="7" height="7" patternUnits="userSpaceOnUse"><rect width="7" height="7" fill="#fff"/><circle cx="3.5" cy="3.5" r="1.05" fill="#111"/></pattern>
<pattern id="dots-mid" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><circle cx="3" cy="3" r="1.55" fill="#111"/></pattern>
<pattern id="dots-dark" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="#fff"/><circle cx="2.5" cy="2.5" r="1.95" fill="#111"/></pattern>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><line x1="0" y1="0" x2="0" y2="6" stroke="#111" stroke-width="1.4"/></pattern>
<pattern id="crosshatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#fff"/><path d="M0 0V7M0 0H7" stroke="#111" stroke-width="1.3"/></pattern>
</defs>"""

PIP_TR = "translate(385 190) scale(0.66)"
PARASOL_TILT = "rotate(6 430 190)"
NIB_TR = "translate(228 167) scale(0.56)"


def main():
    parts = [
        ("ground", ground()),
        ("smoke", smoke()),
        ("far-legs", far_legs()),
        ("shell", shell() + porthole() + door()),
        ("chimney", chimney()),
        ("nib", g(nib(), NIB_TR)),
        ("hanging-pot", pot()),
        ("roof-deck", deck()),
        ("parasol-pole", g(parasol_pole(), PARASOL_TILT)),
        ("pip", g(pip_body() + helm_post() + wheel() + pip_hand(), PIP_TR)),
        ("deck-rail", deck_rail()),
        ("parasol", g(parasol(), PARASOL_TILT)),
        ("bunting", bunting()),
        ("hull", hull() + hull_pipe() + saddle() + porch()),
        ("crate", crate()),
        ("kettle", kettle()),
        ("ladder", ladder()),
        ("near-legs", near_legs()),
        ("head", g(head(), "translate(820 330) scale(1.08) translate(-820 -330)")),
        ("ground-tufts", ground_front()),
    ]
    body = "".join(f"<!-- {name} --><g id=\"{name}\">{content}</g>" for name, content in parts)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 800" width="1000" height="800" role="img">'
           '<title>The snail caravan: a riveted mechanical snail on four jointed legs, its spiral shell made into '
           'a little house with a porthole, door and smoking stovepipe; Pip steers at a ship\'s wheel under a '
           'patched parasol while Nib waves from the chimney</title>'
           + DEFS
           + '<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)"><g filter="url(#halo)">'
           + body + "</g></g></svg>")
    with open(OUT, "w") as fh:
        fh.write(svg)
    print(f"wrote {os.path.normpath(OUT)} ({len(svg) / 1024:.0f} KB)")


main()
