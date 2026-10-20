"""Generator for assets/hero-letters.svg.

Requires Python 3 and shapely (pip install shapely). Run: python3 tools/generate-hero-letters.py

Each capital is designed by hand as a base outline in a local 240x320 box
(polygons, superellipses and a buffered S centre-line), then tilted, fitted
to its letter box, given a hand-cut wobble, and decorated with ink textures.
"""
import math
import os
import random
import sys

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

OUT = (
	sys.argv[1]
	if len(sys.argv) > 1
	else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "hero-letters.svg")
)
LIGHT = (-0.7071, -0.7071)  # light comes from the upper left


def f(v):
	s = f"{v:.1f}"
	if s.endswith(".0"):
		s = s[:-2]
	return "0" if s == "-0" else s


# ------------------------------------------------------------------ geometry
def superellipse(cx, cy, a, b, n, steps=160, rot=0.0):
	pts = []
	cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
	for i in range(steps):
		t = 2 * math.pi * i / steps
		c, s = math.cos(t), math.sin(t)
		x = a * math.copysign(abs(c) ** (2 / n), c)
		y = b * math.copysign(abs(s) ** (2 / n), s)
		pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
	return Polygon(pts)


def jitter_poly(pts, rng, amt=2.4):
	return Polygon([(x + rng.uniform(-amt, amt), y + rng.uniform(-amt, amt)) for x, y in pts])


def round_corners(poly, convex=7.0, concave=4.0):
	p = poly.buffer(-convex, join_style="round", quad_segs=8).buffer(convex, join_style="round", quad_segs=8)
	p = p.buffer(concave, join_style="round", quad_segs=8).buffer(-concave, join_style="round", quad_segs=8)
	return largest(p)


def largest(g):
	if isinstance(g, MultiPolygon):
		return max(g.geoms, key=lambda q: q.area)
	return g


def resample(coords, spacing):
	"""Uniformly resample a closed ring (coords without the repeated end)."""
	pts = list(coords)
	if pts[0] == pts[-1]:
		pts = pts[:-1]
	n = len(pts)
	seg = []
	total = 0.0
	for i in range(n):
		a, b = pts[i], pts[(i + 1) % n]
		d = math.dist(a, b)
		seg.append(d)
		total += d
	count = max(8, int(round(total / spacing)))
	step = total / count
	out = []
	i, acc = 0, 0.0
	for k in range(count):
		target = k * step
		while acc + seg[i] < target and i < n - 1:
			acc += seg[i]
			i += 1
		a, b = pts[i], pts[(i + 1) % n]
		t = 0 if seg[i] == 0 else (target - acc) / seg[i]
		out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
	return out, total


def resample_open(pts, spacing):
	seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
	total = sum(seg)
	if total == 0:
		return list(pts)
	count = max(2, int(round(total / spacing)))
	out = []
	i, acc = 0, 0.0
	for k in range(count + 1):
		target = total * k / count
		while i < len(seg) - 1 and acc + seg[i] < target:
			acc += seg[i]
			i += 1
		a, b = pts[i], pts[i + 1]
		t = 0 if seg[i] == 0 else min(1, (target - acc) / seg[i])
		out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
	return out


