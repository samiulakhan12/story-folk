#!/usr/bin/env python3
"""Builds the snail caravan for the Storyfolk site: three files in ../assets/ (relative to this script)

  caravan.svg ......... the complete still: motion off, the no-JS fallback, and the reference
  caravan-base.svg .... the still minus every moving part, filters kept; it never changes
  caravan-motion.svg .. ONLY the moving parts (same viewBox, transparent), animated by an internal
                        <style>; every class and @keyframes name starts with cv-
At rest (animation: none) base + motion reproduce the still.

Standard library only (math, os, re, bisect, random). Run from any directory:
    python3 tools/generate-caravan.py

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

Moving pieces are wrapped in <!--mv:name--> tags while the drawing is built: the still strips the
tags (byte-identical to the pre-motion file), the base drops the tagged pieces, and the motion
layer re-uses them. Motion layer (class: cycle):
  smoke ............... cv-smoke0-8 (5.5-9 s): each puff drifts along one spine from behind Nib to the
                        upper left, fading in behind its drawn spot and out ahead of it; cv-ring0-2 rings
  Nib ................. cv-nibwave (5.2 s, three waves then a rest), cv-nibblink, cv-nibglance + sf-look,
                        cv-nibdrop0-2 (the ink drops bob)
  hanging pot ......... cv-pot (5.6 s pendulum from the hook), cv-potsteam
  Pip ................. cv-lantern (4.6 s swing from the fist) with cv-glow, cv-scarf (the tail beyond
                        SCARF_CUT flutters), cv-pipblink, cv-pipglance + sf-look
  parasol ............. cv-parasol (7.4 s gusts about the pole's seam above the wheel), cv-fringe0/1
  bunting ............. cv-bunting (locked to the parasol so the knot stays on the rib tip), cv-flag0-6
  kettle .............. cv-steam, cv-puffling0/1
  lifted front leg .... cv-step (6.6 s: the shin paws down and up from the knee), cv-dust0/1
  head ................ cv-stalkr/l (6.4 s sway), cv-blink (double blink), cv-glance + sf-look,
                        cv-headlamp (rays pulse)
"""
import bisect
import math
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
OUT = os.path.join(ASSETS, "caravan.svg")
OUT_BASE = os.path.join(ASSETS, "caravan-base.svg")
OUT_MOTION = os.path.join(ASSETS, "caravan-motion.svg")

INK = "#111"
W = "#fff"
DL, DM, DD, HA, CH = ("url(#dots-light)", "url(#dots-mid)", "url(#dots-dark)",
                      "url(#hatch)", "url(#crosshatch)")

_n = [0]


def nid():
    _n[0] += 1
    return f"c{_n[0]}"


def mark(name, s):
    """tag a moving piece in the full drawing; the still strips the tags, the base drops the piece"""
    return f"<!--mv:{name}-->{s}<!--/mv:{name}-->"


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
PUFFS = ((40, 44, 21, 1), (72, 32, 18, 9), (46, 74, 16, 10), (88, 62, 27, 2),     # old cloud drifting off
         (126, 96, 18, 3), (128, 120, 12, 11), (150, 110, 15, 8),                  # middle cloud
         (180, 140, 11, 4), (198, 161, 8, 5))                                      # fresh puffs
SMOKE_BUBBLES = ((50, 98, 3, 1.8), (172, 100, 2.2, 1.5), (118, 128, 1.8, 1.4))      # x, y, r, stroke


def smoke():
    o = []
    for i, (x, y, r, s) in enumerate(PUFFS):
        d = fuzz(x, y, r, 9, 0.3, seed=s, bulge=0.42)
        o.append(mark(f"puff{i}", S(d, W, 3.4, F(circ(x + r * 0.45, y + r * 0.4, r * 0.95), DL) + P(circ(x - r * 0.2, y - r * 0.2, r * 0.95), W, 0)
                 + L(f"M{n(x - r * 0.5)} {n(y - r * 0.1)}Q{n(x - r * 0.3)} {n(y - r * 0.55)} {n(x + r * 0.15)} {n(y - r * 0.55)}", 1.5))))
    o.append(mark("curl0", L("M15 80Q9 70 17 62", 1.8)) + mark("curl1", L("M122 52Q116 44 124 36", 1.6)))
    for i, (x, y, r, sw) in enumerate(SMOKE_BUBBLES):
        o.append(mark(f"bub{i}", C(x, y, r, W, sw)))
    return "".join(o)


# ---------------------------------------------------------------------------
# LEGS
# ---------------------------------------------------------------------------
def leg(hip, knee, ankle, padc, far=False, lifted=False, rot=0, name=None):
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
    shin_at = len(o)
    o.append(S(sh, body, sw, inner))
    if not far:
        o.append(coil((knee[0] + dx * 0.2, knee[1] + dy * 0.2), (knee[0] + dx * 0.8, knee[1] + dy * 0.8), 6, 17, 2.4))
    # ankle ball + pad
    o.append(pad(padc[0], padc[1], 40 if not far else 33, 11.5 if not far else 9.5, 9 if not far else 7, rot,
                 W if not far else DL, DM if not far else DD, 3.6 if not far else 3.2))
    o.append(C(ankle[0], ankle[1], 10 if not far else 8.5, DL if not far else DM, 3))
    o.append(C(ankle[0] - 2, ankle[1] - 2, 2.2, W))
    knee_j = joint(knee[0], knee[1], 18 if not far else 14, DL if not far else DM)
    if name:  # the shin swings from the knee: shin plate, coil, pad and ankle move together
        o[shin_at:] = [mark(f"{name}-shin", "".join(o[shin_at:]))]
        knee_j = mark(f"{name}-knee", knee_j)
    # knee joint
    o.append(knee_j)
    return "".join(o)


def far_legs():
    o = [leg((318, 566), (368, 638), (346, 701), (344, 714), far=True),
         leg((640, 566), (682, 634), (657, 699), (655, 713), far=True)]
    return "".join(o)


DUST = ((716, 708, 2.2), (732, 718, 1.6), (746, 706, 1.8), (724, 730, 1.3))   # falling from the lifted pad


def near_legs():
    o = []
    o.append(leg((255, 574), (306, 650), (280, 716), (278, 731)))
    o.append(joint(255, 574, 24))
    # lifted front leg, mid-step
    o.append(leg((612, 574), (692, 610), (720, 664), (727, 680), lifted=True, rot=-16, name="front"))
    o.append(joint(615, 574, 24))
    # motion swooshes + dust falling from the lifted pad
    o.append(mark("swoosh", T(744, 652, 760, 660, 772, 676, 1.8) + T(752, 640, 770, 648, 782, 662, 1.5)))
    o.append("".join(mark(f"dust{i}", C(x, y, r, INK)) for i, (x, y, r) in enumerate(DUST)))
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
NIB_DROPS = ((-52, -40, 5, -40), (50, -60, 4.2, 35), (-44, -74, 3.2, -25))


