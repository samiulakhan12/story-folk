#!/usr/bin/env python3
"""Builds ../assets/reader.svg: Wren reading on a tower of three hardback books.

Wren sits cross-legged on the top book with an open book in her lap; Nib the ink sprite
peeks out of its pages, a mug of cocoa steams beside her, and a paper boat and a small
candle sit at the foot of the stack.  Path data is hand-written; Python only assembles
groups, clips, mirrored parts and repeated texture marks.
Standard library only:  python3 tools/generate-reader.py
"""
import math
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "reader.svg")

INK = "#111"
W = "#fff"
DL, DM, DD, HA, CH = ("url(#dots-light)", "url(#dots-mid)", "url(#dots-dark)",
                      "url(#hatch)", "url(#crosshatch)")

_n = [0]


def nid():
    _n[0] += 1
    return f"rd{_n[0]}"


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
# GROUND — halftone shadow under the stack
# ---------------------------------------------------------------------------
def ground():
    o = []
    o.append(E(400, 773, 300, 18, DM))
    o.append(E(392, 772, 236, 6, DD))
    o.append(T(86, 774, 104, 772, 126, 774, 1.6) + T(668, 775, 690, 773, 712, 775, 1.6))
    o.append(T(140, 782, 170, 784, 200, 782, 1.4) + T(600, 783, 630, 785, 656, 782, 1.4))
    return "".join(o)


# ---------------------------------------------------------------------------
# BOOKS — three big hardbacks, stacked a little crooked
# ---------------------------------------------------------------------------
DX, DY = 16, -22