def ring_normals(pts, poly, closed=True):
	"""Unit normals pointing out of the polygon material."""
	n = len(pts)
	raw = []
	for i in range(n):
		if closed:
			a, b = pts[i - 1], pts[(i + 1) % n]
		else:
			a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
		dx, dy = b[0] - a[0], b[1] - a[1]
		L = math.hypot(dx, dy) or 1
		raw.append((dy / L, -dx / L))
	votes = 0
	for i in range(0, n, max(1, n // 24)):
		p, q = pts[i], raw[i]
		if poly.contains(Point(p[0] + q[0] * 2.5, p[1] + q[1] * 2.5)):
			votes -= 1
		else:
			votes += 1
	sgn = 1 if votes >= 0 else -1
	return [(x * sgn, y * sgn) for x, y in raw]


def wobble_ring(coords, rng, spacing=9.0, amp=1.7):
	pts, total = resample(coords, spacing)
	ph = [rng.uniform(0, 2 * math.pi) for _ in range(3)]
	lam = [rng.uniform(150, 230), rng.uniform(45, 70), rng.uniform(22, 30)]
	n = len(pts)
	out = []
	for i, (x, y) in enumerate(pts):
		a, b = pts[i - 1], pts[(i + 1) % n]
		dx, dy = b[0] - a[0], b[1] - a[1]
		L = math.hypot(dx, dy) or 1
		nx, ny = dy / L, -dx / L
		s = total * i / n
		d = (
			amp * math.sin(2 * math.pi * s / lam[0] + ph[0])
			+ amp * 0.5 * math.sin(2 * math.pi * s / lam[1] + ph[1])
			+ amp * 0.22 * math.sin(2 * math.pi * s / lam[2] + ph[2])
			+ rng.uniform(-0.25, 0.25)
		)
		out.append((x + nx * d, y + ny * d))
	return out


def catmull_closed(pts):
	n = len(pts)
	d = [f"M{f(pts[0][0])} {f(pts[0][1])}"]
	for i in range(n):
		p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
		c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
		c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
		d.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}")
	return "".join(d) + "Z"


def catmull_open(pts):
	n = len(pts)
	d = [f"M{f(pts[0][0])} {f(pts[0][1])}"]
	for i in range(n - 1):
		p0 = pts[max(0, i - 1)]
		p1, p2 = pts[i], pts[i + 1]
		p3 = pts[min(n - 1, i + 2)]
		c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
		c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
		d.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}")
	return "".join(d)


def poly_path(pts):
	q = [(round(x, 1), round(y, 1)) for x, y in pts]
	out = [f"M{f(q[0][0])} {f(q[0][1])}l"]
	steps = []
	for (x0, y0), (x1, y1) in zip(q, q[1:]):
		dx, dy = round(x1 - x0, 1), round(y1 - y0, 1)
		if dx == 0 and dy == 0:
			continue
		sy = f(dy)
		steps.append(f(dx) + ("" if sy.startswith("-") else " ") + sy)
	sd = ""
	for st in steps:
		sd += st if (st.startswith("-") or not sd) else " " + st
	return out[0] + sd + "z"


def tapered(pts, w, rng=None, start_taper=0.35, end_taper=0.35, min_w=0.25, rough=0.0):
	"""A brush stroke along an open polyline, as a filled outline."""
	pts = resample_open(pts, 3.0)
	n = len(pts)
	if n < 3:
		return ""
	grain = [1.0] * n
	if rough and rng:
		raw = [1 - rough * rng.random() for _ in range(n)]
		grain = [(raw[max(0, i - 1)] + raw[i] + raw[min(n - 1, i + 1)]) / 3 for i in range(n)]
	left, right = [], []
	for i in range(n):
		a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
		dx, dy = b[0] - a[0], b[1] - a[1]
		L = math.hypot(dx, dy) or 1
		nx, ny = -dy / L, dx / L
		t = i / (n - 1)
		k = 1.0
		if t < start_taper:
			k = (t / start_taper) ** 0.7
		if t > 1 - end_taper:
			k = min(k, ((1 - t) / end_taper) ** 0.7)
		hw = max(min_w, w * k * grain[i]) / 2
		x, y = pts[i]
		left.append((x + nx * hw, y + ny * hw))
		right.append((x - nx * hw, y - ny * hw))
	return poly_path(left + right[::-1])


def ring_runs(pts, normals, cond):
	"""Split a closed ring into maximal runs of consecutive points meeting cond."""
	n = len(pts)
	flags = [cond(pts[i], normals[i]) for i in range(n)]
	if all(flags):
		return [pts + [pts[0]]]
	start = flags.index(False)
	runs, cur = [], []
	for k in range(1, n + 1):
		i = (start + k) % n
		if flags[i]:
			cur.append(pts[i])
		elif cur:
			runs.append(cur)
			cur = []
	if cur:
		runs.append(cur)
	return runs


def run_len(run):
	return sum(math.dist(run[i], run[i + 1]) for i in range(len(run) - 1))


def split_run(run, rng, seg_range=(40, 140), gap_range=(5, 12)):
	"""Break a polyline into dashes with irregular gaps, like a re-inked line."""
	pts = resample_open(run, 2.0)
	out, i = [], 0
	while i < len(pts) - 2:
		ln = int(rng.uniform(*seg_range) / 2)
		piece = pts[i : i + ln]
		if len(piece) > 4:
			out.append(piece)
		i += ln + int(rng.uniform(*gap_range) / 2)
	return out


