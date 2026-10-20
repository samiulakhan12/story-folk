#!/usr/bin/env python3
"""Builds ../assets/duo.svg: Pip and Juniper heading out on an adventure together.

Pip (front-left) holds his brass lantern up high; Juniper (behind-right) leans on a
walking staff, a bedroll on her back, and the two of them hold a map between them.
Path data is hand-written; Python only assembles groups, clips, mirrored parts and
repeated texture marks.  Standard library only:  python3 tools/generate-duo.py
"""
import math
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "duo.svg")

INK = "#111"
W = "#fff"
DL, DM, DD, HA, CH = ("url(#dots-light)", "url(#dots-mid)", "url(#dots-dark)",
                      "url(#hatch)", "url(#crosshatch)")

_n = [0]


def nid():
    _n[0] += 1
    return f"du{_n[0]}"


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


# --- primitives -------------------------------------------------------------
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
    return (f"M{n(cx - r)} {n(cy)}A{n(r)} {n(r)} 0 1 0 {n(cx + r)} {n(cy)}"
            f"A{n(r)} {n(r)} 0 1 0 {n(cx - r)} {n(cy)}Z")


def ell(cx, cy, rx, ry):
    return (f"M{n(cx - rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(cx + rx)} {n(cy)}"
            f"A{n(rx)} {n(ry)} 0 1 0 {n(cx - rx)} {n(cy)}Z")


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
    """closed path through pts whose edges bulge outward (fluff, pom-poms)"""
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


def fuzz(cx, cy, r, k=13, jitter=0.18, seed=1):
    rnd = random.Random(seed)
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k + rnd.uniform(-0.12, 0.12)
        rr = r * (1 + rnd.uniform(-jitter, jitter) * 0.5)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return scallop(pts, 0.36)


def flicks(box, count, seed, length=(4, 8), ang=(20, 70), w=1.5):
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


def specks(box, count, seed, r=(0.8, 1.5)):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    return "".join(C(rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(*r), INK) for _ in range(count))


def tufts(pts, size=8, w=1.8):
    """little grass tufts at the given ground points"""
    out = []
    for x, y in pts:
        s = size
        out.append(L(f"M{n(x - s * 0.7)} {n(y - s)}Q{n(x - s * 0.2)} {n(y - s * 0.3)} {n(x)} {n(y)}"
                     f"Q{n(x + s * 0.1)} {n(y - s * 0.8)} {n(x + s * 0.2)} {n(y - s * 1.4)}"
                     f"M{n(x)} {n(y)}Q{n(x + s * 0.35)} {n(y - s * 0.4)} {n(x + s * 0.8)} {n(y - s * 0.9)}", w))
    return "".join(out)


def stitches(d, sw=1.4):
    return L(d, sw, extra='stroke-dasharray="3 3.6"')


def g(content, tr=None, extra=""):
    t = f' transform="{tr}"' if tr else ""
    return f"<g{t}{' ' + extra if extra else ''}>{content}</g>"


def mir(d, ax):
    """mirror an absolute M/L/C/Q/Z path about the vertical line x = ax"""
    toks = re.findall(r"[MLCQZ]|-?\d*\.?\d+", d)
    out, nums = [], []
    for t in toks:
        if t in "MLCQZ":
            out.append(t)
        else:
            nums.append(float(t))
            if len(nums) == 2:
                out.append(f"{n(2 * ax - nums[0])} {n(nums[1])}")
                nums = []
    s = ""
    for t in out:
        s += t if t in "MLCQZ" else (t if s and s[-1] in "MLCQZ" else " " + t)
    return s


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


def spiral(cx, cy, rx, ry, turns=2.2, steps=40, rot=0):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = t * turns * 2 * math.pi + rot
        pts.append((cx + math.cos(a) * rx * t, cy + math.sin(a) * ry * t))
    return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts)


def densify(pts, step):
    path = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        k = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for j in range(k):
            t = j / k
            path.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    path.append(pts[-1])
    return path


# ---------------------------------------------------------------------------
# GROUND — one shared halftone shadow
# ---------------------------------------------------------------------------
def ground():
    o = []
    o.append(E(352, 793, 286, 19, DM))
    for cx, rx in ((204, 52), (296, 52), (398, 58), (544, 58)):
        o.append(E(cx, 795, rx, 6.5, DD))
    o.append(E(621, 792, 12, 3.4, DD))
    o.append(T(70, 793, 90, 791, 112, 793, 1.6) + T(592, 793, 612, 795, 640, 793, 1.6))
    o.append(T(120, 800, 150, 802, 178, 800, 1.4) + T(520, 802, 548, 804, 574, 801, 1.4))
    o.append(tufts([(86, 790), (634, 791), (664, 794)], 9))
    o.append(E(104, 795, 6, 3.6, W, 2.4) + E(652, 798, 4.6, 3, W, 2.2) + E(120, 798, 3, 2, W, 2))
    return "".join(o)


