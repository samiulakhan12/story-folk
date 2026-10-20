#!/usr/bin/env python3
"""Builds ../assets/reader.svg: Wren reading on a tower of three hardback books.

Wren sits cross-legged on the top book with an open book in her lap; Nib the ink sprite
peeks out of its pages, a mug of cocoa steams beside her, and a paper boat and a small
candle sit at the foot of the stack.  Path data is hand-written; Python only assembles
groups, clips, mirrored parts and repeated texture marks.
Standard library only:  python3 tools/generate-reader.py

One run writes three files: reader.svg (the complete still), reader-base.svg (the still
minus every moving part) and reader-motion.svg (only the moving parts, with their idle
animation in an internal <style>; laid over the base it reproduces the still at rest).
"""
import math
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "reader.svg")
OUT_BASE = os.path.join(HERE, "..", "assets", "reader-base.svg")
OUT_MOTION = os.path.join(HERE, "..", "assets", "reader-motion.svg")

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


def mv(name, s):
    """mark a moving part: kept in the still, cut from the base, rebuilt in the motion layer"""
    return f"<!--mv:{name}-->{s}<!--/mv-->"


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
STEAM = (("M556 418C546 404 564 394 556 380C550 370 556 360 564 354", 9),
         ("M574 416C584 400 568 390 578 374C584 364 580 352 572 344", 8),
         ("M540 424C534 414 544 408 540 398", 6))
MUG_HANDLE = "M590 438C612 434 618 470 592 474L592 464C604 462 604 446 590 448Z"
MUG_BODY = "M538 428L594 428L592 484C592 494 540 494 540 484Z"


STEAM_BOX = ((532, 340, 48, 94), (556, 330, 44, 100), (522, 384, 36, 52))  # filter regions round each wisp


def wisp(d, w):
    return L(d, w + 4.6) + L(d, w, W)


def mug():
    o = []
    o.append(E(566, 492, 30, 6, DD))
    for d, w in STEAM:
        o.append(mv("steam", wisp(d, w)))
    handle = MUG_HANDLE
    o.append(S(handle, W, 4, F("M596 430L620 430L620 478L596 478Z", DM)))
    body = MUG_BODY
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


def candle_rays():
    return "".join(ray(652, 652, a, 28, 44 if a % 56 else 38, 2.6) for a in range(-160, 30, 28))


def candle_flame():
    return (P("M652 626C662 640 666 652 660 664C656 670 648 670 644 664C638 652 642 640 652 626Z", W, 3.2)
            + P("M652 646C656 652 657 657 655 661C654 663 650 663 649 661C647 657 648 652 652 646Z", INK, 0))


def candle():
    o = []
    o.append(mv("candle-glow", candle_rays()))
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
    o.append(mv("candle-flame", candle_flame()))
    return "".join(o)


# ---------------------------------------------------------------------------
# NIB — peeking out of the open book's gutter (local frame of Wren's lap)
# ---------------------------------------------------------------------------
def nib_parts():
    """Nib in its own frame, in paint order: body, eye whites, pupils, catch-lights, face"""
    body = "M0 -58C8 -42 36 -22 36 4C36 26 20 40 0 40C-20 40 -36 26 -36 4C-36 -22 -8 -42 0 -58Z"
    nibd = "M0 -88C5 -78 13 -68 13 -58C13 -51 8 -48 0 -47C-8 -48 -13 -51 -13 -58C-13 -68 -5 -78 0 -88Z"
    return {
        "body": (P(body, INK, 4.5) + T(-27, -2, -29, -24, -12, -38, 5.5, W) + C(-28, 7, 2.6, W)
                 + S(nibd, W, 3.6, F("M0 -90L16 -90L16 -45L0 -45Z", DM) + L("M0 -84L0 -63", 2.2) + C(0, -61, 2.8, INK)
                     + L("M-12 -54Q0 -49 12 -54", 2.2))),
        "whites": C(-14, -4, 13, W) + C(14, -4, 13, W),
        "pupils": C(-12.5, -8.5, 6.6, INK) + C(15.5, -8.5, 6.6, INK),
        "shines": C(-14.8, -11.2, 2.5, W) + C(13.2, -11.2, 2.5, W) + C(-10.5, -6, 1, W) + C(17.5, -6, 1, W),
        "face": (T(-23, -22, -15, -27, -7, -23, 2.6, W) + T(7, -23, 15, -27, 23, -22, 2.6, W)
                 + P("M-7 12Q0 23 7 12Q0 15 -7 12Z", W, 0) + E(-25, 9, 5.5, 3.2, DL) + E(25, 9, 5.5, 3.2, DL)),
    }