def rings(poly):
	yield poly.exterior
	yield from poly.interiors


# ------------------------------------------------------------------ letters
def base_S(rng):
	pts = []
	for k in range(0, 256, 3):  # top bowl: from the upper terminal over the top and down the left
		t = math.radians(-14 - k)
		pts.append((122 + 79 * math.cos(t), 97 + 58 * math.sin(t)))
	for k in range(0, 259, 3):  # spine across and the lower bowl round to the lower terminal
		t = math.radians(-90 + k)
		pts.append((119 + 84 * math.cos(t), 218 + 63 * math.sin(t)))
	shape = LineString(pts).buffer(39, cap_style="flat", join_style="round", quad_segs=10)
	return round_corners(largest(shape), 10, 3)


def base_T(rng):
	p = jitter_poly([(0, 6), (120, 1), (242, 0), (238, 82), (163, 84), (166, 320), (76, 320), (79, 86), (3, 86)], rng)
	return round_corners(p, 7, 4)


def base_O1(rng):
	outer = superellipse(120, 160, 121, 160, 2.7)
	hole = superellipse(121, 161, 39, 80, 2.3)
	return round_corners(outer.difference(hole), 4, 3)


def base_O2(rng):
	outer = superellipse(120, 160, 120, 160, 2.35, rot=1.5)
	hole = superellipse(118, 158, 38, 84, 2.1, rot=4)
	return round_corners(outer.difference(hole), 4, 3)


def base_R(rng):
	stem = jitter_poly([(0, 0), (84, 0), (84, 320), (0, 320)], rng, 1.5)
	bowl = unary_union([box(0, 0, 150, 186), superellipse(150, 93, 90, 93, 2.4)])
	counter = unary_union([box(84, 72, 146, 114), Point(146, 93).buffer(21)])
	leg = jitter_poly([(92, 172), (178, 172), (244, 320), (154, 320)], rng, 1.5)
	return round_corners(unary_union([stem, bowl, leg]).difference(counter), 7, 4)


def base_Y(rng):
	p = jitter_poly([(0, 0), (86, 0), (121, 92), (157, 0), (242, 0), (164, 188), (166, 320), (77, 320), (79, 188)], rng)
	return round_corners(p, 7, 4)


def base_F(rng):
	p = jitter_poly(
		[(0, 0), (240, 2), (237, 82), (85, 84), (85, 136), (198, 134), (201, 208), (85, 210), (87, 320), (0, 320)], rng
	)
	return round_corners(p, 7, 4)


def base_L(rng):
	p = jitter_poly([(0, 0), (68, 0), (68, 236), (238, 236), (242, 320), (0, 320)], rng, 1.0)
	return round_corners(p, 7, 4)


def base_K(rng):
	p = jitter_poly(
		[(0, 0), (82, 0), (82, 112), (158, 0), (246, 0), (142, 154), (246, 320), (156, 320), (82, 206), (82, 320), (0, 320)],
		rng,
	)
	return round_corners(p, 7, 4)


# name, base builder, tilt (deg), target box (x0, y0, x1, y1), seed
LETTERS = [
	("S", base_S, -2.6, (150, 151, 390, 466), 11),
	("T", base_T, 2.1, (410, 156, 650, 468), 12),
	("O1", base_O1, -1.4, (670, 150, 910, 466), 13),
	("R", base_R, 2.6, (930, 155, 1170, 470), 14),
	("Y", base_Y, -2.0, (1190, 151, 1430, 464), 15),
	("F", base_F, 1.9, (430, 493, 670, 810), 16),
	("O2", base_O2, -2.4, (690, 490, 930, 805), 17),
	("L", base_L, -0.6, (950, 496, 1190, 810), 18),
	("K", base_K, 2.4, (1210, 491, 1436, 808), 19),
]

LETTER_POLYS = []
FREE_ZONES = [box(0, 0, 1600, 147), box(100, 480, 420, 900), box(1450, 0, 1600, 900), box(1030, 490, 1190, 720)]