# ---------------------------------------------------------------------------
# JUNIPER — behind-right: staff, bedroll, satchel, spyglass, braids, aviator cap
# ---------------------------------------------------------------------------
def braid(pts, seed, w=12.5):
    """front-view braid: ink lobes separated by white weave lines, string tie, tuft"""
    out = []
    k = w / 6.8
    path = densify(pts, w * 1.05)
    dline = "M" + "L".join(f"{n(x)} {n(y)}" for x, y in path)
    out.append(L(dline, w * 1.9 + 6))
    lobes = []
    for i, (x, y) in enumerate(path[:-1]):
        dx, dy = path[i + 1][0] - x, path[i + 1][1] - y
        a = math.degrees(math.atan2(dy, dx))
        side = 1 if i % 2 else -1
        nx, ny = -dy, dx
        ln = math.hypot(nx, ny) or 1
        cx, cy = x + nx / ln * side * 2.4 * k, y + ny / ln * side * 2.4 * k
        lobes.append(E(cx, cy, w * 1.02, w * 0.58, INK, 0, a + side * 40))
        lobes.append(f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(w * 1.02)}" ry="{n(w * 0.58)}" fill="none" '
                     f'stroke="{W}" stroke-width="2" transform="rotate({n(a + side * 40)} {n(cx)} {n(cy)})"/>')
        hx, hy = cx - nx / ln * side * 1.2 * k, cy - ny / ln * side * 1.2 * k
        lobes.append(T(hx - dx * 0.3, hy - dy * 0.3, hx, hy, hx + dx * 0.3, hy + dy * 0.3, 1.6, W))
    k2 = nid()
    # clip the lobes to a tube round the braid's centre line (clipPath ignores strokes)
    out.append(f'<clipPath id="{k2}"><path d="{tube(path, w * 1.9, w * 1.9)}"/></clipPath>')
    out.append(f'<g clip-path="url(#{k2})">{"".join(lobes)}</g>')
    (xa, ya), (xb, yb) = path[-2], path[-1]
    a = math.degrees(math.atan2(yb - ya, xb - xa))
    tie = (f'<g transform="translate({n(xb)} {n(yb)}) rotate({n(a)}) scale(1.6)">'
           + P("M-3 -7L4 -7L4 7L-3 7Z", W, 2) + L("M-0.5 -7L0.5 7M2 -7L2.5 7", 1)
           + P("M4 -5.5L15 -9.5L12 -3L19 -1L12 2.5L16 9L4 5.5Z", INK, 0)
           + L("M1 6.5Q-2 12 -7 13M1 6.5Q5 12 2 16", 1.3)
           + "</g>")
    out.append(tie)
    return "".join(out)