NIB_AT = "translate(64 -100) scale(0.9)"


def nib():
    q = nib_parts()
    return g(q["body"] + q["whites"] + q["pupils"] + q["shines"] + q["face"], NIB_AT)


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


# Wren's moving bits (shared by the still and the motion layer) and the shapes that cover them
WREN_AT = "translate(366 490) scale(1.07)"
EAR_L = circ(-68, -212, 12)
FACE = circ(0, -222, 66)
LPAGE = "M0 -70Q-52 -88 -104 -78L-106 -30Q-54 -40 0 -20Z"
RPAGE = mir(LPAGE, 0)
GUTTER = "M0 -70L0 -20"
BOOKMARK = "M-3 -22L7 -20L12 26L7 20L2 30Z"


def paw(sx):
    return f"M{sx * 114} -46C{sx * 120} -36 {sx * 114} -24 {sx * 104} -24C{sx * 96} -24 {sx * 92} -32 {sx * 96} -42Z"


def quill():
    """quill tucked behind her ear (local quill frame: base at 0,0)"""
    vane = ("M0 -26C-10 -50 -18 -88 -17 -118L-10 -116L-16 -128C-15 -150 -9 -170 0 -184"
            "C6 -170 12 -148 12 -122C12 -106 10 -98 9 -92L3 -90L8 -84C7 -60 4 -42 0 -26Z")
    barbs = "".join(L(f"M0 {y}L-14 {y - 13}", 1.1) for y in range(-36, -170, -9))
    barbs += "".join(L(f"M0 {y}L10 {y - 11}", 1.1) for y in range(-34, -170, -9))
    q = S(vane, W, 3.6, F("M0 -190L16 -190L16 -20L0 -20Z", DL) + barbs)
    q += L("M0 6L0 -184", 2.8)
    q += P("M-4 4L4 4L2 20L0 24L-2 20Z", DD, 2.2) + L("M0 12L0 22", 1.2, W)
    return g(q, "translate(-72 -214) rotate(-24)")


def wren_eyes():
    return E(-24, -205, 7.5, 9.5, INK) + E(30, -205, 7.5, 9.5, INK)


def wren_shines():
    return C(-26.5, -208.5, 2.8) + C(27.5, -208.5, 2.8) + C(-21.5, -201, 1.1) + C(32.5, -201, 1.1)


def book_page(d, sgn):
    txt = "".join(L(f"M{n(sgn * 14)} {n(-62 + i * 8 + 4)}Q{n(sgn * 50)} {n(-72 + i * 8)} {n(sgn * 90)} {n(-66 + i * 8 - 2)}",
                    1.3, extra='stroke-dasharray="7 3 12 3"') for i in range(5))
    return (S(d, W, 3.6, txt + F(f"M0 -80L{sgn * 26} -80L{sgn * 26} -14L0 -14Z", DL))
            + L(f"M{sgn * 104} -74Q{sgn * 52} -86 0 -68", 1.2) + L(f"M{sgn * 106} -36Q{sgn * 54} -44 0 -24", 1.2))