def nib():
    o = []
    for i, (x, y, r, a) in enumerate(NIB_DROPS):
        o.append(mark(f"nib-drop{i}", drop(x, y, r, a)))
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
    o.append(mark("nib-arm", L("M33 6Q48 0 54 -16", 6.5) + C(55, -20, 5.4, INK)
                  + L("M62 -34Q68 -28 66 -20M70 -40Q78 -30 74 -18", 2.4)))
    # face, looking right toward Pip
    o.append(mark("nib-eyes", C(-12, -2, 13, W) + C(16, -2, 13, W) + C(-7, 0.5, 6.6, INK) + C(21, 0.5, 6.6, INK)
                  + C(-9.3, -2.2, 2.5, W) + C(18.7, -2.2, 2.5, W) + C(-5, 3, 1, W) + C(23, 3, 1, W)))
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
    swing_at = len(o)
    for y in (353, 360):
        o.append(E(151, y, 2.4, 3.8, "none", 1.8))
    # bail handle + pot
    o.append(L("M130 378Q130 362 151 364Q172 362 172 378", 2.6))
    body = "M127 378L175 378C177 400 168 414 151 414C134 414 125 400 127 378Z"
    o.append(S(body, W, 4, F("M156 370L184 370L184 420L156 420Z", DM) + F("M120 404L184 404L184 420L120 420Z", HA)
               + L("M128 388Q151 392 175 388", 1.6)))
    o.append(P("M122 372L180 372L180 380L122 380Z", DL, 3) + C(124, 380, 3, W, 2) + C(178, 380, 3, W, 2))
    o.append(P("M131 372C134 362 168 362 171 372Z", W, 2.8) + C(151, 362, 3, INK))
    o[swing_at:] = [mark("pot-swing", "".join(o[swing_at:]))]   # chain, bail, pot and lid swing from the hook
    # soot drips + a curl of steam
    o.append(mark("pot-steam", L("M160 360Q154 352 160 346Q166 340 160 332", 1.6)))
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
    o.append(mark("k-steam", L("M657 446Q652 436 660 430Q668 424 662 414", 2) + L("M668 440Q664 432 670 428", 1.6)))
    o.append(mark("k-bub0", C(651, 404, 4, W, 1.8)) + mark("k-bub1", C(644, 393, 2.6, W, 1.6)))
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


BUNTING = ((553, 92), (668, 240), (786, 233))   # tied to the parasol rib tip, sagging, tied to the eye stalk


def bunting_flags():
    """(x, y, angle, fill) of each pennant: hung from the string, rotated to its slope"""
    a, c, b = BUNTING
    fills = (W, DM, HA, W, DD, DL, W)
    k = len(fills)
    out = []
    for i, fl in enumerate(fills):
        t = (i + 0.7) / (k + 0.4)
        x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]
        tx = 2 * (1 - t) * (c[0] - a[0]) + 2 * t * (b[0] - c[0])
        ty = 2 * (1 - t) * (c[1] - a[1]) + 2 * t * (b[1] - c[1])
        out.append((x, y, math.degrees(math.atan2(ty, tx)), fl))
    return out


def flag_art(fl):
    return P("M-11 0L11 0L-3 26Z", fl, 2.6) + L("M-11 1.5L11 1.5", 1.2)


def bunting():
    o = []
    a, c, b = BUNTING
    o.append(mark("b-string", L(f"M{a[0]} {a[1]}Q{c[0]} {c[1]} {b[0]} {b[1]}", 2.2)))
    for i, (x, y, ang, fl) in enumerate(bunting_flags()):
        o.append(mark(f"flag{i}", g(flag_art(fl), f"translate({n(x)} {n(y)}) rotate({n(ang)})")))
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


FRINGE = ((330, 80, 327, 86), (344, 80, 341, 87), (392, 85, 389, 91), (455, 86, 452, 92), (512, 82, 509, 89),
          (528, 80, 525, 86))


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
    o.append(mark("fringe", L("".join(f"M{a} {b}L{c} {d}" for a, b, c, d in FRINGE), 1.5)))
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
    lantern_at = len(o)
    o.append(mark("lantern-rays", rays))
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
    o[lantern_at:] = [mark("lantern", "".join(o[lantern_at:]))]   # swings from the fist
    o.append(mark("fist", S("M-73 -73C-80 -78 -90 -75 -91 -66C-92 -57 -84 -53 -76 -55C-71 -59 -70 -67 -73 -73Z", W, 4,
                            F("M-82 -60C-86 -54 -78 -52 -74 -56L-72 -64Z", DL))
                  + P("M-77 -72C-78 -79 -86 -81 -88 -75C-86 -72 -81 -70 -77 -72Z", W, 3)
                  + L("M-86 -66Q-82 -64 -78 -66M-87 -61Q-83 -59 -79 -61", 1.6)))

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
    o.append(mark("tail", S(tail, W, 4, bands + L("M-30 -58C-42 -66 -52 -76 -66 -80", 1.6) + L("M-78 -84Q-90 -84 -100 -90", 1.6))))
    o.append(mark("tail-bits", L("M-108 -96L-117 -101M-109 -91L-119 -93M-110 -86L-118 -85", 2)
                  + T(-118, -112, -128, -114, -138, -108, 2.2) + T(-122, -78, -130, -76, -138, -80, 2)))
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
    o.append(mark("pip-eyes", E(-11 + fx, -74, 4.6, 6.2, INK) + E(11 + fx, -74, 4.6, 6.2, INK)
                  + C(-12.6 + fx, -76.6, 1.9) + C(9.4 + fx, -76.6, 1.9) + C(-9.6 + fx, -71.6, 0.8) + C(12.4 + fx, -71.6, 0.8)))
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


def eye(cx, cy, r, px, py, name):
    o = []
    # goggle ring
    ring = circ(cx, cy, r + 9) + circ(cx, cy, r + 1)
    o.append(C(cx, cy, r + 1, W))
    o.append(f'<path d="{ring}" fill="{DL}" fill-rule="evenodd" stroke="{INK}" stroke-width="3.6"/>')
    for i in range(6):
        a = math.radians(i * 60 + 30)
        o.append(C(cx + math.cos(a) * (r + 5), cy + math.sin(a) * (r + 5), 1.6, INK))
    o = [mark(f"{name}-ring", "".join(o))]
    # eyeball
    inner = [F(circ(cx + r * 0.35, cy + r * 0.45, r * 0.9), DL), P(circ(cx - r * 0.15, cy - r * 0.2, r * 0.95), W, 0)]
    inner.append(E(px, py, r * 0.5, r * 0.58, INK))
    inner.append(C(px - r * 0.18, py - r * 0.22, r * 0.17, W) + C(px + r * 0.2, py + r * 0.2, r * 0.07, W))
    # happy lower lid
    inner.append(L(f"M{n(cx - r)} {n(cy + r * 0.62)}Q{n(cx)} {n(cy + r * 0.28)} {n(cx + r)} {n(cy + r * 0.62)}", 2.4))
    o.append(mark(f"{name}-ball", S(circ(cx, cy, r), W, 3.6, "".join(inner))))
    # glass glint across the goggle
    o.append(mark(f"{name}-glint", L(f"M{n(cx - r * 0.75)} {n(cy - r * 0.3)}Q{n(cx - r * 0.6)} {n(cy - r * 0.7)} {n(cx - r * 0.25)} {n(cy - r * 0.8)}", 2.6, W)))
    return mark(name, "".join(o))


HEAD = ("M752 330C750 282 790 256 825 258C870 262 894 300 888 342C884 378 860 400 822 400"
        "C786 400 754 380 752 330Z")
STALK_R = ((846, 272), (850, 238), (858, 200), 15, 12)     # base, bend, tip, widths (head-local coords)
STALK_L = ((796, 276), (786, 244), (782, 212), 17, 13)
EYE_R = (858, 180, 26, 865, 184)                         # centre, radius, pupil centre
EYE_L = (780, 190, 29, 788, 195)
LAMP = (897, 297)                                        # headlamp rays radiate from here