def emblem(kind, cx, cy):
    if kind == "star":
        pts = []
        for i in range(10):
            a = math.radians(-90 + i * 36)
            r = 11 if i % 2 == 0 else 4.6
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        return P("M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts) + "Z", INK, 0)
    if kind == "moon":
        return P(f"M{cx + 3} {cy - 11}C{cx - 12} {cy - 10} {cx - 12} {cy + 10} {cx + 3} {cy + 11}"
                 f"C{cx - 4} {cy + 6} {cx - 4} {cy - 6} {cx + 3} {cy - 11}Z", INK, 0) + C(cx + 8, cy - 5, 1.6, INK) + C(cx + 6, cy + 6, 1.2, INK)
    # leaf
    return (P(f"M{cx - 12} {cy + 6}C{cx - 8} {cy - 8} {cx + 4} {cy - 11} {cx + 13} {cy - 9}"
              f"C{cx + 10} {cy + 2} {cx} {cy + 10} {cx - 12} {cy + 6}Z", INK, 0)
            + L(f"M{cx - 10} {cy + 5}Q{cx} {cy - 2} {cx + 10} {cy - 7}", 1.3, W))


def book(x0, x1, y0, y1, face, cover, emb, seed, ribbon=False):
    o = []
    bd = 10
    top = f"M{x0} {y0}L{x1} {y0}L{x1 + DX} {y0 + DY}L{x0 + DX} {y0 + DY}Z"
    right = f"M{x1} {y0}L{x1 + DX} {y0 + DY}L{x1 + DX} {y1 + DY}L{x1} {y1}Z"
    # top face: cloth cover with a tooled border
    o.append(S(top, cover, 4.6,
               P(f"M{x0 + 14} {y0 - 4}L{x1 - 10} {y0 - 4}L{x1 + DX - 18} {y0 + DY + 5}L{x0 + DX + 8} {y0 + DY + 5}Z",
                 "none", 1.6)))
    # head edge: boards and the page block between them
    pages = "".join(L(f"M{x1} {y}L{x1 + DX} {y + DY}", 1.1) for y in range(y0 + bd + 5, y1 - bd, 5))
    o.append(S(right, W, 4.4,
               F(f"M{x1 - 2} {y0 - 2}L{x1 + DX + 2} {y0 + DY - 2}L{x1 + DX + 2} {y0 + DY + bd}L{x1 - 2} {y0 + bd}Z", cover)
               + F(f"M{x1 - 2} {y1 - bd}L{x1 + DX + 2} {y1 + DY - bd}L{x1 + DX + 2} {y1 + DY + 2}L{x1 - 2} {y1 + 2}Z", cover)
               + pages
               + L(f"M{x1} {y0 + bd}L{x1 + DX} {y0 + DY + bd}M{x1} {y1 - bd}L{x1 + DX} {y1 + DY - bd}", 2.4)))
    if face == "spine":
        front = (f"M{x0} {y0}Q{(x0 + x1) / 2} {y0 - 4} {x1} {y0}L{x1} {y1}"
                 f"Q{(x0 + x1) / 2} {y1 + 4} {x0} {y1}Z")
        mid = (x0 + x1) / 2
        hh = y1 - y0
        inner = (F(f"M{x0 - 4} {y1 - hh * 0.3}L{x1 + 4} {y1 - hh * 0.3}L{x1 + 4} {y1 + 6}L{x0 - 4} {y1 + 6}Z", DD)
                 + T(x0 + 20, y0 + 10, mid, y0 + 7, x1 - 20, y0 + 10, 1.8, W))
        for bx in (x0 + 34, x0 + 52, x1 - 52, x1 - 34):
            inner += P(f"M{bx - 3} {y0 - 4}L{bx + 3} {y0 - 4}L{bx + 3} {y1 + 4}L{bx - 3} {y1 + 4}Z", W, 2.4)
        for gx in (x0 + 64, x1 - 64):
            inner += L(f"M{gx} {y0 + 8}L{gx} {y1 - 8}", 1.6) + L(f"M{gx + (6 if gx < mid else -6)} {y0 + 8}L{gx + (6 if gx < mid else -6)} {y1 - 8}", 1.2)
        lw, lh = 66, 30
        inner += P(f"M{mid - lw} {y0 + hh / 2 - lh}L{mid + lw} {y0 + hh / 2 - lh}L{mid + lw} {y0 + hh / 2 + lh}"
                   f"L{mid - lw} {y0 + hh / 2 + lh}Z", W, 3.2)
        inner += P(f"M{mid - lw + 7} {y0 + hh / 2 - lh + 7}L{mid + lw - 7} {y0 + hh / 2 - lh + 7}"
                   f"L{mid + lw - 7} {y0 + hh / 2 + lh - 7}L{mid - lw + 7} {y0 + hh / 2 + lh - 7}Z", "none", 1.4,
                   'stroke-dasharray="3 3"')
        inner += emblem(emb, mid, y0 + hh / 2)
        inner += L(f"M{mid - 44} {y0 + hh / 2}L{mid - 20} {y0 + hh / 2}M{mid + 20} {y0 + hh / 2}L{mid + 44} {y0 + hh / 2}", 1.6)
        inner += flicks((x0 + 70, y0 + 8, x1 - 70, y1 - 10), 10, seed, (3, 6), (10, 40), 1.1)
        o.append(S(front, cover, 5.2, inner))
    else:  # fore-edge with the page block between two boards
        front = f"M{x0} {y0}L{x1} {y0}L{x1} {y1}L{x0} {y1}Z"
        lines = "".join(L(f"M{x0 + 8} {y}Q{(x0 + x1) / 2} {y - 4} {x1 - 8} {y}", 1.1) for y in range(y0 + bd + 6, y1 - bd - 2, 5))
        inner = (P(f"M{x0 + 7} {y0 + bd}Q{(x0 + x1) / 2} {y0 + bd + 6} {x1 - 7} {y0 + bd}L{x1 - 7} {y1 - bd}"
                   f"Q{(x0 + x1) / 2} {y1 - bd - 6} {x0 + 7} {y1 - bd}Z", W, 2.2)
                 + lines
                 + F(f"M{x0} {y1 - bd - 18}Q{(x0 + x1) / 2} {y1 - bd - 22} {x1} {y1 - bd - 18}L{x1} {y1}L{x0} {y1}Z", DL)
                 + P(f"M{x0 - 4} {y0 - 4}L{x1 + 4} {y0 - 4}L{x1 + 4} {y0 + bd}L{x0 - 4} {y0 + bd}Z", cover, 0)
                 + P(f"M{x0 - 4} {y1 - bd}L{x1 + 4} {y1 - bd}L{x1 + 4} {y1 + 4}L{x0 - 4} {y1 + 4}Z", cover, 0)
                 + L(f"M{x0} {y0 + bd}L{x1} {y0 + bd}M{x0} {y1 - bd}L{x1} {y1 - bd}", 2.6))
        for cx in (x0, x1):
            s = 1 if cx == x0 else -1
            inner += P(f"M{cx} {y0 - 2}L{cx + 22 * s} {y0 - 2}L{cx} {y0 + bd + 1}Z", DD, 2)
            inner += P(f"M{cx} {y1 + 2}L{cx + 22 * s} {y1 + 2}L{cx} {y1 - bd - 1}Z", DD, 2)
        o.append(S(front, W, 5.2, inner))
    if ribbon:
        o.append(P(f"M{x1 + 4} {y1 - 30}L{x1 + 14} {y1 - 34}L{x1 + 18} {y1 + 26}L{x1 + 12} {y1 + 20}L{x1 + 8} {y1 + 30}Z", DD, 2.6))
    return "".join(o)


def stack():
    o = []
    o.append("<!-- bottom book -->" + book(165, 618, 676, 770, "spine", DM, "star", 3))
    o.append("<!-- middle book -->" + g(book(190, 602, 586, 678, "pages", CH, "", 5, ribbon=True), "rotate(-2 396 632)"))
    o.append("<!-- top book -->" + g(book(178, 590, 494, 586, "spine", HA, "moon", 7), "rotate(1.5 384 540)"))
    return "".join(o)


# ---------------------------------------------------------------------------
# MUG of cocoa on the top book, with steam
# ---------------------------------------------------------------------------
def mug():
    o = []
    o.append(E(566, 492, 30, 6, DD))
    for d, w in (("M556 418C546 404 564 394 556 380C550 370 556 360 564 354", 9),
                 ("M574 416C584 400 568 390 578 374C584 364 580 352 572 344", 8),
                 ("M540 424C534 414 544 408 540 398", 6)):
        o.append(L(d, w + 4.6) + L(d, w, W))
    handle = "M590 438C612 434 618 470 592 474L592 464C604 462 604 446 590 448Z"
    o.append(S(handle, W, 4, F("M596 430L620 430L620 478L596 478Z", DM)))
    body = "M538 428L594 428L592 484C592 494 540 494 540 484Z"
    o.append(S(body, W, 4.8, F("M574 420L600 420L600 500L572 500C578 476 578 446 574 420Z", DM)
               + F("M534 450L600 450L600 466L534 466Z", DL) + L("M538 450L594 450M538 466L594 466", 2)
               + P("M558 460C552 452 560 446 566 452C572 446 580 452 574 460L566 468Z", W, 2)
               + T(546, 436, 548, 456, 546, 478, 1.6, W)))
    o.append(E(566, 428, 28, 7.5, W, 4.4))
    o.append(E(566, 430, 23, 5, DD))
    o.append(P("M560 424L572 423L573 431L561 432Z", W, 2) + P("M550 428L558 426L559 432L551 433Z", W, 1.8))
    return "".join(o)


# ---------------------------------------------------------------------------
# PAPER BOAT and CANDLE at the base of the stack
# ---------------------------------------------------------------------------
def boat():
    o = []
    o.append(E(160, 774, 70, 7, DD))
    hull = "M88 708L234 708L210 770L114 770Z"
    o.append(S(hull, W, 4.8, F("M161 700L240 700L216 776L161 776Z", HA) + L("M100 724L222 724", 1.6)
               + L("M161 708L161 770", 2)))
    sail = "M118 708L161 630L206 708Z"
    o.append(S(sail, W, 4.6, F("M161 624L214 712L161 712Z", DM) + L("M161 634L161 708", 2.4)))
    o.append(L("M128 708L161 690L196 708", 1.6))
    o.append(T(86, 766, 74, 760, 62, 764, 1.8) + T(240, 766, 252, 760, 264, 764, 1.8))
    return "".join(o)


def candle():
    o = []
    for a in range(-160, 30, 28):
        o.append(ray(652, 652, a, 28, 44 if a % 56 else 38, 2.6))
    o.append(E(654, 770, 48, 6, DD))
    dish = "M606 760C606 748 702 748 702 760C702 772 606 772 606 760Z"
    o.append(S(dish, W, 4.4, F("M654 740L710 740L710 776L654 776Z", DM)))
    o.append(S("M698 752C716 746 722 762 704 766L702 760C710 758 710 752 700 756Z", W, 3.2))
    body = "M636 688L670 688L670 756C662 762 644 762 636 756Z"
    o.append(S(body, W, 4.6, F("M656 682L676 682L676 764L656 764Z", DM)
               + T(642, 700, 643, 726, 642, 748, 1.6, INK)))
    o.append(P("M634 690C634 684 672 684 672 690C672 698 668 702 666 712C664 718 660 718 660 710"
               "C658 700 650 700 648 706C646 714 642 716 640 708C638 700 634 698 634 690Z", W, 3.6))
    o.append(L("M653 686L652 672", 2.6))
    o.append(P("M652 626C662 640 666 652 660 664C656 670 648 670 644 664C638 652 642 640 652 626Z", W, 3.2))
    o.append(P("M652 646C656 652 657 657 655 661C654 663 650 663 649 661C647 657 648 652 652 646Z", INK, 0))
    return "".join(o)


# ---------------------------------------------------------------------------
# NIB — peeking out of the open book's gutter (local frame of Wren's lap)
# ---------------------------------------------------------------------------
def nib(cx, cy, s):
    o = []
    body = "M0 -58C8 -42 36 -22 36 4C36 26 20 40 0 40C-20 40 -36 26 -36 4C-36 -22 -8 -42 0 -58Z"
    o.append(P(body, INK, 4.5))
    o.append(T(-27, -2, -29, -24, -12, -38, 5.5, W) + C(-28, 7, 2.6, W))
    nibd = "M0 -88C5 -78 13 -68 13 -58C13 -51 8 -48 0 -47C-8 -48 -13 -51 -13 -58C-13 -68 -5 -78 0 -88Z"
    o.append(S(nibd, W, 3.6, F("M0 -90L16 -90L16 -45L0 -45Z", DM) + L("M0 -84L0 -63", 2.2) + C(0, -61, 2.8, INK)
               + L("M-12 -54Q0 -49 12 -54", 2.2)))
    o.append(C(-14, -4, 13, W) + C(14, -4, 13, W))
    o.append(C(-12.5, -8.5, 6.6, INK) + C(15.5, -8.5, 6.6, INK))
    o.append(C(-14.8, -11.2, 2.5, W) + C(13.2, -11.2, 2.5, W) + C(-10.5, -6, 1, W) + C(17.5, -6, 1, W))
    o.append(T(-23, -22, -15, -27, -7, -23, 2.6, W) + T(7, -23, 15, -27, 23, -22, 2.6, W))
    o.append(P("M-7 12Q0 23 7 12Q0 15 -7 12Z", W, 0))
    o.append(E(-25, 9, 5.5, 3.2, DL) + E(25, 9, 5.5, 3.2, DL))
    return g("".join(o), f"translate({n(cx)} {n(cy)}) scale({s})")


# ---------------------------------------------------------------------------
# WREN — cross-legged on the top book, reading (local frame: origin = seat)
# ---------------------------------------------------------------------------
def cable(cx, y0, y1, w=8, sw=1.7):
    """rope cable: two rails with twisted strands between them"""
    out = L(f"M{cx - w - 3} {y0}L{cx - w - 3} {y1}M{cx + w + 3} {y0}L{cx + w + 3} {y1}", 1.3)
    for y in range(y0, y1 - 8, 11):
        out += L(f"M{cx - w} {y + 11}Q{cx - 2} {y + 9} {cx + w} {y}", sw)
        out += L(f"M{cx - w} {y + 1}Q{cx - w + 3} {y + 4} {cx - 3} {y + 5}", 1.2)
    return out


def wren():
    o = []
    # --- big cloud of curly hair (behind everything)
    rnd = random.Random(12)
    pts = []
    k = 26
    for i in range(k):
        a = 2 * math.pi * i / k + rnd.uniform(-0.04, 0.04)
        rr = 1 + rnd.uniform(-0.05, 0.05)
        pts.append((math.cos(a) * 136 * rr, -250 + math.sin(a) * 124 * rr))
    hair = scallop(pts, 0.36)
    curls = ""
    # a white curl highlight tucked inside every bump of the silhouette
    for i in range(k):
        p, q = pts[i], pts[(i + 1) % k]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        ang = math.atan2(my + 250, mx)
        ix, iy = mx - math.cos(ang) * 2, my - math.sin(ang) * 2
        a0 = math.degrees(ang)
        curls += g(T(-10, 4, 0, -9, 10, 2, 2.2, W), f"translate({n(ix)} {n(iy)}) rotate({n(a0 + 90)})")
    rc = random.Random(5)
    for ring, cnt, size in ((0.74, 19, 0.85), (0.5, 13, 0.75), (0.26, 6, 0.7)):
        for i in range(cnt):
            a = 2 * math.pi * (i + rc.uniform(-0.25, 0.25) + ring) / cnt
            x, y = math.cos(a) * 128 * ring, -250 + math.sin(a) * 116 * ring
            if y > -205 and abs(x) < 80:
                continue  # under the face
            sc = size * rc.uniform(0.85, 1.15)
            curls += g(T(-10, 4, 0, -9, 10, 2, 2, W), f"translate({n(x)} {n(y)}) rotate({n(math.degrees(a) + 90)}) scale({n(sc)})")
    o.append(S(hair, INK, 5, curls))

    # --- quill tucked behind her ear, sticking up out of the curls (local quill frame: base at 0,0)
    vane = ("M0 -26C-10 -50 -18 -88 -17 -118L-10 -116L-16 -128C-15 -150 -9 -170 0 -184"
            "C6 -170 12 -148 12 -122C12 -106 10 -98 9 -92L3 -90L8 -84C7 -60 4 -42 0 -26Z")
    barbs = "".join(L(f"M0 {y}L-14 {y - 13}", 1.1) for y in range(-36, -170, -9))
    barbs += "".join(L(f"M0 {y}L10 {y - 11}", 1.1) for y in range(-34, -170, -9))
    q = S(vane, W, 3.6, F("M0 -190L16 -190L16 -20L0 -20Z", DL) + barbs)
    q += L("M0 6L0 -184", 2.8)
    q += P("M-4 4L4 4L2 20L0 24L-2 20Z", DD, 2.2) + L("M0 12L0 22", 1.2, W)
    o.append(g(q, "translate(-72 -214) rotate(-24)"))
    # --- knees and thighs in striped tights
    lthigh = "M-40 -40C-80 -46 -132 -44 -152 -20C-162 -4 -150 14 -126 14C-96 14 -60 6 -36 -2Z"
    for d, shade in ((lthigh, "M-170 4L-20 4L-20 20L-170 20Z"), (mir(lthigh, 0), "M20 -54L170 -54L170 20L20 20Z")):
        stripes = "".join(F(f"M{x} -60L{x + 9} -60L{x + 12} 24L{x + 3} 24Z", DD) for x in range(-164, 160, 21))
        o.append(S(d, W, 4.8, F(shade, DL) + stripes + L("M-150 -14Q-140 -26 -126 -30", 1.4) + L("M150 -14Q140 -26 126 -30", 1.4)))

    # --- oversized cable-knit sweater
    sw = ("M-62 -158C-88 -150 -100 -120 -102 -82C-104 -52 -106 -28 -100 -10C-60 0 60 0 100 -10"
          "C106 -28 104 -52 102 -82C100 -120 88 -150 62 -158C40 -166 -40 -166 -62 -158Z")
    knit = "".join(L(f"M{x - 2.5} {y - 2}L{x} {y + 1}L{x + 2.5} {y - 2}", 1.1)
                   for x in range(-90, 92, 9) for y in range(-140, -20, 14) if abs(x) not in range(10, 32) and abs(x) < 86 and not (40 < abs(x) < 64))
    o.append(S(sw, W, 5.2, F("M60 -170C96 -150 108 -100 106 -40L106 0L76 0C84 -60 82 -120 60 -170Z", DM)
               + knit + cable(-52, -152, -20) + cable(52, -152, -20) + cable(0, -140, -20, 7)
               + F("M-110 -28C-60 -18 60 -18 110 -28L110 4L-110 4Z", W)
               + "".join(L(f"M{x} -26L{x} 2", 1.5) for x in range(-100, 104, 6))
               + L("M-104 -26C-60 -16 60 -16 104 -26", 2.6)))

    # --- shins crossed in front, ink ankle boots tucked under the knees
    bshin = "M128 -16C70 -14 0 -8 -64 -6L-64 16C0 14 70 12 128 10Z"
    fshin = "M-128 -6C-70 -2 0 4 64 6L64 28C0 26 -70 20 -128 18Z"
    for d, sh in ((bshin, "M-70 8L134 8L134 20L-70 20Z"), (fshin, "M-134 18L70 18L70 34L-134 34Z")):
        stripes = "".join(F(f"M{x} -24L{x + 9} -24L{x + 8} 40L{x - 1} 40Z", DD) for x in range(-134, 134, 21))
        o.append(S(d, W, 4.6, F(sh, DL) + stripes))
    boot = ("M-52 -22L-76 -22C-78 -12 -82 -6 -94 -2C-108 2 -122 4 -124 12C-125 18 -120 22 -110 22"
            "L-56 22C-52 10 -51 -6 -52 -22Z")
    bsole = "M-126 12C-128 22 -122 28 -110 28L-54 28C-50 28 -50 20 -54 20L-110 20C-118 20 -122 18 -126 12Z"
    blace = "M-78 -16L-62 -10M-62 -16L-78 -10M-82 -6L-64 0M-64 -6L-82 0"
    bcuff = "M-50 -28L-80 -28L-80 -18L-50 -18Z"
    for side, dy in ((0, 0), (1, 12)):
        f = (lambda d: d) if side == 0 else (lambda d: mir(d, 0))
        q = S(f(boot), W, 4.6, F(f("M-70 -30L-48 -30L-48 30L-70 30Z") if side == 0 else "M96 -30L130 -30L130 30L96 30Z", DM)
              + F(f("M-130 6C-110 2 -90 4 -76 10L-76 30L-130 30Z"), DL) + L(f(blace), 1.6)
              + L(f("M-120 10C-112 6 -100 6 -92 10"), 1.8))
        q += P(f(bsole), INK, 2.4) + "".join(L(f(f"M{x} 22L{x - 2} 27"), 1.4, W) for x in (-112, -100, -88, -76, -64))
        q += P(f(bcuff), W, 3.4) + L(f("M-78 -23L-52 -23"), 1.3, extra='stroke-dasharray="2 3"')
        o.append(g(q, f"translate(0 {dy})"))

    # --- oversized sleeves running down to the book
    lsl = "M-60 -156C-90 -152 -110 -128 -116 -98C-120 -80 -124 -66 -124 -58L-90 -50C-88 -66 -84 -86 -76 -104Z"
    for d, sh, sx in ((lsl, "M-80 -110L-60 -110L-84 -40L-100 -40Z", -1), (mir(lsl, 0), "M88 -160L140 -120L130 -40L96 -40Z", 1)):
        o.append(S(d, W, 5, F(sh, DM if sx > 0 else DL)
                   + g(cable(0, -40, 40, 6, 1.5), f"translate({sx * 101} -104) rotate({-sx * 16})")))
    lcuff = "M-126 -64L-88 -56L-90 -36L-128 -44Z"
    for d in (lcuff, mir(lcuff, 0)):
        o.append(S(d, W, 4, "".join(L(f"M{x} -70L{x - 2} -30", 1.5) for x in range(-130, 132, 6))))

    # --- neck, rolled collar
    o.append(S("M-24 -176L24 -176L26 -150L-26 -150Z", W, 4.2, F("M-30 -180L30 -180L30 -164L-30 -164Z", DL)))
    col = "M-40 -170C-22 -178 22 -178 40 -170L42 -146C22 -138 -22 -138 -42 -146Z"
    o.append(S(col, W, 4.6, "".join(L(f"M{x} -180Q{x + 1} -160 {x} -136", 1.5) for x in range(-40, 44, 6))
               + F("M22 -180L46 -180L46 -136L22 -136Z", DM)))

    # --- ears, face, curly fringe, glasses, features
    o.append(S(circ(-68, -212, 12), W, 4, F(circ(-68, -212, 12), DL) + P(circ(-70, -215, 10), W, 0)) + L("M-64 -218Q-71 -212 -64 -206", 1.6))
    o.append(S(circ(68, -212, 12), W, 4, F(circ(68, -212, 12), DM)) + L("M64 -218Q71 -212 64 -206", 1.6))
    o.append(S(circ(0, -222, 66), W, 5.2, F(circ(0, -222, 66), DL) + P(circ(-9, -231, 67), W, 0)))
    fr = []
    for i in range(9):
        x = -64 + i * 16
        fr.append((x, -262 + (6 if i % 2 else 0) - abs(x) * 0.06))
    fringe = "M-72 -250C-74 -300 -40 -318 0 -318C40 -318 74 -300 72 -250"
    for x, y in fr[::-1]:
        fringe += f"Q{n(x + 8)} {n(y + 16)} {n(x)} {n(y)}"
    fringe += "Z"
    o.append(P(fringe, INK, 4.4))
    o.append("".join(g(T(-7, 3, 0, -6, 7, 2, 1.8, W), f"translate({n(x + 2)} {n(y - 6)})") for x, y in fr[1::2]))
    # eyes looking down at Nib (down and to the right)
    o.append(E(-24, -205, 7.5, 9.5, INK) + E(30, -205, 7.5, 9.5, INK))
    o.append(C(-26.5, -208.5, 2.8) + C(27.5, -208.5, 2.8) + C(-21.5, -201, 1.1) + C(32.5, -201, 1.1))
    o.append(T(-40, -238, -28, -246, -16, -240, 2.6) + T(16, -240, 28, -246, 40, -238, 2.6))
    for gx in (-29, 29):
        o.append(C(gx, -212, 23, "none", 4.2))
        o.append(T(gx - 14, -220, gx - 12, -228, gx - 4, -231, 1.8, INK))
        o.append(L(f"M{gx + 8} -226L{gx + 15} -219", 1.6))
    o.append(L("M-6 -214Q0 -220 6 -214", 3.6))
    o.append(L("M-52 -214L-62 -210M52 -214L62 -210", 3.4))
    o.append(L("M-2 -186Q2 -183 6 -186", 2.2))
    o.append(P("M-12 -176Q2 -157 15 -177Q2 -172 -12 -176Z", INK, 0))
    o.append(P("M-4 -167Q2 -172 8 -167Q2 -163 -4 -167Z", DL, 0))
    o.append(E(-44, -184, 11, 6.5, DL) + E(46, -184, 11, 6.5, DL))

    # --- open book in her lap; Nib peeks over the far edge of the right-hand page
    cover = "M-112 -78Q-56 -94 0 -74Q56 -94 112 -78L116 -22Q58 -34 0 -14Q-58 -34 -116 -22Z"
    o.append(P(cover, DD, 4.6))
    o.append(L("M-110 -70Q-56 -84 0 -66M110 -70Q56 -84 0 -66", 1.4))
    lpage = "M0 -70Q-52 -88 -104 -78L-106 -30Q-54 -40 0 -20Z"
    rpage = mir(lpage, 0)

    def page(d, sgn):
        txt = "".join(L(f"M{n(sgn * 14)} {n(-62 + i * 8 + 4)}Q{n(sgn * 50)} {n(-72 + i * 8)} {n(sgn * 90)} {n(-66 + i * 8 - 2)}",
                        1.3, extra='stroke-dasharray="7 3 12 3"') for i in range(5))
        return (S(d, W, 3.6, txt + F(f"M0 -80L{sgn * 26} -80L{sgn * 26} -14L0 -14Z", DL))
                + L(f"M{sgn * 104} -74Q{sgn * 52} -86 0 -68", 1.2) + L(f"M{sgn * 106} -36Q{sgn * 54} -44 0 -24", 1.2))
    o.append(page(lpage, -1))
    o.append(nib(64, -100, 0.9))
    o.append(page(rpage, 1))
    o.append(L("M0 -70L0 -20", 2.6))
    o.append(P("M-3 -22L7 -20L12 26L7 20L2 30Z", DD, 2.6))
    # Nib's tiny ink hands on the page edge, and a few splashes
    o.append(L("M36 -96Q26 -94 22 -82", 5.2) + C(22, -79, 6, INK) + L("M93 -98Q102 -94 102 -84", 5.2) + C(102, -80, 6, INK))
    for x, y, r, a in ((14, -138, 4, -30), (108, -132, 3.6, 40), (118, -104, 3, 80), (8, -112, 2.8, -60)):
        o.append(f'<path d="M0 {n(-2.3 * r)}C{n(0.45 * r)} {n(-1.5 * r)} {n(r)} {n(-0.8 * r)} {n(r)} 0A{n(r)} {n(r)} 0 1 1 {n(-r)} 0'
                 f'C{n(-r)} {n(-0.8 * r)} {n(-0.45 * r)} {n(-1.5 * r)} 0 {n(-2.3 * r)}Z" fill="{INK}" '
                 f'transform="translate({x} {y}) rotate({a})"/>')
    o.append(C(40, -64, 2.6, INK) + C(52, -58, 1.6, INK) + C(76, -66, 2, INK))
    # sweater-paw hands holding the book
    for sx in (-1, 1):
        hand = (f"M{sx * 114} -46C{sx * 120} -36 {sx * 114} -24 {sx * 104} -24C{sx * 96} -24 {sx * 92} -32 {sx * 96} -42Z")
        o.append(P(hand, W, 3.8) + L(f"M{sx * 102} -42Q{sx * 106} -36 {sx * 102} -29", 1.6))
    return "".join(o)


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
            + "<!-- stack -->" + stack()
            + "<!-- mug -->" + g(mug(), extra='id="mug"')
            + "<!-- wren -->" + g(wren(), "translate(366 490) scale(1.07)", 'id="wren"')
            + "<!-- boat -->" + g(boat(), extra='id="boat"')
            + "<!-- candle -->" + g(candle(), extra='id="candle"'))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="800" height="800" role="img">'
           "<title>Wren sits cross-legged on a tall stack of three hardback books, reading an open book on her lap "
           "while Nib the ink sprite peeks out of its pages; a mug of cocoa steams beside her, with a paper boat "
           "and a little candle at the foot of the stack</title>"
           + DEFS
           + f'<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">{body}</g></svg>')
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
