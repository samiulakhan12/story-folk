#!/usr/bin/env python3
"""Generator for the Storyfolk hero characters layer, as three stacked files.

Requires only the Python 3 standard library (no pip dependencies).
Run: python3 tools/generate-hero-cast.py [out.svg]
(writes ../assets/hero-cast.svg, hero-cast-base.svg and hero-cast-motion.svg next to this
file; with an argument, the other two are named after it)

  hero-cast.svg         the complete still: motion off, no-JS fallback, and the reference
  hero-cast-base.svg    the still minus every moving part (it never changes)
  hero-cast-motion.svg  only the moving parts, with their CSS animation; at rest
                        base + motion reproduce the still

All three sit exactly on top of assets/hero-letters.svg (viewBox 0 0 1600 900).
Path data is hand-written; Python only assembles groups, clips, smooth outlines through
hand-placed points, and repeated texture marks. The contact points below were measured
from the letter outlines in hero-letters.svg.

Each character function returns a list of items in drawing order. A plain string is a
static part. The item classes further down (Mo, Grp, Clip, Look, Split, Rider, MOnly,
BaseOnly) say what moves, about which joint, and what each of the three files gets, so
the still is the same SVG it always was and the motion layer keeps its stacking order.
"""
import math
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

OUT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "hero-cast.svg")
)
OUT_BASE = re.sub(r"(\.svg)?$", "-base.svg", OUT, count=1)
OUT_MOTION = re.sub(r"(\.svg)?$", "-motion.svg", OUT, count=1)
INK = "#111"
W = "#fff"
DL, DM, DD, HA, CH = ("url(#dots-light)", "url(#dots-mid)", "url(#dots-dark)",
                      "url(#hatch)", "url(#crosshatch)")

# letter-contact parameters, measured from hero-letters.svg
L_FOOT_TOP = 727   # top of the L's foot (Captain Ribbit's seat)
# top edge of the O in STORY, (x, y) every 6px: Bolt's head is clipped to sit behind it
O_TOP = [(690, 196.4), (696, 186.2), (702, 177.2), (708, 170.9), (714, 166.3), (720, 163.1), (726, 161.0),
         (732, 157.4), (738, 154.8), (744, 152.9), (750, 151.3), (756, 150.5), (762, 150.1), (768, 150.7),
         (774, 150.8), (780, 150.7), (786, 150.3), (792, 150.3), (798, 150.3), (804, 150.0), (810, 151.0),
         (816, 152.5), (822, 154.1), (828, 155.1), (834, 156.2), (840, 157.7), (846, 159.5), (852, 162.0),
         (858, 165.8), (864, 171.1), (870, 175.2), (876, 180.7), (882, 186.6), (888, 193.7), (894, 206.7)]

# clip ids: "k" for the still's own clips, "m" for clips only the motion layer has,
# "b" for clips only the base has (each file is separate, so the counters never clash)
_n = {"k": 0, "m": 0, "b": 0}


def nid(p="k"):
    _n[p] += 1
    return f"{p}{_n[p]}"


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def n2(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


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


def rect(x0, y0, x1, y1):
    return f"M{n(x0)} {n(y0)}L{n(x1)} {n(y0)}L{n(x1)} {n(y1)}L{n(x0)} {n(y1)}Z"


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
    """closed path through pts whose edges bulge outward (moss, fluff, pom-poms)"""
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


def fuzz(cx, cy, r, k=11, jitter=0.18, seed=1):
    rnd = random.Random(seed)
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k + rnd.uniform(-0.12, 0.12)
        rr = r * (1 + rnd.uniform(-jitter, jitter) * 0.5)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return scallop(pts, 0.38)


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


def tufts(box, count, seed, size=6, w=1.6):
    """little 'v' moss/grass tufts"""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    out = []
    for _ in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        s = size * rnd.uniform(0.7, 1.2)
        out.append(L(f"M{n(x - s * 0.6)} {n(y - s)}Q{n(x - s * 0.2)} {n(y - s * 0.3)} {n(x)} {n(y)}"
                     f"Q{n(x + s * 0.15)} {n(y - s * 0.5)} {n(x + s * 0.5)} {n(y - s * 1.1)}", w))
    return "".join(out)


def stitches(d, sw=1.3):
    return L(d, sw, extra='stroke-dasharray="2.4 3"')


def rivet(x, y, r=2.4):
    return C(x, y, r, W, 1.8) + C(x - r * 0.3, y - r * 0.3, r * 0.3, INK)


def g(content, tr=None, extra=""):
    t = f' transform="{tr}"' if tr else ""
    return f"<g{t}{' ' + extra if extra else ''}>{content}</g>"


def poly_tube(pts, w0, w1):
    """tapered straight-ish rod as a filled polygon along a polyline"""
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


def _cr_ctrl(pts, closed):
    """Catmull-Rom control points for each segment of a point chain"""
    m = len(pts)
    segs = []
    for i in range(m if closed else m - 1):
        p0 = pts[(i - 1) % m] if closed or i > 0 else pts[i]
        p1, p2 = pts[i], pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if closed or i + 2 < m else pts[(i + 1) % m]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, c1, c2, p2))
    return segs


def cr(pts, closed=True):
    """smooth path through hand-placed points"""
    segs = _cr_ctrl(pts, closed)
    d = f"M{n(pts[0][0])} {n(pts[0][1])}"
    for _, c1, c2, p2 in segs:
        d += f"C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(p2[0])} {n(p2[1])}"
    return d + ("Z" if closed else "")