def head():
    o = []
    # stalks behind the head
    o.append(mark("stalk-r", stalk(*STALK_R, 1)))
    o.append(mark("stalk-l", stalk(*STALK_L, 2)))
    # goggle strap linking the eyes
    o.append(mark("strap", P("M806 176L834 168L836 182L808 190Z", DD, 2.4)))
    o.append(eye(*EYE_R, "eye-r"))
    o.append(eye(*EYE_L, "eye-l"))
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
    rays = "".join(ray(*LAMP, a, 18, 30 + (abs(a) % 4) * 3, 2.4) for a in (-34, -17, 0, 17, 34))
    o.append(mark("rays", rays))
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
HEAD_TR = "translate(820 330) scale(1.08) translate(-820 -330)"
TITLE = ("<title>The snail caravan: a riveted mechanical snail on four jointed legs, its spiral shell made into "
         "a little house with a porthole, door and smoking stovepipe; Pip steers at a ship's wheel under a "
         "patched parasol while Nib waves from the chimney</title>")


def drawing():
    """the full drawing, with every moving piece wrapped in mark() tags"""
    parts = [
        ("ground", ground()),
        ("smoke", smoke()),
        ("far-legs", far_legs()),
        ("shell", shell() + porthole() + door()),
        ("chimney", chimney()),
        ("nib", g(mark("nib", nib()), NIB_TR)),
        ("hanging-pot", pot()),
        ("roof-deck", deck()),
        ("parasol-pole", g(mark("pole", parasol_pole()), PARASOL_TILT)),
        ("pip", g(pip_body() + helm_post() + wheel() + pip_hand(), PIP_TR)),
        ("deck-rail", deck_rail()),
        ("parasol", g(mark("canopy", parasol()), PARASOL_TILT)),
        ("bunting", bunting()),
        ("hull", hull() + hull_pipe() + saddle() + porch()),
        ("crate", crate()),
        ("kettle", kettle()),
        ("ladder", ladder()),
        ("near-legs", near_legs()),
        ("head", g(head(), HEAD_TR)),
        ("ground-tufts", ground_front()),
    ]
    return "".join(f"<!-- {name} --><g id=\"{name}\">{content}</g>" for name, content in parts)


def page(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 800" width="1000" height="800" role="img">'
            + TITLE + DEFS
            + '<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)"><g filter="url(#halo)">'
            + body + "</g></g></svg>")


def unmark(s):
    return re.sub(r"<!--/?mv:[\w-]+-->", "", s)


def piece(body, name):
    m = re.search(rf"<!--mv:{name}-->(.*?)<!--/mv:{name}-->", body, re.S)
    assert m, name
    return m.group(1)


def cut(body, *names, subs=None):
    """drop the named marked pieces (or replace them via subs[name](content))"""
    for name in names:
        f = (subs or {}).get(name, lambda s: "")
        body, k = re.subn(rf"<!--mv:{name}-->(.*?)<!--/mv:{name}-->", lambda m: f(m.group(1)), body, flags=re.S)
        assert k == 1, name
    return body


# ---------------------------------------------------------------------------
# GEOMETRY shared by the base and the motion layer
# ---------------------------------------------------------------------------
POLE_CUT = 149.5      # parasol-local y of the pole's seam above the wheel's top handle knob (top ~154.2):
POLE_KNOB = 152.5     # below it the pole stays put; the swaying part overlaps down to here (its ink smear
                      # reaches 1.3 further, still clear of the knob), so the seam never opens
SCARF_CUT = -56       # Pip-local x: the scarf tail beyond this flutters, the root stays put
DOME_GAP = 5.0        # stalks are hidden this far outside the dome's centre line (outline 2.5 + ink smear 1.3 + margin)


def bez3(p0, c1, c2, p1, t):
    a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
    return (a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0], a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1])


def cubic_path_pts(d, k=32):
    """sample an absolute M/C/Z path as a polyline"""
    v = [float(t) for t in re.findall(r"-?\d+\.?\d*", d)]
    pts = [(v[0], v[1])]
    for i in range(2, len(v) - 5, 6):
        p0, c1, c2, p1 = pts[-1], (v[i], v[i + 1]), (v[i + 2], v[i + 3]), (v[i + 4], v[i + 5])
        pts += [bez3(p0, c1, c2, p1, j / k) for j in range(1, k + 1)]
    return pts


def inside(p, poly):
    x, y = p
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


DOME = cubic_path_pts(HEAD)[:-1]


def stalk_pivot(st):
    """where a stalk's centre line leaves the dome outline (head-local)"""
    (b, c, t) = st[:3]
    for i in range(401):
        u = i / 400
        p = ((1 - u) ** 2 * b[0] + 2 * (1 - u) * u * c[0] + u * u * t[0], (1 - u) ** 2 * b[1] + 2 * (1 - u) * u * c[1] + u * u * t[1])
        if not inside(p, DOME):
            return p
    raise ValueError(st)


def dome_offset(dist):
    cx = sum(p[0] for p in DOME) / len(DOME)
    cy = sum(p[1] for p in DOME) / len(DOME)
    out = []
    m = len(DOME)
    for i, (x, y) in enumerate(DOME):
        (ax, ay), (bx, by) = DOME[i - 1], DOME[(i + 1) % m]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        nx, ny = ty / ln, -tx / ln
        if (x - cx) * nx + (y - cy) * ny < 0:
            nx, ny = -nx, -ny
        out.append((x + nx * dist, y + ny * dist))
    return out


PIVOT_R = stalk_pivot(STALK_R)
PIVOT_L = stalk_pivot(STALK_L)


def base_svg(body):
    k = [0]

    def clip(d):
        def f(s):
            k[0] += 1
            return f'<clipPath id="cvb{k[0]}"><path d="{d}"/></clipPath><g clip-path="url(#cvb{k[0]})">{s}</g>'
        return f

    moving = (["nib", "pot-swing", "pot-steam", "canopy", "lantern", "tail-bits", "pip-eyes", "k-steam", "k-bub0", "k-bub1",
               "b-string", "front-shin", "swoosh", "strap", "eye-r", "eye-l", "rays", "curl0", "curl1"]
              + [f"puff{i}" for i in range(len(PUFFS))] + [f"bub{i}" for i in range(len(SMOKE_BUBBLES))]
              + [f"flag{i}" for i in range(len(bunting_flags()))] + [f"dust{i}" for i in range(len(DUST))])
    body = cut(body, *moving)
    # pieces that move only beyond a seam keep their fixed root here
    body = cut(body, "pole", "tail", "stalk-r", "stalk-l", subs={
        "pole": clip(f"M370 {POLE_CUT}L490 {POLE_CUT}L490 260L370 260Z"),
        "tail": clip(f"M{SCARF_CUT} -200L200 -200L200 200L{SCARF_CUT} 200Z"),
        # a stalk's root, in a thin band just outside the dome, fills the gap under the swaying stalk's clip
        "stalk-r": lambda s: clip(circ(*PIVOT_R, 16))(clip(poly_d(dome_offset(DOME_GAP + 2)))(s)),
        "stalk-l": lambda s: clip(circ(*PIVOT_L, 16))(clip(poly_d(dome_offset(DOME_GAP + 2)))(s)),
    })
    return page(unmark(body))


# ---------------------------------------------------------------------------
# MOTION LAYER  (caravan-motion.svg)
# Every moving part sits in a pivot wrapper whose net transform at rest is the identity, so its
# own ink filter sees the same user space (and the same noise) as the still. White backings for
# all moving parts are painted first (like the still's halo, under everything), each clipped away
# from fixed ink it borders, then the art in the still's paint order.
# ---------------------------------------------------------------------------
HALO = 3.8            # backing reach past the ink (the still's halo filter dilates 3.2 with a square)
EASE = "cubic-bezier(.45,0,.55,1)"
INK_FX = ('<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>'
          '<feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" yChannelSelector="G"/>')
TAG_RE = re.compile(r'<(/?)([A-Za-z]+)((?:\s+[\w:-]+="[^"]*")*)\s*(/?)>')
ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')