def juniper():
    o = []

    # bedroll on her back (only its rolled ends show past her shoulders)
    roll = "M356 318L584 318L584 374L356 374Z"
    o.append(S(roll, DM, 4.5, F("M368 314L392 314L392 380L368 380Z", W)
                + F("M548 314L572 314L572 380L548 380Z", W)
                + L("M372 314L372 380M388 314L388 380M552 314L552 380M568 314L568 380", 2.2)
                + T(360, 334, 470, 330, 580, 334, 1.6, W)))
    for x in (380, 560):  # rope ties
        o.append(P(f"M{x - 5} 314L{x + 5} 314L{x + 5} 378L{x - 5} 378Z", W, 3))
        o.append("".join(L(f"M{x - 5} {y}L{x + 5} {y - 6}", 1.6) for y in range(322, 380, 8)))
    for cx in (356, 584):
        o.append(S(ell(cx, 346, 14, 28), W, 4.5,
                   F(ell(cx + 5, 352, 14, 28), DL) + L(spiral(cx, 346, 11, 23, 2.4, 50, 1.2), 2)))

    # tall striped socks
    sock = "M401 646L447 646L443 744L405 744Z"
    for dd, shade in ((sock, "M428 640L452 640L448 750L428 750Z"),
                      (mir(sock, 471), "M524 640L550 640L546 750L524 750Z")):
        stripes = "".join(F(f"M380 {y}L560 {y}L560 {y + 9}L380 {y + 9}Z", DD) for y in (664, 686, 708, 730))
        o.append(S(dd, W, 4.5, F(shade, DL) + stripes))
    # sneakers: near one points left, far one points right
    shoe = ("M403 734L447 734C453 750 455 768 452 780C450 788 442 790 430 790L366 790"
            "C350 790 344 782 348 772C354 758 374 752 396 748C398 744 400 739 403 734Z")
    sole = "M345 774C341 787 350 796 366 796L430 796C447 796 456 788 454 777C448 784 440 786 430 786L366 786C355 786 349 781 345 774Z"
    toe = "M346 774C352 759 374 752 395 750C391 761 390 774 392 788L366 788C352 788 344 783 346 774Z"
    for sh, so, tc, shade in ((shoe, sole, toe, "M430 728L460 728L460 792L430 792Z"),
                              (mir(shoe, 471), mir(sole, 471), mir(toe, 471), "M570 740L610 740L610 792L570 792Z")):
        o.append(S(sh, W, 4.8, F(shade, DM) + P(tc, HA, 2.6)))
        o.append(P(so, INK, 2.4))
    lace = "M407 740L441 746M441 740L407 746M409 750L440 755M440 750L409 755"
    o.append(L(lace, 2) + L(mir(lace, 471), 2))
    o.append("".join(L(f"M{x} 788L{x + 2} 794", 1.6, W) for x in (364, 378, 392, 406, 420, 434)))
    o.append("".join(L(f"M{x} 788L{x - 2} 794", 1.6, W) for x in (578, 564, 550, 536, 522, 508)))
    o.append(stitches("M352 778C372 781 410 782 446 778") + stitches(mir("M352 778C372 781 410 782 446 778", 471)))

    # patched trousers with rolled cuffs
    trousers = ("M408 484L532 484C544 534 550 596 552 652L488 656C484 628 478 602 470 582"
                "C462 602 456 628 452 656L388 652C390 596 396 534 408 484Z")
    o.append(S(trousers, W, 5,
               F("M520 478L558 478L562 664L532 664C532 610 530 540 520 478Z", DM)
               + F("M396 480L548 480L548 506Q470 512 396 506Z", DM)
               + F("M470 570L482 600L490 664L500 664L490 600L476 560Z", DM)
               + F("M458 592L470 570L462 610L456 664L446 664Z", DL)
               + P("M410 588L440 585L442 616L412 619Z", DL, 2.6)
               + stitches("M414 592L436 590L438 612L416 614Z")
               + P("M500 514L526 512L528 540L503 542Z", W, 2.4)
               + L("M506 520L520 534M520 520L506 534", 1.8)
               + T(414, 540, 426, 532, 432, 520, 1.8) + T(512, 590, 520, 600, 520, 616, 1.8)
               + T(452, 520, 460, 540, 466, 554, 1.6) + T(476, 540, 484, 556, 486, 574, 1.6)
               + T(398, 566, 404, 560, 412, 562, 1.4) + T(528, 562, 536, 556, 542, 560, 1.4)
               + L("M412 640Q424 634 440 640", 1.8) + L("M500 640Q516 634 532 640", 1.8)
               + flicks((400, 500, 450, 570), 7, 31, (3, 6), (30, 70), 1.1)
               + flicks((480, 590, 540, 630), 5, 33, (3, 6), (30, 70), 1.1)))
    cuff_n = "M386 642C410 646 432 648 455 646L453 668C430 670 408 668 384 664Z"
    fold = "M386 654C410 657 432 659 454 657"
    o.append(S(cuff_n, W, 4.5, F("M430 636L460 636L460 674L430 674Z", DM) + L(fold, 2)))
    o.append(S(mir(cuff_n, 471), W, 4.5, F("M524 636L560 636L560 674L524 674Z", DM) + L(mir(fold, 471), 2)))

    # neck
    o.append(S("M455 296L487 296L489 342L453 342Z", W, 4.5, F("M440 290L500 290L500 320L440 320Z", DL)))

    # shirt
    shirt = "M412 334C400 372 400 440 410 488L530 488C540 440 540 372 528 334C506 324 434 324 412 334Z"
    o.append(S(shirt, W, 5,
               F("M508 320C532 360 534 430 528 496L548 496L548 320Z", DM)
               + T(422, 440, 426, 456, 424, 472, 1.8) + T(514, 372, 508, 398, 512, 424, 1.8)
               + T(440, 474, 452, 466, 466, 472, 1.6) + T(490, 470, 500, 464, 512, 470, 1.6)
               + "".join(C(470, y, 2.4, W, 1.8) for y in (372, 440, 466))))
    o.append(P("M444 330L467 362L470 338Z", W, 3.2) + P("M496 330L473 362L470 338Z", W, 3.2))
    o.append(P("M503 346L509 344L513 372L507 374Z", W, 2.4) + P("M503 346L506 336L509 344Z", DD, 1.8))
    o.append(S("M488 360L524 358L525 392L490 394Z", W, 3.2, F("M512 350L530 350L530 400L512 400Z", DM)
               + stitches("M492 366L521 364L522 389")))
    o.append(P("M486 356L526 354L527 368Q507 372 487 370Z", W, 3) + C(507, 364, 2.4, INK))

    # belt
    o.append(P("M407 478L533 478L534 497L406 497Z", INK, 2.4))
    o.append(L("M412 483L456 483M488 483L528 483M412 492L456 492M488 492L528 492", 1.3, W, 'stroke-dasharray="3 3.6"'))
    o.append(P("M458 473L484 473L484 502L458 502Z", W, 3) + L("M465 487L481 487", 2.4)
             + P("M492 476L499 476L499 499L492 499Z", W, 2))

    # brass spyglass tucked under the satchel strap
    glass = (S("M0 -7L15 -7L15 7L0 7Z", W, 3, F("M0 1.5L15 1.5L15 8L0 8Z", DM))
             + P("M15 -9.5L20 -9.5L20 9.5L15 9.5Z", DD, 2.6)
             + S("M20 -10L45 -10L45 10L20 10Z", W, 3.4, F("M20 3L45 3L45 11L20 11Z", DM))
             + P("M45 -12L51 -12L51 12L51 12L45 12Z", DD, 2.6)
             + S("M51 -12L76 -12.5L76 12.5L51 12Z", W, 3.6, F("M51 4L76 4L76 13L51 13Z", DM))
             + P("M76 -14.5L83 -14.5L83 14.5L76 14.5Z", DD, 2.6)
             + S("M83 -14L94 -17L94 17L83 14Z", W, 3.4, F("M83 5L94 5L94 18L83 18Z", DM))
             + E(95, 0, 4, 17, DL, 3) + T(94, -12, 96, -4, 95, 4, 1.4, W)
             + L("M24 -5.5L41 -5.5M55 -7L72 -7", 2, W))
    o.append(g(glass, "translate(424 412) rotate(-9)"))
    o.append(L("M424 402L410 398M424 422L408 428", 2))

    # satchel strap from near shoulder to far hip
    o.append(P("M410 344L424 330L548 504L534 518Z", DL, 3.2))
    o.append(stitches("M416 342L538 510") + stitches("M422 334L544 504"))
    o.append(P("M454 382L470 372L476 380L460 390Z", W, 2.2))

    # satchel on the far hip with rolled maps poking out
    for (x0, y0, x1, y1, rr) in ((540, 534, 538, 466, 10), (566, 536, 572, 470, 9)):
        o.append(S(tube([(x0, y0), (x1, y1)], rr * 2, rr * 2), W, 3.6,
                   F(tube([(x0 + rr * 0.6, y0), (x1 + rr * 0.6, y1)], rr * 0.9, rr * 0.9), DL)))
        a = math.degrees(math.atan2(y1 - y0, x1 - x0))
        mx, my = x0 + (x1 - x0) * 0.62, y0 + (y1 - y0) * 0.62
        o.append(g(L(f"M0 {-rr}L0 {rr}", 2.2) + L(f"M4 {-rr}L4 {rr}", 1.6), f"translate({n(mx)} {n(my)}) rotate({n(a + 90)})"))
        o.append(g(E(0, 0, rr, rr * 0.42, W, 3) + L(spiral(0, 0, rr * 0.75, rr * 0.3, 1.6, 24), 1.4),
                   f"translate({x1} {y1}) rotate({n(a + 90)})"))
    bag = "M498 516C496 548 500 578 506 600L582 600C590 578 592 546 588 516Z"
    o.append(S(bag, W, 4.8, F("M560 510C576 540 578 580 570 606L600 606L600 510Z", DM)
               + F("M490 586C530 592 560 592 600 586L600 606L490 606Z", DL)
               + stitches("M506 592C530 595 560 595 580 592")
               + T(512, 566, 516, 580, 514, 594, 1.6)))
    flap = "M494 508L592 508C594 534 582 552 543 556C506 552 492 534 494 508Z"
    o.append(S(flap, DL, 4.4, P("M490 500L540 500C520 512 508 528 504 552L490 552Z", W, 0)
               + stitches("M502 516C504 536 520 546 543 548C566 546 582 536 584 516")))
    o.append(P("M536 538L551 538L551 572L536 572Z", W, 2.8) + P("M533 556L554 556L554 568L533 568Z", "none", 2.6))

    # walking staff (gnarled stick) planted by her far foot
    cl = [(592, 62), (594, 140), (591, 230), (597, 330), (603, 430), (608, 530), (614, 640), (620, 790)]
    o.append(S(tube(cl, 17, 12), W, 4.5,
               F(tube([(x + 5, y) for x, y in cl], 8, 6), HA)
               + L("M590 120L592 200M588 260L592 320M598 470L602 520M606 580L611 660M612 700L616 760", 1.5)
               + L("M596 90L597 140M595 360L600 410", 1.4)))
    o.append(S("M588 222C580 216 572 210 564 210C559 214 560 221 566 223C574 227 581 232 588 238Z", W, 3.4,
               F("M566 222L590 222L590 240L566 240Z", HA)) + E(563.5, 215.5, 3, 5.4, W, 2.4, 30))
    o.append(S("M612 596C620 590 630 586 638 586C642 590 641 597 636 599C628 602 620 606 614 608Z", W, 3.4,
               F("M612 598L640 598L640 610L612 610Z", HA)) + E(639, 591.5, 3, 5.4, W, 2.4, -30))
    o.append(L("M586 226Q593 230 600 227", 1.8) + L("M607 598Q613 602 619 599", 1.8))
    o.append(S("M585 70C578 54 584 40 596 38C606 40 610 52 603 70Z", W, 4.4,
               F("M598 34L614 34L612 74L600 74Z", HA) + L("M590 52Q594 46 600 48", 1.6)))
    o.append(L("M597 42C601 30 612 22 624 20", 4) + L("M604 30C602 22 596 18 590 18", 3))
    o.append(S("M623 20C628 10 640 6 650 9C646 20 634 25 623 20Z", W, 3, L("M625 19L645 11", 1.4)))
    o.append(S("M591 18C582 10 570 10 563 16C571 25 584 25 591 18Z", W, 3, L("M590 18L567 16", 1.4)))
    # string charm with a bead
    o.append(L("M588 96C580 104 578 118 582 128M600 98C606 108 606 118 602 130", 2) + C(582, 132, 4.4, DD, 2.2))
    o.append(P("M585 90L601 92L601 100L585 98Z", W, 2.4))
    # leather grip wrap under the hand
    o.append(S("M597 396L613 394L615 438L599 440Z", DL, 3.4,
               "".join(L(f"M594 {y}L618 {y - 8}", 2) for y in range(398, 446, 8))))

    # far arm: rolled sleeve, bare forearm, fist round the staff at her hip
    o.append(S("M518 336C540 330 560 346 572 366C580 378 586 388 588 394L558 414C552 400 542 386 528 376Z", W, 4.6,
               F("M556 336L600 380L566 420L548 392Z", DM) + T(546, 360, 554, 372, 558, 388, 1.6)))
    o.append(S("M553 410C560 396 576 386 586 387C594 392 597 398 595 401C584 404 570 414 562 423C556 420 552 415 553 410Z",
               W, 4.2, F("M578 384L600 384L600 426L578 426Z", DL) + L("M557 414C567 404 579 397 591 395", 1.8)))
    o.append(S("M566 416L590 405C596 418 602 430 606 440L583 452C578 440 572 428 566 416Z", W, 4.4,
               F("M588 404L610 404L612 444L594 448Z", DL) + T(574, 426, 578, 432, 580, 440, 1.3)))
    o.append(S("M585 448C587 435 603 431 612 439C620 447 620 463 611 470C601 475 588 471 586 461Z", W, 4.4,
               F("M606 432L624 432L624 476L606 476Z", DL)))
    o.append(L("M588 446Q600 448 614 443M587 455Q600 457 616 452M589 464Q600 466 613 461", 1.9)
             + L("M590 440Q586 446 588 452", 1.8))

    # near arm: rolled sleeve and forearm down to the map
    o.append(S("M414 336C396 344 386 376 384 418L410 424C410 398 414 372 424 352Z", W, 4.6,
               F("M404 360L426 360L414 428L400 428Z", DL) + T(396, 380, 398, 392, 400, 404, 1.5)))
    o.append(S("M381 412C392 404 406 406 416 412C420 420 420 430 416 438C405 432 391 432 381 438C377 430 377 420 381 412Z",
               W, 4.2, F("M404 402L424 402L424 444L404 444Z", DL) + L("M382 425C392 419 404 419 416 424", 1.8)))
    o.append(S("M385 436C387 462 394 488 401 512L424 506C418 482 413 458 413 436Z", W, 4.6,
               F("M404 436L420 436L428 510L414 512Z", DL) + T(392, 470, 396, 480, 400, 490, 1.4)))

    # braids hanging from under the cap, over her shoulders
    o.append(braid([(398, 282), (390, 322), (389, 362), (395, 400), (402, 426)], 1))
    o.append(braid([(542, 282), (550, 322), (551, 362), (545, 400), (538, 426)], 2))

    # head (tilted a touch): face, bangs, fleece trim, aviator cap with ear flaps, features
    h = []
    h.append(S(circ(470, 234, 78), W, 5, F(circ(470, 234, 78), DL) + P(circ(461, 225, 80), W, 0)))
    for d in ("M430 206Q436 238 452 208Z", "M450 202Q462 236 474 202Z", "M472 202Q484 232 494 204Z",
              "M492 206Q502 228 512 210Z"):
        h.append(P(d, INK, 0))
    opening = [(412, 296), (413, 270), (415, 248), (418, 228), (424, 212), (436, 200), (452, 193), (470, 191),
               (488, 193), (504, 200), (516, 212), (522, 228), (525, 248), (527, 270), (528, 296)]
    h.append(fleece(opening, 470, 250))
    cap = ("M411 290C405 306 385 306 379 290C372 256 372 212 382 186C396 162 430 146 470 146"
           "C510 146 544 162 558 186C568 212 568 256 561 290C555 306 535 306 529 290"
           "C527 264 525 238 521 218C506 198 490 190 470 190C450 190 434 198 419 218C415 238 413 264 411 290Z")
    h.append(S(cap, DL, 5.2,
               P("M378 232C374 190 412 154 466 152C432 168 410 196 404 232Z", W, 0)
               + F("M522 146C560 162 576 202 572 250L572 320L548 320C556 262 552 198 522 146Z", HA)
               + L("M470 148L470 190", 2.6) + stitches("M477 150L477 190") + stitches("M463 150L463 190")
               + L("M432 156C414 170 402 190 400 208", 2.2) + L("M508 156C526 170 538 190 540 208", 2.2)
               + stitches("M425 162C409 176 398 192 396 210") + stitches("M515 162C531 176 542 192 544 210")
               + L("M378 208C392 212 406 216 418 222", 2.6) + L("M562 208C548 212 534 216 522 222", 2.6)
               + stitches("M386 224C382 250 384 274 392 294") + stitches("M554 224C558 250 556 274 548 294")
               + T(442, 166, 446, 172, 450, 180, 1.4) + T(494, 162, 498, 168, 500, 176, 1.4)
               + T(530, 178, 532, 186, 532, 194, 1.4) + T(410, 184, 411, 190, 411, 198, 1.4)
               + T(388, 250, 390, 258, 389, 266, 1.4) + T(552, 246, 553, 254, 552, 262, 1.4)))
    # buckle strap dangling from the far flap
    h.append(L("M545 302C548 312 550 320 548 330", 4.6) + L("M545 302C548 312 550 320 548 330", 2, W)
             + P("M541 322L555 322L555 334L541 334Z", W, 2.4))
    # eyes
    h.append(E(445, 252, 10, 13, INK) + E(495, 252, 10, 13, INK))
    h.append(C(441, 246.5, 3.8) + C(491, 246.5, 3.8) + C(448.5, 258, 1.5) + C(498.5, 258, 1.5))
    # determined brows
    h.append(T(427, 230, 440, 225, 456, 234, 3.4) + T(484, 234, 500, 225, 513, 230, 3.4))
    h.append(L("M465 270Q470 275 475 270", 2.4))
    # determined smile with a little smirk
    h.append(P("M448 281Q472 302 496 277Q472 289 448 281Z", INK, 0))
    h.append(T(494, 279, 498, 275, 500, 270, 1.6) + T(449, 284, 446, 282, 445, 279, 1.2))
    h.append(E(513, 278, 11.5, 7, DL))
    h.append(g(P("M-13 -5L13 -5L13 5L-13 5Z", W, 2.4) + P("M-4.5 -5L4.5 -5L4.5 5L-4.5 5Z", DL, 0)
               + L("M-4.5 -5L-4.5 5M4.5 -5L4.5 5", 1.4) + C(-9, -1.5, 0.9, INK) + C(-9, 1.8, 0.9, INK)
               + C(9, -1.5, 0.9, INK) + C(9, 1.8, 0.9, INK), "translate(427 274) rotate(-24)"))
    o.append(g("".join(h), "rotate(-4 470 320)"))
    return "".join(o)