NIB_ARMS = ("M36 -96Q26 -94 22 -82", "M93 -98Q102 -94 102 -84")


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

    # --- quill tucked behind her ear, sticking up out of the curls
    o.append(mv("quill", quill()))
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
    o.append(S(EAR_L, W, 4, F(circ(-68, -212, 12), DL) + P(circ(-70, -215, 10), W, 0)) + L("M-64 -218Q-71 -212 -64 -206", 1.6))
    o.append(S(circ(68, -212, 12), W, 4, F(circ(68, -212, 12), DM)) + L("M64 -218Q71 -212 64 -206", 1.6))
    o.append(S(FACE, W, 5.2, F(circ(0, -222, 66), DL) + P(circ(-9, -231, 67), W, 0)))
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
    o.append(mv("wren-eyes", wren_eyes() + wren_shines()))
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
    o.append(mv("left-page", book_page(LPAGE, -1)))
    o.append(mv("nib", nib()))
    o.append(book_page(RPAGE, 1))
    o.append(L(GUTTER, 2.6))
    o.append(P(BOOKMARK, DD, 2.6))
    # Nib's tiny ink hands on the page edge, and a few splashes
    o.append(mv("nib-arm", L(NIB_ARMS[0], 5.2)) + C(22, -79, 6, INK) + mv("nib-arm", L(NIB_ARMS[1], 5.2)) + C(102, -80, 6, INK))
    for x, y, r, a in ((14, -138, 4, -30), (108, -132, 3.6, 40), (118, -104, 3, 80), (8, -112, 2.8, -60)):
        o.append(f'<path d="M0 {n(-2.3 * r)}C{n(0.45 * r)} {n(-1.5 * r)} {n(r)} {n(-0.8 * r)} {n(r)} 0A{n(r)} {n(r)} 0 1 1 {n(-r)} 0'
                 f'C{n(-r)} {n(-0.8 * r)} {n(-0.45 * r)} {n(-1.5 * r)} 0 {n(-2.3 * r)}Z" fill="{INK}" '
                 f'transform="translate({x} {y}) rotate({a})"/>')
    o.append(C(40, -64, 2.6, INK) + C(52, -58, 1.6, INK) + C(76, -66, 2, INK))
    # sweater-paw hands holding the book
    for sx in (-1, 1):
        hand = paw(sx)
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




# ---------------------------------------------------------------------------
# MOTION LAYER — only the moving parts, each with its own small ink filter and its
# animation in an internal <style>.  Every class and keyframe name starts with "rd-".
# ---------------------------------------------------------------------------
# the ink kit with a roomier filter region for the moving parts; thin stroked parts, whose strokes
# reach well past their geometric bounding box, get their own filter with an explicit region instead
_INK = DEFS[DEFS.index("<filter"):DEFS.index("</filter>") + len("</filter>")]
INK_PRIMS = _INK[_INK.index(">") + 1:-len("</filter>")]
MOTION_DEFS = DEFS.replace(_INK, _INK.replace('x="-3%" y="-3%" width="106%" height="106%"',
                                              'x="-20%" y="-20%" width="140%" height="140%"'))
_thin = []
EASE = "cubic-bezier(.45,0,.55,1)"