def fm(v, d=2):
    s = f"{v:.{d}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "", "-") else s


def tf_pip(x, y):
    return 385 + 0.66 * x, 190 + 0.66 * y


def tf_nib(x, y):
    return 228 + 0.56 * x, 167 + 0.56 * y


def tf_head(x, y):
    return 820 + 1.08 * (x - 820), 330 + 1.08 * (y - 330)


def tf_tilt(x, y):
    a = math.radians(6)
    return (430 + (x - 430) * math.cos(a) - (y - 190) * math.sin(a), 190 + (x - 430) * math.sin(a) + (y - 190) * math.cos(a))


def Cw(x, y, r, fill):
    return f'<circle cx="{fm(x)}" cy="{fm(y)}" r="{fm(r)}" fill="{fill}"/>'


def Ew(x, y, rx, ry, fill):
    return f'<ellipse cx="{fm(x)}" cy="{fm(y)}" rx="{fm(rx)}" ry="{fm(ry)}" fill="{fill}"/>'


def circ_w(cx, cy, r):
    return f"M{fm(cx - r)} {fm(cy)}A{fm(r)} {fm(r)} 0 1 0 {fm(cx + r)} {fm(cy)}A{fm(r)} {fm(r)} 0 1 0 {fm(cx - r)} {fm(cy)}Z"


def poly_d(pts):
    return "M" + "L".join(f"{fm(x, 1)} {fm(y, 1)}" for x, y in pts) + "Z"


def outside(pts, box):
    """clip path d for the box (x0, y0, x1, y1) minus the polygon (use with clip-rule evenodd). Keep the box
    tight: a big non-rectangular clip is re-rasterised every frame and halves the frame rate."""
    return rect_d(*box) + poly_d(pts)