def fleece(pts, cx, cy, out=5, inn=10):
    """scalloped fleece band along a polyline; bumps face the point (cx, cy)"""
    dense = densify(pts, 11)
    outer, inner = [], []
    for i, (x, y) in enumerate(dense):
        a = dense[max(0, i - 1)]
        b = dense[min(len(dense) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        if (cx - x) * nx + (cy - y) * ny < 0:
            nx, ny = -nx, -ny
        outer.append((x - nx * out, y - ny * out))
        inner.append((x + nx * inn, y + ny * inn, nx, ny))
    d = "M" + "L".join(f"{n(x)} {n(y)}" for x, y in outer)
    rev = inner[::-1]
    d += f"L{n(rev[0][0])} {n(rev[0][1])}"
    for i in range(1, len(rev)):
        (x0, y0, nx, ny), (x1, y1, _, _) = rev[i - 1], rev[i]
        d += f"Q{n((x0 + x1) / 2 + nx * 7)} {n((y0 + y1) / 2 + ny * 7)} {n(x1)} {n(y1)}"
    d += "Z"
    return S(d, W, 3, F(d, "none") + "".join(T(x - 2, y - 2, x, y, x + 2, y + 2, 1, INK) for x, y, _, _ in inner[1::2]))


# ---------------------------------------------------------------------------
# THE MAP — held between Juniper's near hand and Pip's free hand
# ---------------------------------------------------------------------------
def shared_map():
    o = []
    sheet = "M352 508C370 502 392 500 414 496L416 574C394 576 372 582 354 588Z"
    o.append(S(sheet, W, 3.6,
               F("M394 494L420 494L420 580L398 580C402 552 400 520 394 494Z", DL)
               + L("M362 574C372 562 364 548 378 542C392 536 384 522 398 514", 2, extra='stroke-dasharray="4 4"')
               + L("M393 506L405 518M405 506L393 518", 3)
               + P("M362 534L370 520L378 534Z", W, 1.8) + P("M372 530L382 512L392 530Z", HA, 1.8)
               + L("M386 560Q391 556 396 560Q401 564 406 560M384 568Q389 564 394 568Q399 572 404 568", 1.4)
               + L("M383 500L384 590", 1.2, extra='stroke-dasharray="2 4"')
               + T(366, 556, 365, 550, 366, 544, 1.6) + C(366, 559, 2.2, INK)))
    o.append(S("M344 506C344 500 358 500 358 506L360 588C360 595 346 595 344 588Z", W, 3.6,
               F("M352 500L362 500L362 596L352 596Z", DM)))
    o.append(E(351, 505, 7, 3.2, W, 2.6) + L(spiral(351, 505, 4.6, 2, 1.5, 20), 1.2))
    o.append(S("M408 494C408 488 422 488 422 494L424 576C424 583 410 583 408 576Z", W, 3.6,
               F("M416 488L426 488L426 584L416 584Z", DM)))
    o.append(E(415, 493, 7, 3.2, W, 2.6) + L(spiral(415, 493, 4.6, 2, 1.5, 20), 1.2))
    # Juniper's near hand gripping the right-hand roll
    o.append(S("M398 512C396 524 402 537 414 538C427 538 433 528 431 516C429 506 419 502 410 503C404 504 400 508 398 512Z",
               W, 4.2, F("M416 500L436 500L436 540L416 540Z", DL)))
    o.append(L("M400 518Q410 520 420 516M400 526Q410 528 421 524", 1.8) + L("M424 508Q430 512 428 520", 2))
    return "".join(o)


# ---------------------------------------------------------------------------
# PIP — front-left: lantern held high, grin, beanie with goggles, striped scarf
# ---------------------------------------------------------------------------
def lantern():
    """local frame: origin where the bail leaves the fist, lantern hangs along +y"""
    o = []
    for i, a in enumerate(range(20, 261, 30)):
        r0 = 50 if i % 2 else 54
        o.append(ray(0, 60, a, r0, r0 + (24 if i % 2 else 16), 3.2 if i % 2 else 2.6))
    for x, y, r in ((-52, 20, 6), (44, 112, 5), (-46, 120, 4.5)):
        o.append(T(x - r, y, x, y + 0.5, x + r, y, 1.4) + T(x, y - r, x + 0.5, y, x, y + r, 1.4))
    o.append(L("M-13 28C-14 8 -8 -2 0 -2C8 -2 14 8 13 28", 3.2))
    o.append(S("M-21 37L21 37L15 27C8 20 -8 20 -15 27Z", W, 3.4, F("M2 18L24 18L24 40L2 40Z", DM)))
    o.append(S(circ(0, 19, 4.6), W, 2.6, F(circ(2, 21, 4), DM)))
    o.append(P("M-26 37L26 37L26 44L-26 44Z", DD, 3))
    glass = "M-20 44L20 44L20 88L-20 88Z"
    o.append(S(glass, W, 3.4,
               P("M0 50C7 60 10 68 6 76C3 80 -3 80 -6 76C-10 68 -7 60 0 50Z", W, 2.2)
               + P("M0 61C3 66 4 70 2 74C1 75.5 -1 75.5 -2 74C-4 70 -3 66 0 61Z", INK, 0)
               + L("M-8 44L-8 88M8 44L8 88", 2.2)
               + T(-15, 50, -16, 60, -15, 72, 1.8, INK)
               + F("M10 44L20 44L20 88L10 88Z", DL)))
    o.append(P("M-26 88L26 88L26 95L-26 95Z", DD, 3))
    o.append(S("M-22 95L22 95L17 106L-17 106Z", W, 3.2, F("M2 92L24 92L24 108L2 108Z", DM)))
    o.append(L("M-20 41L-16 41M-6 41L-2 41M8 41L12 41", 1.4, W))
    return "".join(o)


def pip():
    o = []
    # --- scarf tail streaming out behind him (to the right)
    tail = "M292 440C310 432 326 442 342 430C352 422 360 414 370 404L380 426C368 434 360 442 348 450C330 462 312 456 296 466Z"
    o.append(S(tail, W, 4.5, "".join(F(f"M{x} 380L{x + 12} 380L{x + 20} 480L{x + 8} 480Z", DD) for x in (306, 334, 360))
               + L("M300 452C318 446 334 452 350 440", 1.6)))
    o.append(L("M376 404L384 394M380 412L390 405M382 420L392 418", 2.2))
    o.append(T(362, 392, 370, 384, 380, 382, 1.8))

    # --- legs, socks and big lace-up boots (feet planted a little apart)
    shin = "M206 640L236 640L234 712L208 712Z"
    sock = "M201 698Q220 704 239 698L241 724L199 724Z"
    boot = ("M197 718L245 718C247 732 249 746 249 760C249 780 238 792 214 792L178 792"
            "C160 792 151 782 155 770C159 756 175 748 193 742C195 734 195 726 197 718Z")
    bsole = ("M151 773C148 786 158 797 178 797L216 797C240 797 252 786 252 768"
             "C247 779 236 784 216 784L180 784C166 784 156 781 151 773Z")
    btoe = "M156 770C160 757 175 749 192 743C190 756 191 772 196 786L178 786C163 786 153 781 156 770Z"
    laces = "M204 724L238 732M238 724L204 732M204 736L238 744M238 736L204 744M205 748L237 755M237 748L205 755"
    collar = "M193 708L250 708L250 724L193 724Z"
    for side in (0, 1):
        f = (lambda d: d) if side == 0 else (lambda d: mir(d, 249))
        q = []
        shin_sh = "M222 636L240 636L240 716L222 716Z" if side == 0 else "M278 636L296 636L296 716L278 716Z"
        knee = "M212 668Q220 672 228 668" if side == 0 else "M270 668Q278 672 286 668"
        q.append(S(f(shin), W, 4.6, F(shin_sh, DL) + L(knee, 1.8)
                   + (T(214, 690, 218, 686, 224, 688, 1.2) if side == 0 else T(272, 684, 276, 680, 282, 682, 1.2))))
        q.append(S(f(sock), W, 4, "".join(L(f"M{x} 690L{x} 730", 1.5) for x in range(196, 306, 6))))
        shade = "M232 712L256 712L256 792L232 792Z" if side == 0 else "M316 740L350 740L350 792L316 792Z"
        q.append(S(f(boot), W, 5, F(shade, DM) + P(f(btoe), W, 2.6) + F(f(btoe), DL) + L(f(laces), 1.9)
                   + T(*((166, 760, 172, 756, 180, 756) if side == 0 else (318, 756, 326, 756, 332, 760)), 1.3)))
        q.append(P(f(bsole), INK, 2.4))
        for x in ((204, 238) if side == 0 else (260, 294)):
            for y in (724, 736, 748):
                q.append(C(x, y, 1.9, W, 1.4))
        q.append(P(f(collar), W, 3.8))
        q.append(L("M199 716L245 716" if side == 0 else "M253 716L299 716", 1.4, extra='stroke-dasharray="2 3"'))
        xs = (170, 184, 198, 212, 226) if side == 0 else (328, 314, 300, 286, 272)
        q.append("".join(L(f"M{x} 789L{x + (2 if side == 0 else -2)} 795", 1.6, W) for x in xs))
        o.append(g("".join(q), f"translate({-7 if side == 0 else 7} 0)"))

    # --- cargo shorts
    shorts = "M190 592L308 592L316 648Q286 656 258 648L250 626L242 648Q212 656 182 648Z"
    o.append(S(shorts, W, 4.8,
               F("M262 586L320 586L320 660L262 660Z", HA)
               + F("M178 588L322 588L322 614Q250 620 178 614Z", DD)
               + F("M244 626L250 600L256 626L258 652L242 652Z", DM)
               + P("M184 610L206 608L208 638L188 641Z", W, 2.6) + L("M184 618L207 616", 2) + C(196, 613, 1.6, INK)
               + P("M292 608L314 610L310 641L290 638Z", W, 2.6) + L("M292 616L314 618", 2) + C(302, 613, 1.6, INK)
               + T(222, 612, 228, 622, 226, 634, 1.6) + stitches("M186 644Q212 650 240 644")))

    # --- puffy jacket
    jacket = ("M202 446Q178 450 176 478Q164 500 172 524Q162 550 172 574Q168 600 194 604"
              "L304 604Q330 600 326 574Q336 550 326 524Q334 500 322 478Q320 450 296 446Z")
    teeth = "".join(L(f"M246 {y}L252 {y}", 1.4) for y in range(462, 600, 6))
    o.append(S(jacket, W, 5.2,
               F("M290 440Q318 452 318 478Q330 500 320 524Q332 550 322 574Q326 596 300 608L340 608L340 440Z", DM)
               + F("M160 590Q250 600 340 590L340 612L160 612Z", DL)
               + L("M176 479Q249 492 322 479", 2.8) + L("M172 525Q249 538 326 525", 2.8) + L("M172 575Q249 588 326 575", 2.8)
               + stitches("M180 486Q249 498 318 486") + stitches("M176 532Q249 544 322 532")
               + T(184, 505, 196, 500, 206, 506, 1.8) + T(286, 552, 298, 548, 310, 554, 1.8)
               + T(188, 556, 200, 552, 212, 557, 1.6) + T(282, 500, 292, 496, 302, 501, 1.6)
               + L("M249 452L249 604", 2.8) + teeth
               + P("M184 552L232 550L232 590Q208 596 184 592Z", W, 2.8)
               + P("M182 547L234 545L234 562Q208 566 182 564Z", W, 2.8) + C(208, 556, 2.6, INK)
               + stitches("M188 568L228 567L228 586")
               + P("M266 550L314 552L314 592Q290 596 266 590Z", W, 2.8)
               + P("M264 545L316 547L316 564Q290 566 264 562Z", W, 2.8) + C(290, 556, 2.6, INK)
               + stitches("M270 567L310 568L310 586")))
    o.append(P("M244 466L254 466L254 482L244 482Z", W, 2.2))

    # --- raised arm (puffy sleeve, ribbed cuff, fist) and the lantern
    sleeve = ("M225 460Q210 416 184 377Q169 333 144 293L112 307"
              "Q122 353 144 395Q158 440 183 480C192 494 220 484 225 460Z")
    o.append(S(sleeve, W, 5,
               F("M130 293Q155 333 170 377Q196 416 211 460L214 490L250 490L250 280L130 280Z", DM)
               + L("M144 395Q166 392 184 377", 2.8) + stitches("M149 405Q170 401 189 388")
               + T(124, 348, 134, 342, 146, 342, 1.6) + T(156, 440, 166, 432, 178, 432, 1.6)
               + T(170, 470, 178, 462, 190, 462, 1.4)))
    o.append(S("M111 308L147 295L141 279L106 292Z", W, 3.8, "".join(L(f"M{100 + i * 6} 312L{110 + i * 6} 276", 1.5) for i in range(9))))
    o.append(C(122, 244, 6.5, "none", 3))
    o.append(S("M104 266C102 254 112 246 124 248C136 250 142 262 138 274C134 286 120 292 110 286C102 282 102 274 104 266Z",
               W, 4.4, F("M124 244L146 244L146 292L124 292Z", DL)))
    o.append(L("M108 262Q116 258 126 262M107 270Q115 266 126 270", 1.8) + L("M128 254Q134 262 130 272", 2.2))
    o.append(g(lantern(), "translate(112 286) rotate(24)"))
    for mx, my, rot in ((52, 226, -18), (172, 214, 22)):
        moth = (P("M0 0C-6 -12 -18 -14 -20 -6C-21 0 -12 4 0 2Z", DL, 2.4)
                + P("M0 0C6 -12 18 -14 20 -6C21 0 12 4 0 2Z", DL, 2.4)
                + P("M0 1C-4 6 -10 10 -12 6C-12 3 -6 2 0 1Z", W, 2)
                + P("M0 1C4 6 10 10 12 6C12 3 6 2 0 1Z", W, 2)
                + E(0, 0, 2.6, 7, INK) + L("M-1 -6Q-4 -12 -7 -13M1 -6Q4 -12 7 -13", 1.4))
        o.append(g(moth, f"translate({mx} {my}) rotate({rot})"))
        o.append(L(f"M{mx + 14} {my + 12}q6 4 12 2", 1.4, extra='stroke-dasharray="2 3"'))

    # --- free arm reaching to hold the map
    o.append(S("M282 470C300 462 318 470 330 488C340 502 348 516 352 528L326 546C318 532 306 516 294 506Z", W, 5,
               F("M318 470L360 520L340 540L322 520Z", DM) + L("M300 500Q316 496 334 494", 2.4)
               + stitches("M304 510Q318 506 336 504")))
    o.append(S("M326 546L352 528L360 540L334 558Z", W, 3.6, "".join(L(f"M{322 + i * 6} 532L{332 + i * 6} 560", 1.5) for i in range(8))))
    o.append(S("M334 556C330 566 336 579 348 581C360 582 367 573 365 562C363 552 353 548 345 549C340 550 336 552 334 556Z",
               W, 4.2, F("M350 546L370 546L370 584L350 584Z", DL)))
    o.append(L("M337 562Q347 566 358 562M337 570Q347 574 358 570", 1.8))

    # --- front scarf tail (under the wrap)
    ftail = "M210 452C207 478 205 506 203 534L237 536C237 510 238 482 240 456Z"
    o.append(S(ftail, W, 4.6, "".join(F(f"M190 {y}L250 {y + 2}L250 {y + 12}L190 {y + 10}Z", DD) for y in (466, 492, 518))))
    o.append(L("M207 536L205 548M214 537L213 550M221 537L221 551M228 537L229 550M235 536L237 548", 2.2))

    # --- scarf wrap round the neck
    wrap = "M192 426C224 444 272 444 304 426L308 458C274 476 222 476 188 458Z"
    o.append(S(wrap, W, 5, "".join(F(f"M{x} 420L{x + 13} 420L{x + 11} 480L{x - 2} 480Z", DD) for x in (204, 234, 264, 292))
               + L("M192 442C224 460 272 460 306 442", 1.8)))
    o.append(S("M206 450C200 446 196 456 200 466C206 474 222 474 230 466C236 458 232 448 224 448Z", W, 4,
               F("M206 444L220 444L218 476L204 476Z", DD) + L("M214 452Q218 460 214 468", 1.8)))

    # --- ears, face
    o.append(S(circ(184, 384, 13), W, 4.2, F(circ(184, 384, 13), DL) + P(circ(182, 381, 11), W, 0)) + L("M188 378Q181 384 188 390", 1.8))
    o.append(S(circ(313, 384, 13), W, 4.2, F(circ(313, 384, 13), DM)) + L("M309 378Q316 384 309 390", 1.8))
    o.append(S(circ(248, 374, 62), W, 5.2,
               F(circ(248, 374, 62), DL) + P(circ(238, 365, 63), W, 0)
               + F("M180 352C214 340 282 340 316 352L316 370C282 358 214 358 180 370Z", DM)))
    # hair tufts under the cuff
    o.append(P("M190 352L180 374L189 371L184 390L200 368L200 354Z", INK, 0))
    o.append(P("M306 352L316 374L307 371L312 390L296 368L296 354Z", INK, 0))
    o.append(P("M222 356Q228 377 238 356Z", INK, 0) + P("M256 356Q264 374 272 356Z", INK, 0))
    # eyes, brows, nose, grin, cheeks, freckles
    o.append(E(226, 391, 9.5, 13, INK) + E(272, 391, 9.5, 13, INK))
    o.append(C(222.5, 385.5, 3.8) + C(268.5, 385.5, 3.8) + C(229.5, 397, 1.5) + C(275.5, 397, 1.5))
    o.append(T(211, 375, 223, 368, 237, 373, 3) + T(259, 373, 273, 368, 285, 375, 3))
    o.append(L("M243 404Q248 409 253 404", 2.4))
    o.append(P("M227 413Q248 446 269 413Q248 419 227 413Z", INK, 0))
    o.append(P("M232 415Q248 420 264 415L262 421Q248 425 234 421Z", W, 0))
    o.append(P("M238 430Q248 421 259 429Q249 435 238 430Z", DL, 0))
    o.append(T(222, 409, 224, 412, 228, 414, 1.4) + T(274, 409, 272, 412, 268, 414, 1.4))
    o.append(E(205, 410, 12, 7.5, DL) + E(291, 410, 12, 7.5, DL))
    o.append("".join(C(x, y, 1.5, INK) for x, y in ((199, 403), (206, 400), (212, 404), (285, 404), (291, 400), (298, 403))))

    # --- beanie: dome with knit ribs, goggles, ribbed cuff, pom-pom
    pom = fuzz(252, 240, 22, 13, seed=4)
    o.append(S(pom, W, 4.2, F(circ(262, 250, 22), DL) + P(circ(246, 233, 17), W, 0)
               + flicks((236, 224, 270, 256), 16, 11, (3, 6), (0, 180), 1.3)))
    dome = "M184 340C178 296 206 262 248 260C292 262 320 296 314 340Z"
    ribs = ""
    for i in range(11):
        xb = 190 + 12 * i
        ribs += L(f"M{xb} 342Q{n(xb + (248 - xb) * 0.25)} 300 {n(248 + (xb - 248) * 0.3)} 262", 1.5)
    chev = ""
    for y, half in ((330, 1.0), (320, 0.96), (284, 0.75), (274, 0.62)):
        for i in range(10):
            x = 248 + (196 + 12 * i - 248) * half
            chev += L(f"M{n(x - 3)} {y - 3}L{n(x)} {y + 1}L{n(x + 3)} {y - 3}", 1.3)
    o.append(S(dome, W, 5.2, F("M268 254C302 262 324 296 318 344L290 344C298 304 290 274 268 254Z", DM) + ribs + chev))
    o.append(P("M182 302C214 290 282 290 316 302L316 316C282 304 214 304 182 316Z", DD, 3))
    for gx in (222, 274):
        o.append(S(circ(gx, 303, 21), W, 4.6, F(circ(gx + 6, 309, 19), DL)))
        o.append(S(circ(gx, 303, 13.5), DM, 3, P(circ(gx - 4, 299, 10), W, 0)))
        o.append(T(gx - 9, 300, gx - 7, 294, gx - 2, 291, 1.6, INK))
        o.append(C(gx - 15, 303, 1.6, INK) + C(gx + 15, 303, 1.6, INK) + C(gx, 288, 1.6, INK) + C(gx, 318, 1.6, INK))
    o.append(L("M242 298Q248 292 254 298", 4.4))
    cuffb = "M178 338C212 326 284 326 318 338L320 364C284 352 212 352 176 364Z"
    o.append(S(cuffb, W, 5.2, F("M290 320L326 320L326 370L290 370Z", DM)
               + "".join(L(f"M{x} 320Q{x + 1} 345 {x} 370", 1.6) for x in range(182, 320, 7))))
    return "".join(o)


# ---------------------------------------------------------------------------
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
    body = ("<!-- ground -->" + ground()
            + "<!-- juniper -->" + g(juniper(), extra='id="juniper"')
            + "<!-- map -->" + g(shared_map(), extra='id="map"')
            + "<!-- pip -->" + g(pip(), extra='id="pip"'))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 820" width="700" height="820" role="img">'
           "<title>Pip and Juniper heading out on an adventure: Pip holds his brass lantern up high and grins, "
           "Juniper leans on her walking staff with a bedroll on her back, and they share a map between them</title>"
           + DEFS
           + f'<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">{body}</g></svg>')
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