def n2(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def ink(inner, box=None):
    """ink filter on a group inside a moving part; box (x, y, w, h) gives a thin part its own filter region"""
    if box is None:
        return f'<g filter="url(#ink)">{inner}</g>'
    fid = f"ink-t{len(_thin)}"
    x, y, w, h = box
    _thin.append(f'<filter id="{fid}" filterUnits="userSpaceOnUse" x="{n2(x)}" y="{n2(y)}" '
                 f'width="{n2(w)}" height="{n2(h)}">{INK_PRIMS}</filter>')
    return f'<g filter="url(#{fid})">{inner}</g>'


def piv(cls, inner, x, y):
    """animated wrapper turning about (x, y) of the root frame"""
    return (f'<g transform="translate({n2(x)} {n2(y)})"><g class="{cls}">'
            f'<g transform="translate({n2(-x)} {n2(-y)})">{inner}</g></g></g>')


def look(r, cls, inner):
    """pupils: the page moves .sf-look to follow the cursor; idle glances go on the inner group"""
    return f'<g class="sf-look" data-look="{r}"><g class="{cls}">{inner}</g></g>'


def wpt(x, y):
    """Wren-frame point -> root frame"""
    return 366 + 1.07 * x, 490 + 1.07 * y


def npt(x, y):
    """Nib-frame point -> root frame"""
    return wpt(64 + 0.9 * x, -100 + 0.9 * y)


def wr(s):
    return g(s, WREN_AT)


def cover_mask(mid, box, inner):
    """luminance mask: everything visible except the inked silhouettes of the shapes that cover a part"""
    x, y, w, h = box
    return (f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="{x}" y="{y}" width="{w}" height="{h}">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff"/>'
            f'<g filter="url(#ink)" fill="#000" stroke="#000" stroke-linejoin="round" stroke-linecap="round">{inner}</g></mask>')


def sil(d, sw):
    return f'<path d="{d}" stroke-width="{sw}"/>'


# --- keyframes --------------------------------------------------------------
def kf(name, frames):
    """frames: [(percent, declarations)] -> one-line @keyframes"""
    return f"@keyframes {name} {{ " + " ".join(f"{n2(p)}% {{ {d} }}" for p, d in frames) + " }"


def rot_kf(name, pts):
    return kf(name, [(p, f"transform: rotate({n2(a)}deg)") for p, a in pts])


def move_kf(name, pts):
    return kf(name, [(p, f"transform: translate({n2(x)}px, {n2(y)}px)") for p, x, y in pts])


BLINK = ((0, 1), (0.07, 0.08), (0.19, 0.08), (0.29, 1))


def blink_kf(name, period, closes):
    """closes: start times (s) of each blink; ~70 ms to close, 120 ms shut, ~100 ms to open"""
    fr = [(0, "transform: scaleY(1)")]
    for t in closes:
        fr += [(100 * (t + dt) / period, f"transform: scaleY({v})") for dt, v in BLINK]
    return kf(name, fr + [(100, "transform: scaleY(1)")])


def shine_kf(name, period, closes):
    """catch-lights go out while the eye is shut, so the closed eye reads as one clean line"""
    fr = [(0, "opacity: 1")]
    for t in closes:
        fr += [(100 * (t + dt) / period, f"opacity: {v}") for dt, v in ((0, 1), (0.04, 0), (0.23, 0), (0.29, 1))]
    return kf(name, fr + [(100, "opacity: 1")])


def eased(points, step=1.0):
    """dense samples of a piecewise sine-eased curve: points [(percent, value)] -> [(percent, value)]"""
    out = [points[0]]
    for (p0, v0), (p1, v1) in zip(points, points[1:]):
        if v0 == v1:
            out.append((p1, v1))
            continue
        k = max(2, int((p1 - p0) / step))
        for j in range(1, k + 1):
            u = j / k
            out.append((p0 + (p1 - p0) * u, v0 + (v1 - v0) * (0.5 - 0.5 * math.cos(math.pi * u))))
    return out


def motion_style():
    kfs, rules = [], []

    def anim(cls, dur, delay, ease=EASE):
        rules.append(f".{cls} {{ animation: {cls} {dur}s {ease} {delay}s infinite; transform-origin: 0 0 }}")

    # cocoa steam: each wisp rises, swells and fades, then grows back up out of the mug into its drawn place
    for i, (dur, delay, rise) in enumerate(((5.2, -0.6, 36), (6.4, -3.9, 42), (5.8, -2.2, 24))):
        # it stays mostly opaque for the first half of the rise and regrows quickly, so the three wisps
        # (on different cycles) are seldom all faint at once; per-segment timing keeps the rise from stalling
        kfs.append(kf(f"rd-steam{i}", [
            (0, "transform: translate(0px, 0px) scale(1); opacity: 1"),
            (10, "transform: translate(0px, 0px) scale(1); opacity: 1; animation-timing-function: cubic-bezier(.5,0,.75,.75)"),
            (28, f"transform: translate(0px, -{n2(0.45 * rise)}px) scale(1.07); opacity: 0.85; animation-timing-function: linear"),
            (44, f"transform: translate(0px, -{rise}px) scale(1.16); opacity: 0"),
            (44.5, "transform: translate(0px, 6px) scale(0.4); opacity: 0; animation-timing-function: linear"),
            (54, "transform: translate(0px, 2px) scale(0.75); opacity: 0.7; animation-timing-function: cubic-bezier(.25,.25,.5,1)"),
            (66, "transform: translate(0px, 0px) scale(1); opacity: 1"),
            (100, "transform: translate(0px, 0px) scale(1); opacity: 1")]))
        anim(f"rd-steam{i}", dur, delay)
    # Wren: quill wiggle, blink, reading glances, the left-hand page lifting now and then
    kfs.append(rot_kf("rd-quill", [(0, 0), (4, -3), (9, 2.4), (14, -1.6), (19, 0.9), (24, -0.4), (29, 0), (100, 0)]))
    anim("rd-quill", 6.9, -4.6)
    kfs.append(blink_kf("rd-wren-blink", 5.6, [3.05]))
    kfs.append(shine_kf("rd-wren-shine", 5.6, [3.05]))
    anim("rd-wren-blink", 5.6, -1.7)
    anim("rd-wren-shine", 5.6, -1.7)
    kfs.append(move_kf("rd-wren-glance", [(0, 0, 0), (5, -2.4, -0.4), (27, 2.4, -0.4), (31, -2.4, 0.4), (53, 2.4, 0.4),
                                          (57, -2.4, 1.1), (79, 2.4, 1.1), (86, 0, 0), (100, 0, 0)]))
    anim("rd-wren-glance", 9, -0.4)
    kfs.append(kf("rd-page", [(p, f"transform: skewY({n2(a)}deg) scale({n2(b)}, 1)") for p, a, b in
                              ((0, 0, 1), (4, 2.6, 0.985), (8, -0.7, 1), (12, 1.3, 0.993), (16, -0.3, 1), (20, 0, 1),
                               (100, 0, 1))]))
    anim("rd-page", 7.7, -5.9)
    # Nib ducks behind the page until only its eyes show, then pops back up; its arms pivot on its fists
    peek = eased([(0, 0), (28, 0), (40, 11), (56, 11), (61, -1), (65, 0), (100, 0)])
    kfs.append(kf("rd-nib", [(p, f"transform: translate(0px, {n2(1.07 * d)}px)") for p, d in peek]))
    for name, (vx, vy) in (("rd-arm-l", (14, -14)), ("rd-arm-r", (-9, -14))):
        a0 = math.atan2(vy, vx)
        kfs.append(rot_kf(name, [(p, math.degrees(math.atan2(vy + d, vx) - a0)) for p, d in peek]))
    for cls in ("rd-nib", "rd-arm-l", "rd-arm-r"):
        anim(cls, 8.8, -1.3, "linear")
    kfs.append(blink_kf("rd-nib-blink", 3.9, [1.5]))
    anim("rd-nib-blink", 3.9, -0.2)
    kfs.append(move_kf("rd-nib-glance", [(0, 0, 0), (8, -3, 0.5), (34, -3, 0.5), (41, 0, 0), (60, 0, 0),
                                         (66, 0.8, 3), (82, 0.8, 3), (88, 0, 0), (100, 0, 0)]))
    anim("rd-nib-glance", 6.7, -2.8)
    # candle
    fl = [(0, 1, 1, 0), (8, 0.92, 1.1, -4), (16, 1.05, 0.93, 3), (25, 0.95, 1.07, -2), (33, 1.02, 0.97, 1.5),
          (46, 0.94, 1.09, 3), (55, 1.03, 0.95, -2.5), (64, 1, 1.04, 0), (77, 0.93, 1.1, -3), (87, 1.04, 0.95, 2),
          (100, 1, 1, 0)]
    kfs.append(kf("rd-flame", [(p, f"transform: scale({n2(a)}, {n2(b)}) skewX({n2(c)}deg)") for p, a, b, c in fl]))
    anim("rd-flame", 3.1, -1.1)
    kfs.append(kf("rd-glow", [(0, "transform: scale(1); opacity: 1"), (20, "transform: scale(1.06); opacity: 0.55"),
                              (38, "transform: scale(1); opacity: 1"), (55, "transform: scale(1.03); opacity: 0.75"),
                              (70, "transform: scale(1); opacity: 1"), (100, "transform: scale(1); opacity: 1")]))
    anim("rd-glow", 4.4, -0.9)
    classes = [r.split(" ", 1)[0] for r in rules]
    return ("<style>\n" + "\n".join(kfs) + "\n" + "\n".join(rules) + "\n"
            + "@media (prefers-reduced-motion: reduce) { " + ", ".join(classes) + " { animation: none !important } }\n"
            + "</style>")


def motion():
    defs = [MOTION_DEFS[:-len("</defs>")]]
    # masks: the still shapes that lie over each moving part, so it slides under them
    defs.append(cover_mask("rd-m-mug", (500, 260, 140, 240),
                           sil(MUG_HANDLE, 4) + sil(MUG_BODY, 4.8) + sil(ell(566, 428, 28, 7.5), 4.4)))
    defs.append(cover_mask("rd-m-quill", (180, 30, 260, 300), wr(sil(EAR_L, 4) + sil(FACE, 5.2))))
    defs.append(cover_mask("rd-m-page", (220, 360, 260, 160),
                           wr(sil(RPAGE, 3.6) + sil(GUTTER, 2.6) + sil(BOOKMARK, 2.6) + sil(paw(-1), 3.8))))
    defs.append(cover_mask("rd-m-nib", (370, 250, 150, 200), wr(sil(RPAGE, 3.6))))
    eyes = "".join(f'<circle cx="{x}" cy="-4" r="13" transform="{WREN_AT} {NIB_AT}"/>' for x in (-14, 14))
    defs.append(f'<clipPath id="rd-c-nib-eyes">{eyes}</clipPath>')
    o = []
    # cocoa steam
    o.append('<g mask="url(#rd-m-mug)">'
             + "".join(piv(f"rd-steam{i}", ink(wisp(d, w), box), *(float(v) for v in re.match(r"M(\S+) (\S+?)C", d).groups()))
                       for i, ((d, w), box) in enumerate(zip(STEAM, STEAM_BOX))) + "</g>")
    # Wren
    o.append('<g mask="url(#rd-m-quill)">' + piv("rd-quill", ink(wr(quill())), *wpt(-72, -214)) + "</g>")
    o.append(piv("rd-wren-blink", look(3, "rd-wren-glance", ink(wr(wren_eyes()))
                                       + '<g class="rd-wren-shine">' + ink(wr(wren_shines())) + "</g>"), *wpt(3, -205)))
    o.append('<g mask="url(#rd-m-page)">' + piv("rd-page", ink(wr(book_page(LPAGE, -1))), *wpt(0, -45)) + "</g>")
    q = nib_parts()

    def nb(s):
        return wr(g(s, NIB_AT))
    # body, then the arms (which pivot on the fists gripping the page), then eyes and face: while Nib ducks,
    # the arms swing across its cheeks and must pass behind them.  At rest the three layers don't overlap.
    o.append('<g mask="url(#rd-m-nib)"><g class="rd-nib">' + ink(nb(q["body"])) + "</g></g>")
    o.append(piv("rd-arm-l", ink(wr(L(NIB_ARMS[0], 5.2)), (380, 378, 34, 34)), *wpt(22, -82)))
    o.append(piv("rd-arm-r", ink(wr(L(NIB_ARMS[1], 5.2)), (456, 376, 30, 34)), *wpt(102, -84)))
    o.append('<g mask="url(#rd-m-nib)"><g class="rd-nib">'
             + piv("rd-nib-blink", ink(nb(q["whites"])) + '<g clip-path="url(#rd-c-nib-eyes)">'
                   + look(3.5, "rd-nib-glance", ink(nb(q["pupils"] + q["shines"]))) + "</g>", *npt(0, -4))
             + ink(nb(q["face"])) + "</g></g>")
    # candle
    o.append(piv("rd-glow", ink(candle_rays()), 652, 652))
    o.append(piv("rd-flame", ink(candle_flame()), 652, 668))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="800" height="800" aria-hidden="true">'
            + motion_style() + "".join(defs) + "".join(_thin) + "</defs>"
            + f'<g stroke-linecap="round" stroke-linejoin="round">{"".join(o)}</g></svg>')


def main():
    body = ("<!-- ground -->" + ground()
            + "<!-- stack -->" + stack()
            + "<!-- mug -->" + g(mug(), extra='id="mug"')
            + "<!-- wren -->" + g(wren(), WREN_AT, 'id="wren"')
            + "<!-- boat -->" + g(boat(), extra='id="boat"')
            + "<!-- candle -->" + g(candle(), extra='id="candle"'))

    def page(content):
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="800" height="800" role="img">'
                "<title>Wren sits cross-legged on a tall stack of three hardback books, reading an open book on her lap "
                "while Nib the ink sprite peeks out of its pages; a mug of cocoa steams beside her, with a paper boat "
                "and a little candle at the foot of the stack</title>"
                + DEFS
                + f'<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">{content}</g></svg>')
    still = page(re.sub(r"<!--/?mv(:[\w-]+)?-->", "", body))
    base = page(re.sub(r"<!--mv:[\w-]+-->.*?<!--/mv-->", "", body, flags=re.S))
    for path, svg in ((OUT, still), (OUT_BASE, base), (OUT_MOTION, motion())):
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {os.path.normpath(path)} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