def rect_d(x0, y0, x1, y1):
    return poly_d([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def halo(svg, h):
    """white backing for a piece: each shape filled and stroked white so it reaches h past its ink"""
    out, stack, skip = [], [], 0
    for m in TAG_RE.finditer(svg):
        close, tag, attrs, selfc = m.groups()
        a = dict(ATTR_RE.findall(attrs))
        if tag == "clipPath":
            skip += -1 if close else (0 if selfc else 1)
            continue
        if tag == "g":
            if close:
                if stack.pop() == "skip":
                    skip -= 1
                elif not skip:
                    out.append("</g>")
            elif "clip-path" in a:          # clipped detail lies inside the outline drawn after it
                stack.append("skip")
                skip += 1
            else:
                stack.append("keep")
                if not skip:
                    out.append(f'<g transform="{a["transform"]}">' if "transform" in a else "<g>")
            continue
        if skip or close or tag not in ("path", "circle", "ellipse"):
            continue
        stroked = a.get("stroke", "none") != "none"
        sw = float(a.get("stroke-width", 0)) if stroked else 0.0
        filled = a.get("fill", "#000") != "none"
        if not (filled or stroked):
            continue
        geo = "".join(f' {k}="{a[k]}"' for k in ("d", "cx", "cy", "r", "rx", "ry", "transform") if k in a)
        out.append(f'<{tag}{geo} fill="{W if filled else "none"}" stroke="{W}" stroke-width="{fm(sw + 2 * h)}"/>')
    return "".join(out)


def _mul(a, b):
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3],
            a[1] * b[2] + a[3] * b[3], a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def _tf(s):
    m = (1, 0, 0, 1, 0, 0)
    for fn, args in re.findall(r"(\w+)\(([^)]*)\)", s):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip())]
        if fn == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif fn == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif fn == "rotate":
            c, s_ = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
            t = (c, s_, -s_, c, 0, 0)
            if len(v) == 3:
                t = _mul(_mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        else:
            raise ValueError(fn)
        m = _mul(m, t)
    return m


def _path_pts(d):
    """points whose box contains an absolute-coordinate path (M L Q C A Z)"""
    toks = re.findall(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)", d)
    pts, i, cmd, cur = [], 0, "M", (0.0, 0.0)
    take = {"M": 2, "L": 2, "Q": 4, "C": 6, "A": 7}
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            continue
        if cmd not in take:
            raise ValueError(cmd)
        v = [float(t) for t in toks[i:i + take[cmd]]]
        i += take[cmd]
        if cmd == "A":
            rx, ry = v[0], v[1]
            (px, py), end = cur, (v[5], v[6])
            gap = math.hypot(end[0] - px, end[1] - py)
            if min(abs(gap - 2 * rx), abs(gap - 2 * ry)) < 0.05 * max(rx, ry):   # half ellipse: centred between
                cx, cy = (px + end[0]) / 2, (py + end[1]) / 2
                pts += [(cx - rx, cy - ry), (cx + rx, cy + ry), end]
            else:                                                                # any other arc: generous
                r = 2 * max(rx, ry)
                pts += [(px - r, py - r), (px + r, py + r), (end[0] - r, end[1] - r), (end[0] + r, end[1] + r)]
            cur = end
        else:
            pts += list(zip(v[0::2], v[1::2]))
            cur = pts[-1]
    return pts


def bbox(svg):
    """conservative bounding box of drawn markup (control points, arcs grown, strokes included)"""
    stack, skip = [(1, 0, 0, 1, 0, 0)], 0
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for m in TAG_RE.finditer(svg):
        close, tag, attrs, selfc = m.groups()
        if tag == "clipPath":
            skip += -1 if close else 1
            continue
        if skip:
            continue
        if close:
            if tag == "g":
                stack.pop()
            continue
        a = dict(ATTR_RE.findall(attrs))
        cur = _mul(stack[-1], _tf(a["transform"])) if "transform" in a else stack[-1]
        if tag == "g":
            if not selfc:
                stack.append(cur)
            continue
        if tag == "path":
            pts = _path_pts(a["d"])
        elif tag in ("circle", "ellipse"):
            cx, cy = float(a["cx"]), float(a["cy"])
            rx = float(a.get("r", a.get("rx", 0)))
            ry = float(a.get("r", a.get("ry", 0)))
            pts = [(cx - rx, cy - ry), (cx + rx, cy + ry)]
        else:
            continue
        h = float(a.get("stroke-width", 0)) / 2 if a.get("stroke", "none") != "none" else 0
        for (x, y) in pts:
            for dx in (-h, h):
                for dy in (-h, h):
                    X = cur[0] * (x + dx) + cur[2] * (y + dy) + cur[4]
                    Y = cur[1] * (x + dx) + cur[3] * (y + dy) + cur[5]
                    x0, y0, x1, y1 = min(x0, X), min(y0, Y), max(x1, X), max(y1, Y)
    return x0, y0, x1, y1


def pivot(cls, px, py, inner):
    return (f'<g transform="translate({fm(px)} {fm(py)})"><g class="{cls}">'
            f'<g transform="translate({fm(-px)} {fm(-py)})">{inner}</g></g></g>')


def wrap(cls, inner):
    return f'<g class="{cls}">{inner}</g>'


def look(r, glance, inner):
    return f'<g class="sf-look" data-look="{fm(r, 1)}"><g class="{glance}">{inner}</g></g>'


class Motion:
    def __init__(self):
        self.defs, self.css, self.classes, self.k = [], [], [], 0

    def uid(self, p):
        self.k += 1
        return f"{p}{self.k}"

    def ink(self, svg, pad=4):
        """own ink filter for one moving part, its region just around the part"""
        x0, y0, x1, y1 = bbox(svg)
        x0, y0, x1, y1 = math.floor(x0 - pad), math.floor(y0 - pad), math.ceil(x1 + pad), math.ceil(y1 + pad)
        fid = self.uid("k")
        self.defs.append(f'<filter id="{fid}" filterUnits="userSpaceOnUse" x="{x0}" y="{y0}" width="{x1 - x0}" '
                         f'height="{y1 - y0}">{INK_FX}</filter>')
        return f'<g filter="url(#{fid})">{svg}</g>'

    def clip(self, d, svg, evenodd=False):
        cid = self.uid("q")
        rule = ' clip-rule="evenodd"' if evenodd else ""
        self.defs.append(f'<clipPath id="{cid}"><path d="{d}"{rule}/></clipPath>')
        return f'<g clip-path="url(#{cid})">{svg}</g>'

    def anim(self, cls, frames, dur, delay=0.0, ease=EASE):
        """frames [(percent, declarations)]; 0% and 100% must be the identical rest pose"""
        frames = sorted(frames, key=lambda f: f[0])
        assert frames[0][0] == 0 and frames[-1][0] == 100 and frames[0][1] == frames[-1][1], cls
        body = f"0%,100%{{{frames[0][1]}}}" + "".join(f"{fm(p)}%{{{d}}}" for p, d in frames[1:-1])
        self.css.append(f"@keyframes {cls}{{{body}}}")
        self.css.append(f".{cls}{{animation:{cls} {fm(dur)}s {ease} {fm(delay)}s infinite;transform-origin:0 0}}")
        self.classes.append(cls)


def rot(pts):
    return [(p, f"transform:rotate({fm(a)}deg)") for p, a in pts]


def pendulum(amp, k=12, phase=0.0):
    """sine swing through the rest pose (linear between k samples)"""
    return rot([(100 * i / k, amp * math.sin(2 * math.pi * i / k + phase) - amp * math.sin(phase)) for i in range(k + 1)])


def blink(dur, at, closed=0.08):
    """scaleY blinks: shut over 80 ms, held shut 120 ms, open over 100 ms"""
    f = [(0, "transform:scaleY(1)"), (100, "transform:scaleY(1)")]
    for t in at:
        f += [(100 * t / dur, "transform:scaleY(1)"), (100 * (t + 0.08) / dur, f"transform:scaleY({closed})"),
              (100 * (t + 0.2) / dur, f"transform:scaleY({closed})"), (100 * (t + 0.3) / dur, "transform:scaleY(1)")]
    return f


def moves(pts):
    """[(percent, dx, dy, opacity or None, scale or None)] -> frames"""
    out = []
    for p, dx, dy, op, sc in pts:
        d = f"transform:translate({fm(dx, 1)}px,{fm(dy, 1)}px) scale({fm(sc if sc is not None else 1, 3)})"
        if op is not None:
            d += f";opacity:{fm(op)}"
        out.append((p, d))
    return out


# ---- smoke: a relay of puffs along one spine ------------------------------------------------
# The spine runs from behind Nib (the chimney mouth) up and back to the upper left. Each puff
# drifts along its own stretch of it at a steady pace, keeping its sideways offset: it fades in a
# little behind its drawn spot, passes through that spot (where it sits at t=0, exactly as
# caravan.svg draws it), grows a little and fades out ahead, then restarts invisibly. The freshest
# puff restarts behind Nib, so the chimney keeps sending out new smoke; further out, puffs fade
# in where the one ahead of them faded out, so the trail flows without ever scaling a small puff
# up into a big one (its outline would thicken).
SMOKE_SPINE = [(217, 174), (199, 160), (181, 139), (140, 107), (96, 72), (58, 50), (28, 41), (4, 37), (-60, 31)]
# per puff (same order as PUFFS): spine distance travelled before / after the drawn spot, seconds
SMOKE_RUNS = ((26, 16, 9.0), (30, 20, 8.6), (30, 20, 8.2), (36, 26, 8.8), (30, 36, 7.4), (30, 34, 7.0),
              (30, 34, 6.6), (26, 40, 6.1), (21, 30, 5.5))
# start offsets chosen (by a search over 60 s) so the puffs' fades never line up and the trail stays full
SMOKE_DELAYS = (-3.2, -7.5, -1.6, -6.5, -2.6, -3.6, -5.1, -1.0, -4.0)
SMOKE_IN = 9         # fade-in distance after a restart
SMOKE_OUT = 12        # fade-out distance before the end of a run (shorter if the run ends at the canvas edge)
SMOKE_GROW = 0.006    # scale gained per unit of travel


class Spine:
    def __init__(self, pts, k=40):
        m = len(pts)
        self.p = []
        for i in range(m - 1):
            p0, p1, p2, p3 = pts[max(0, i - 1)], pts[i], pts[i + 1], pts[min(m - 1, i + 2)]
            for j in range(k):
                t = j / k
                self.p.append(tuple(0.5 * (2 * p1[q] + (p2[q] - p0[q]) * t + (2 * p0[q] - 5 * p1[q] + 4 * p2[q] - p3[q]) * t * t
                                           + (3 * p1[q] - p0[q] - 3 * p2[q] + p3[q]) * t ** 3) for q in (0, 1)))
        self.p.append(pts[-1])
        self.acc = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.acc.append(self.acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.acc[-1]

    def at(self, s):
        s = max(0.0, min(s, self.length - 1e-6))
        i = max(0, min(len(self.p) - 2, bisect.bisect_right(self.acc, s) - 1))
        (ax, ay), (bx, by) = self.p[i], self.p[i + 1]
        seg = self.acc[i + 1] - self.acc[i]
        f = (s - self.acc[i]) / seg
        tx, ty = (bx - ax) / seg, (by - ay) / seg
        return (ax + (bx - ax) * f, ay + (by - ay) * f), (tx, ty), (-ty, tx)

    def project(self, x, y):
        j = min(range(len(self.p)), key=lambda i: (self.p[i][0] - x) ** 2 + (self.p[i][1] - y) ** 2)
        s = self.acc[j]
        (cx, cy), (tx, ty), (nx, ny) = self.at(s)
        return s, (x - cx) * tx + (y - cy) * ty, (x - cx) * nx + (y - cy) * ny


def smoke_frames():
    """[(frames, seconds)] per puff"""
    sp = Spine(SMOKE_SPINE)
    out = []
    for (x, y, r, _), (back, fwd, dur) in zip(PUFFS, SMOKE_RUNS):
        si, u, w = sp.project(x, y)

        def pos(s):
            (cx, cy), (tx, ty), (nx, ny) = sp.at(s)
            return cx + nx * w + tx * u - x, cy + ny * w + ty * u - y

        def scale(s):
            return 1 + SMOKE_GROW * (s - si)

        end = si
        while end < si + fwd:               # a run stops before the puff (and its halo) reaches the edge
            dx, dy = pos(end + 0.5)
            rad = r * scale(end + 0.5) * 1.3 + 5.5
            if x + dx - rad < 0 or y + dy - rad < 0:
                break
            end += 0.5
        start = max(0.0, si - back)
        out_len = min(SMOKE_OUT, end - si)
        assert si - start >= SMOKE_IN, (x, y)
        run = end - start
        tw = (end - si) / run                # this puff reaches the end of its run (invisible) and restarts
        stops = sorted({si, end - out_len, end, start, start + SMOKE_IN} | {start + run * q / 6 for q in range(1, 6)})

        def op(s):
            return min(1.0, (s - start) / SMOKE_IN, (end - s) / out_len if out_len else 1.0)

        rows = []
        for s in stops:
            t = (s - si) / run if s >= si else tw + 0.0004 + (s - start) / run * (1 - tw - 0.0004)
            rows.append((t, s))
        rows += [(1.0, si)]
        fr, seen = [], set()
        for t, s in sorted(rows):
            pct = round(100 * t, 2)
            if pct in seen:
                continue
            seen.add(pct)
            dx, dy = pos(s) if 0 < t < 1 else (0.0, 0.0)
            fr.append((pct, dx, dy, round(max(0.0, op(s)), 2) if 0 < t < 1 else 1.0, scale(s) if 0 < t < 1 else 1.0))
        out.append((moves(fr), dur))
    return out


def motion_svg(body):
    mo = Motion()
    H = HALO
    bk, art = [], []

    # ---- smoke from the chimney ------------------------------------------------------------
    for i, ((x, y, r, _), (frames, dur)) in enumerate(zip(PUFFS, smoke_frames())):
        cls = f"cv-smoke{i}"
        mo.anim(cls, frames, dur, SMOKE_DELAYS[i], "linear")
        pz = unmark(piece(body, f"puff{i}"))
        bk.append(pivot(cls, x, y, halo(pz, H)))
        art.append(pivot(cls, x, y, mo.ink(pz)))
    for i, ((x, y, r, sw), dur, delay) in enumerate(zip(SMOKE_BUBBLES, (4.7, 5.9, 5.3), (-1.1, -3.4, -0.4))):
        cls = f"cv-ring{i}"
        mo.anim(cls, moves([(0, 0, 0, 1, 1), (38, -9, -7, 0, 1.25), (38.2, 7, 6, 0, 0.5), (64, 0, 0, 1, 1),
                            (100, 0, 0, 1, 1)]), dur, delay, "ease-in-out")
        pz = unmark(piece(body, f"bub{i}"))
        bk.append(pivot(cls, x, y, halo(pz, H)))
        art.append(pivot(cls, x, y, mo.ink(pz)))
    for i in range(2):                       # wind curls: fixed, but painted over the drifting puffs
        pz = unmark(piece(body, f"curl{i}"))
        bk.append(halo(pz, H))
        art.append(mo.ink(pz))

    # ---- Nib on the chimney: waves, blinks, looks; ink drops bob --------------------------
    nb = piece(body, "nib")
    hn = H / 0.56
    still_nib = unmark(cut(nb, "nib-drop0", "nib-drop1", "nib-drop2", "nib-arm", "nib-eyes"))
    nbk = [g(halo(still_nib, hn), NIB_TR)]
    for i, (dur, delay, dy) in enumerate(((3.9, -0.6, -2.4), (4.7, -2.9, -2.0), (5.5, -1.7, -2.6))):
        cls = f"cv-nibdrop{i}"
        mo.anim(cls, moves([(0, 0, 0, None, None), (50, 0, dy, None, None), (100, 0, 0, None, None)]), dur, delay)
        pz = unmark(piece(nb, f"nib-drop{i}"))
        nbk.append(wrap(cls, g(halo(pz, hn), NIB_TR)))
        art.append(wrap(cls, mo.ink(g(pz, NIB_TR))))
    art.append(mo.ink(g(still_nib, NIB_TR)))
    ax, ay = tf_nib(33, 6)                   # shoulder
    mo.anim("cv-nibwave", rot([(0, 0), (6, -14), (13, 7), (20, -14), (27, 7), (34, -10), (42, 0), (100, 0)]), 5.2, -1.3)
    pz = unmark(piece(nb, "nib-arm"))
    nbk.append(pivot("cv-nibwave", ax, ay, g(halo(pz, hn), NIB_TR)))
    art.append(pivot("cv-nibwave", ax, ay, mo.ink(g(pz, NIB_TR))))
    eyes = []
    for (ex, px, g1, g2) in ((-12, -7, (-9.3, -2.2), (-5, 3)), (16, 21, (18.7, -2.2), (23, 3))):
        wx, wy = tf_nib(ex, -2)
        pupil = Cw(*tf_nib(px, 0.5), 6.6 * 0.56, INK) + Cw(*tf_nib(*g1), 2.5 * 0.56, W) + Cw(*tf_nib(*g2), 0.56, W)
        eyes.append((Cw(wx, wy, 13 * 0.56, W), mo.clip(circ_w(wx, wy, 13 * 0.56), look(2.2, "cv-nibglance", pupil))))
    mo.anim("cv-nibblink", blink(5.3, (2.6,)), 5.3, -0.7)
    mo.anim("cv-nibglance", moves([(0, 0, 0, None, None), (40, 0, 0, None, None), (44, -2.2, -1.2, None, None),
                                   (61, -2.2, -1.2, None, None), (65, 0, 0, None, None), (100, 0, 0, None, None)]), 7.9, -2.1)
    art.append(pivot("cv-nibblink", *tf_nib(2, -2), mo.ink(eyes[0][0] + eyes[1][0] + eyes[0][1] + eyes[1][1])))
    rim = [(202.5, 182), (254, 182), (254, 203), (202.5, 203)]     # no white over the chimney rim Nib sits in
    bk.append(mo.clip(outside(rim, (180, 100, 280, 210)), "".join(nbk), True))

    # ---- hanging pot swings from its hook; a curl of steam rises ---------------------------
    pz = unmark(piece(body, "pot-swing"))
    mo.anim("cv-pot", pendulum(4.2), 5.6, -2.2, "linear")
    bracket = outside([(147, 331), (215, 337), (215, 350), (213, 376), (205, 376), (167, 344), (155, 343.5), (155, 352.5),
                       (145, 352.5), (145, 331)], (100, 300, 230, 440))   # bracket arm, brace, hook: no white
    bk.append(mo.clip(bracket, pivot("cv-pot", 151, 349.2, halo(pz, H)), True))
    art.append(pivot("cv-pot", 151, 349.2, mo.ink(pz)))
    pz = unmark(piece(body, "pot-steam"))
    mo.anim("cv-potsteam", moves([(0, 0, 0, 1, None), (34, 0, -9, 0, None), (34.3, 0, 5, 0, None), (62, 0, 0, 1, None),
                                  (100, 0, 0, 1, None)]), 4.1, -0.9, "ease-in-out")
    bk.append(mo.clip(bracket, wrap("cv-potsteam", halo(pz, H)), True))
    art.append(wrap("cv-potsteam", mo.ink(pz)))

    # ---- Pip: the lantern swings from his fist, the scarf tail flutters, he blinks and looks
    hp = H / 0.66
    lant = piece(body, "lantern")
    rays = unmark(piece(lant, "lantern-rays"))
    lamp = unmark(cut(lant, "lantern-rays"))
    lx, ly = tf_pip(-82, -61)
    mo.anim("cv-lantern", pendulum(4), 4.6, -1.5, "linear")
    mo.anim("cv-glow", [(0, "opacity:1"), (30, "opacity:.6"), (45, "opacity:.85"), (70, "opacity:.5"), (100, "opacity:1")],
            2.9, -0.8, "ease-in-out")
    cuff = [tf_pip(x, y) for x, y in ((-76, -104), (12, -104), (12, -30), (-24, -32), (-50, -44), (-62, -47), (-72, -46),
                                      (-76, -50))]
    bk.append(mo.clip(outside(cuff, (280, 125, 375, 210)), pivot("cv-lantern", lx, ly, g(wrap("cv-glow", halo(rays, hp)) + halo(lamp, hp), PIP_TR)),
                      True))
    art.append(pivot("cv-lantern", lx, ly, mo.ink(g(wrap("cv-glow", rays) + lamp, PIP_TR))))
    art.append(mo.ink(g(unmark(piece(body, "fist")), PIP_TR)))     # the fist stays over the lantern's bail
    tail = unmark(piece(body, "tail"))
    bits = unmark(piece(body, "tail-bits"))
    sx, sy = tf_pip(SCARF_CUT, -79)
    mo.anim("cv-scarf", rot([(0, 0), (14, -4.5), (30, 2.5), (46, -3.5), (62, 1.5), (78, -1.5), (100, 0)]), 3.3, -0.4)
    # the moving end overlaps the fixed root by 3 (identical at rest, so a swing doubles a line instead
    # of opening a gap); its white backing stops 3 short, so it never paints over the root
    tcut = f"M-200 -200L{SCARF_CUT + 3} -200L{SCARF_CUT + 3} 0L-200 0Z"
    tcut_bk = f"M-200 -200L{SCARF_CUT - 3} -200L{SCARF_CUT - 3} 0L-200 0Z"
    edge = [bez3((-110, -84), (-96, -76), (-82, -80), (-66, -74), t / 40) for t in range(41)]
    edge += [bez3((-66, -74), (-50, -68), (-40, -56), (-26, -48), t / 40) for t in range(1, 41)]
    edge = [p for p in edge if -94 <= p[0] <= SCARF_CUT]
    below = [tf_pip(*p) for p in edge + [(SCARF_CUT, 30), (-94, 30)]]    # sleeve, cuff, fist: no white over them
    bk.append(mo.clip(outside(below, (275, 100, 365, 150)), pivot("cv-scarf", sx, sy, g(mo.clip(tcut_bk, halo(tail, hp)) + halo(bits, hp), PIP_TR)),
                      True))
    art.append(pivot("cv-scarf", sx, sy, mo.ink(g(mo.clip(tcut, tail) + bits, PIP_TR))))
    peyes = ""
    for ex in (-7, 15):
        cx, cy = tf_pip(ex, -74)
        peyes += look(1.3, "cv-pipglance", Ew(cx, cy, 4.6 * 0.66, 6.2 * 0.66, INK) + Cw(*tf_pip(ex - 1.6, -76.6), 1.9 * 0.66, W)
                      + Cw(*tf_pip(ex + 1.4, -71.6), 0.8 * 0.66, W))
    mo.anim("cv-pipblink", blink(4.3, (1.4,), 0.12), 4.3, -2.6)
    mo.anim("cv-pipglance", moves([(0, 0, 0, None, None), (52, 0, 0, None, None), (56, -1.1, 0.3, None, None),
                                   (74, -1.1, 0.3, None, None), (78, 0, 0, None, None), (100, 0, 0, None, None)]), 6.7, -1.2)
    art.append(pivot("cv-pipblink", *tf_pip(4, -74), mo.ink(peyes)))

    # ---- parasol sways on its pole; the fringe flickers -----------------------------------
    pole = unmark(piece(body, "pole"))
    cano = piece(body, "canopy")
    canopy = unmark(cut(cano, "fringe"))
    px, py = tf_tilt(430, POLE_CUT)          # the parasol sways about the pole's seam above the wheel
    sway = [(0, 0), (16, 3), (34, -1.9), (52, 1.3), (68, -0.6), (82, 0.25), (100, 0)]
    mo.anim("cv-parasol", rot(sway), 7.4, -1.9)
    mo.anim("cv-fringe0", rot([(0, 0), (25, 11), (50, -6), (75, 8), (100, 0)]), 2.3, -0.5, "ease-in-out")
    mo.anim("cv-fringe1", rot([(0, 0), (25, -9), (50, 7), (75, -10), (100, 0)]), 2.9, -1.6, "ease-in-out")
    fr_a = fr_b = ""
    for i, (a, b, c, d) in enumerate(FRINGE):
        line = L(f"M{a} {b}L{c} {d}", 1.5)
        fr_a += pivot(f"cv-fringe{i % 2}", a, b, line)
        fr_b += pivot(f"cv-fringe{i % 2}", a, b, halo(line, H))

    def pole_clip(s, y):
        return mo.clip(f"M370 0L490 0L490 {fm(y)}L370 {fm(y)}Z", s)

    bk.append(pivot("cv-parasol", px, py, g(pole_clip(halo(pole, H), POLE_CUT - 2) + halo(canopy, H) + fr_b, PARASOL_TILT)))
    art.append(pivot("cv-parasol", px, py, mo.ink(g(pole_clip(pole, POLE_KNOB) + canopy + fr_a, PARASOL_TILT))))

    # ---- bunting: pulled along by the parasol tip, each pennant flutters --------------------
    # Rotating the string about its stalk end by beta and scaling it by (1 + sigma) moves its parasol end
    # exactly as the rib tip moves (to first order), so the knot never slips off the tip.
    (ex0, ey0), _, (bx, by) = BUNTING
    tx, ty = tf_tilt(542, 79)                # the rib tip the string is tied to
    qx, qy = tx - px, ty - py                # rib tip about the parasol pivot
    lx2, ly2 = ex0 - bx, ey0 - by            # string end about its stalk end
    det = -(lx2 * lx2 + ly2 * ly2)           # solve  beta*(-ly2, lx2) + sigma*(lx2, ly2) = (-qy, qx)
    beta = (-qy * ly2 - lx2 * qx) / det      # degrees of string turn per degree of sway
    sigma = (-ly2 * qx + lx2 * qy) / det     # string scale change per radian of sway
    mo.anim("cv-bunting", [(p, f"transform:rotate({fm(a * beta, 3)}deg) scale({fm(1 + math.radians(a) * sigma, 4)})")
                           for p, a in sway], 7.4, -1.9)
    fa = fb = ""
    for i, (x, y, ang, fl) in enumerate(bunting_flags()):
        cls = f"cv-flag{i}"
        sk = (8, -6, 4) if i % 2 else (-7, 6, -3)
        mo.anim(cls, [(0, "transform:skewX(0deg) scaleY(1)"), (24, f"transform:skewX({sk[0]}deg) scaleY(.95)"),
                      (52, f"transform:skewX({sk[1]}deg) scaleY(.98)"), (78, f"transform:skewX({sk[2]}deg) scaleY(.96)"),
                      (100, "transform:skewX(0deg) scaleY(1)")], (3.1, 3.7, 3.3, 4.1, 3.5, 3.9, 3.2)[i], -0.45 * i)
        tr = f"translate({n(x)} {n(y)}) rotate({n(ang)})"
        back = f"rotate({n(-ang)}) translate({n(-x)} {n(-y)})"   # filter in viewBox space, so its noise matches the still
        fa += g(wrap(cls, g(mo.ink(g(flag_art(fl), tr)), back)), tr)
        fb += g(wrap(cls, halo(flag_art(fl), H)), tr)
    string = unmark(piece(body, "b-string"))
    bk.append(pivot("cv-bunting", bx, by, halo(string, H) + fb))
    art.append(pivot("cv-bunting", bx, by, mo.ink(string) + fa))

    # ---- teakettle steam -------------------------------------------------------------------
    pz = unmark(piece(body, "k-steam"))
    mo.anim("cv-steam", moves([(0, 0, 0, 1, None), (30, 2, -11, 0, None), (30.3, -1, 6, 0, None), (58, 0, 0, 1, None),
                               (100, 0, 0, 1, None)]), 3.4, -1.2, "ease-in-out")
    kbk = [wrap("cv-steam", halo(pz, H))]
    art.append(wrap("cv-steam", mo.ink(pz)))
    for i, (x, y, dur, delay) in enumerate(((651, 404, 4.4, -2.0), (644, 393, 5.0, -0.3))):
        cls = f"cv-puffling{i}"
        mo.anim(cls, moves([(0, 0, 0, 1, 1), (40, -5, -16, 0, 1.3), (40.3, 4, 9, 0, 0.5), (70, 0, 0, 1, 1),
                            (100, 0, 0, 1, 1)]), dur, delay, "ease-in-out")
        pz = unmark(piece(body, f"k-bub{i}"))
        kbk.append(pivot(cls, x, y, halo(pz, H)))
        art.append(pivot(cls, x, y, mo.ink(pz)))
    bk.append(mo.clip(rect_d(600, 330, 720, 448), "".join(kbk)))

    # ---- the lifted front leg paws from the knee: down toward the ground, up, back --------
    shin = unmark(piece(body, "front-shin")) + unmark(piece(body, "swoosh"))
    step = rot([(0, 0), (12, 0), (34, 10), (44, 10), (64, -5), (76, -5), (100, 0)])
    mo.anim("cv-step", step, 6.6, -0.9)
    # where the shin's white may show: open air right of the far leg (whose right edge, knee, ankle and pad
    # it follows), below the hull and the lifted thigh, above the ground line
    leg_air = [(704, 598), (800, 598), (800, 714.5), (691, 711.5), (686, 704.5), (676, 702), (667, 699), (694, 638),
               (697, 630), (693, 623), (692, 610)]
    bk.append(mo.clip(poly_d(leg_air), pivot("cv-step", 692, 610, halo(shin, H))))
    art.append(pivot("cv-step", 692, 610, mo.ink(shin)))
    art.append(mo.ink(unmark(piece(body, "front-knee"))))   # the knee plate stays over the swinging shin
    for j in range(2):                      # dust shaken off the pad as it moves, back once it is up again
        mo.anim(f"cv-dust{j}", moves([(0, 0, 0, 1, None), (10, 0, 4 + 2 * j, 0.7, None), (24, 0, 11 + 3 * j, 0, None),
                                      (86 + 3 * j, 0, 0, 0, None), (95, 0, 0, 1, None), (100, 0, 0, 1, None)]), 6.6, -0.9,
                "ease-in")
    dbk = ""
    for i in range(len(DUST)):
        pz = unmark(piece(body, f"dust{i}"))
        dbk += wrap(f"cv-dust{i % 2}", halo(pz, H))
        art.append(wrap(f"cv-dust{i % 2}", mo.ink(pz)))
    bk.append(mo.clip(rect_d(690, 690, 770, 711), dbk))       # white only above the ground line

    # ---- snail head: eye stalks sway, eyes blink and look, headlamp rays pulse -------------
    hh = H / 1.08
    mo.anim("cv-blink", blink(6.1, (3.4, 3.75)), 6.1, -1.0)
    mo.anim("cv-glance", moves([(0, 0, 0, None, None), (30, 0, 0, None, None), (34, -7, -3, None, None),
                                (52, -7, -3, None, None), (56, 0, 0, None, None), (100, 0, 0, None, None)]), 8.3, -3.1)
    stalk_sway = [(0, 0), (22, 2.6), (50, -2.2), (74, 1.2), (100, 0)]
    mo.anim("cv-stalkr", rot(stalk_sway), 6.4, -0.4)
    mo.anim("cv-stalkl", rot(stalk_sway), 6.4, -0.65)

    def eye_parts(name, ed, r_look):
        cx, cy, r, ppx, ppy = ed
        er = piece(body, name)
        ring = unmark(piece(er, f"{name}-ring"))
        glint = unmark(piece(er, f"{name}-glint"))
        k = mo.uid("q")
        cd = circ(cx, cy, r)
        mo.defs.append(f'<clipPath id="{k}"><path d="{cd}"/></clipPath>')
        shade = F(circ(cx + r * 0.35, cy + r * 0.45, r * 0.9), DL) + P(circ(cx - r * 0.15, cy - r * 0.2, r * 0.95), W, 0)
        lid = L(f"M{n(cx - r)} {n(cy + r * 0.62)}Q{n(cx)} {n(cy + r * 0.28)} {n(cx + r)} {n(cy + r * 0.62)}", 2.4)
        wx, wy = tf_head(cx, cy)
        wpx, wpy = tf_head(ppx, ppy)
        s = 1.08
        pupil = (Ew(wpx, wpy, r * 0.5 * s, r * 0.58 * s, INK) + Cw(*tf_head(ppx - r * 0.18, ppy - r * 0.22), r * 0.17 * s, W)
                 + Cw(*tf_head(ppx + r * 0.2, ppy + r * 0.2), r * 0.07 * s, W))
        ball = (g(f'<path d="{cd}" fill="{W}"/><g clip-path="url(#{k})">{shade}</g>', HEAD_TR)
                + mo.clip(circ_w(wx, wy, r * s), look(r_look, "cv-glance", pupil))
                + g(f'<g clip-path="url(#{k})">{lid}</g><path d="{cd}" fill="none" stroke="{INK}" stroke-width="3.6"/>', HEAD_TR))
        return g(ring, HEAD_TR) + pivot("cv-blink", wx, wy, ball) + g(glint, HEAD_TR), halo(unmark(er), hh)

    eye_r, eye_r_bk = eye_parts("eye-r", EYE_R, 7.6)
    eye_l, eye_l_bk = eye_parts("eye-l", EYE_L, 8.5)
    wr, wl = tf_head(*PIVOT_R), tf_head(*PIVOT_L)
    st_r, st_l, strap = (unmark(piece(body, k)) for k in ("stalk-r", "stalk-l", "strap"))
    dome = outside([tf_head(*p) for p in dome_offset(DOME_GAP)], (705, 110, 930, 320))
    # the backing stops 1 further out, so its antialiased white never shows through the art's clip edge
    dome_bk = outside([tf_head(*p) for p in dome_offset(DOME_GAP + 1)], (705, 110, 930, 320))
    bk.append(mo.clip(dome_bk, pivot("cv-stalkl", *wl, g(halo(strap, hh), HEAD_TR))
                      + pivot("cv-stalkr", *wr, g(halo(st_r, hh) + eye_r_bk, HEAD_TR))
                      + pivot("cv-stalkl", *wl, g(halo(st_l, hh) + eye_l_bk, HEAD_TR)), True))
    art.append(mo.clip(dome, pivot("cv-stalkl", *wl, mo.ink(g(strap, HEAD_TR)))
                       + pivot("cv-stalkr", *wr, mo.ink(g(st_r, HEAD_TR) + eye_r))
                       + pivot("cv-stalkl", *wl, mo.ink(g(st_l, HEAD_TR) + eye_l)), True))
    rays = unmark(piece(body, "rays"))
    hx, hy = tf_head(*LAMP)
    mo.anim("cv-headlamp", [(0, "transform:scale(1);opacity:1"), (9, "transform:scale(1.14);opacity:.5"),
                            (20, "transform:scale(1);opacity:1"), (31, "transform:scale(1.14);opacity:.5"),
                            (44, "transform:scale(1);opacity:1"), (100, "transform:scale(1);opacity:1")], 3.3, -0.2)
    bk.append(pivot("cv-headlamp", hx, hy, g(halo(rays, hh), HEAD_TR)))
    art.append(pivot("cv-headlamp", hx, hy, mo.ink(g(rays, HEAD_TR))))

    patterns = "".join(re.findall(r"<pattern .*?</pattern>", DEFS))
    css = ("\n".join(mo.css) + "\n@media (prefers-reduced-motion: reduce){\n"
           + ",".join("." + c for c in mo.classes) + "{animation:none!important}}")
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 800" width="1000" height="800" aria-hidden="true">'
            f"<defs>{patterns}{''.join(mo.defs)}</defs><style>\n{css}\n</style>"
            '<g stroke-linecap="round" stroke-linejoin="round">'
            f"<g>{''.join(bk)}</g>{''.join(art)}</g></svg>")


def main():
    body = drawing()
    for path, svg in ((OUT, page(unmark(body))), (OUT_BASE, base_svg(body)), (OUT_MOTION, motion_svg(body))):
        with open(path, "w") as fh:
            fh.write(svg)
        print(f"wrote {os.path.normpath(path)} ({len(svg) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