def place(poly, tilt, tb):
	p = affinity.rotate(poly, tilt, origin=(120, 160))
	minx, miny, maxx, maxy = p.bounds
	x0, y0, x1, y1 = tb
	p = affinity.translate(p, -minx, -miny)
	p = affinity.scale(p, (x1 - x0) / (maxx - minx), (y1 - y0) / (maxy - miny), origin=(0, 0))
	return affinity.translate(p, x0, y0), (minx, miny, maxx, maxy)


def place_aux(geom, tilt, tb, bounds):
	minx, miny, maxx, maxy = bounds
	x0, y0, x1, y1 = tb
	g = affinity.rotate(geom, tilt, origin=(120, 160))
	g = affinity.translate(g, -minx, -miny)
	g = affinity.scale(g, (x1 - x0) / (maxx - minx), (y1 - y0) / (maxy - miny), origin=(0, 0))
	return affinity.translate(g, x0, y0)


def place_pt(pt, tilt, tb, bounds):
	g = place_aux(Point(pt), tilt, tb, bounds)
	return (g.x, g.y)


def letter_svg(name, builder, tilt, tb, seed):
	rng = random.Random(seed)
	base = orient(builder(rng))
	placed, bounds = place(base, tilt, tb)

	# hand-cut wobble on every ring
	ext = wobble_ring(placed.exterior.coords, rng)
	holes = [wobble_ring(r.coords, rng, amp=1.3) for r in placed.interiors]
	P = Polygon(ext, holes).buffer(0)
	P = orient(largest(P))
	LETTER_POLYS.append(P)
	d_main = catmull_closed(ext) + "".join(catmull_closed(h) for h in holes)

	for z in FREE_ZONES:
		a = P.intersection(z).area
		if a > 1:
			print(f"WARN {name} intrudes free zone {z.bounds}: {a:.0f}px2", file=sys.stderr)

	# letterpress shadow: the letter extruded down-right by 11px
	sh = unary_union([affinity.translate(P, k, k) for k in (1.5, 3, 4.5, 6, 7.5, 9, 10.5, 12)])
	sh = orient(largest(sh.buffer(0.3).buffer(-0.3)))
	sh_d = "".join(catmull_closed(resample(r.coords, 9)[0]) for r in rings(sh))

	g = [f'\n<!-- letter {name} -->\n<g id="L-{name}">']
	g.append(f'<path d="{sh_d}" fill="url(#hatch)" stroke="#111" stroke-width="3.2"/>')
	g.append(f'<use href="#p-{name}" fill="#111"/>')
	g.append(f'<g clip-path="url(#c-{name})">')

	# halftone band along the bottom: three steps from ink to dots-mid
	band_base_y = 320
	def band(top, wav):
		xs = [x for x in range(-30, 280, 10)]
		ph = rng.uniform(0, 6.3)
		edge = [(x, top + wav * math.sin(x / 23 + ph) + rng.uniform(-0.8, 0.8)) for x in xs]
		return Polygon(edge + [(280, 360), (-30, 360)])
	ramp = [(246, 1.6, "url(#wdots-1)"), (257, 1.9, "url(#wdots-2)"), (267, 2.1, "url(#wdots-3)"), (277, 2.3, "url(#bdots-4)"), (288, 2.6, "url(#dots-mid)")]
	for top, wav, fill in ramp:
		geom = place_aux(band(top, wav), tilt, tb, bounds).intersection(P).buffer(0)
		polys = geom.geoms if hasattr(geom, "geoms") else [geom]
		dd = ""
		for q in polys:
			if q.area < 4 or not isinstance(q, Polygon):
				continue
			for r in rings(q):
				dd += poly_path(resample(r.coords, 6)[0])
		if dd:
			g.append(f'<path d="{dd}" fill="{fill}" fill-rule="evenodd"/>')
	band_top_poly = place_aux(band(244, 0), tilt, tb, bounds)  # streaks stay above this
	hl_stop_poly = place_aux(band(262, 0), tilt, tb, bounds)  # the lit inner line may run a bit into the ramp

	marks = []  # white brush marks (filled outlines)

	# inner outline ~10px in, only on the lit (upper-left) faces
	inset = P.buffer(-10, join_style="round", quad_segs=6)
	inset_polys = inset.geoms if hasattr(inset, "geoms") else [inset]
	for ip in inset_polys:
		for ri, r in enumerate(rings(ip)):
			pts, _ = resample(r.coords, 3)
			nrm = ring_normals(pts, ip)
			thr = 0.18 if ri == 0 else 0.35
			runs = ring_runs(pts, nrm, lambda p, n: n[0] * LIGHT[0] + n[1] * LIGHT[1] > thr and not hl_stop_poly.contains(Point(p)))
			for run in runs:
				if run_len(run) < 18:
					continue
				for piece in split_run(run, rng, (50, 170), (6, 13)):
					w = rng.uniform(2.8, 3.8) if ri == 0 else rng.uniform(2.0, 2.6)
					marks.append(tapered(piece, w, start_taper=0.12, end_taper=0.18))

	# dry-brush streaks running with the stroke, 2-4 broken hairlines per streak;
	# only on straight-ish runs so a streak never wraps a corner
	def turning(frag):
		tot, worst = 0.0, 0.0
		for k in range(3, len(frag) - 3, 3):
			a = math.atan2(frag[k][1] - frag[k - 3][1], frag[k][0] - frag[k - 3][0])
			b = math.atan2(frag[k + 3][1] - frag[k][1], frag[k + 3][0] - frag[k][0])
			d = abs((b - a + math.pi) % (2 * math.pi) - math.pi)
			tot += d
			worst = max(worst, d)
		return math.degrees(tot), math.degrees(worst)

	want, tries = rng.randint(5, 7), 0
	while want > 0 and tries < 80:
		tries += 1
		dbase = rng.uniform(17, 30)
		rp = largest(P.buffer(-dbase, join_style="round", quad_segs=6))
		if rp.is_empty:
			continue
		rr = list(rings(rp))
		r = rng.choice(rr) if rng.random() < 0.15 else rr[0]
		pts, total = resample(r.coords, 3)
		ln = int(rng.uniform(50, 125) / 3)
		start = rng.randrange(len(pts))
		frag = [pts[(start + k) % len(pts)] for k in range(ln)]
		if any(band_top_poly.contains(Point(p)) for p in frag[:: max(1, ln // 6)]):
			continue
		tot, worst = turning(frag)
		if tot > 38 or worst > 11:
			continue
		want -= 1
		nrm = ring_normals(frag, rp, closed=False)
		for h in range(rng.randint(2, 4)):
			off = h * rng.uniform(2.4, 3.4) + rng.uniform(-0.6, 0.6)
			a = rng.randint(0, ln // 4)
			b = ln - rng.randint(0, ln // 3)
			hair = [(frag[k][0] - nrm[k][0] * off, frag[k][1] - nrm[k][1] * off) for k in range(a, b)]
			if len(hair) < 7:
				continue
			for piece in split_run(hair, rng, (18, 60), (3, 10)):
				marks.append(tapered(piece, rng.uniform(1.2, 2.2), rng, 0.25, 0.55, rough=0.55))

	# hatch flicks near the lit edges
	inner = largest(P.buffer(-19, join_style="round"))
	if not inner.is_empty:
		pts, _ = resample(inner.exterior.coords, 4)
		nrm = ring_normals(pts, inner)
		lit = [i for i in range(len(pts)) if nrm[i][0] * LIGHT[0] + nrm[i][1] * LIGHT[1] > 0.55]
		rng.shuffle(lit)
		used = []
		clusters = 0
		for i in lit:
			p = pts[i]
			if any(math.dist(p, u) < 60 for u in used):
				continue
			used.append(p)
			clusters += 1
			tx, ty = -nrm[i][1], nrm[i][0]
			for k in range(rng.randint(3, 4)):
				cx = p[0] + tx * (k - 1.5) * 6.5 - nrm[i][0] * rng.uniform(0, 3)
				cy = p[1] + ty * (k - 1.5) * 6.5 - nrm[i][1] * rng.uniform(0, 3)
				L = rng.uniform(8, 14) * (1 - abs(k - 1.5) * 0.2)
				marks.append(tapered([(cx - 0.707 * L / 2, cy + 0.707 * L / 2), (cx + 0.707 * L / 2, cy - 0.707 * L / 2)], rng.uniform(1.8, 2.5), None, 0.25, 0.6))
			if clusters >= 3:
				break

	# speckles
	sp_area = P.buffer(-7)
	minx, miny, maxx, maxy = P.bounds
	dots = []
	tries = 0
	while len(dots) < 16 and tries < 600:
		tries += 1
		x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy - 80)
		if sp_area.contains(Point(x, y)):
			dots.append((x, y, rng.uniform(0.7, 1.7)))

	# per-letter extras
	extra = []
	if name == "O1":
		# shine: a curved white bar and a dot on the upper-left of the ring
		c = place_pt((120, 160), tilt, tb, bounds)
		arc = [(c[0] + 98 * math.cos(math.radians(a)), c[1] + 132 * math.sin(math.radians(a))) for a in range(197, 246, 3)]
		arc = [(x + 6, y + 8) for x, y in arc]
		marks.append(tapered(arc, 7.5, None, 0.3, 0.45))
		dx, dy = c[0] + 95 * math.cos(math.radians(257)) + 8, c[1] + 128 * math.sin(math.radians(257)) + 10
		extra.append(f'<ellipse cx="{f(dx)}" cy="{f(dy)}" rx="4.6" ry="4" fill="#fff"/>')
	if name == "O2":
		# knot-hole: a little white spiral with wood-grain rings around it
		kx, ky = place_pt((50, 118), tilt, tb, bounds)
		sp = []
		for k in range(0, 560, 12):
			t = math.radians(k)
			r = 1.2 + k / 360 * 4.6
			sp.append((kx + r * math.cos(t) * 1.15, ky + r * math.sin(t)))
		marks.append(tapered(sp, 2.6, None, 0.15, 0.25))
		for rad, a0, a1 in ((12, -70, 210), (19, -30, 160)):
			arc = [(kx + rad * 1.1 * math.cos(math.radians(a)), ky + rad * math.sin(math.radians(a)) * 1.5) for a in range(a0, a1, 6)]
			marks.append(tapered(arc, 1.8, None, 0.3, 0.3))
		for off, span in ((-15, 70), (17, 62), (25, 48)):
			grain = []
			for j in range(-span, span + 1, 4):
				bow = math.copysign(11 * math.exp(-((j / 26) ** 2)), off)
				grain.append((kx + off + bow + 1.2 * math.sin(j / 9), ky + j))
			marks.append(tapered(grain, 1.5, None, 0.35, 0.35))

	marks = [m for m in marks if m]
	g.append(f'<path d="{"".join(marks)}" fill="#fff"/>')
	g.append("<g fill=\"#fff\">" + "".join(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}"/>' for x, y, r in dots) + "</g>")
	g.extend(extra)
	g.append("</g>")
	g.append(f'<use href="#p-{name}" fill="none" stroke="#111" stroke-width="4.6"/>')
	g.append("</g>")

	defs = f'<path id="p-{name}" d="{d_main}" fill-rule="evenodd" clip-rule="evenodd"/>'
	clip = f'<clipPath id="c-{name}"><use href="#p-{name}"/></clipPath>'
	return defs, clip, "\n".join(g)


# ------------------------------------------------------------------ ground
def ground_svg():
	rng = random.Random(99)
	out = ["\n<!-- ground line with grass tufts, sprouts and pebbles -->", '<g id="ground">']

	def gy(x):
		return 880 + 1.8 * math.sin(x / 97) + 1.1 * math.sin(x / 31 + 1.3)

	ink = []
	# the line itself, inked in three overlapping strokes
	for x0, x1, w in ((80, 646, 6.0), (606, 1196, 6.4), (1160, 1560, 5.8)):
		pts = [(x, gy(x) + rng.uniform(-0.3, 0.3)) for x in range(x0, x1 + 1, 8)]
		ink.append(tapered(pts, w, None, 0.07, 0.09, 0.8))
	# short second strokes just under the line, as if re-inked
	for x0 in (120, 300, 470, 700, 905, 1080, 1250, 1430):
		x0 += rng.uniform(-20, 20)
		L = rng.uniform(34, 80)
		pts = [(x, gy(x) + 5.5 + rng.uniform(-0.4, 0.4)) for x in range(int(x0), int(x0 + L), 6)]
		ink.append(tapered(pts, 2.1, None, 0.3, 0.4))
	# dirt texture under the line
	x = 96
	while x < 1540:
		for k in range(rng.randint(2, 4)):
			xx = x + k * 6 + rng.uniform(-1, 1)
			y0 = gy(xx) + rng.uniform(8, 11)
			L = rng.uniform(6, 11)
			ink.append(tapered([(xx, y0), (xx - L * 0.55, y0 + L * 0.35)], 1.6, None, 0.2, 0.5))
		x += rng.uniform(50, 95)
	# grass tufts: curved blades fanning out of the line
	tuft_x = [96, 160, 236, 300, 372, 448, 520, 588, 664, 730, 806, 880, 960, 1030, 1104, 1176, 1250, 1322, 1396, 1466, 1540]
	for tx in tuft_x:
		tx += rng.uniform(-10, 10)
		blades = rng.randint(3, 6)
		big = rng.uniform(0.8, 1.25)
		for bi in range(blades):
			c = bi - (blades - 1) / 2
			bx = tx + c * 4.4
			h = rng.uniform(12, 24) * big * (1 - abs(c) * 0.16)
			lean = c * 4.0 + rng.uniform(-2.5, 2.5)
			by = gy(bx) + 1.5
			pts = [(bx + lean * t * t, by - h * t) for t in [i / 8 for i in range(9)]]
			ink.append(tapered(pts, rng.uniform(2.8, 3.6), None, 0.0, 0.85, 0.3))
	out.append(f'<path d="{"".join(ink)}" fill="#111"/>')

	# little two-leaf sprouts
	for sx in (408, 842, 1210, 1508):
		base = (sx, gy(sx) + 1)
		h = rng.uniform(20, 27)
		top = (sx + rng.uniform(-3, 3), base[1] - h)
		out.append(
			f'<path d="M{f(base[0])} {f(base[1])}Q{f(sx - 3)} {f(base[1] - h * 0.5)} {f(top[0])} {f(top[1])}" fill="none" stroke="#111" stroke-width="2.6"/>'
		)
		for side in (-1, 1):
			lx, ly = top[0], top[1] + 2
			tipx, tipy = lx + side * 15, ly - 6
			out.append(
				f'<path d="M{f(lx)} {f(ly)}Q{f(lx + side * 5)} {f(ly - 10)} {f(tipx)} {f(tipy)}Q{f(lx + side * 9)} {f(ly + 3)} {f(lx)} {f(ly)}Z" '
				f'fill="{"url(#dots-light)" if side > 0 else "#fff"}" stroke="#111" stroke-width="2.2"/>'
			)
			out.append(
				f'<path d="M{f(lx + side * 2)} {f(ly - 1)}Q{f(lx + side * 8)} {f(ly - 4)} {f(tipx - side * 3)} {f(tipy + 1)}" fill="none" stroke="#111" stroke-width="1.2"/>'
			)

	# pebbles sitting in the line, some with a small companion
	pebbles = [138, 228, 330, 498, 618, 772, 918, 1006, 1094, 1282, 1362, 1450, 1526]
	for i, px in enumerate(pebbles):
		for j in range(2 if i % 4 == 1 else 1):
			qx = px + rng.uniform(-8, 8) + j * 17
			rx, ry = (rng.uniform(7, 13), rng.uniform(4.5, 7.5)) if j == 0 else (rng.uniform(4, 6), rng.uniform(3, 4))
			cy = gy(qx) + rng.uniform(-0.5, 2) + j * 1.5
			pts = []
			for k in range(14):
				t = 2 * math.pi * k / 14
				rr = 1 + rng.uniform(-0.12, 0.08)
				pts.append((qx + rx * rr * math.cos(t), cy + ry * rr * math.sin(t) - (1.5 if math.sin(t) < 0 else 0)))
			fill = "url(#dots-light)" if (i + j) % 3 == 1 else "#fff"
			out.append(f'<path d="{catmull_closed(pts)}" fill="{fill}" stroke="#111" stroke-width="2.6"/>')
			if j == 0:
				out.append(
					f'<path d="M{f(qx - rx * 0.5)} {f(cy - ry * 0.15)}q{f(rx * 0.2)} {f(-ry * 0.45)} {f(rx * 0.55)} {f(-ry * 0.5)}" fill="none" stroke="#111" stroke-width="1.4"/>'
				)
	# a few loose grit dots
	gd = []
	for _ in range(30):
		xx = rng.uniform(90, 1550)
		gd.append(f'<circle cx="{f(xx)}" cy="{f(gy(xx) + rng.uniform(7, 15))}" r="{f(rng.uniform(0.9, 1.7))}"/>')
	out.append('<g fill="#111">' + "".join(gd) + "</g>")
	out.append("</g>")
	return "\n".join(out)



# ------------------------------------------------------------------ spatter
def spatter_svg():
	"""A few stray ink droplets beside the letters, as if flicked off the brush."""
	rng = random.Random(5)
	ink = unary_union([Polygon(q.exterior) for q in LETTER_POLYS]).buffer(16)  # counters count as letter, so no specks in holes
	near = unary_union(LETTER_POLYS).buffer(40)
	keep_out = unary_union(FREE_ZONES + [box(0, 0, 1600, 150), box(0, 840, 1600, 900)])
	out = ["\n<!-- stray ink spatter -->", '<g fill="#111">']
	placed, tries = [], 0
	while len(placed) < 11 and tries < 4000:
		tries += 1
		x, y = rng.uniform(130, 1450), rng.uniform(150, 840)
		p = Point(x, y)
		if not near.contains(p) or ink.contains(p) or keep_out.intersects(p.buffer(14)):
			continue
		if any(math.dist((x, y), q) < 120 for q in placed):
			continue
		placed.append((x, y))
		r = rng.uniform(2.2, 3.8)
		blob = [(x + r * (1 + rng.uniform(-0.18, 0.18)) * math.cos(2 * math.pi * k / 9), y + r * (1 + rng.uniform(-0.18, 0.18)) * math.sin(2 * math.pi * k / 9)) for k in range(9)]
		out.append(f'<path d="{catmull_closed(blob)}"/>')
		ang = rng.uniform(0, 2 * math.pi)
		for k in range(rng.randint(1, 3)):
			d = r + rng.uniform(3, 9)
			a = ang + rng.uniform(-0.6, 0.6)
			out.append(f'<circle cx="{f(x + d * math.cos(a))}" cy="{f(y + d * math.sin(a))}" r="{f(rng.uniform(0.7, 1.5))}"/>')
	out.append("</g>")
	return "\n".join(out)


# ------------------------------------------------------------------ assemble
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
  <!-- halftone ramp on ink, same lattice as dots-mid: white dots grow, then black dots shrink -->
  <pattern id="wdots-1" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="0" cy="0" r="0.85" fill="#fff"/><circle cx="6" cy="0" r="0.85" fill="#fff"/><circle cx="0" cy="6" r="0.85" fill="#fff"/><circle cx="6" cy="6" r="0.85" fill="#fff"/></pattern>
  <pattern id="wdots-2" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="0" cy="0" r="1.5" fill="#fff"/><circle cx="6" cy="0" r="1.5" fill="#fff"/><circle cx="0" cy="6" r="1.5" fill="#fff"/><circle cx="6" cy="6" r="1.5" fill="#fff"/></pattern>
  <pattern id="wdots-3" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="0" cy="0" r="2.15" fill="#fff"/><circle cx="6" cy="0" r="2.15" fill="#fff"/><circle cx="0" cy="6" r="2.15" fill="#fff"/><circle cx="6" cy="6" r="2.15" fill="#fff"/></pattern>
  <pattern id="bdots-4" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><circle cx="3" cy="3" r="2.05" fill="#111"/></pattern>
"""

parts_defs, parts_clip, parts_body = [], [], []
for spec in LETTERS:
	d, c, b = letter_svg(*spec)
	parts_defs.append(d)
	parts_clip.append(c)
	parts_body.append(b)

svg = (
	'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900" role="img">\n'
	"<title>Storyfolk wordmark: hand-inked block letters spelling STORY over FOLK</title>\n"
	+ DEFS
	+ "\n".join(parts_defs)
	+ "\n"
	+ "\n".join(parts_clip)
	+ "\n</defs>\n"
	+ '<g filter="url(#ink)" stroke-linecap="round" stroke-linejoin="round">'
	+ "\n<!-- top row: STORY -->"
	+ "\n".join(parts_body[:5])
	+ "\n<!-- bottom row: FOLK -->"
	+ "\n".join(parts_body[5:])
	+ spatter_svg()
	+ ground_svg()
	+ "\n</g>\n</svg>\n"
)
with open(OUT, "w") as fh:
	fh.write(svg)
print(f"wrote {OUT} ({len(svg) / 1024:.0f} KB)")