def cubic_pt(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def cr_samples(pts, closed=True, k=10):
    """dense points along the same smooth curve cr() draws"""
    out = []
    for p1, c1, c2, p2 in _cr_ctrl(pts, closed):
        for j in range(k):
            out.append(cubic_pt(p1, c1, c2, p2, j / k))
    if not closed:
        out.append(pts[-1])
    return out


# ---------------------------------------------------------------------------
# MOTION SPLIT
# A character is a list of items in drawing order. Each item renders three ways: into the
# still (exactly the drawing as it always was), into the base (the still minus moving
# parts) and into the motion layer (moving parts only, each inside its pivot wrappers).
# In the motion layer every run of shapes gets its own small ink filter, placed so that
# at rest its user space is the root's, as it is for the still's one big filter; and a
# part that needs a white halo over the black letters is drawn twice: first as a white
# silhouette in a "back" pass under all of that character's art, then as itself.
# ---------------------------------------------------------------------------
def tmat(s):
    """2x3 affine matrix (a, b, c, d, e, f) of an SVG transform list"""
    m = (1, 0, 0, 1, 0, 0)
    for fn, args in re.findall(r"(\w+)\(([^)]*)\)", s or ""):
        v = [float(t) for t in re.split(r"[\s,]+", args.strip())]
        if fn == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif fn == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif fn == "rotate":
            a = math.radians(v[0])
            ca, sa = math.cos(a), math.sin(a)
            cx, cy = (v[1], v[2]) if len(v) == 3 else (0, 0)
            t = (ca, sa, -sa, ca, cx - ca * cx + sa * cy, cy - sa * cx - ca * cy)
        else:
            raise ValueError(fn)
        m = mmul(m, t)
    return m


def mmul(m, t):
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = t
    return (a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2,
            a * e2 + c * f2 + e, b * e2 + d * f2 + f)


def apply(m, p):
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


class Ctx:
    def __init__(self, frame, m, ink="ink"):
        self.frame, self.m, self.ink = frame, m, ink

    def sub(self, tr):
        return Ctx(self.frame + [tr], mmul(self.m, tmat(tr)), self.ink) if tr else self

    def inked(self, ink):
        return Ctx(self.frame, self.m, ink)


HALO = 11  # white backing: the still's halo is a 4.5 square-kernel dilation, ~5.7 on average
SHAPES = {"path", "circle", "ellipse", "rect", "line", "polyline", "polygon"}


def silhouette(frag):
    """white, fattened copy of a fragment: the backing that stands in for the halo filter"""
    root = ET.fromstring(f"<g>{frag}</g>")

    def walk(el):
        for ch in list(el):
            if ch.tag == "clipPath" or ch.get("clip-path"):
                el.remove(ch)  # clipped detail lies inside its shape; the shape's copy covers it
                continue
            if ch.tag in SHAPES:
                sw = float(ch.get("stroke-width", 0)) if ch.get("stroke") not in (None, "none") else 0
                if ch.get("fill") != "none":
                    ch.set("fill", W)
                ch.set("stroke", W)
                ch.set("stroke-width", n(sw + HALO))
                ch.attrib.pop("stroke-dasharray", None)
            walk(ch)
    walk(root)
    return "".join(ET.tostring(ch, encoding="unicode") for ch in root)


def retag(s, suffix):
    """the same fragment with its clip ids renamed, for a second copy in one file"""
    return re.sub(r'(id="|url\(#)(k\d+)', r"\1\2" + suffix, s)


USED = []  # animated classes, in first-use order


def m_render(items, ctx, mode, moving, back):
    out, run = [], []

    def flush():
        if run:
            body = "".join(run)
            fr = " ".join(ctx.frame)
            if mode == "art":
                out.append(f'<g filter="url(#{ctx.ink})"><g transform="{fr}">{body}</g></g>')
            else:
                out.append(f'<g transform="{fr}">{body}</g>')
            run.clear()
    for it in items:
        if isinstance(it, str):
            if moving and mode == "art":
                run.append(it)
            elif moving and back:
                run.append(silhouette(it))
        else:
            flush()
            out.append(it.motion(ctx, mode, moving, back))
    flush()
    return "".join(out)


def r_still(items):
    return "".join(it if isinstance(it, str) else it.still() for it in items)


def r_base(items):
    return "".join(it if isinstance(it, str) else it.base() for it in items)


class Mo:
    """a moving part: rotates/scales about `pivot` (in the coordinates it is placed in),
    or only translates/fades when pivot is None. back=True gives its shapes a halo backing."""

    def __init__(self, cls, items, pivot=None, back=False, ink="ink"):
        self.cls, self.items, self.pivot, self.back, self.ink = cls, items, pivot, back, ink

    def still(self):
        return r_still(self.items)

    def base(self):
        return ""

    def motion(self, ctx, mode, moving, back):
        inner = m_render(self.items, ctx.inked(self.ink), mode, True, self.back)
        if not inner:
            return ""
        if self.cls not in USED:
            USED.append(self.cls)
        if self.pivot is None:
            return f'<g class="{self.cls}">{inner}</g>'
        px, py = apply(ctx.m, self.pivot)
        return (f'<g transform="translate({n2(px)} {n2(py)})"><g class="{self.cls}">'
                f'<g transform="translate({n2(-px)} {n2(-py)})">{inner}</g></g></g>')


class Grp:
    """a plain group of the still (transform and/or attributes such as a clip or filter);
    in the motion layer only its transform is kept"""

    def __init__(self, items, tr=None, extra=""):
        self.items, self.tr, self.extra = items, tr, extra

    def still(self):
        return g(r_still(self.items), self.tr, self.extra)

    def base(self):
        return g(r_base(self.items), self.tr, self.extra)

    def motion(self, ctx, mode, moving, back):
        return m_render(self.items, ctx.sub(self.tr), mode, moving, back)


class Clip:
    """motion-layer clip (local path d, plus an optional extra transform for the path):
    keeps a moving part out of what is drawn in front of it in the still"""

    def __init__(self, d, items, evenodd=False, tr=""):
        self.d, self.items, self.evenodd, self.tr, self.id = d, items, evenodd, tr, None

    def still(self):
        return r_still(self.items)

    def base(self):
        return r_base(self.items)

    def motion(self, ctx, mode, moving, back):
        inner = m_render(self.items, ctx, mode, moving, back)
        if not inner:
            return ""
        defs = ""
        if self.id is None:
            self.id = nid("m")
            fr = " ".join(ctx.frame + ([self.tr] if self.tr else []))
            rule = ' clip-rule="evenodd"' if self.evenodd else ""
            defs = f'<clipPath id="{self.id}"><path transform="{fr}" d="{self.d}"{rule}/></clipPath>'
        return defs + f'<g clip-path="url(#{self.id})">{inner}</g>'


class Look:
    """a pupil the page can point at the cursor: sf-look (reserved for the page script,
    never animated here) > idle glance > pupil and catch-lights"""

    def __init__(self, r, glance, items):
        self.r, self.glance, self.items = r, glance, items

    def still(self):
        return r_still(self.items)

    def base(self):
        return ""

    def motion(self, ctx, mode, moving, back):
        if mode != "art":
            return ""
        if self.glance not in USED:
            USED.append(self.glance)
        inner = m_render(self.items, ctx, "art", True, False)
        return f'<g class="sf-look" data-look="{self.r}"><g class="{self.glance}">{inner}</g></g>'


class Split:
    """one drawing that is cut up differently per file: `still` as drawn, `base` what stays
    behind, `motion` the items that replace it in the motion layer"""

    def __init__(self, still, base, motion, back=False):
        self.s, self.b, self.m, self.back = still, base, motion, back

    def still(self):
        return self.s

    def base(self):
        return self.b

    def motion(self, ctx, mode, moving, back):
        return m_render(self.m, ctx, mode, True, self.back)


class Rider:
    """a static part drawn in the base AND repeated in the motion layer, because in the
    still it lies on top of something that moves"""

    def __init__(self, items, back=False):
        self.items, self.back = items, back

    def still(self):
        return r_still(self.items)

    def base(self):
        return r_base(self.items)

    def motion(self, ctx, mode, moving, back):
        return m_render(self.items, ctx, mode, True, self.back)


class MOnly(Rider):
    """static ink only the motion layer needs (it restores an outline that a moving part,
    clipped at the outline's centre line, would otherwise cover)"""

    def still(self):
        return ""

    def base(self):
        return ""


class BaseOnly:
    def __init__(self, s):
        self.s = s

    def still(self):
        return ""

    def base(self):
        return self.s

    def motion(self, ctx, mode, moving, back):
        return ""


BIG = "M-400 -500L400 -500L400 400L-400 400Z"  # a local rect, for "everything outside" clips


# ---------------------------------------------------------------------------
# PIP — sits on the T's crossbar (seat point 530,150), holds his lantern out
# ---------------------------------------------------------------------------
PIP_SHORTS = "M-33 -8C-36 4 -32 13 -21 14L-5 14C-3 9 3 9 5 14L21 14C32 13 36 4 33 -8Z"


def pip():
    o = []
    o.append(E(4, 1.5, 50, 4.5, DM))  # contact shadow on the crossbar edge

    # lantern arm (behind torso)
    sleeve = "M-18 -57C-32 -66 -48 -73 -62 -75Q-68 -64 -64 -51C-50 -51 -36 -45 -24 -35Z"
    o.append(S(sleeve, W, 4.5,
               F("M-24 -44C-38 -50 -52 -55 -66 -57L-66 -48C-50 -48 -36 -42 -24 -33Z", DM)
               + L("M-40 -70Q-45 -60 -42 -47", 2.2) + L("M-28 -62Q-32 -54 -30 -42", 1.8)))
    cuff = "M-61 -77Q-69 -64 -63 -50L-72 -49Q-78 -63 -70 -78Z"
    o.append(S(cuff, W, 3.5, "".join(L(f"M{x} -82L{x - 2} -44", 1.4) for x in (-63, -66.5, -70, -73.5))))

    # brass lantern hanging from the fist; it swings from the bail, the flame flickers and
    # the light rays twinkle in two sets
    lx = -82
    # light rays fan out to the side and up, none pointing down into the crossbar
    rays = [ray(lx, -26, a, 21, 29 + (a % 3) * 2, 2.8) for a in (150, 180, 210, 240, 270, 302, 18)]
    lan = [Mo("hc-pip-raya", ["".join(rays[:4])], pivot=(lx, -26)), Mo("hc-pip-rayb", ["".join(rays[4:])], pivot=(lx, -26))]
    lan.append(L(f"M{lx - 8} -45Q{lx - 8} -60 {lx} -61Q{lx + 8} -60 {lx + 8} -45", 2.6))
    lan.append(S(f"M{lx - 11} -37L{lx + 11} -37L{lx + 7} -44Q{lx} -49 {lx - 7} -44Z", W, 3,
                 F(f"M{lx} -50L{lx + 12} -50L{lx + 12} -36L{lx} -36Z", DM)))
    lan.append(C(lx, -48.5, 2.6, W, 2))
    lan.append(P(f"M{lx - 13} -37L{lx + 13} -37L{lx + 13} -33L{lx - 13} -33Z", DD, 2.6))
    lan.append(P(f"M{lx - 10} -33L{lx + 10} -33L{lx + 10} -15L{lx - 10} -15Z", W, 3))
    lan.append(Mo("hc-pip-flame", [
        P(f"M{lx} -31C{lx + 5} -25 {lx + 6} -21 {lx + 3} -18C{lx + 1} -16.5 {lx - 1} -16.5 {lx - 3} -18"
          f"C{lx - 6} -21 {lx - 5} -25 {lx} -31Z", W, 1.8),
        P(f"M{lx} -25C{lx + 2} -22 {lx + 2.4} -20 {lx + 1} -18.5C{lx} -18 {lx - 1} -18 {lx - 1.4} -18.6"
          f"C{lx - 2.4} -20 {lx - 2} -22 {lx} -25Z", INK, 0)], pivot=(lx, -17)))
    lan.append(L(f"M{lx - 6} -33L{lx - 6} -15M{lx + 6} -33L{lx + 6} -15", 1.6))
    lan.append(P(f"M{lx - 13} -15L{lx + 13} -15L{lx + 10} -9L{lx - 10} -9Z", DM, 2.8))
    lan.append(T(lx - 8, -30, lx - 9, -24, lx - 8, -19, 1.6, W))
    o.append(Mo("hc-pip-lantern", lan, pivot=(lx, -63)))
    # fist round the bail (it lies over the bail, so the motion layer repeats it)
    o.append(Rider([
        S("M-73 -73C-80 -78 -90 -75 -91 -66C-92 -57 -84 -53 -76 -55C-71 -59 -70 -67 -73 -73Z", W, 4,
          F("M-82 -60C-86 -54 -78 -52 -74 -56L-72 -64Z", DL)),
        P("M-77 -72C-78 -79 -86 -81 -88 -75C-86 -72 -81 -70 -77 -72Z", W, 3),
        L("M-86 -66Q-82 -64 -78 -66M-87 -61Q-83 -59 -79 -61", 1.6)]))

    # legs and big lace-up boots
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
        out.append(S(boot, W, 4.5,
                     F(f"M{-14 * s} 40L{4 * s} 40L{4 * s} 90L{-14 * s} 90Z" if s > 0 else
                       f"M{-14 * s} 40L{4 * s} 40L{4 * s} 90L{-14 * s} 90Z", DM)
                     + lace + L(f"M{-38 * s} 68Q{-22 * s} 74 {-6 * s} 67", 2.2)))
        out.append(P(f"M{-40 * s} 70C{-41 * s} 81 {-35 * s} 88 {-24 * s} 88C{-13 * s} 88 {-5 * s} 83 {-4 * s} 73"
                     f"C{-9 * s} 79 {-17 * s} 81 {-24 * s} 81C{-31 * s} 81 {-37 * s} 77 {-40 * s} 70Z", INK, 2.5))
        out.append(P(f"M{-33 * s} 42L{-8 * s} 42L{-8 * s} 48L{-33 * s} 48Z", W, 3.2))
        return "".join(out)

    # the lower legs kick from the knees; in the motion layer they are clipped to below the
    # shorts' outer edge (the shorts lie over their tops) and backed in white over the T
    o.append(Clip("M-300 -30L300 -30L300 300L-300 300Z" + PIP_SHORTS, [
        Mo("hc-pip-legl", [leg(1)], pivot=(-20, 11), back=True),
        Mo("hc-pip-legr", [Grp([leg(-1)], "rotate(-14 18 10)")], pivot=(18, 10), back=True)],
        evenodd=True, tr="translate(0 2.25)"))

    # cargo shorts (foreshortened thighs)
    shorts = PIP_SHORTS
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

    # resting arm, hand gripping the crossbar edge
    sl2 = "M23 -57C40 -54 48 -38 49 -18L35 -15C34 -28 31 -38 25 -44Z"
    o.append(S(sl2, W, 4.5, F("M38 -60L56 -60L56 -14L40 -14C42 -30 42 -44 38 -60Z", DM)
               + L("M29 -38Q38 -36 47 -40", 2.2)))
    o.append(S("M34 -20L49 -22L50 -12L35 -10Z", W, 3.4,
               "".join(L(f"M{x} -24L{x + 1} -8", 1.4) for x in (37, 40.5, 44, 47.5))))
    o.append(S("M34 -11C34 -16 50 -17 53 -10C56 -3 55 5 51 7C47 8 43 4 41 1C37 -2 34 -6 34 -11Z", W, 4,
               F("M47 -14L58 -14L58 9L47 9Z", DL)))
    o.append(L("M46 -2Q48 3 47 6M42 -4Q43 1 41 3", 1.8))

    # striped scarf: tail streaming right, front tail, wrap
    tail = ("M17 -62C36 -70 50 -62 64 -70C78 -78 90 -72 104 -82L108 -68C94 -60 82 -64 68 -56"
            "C54 -48 40 -54 24 -47Z")
    bands = "".join(F(f"M{x} -90L{x + 12} -90L{x + 15} -40L{x + 3} -40Z", DD) for x in (34, 60, 86))
    tail_s = S(tail, W, 4, bands + L("M30 -58C46 -62 56 -56 70 -63", 1.6) + L("M78 -68Q90 -70 100 -76", 1.6))
    wind = L("M106 -80L115 -85M107 -75L117 -77M108 -70L116 -69", 2)
    arcs = T(112, -96, 124, -98, 134, -92, 2.2) + T(118, -60, 128, -58, 136, -63, 2)
    # the tail flutters as three hinged segments (a wave running out to the tip); the root
    # stays in the base, under the wrap and face, and each segment overlaps the next by 2
    bk = nid("b")
    root = (f'<clipPath id="{bk}"><path d="{rect(-300, -300, 40, 300)}"/></clipPath>'
            f'<g clip-path="url(#{bk})">{tail_s}</g>')
    seg3 = Mo("hc-pip-scarf3", [Clip(rect(88, -200, 300, 100), [retag(tail_s, "c")]),
                                Mo("hc-pip-wind", [wind, arcs])], pivot=(88, -68.5))
    seg2 = Mo("hc-pip-scarf2", [Clip(rect(64, -200, 90, 100), [retag(tail_s, "b")]), seg3], pivot=(64, -62))
    seg1 = Mo("hc-pip-scarf1", [Clip(rect(38, -200, 66, 100), [tail_s]), seg2], pivot=(38, -58.5))
    o.append(Split(tail_s + wind + arcs, root, [seg1]))
    ftail = "M-25 -52C-27 -40 -25 -28 -23 -15L-8 -17C-10 -29 -10 -41 -10 -52Z"
    o.append(S(ftail, W, 4, F("M-30 -46L-5 -46L-5 -39L-30 -39Z", DD) + F("M-30 -33L-5 -33L-5 -26L-30 -26Z", DD)))
    o.append(L("M-21 -15L-22 -9M-17 -15.5L-17 -9.5M-13 -16L-12 -10", 2))
    wrap = "M-31 -63C-14 -55 14 -55 31 -63L31 -49C14 -41 -14 -41 -31 -49Z"
    o.append(S(wrap, W, 4.5, "".join(F(f"M{x} -66L{x + 9} -66L{x + 8} -40L{x - 1} -40Z", DD) for x in (-24, -5, 14))
               + L("M-30 -55C-14 -48 14 -48 30 -55", 1.6)))

    # ears, face
    o.append(S(circ(-29, -79, 6), W, 3.5, F(circ(-29, -79, 6), DL)) + L("M-30 -82Q-26 -79 -30 -76", 1.6))
    o.append(S(circ(29, -79, 6), W, 3.5, F(circ(29, -79, 6), DM)) + L("M30 -82Q26 -79 30 -76", 1.6))
    o.append(S(circ(0, -82, 29), W, 5,
               F(circ(0, -82, 29), DL) + P(circ(-7, -87, 30), W, 0)
               + F("M-34 -96C-12 -100 12 -100 34 -96L34 -85C12 -89 -12 -89 -34 -85Z", DM)))
    # solid ink eyes: they blink as a pair and look round within the face
    eyes = E(-11, -74, 4.6, 6.2, INK) + E(11, -74, 4.6, 6.2, INK)
    catch = C(-12.6, -76.6, 1.9) + C(9.4, -76.6, 1.9) + C(-9.6, -71.6, 0.8) + C(12.4, -71.6, 0.8)
    o.append(Split(eyes + catch, "", [Mo("hc-pip-blink", [Look(2.2, "hc-pip-glance", [eyes + catch])],
                                         pivot=(0, -74))]))
    o.append(T(-17, -83, -11, -87, -5, -84.5, 2.4) + T(5, -84.5, 11, -87, 17, -83, 2.4))
    o.append(L("M-2.5 -67Q0 -64.5 2.5 -67", 2))
    o.append(P("M-8.5 -61Q0 -49 8.5 -61Q0 -59 -8.5 -61Z", INK, 0))
    o.append(P("M-4 -56.5Q0 -53 4 -56.5Q0 -58.5 -4 -56.5Z", W, 0))
    o.append(E(-19.5, -65.5, 6, 3.8, DL) + E(19.5, -65.5, 6, 3.8, DL))
    o.append("".join(C(x, y, 0.95, INK) for x, y in
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
    for gx in (-12, 12):
        o.append(S(circ(gx, -115, 10.5), W, 4.2, F(circ(gx + 4, -111, 9), DL)))
        o.append(L(f"M{gx - 5} -118Q{gx - 3} -121.5 {gx + 1} -121.5", 2, W))
        o.append(C(gx, -115, 7, "none", 1.6))
    o.append(L("M-1.5 -116Q0 -118 1.5 -116", 3.4))
    cuffb = "M-36 -101C-12 -107 12 -107 36 -101L36 -88C12 -94 -12 -94 -36 -88Z"
    o.append(S(cuffb, W, 4.5,
               "".join(L(f"M{x} -110L{x} -84", 1.5) for x in range(-32, 36, 5))
               + F("M22 -112L40 -112L40 -84L22 -84Z", DM)))
    return o


# ---------------------------------------------------------------------------
# JUNIPER — wide stance across the notch of the Y, spyglass to her eye, looking right
# ---------------------------------------------------------------------------
def _frame(c, k):
    """point, unit tangent and unit normal at sample k of a polyline"""
    a = c[max(k - 1, 0)]
    b = c[min(k + 1, len(c) - 1)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1
    return c[k], (dx / ln, dy / ln), (-dy / ln, dx / ln)


def braid(pts, w0=12.5, w1=8.5, lobe=7.0, tie_rot=0):
    """a thick hanging plait: lobed ink tube along a smooth centre line, white plait
    chevrons, a string tie and a brushy tuft at the end"""
    c = cr_samples(pts, closed=False, k=14)
    acc = [0.0]
    for i in range(1, len(c)):
        acc.append(acc[-1] + math.hypot(c[i][0] - c[i - 1][0], c[i][1] - c[i - 1][1]))
    total = acc[-1]
    left, right = [], []
    for k in range(len(c)):
        p, t, nn = _frame(c, k)
        s = acc[k]
        w = (w0 + (w1 - w0) * s / total) / 2
        w *= 1 + 0.16 * abs(math.sin(math.pi * s / lobe))  # each plait lobe bulges a little
        left.append((p[0] + nn[0] * w, p[1] + nn[1] * w))
        right.append((p[0] - nn[0] * w, p[1] - nn[1] * w))
    tube = "M" + "L".join(f"{n(x)} {n(y)}" for x, y in left + right[::-1]) + "Z"
    out = [P(tube, INK, 3)]
    # plait chevrons (white), alternating a little so it reads as woven
    s = lobe * 0.6
    j = 0
    while s < total - 4:
        k = min(range(len(acc)), key=lambda i: abs(acc[i] - s))
        p, t, nn = _frame(c, k)
        w = (w0 + (w1 - w0) * s / total) / 2 * 0.86
        sh = 0.8 if j % 2 else -0.8
        tipx, tipy = p[0] + t[0] * 2.6 + nn[0] * sh, p[1] + t[1] * 2.6 + nn[1] * sh
        for side in (1, -1):
            ex, ey = p[0] + nn[0] * w * side - t[0] * 3.2, p[1] + nn[1] * w * side - t[1] * 3.2
            out.append(T(ex, ey, (ex + tipx) / 2, (ey + tipy) / 2, tipx, tipy, 1.1, W))
        s += lobe
        j += 1
    # string tie + tuft, in the end frame
    p, t, nn = _frame(c, len(c) - 1)
    ang = math.degrees(math.atan2(t[1], t[0])) - 90 + tie_rot
    hw = w1 / 2 + 1
    tie = (P(f"M{n(-hw)} -3L{n(hw)} -3L{n(hw)} 3L{n(-hw)} 3Z", W, 2.2)
           + L(f"M{n(-hw)} -0.6L{n(hw)} 0.2", 1.2)
           + L(f"M{n(hw)} 0Q{n(hw + 6)} -5 {n(hw + 7)} 1Q{n(hw + 4)} 4 {n(hw)} 1", 1.6)
           + L(f"M{n(hw)} 1Q{n(hw + 4)} 7 {n(hw + 2)} 11", 1.4))
    tw = w1 / 2
    tuft = (f"M{n(-tw)} 2.5C{n(-tw * 1.3)} 7 {n(-tw * 1.7)} 11 {n(-tw * 1.5)} 15L{n(-tw * 0.6)} 11.5"
            f"L0 16.5L{n(tw * 0.6)} 11.5L{n(tw * 1.5)} 15C{n(tw * 1.7)} 11 {n(tw * 1.3)} 7 {n(tw)} 2.5Z")
    tie_g = (P(tuft, INK, 2.4) + L(f"M{n(-tw * 0.6)} 5L{n(-tw * 0.9)} 11M{n(tw * 0.5)} 5L{n(tw * 0.8)} 11", 1.1, W)
             + tie)
    out.append(g(tie_g, f"translate({n(p[0])} {n(p[1])}) rotate({n(ang)})"))
    return "".join(out)


def _quad(c, a, l0, l1, hw):
    """rectangle along unit axis a from l0 to l1, half-width hw, around point c"""
    px, py = -a[1], a[0]
    pts = [(c[0] + a[0] * l0 + px * hw, c[1] + a[1] * l0 + py * hw),
           (c[0] + a[0] * l1 + px * hw, c[1] + a[1] * l1 + py * hw),
           (c[0] + a[0] * l1 - px * hw, c[1] + a[1] * l1 - py * hw),
           (c[0] + a[0] * l0 - px * hw, c[1] + a[1] * l0 - py * hw)]
    return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts) + "Z"


JUN_SHIRT = "M-16 -84C-21 -75 -21 -65 -18 -55L24 -55C27 -65 28 -75 26 -85C18 -88 0 -88 -16 -84Z"
JUN_NECK = (8, -86)  # head, spyglass and hands pan about her neck; each arm about its shoulder


def juniper():
    o = []
    # contact shadows on the two arms of the Y (left arm sits ~2px lower: the letter is tilted)
    o.append(E(-60, 1.2, 25, 3.6, DM) + E(59, -1.4, 25, 3.6, DM))

    # far braid, hanging behind her back (it rides the head and sways from its root)
    o.append(Mo("hc-jun-pan", [Mo("hc-jun-braidf", [
        braid([(-20, -104), (-29, -92), (-35, -78), (-38, -64)], 12, 8.5, tie_rot=6)], pivot=(-20, -102))],
        pivot=JUN_NECK))

    # far arm (behind the body): elbow out front, hand under the spyglass barrel. In the
    # motion layer it is clipped clear of the shirt, which lies over its root.
    o.append(Clip(BIG + JUN_SHIRT, [Mo("hc-jun-pan", [
        S(cr([(22, -89), (42, -91), (60, -93), (68, -87), (62, -78), (42, -76), (22, -75)]), W, 4,
          F("M20 -82L72 -84L72 -70L20 -70Z", DM)),
        S(cr([(63, -90), (78, -101), (94, -111), (102, -106), (96, -96), (80, -84), (69, -80)]), W, 3.6,
          F("M74 -74L106 -104L106 -74Z", DL)),
        E(66, -85, 5.5, 8.6, W, 3, -12) + L("M64 -92Q62 -85 64 -78", 1.3)], pivot=(24, -82))],
        evenodd=True, tr="translate(2.2 -2.2)"))

    # legs: tall striped socks and sneakers, splayed across the notch
    for s, dy in ((-1, 1.8), (1, -0.6)):
        sock_ax = (s * 0.62, 0.785)  # from the trouser cuff down to the ankle
        c0 = (s * 33, -30)
        sock = _quad(c0, sock_ax, 0, 22, 6.2)
        stripes = "".join(P(_quad(c0, sock_ax, l, l + 3.6, 9), DD, 0) for l in (4, 11.5, 19))
        shade = F(_quad((c0[0] + 3.5, c0[1]), sock_ax, -2, 26, 3.2), HA)  # shadow side of the sock
        o.append(g(S(sock, W, 3.6, shade + stripes), f"translate(0 {n(dy * 0.5)})"))
        shoe = (f"M{40 * s} -13C{44 * s} -17.5 {54 * s} -18.5 {60 * s} -14.5C{68 * s} -13.5 {78 * s} -10 {79.5 * s} -3.5"
                f"C{80 * s} 0 {77 * s} 1 {73 * s} 1L{40 * s} 1C{36.5 * s} -1 {36 * s} -9 {40 * s} -13Z")
        inner = (F(f"M{34 * s} -20L{47 * s} -20L{47 * s} 3L{34 * s} 3Z", HA)
                 + L(f"M{37 * s} -3.6L{80 * s} -3.6", 2.6)
                 + L(f"M{63 * s} -14Q{70 * s} -10 {70 * s} -4", 2)
                 + L(f"M{47 * s} -16.5L{51 * s} -12.5M{51 * s} -17.5L{54.5 * s} -13.5M{55 * s} -17L{58 * s} -13", 1.5)
                 + C(72 * s, -9, 1.4, INK))
        o.append(g(S(shoe, W, 4, inner), f"translate(0 {n(dy)})"))

    # patched trousers, rolled at the knee
    trousers = ("M-18 -57L24 -57C28 -49 33 -42 39 -36L28 -25C22 -30 12 -34 3 -38C-6 -34 -16 -30 -24 -25"
                "L-35 -36C-29 -42 -23 -49 -18 -57Z")
    o.append(S(trousers, W, 4.4,
               F("M8 -60C14 -50 22 -38 30 -26L44 -36C36 -44 30 -52 26 -60Z", DM)
               + F("M-3 -46L9 -46L3 -38Z", DD)
               + P("M-24 -46L-13 -43L-16 -33L-27 -36Z", DL, 2) + stitches("M-23 -44.5L-15 -42L-17.5 -34.5")
               + P("M14 -50L23 -51L26 -43L17 -41Z", W, 2) + stitches("M15.5 -48.5L22 -49L24 -44")
               + L("M-10 -52Q-7 -48 -9 -44", 1.6) + L("M13 -54Q16 -50 15 -46", 1.6)))
    for s in (-1, 1):
        cx, cy, ax, ay = s * 33.5, -30.5, s * 0.62, 0.785
        o.append(P(_quad((cx, cy), (ax, ay), -4, 3, 9.2), W, 3.2)
                 + L(f"M{n(cx - ay * 8.4)} {n(cy + ax * 8.4)}L{n(cx + ay * 8.4)} {n(cy - ax * 8.4)}", 1.3))

    # shirt, belt, satchel strap
    shirt = JUN_SHIRT
    o.append(S(shirt, W, 4.4, F("M12 -92C22 -84 25 -68 24 -52L34 -52L34 -92Z", DM)
               + C(6, -71, 1.3, INK) + C(6, -63, 1.3, INK) + L("M-12 -66Q-7 -62 -3 -66", 1.5)))
    o.append(P("M-6 -88L4 -78L6 -87Z", W, 2.4) + P("M17 -89L8 -78L6 -87Z", W, 2.4))
    o.append(P("M-20 -60L26 -60L26 -53L-20 -53Z", INK, 2) + P("M-0.5 -62L8.5 -62L8.5 -51L-0.5 -51Z", W, 2.2)
             + P("M2 -59.5L6 -59.5L6 -53.5L2 -53.5Z", INK, 0))
    o.append(S("M-15 -86L-9 -90L36 -58L31 -53Z", DL, 2.4, stitches("M-11 -87L33 -56")))
    # satchel on her right hip, rolled maps poking out of the back
    for (x0, y0, x1, y1, rr) in ((44, -54, 64, -62, 4.4), (46, -47, 67, -50, 4)):
        o.append(P(poly_tube([(x0, y0), (x1, y1)], rr * 2, rr * 2), W, 2.4))
        a = math.degrees(math.atan2(y1 - y0, x1 - x0))
        o.append(g(E(0, 0, 2.2, rr, W, 2.2) + L("M0 -1.4Q1.3 0 0 1.4", 1.1), f"translate({x1} {y1}) rotate({n(a)})"))
        o.append(L(f"M{n(x0 + (x1 - x0) * 0.35)} {n(y0 + (y1 - y0) * 0.35 - 2.6)}"
                   f"L{n(x0 + (x1 - x0) * 0.8)} {n(y0 + (y1 - y0) * 0.8 - 2.6)}", 1.1))
    bag = "M22 -60C21 -48 23 -40 28 -36L49 -36C53 -42 53 -52 51 -60Z"
    o.append(S(bag, W, 4, F("M20 -47C30 -44 42 -44 55 -47L55 -33L20 -33Z", DM) + stitches("M26 -40L47 -40")))
    flap = "M20 -63L53 -63C54 -55 49 -49 36.5 -48C26 -49 20 -54 20 -63Z"
    o.append(S(flap, DL, 3.4, P(circ(36, -59, 11), W, 0) + stitches("M24 -60Q36.5 -50 49 -60")))
    o.append(P("M33.5 -53L39.5 -53L39.5 -46.5L33.5 -46.5Z", W, 2))

    # near braid, hanging over her shoulder from under the cap
    o.append(Mo("hc-jun-pan", [Mo("hc-jun-braidn", [
        braid([(-10, -96), (-14, -86), (-16, -74), (-15, -62)], 13, 9, tie_rot=-4)], pivot=(-10, -94))],
        pivot=JUN_NECK))

    # head, face, spyglass and the hand on the barrel pan together, slowly sweeping the view
    hd = []
    # head: face, aviator cap, fleece trim, ear flap
    hd.append(S(circ(10, -106, 28), W, 4.6, F(circ(10, -106, 28), DL) + P(circ(4, -110, 29), W, 0)))
    cap = ("M38 -113C39 -131 24 -144.5 6 -144C-12 -143.5 -26 -131 -26 -113C-26 -104 -23 -97 -19 -93"
           "L-6 -100C-5 -108 0 -114 10 -117C20 -120 30 -119 38 -113Z")
    hd.append(S(cap, W, 4.6,
                F("M14 -148C32 -142 42 -130 40 -112L28 -117C30 -128 26 -138 14 -148Z", DM)
                + F("M-30 -118C-24 -108 -20 -100 -14 -94L-30 -90Z", DL)
                + stitches("M5 -143C1 -134 -2 -125 -4 -114") + L("M-19 -128Q-10 -140 4 -143", 1.5)
                + L("M14 -140Q22 -136 27 -128", 1.3)))
    trim = scallop([(-8, -101), (-5, -110), (2, -116.5), (12, -120), (22, -121.5), (32, -119.5), (39.5, -115),
                    (39, -109), (31, -113.5), (22, -115.5), (12, -114), (3, -110), (-1, -104), (-2, -97)], 0.22)
    hd.append(S(trim, W, 2.6, F("M-10 -110L42 -116L42 -110L-10 -104Z", DL)))
    hd.append(P("M12 -114Q15.5 -106 19 -114.5Z", INK, 0) + P("M19.5 -115Q24 -108 27.5 -115.5Z", INK, 0)
              + P("M28 -115Q31.5 -109.5 34 -113.5Z", INK, 0))
    flapd = "M-19 -113C-25 -103 -23 -88 -14 -82C-7 -82 -3 -90 -3 -103C-3 -109 -9 -114 -19 -113Z"
    hd.append(S(flapd, DL, 4, F("M-12 -116L0 -116L0 -80L-12 -80Z", HA) + stitches("M-17 -107C-20 -99 -18 -91 -13 -87")))
    hd.append(L("M-9 -83Q-7 -75 -1 -72", 2.2))

    # face: near eye squeezed shut, far eye at the eyepiece, open grin; the brows lift when
    # she spots something
    hd.append(L("M7 -102.5Q14 -108.5 21 -102.5", 3.2) + L("M7 -102.5L3.5 -104.5M7.5 -100.5L4 -99.5", 1.5))
    hd.append(Mo("hc-jun-brow", [T(6, -112, 12.5, -117, 19.5, -113.5, 2.4) + T(27, -113, 32, -115.5, 38, -112, 2.2)]))
    hd.append(P("M13 -92.5Q22.5 -76 32 -94Q22.5 -89.5 13 -92.5Z", INK, 1.2) + P("M17.5 -85Q22.5 -81 27 -86Q22 -88 17.5 -85Z", W, 0))
    hd.append(E(1, -93, 6.5, 3.8, DL))
    hd.append(C(-2, -97, 0.9, INK) + C(2, -98.5, 0.9, INK) + C(0.5, -95, 0.9, INK))

    # the spyglass (brass, three draws), sparkle at the lens
    sg = (P("M0 -4.4L9 -4.4L9 4.4L0 4.4Z", W, 2.6) + F("M0.5 0.5L8.5 0.5L8.5 4L0.5 4Z", HA)
          + P("M9 -5.6L12 -5.6L12 5.6L9 5.6Z", DD, 2.4)
          + S("M12 -5.6L36 -5.6L36 5.6L12 5.6Z", W, 3, F("M12 0L36 0L36 6L12 6Z", DM) + L("M15 -3L33 -3", 1.5, W))
          + P("M36 -6.8L40 -6.8L40 6.8L36 6.8Z", DD, 2.6)
          + S("M40 -7L64 -7L64 7L40 7Z", W, 3.2, F("M40 0.5L64 0.5L64 7.5L40 7.5Z", DM) + L("M43 -4L61 -4", 1.6, W))
          + P("M64 -8.4L68 -8.4L68 8.4L64 8.4Z", DD, 2.6)
          + S("M68 -8.6L90 -9.8L90 9.8L68 8.6Z", W, 3.6, F("M68 0.5L91 0.5L91 11L68 11Z", DM)
              + L("M71 -5.6L88 -6.4", 1.6, W) + L("M78 -9L78 9", 1.3))
          + P("M90 -11L95 -11L95 11L90 11Z", DD, 2.8)
          + E(95.5, 0, 2.8, 10.5, DL, 2.6)
          + L("M20 -5.6L20 5.6M28 -5.6L28 5.6", 1.2) + L("M50 -7L50 7", 1.2))
    hd.append(g(sg, "translate(31 -104) rotate(-8)"))
    hd.append(Mo("hc-jun-spark", [
        g(ray(0, 0, -90, 0, 8, 2.2) + ray(0, 0, 0, 0, 8, 2.2) + ray(0, 0, 90, 0, 6, 2) + ray(0, 0, 180, 0, 6, 2),
          "translate(131 -132)"),
        L("M123 -134L127 -140M134 -124L140 -126", 1.6)], pivot=(131, -132)))
    # far hand wrapped over the barrel
    hd.append(S("M93 -105C92 -114 98 -120 105 -119C111 -118 114 -112 112 -106C109 -101 100 -99 93 -105Z", W, 3.6,
                F("M104 -122L116 -122L116 -98L104 -98Z", DL)))
    hd.append(L("M98 -116Q102 -114 106 -116.5M97 -111.5Q101 -109.5 105.5 -112", 1.4))
    late = [it for it in hd if isinstance(it, Mo)]
    o.append(Split(r_still(hd), "", [Mo("hc-jun-pan", [it for it in hd if not isinstance(it, Mo)] + late,
                                        pivot=JUN_NECK)]))

    # near arm: rolled sleeve, bare forearm up to the eyepiece (pans about her shoulder)
    o.append(Mo("hc-jun-pan", [
        S(cr([(9, -83), (24, -80), (37, -72), (44, -64), (37, -57), (25, -62), (11, -68), (5, -76)]), W, 4.2,
          F("M14 -66L48 -70L48 -54L14 -54Z", DM)),
        S(cr([(36, -67), (46, -84), (56, -99), (64, -102), (66, -94), (57, -79), (48, -62)]), W, 3.8,
          F("M54 -60L70 -96L70 -60Z", DL)),
        E(41, -64, 6, 9, W, 3, 32) + L("M38 -70Q37 -63 42 -58", 1.3)], pivot=(10, -76)))
    o.append(Mo("hc-jun-pan", [
        S("M56 -107C56 -116 64 -120 70 -118C76 -116 77 -108 74 -103C70 -98 60 -99 56 -107Z", W, 3.6,
          F("M68 -120L80 -120L80 -96L68 -96Z", DL)),
        L("M59 -112Q63 -110.5 67.5 -112.5M58.5 -107.5Q62.5 -106 67 -108", 1.4)], pivot=JUN_NECK))
    return o


# ---------------------------------------------------------------------------
# BOLT — peeks over the top of the O: head tucked behind the letter's edge, claws over it
# ---------------------------------------------------------------------------
BOLT_X, BOLT_Y = 790, 150
BOLT_TILT = -5  # the head's rotate(-5 0 -40)


def o_edge(x):
    """y of the O's top edge at x, and its slope angle in degrees"""
    for (x0, y0), (x1, y1) in zip(O_TOP, O_TOP[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * t, math.degrees(math.atan2(y1 - y0, x1 - x0))
    raise ValueError(x)


def bolt():
    """returns the whole robot; the head is clipped so it disappears behind the O"""
    head = []
    head.append(P("M-61 -66L-71 -64L-71 -34L-61 -32Z", DM, 4) + rivet(-66, -49, 2.6))
    head.append(P("M61 -66L71 -64L71 -34L61 -32Z", DM, 4) + rivet(66, -49, 2.6))
    # antenna: a springy two-part stalk that boings, its beep rays flashing out
    head.append(P("M-1 -89L13 -89L11 -97L1 -97Z", DM, 3))
    stalk = L("M6 -97L8 -113L24 -125", 4)
    ball = S(circ(27, -128, 7.5), W, 3.6, F(circ(31, -125, 7), DM) + C(24.5, -130.5, 2.2))
    beeps = ray(27, -128, -150, 12, 19, 2.4) + ray(27, -128, -100, 12, 19, 2.4) + ray(27, -128, -40, 12, 18, 2.4)
    head.append(Split(stalk + ball + beeps, "", [Mo("hc-bolt-ant", [
        L("M6 -97L8 -113", 4),
        Mo("hc-bolt-antb", [L("M8 -113L24 -125", 4), ball, Mo("hc-bolt-rays", [beeps], pivot=(27, -128))],
           pivot=(8, -113))], pivot=(6, -97))]))
    # the box runs on below the letter's edge; the clip hides that part
    hd = "M-51 -90C-58 -90 -62 -86 -62 -79L-61 40L61 40L62 -79C62 -86 58 -90 51 -90Z"
    head.append(S(hd, W, 5,
                  F("M42 -94L70 -94L70 44L46 44Z", DM)
                  + F("M-70 -14C-30 -10 30 -10 70 -14L70 44L-70 44Z", HA)
                  + L("M-61 -77L61 -77", 2.6)
                  + "".join(rivet(x, -83.5, 2.2) for x in (-50, -30, -10, 10, 30, 50))
                  + rivet(-53, -68) + rivet(53, -68) + rivet(-53, -24) + rivet(53, -24)
                  + L("M-40 -6Q-30 -9 -22 -6", 1.6) + flicks((-52, -72, 48, -20), 8, 21, (3, 5), (10, 40), 1.1)))
    # eyes: big camera lens and a smaller one beside it. The big lens's iris breathes in
    # and out as it focuses; for a blink its aperture snaps shut while a shutter drops over
    # the small lens. Both pupils follow the cursor.
    head.append(C(-14, -44, 27, W, 4.6))
    head.append("".join(C(-14 + 22.5 * math.cos(math.radians(a)), -44 + 22.5 * math.sin(math.radians(a)), 1.7, INK)
                        for a in (45, 135, 225, 315)))
    head.append(C(-14, -44, 19.5, DM, 3))
    iris = C(-14, -44, 14, INK)
    glint = C(-19.5, -50, 5, W) + C(-7.5, -37.5, 2.2, W) + C(-11, -53, 1.4, W)
    head.append(Split(iris + glint, "", [Mo("hc-bolt-shut", [Mo("hc-bolt-iris", [
        Look(3.5, "hc-bolt-glance", [iris + glint])], pivot=(-14, -44))], pivot=(-14, -44))]))
    lens = C(31, -57, 11.5, W, 4.2)
    pupil = C(31, -57, 6.4, INK) + C(28.6, -59.4, 2.1, W)
    shutter = P(rect(17, -98, 45, -71.5), DM, 0) + L("M17 -71.5L45 -71.5", 2.6)  # parked above the lens
    head.append(Split(lens + pupil, lens, [Look(3, "hc-bolt-glance2", [pupil]),
                                           Clip(circ(31, -57, 9.4), [Mo("hc-bolt-lid", [shutter])])]))
    head.append(E(47, -39, 6, 3.4, DL))
    grille = "M14 -31Q30 -22 46 -31L46 -23Q30 -12 14 -23Z"
    head.append(S(grille, W, 3, "".join(L(f"M{x} -36L{x} -10", 1.6) for x in range(18, 46, 5))))

    # clip: everything above the O's top edge, in Bolt-local coordinates
    k = nid()
    edge = [(x - BOLT_X, y - BOLT_Y + 0.6) for x, y in O_TOP]
    d = (f"M{n(edge[0][0])} -240" + "".join(f"L{n(x)} {n(y)}" for x, y in edge)
         + f"L{n(edge[-1][0])} -240Z")
    o = [f'<clipPath id="{k}"><path d="{d}"/></clipPath>',
         Grp([Grp([Grp(head, f"rotate({BOLT_TILT} 0 -40)")], None, 'filter="url(#halo)"')], None,
             f'clip-path="url(#{k})"')]

    # claws hooked over the curved edge, each turned to follow it; they tap the edge in turn,
    # rocking on their inner corner so they never leave it
    claws = []
    for gx, s in ((721, -1), (857, 1)):
        ey, ang = o_edge(gx)
        c = []
        palm = "M-15 0C-17 -15 -8 -23 1 -21C11 -19 15 -11 13 0Z"
        c.append(S(palm, W, 4, F("M4 -26L20 -26L20 2L4 2Z", DM) + L("M-14 -8Q0 -5 13 -8", 2)) + rivet(-1, -13, 2.2))
        for px in (-9, 7):
            c.append(S(f"M{px - 5} -3C{px - 8} 5 {px - 6} 14 {px} 18C{px + 2} 12 {px + 3} 6 {px + 5} -2Z", W, 3.6,
                       F(f"M{px} -4L{px + 8} -4L{px + 8} 20L{px} 20Z", DM)))
        c.append(T(-22 * s, -20, -26 * s, -25, -24 * s, -31, 1.8))
        tr = f"translate({n(gx - BOLT_X)} {n(ey - BOLT_Y + 1)}) rotate({n(ang)})"
        pivot = apply(tmat(tr), (13, 0) if s < 0 else (-15, 0))
        claws.append(Mo("hc-bolt-clawl" if s < 0 else "hc-bolt-clawr", [Grp(["".join(c)], tr)], pivot=pivot,
                        back=True))
    o.append(Grp(claws, None, 'filter="url(#halo)"'))
    return o


# ---------------------------------------------------------------------------
# NIB — floating ink-drop sprite between the rows
# ---------------------------------------------------------------------------
NIB_DROPS = ((62, 6, 5, 50), (84, 30, 4, 80), (54, 50, 3.4, 125), (-62, -2, 4.4, -70))


def nib():
    o = []
    # ink droplets flicked off to the sides, kept where the page behind is white (the gap
    # between the rows and the L's open corner), so they read as drops, not white patches.
    # Each one drifts off and fades, then is flicked out again to its spot.
    drops = [drop(x, y, r, a) for x, y, r, a in NIB_DROPS]
    dots = [C(78, 8, 2.2, INK), C(94, 48, 1.8, INK), C(-74, 6, 2, INK), C(38, 60, 1.6, INK)]
    pair = (0, 1, 3, 2)  # the speck that flew off with each drop
    o.append(Split("".join(drops) + "".join(dots), "", [
        Mo(f"hc-nib-d{i + 1}", [drops[i] + dots[pair[i]]], pivot=NIB_DROPS[i][:2], back=True) for i in range(4)]))
    # the sprite bobs and tilts as it floats, paddling with its little arms
    fl = []
    body = "M0 -58C8 -42 36 -22 36 4C36 26 20 40 0 40C-20 40 -36 26 -36 4C-36 -22 -8 -42 0 -58Z"
    fl.append(P(body, INK, 4.5))
    fl.append(T(-27, -2, -29, -24, -12, -38, 5.5, W) + C(-28, 7, 2.6, W))
    fl.append(T(30, 12, 30, 28, 14, 35, 2.2, W))
    nibd = "M0 -88C5 -78 13 -68 13 -58C13 -51 8 -48 0 -47C-8 -48 -13 -51 -13 -58C-13 -68 -5 -78 0 -88Z"
    fl.append(S(nibd, W, 3.6, F("M0 -90L16 -90L16 -45L0 -45Z", DM) + L("M0 -84L0 -63", 2.2) + C(0, -61, 2.8, INK)
                + L("M-12 -54Q0 -49 12 -54", 2.2)))
    # arms
    fl.append(Mo("hc-nib-arml", [L("M-33 10Q-46 6 -50 -9", 6.5) + C(-51, -12, 5.4, INK)], pivot=(-33, 10), back=True))
    fl.append(Mo("hc-nib-armr", [L("M33 14Q46 19 52 11", 6.5) + C(54.5, 9, 5.4, INK)], pivot=(33, 14), back=True))
    # face: white eyes whose pupils (clipped to the whites) follow the cursor
    whites = C(-14, -2, 13, W) + C(14, -2, 13, W)
    pupils = C(-10.5, 1.5, 6.6, INK) + C(17.5, 1.5, 6.6, INK)
    catch = C(-12.8, -1.2, 2.5, W) + C(15.2, -1.2, 2.5, W) + C(-8.5, 4, 1, W) + C(19.5, 4, 1, W)
    eye = [whites]
    for ex, px, cx, sx in ((-14, -10.5, -12.8, -8.5), (14, 17.5, 15.2, 19.5)):
        eye.append(Clip(circ(ex, -2, 13), [
            Look(3.5, "hc-nib-glance", [C(px, 1.5, 6.6, INK) + C(cx, -1.2, 2.5, W) + C(sx, 4, 1, W)])]))
    fl.append(Split(whites + pupils + catch, "", [Mo("hc-nib-blink", eye, pivot=(0, -2))]))
    fl.append(T(-23, -20, -15, -25, -7, -21, 2.6, W) + T(7, -21, 15, -25, 23, -20, 2.6, W))
    fl.append(P("M-7 16Q0 28 7 16Q0 19 -7 16Z", W, 0))
    fl.append(E(-25, 13, 5.5, 3.2, DL) + E(25, 13, 5.5, 3.2, DL))
    o.append(Mo("hc-nib-float", fl, pivot=(0, -10), back=True))
    # hover lines under it narrow as it rises and widen as it sinks
    o.append(Mo("hc-nib-hover", [L("M-16 54Q0 59 16 54", 2.4) + L("M-9 63Q0 66 9 63", 2.2)], pivot=(0, 58), back=True))
    return o


# ---------------------------------------------------------------------------
# CAPTAIN RIBBIT — sits in the L's corner, line dangling past the baseline
# ---------------------------------------------------------------------------
RIB_TIP = (108, -150)
RIB_FLEX = (75, -113)  # the rod's top section flexes from here when it twitches


def ribbit():
    o = []
    o.append(E(2, 1.5, 62, 4.5, DM))
    tipx, tipy = RIB_TIP
    # line, bobber, hooked fish: the whole rig follows the rod tip; the fish wiggles on the
    # hook, the bobber jiggles, the motion marks quiver and a drip falls off the fish
    hook_y = 868 - L_FOOT_TOP - 44
    line = L(f"M{tipx} {tipy}Q{tipx + 2} {(tipy + hook_y) / 2} {tipx} {hook_y}", 1.7)
    by = (tipy + hook_y) * 0.55
    bobber = (S(circ(tipx + 1, by, 7), W, 2.8, F(f"M{tipx - 9} {by - 9}L{tipx + 10} {by - 9}L{tipx + 10} {by}L{tipx - 9} {by}Z", HA))
              + L(f"M{tipx + 1} {by - 7}L{tipx + 1} {by - 12}", 2.4))
    fy = hook_y
    fish = g(
        L("M0 -4Q4 -1 2 3", 1.8)
        + P("M-9 30L-17 44Q-6 39 -1 45L-3 31Z", W, 3, )
        + S("M0 2C8 4 13 12 12 22C11 30 6 34 -1 36C-7 34 -12 28 -12 20C-12 10 -7 3 0 2Z", W, 3.8,
            F("M3 0L16 0L16 40L3 40Z", DM) + L("M-6 16Q-2 19 2 16M-5 22Q-1 25 3 22M-3 28Q1 31 5 28", 1.4))
        + C(-4, 11, 3, INK) + C(-4.9, 10.1, 1, W) + E(2, 5, 2.4, 1.8, INK)
        + P("M10 16L18 12L16 22Z", W, 2.4),
        f"translate({tipx} {fy}) rotate(10)")
    marks = (L(f"M{tipx - 20} {fy + 14}Q{tipx - 24} {fy + 22} {tipx - 20} {fy + 30}", 2)
             + L(f"M{tipx + 24} {fy + 12}Q{tipx + 28} {fy + 20} {tipx + 24} {fy + 28}", 2))
    drip = drop(tipx + 19, fy + 44, 2.6, 160)
    o.append(Mo("hc-rib-line", [line, Mo("hc-rib-bob", [bobber], back=True),
                                Mo("hc-rib-fish", [fish], pivot=(tipx, fy), back=True),
                                Mo("hc-rib-marks", [marks], pivot=(tipx + 2, fy + 21), back=True),
                                Mo("hc-rib-drip", [drip], back=True)], back=True, ink="inkw"))

    # rod (tapered), reel, guides; the top section is a separate piece in the motion layer
    rod = poly_tube([(0, -16), (40, -71), (75, -113), (tipx, tipy)], 6, 2)
    w_flex = 6 + (2 - 6) * 2 / 3
    guides = []
    for t in (0.45, 0.7, 0.88):
        x, y = 0 + (tipx - 0) * t, -16 + (tipy + 16) * t
        guides.append(C(x + 2, y + 2, 2.2, W, 1.5))
    o.append(Split(P(rod, INK, 1.2), P(poly_tube([(0, -16), (40, -71), RIB_FLEX], 6, w_flex), INK, 1.2),
                   [Mo("hc-rib-tip", [P(poly_tube([RIB_FLEX, (tipx, tipy)], w_flex, 2), INK, 1.2), guides[2]],
                       pivot=RIB_FLEX)]))
    o.append(S(circ(20, -36, 7.5), W, 2.8, C(20, -36, 2.4, INK)) + L("M20 -36L29 -30", 2.4) + C(29.5, -29.5, 2.4, INK))
    o.append(guides[0])
    o.append(guides[1])
    o.append(Split(guides[2], "", []))  # drawn by the rod tip in the motion layer

    # dangling legs and webbed feet
    for s, fx in ((-1, -24), (1, 20)):
        o.append(S(f"M{fx - 7} -4L{fx + 7} -4L{fx + 6} 21L{fx - 6} 21Z", W, 3.8,
                   F(f"M{fx + 1} -6L{fx + 10} -6L{fx + 10} 24L{fx + 1} 24Z", DL) + E(fx - 2, 8, 2.4, 3.2, DM, 1.2)))
        foot = (f"M{fx - 6} 19C{fx - 16} 22 {fx - 20} 31 {fx - 17} 37Q{fx - 12} 33 {fx - 8} 34"
                f"Q{fx - 4} 41 {fx + 1} 37Q{fx + 6} 33 {fx + 9} 36C{fx + 13} 30 {fx + 10} 22 {fx + 6} 19Z")
        o.append(S(foot, W, 3.6, F(f"M{fx + 2} 18L{fx + 14} 18L{fx + 14} 40L{fx + 2} 40Z", DL)
                   + L(f"M{fx - 3} 23L{fx - 12} 33M{fx} 24L{fx} 35M{fx + 3} 23L{fx + 8} 32", 1.4)))
        o.append(C(fx - 17, 37, 3, W, 2.4) + C(fx + 1, 38, 3, W, 2.4) + C(fx + 9.5, 36, 3, W, 2.4))

    # slicker coat
    coat = "M-30 -96C-46 -88 -54 -60 -54 -30C-54 -12 -50 -2 -44 3L44 3C50 -6 52 -24 50 -44C48 -70 40 -90 26 -96Z"
    o.append(S(coat, W, 5,
               F("M28 -100C46 -88 56 -60 56 -30L56 8L32 8C40 -20 42 -60 28 -100Z", HA)
               + F("M-58 -8C-20 -2 20 -2 58 -8L58 8L-58 8Z", HA)
               + L("M4 -92C8 -60 10 -30 8 3", 2.6)
               + L("M-42 -70Q-36 -50 -40 -30", 1.8) + L("M-30 -40Q-26 -20 -30 -2", 1.6)
               + P("M-44 -36L-18 -37L-18 -30L-44 -29Z", W, 2.4) + stitches("M-48 -4Q0 2 48 -4")))
    for y in (-74, -50, -26):
        o.append(P(f"M11 {y - 3}L24 {y - 3.5}L24 {y + 2.5}L11 {y + 3}Z", W, 2.4) + L(f"M6 {y}L11 {y}", 1.8))
    # head
    headd = "M-44 -112C-46 -134 -24 -146 6 -146C38 -146 58 -134 58 -114C58 -100 44 -92 8 -92C-28 -92 -44 -100 -44 -112Z"
    o.append(S(headd, W, 5,
               F("M58 -150C66 -120 50 -86 8 -86L8 -96C40 -98 54 -110 50 -150Z", DL)
               + E(-30, -122, 5, 3.5, DM, 1.8) + E(-18, -132, 3.4, 2.4, DM, 1.6) + E(-36, -108, 3, 2.2, DM, 1.5)
               + E(48, -130, 3, 2.2, DM, 1.4)
               + L("M-36 -108C-12 -97 22 -98 48 -110", 3.4)
               + C(38, -126, 1.6, INK) + C(45, -126, 1.6, INK)))
    o.append(T(48, -110, 52, -112, 54, -117, 2.2) + T(-36, -108, -40, -109, -41, -113, 2))
    o.append(E(40, -112, 7, 4, DL))
    # collar
    o.append(S("M-36 -94C-32 -108 -12 -106 3 -99L1 -86C-12 -91 -25 -89 -32 -82Z", W, 4, F("M-40 -100L-10 -100L-10 -80L-40 -80Z", HA)))
    o.append(S("M32 -96C34 -108 16 -108 4 -99L6 -86C16 -91 25 -89 29 -82Z", W, 4, F("M18 -110L40 -110L40 -80L18 -80Z", HA)))
    # sou'wester hat (behind the eye bulges)
    o.append(S("M-18 -146C-18 -168 -2 -176 14 -176C30 -176 40 -166 40 -146Z", W, 4.6,
               F("M22 -180C40 -172 44 -160 42 -144L28 -144C32 -158 30 -170 22 -180Z", HA)
               + L("M4 -175C0 -164 -1 -154 0 -146M24 -175C27 -164 27 -154 26 -146", 1.8)))
    brim = "M-68 -127C-56 -146 -30 -152 10 -152C38 -152 58 -150 66 -143C58 -139 40 -141 10 -141C-20 -141 -46 -136 -68 -127Z"
    o.append(S(brim, W, 4.4, F("M-70 -136C-40 -146 20 -146 70 -142L70 -136L-70 -120Z", HA)
               + stitches("M-56 -136C-36 -146 0 -148 30 -147C46 -147 56 -146 60 -144")))
    # droopy-lidded eyes; for a slow blink the heavy lids slide all the way down
    eyes_s, eyes_b, eyes_m, rims = "", "", [], ""
    for ex, er, px in ((-14, 15, -9), (29, 13.5, 33)):
        k = nid()
        clip_def = f'<clipPath id="{k}"><path d="{circ(ex, -140, er)}"/></clipPath>'
        white = C(ex, -140, er, W)
        pup = E(px, -134, 5.2, 5, INK) + C(px - 1.6, -136, 1.6, W)
        lid = P(f"M{ex - er - 2} -160L{ex + er + 2} -160L{ex + er + 2} -140Q{ex} -134 {ex - er - 2} -140Z", DL, 0)
        shade = F(f"M{ex - er} -160L{ex + er + 2} -160L{ex + er + 2} -136L{ex + 4} -136Z", DM)
        inside = f'<g clip-path="url(#{k})">' + pup + lid + shade + "</g>"
        lidline = L(f"M{ex - er + 1} -140Q{ex} -133 {ex + er - 1} -140", 3.6)
        rim = P(circ(ex, -140, er), "none", 4.4)
        # the lid and its shading, carried on upward so a lowered lid still fills the eye
        lid_m = P(f"M{ex - er - 2} -184L{ex + er + 2} -184L{ex + er + 2} -140Q{ex} -134 {ex - er - 2} -140Z", DL, 0)
        shade_m = F(f"M{ex - 2 * er - 4} -184L{ex + er + 2} -184L{ex + er + 2} -136L{ex + 4} -136Z", DM)
        eyes_s += clip_def + white + inside + lidline + rim
        eyes_b += white + rim
        eyes_m.append(Clip(circ(ex, -140, er), [Look(3.5, "hc-rib-glance", [pup]),
                                                 Mo("hc-rib-blink", [lid_m + shade_m + lidline])]))
        rims += rim
    o.append(Split(eyes_s, eyes_b, eyes_m + [rims]))
    # arms with frog hands on the rod
    o.append(S("M-40 -82C-52 -62 -42 -36 -20 -28L-14 -39C-26 -44 -32 -60 -28 -79Z", W, 4.4,
               F("M-46 -60C-40 -44 -30 -36 -18 -32L-14 -26L-50 -26Z", HA)))
    o.append(S("M-18 -38C-14 -44 -4 -42 -1 -34C2 -26 -4 -20 -11 -22C-17 -24 -20 -32 -18 -38Z", W, 3.6,
               E(-6, -27, 2, 1.5, DM, 1)))
    o.append(C(-1.5, -33, 2.8, W, 2.2) + C(-3, -26, 2.8, W, 2.2))
    o.append(S("M22 -90C40 -92 52 -80 52 -66L38 -60C38 -70 32 -76 22 -76Z", W, 4.4,
               F("M40 -96L60 -96L60 -60L42 -60C44 -72 44 -84 40 -96Z", HA)))
    o.append(S("M36 -66C40 -72 52 -70 54 -62C56 -54 48 -50 42 -52C38 -54 35 -60 36 -66Z", W, 3.6))
    o.append(C(54, -63, 2.9, W, 2.2) + C(53, -56.5, 2.9, W, 2.2) + L("M44 -64Q48 -61 51 -64", 1.4))
    return o


# ---------------------------------------------------------------------------
# MOSS — forest giant sitting bottom-left, his back leaning on the F's left edge
# local origin = global (268, 880); the F's left edge sits at local x ~164-168
# ---------------------------------------------------------------------------
MOSS_BODY = [(-142, -8), (-170, -62), (-176, -138), (-164, -214), (-138, -276), (-92, -322), (-30, -351),
             (24, -358), (84, -347), (130, -321), (162, -284), (173, -236), (172, -170), (167, -100),
             (153, -34), (120, -8), (0, -4), (-90, -5)]
MOSS_HAND = "translate(-206 -294) rotate(-16) scale(1.2)"
MOSS_BIRD = "translate(-132 -415) rotate(-6)"


def bulge_chain(pts, bulge):
    """Q segments through pts, each bulging to the left of the direction of travel"""
    d = ""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1
        d += f"Q{n((x0 + x1) / 2 + dy / ln * ln * bulge)} {n((y0 + y1) / 2 - dx / ln * ln * bulge)} {n(x1)} {n(y1)}"
    return d


def tuft_at(x, y, ang, s=7, w=1.6):
    """three-blade grass/moss tuft standing on (x, y), leaning ang degrees from upright"""
    blades = (f"M0 0Q{n(-s * 0.3)} {n(-s * 0.5)} {n(-s * 0.75)} {n(-s * 0.9)}"
              f"M0 0Q{n(s * 0.05)} {n(-s * 0.6)} {n(s * 0.1)} {n(-s * 1.2)}"
              f"M0 0Q{n(s * 0.35)} {n(-s * 0.45)} {n(s * 0.7)} {n(-s * 0.8)}")
    return f'<path d="{blades}" fill="none" stroke="{INK}" stroke-width="{w}" transform="translate({n(x)} {n(y)}) rotate({n(ang)})"/>'


def blob(cx, cy, rx, ry, k=9, seed=1, rot=0, bulge=0.34):
    """clumpy scalloped blob (moss clump, brow)"""
    rnd = random.Random(seed)
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k + rnd.uniform(-0.15, 0.15)
        r = 1 + rnd.uniform(-0.12, 0.12)
        x, y = math.cos(a) * rx * r, math.sin(a) * ry * r
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return scallop(pts, bulge)


def rpoly(pts, r=4):
    """closed polygon with straight edges and small rounded corners (cut stone)"""
    m = len(pts)
    d = ""
    for i in range(m):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % m]
        a = (p1[0] + (p0[0] - p1[0]) * min(r / (math.dist(p0, p1) or 1), 0.45),
             p1[1] + (p0[1] - p1[1]) * min(r / (math.dist(p0, p1) or 1), 0.45))
        b = (p1[0] + (p2[0] - p1[0]) * min(r / (math.dist(p1, p2) or 1), 0.45),
             p1[1] + (p2[1] - p1[1]) * min(r / (math.dist(p1, p2) or 1), 0.45))
        d += f"{'M' if i == 0 else 'L'}{n(a[0])} {n(a[1])}Q{n(p1[0])} {n(p1[1])} {n(b[0])} {n(b[1])}"
    return d + "Z"


def arm(pts, sw=4.8, fill=W, inner=""):
    """limb that grows out of the body: filled closed, but the joining edge (last point back
    to the first) is left unstroked so the shoulder melts into the body"""
    closed = cr(pts)
    segs = _cr_ctrl(pts, True)[:-1]
    open_d = f"M{n(pts[0][0])} {n(pts[0][1])}" + "".join(
        f"C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(p2[0])} {n(p2[1])}" for _, c1, c2, p2 in segs)
    k = nid()
    return (f'<clipPath id="{k}"><path d="{closed}"/></clipPath><path d="{closed}" fill="{fill}"/>'
            f'<g clip-path="url(#{k})">{inner}</g>' + L(open_d, sw))


def moss():
    o = []
    # ground shadow, tufts and a pebble
    o.append(E(10, -1, 186, 11, DM))
    o.append(tuft_at(-172, 0, -8, 11, 2.2) + tuft_at(-160, 0, 6, 8, 2) + tuft_at(176, 0, 4, 9, 2))
    o.append(S(ell(-186, -3, 7.5, 4.6), W, 2.4, F(ell(-184, -1, 6, 3.5), HA)))

    body = cr(MOSS_BODY)
    samp = cr_samples(MOSS_BODY, k=12)

    def outward(p, d):
        dx, dy = p[0] - 0, p[1] - (-190)
        ln = math.hypot(dx, dy) or 1
        return (p[0] + dx / ln * d, p[1] + dy / ln * d)

    # moss blanket over the head: clumpy top along the silhouette, scalloped fringe below
    i0 = next(i for i, p in enumerate(samp) if p[1] < -244)
    i1 = next(i for i, p in enumerate(samp) if i > i0 + 20 and p[0] > 0 and p[1] > -282)
    top = [outward(samp[i], 3.5) for i in range(i0, i1 + 1, 3)]
    fringe = [(top[-1][0] - 2, top[-1][1] + 6), (144, -290), (122, -303), (98, -295), (72, -306), (46, -298),
              (18, -307), (-10, -298), (-38, -306), (-64, -296), (-88, -293), (-110, -281), (-128, -271),
              (-145, -253), (top[0][0] + 2, top[0][1] + 4)]
    cap = f"M{n(top[0][0])} {n(top[0][1])}" + bulge_chain(top, 0.2) + f"L{n(fringe[0][0])} {n(fringe[0][1])}" \
        + bulge_chain(fringe, 0.3) + "Z"

    # body: earth and stone, shaded away from the upper-left light
    inner = []
    inner.append(F(cr([(92, -360), (128, -310), (142, -236), (142, -150), (132, -80), (110, -20), (96, 4),
                       (230, 4), (230, -360)]), DM))
    inner.append(F(cr([(146, -300), (160, -236), (160, -150), (152, -80), (132, -14), (118, 4),
                       (230, 4), (230, -300)]), DD))
    inner.append(F("M-200 -40C-110 -24 100 -24 210 -40L210 4L-200 4Z", DM))
    inner.append(F(cr([(-178, -200), (-160, -120), (-150, -60), (-132, -30), (-110, -14), (-200, -14)]), DL))
    # moss clumps scattered over the body
    for (cx, cy, rx, ry, sd, pat) in ((140, -122, 13, 10, 4, DL), (64, -84, 15, 8, 5, DM),
                                       (-118, -46, 16, 9, 6, DL), (-110, -150, 10, 8, 7, DM), (146, -44, 12, 8, 8, DM)):
        inner.append(P(blob(cx, cy, rx, ry, 9, sd), pat, 2.2))
        inner.append(tuft_at(cx - rx * 0.3, cy - ry * 0.7, -10, 5, 1.3) + tuft_at(cx + rx * 0.4, cy - ry * 0.8, 12, 4.5, 1.3))
    # stone plates with cracks, and pebbles set in the earth
    # stones set in the earth: straight-cut edges, a lit top and a hatched side facet
    for pts in (([(-108, -94), (-96, -114), (-70, -122), (-56, -104), (-64, -84), (-92, -80)]),
                ([(96, -66), (110, -90), (130, -84), (144, -70), (134, -48), (104, -52)]),
                ([(6, -94), (24, -112), (40, -108), (54, -98), (46, -78), (14, -80)])):
        dd = rpoly(pts, 4)
        side = rpoly([pts[2], pts[3], pts[4], pts[5], (pts[5][0] + 4, pts[5][1] - 8), (pts[3][0] - 8, pts[3][1] - 2)], 2)
        inner.append(S(dd, W, 2.8, F(side, HA) + L(f"M{n(pts[5][0] + 4)} {n(pts[5][1] - 8)}L{n(pts[3][0] - 8)} {n(pts[3][1] - 2)}", 1.6)
                       + L(f"M{n(pts[0][0] + 5)} {n(pts[0][1] - 3)}L{n(pts[1][0] + 4)} {n(pts[1][1] + 3)}L{n(pts[2][0] - 2)} {n(pts[2][1] + 5)}", 1.3, W)))
    # cracks running through the stone of his body
    inner.append(L("M78 -292L84 -280L80 -270L90 -258", 1.8) + L("M84 -280L94 -284", 1.4)
                 + L("M-132 -66L-124 -56L-128 -44L-118 -34", 1.8) + L("M-124 -56L-114 -60", 1.4)
                 + L("M150 -210L142 -198L148 -186", 1.6))
    for (x, y, rx, ry) in ((-112, -176, 6.5, 4.6), (64, -158, 6, 4.4), (-38, -72, 6, 4), (152, -96, 6, 4.5),
                           (-150, -30, 6, 4), (-124, -150, 5.5, 4)):
        inner.append(S(ell(x, y, rx, ry), W, 2.2, F(ell(x + 2, y + 2, rx * 0.8, ry * 0.75), HA)))
    inner.append(specks((-160, -110, -60, -30), 26, 12, (0.7, 1.5)) + specks((60, -150, 150, -40), 22, 13, (0.7, 1.5))
                 + specks((-130, -290, 130, -200), 18, 14, (0.6, 1.2)))
    inner.append(flicks((-150, -280, 150, -40), 40, 15, (4, 8), (25, 70), 1.4))
    # the sash runs round the body: rope band with twist marks
    sash = "M-182 -186Q-2 -148 182 -102L182 -83Q-2 -129 -182 -166Z"
    twist = []
    for i in range(44):
        t = i / 43
        x = (1 - t) ** 2 * -182 + 2 * (1 - t) * t * -2 + t * t * 182
        y = (1 - t) ** 2 * -176 + 2 * (1 - t) * t * -139 + t * t * -92.5
        twist.append(L(f"M{n(x - 5)} {n(y - 9)}Q{n(x + 2)} {n(y - 3)} {n(x + 4)} {n(y + 9)}", 2))
    inner.append(S(sash, W, 3.4, F("M-190 -174Q-2 -136 190 -90L190 -70L-190 -70Z", DM) + "".join(twist)
                   + L("M-182 -176Q-2 -139 182 -92.5", 1.2, W)))
    o.append(S(body, W, 5.5, "".join(inner)))

    # the moss blanket on top, its clumps breaking the silhouette
    k = nid()
    cap_in = (F(blob(-60, -322, 34, 14, 10, 21), DM) + F(blob(40, -330, 30, 12, 10, 22), DM)
              + F(blob(110, -300, 18, 10, 9, 23), DM) + F(blob(-122, -280, 14, 12, 9, 24), DM)
              + P(blob(-20, -340, 18, 8, 9, 25), W, 0) + P(blob(-96, -314, 12, 6, 9, 26), W, 0)
              + "".join(tuft_at(x, y, a, 6, 1.4) for x, y, a in ((-110, -300, -20), (-80, -320, -10), (-40, -332, 0),
                                                                 (0, -338, 4), (40, -340, 6), (80, -326, 14),
                                                                 (118, -306, 24), (-130, -270, -30), (20, -312, 0),
                                                                 (-60, -310, -6), (70, -306, 8)))
              + specks((-140, -350, 140, -296), 30, 27, (0.7, 1.5)))
    o.append(f'<clipPath id="{k}"><path d="{cap}"/></clipPath><path d="{cap}" fill="{DL}"/>'
             f'<g clip-path="url(#{k})">{cap_in}</g>')
    o.append(L(f"M{n(top[0][0])} {n(top[0][1])}" + bulge_chain(top, 0.2), 4.6))
    o.append(L(f"M{n(fringe[0][0])} {n(fringe[0][1])}" + bulge_chain(fringe, 0.3), 2.6))

    # tufts and sprouts standing out of the silhouette
    for i in range(1, len(top) - 1, 2):
        x, y = top[i]
        ang = math.degrees(math.atan2(x - 0, -(y + 190))) * 0.9
        if not (-40 < x < 30):  # leave room for the leaf stem
            o.append(tuft_at(x, y + 1, ang, 8, 1.8))

    def sprout(x, y, s=1.0, lean=0):
        return g(L("M0 0Q-1 -8 0 -16", 2.4)
                 + S("M0 -15C-4 -22 -13 -24 -18 -20C-13 -14 -5 -13 0 -15Z", W, 2.4, F("M-18 -18L0 -18L0 -12L-18 -12Z", DL))
                 + S("M0 -16C3 -24 12 -27 17 -24C13 -17 5 -15 0 -16Z", W, 2.4, F("M0 -20L17 -20L17 -14L0 -14Z", DM)),
                 f"translate({x} {y}) rotate({lean}) scale({s})")
    o.append(sprout(-118, -310, 0.8, -36) + sprout(58, -352, 0.85, 10) + sprout(-138, -282, 0.6, -52))

    # mushrooms on his right shoulder, where it rests on the F
    for (mx, my, sc, rot) in ((126, -322, 1.0, 26), (150, -300, 0.78, 40), (104, -338, 0.62, 12)):
        o.append(g(S("M-5 0C-6 -8 -5 -16 -4 -22L4 -22C5 -16 6 -8 5 0Z", W, 2.6, F("M0 -24L8 -24L8 2L0 2Z", DL))
                   + S("M-18 -20C-18 -32 -8 -38 0 -38C8 -38 18 -32 18 -20C8 -17 -8 -17 -18 -20Z", W, 3.4,
                       F("M4 -40L22 -40L22 -16L8 -16Z", DM) + C(-8, -28, 3, W, 1.6) + C(4, -32, 2.4, W, 1.6)
                       + C(11, -24, 2, W, 1.4))
                   + L("M-14 -20Q0 -16 14 -20", 1.4) + L("M-11 -19L-9 -15M-4 -18L-3 -14M3 -18L3 -14M9 -19L8 -15", 1),
                   f"translate({mx} {my}) rotate({rot}) scale({sc})"))

    # acorn charm hanging from the sash
    o.append(L("M-30 -136Q-35 -130 -30 -124M-30 -136Q-25 -130 -30 -124", 2))
    o.append(S("M-42 -118C-42 -102 -35 -92 -30 -89C-25 -92 -18 -102 -18 -118Z", W, 3,
               F("M-30 -120L-15 -120L-15 -86L-30 -86Z", DL) + T(-37, -113, -38, -105, -35, -97, 2, INK)))
    o.append(P("M-45 -117Q-30 -135 -15 -117Q-30 -112 -45 -117Z", CH, 3) + L("M-30 -128L-28 -135", 2.6))

    # face: calm half-lidded eyes under mossy brows, pebble nose, wide soft smile; head tilted
    # a little toward the F he leans on. The dark eyes look round under their white lids and
    # blink by squashing up into the lid line.
    f = []
    f.append(Mo("hc-moss-brow", [P(blob(-56, -263, 17, 7, 9, 31, -12, 0.4), DM, 2.2)
                                 + P(blob(16, -266, 16, 7, 9, 32, 12, 0.4), DM, 2.2)]))
    for (x, y) in ((-54, -239), (16, -242)):
        eye = E(x, y, 7, 8.8, INK)
        lid = P(f"M{x - 10} {y - 1.5}Q{x} {y - 7} {x + 10} {y - 1.5}L{x + 10} {y - 13}L{x - 10} {y - 13}Z", W, 0)
        lidline = T(x - 10.5, y - 1, x, y - 8, x + 10.5, y - 1, 2)
        catch = C(x - 2.6, y + 1.6, 1.9, W) + C(x + 2.4, y + 4.6, 0.8, W)
        f.append(Split(eye + lid + lidline + catch, "", [
            Mo("hc-moss-blink", [Look(2.5, "hc-moss-glance", [eye + catch])], pivot=(x, y - 3)), lid + lidline]))
        f.append(L(f"M{x - 8} {y + 12}Q{x} {y + 16} {x + 8} {y + 12}", 1.6))
    nose = [(-41, -216), (-35, -226), (-21, -229), (-7, -225), (-2, -215), (-12, -207), (-30, -206)]
    f.append(S(cr(nose), W, 3.2, F(cr([(x + 5, y + 6) for x, y in nose]), HA) + L("M-34 -222Q-27 -226 -19 -225", 1.6, W)))
    f.append(T(-34, -201.5, -21, -199, -8, -202, 1.6))
    mouth = "M-74 -194Q-22 -184 30 -197Q-22 -154 -74 -194Z"
    f.append(S(mouth, INK, 3, E(-20, -175, 19, 7.5, DL) + L("M-20 -181L-20 -175", 1.3)))
    f.append(T(-78, -199, -79.5, -193, -75, -188, 1.8) + T(34, -202, 35.5, -196, 31.5, -191, 1.8))
    f.append(L("M-42 -165Q-22 -159 -2 -165", 1.6))
    f.append(E(-90, -210, 16, 10, DL) + E(52, -214, 14, 9, DL))
    f.append(specks((-100, -216, -80, -204), 4, 41, (0.7, 1.1)) + specks((44, -220, 62, -208), 3, 42, (0.7, 1.1)))
    o.append(Grp(f, "rotate(4 -20 -225)"))

    # stubby arms: the left one raised in a slow, friendly wave; the right hand rests on his
    # belly (shoulders melt into the body). The raised arm waves from the shoulder and the
    # hand follows through from the wrist.
    larm = [(-140, -186), (-166, -180), (-190, -190), (-207, -210), (-216, -234), (-221, -258), (-220, -278),
            (-198, -284), (-192, -262), (-191, -242), (-178, -226), (-156, -224), (-136, -232)]
    wave = [arm(larm, 4.8, W, F(cr([(-150, -178), (-178, -186), (-202, -210), (-212, -246), (-196, -252),
                                    (-182, -230), (-150, -216)]), DM)
                + F(blob(-168, -214, 15, 9, 8, 51, -20), DM) + tuft_at(-172, -222, -30, 6, 1.4)
                + flicks((-210, -250, -180, -200), 4, 53, (3, 6), (40, 80), 1.3))]
    # open stubby hand, palm out (the wrist edge is left unstroked)
    hand = ("M-13 16C-18 8 -20 -4 -18 -14C-22 -22 -24 -32 -19 -36C-14 -39 -10 -34 -9 -27"
            "C-10 -36 -8 -43 -2 -43C4 -43 6 -36 4 -27C6 -34 10 -38 14 -36C19 -33 19 -24 16 -16"
            "C21 -15 27 -16 30 -11C33 -5 28 2 20 4C16 9 13 13 13 16")
    k = nid()
    wave.append(Mo("hc-moss-hand", [g(f'<clipPath id="{k}"><path d="{hand}Z"/></clipPath><path d="{hand}Z" fill="{W}"/>'
                                      f'<g clip-path="url(#{k})">' + F("M6 -50L40 -50L40 20L6 20Z", DL)
                                      + F("M-30 8C-10 14 10 14 30 6L30 24L-30 24Z", DM) + "</g>"
                                      + L(hand, 4.6) + L("M-9 -26L-9 -16M4 -26L4 -17", 1.8) + L("M-8 2Q1 7 9 1", 1.6)
                                      + L("M16 -15Q14 -10 15 -5", 1.6), MOSS_HAND)],
                   pivot=apply(tmat(MOSS_HAND), (0, 15))))
    wave.append(L("M-238 -276Q-246 -296 -240 -316", 2.4) + L("M-250 -282Q-258 -302 -252 -322", 2)
                + L("M-222 -346Q-206 -354 -190 -346", 2))  # wave marks
    # the arm's shadow on his side
    wave.append(F(cr([(-166, -176), (-150, -170), (-138, -184), (-150, -188)]), DM))
    o.append(Split(r_still(wave), "", [Mo("hc-moss-arm", [wave[0], wave[2], wave[3], wave[1]], pivot=(-150, -208))]))
    rarm = [(150, -240), (160, -206), (160, -170), (146, -138), (120, -116), (96, -108), (78, -112),
            (72, -124), (82, -134), (90, -134), (110, -152), (120, -180), (118, -214), (112, -238)]
    o.append(arm(rarm, 4.8, W, F(cr([(136, -250), (152, -200), (140, -150), (108, -116), (180, -110), (180, -250)]), DM)
                 + tuft_at(138, -235, 16, 5, 1.4) + tuft_at(128, -238, 4, 4.5, 1.3)
                 + flicks((122, -210, 150, -150), 5, 54, (3, 6), (40, 80), 1.3)))
    o.append(L("M84 -134Q90 -130 92 -136", 2.2))  # thumb
    o.append(L("M80 -122Q77 -114 82 -109M90 -119Q88 -111 93 -106", 1.8))
    # boulder feet, toes like pebbles
    for (pts, toes, shade) in (
        ([(-140, -34), (-128, -58), (-96, -68), (-62, -60), (-46, -34), (-58, -6), (-96, 2), (-130, -6)],
         ((-120, -58), (-98, -66), (-76, -60)), "M-76 -70C-48 -50 -46 -14 -80 4L-40 6L-40 -70Z"),
        ([(18, -36), (30, -60), (62, -70), (96, -62), (110, -36), (100, -8), (64, 2), (28, -6)],
         ((40, -62), (62, -69), (84, -63)), "M82 -72C112 -50 112 -14 76 4L120 6L120 -72Z")):
        fd = cr(pts)
        x0 = min(p[0] for p in pts)
        o.append(S(fd, W, 4.8, F(shade, DM) + flicks((x0 + 10, -50, x0 + 80, -10), 7, int(x0) + 300, (3, 6), (30, 70), 1.4)
                   + L(f"M{x0 + 22} -26L{x0 + 30} -18L{x0 + 27} -8", 1.5)
                   + F(blob(x0 + 26, -46, 10, 6, 8, int(x0) + 400), DL)))
        for tx, ty in toes:
            o.append(S(ell(tx, ty, 9, 7), W, 3, F(ell(tx + 3, ty + 2.5, 7, 5), DL)))
        o.append(tuft_at(toes[1][0] + 2, toes[1][1] - 6, 6, 6, 1.6))

    # the big leaf grows from the top of his head on a short curved stem; it sways in the
    # breeze from the stem base, the leaf lagging a little behind the stem, and the bird
    # riding it hops and pecks now and then
    stem = poly_tube([(6, -350), (5, -364), (-2, -376), (-15, -384)], 10, 7)
    sway = [S(stem, W, 3, F("M3 -390L14 -390L14 -348L3 -348Z", DM))]
    sway.append(L("M2 -370Q-6 -374 -9 -369", 1.4))
    leaf = "M-14 -383C-36 -420 -110 -428 -168 -388C-124 -364 -52 -352 -14 -383Z"
    veins = "".join(L(f"M{x} {y}Q{x - 9} {y - 10} {x - 22} {y - 13}", 1.6)
                    for x, y in ((-34, -392), (-62, -397), (-92, -399), (-120, -396)))
    veins += "".join(L(f"M{x} {y}Q{x - 8} {y + 7} {x - 19} {y + 8}", 1.4) for x, y in ((-44, -394), (-76, -398), (-108, -397)))
    blade = [S(leaf, W, 4.4, F("M-172 -390C-110 -399 -56 -397 -10 -383L-10 -350L-172 -350Z", DM)
               + F("M-34 -420C-56 -424 -84 -426 -114 -420L-114 -406C-84 -410 -56 -408 -34 -406Z", DL)
               + L("M-14 -383C-56 -397 -110 -401 -166 -388", 2.4) + veins)]
    blade.append(L("M-150 -390Q-158 -385 -164 -388", 1.4))
    # the bird perched near the leaf's tip
    bird_pre = (L("M-2 0L-4 8M4 0L5 8", 2.2) + L("M-8 8L-1 8M2 8L9 8", 1.8)
                + P("M10 -6L26 -18L22 -6L28 -6L16 2Z", DM, 2.6)
                + S("M-16 -8C-18 -22 -6 -30 4 -26C12 -23 15 -14 13 -6C9 2 -10 2 -16 -8Z", W, 3.6,
                    F("M0 -30L20 -30L20 4L4 4C10 -6 8 -20 0 -30Z", DM) + F("M-18 -2C-8 4 6 4 16 -2L16 4L-18 4Z", DL))
                + P("M-4 -14C2 -18 10 -14 10 -8C4 -6 -2 -8 -4 -14Z", DL, 2.2)
                + P("M-16 -18L-26 -15L-16 -12Z", W, 2.4))
    bird_eye = C(-9, -18, 2.4, INK) + C(-9.8, -18.8, 0.8, W)
    bird_post = E(-11, -11, 2.6, 1.6, DL) + T(-4, -27, -6, -33, -2, -37, 2.2) + T(0, -26, 2, -33, 6, -35, 2)
    bird = Grp([bird_pre + bird_eye + bird_post], MOSS_BIRD)
    blade.append(Mo("hc-moss-bird", [bird], pivot=apply(tmat(MOSS_BIRD), (0.5, 8)), back=True))
    sway.append(Mo("hc-moss-leaf", blade, pivot=(-14, -383), back=True))
    o.append(Mo("hc-moss-stem", sway, pivot=(6, -350)))
    return o


# ---------------------------------------------------------------------------
# QUIRK — original critter with a question-mark tail, peeking round the K
# ---------------------------------------------------------------------------
def quirk():
    o = []
    o.append(E(10, -1, 46, 5.5, DM))
    tail = "M30 -30C54 -44 66 -80 64 -112C62 -150 40 -172 18 -170C0 -168 -6 -152 2 -140"
    body = "M-30 -60C-34 -88 -14 -104 8 -104C32 -104 44 -84 42 -54C40 -24 30 -2 6 -2C-18 -2 -30 -28 -30 -60Z"
    headd = scallop([(-56, -116), (-54, -132), (-42, -144), (-24, -149), (-6, -144), (6, -132), (9, -114),
                     (2, -94), (-12, -84), (-30, -82), (-46, -90)], 0.18)
    # the tail swishes behind the body and head: in the motion layer it is clipped out of
    # both, and their outlines are re-inked over it further down
    o.append(Clip(BIG + body, [Clip(BIG + headd, [Mo("hc-qk-tail", [
        L(tail, 31) + L(tail, 23.5, W) + L(tail, 23.5, DD, 'stroke-dasharray="12 14"'),
        T(-6, -146, -10, -134, -2, -124, 3) + T(4, -150, 10, -140, 8, -128, 2.4)], pivot=(30, -30))],
        evenodd=True)], evenodd=True))
    o.append(S(body, W, 4.8, F("M14 -108C40 -100 48 -60 40 -30C34 -10 24 0 10 2L50 2L50 -108Z", DM)
               + P("M-18 -64C-20 -42 -12 -16 6 -12C18 -16 22 -40 18 -64C10 -72 -10 -72 -18 -64Z", W, 0)
               + L("M-18 -64C-20 -42 -12 -16 6 -12C18 -16 22 -40 18 -64", 1.6, extra='stroke-dasharray="1 0"')
               + tufts((-12, -56, 12, -20), 6, 41, 4, 1.3)))
    for fx in (-14, 22):
        o.append(S(f"M{fx - 13} 0C{fx - 15} -8 {fx - 8} -13 {fx} -12C{fx + 9} -12 {fx + 14} -6 {fx + 12} 0Z", W, 3.8,
                   F(f"M{fx + 2} -14L{fx + 16} -14L{fx + 16} 2L{fx + 2} 2Z", DL))
                 + L(f"M{fx - 4} -1L{fx - 4} -5M{fx + 3} -1L{fx + 3} -5", 1.6))
    # ears twitch from their roots (clipped out of the head, which lies over them)
    o.append(Clip(BIG + headd, [
        Mo("hc-qk-earl", [S("M-48 -128C-66 -146 -80 -168 -78 -180C-64 -180 -46 -162 -36 -140Z", W, 4.2,
                            P("M-48 -136C-60 -150 -70 -164 -70 -172C-62 -170 -50 -156 -43 -142Z", HA, 2))],
           pivot=(-42, -134), back=True),
        Mo("hc-qk-earr", [S("M-14 -140C-17 -160 -12 -180 -3 -187C7 -177 9 -158 2 -136Z", W, 4.2,
                            P("M-10 -144C-12 -160 -8 -174 -3 -179C3 -171 4 -158 -1 -142Z", HA, 2)
                            + F("M0 -190L12 -190L12 -130L0 -130Z", DM))], pivot=(-6, -138))], evenodd=True))
    # head with fluffy cheeks
    tuft = P("M-34 -146L-30 -158L-24 -148L-20 -160L-15 -147Z", W, 2.6)
    # (the band above y=-118 holds the head's outline where the ears and tail meet it; the
    # tuft is redrawn over it as in the still; the second box is where the tail leaves the body)
    o.append(MOnly([Clip(rect(-400, -500, 400, -118) + rect(25, -80, 400, -14), [L(headd, 4.6), L(body, 4.8), tuft])]))
    o.append(S(headd, W, 4.6, F(circ(-12, -108, 28), DL) + P(circ(-30, -118, 30), W, 0)))
    o.append(tuft)
    eyes = E(-36, -114, 5.6, 7.2, INK) + E(-12, -116, 5.6, 7.2, INK)
    catch = C(-37.8, -116.8, 2.3) + C(-13.8, -118.8, 2.3) + C(-34.4, -110.8, 0.9) + C(-10.4, -112.8, 0.9)
    o.append(Split(eyes + catch, "", [Mo("hc-qk-blink", [Look(2.2, "hc-qk-glance", [eyes + catch])],
                                        pivot=(-24, -115))]))
    o.append(T(-42, -125, -37, -128, -31, -126, 2.2) + T(-17, -131, -11, -135, -5, -131, 2.2))
    o.append(P("M-27 -106C-25 -108 -21 -108 -19 -106C-20 -103 -22 -102 -23 -102C-24 -102 -26 -103 -27 -106Z", INK, 0))
    o.append(L("M-31 -97Q-27 -93 -23 -97Q-19 -93 -15 -97", 2.2) + P("M-25 -96L-21 -96L-21 -92.5L-25 -92.5Z", W, 1.4))
    o.append(E(-44, -101, 5.6, 3.4, DL) + E(-4, -103, 5.6, 3.4, DL))
    o.append(L("M-52 -104L-64 -106M-52 -99L-63 -97M5 -106L16 -109M5 -101L16 -100", 1.4))
    # paws: one resting on the K's edge, one at the chest
    o.append(S("M-24 -78C-36 -82 -52 -84 -62 -82C-70 -80 -70 -72 -62 -70C-52 -68 -36 -66 -22 -64Z", W, 4,
               F("M-70 -76L-20 -76L-20 -60L-70 -60Z", DL)))
    o.append(L("M-62 -79L-62 -72M-56 -80L-56 -71", 1.5))
    # the other paw held up shyly at the chest (forearm + mitten paw with toe creases); it
    # gives a little wave from the elbow
    o.append(Mo("hc-qk-paw", [
        S(cr([(26, -50), (24, -62), (16, -74), (6, -82), (-3, -80), (-5, -72), (4, -64), (12, -54)]), W, 3.6,
          F("M10 -86L30 -86L30 -46L10 -46Z", DL)),
        L("M-2 -77L3 -74.5M1.5 -81L6 -77", 1.4)], pivot=(19, -53)))
    return o


# ---------------------------------------------------------------------------
# ANIMATION. Every class keyframes from and back to identity, so animation:none is the
# still drawing. Amounts are in viewBox units and degrees.
# ---------------------------------------------------------------------------
EASE = "cubic-bezier(.45,0,.55,1)"
SIN_OUT, SIN_IN, SIN_IO = "cubic-bezier(.61,1,.88,1)", "cubic-bezier(.12,0,.39,0)", "cubic-bezier(.37,0,.63,1)"
DOWN, UP = "cubic-bezier(.55,0,1,.45)", "cubic-bezier(0,.55,.45,1)"  # strike / rebound
ANIM = {}


def anim(cls, dur, delay, frames, ease=EASE):
    """frames: [(pct or (pcts), css declarations)]; a declaration list may end with
    ';animation-timing-function:...' for the segment that starts there"""
    ANIM[cls] = (dur, delay, ease, frames)


def rot(cls, dur, delay, pts, ease=EASE):
    anim(cls, dur, delay, [(p, f"transform:rotate({n2(a)}deg)") for p, a in pts], ease)


def tr(cls, dur, delay, pts, ease=EASE):
    anim(cls, dur, delay, [(p, f"transform:translate({n2(x)}px,{n2(y)}px)") for p, x, y in pts], ease)


def blink(cls, dur, delay, at, double=False):
    """eye squash to 8% height: closes in ~70ms, holds ~120ms, opens in ~100ms"""
    ms = lambda t: t / dur / 10  # milliseconds as % of the cycle
    pts = [(0, 1), (at, 1), (at + ms(70), .08), (at + ms(190), .08), (at + ms(290), 1)]
    if double:
        b = at + ms(420)
        pts += [(b, 1), (b + ms(70), .08), (b + ms(170), .08), (b + ms(270), 1)]
    pts.append((100, 1))
    anim(cls, dur, delay, [(p, f"transform:scale(1,{n2(s)})") for p, s in pts])


def sway(cls, dur, delay, amp, amp2=None):
    """smooth sine swing through rest: +amp, then -amp2"""
    a2 = amp if amp2 is None else amp2
    anim(cls, dur, delay, [(0, f"transform:rotate(0deg);animation-timing-function:{SIN_OUT}"),
                           (25, f"transform:rotate({n2(amp)}deg);animation-timing-function:{SIN_IO}"),
                           (75, f"transform:rotate({n2(-a2)}deg);animation-timing-function:{SIN_IN}"),
                           (100, "transform:rotate(0deg)")])


# MOSS: a slow giant's wave every 6.4s (three swings from the shoulder, the hand trailing
# from the wrist), half-lidded blink, glances, the leaf in the breeze and the bird's antics
rot("hc-moss-arm", 6.4, -0.6, [(0, 0), (7, 14), (17, -5), (28, 14), (39, -5), (50, 10), (61, 0), (100, 0)])
rot("hc-moss-hand", 6.4, -0.6, [(0, 0), (3.5, -10), (9, 5), (12, 11), (19, -5), (22.5, -11), (30, 5), (33.5, 11),
                                (41, -5), (44.5, -10), (52, 4), (56, 7), (63, 0), (100, 0)])
tr("hc-moss-brow", 6.4, -0.6, [(0, 0, 0), (6, 0, -2.6), (55, 0, -2.6), (63, 0, 0), (100, 0, 0)])
blink("hc-moss-blink", 5.3, -1.9, 88)
tr("hc-moss-glance", 7.9, -3.1, [(0, 0, 0), (9, -2.2, 0.5), (32, -2.2, 0.5), (40, 2, -0.4), (62, 2, -0.4),
                                 (70, 0, 0), (100, 0, 0)])
sway("hc-moss-stem", 5.9, -2.2, 1.8)
sway("hc-moss-leaf", 5.9, -1.5, 2.4)
_B = "transform:translate({}px,{}px) rotate({}deg) scale({},{})"
anim("hc-moss-bird", 8.3, -5.1, [
    ((0, 15), _B.format(0, 0, 0, 1, 1)), (18.5, _B.format(0, 0, 0, 1.07, .88)),
    (22.5, _B.format(0, -11, 0, .95, 1.07)), (26.5, _B.format(0, 0, 0, 1.08, .88)), (30, _B.format(0, 0, 0, 1, 1)),
    (58, _B.format(0, 0, 0, 1, 1)), (60.5, _B.format(0, 0, -24, 1, 1)), (63, _B.format(0, 0, -2, 1, 1)),
    (65.5, _B.format(0, 0, -24, 1, 1)), (68.5, _B.format(0, 0, 0, 1, 1)), (100, _B.format(0, 0, 0, 1, 1))])

# PIP: on a 6.6s loop his boots kick in turn from the knees and set the lantern swinging,
# the swing dying away before the next kicks; the flame flickers, the scarf flutters
_K = "transform:rotate({}deg) scale(1,{})"
anim("hc-pip-legl", 6.6, -0.4, [((0,), _K.format(0, 1)), (5, _K.format(14, .88)), (10.5, _K.format(-3, 1)),
                                (14.5, _K.format(0, 1)), (27, _K.format(0, 1)), (32, _K.format(10, .92)),
                                (37, _K.format(-2, 1)), (41, _K.format(0, 1)), (100, _K.format(0, 1))])
anim("hc-pip-legr", 6.6, -0.4, [((0, 12), _K.format(0, 1)), (17, _K.format(-14, .88)), (22.5, _K.format(3, 1)),
                                (26.5, _K.format(0, 1)), (38, _K.format(0, 1)), (43, _K.format(-10, .92)),
                                (48, _K.format(2, 1)), (52, _K.format(0, 1)), (100, _K.format(0, 1))])
_q = 100 / 12  # a 2.2s pendulum period is a third of the loop
anim("hc-pip-lantern", 6.6, -0.4, [(0, f"transform:rotate(0deg);animation-timing-function:{SIN_OUT}")] + [
    (_q * (2 * i + 1), f"transform:rotate({a}deg);animation-timing-function:{SIN_IN if i == 5 else SIN_IO}")
    for i, a in enumerate((8, -7.2, 6, -4.8, 3.6, -2.5))] + [(100, "transform:rotate(0deg)")])
anim("hc-pip-flame", 1.9, 0, [(p, f"transform:scale({sx},{sy})") for p, sx, sy in
                              ((0, 1, 1), (14, .92, 1.12), (29, 1.05, .93), (43, .96, 1.08), (58, 1.04, .9),
                               (72, .94, 1.1), (87, 1.02, .96), (100, 1, 1))])
_RY = [(0, "transform:scale(1);opacity:1"), (30, "transform:scale(.84);opacity:.7"),
       (55, "transform:scale(1.08);opacity:1"), (75, "transform:scale(1);opacity:1"), (100, "transform:scale(1);opacity:1")]
anim("hc-pip-raya", 2.6, 0, _RY)
anim("hc-pip-rayb", 2.6, -1.3, _RY)
_FL = ((0, 0), (12, 1), (26, -.85), (40, .85), (54, -.65), (68, .35), (80, 0), (100, 0))
for i, (amp, dl) in enumerate(((3, -1.0), (4.2, -0.82), (5.4, -0.64))):
    rot(f"hc-pip-scarf{i + 1}", 3.8, dl, [(p, a * amp) for p, a in _FL])
anim("hc-pip-wind", 3.8, -0.64, [(p, f"transform:translate({x}px,{y}px);opacity:{o}") for p, x, y, o in
                                 ((0, 0, 0, 1), (22, 4.5, -1.2, .6), (44, 0, 0, 1), (66, 3.5, -1, .7), (86, 0, 0, 1),
                                  (100, 0, 0, 1))])
blink("hc-pip-blink", 4.4, -0.7, 82, double=True)
tr("hc-pip-glance", 6.1, -2.4, [(0, 0, 0), (8, 1.8, -0.4), (30, 1.8, -0.4), (36, -1.6, 0.5), (58, -1.6, 0.5),
                                (64, 0, 0), (100, 0, 0)])

# BOLT: antenna boing (two springy joints, beep rays flashing), focusing iris, a camera
# blink (aperture snaps shut, shutter drops on the small lens), glances, claw taps
rot("hc-bolt-ant", 4.9, -1.4, [(0, 0), (5, -12), (10, 9), (15, -6.5), (20, 4.5), (25, -2.5), (30, 1.2), (35, 0), (100, 0)])
rot("hc-bolt-antb", 4.9, -1.4, [(0, 0), (6.5, -10), (11.5, 10), (16.5, -7), (21.5, 4.5), (26.5, -2.5), (31.5, 1.2),
                                (37, 0), (100, 0)])
anim("hc-bolt-rays", 4.9, -1.4, [(0, "transform:scale(1);opacity:1"), (4, "transform:scale(1.4);opacity:.2"),
                                 (4.1, "transform:scale(.5);opacity:0"), (13, "transform:scale(1);opacity:1"),
                                 (100, "transform:scale(1);opacity:1")])
anim("hc-bolt-iris", 3.7, -0.9, [(p, f"transform:scale({s})") for p, s in
                                 ((0, 1), (14, .86), (22, .9), (32, .8), (48, 1.06), (58, 1), (100, 1))])
anim("hc-bolt-shut", 6.7, -4.2, [((0, 91.5), "transform:scale(1)"), (93, "transform:scale(.12)"),
                                 (95.5, "transform:scale(.12)"), (97.5, "transform:scale(1.05)"),
                                 (99, "transform:scale(1)"), (100, "transform:scale(1)")])
_LD = 26.5  # the shutter's drop, along the tilted head's own vertical
_lx, _ly = -math.sin(math.radians(BOLT_TILT)) * _LD, math.cos(math.radians(BOLT_TILT)) * _LD
tr("hc-bolt-lid", 6.7, -4.2, [(0, 0, 0), (91.5, 0, 0), (93, _lx, _ly), (95.5, _lx, _ly), (97.5, 0, 0), (100, 0, 0)])
tr("hc-bolt-glance", 5.3, -2.6, [(0, 0, 0), (10, -2.6, 1), (34, -2.6, 1), (41, 2.4, -1.2), (66, 2.4, -1.2),
                                 (73, 0, 0), (100, 0, 0)])
tr("hc-bolt-glance2", 4.1, -0.5, [(0, 0, 0), (6, 2.4, -1), (28, 2.4, -1), (32, -2.2, 0.8), (54, -2.2, 0.8),
                                  (58, 0.6, 2), (76, 0.6, 2), (80, 0, 0), (100, 0, 0)])


def taps(sign, start):
    """two taps: lift (ease out), strike (ease in), a tiny rebound"""
    f = [(0, 0)] + ([(start, 0)] if start else [])
    for t0, a in ((start, 11), (start + 11, 8)):
        f += [(t0 + 5, a), (t0 + 8, 0), (t0 + 9.5, -a / 9), (t0 + 11, 0)]
    f.append((100, 0))
    out = []
    for p, a in f:
        tf = DOWN if a > 1 else UP
        out.append((p, f"transform:rotate({n2(sign * a)}deg);animation-timing-function:{tf}"))
    return out


anim("hc-bolt-clawl", 4.4, -0.3, taps(1, 0))
anim("hc-bolt-clawr", 4.4, -0.3, taps(-1, 5.5))

# JUNIPER: a slow 9.1s sweep of the spyglass (head, glass, hands and both arms, each about
# its own joint), brows lifting as she spots something, swaying braids, lens sparkle
rot("hc-jun-pan", 9.1, -1.5, [(0, 0), (22, -4), (29, -3.4), (37, -4.3), (45, -4), (66, 3), (74, 2.6), (84, 3),
                              (100, 0)])
tr("hc-jun-brow", 9.1, -1.5, [(0, 0, 0), (24, 0, 0), (27, 0, -2.6), (36, 0, -2.6), (40, 0, 0), (68, 0, 0),
                              (71, 0, -2.2), (78, 0, -2.2), (81, 0, 0), (100, 0, 0)])
anim("hc-jun-spark", 3.3, -0.4, [(0, "transform:scale(1) rotate(0deg);opacity:1"),
                                 (10, "transform:scale(1.5) rotate(20deg);opacity:1"),
                                 (22, "transform:scale(.4) rotate(45deg);opacity:.35"),
                                 (34, "transform:scale(1) rotate(0deg);opacity:1"),
                                 (100, "transform:scale(1) rotate(0deg);opacity:1")])
sway("hc-jun-braidn", 4.3, -1.1, 3.5)
sway("hc-jun-braidf", 4.9, -2.9, 3)

# NIB: 4.6s float (rise 4.5, sink 3, tilting), paddling arms at twice the rate, hover
# lines that breathe with the height, drifting droplets, blink and glance
_F = "transform:translate(0px,{}px) rotate({}deg);animation-timing-function:{}"
anim("hc-nib-float", 4.6, -1.2, [(0, _F.format(0, 0, SIN_OUT)), (25, _F.format(-5, -2, SIN_IO)),
                                 (75, _F.format(3, 1.5, SIN_IN)), (100, "transform:translate(0px,0px) rotate(0deg)")])
anim("hc-nib-hover", 4.6, -1.2, [(0, f"transform:scale(1,1);animation-timing-function:{SIN_OUT}"),
                                 (25, f"transform:scale(.84,1);animation-timing-function:{SIN_IO}"),
                                 (75, f"transform:scale(1.08,1);animation-timing-function:{SIN_IN}"),
                                 (100, "transform:scale(1,1)")])
sway("hc-nib-arml", 2.3, -0.6, 9, 6)
sway("hc-nib-armr", 2.3, -0.6, -9, -6)
for i, ((x, y, r, a), dur, dl) in enumerate(zip(NIB_DROPS, (3.9, 4.7, 5.3, 6.1), (-0.5, -2.2, -3.9, -1.3))):
    ln = math.hypot(x, y + 5)
    dx, dy = x / ln * 13 * 1.08, (y + 5) / ln * 13 * 1.08 + 4  # outward from Nib, and a little fall
    anim(f"hc-nib-d{i + 1}", dur, dl, [
        (0, "transform:translate(0px,0px) scale(1);opacity:1"),
        (40, f"transform:translate({n2(dx)}px,{n2(dy)}px) scale(.4);opacity:0"),
        (40.1, f"transform:translate({n2(-dx * .35)}px,{n2(-dy * .35)}px) scale(.4);opacity:0"),
        (62, "transform:translate(0px,0px) scale(1);opacity:1"),
        (100, "transform:translate(0px,0px) scale(1);opacity:1")])
blink("hc-nib-blink", 5.0, -3.3, 70)
tr("hc-nib-glance", 6.7, -1.8, [(0, 0, 0), (10, -2.6, -1.2), (35, -2.6, -1.2), (42, 2.4, 0.6), (64, 2.4, 0.6),
                                (71, 0, 0), (100, 0, 0)])

# CAPTAIN RIBBIT: the fish's wiggle (5.1s) jiggles the bobber, shakes the marks and sheds
# a drip; the rod tip twitches twice in 7.3s and the whole rig follows it; slow droopy blink
_TIP = [(0, 0), (58, 0), (60, 8), (63, -3.2), (66, 1.4), (69, 0), (76, 0), (78, 4.5), (81, -1.5), (84, 0), (100, 0)]
rot("hc-rib-tip", 7.3, -2.0, _TIP)
_v = (RIB_TIP[0] - RIB_FLEX[0], RIB_TIP[1] - RIB_FLEX[1])


def _tipmove(a):
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    return _v[0] * ca - _v[1] * sa - _v[0], _v[0] * sa + _v[1] * ca - _v[1]


tr("hc-rib-line", 7.3, -2.0, [(p,) + _tipmove(a) for p, a in _TIP])
rot("hc-rib-fish", 5.1, -0.6, [(0, 0), (4, 12), (8, -10), (12, 11), (16, -9), (20, 7), (25, -4), (30, 2), (35, 0),
                               (100, 0)])
tr("hc-rib-bob", 5.1, -0.6, [(0, 0, 0), (4, 0, 2.4), (8, 0, -1.2), (12, 0, 2), (16, 0, -0.8), (21, 0, 1.2),
                             (28, 0, 0), (100, 0, 0)])
anim("hc-rib-marks", 5.1, -0.6, [(p, f"transform:scale({s},1)") for p, s in
                                 ((0, 1), (4, 1.18), (8, .94), (12, 1.15), (16, .96), (22, 1.08), (30, 1), (100, 1))])
anim("hc-rib-drip", 5.1, -0.6, [((0, 6), "transform:translate(0px,0px);opacity:1"),
                                (26, "transform:translate(3px,22px);opacity:0"),
                                (26.1, "transform:translate(0px,-6px);opacity:0"),
                                (40, "transform:translate(0px,0px);opacity:1"),
                                (100, "transform:translate(0px,0px);opacity:1")])
tr("hc-rib-blink", 6.3, -4.4, [(0, 0, 0), (78, 0, 0), (84, 0, 14), (88, 0, 14), (95, 0, 0), (100, 0, 0)])
tr("hc-rib-glance", 8.1, -2.7, [(0, 0, 0), (9, -2.8, 0.6), (34, -2.8, 0.6), (42, 2.4, 1.2), (66, 2.4, 1.2),
                                (74, 0, 0), (100, 0, 0)])

# QUIRK: ear flicks (5.7s and 7.1s), a slow tail swish, a shy little wave, blink and glance
rot("hc-qk-earl", 5.7, -1.3, [(0, 0), (60, 0), (62, -12), (64.5, 4), (67, -7), (70, 1), (72, 0), (100, 0)])
rot("hc-qk-earr", 7.1, -3.6, [(0, 0), (40, 0), (42, 12), (44.5, -3), (47, 7), (50, -1), (52, 0), (100, 0)])
rot("hc-qk-tail", 6.2, -2.1, [(0, 0), (20, 5), (45, -4), (65, 3), (80, -1), (90, 0), (100, 0)])
rot("hc-qk-paw", 5.2, -0.9, [(0, 0), (6, -14), (12, 5), (18, -14), (24, 5), (30, -8), (36, 0), (100, 0)])
blink("hc-qk-blink", 3.9, -2.2, 76)
tr("hc-qk-glance", 5.9, -4.0, [(0, 0, 0), (8, -2, 0.4), (30, -2, 0.4), (36, 1.8, -0.6), (58, 1.8, -0.6),
                               (64, 0, 0), (100, 0, 0)])


def css():
    rules, kfs = [], []
    for cls in USED:
        dur, delay, ease, frames = ANIM[cls]
        rules.append(f".{cls}{{transform-origin:0 0;animation:{cls} {n2(dur)}s {ease} {n2(delay)}s infinite}}")
        body = ""
        for p, decl in frames:
            ps = ",".join(f"{n2(x)}%" for x in (p if isinstance(p, tuple) else (p,)))
            body += f"{ps}{{{decl}}}"
        kfs.append(f"@keyframes {cls}{{{body}}}")
    missing = set(ANIM) - set(USED)
    assert not missing, f"keyframes defined but unused: {missing}"
    stop = ",".join(f".{c}" for c in USED)
    return ("\n".join(rules) + "\n" + "\n".join(kfs) + "\n"
            + f"@media (prefers-reduced-motion: reduce){{{stop}{{animation:none!important}}}}")


# ---------------------------------------------------------------------------
PATTERNS = """<pattern id="dots-light" width="7" height="7" patternUnits="userSpaceOnUse"><rect width="7" height="7" fill="#fff"/><circle cx="3.5" cy="3.5" r="1.05" fill="#111"/></pattern>
<pattern id="dots-mid" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><circle cx="3" cy="3" r="1.55" fill="#111"/></pattern>
<pattern id="dots-dark" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="#fff"/><circle cx="2.5" cy="2.5" r="1.95" fill="#111"/></pattern>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><line x1="0" y1="0" x2="0" y2="6" stroke="#111" stroke-width="1.4"/></pattern>
<pattern id="crosshatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#fff"/><path d="M0 0V7M0 0H7" stroke="#111" stroke-width="1.3"/></pattern>"""
DEFS = """<defs>
<filter id="ink" x="-3%" y="-3%" width="106%" height="106%">
<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="halo" x="-12%" y="-12%" width="124%" height="124%">
<feMorphology in="SourceAlpha" operator="dilate" radius="4.5" result="d"/>
<feFlood flood-color="#fff" result="w"/>
<feComposite in="w" in2="d" operator="in" result="wd"/>
<feMerge><feMergeNode in="wd"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
""" + PATTERNS + """
</defs>"""
# the motion layer's ink: the same noise, but sized per small part ("inkw" for the long
# thin fishing line, whose box is almost no width at all)
TURB = """<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" yChannelSelector="G"/>"""
MDEFS = (f'<defs>\n<filter id="ink" x="-25%" y="-25%" width="150%" height="150%">\n{TURB}\n</filter>\n'
         f'<filter id="inkw" x="-400%" y="-10%" width="900%" height="120%">\n{TURB}\n</filter>\n{PATTERNS}\n</defs>')
TITLE = ('<title>The Storyfolk cast clambering over the STORY FOLK letters: Moss the forest giant, Pip with his '
         'lantern, Bolt the robot, Juniper with her spyglass, Nib the ink sprite, Captain Ribbit fishing, and '
         'Quirk the question-mark-tailed critter</title>')
ROOT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900"'


def main():
    # (name, content, transform, wrap the group in the white halo)
    groups = [
        ("moss", moss(), "translate(268 880)", True),
        ("pip", pip(), "translate(530 153) scale(0.86)", True),
        ("bolt", bolt(), f"translate({BOLT_X} {BOLT_Y})", False),  # bolt() applies its own halo inside its clip
        ("juniper", juniper(), "translate(1312 151)", True),
        ("nib", nib(), "translate(1046 478) scale(1.08)", True),
        ("captain-ribbit", ribbit(), f"translate(1092 {L_FOOT_TOP})", True),
        ("quirk", quirk(), "translate(1500 880)", True),
    ]
    still, base, motion = [], [], []
    for name, items, tr_, halo in groups:
        for out, content in ((still, r_still(items)), (base, r_base(items))):
            inner = f'<g filter="url(#halo)">{content}</g>' if halo else content
            out.append(f'<!-- {name} --><g id="{name}" transform="{tr_}">{inner}</g>')
        ctx = Ctx([tr_], tmat(tr_))
        backing = m_render(items, ctx, "back", False, False)
        art = m_render(items, ctx, "art", False, False)
        motion.append(f"<!-- {name} -->{backing}{art}")
    files = [
        (OUT, ROOT + ' role="img">' + TITLE + DEFS
         + '<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">' + "".join(still) + "</g></svg>"),
        (OUT_BASE, ROOT + ' aria-hidden="true">' + DEFS
         + '<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">' + "".join(base) + "</g></svg>"),
        (OUT_MOTION, ROOT + ' aria-hidden="true">' + MDEFS + "<style>\n" + css() + "\n</style>"
         + '<g stroke-linecap="round" stroke-linejoin="round">' + "\n".join(motion) + "</g></svg>"),
    ]
    for path, svg in files:
        with open(path, "w") as fh:
            fh.write(svg)
        print(f"wrote {path} ({len(svg) / 1024:.0f} KB)")


main()
