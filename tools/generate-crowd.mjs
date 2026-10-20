// Storyfolk crowd band: a dense crowd of original kid and creature busts for the black
// "staycurious" band. A seeded PRNG picks every part, so the output is stable from run to run.
// Run from any directory: node tools/generate-crowd.mjs. One run writes three files:
//   assets/crowd.svg         the complete still (motion off, no-JS fallback, reference)
//   assets/crowd-base.svg    the still minus the open eyes, which leaves the face skin bare
//   assets/crowd-motion.svg  only the open eyes, which blink and glance; base + motion at rest
//                            reproduce the still

import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const asset = (name) => fileURLToPath(new URL(`../assets/${name}`, import.meta.url));
const OUT = asset("crowd.svg");
const OUT_BASE = asset("crowd-base.svg");
const OUT_MOTION = asset("crowd-motion.svg");
const SEED = 20261020;

const INK = "#111";
const W = "#fff";
const DL = "url(#dots-light)";
const DT = "url(#dots-tan)";
const DM = "url(#dots-mid)";
const DD = "url(#dots-dark)";
const HA = "url(#hatch)";
const CH = "url(#crosshatch)";
const PO = "url(#polka)";

// Six staggered rows, back (top) to front. The back row's heads make the top silhouette.
const ROWS = [
	{ y: 150, s: 0.8 },
	{ y: 303, s: 0.855 },
	{ y: 456, s: 0.91 },
	{ y: 609, s: 0.965 },
	{ y: 762, s: 1.02 },
	{ y: 915, s: 1.075 },
];
const STEP = 166;

// ------------------------------------------------------------------ seeded randomness

function mulberry32(seed) {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

// `plan` picks the cast; `jit` adds per-figure wobble and is reseeded for every figure, so
// tweaking one drawing routine never reshuffles the whole crowd.
let plan = mulberry32(SEED);
let jit = mulberry32(SEED);
const between = (lo, hi) => lo + (hi - lo) * plan();
const pick = (list) => list[Math.floor(plan() * list.length)];
const chance = (odds) => plan() < odds;
const wob = (lo, hi) => lo + (hi - lo) * jit();

function shuffle(list) {
	const out = [...list];
	for (let i = out.length - 1; i > 0; i--) {
		const j = Math.floor(plan() * (i + 1));
		[out[i], out[j]] = [out[j], out[i]];
	}
	return out;
}

/** A shuffled deck of `count` cards dealt from weighted entries ([value, weight]). */
function deck(entries, count) {
	const cards = [];
	const total = entries.reduce((sum, [, weight]) => sum + weight, 0);
	for (const [value, weight] of entries) {
		const n = Math.round((weight / total) * count);
		for (let i = 0; i < n; i++) cards.push(value);
	}
	while (cards.length < count) cards.push(entries[cards.length % entries.length][0]);
	return shuffle(cards.slice(0, count));
}

// ------------------------------------------------------------------ svg helpers

function f(v) {
	const r = Math.round(v * 10) / 10;
	return Object.is(r, -0) ? "0" : String(r);
}

/** Tagged template for path data: every interpolated number is rounded to one decimal. */
function p(strings, ...values) {
	let out = strings[0];
	values.forEach((v, i) => {
		out += (typeof v === "number" ? f(v) : v) + strings[i + 1];
	});
	return out;
}

function shape(d, fill = W, sw = 4.2) {
	const stroke = sw ? ` stroke="${INK}" stroke-width="${f(sw)}"` : "";
	return `<path d="${d}" fill="${fill}"${stroke}/>`;
}

function ink(d, sw = 2.6, color = INK) {
	return `<path d="${d}" fill="none" stroke="${color}" stroke-width="${f(sw)}"/>`;
}

function dashed(d, sw = 1.4) {
	const stroke = `stroke="${INK}" stroke-width="${f(sw)}" stroke-dasharray="3 3.5"`;
	return `<path d="${d}" fill="none" ${stroke}/>`;
}

function circle(cx, cy, r, fill = W, sw = 0) {
	const stroke = sw ? ` stroke="${INK}" stroke-width="${f(sw)}"` : "";
	return `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(r)}" fill="${fill}"${stroke}/>`;
}

function oval(cx, cy, rx, ry, fill = W, sw = 0, rot = 0) {
	const stroke = sw ? ` stroke="${INK}" stroke-width="${f(sw)}"` : "";
	const turn = rot ? ` transform="rotate(${f(rot)} ${f(cx)} ${f(cy)})"` : "";
	const at = `cx="${f(cx)}" cy="${f(cy)}" rx="${f(rx)}" ry="${f(ry)}"`;
	return `<ellipse ${at} fill="${fill}"${stroke}${turn}/>`;
}

function group(body, transform) {
	return body ? `<g transform="${transform}">${body}</g>` : "";
}

let uid = 0;

/** Filled shape whose inner shading is clipped to it, outlined last (path data written once). */
function clipped(d, fill, sw, inner, evenodd = false) {
	uid += 1;
	const rule = evenodd ? ' fill-rule="evenodd" clip-rule="evenodd"' : "";
	return (
		`<defs><path id="s${uid}" d="${d}"${rule}/></defs>` +
		`<clipPath id="k${uid}"><use href="#s${uid}"/></clipPath>` +
		`<use href="#s${uid}" fill="${fill}"/><g clip-path="url(#k${uid})">${inner}</g>` +
		`<use href="#s${uid}" fill="none" stroke="${INK}" stroke-width="${f(sw)}"/>`
	);
}

/** Tapered ink stroke: a thin crescent from (x0,y0) to (x1,y1) bowed towards (cx,cy). */
function taper(x0, y0, cx, cy, x1, y1, w, fill = INK) {
	const len = Math.hypot(x1 - x0, y1 - y0) || 1;
	const nx = (-(y1 - y0) / len) * w;
	const ny = ((x1 - x0) / len) * w;
	const d = p`M${x0} ${y0}Q${cx + nx} ${cy + ny} ${x1} ${y1}Q${cx - nx} ${cy - ny} ${x0} ${y0}Z`;
	return shape(d, fill, 0);
}

/** Catmull-Rom spline through points; a point with a truthy third entry is a sharp corner. */
function smooth(pts, closed = true) {
	const n = pts.length;
	const at = (i) => (closed ? pts[(i + n) % n] : pts[Math.min(n - 1, Math.max(0, i))]);
	let d = p`M${pts[0][0]} ${pts[0][1]}`;
	for (let i = 0; i < (closed ? n : n - 1); i++) {
		const [a, b, c, e] = [at(i - 1), at(i), at(i + 1), at(i + 2)];
		const c1 = b[2] ? b : [b[0] + (c[0] - a[0]) / 6, b[1] + (c[1] - a[1]) / 6];
		const c2 = c[2] ? c : [c[0] - (e[0] - b[0]) / 6, c[1] - (e[1] - b[1]) / 6];
		d += p`C${c1[0]} ${c1[1]} ${c2[0]} ${c2[1]} ${c[0]} ${c[1]}`;
	}
	return closed ? `${d}Z` : d;
}

/**
 * Scalloped outline: each segment bulges to its left-hand side, which is outwards for a
 * shape traced clockwise on screen. A numeric third entry overrides the bulge of the
 * segment that ends at that point.
 */
function bumps(pts, bulge = 0.4, closed = true) {
	let d = p`M${pts[0][0]} ${pts[0][1]}`;
	for (let i = 0; i < (closed ? pts.length : pts.length - 1); i++) {
		const a = pts[i];
		const b = pts[(i + 1) % pts.length];
		const k = typeof b[2] === "number" ? b[2] : bulge;
		const cx = (a[0] + b[0]) / 2 + (b[1] - a[1]) * k;
		const cy = (a[1] + b[1]) / 2 - (b[0] - a[0]) * k;
		d += p`Q${cx} ${cy} ${b[0]} ${b[1]}`;
	}
	return closed ? `${d}Z` : d;
}

/** Fuzzy round tuft (pom-poms, afro clouds, puffs). */
function puff(cx, cy, r, count, jitter = 0.07) {
	const pts = [];
	for (let i = 0; i < count; i++) {
		const a = (i / count) * Math.PI * 2 + 0.3;
		const rr = r * (1 + wob(-jitter, jitter));
		pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
	}
	return bumps(pts, 0.42);
}

function ellipsePath(cx, cy, rx, ry) {
	return (
		p`M${cx - rx} ${cy}A${rx} ${ry} 0 1 0 ${cx + rx} ${cy}` +
		p`A${rx} ${ry} 0 1 0 ${cx - rx} ${cy}Z`
	);
}

function roundRect(x, y, w, h, r) {
	return (
		p`M${x + r} ${y}L${x + w - r} ${y}` +
		p`Q${x + w} ${y} ${x + w} ${y + r}` +
		p`L${x + w} ${y + h - r}` +
		p`Q${x + w} ${y + h} ${x + w - r} ${y + h}` +
		p`L${x + r} ${y + h}` +
		p`Q${x} ${y + h} ${x} ${y + h - r}` +
		p`L${x} ${y + r}Q${x} ${y} ${x + r} ${y}` +
		p`Z`
	);
}

function starPath(cx, cy, r, inner, points = 5) {
	const pts = [];
	for (let i = 0; i < points * 2; i++) {
		const a = -Math.PI / 2 + (i * Math.PI) / points;
		const rr = i % 2 ? inner : r;
		pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, true]);
	}
	return smooth(pts);
}

function heartPath(cx, cy, s) {
	return (
		p`M${cx} ${cy + s * 0.9}` +
		p`C${cx - s * 1.3} ${cy} ${cx - s * 0.9} ${cy - s} ${cx} ${cy - s * 0.35}` +
		p`C${cx + s * 0.9} ${cy - s} ${cx + s * 1.3} ${cy} ${cx} ${cy + s * 0.9}` +
		p`Z`
	);
}

const darker = (fill) =>
	({ [W]: DM, [DL]: DM, [DT]: DM, [DM]: DD, [HA]: CH, [DD]: CH, [PO]: DM, [CH]: DD })[fill] ?? DM;
const detailOn = (fill) => (fill === INK ? W : INK);

// ------------------------------------------------------------------ head geometry

/** Point on a head outline (superellipse halves) at `deg` (0 = right, 90 = chin). */
function headPoint(h, deg, grow = 0) {
	const a = (deg * Math.PI) / 180;
	const c = Math.cos(a);
	const s = Math.sin(a);
	const lower = s > 0;
	const e = 2 / (lower ? h.nb : h.n);
	const ry = (lower ? h.ryb : h.ry) + grow;
	return [Math.sign(c) * Math.abs(c) ** e * (h.rx + grow), Math.sign(s) * Math.abs(s) ** e * ry];
}

function arc(h, from, to, grow = 0, step = 12) {
	const count = Math.max(2, Math.round(Math.abs(to - from) / step));
	const pts = [];
	for (let i = 0; i <= count; i++) pts.push(headPoint(h, from + ((to - from) * i) / count, grow));
	return pts;
}

const headPath = (h) => smooth(arc(h, 0, 345, 0, 15));
const mirrorPts = (pts, s) => (s > 0 ? pts : pts.map(([x, y, c]) => [-x, y, c]).reverse());

function faceGeo(h, k) {
	const er = k.eye;
	const eh = er * 1.3;
	const ey = h.ryb * 0.24;
	return { ex: h.rx * 0.37, ey, er, eh, my: ey + eh + 12, lx: k.look };
}

// ------------------------------------------------------------------ moving eyes

// While a figure is drawn, `figure` gathers its open eyes. Each one leaves a token in the
// drawing: the still puts the eye back there, the base leaves the face skin under it bare, and
// the motion layer draws the eyes again on their own so they can blink and glance.
let figure = { eyes: [], tilt: 0, cy: 0 };
const OPEN_EYES = new Set(["open", "wide"]);
const EYE_TOKEN = /\u0000(\d+)\u0000/g;

/** An eye centred on (x, y) in head space; open ones move, drawn-closed ones stay put. */
function blinker(kind, markup, x, y) {
	if (!OPEN_EYES.has(kind)) return markup;
	figure.eyes.push({ markup, x, y });
	return `\u0000${figure.eyes.length - 1}\u0000`;
}

/** The head's tilt about its neck point (0, cy), remembered so the eyes can follow it. */
function headTurn(k, cy) {
	figure.tilt = Number(f(k.tilt));
	figure.cy = Number(f(cy));
	return `rotate(${f(k.tilt)} 0 ${f(cy)})`;
}

// ------------------------------------------------------------------ faces

const EXPRESSIONS = {
	smile: { eyes: ["open", "open"], mouth: "smile" },
	grin: { eyes: ["open", "open"], mouth: "grin" },
	laugh: { eyes: ["happy", "happy"], mouth: "open" },
	calm: { eyes: ["calm", "calm"], mouth: "small" },
	surprised: { eyes: ["wide", "wide"], mouth: "o", brow: -5 },
	wink: { eyes: ["open", "happy"], mouth: "smirk" },
	tongue: { eyes: ["open", "open"], mouth: "tongue" },
	cheeky: { eyes: ["open", "open"], mouth: "cat" },
	gappy: { eyes: ["open", "open"], mouth: "gap" },
	beam: { eyes: ["happy", "happy"], mouth: "grin" },
};

function eye(kind, x, y, er, eh, s) {
	if (kind === "happy")
		return taper(x - er - 1.5, y + 3, x, y - eh * 1.25, x + er + 1.5, y + 3, 3.8);
	if (kind === "calm") {
		const lid = taper(x - er - 1, y - 1, x, y + eh * 0.95, x + er + 1, y - 1, 3.6);
		return (
			lid + taper(x + s * (er + 0.5), y - 1, x + s * (er + 3), y - 2, x + s * (er + 5), y - 6, 1.8)
		);
	}
	const k = kind === "wide" ? 1.14 : 1;
	return (
		oval(x, y, er * k, eh * k, INK) +
		circle(x - er * 0.34 * k, y - eh * 0.36 * k, er * 0.44 * k) +
		circle(x + er * 0.38 * k, y + eh * 0.42 * k, er * 0.17 * k)
	);
}

function mouth(kind, x, my) {
	switch (kind) {
		case "grin":
			return (
				shape(
					p`M${x - 12} ${my - 1}Q${x} ${my + 21} ${x + 12} ${my - 1}` +
						p`Q${x} ${my + 2} ${x - 12} ${my - 1}Z`,
					INK,
					0,
				) +
				shape(
					p`M${x - 10} ${my + 0.6}Q${x} ${my + 3} ${x + 10} ${my + 0.6}` +
						p`L${x + 8.6} ${my + 4.6}Q${x} ${my + 7} ${x - 8.6} ${my + 4.6}Z`,
					W,
					0,
				)
			);
		case "open":
			return (
				shape(
					p`M${x - 10} ${my}Q${x} ${my + 20} ${x + 10} ${my}Q${x} ${my + 3} ${x - 10} ${my}Z`,
					INK,
					0,
				) +
				shape(
					p`M${x - 5} ${my + 8}Q${x} ${my + 4.5} ${x + 5} ${my + 8}` +
						p`Q${x} ${my + 11.5} ${x - 5} ${my + 8}Z`,
					W,
					0,
				)
			);
		case "gap":
			return (
				shape(
					p`M${x - 11} ${my - 1}Q${x} ${my + 20} ${x + 11} ${my - 1}` +
						p`Q${x} ${my + 2} ${x - 11} ${my - 1}Z`,
					INK,
					0,
				) +
				shape(
					p`M${x - 7} ${my + 0.4}L${x - 1.5} ${my + 1.2}` +
						p`L${x - 1.8} ${my + 5.5}L${x - 6.4} ${my + 4.6}Z`,
					W,
					0,
				) +
				shape(
					p`M${x + 7} ${my + 0.4}L${x + 1.5} ${my + 1.2}` +
						p`L${x + 1.8} ${my + 5.5}L${x + 6.4} ${my + 4.6}Z`,
					W,
					0,
				)
			);
		case "o":
			return oval(x, my + 5, 4.8, 6.2, INK) + oval(x - 1.4, my + 2.8, 1.5, 1.2, W);
		case "tongue":
			return (
				shape(
					p`M${x - 4.5} ${my + 4}C${x - 6} ${my + 15} ${x + 6} ${my + 15} ${x + 4.5} ${my + 4}Z`,
					W,
					2.4,
				) +
				ink(p`M${x} ${my + 6}L${x} ${my + 10}`, 1.5) +
				ink(p`M${x - 10} ${my}Q${x} ${my + 9} ${x + 10} ${my}`, 2.8)
			);
		case "cat":
			return ink(
				p`M${x - 9} ${my + 1}Q${x - 4.5} ${my + 8} ${x} ${my + 1.5}` +
					p`Q${x + 4.5} ${my + 8} ${x + 9} ${my + 1}`,
				2.6,
			);
		case "small":
			return ink(p`M${x - 5.5} ${my + 2}Q${x} ${my + 6.5} ${x + 5.5} ${my + 2}`, 2.6);
		case "smirk":
			return (
				ink(p`M${x - 8} ${my + 3}Q${x + 1} ${my + 9} ${x + 9} ${my}`, 2.8) +
				ink(p`M${x + 8} ${my - 2}L${x + 10.5} ${my + 1.5}`, 2)
			);
		default:
			return ink(p`M${x - 9} ${my}Q${x} ${my + 10} ${x + 9} ${my}`, 2.8);
	}
}

function bandAid(x, y, rot) {
	return group(
		shape(roundRect(-11, -4.5, 22, 9, 4.5), W, 2) +
			shape(roundRect(-4, -3.5, 8, 7, 1.5), DL, 1.4) +
			circle(-7.5, -1.2, 0.8, INK) +
			circle(-7.5, 1.5, 0.8, INK) +
			circle(7.5, -1.2, 0.8, INK) +
			circle(7.5, 1.5, 0.8, INK),
		`translate(${f(x)} ${f(y)}) rotate(${f(rot)})`,
	);
}

/** Eyes, brows, nose, mouth and cheek marks for a kid-type face. */
function drawFace(h, k, hide = [false, false]) {
	const g = faceGeo(h, k);
	const ex = EXPRESSIONS[k.expr];
	const out = [];
	const tone = k.skin.tone;
	if (tone < 2 && k.cheeks) {
		const blush = tone === 0 ? DL : DM;
		for (const s of [-1, 1]) {
			if (k.bandAid !== s) out.push(oval(s * (g.ex + 11), g.my - 4, 8.5, 5.4, blush));
		}
	}
	if (tone >= 2) {
		out.push(
			ink(
				p`M${-g.ex - 15} ${g.my - 9}Q${-g.ex - 11} ${g.my - 13} ${-g.ex - 5} ${g.my - 12}`,
				2.4,
				W,
			),
		);
	}
	if (k.freckles && tone < 3) {
		for (const s of [-1, 1]) {
			for (const [dx, dy] of [
				[6, -8],
				[11, -10],
				[9, -5],
				[14, -6],
			]) {
				out.push(circle(s * (g.ex + dx) + g.lx * 0.5, g.my + dy, 1.05, INK));
			}
		}
	}
	[-1, 1].forEach((s, i) => {
		const x = s * g.ex + g.lx;
		const kind = ex.eyes[i];
		if (!hide[i]) out.push(blinker(kind, eye(kind, x, g.ey, g.er, g.eh, s), x, g.ey));
		const by = g.ey - g.eh - 8 + (ex.brow ?? 0);
		out.push(taper(x - 7, by + 1.5, x + s * 0.5, by - 2.6, x + 7, by + 1.5, 2.6));
	});
	out.push(
		ink(
			p`M${-3 + g.lx * 0.6} ${g.ey + g.eh + 1}` +
				p`Q${g.lx * 0.6} ${g.ey + g.eh + 4} ${3 + g.lx * 0.6} ${g.ey + g.eh + 1}`,
			2.2,
		),
	);
	out.push(mouth(ex.mouth, g.lx * 0.5, g.my));
	if (k.bandAid) out.push(bandAid(k.bandAid * (g.ex + 12), g.my - 6, k.bandAid * -28));
	return out.join("");
}

// ------------------------------------------------------------------ eyewear

function eyewear(h, k) {
	const g = faceGeo(h, k);
	const out = [];
	if (k.eyewear === "glasses") {
		const r = g.er * 1.85;
		for (const s of [-1, 1]) {
			const x = s * g.ex + g.lx;
			out.push(circle(x, g.ey, r, "none", 3.2));
			out.push(
				ink(
					p`M${x + 4} ${g.ey - r + 5}L${x + 8} ${g.ey - r + 9}` +
						p`M${x + 6.5} ${g.ey - r + 3.5}L${x + 9.5} ${g.ey - r + 6.5}`,
					1.6,
				),
			);
			out.push(ink(p`M${x + s * r} ${g.ey - 3}L${s * (h.rx - 2)} ${g.ey - 1}`, 2.6));
		}
		out.push(
			ink(
				p`M${-g.ex + r + g.lx} ${g.ey - 2}Q${g.lx} ${g.ey - 8} ${g.ex - r + g.lx} ${g.ey - 2}`,
				3,
			),
		);
	} else if (k.eyewear === "shades") {
		for (const s of [-1, 1]) {
			const x = s * g.ex + g.lx;
			const lens =
				k.shadeStyle === "heart"
					? heartPath(x, g.ey + 1, 13)
					: roundRect(x - 15, g.ey - 10, 30, 21, 8);
			out.push(shape(lens, INK, 3));
			out.push(
				ink(
					p`M${x - 8} ${g.ey - 2}L${x - 2} ${g.ey - 7}M${x - 7} ${g.ey + 4}L${x + 3} ${g.ey - 5}`,
					2.2,
					W,
				),
			);
			out.push(ink(p`M${x + s * 15} ${g.ey - 4}L${s * (h.rx - 2)} ${g.ey - 3}`, 2.8));
		}
		out.push(
			ink(
				p`M${-g.ex + 14 + g.lx} ${g.ey - 4}Q${g.lx} ${g.ey - 9} ${g.ex - 14 + g.lx} ${g.ey - 4}`,
				3.2,
			),
		);
	} else if (k.eyewear === "patch") {
		const x = g.ex + g.lx;
		out.push(
			ink(
				p`M${x - 9} ${g.ey - 8}L${-h.rx * 0.55} ${-h.ry * 0.62}` +
					p`M${x + 10} ${g.ey - 6}L${h.rx - 1} ${g.ey - 9}`,
				2.6,
			),
		);
		out.push(oval(x, g.ey + 1, 13, 12, INK, 2.4));
		out.push(ink(p`M${x - 6} ${g.ey - 4}Q${x - 2} ${g.ey - 8} ${x + 4} ${g.ey - 7}`, 2, W));
	}
	return out.join("");
}

// ------------------------------------------------------------------ hair

/** Little "c" curl flicks scattered along the hair mass. */
function curlMarks(h, color, grow, from = 200, to = 340, step = 26) {
	let out = "";
	for (let a = from; a <= to; a += step) {
		const [x, y] = headPoint(h, a + wob(-6, 6), grow);
		out += ink(p`M${x - 3.5} ${y + 1.5}Q${x - 1} ${y - 4.5} ${x + 3.5} ${y - 1}`, 1.6, color);
	}
	return out;
}

function shine(h, hf) {
	if (hf !== INK) return "";
	return (
		ink(smooth(arc(h, 218, 246, -5, 7), false), 3, W) +
		ink(smooth(arc(h, 254, 262, -5, 4), false), 3, W)
	);
}

const HAIR = {
	curls(h, hf) {
		const outer = arc(h, 170, 370, 7, 15);
		const fringe = [];
		for (let i = 0; i <= 6; i++) {
			const x = h.rx * (0.92 - (1.84 * i) / 6);
			fringe.push([x, -h.ry * 0.42 + h.ry * 0.46 * (x / h.rx) ** 2]);
		}
		const d = bumps([...outer, ...fringe], 0.42);
		return { front: shape(d, hf, 3.6) + curlMarks(h, detailOn(hf), -9) };
	},
	bob(h, hf) {
		const jaw = h.ryb * 0.62;
		const back = smooth([
			[-(h.rx + 11), jaw, true],
			[-(h.rx + 12), 0],
			...arc(h, 195, 345, 10, 15),
			[h.rx + 12, 0],
			[h.rx + 11, jaw, true],
			[h.rx * 0.3, jaw + 8],
			[-h.rx * 0.3, jaw + 8],
		]);
		const bang = -h.ry * 0.3;
		const front = smooth([
			...arc(h, 172, 368, 6, 14),
			[h.rx * 0.86, bang * 0.4, true],
			[h.rx * 0.45, bang],
			[0, bang - 2],
			[-h.rx * 0.45, bang],
			[-h.rx * 0.86, bang * 0.4, true],
		]);
		let strands = "";
		for (const t of [-0.62, -0.28, 0.1, 0.46]) {
			strands += ink(p`M${h.rx * t} ${bang + 0.5}l1.5 -9`, 1.6, detailOn(hf));
		}
		const sideLines =
			ink(
				p`M${-(h.rx + 6)} ${jaw - 6}Q${-(h.rx + 9)} ${jaw * 0.3} ${-(h.rx + 6)} -6`,
				1.6,
				detailOn(hf),
			) +
			ink(p`M${h.rx + 6} ${jaw - 6}Q${h.rx + 9} ${jaw * 0.3} ${h.rx + 6} -6`, 1.6, detailOn(hf));
		return {
			back: shape(back, hf, 3.8) + sideLines,
			front: shape(front, hf, 3.6) + strands + shine(h, hf),
		};
	},
	spiky(h, hf) {
		const pts = [];
		const n = 14;
		for (let i = 0; i <= n; i++) {
			const a = 172 + (196 * i) / n;
			const tip = i % 2 === 1 && a > 186 && a < 354;
			pts.push(headPoint(h, tip ? a + 4 : a, tip ? 19 + wob(-3, 5) : 5));
		}
		const fr = [
			[0.9, -0.02],
			[0.62, -0.2],
			[0.42, -0.44],
			[0.14, -0.17],
			[-0.1, -0.46],
			[-0.36, -0.2],
			[-0.56, -0.44],
			[-0.9, -0.02],
		];
		for (const [x, y] of fr) pts.push([h.rx * x, h.ry * y]);
		const marks =
			ink(
				p`M${-h.rx * 0.3} ${-h.ry * 0.62}l6 -14M${h.rx * 0.2} ${-h.ry * 0.66}l-3 -14`,
				1.6,
				detailOn(hf),
			) + ink(p`M${h.rx * 0.55} ${-h.ry * 0.55}l7 -10`, 1.6, detailOn(hf));
		return { front: shape(bumps(pts, 0.08), hf, 3.6) + marks + shine(h, hf) };
	},
	braids(h, hf, _side, k) {
		const front = parted(h, -0.6);
		const yn = h.ryb + 6;
		let mid = "";
		for (const side of [-1, 1]) {
			mid += braid(side * (h.rx - 4), h.ryb * 0.45, side * (h.rx + 9), yn + 58, hf, side, k);
		}
		return { mid, front: shape(front, hf, 3.6) + partLine(h, hf, 0) + shine(h, hf) };
	},
	bun(h, hf) {
		const back =
			circle(0, -h.ry - 12, 20, hf, 3.8) +
			ink(
				p`M-9 ${-h.ry - 16}Q0 ${-h.ry - 26} 10 ${-h.ry - 15}Q4 ${-h.ry - 8} -3 ${-h.ry - 12}`,
				1.7,
				detailOn(hf),
			);
		const front = pulledBack(h, -0.56);
		return {
			back,
			front:
				shape(front, hf, 3.6) +
				combLines(h, hf) +
				oval(0, -h.ry - 4, 12, 4.6, DD, 2.4) +
				shine(h, hf),
		};
	},
	puffs(h, hf) {
		let back = "";
		let ties = "";
		for (const s of [-1, 1]) {
			back += shape(puff(s * h.rx * 0.84, -h.ry * 0.8, 25, 11), hf, 3.8);
			back += curlMarks(
				{ rx: 14, ry: 14, ryb: 14, n: 2, nb: 2 },
				detailOn(hf),
				0,
				200,
				340,
				60,
			).replace(/<path/g, `<path transform="translate(${f(s * h.rx * 0.84)} ${f(-h.ry * 0.8)})"`);
			// hair tie: two short bands across the stem of each puff
			const [tx, ty] = [s * h.rx * 0.66, -h.ry * 0.72];
			const tie = p`M${tx - s * 9} ${ty - 6}Q${tx} ${ty + 1} ${tx + s * 4} ${ty + 9}`;
			ties += ink(tie, 5.4) + ink(tie, 1.8, hf === INK ? W : DL);
		}
		return { back, front: shape(parted(h, -0.58), hf, 3.6) + partLine(h, hf, 0) + ties };
	},
	afro(h, hf) {
		const r = h.rx + 17;
		const back = shape(puff(0, -h.ry * 0.2, r, 20, 0.05), hf, 3.8);
		const marks = curlMarks(
			{ rx: r - 9, ry: r - 9, ryb: r - 9, n: 2, nb: 2 },
			detailOn(hf),
			0,
			150,
			390,
			24,
		).replace(/<path/g, `<path transform="translate(0 ${f(-h.ry * 0.2)})"`);
		const fringe = [];
		for (let i = 0; i <= 6; i++) {
			const x = h.rx * (0.9 - (1.8 * i) / 6);
			fringe.push([x, -h.ry * 0.44 + h.ry * 0.46 * (x / h.rx) ** 2]);
		}
		return {
			back: back + marks,
			front: shape(bumps([...arc(h, 172, 368, 2, 16), ...fringe], 0.4), hf, 3.4),
		};
	},
	buzz(h, hf) {
		const fill = hf === INK || hf === DD ? DD : DM;
		const line = [];
		for (let i = 0; i <= 10; i++) {
			const t = 0.92 - (1.84 * i) / 10;
			line.push([h.rx * t, -h.ry * 0.6 + h.ry * 0.34 * t * t]);
		}
		// a fuzzy, slightly scalloped edge reads as cropped hair rather than a cap
		const d = bumps([...arc(h, 188, 352, 2.5, 9), ...line], 0.16);
		let ticks = "";
		for (const t of [-0.6, -0.3, 0, 0.3, 0.6]) {
			const x = h.rx * t;
			const y = -h.ry * 0.6 + h.ry * 0.34 * t * t;
			ticks += ink(p`M${x} ${y - 3}l${t * 3} -6`, 1.4);
		}
		return { front: shape(d, fill, 2.8) + ticks };
	},
	swoop(h, hf, s) {
		const fr = [
			[0.92, -0.06],
			[0.55, -0.42],
			[0.05, -0.44],
			[-0.45, -0.22],
			[-0.86, 0.02, true],
		];
		const raw = [...arc(h, 172, 368, 6, 14), ...fr.map(([x, y, c]) => [h.rx * x, h.ry * y, c])];
		const pts = s > 0 ? raw : raw.map(([x, y, c]) => [-x, y, c]);
		const strands =
			ink(
				smooth(
					mirrorPts(
						[
							[h.rx * 0.6, -h.ry * 0.72],
							[0, -h.ry * 0.64],
							[-h.rx * 0.55, -h.ry * 0.28],
						],
						s,
					),
					false,
				),
				1.6,
				detailOn(hf),
			) +
			ink(
				smooth(
					mirrorPts(
						[
							[h.rx * 0.3, -h.ry * 0.86],
							[-h.rx * 0.2, -h.ry * 0.74],
							[-h.rx * 0.7, -h.ry * 0.3],
						],
						s,
					),
					false,
				),
				1.6,
				detailOn(hf),
			);
		const lick = shape(
			p`M${s * -4} ${-h.ry - 3}Q${s * 2} ${-h.ry - 22} ${s * 15} ${-h.ry - 19}` +
				p`Q${s * 6} ${-h.ry - 12} ${s * 8} ${-h.ry - 2}Z`,
			hf,
			3,
		);
		return { back: lick, front: shape(smooth(pts), hf, 3.6) + strands + shine(h, hf) };
	},
	ponytail(h, hf, s) {
		const tail = smooth(
			mirrorPts(
				[
					[h.rx * 0.2, -h.ry * 0.98],
					[h.rx + 22, -h.ry * 0.86],
					[h.rx + 38, -h.ry * 0.3],
					[h.rx + 30, h.ry * 0.42, true],
					[h.rx + 16, -h.ry * 0.12],
					[h.rx * 0.5, -h.ry * 0.5],
				],
				s,
			),
		);
		const tailLines = ink(
			p`M${s * (h.rx + 16)} ${-h.ry * 0.7}` +
				p`Q${s * (h.rx + 30)} ${-h.ry * 0.3} ${s * (h.rx + 28)} ${h.ry * 0.2}`,
			1.6,
			detailOn(hf),
		);
		return {
			back: shape(tail, hf, 3.8) + tailLines,
			front:
				shape(pulledBack(h, -0.54), hf, 3.6) +
				combLines(h, hf) +
				oval(s * h.rx * 0.84, -h.ry * 0.6, 5, 8.5, DD, 2.4, s * 30) +
				shine(h, hf),
		};
	},
	long(h, hf) {
		const yn = h.ryb + 6;
		const back = smooth([
			[-(h.rx + 13), yn + 44, true],
			[-(h.rx + 15), 0],
			...arc(h, 190, 350, 11, 15),
			[h.rx + 15, 0],
			[h.rx + 13, yn + 44, true],
			[0, yn + 44],
		]);
		let mid = "";
		for (const s of [-1, 1]) {
			const lock = [
				[h.rx - 14, 0],
				[h.rx + 9, h.ry * 0.25],
				[h.rx + 12, h.ryb * 0.85],
				[h.rx + 7, yn + 14],
				[h.rx + 13, yn + 46, true],
				[h.rx - 3, yn + 30],
				[h.rx - 9, yn + 6],
				[h.rx - 14, h.ryb * 0.6],
			].map(([x, y, c]) => [s * x, y, c]);
			mid += shape(smooth(lock), hf, 3.6);
			mid += ink(
				p`M${s * (h.rx + 2)} ${h.ryb * 0.7}` +
					p`Q${s * (h.rx + 6)} ${yn + 6} ${s * (h.rx + 4)} ${yn + 30}`,
				1.6,
				detailOn(hf),
			);
		}
		return {
			back: shape(back, hf, 3.8),
			mid,
			front: shape(parted(h, -0.56), hf, 3.6) + partLine(h, hf, 0) + shine(h, hf),
		};
	},
};

/** Hair cap with a centre parting (curtain fringe). */
function parted(h, top) {
	return smooth([
		...arc(h, 172, 368, 5, 14),
		[h.rx * 0.9, h.ry * 0.04],
		[h.rx * 0.6, -h.ry * 0.3],
		[h.rx * 0.3, (top + 0.04) * h.ry],
		[h.rx * 0.06, top * h.ry],
		[0, (top + 0.05) * h.ry, true],
		[-h.rx * 0.06, top * h.ry],
		[-h.rx * 0.3, (top + 0.04) * h.ry],
		[-h.rx * 0.6, -h.ry * 0.3],
		[-h.rx * 0.9, h.ry * 0.04],
	]);
}

function partLine(h, hf, x) {
	return ink(p`M${x} ${-h.ry * 0.52}Q${x + 1} ${-h.ry * 0.8} ${x} ${-h.ry - 4}`, 1.6, detailOn(hf));
}

/** Hair cap combed back off the forehead (buns, ponytails). */
function pulledBack(h, top) {
	return smooth([
		...arc(h, 172, 368, 4, 14),
		[h.rx * 0.9, -h.ry * 0.02],
		[h.rx * 0.55, -h.ry * 0.46],
		[0, top * h.ry],
		[-h.rx * 0.55, -h.ry * 0.46],
		[-h.rx * 0.9, -h.ry * 0.02],
	]);
}

function combLines(h, hf) {
	let out = "";
	for (const t of [-0.45, -0.15, 0.15, 0.45]) {
		out += ink(
			p`M${h.rx * t * 1.2} ${-h.ry * 0.52}` +
				p`Q${h.rx * t} ${-h.ry * 0.8} ${h.rx * t * 0.3} ${-h.ry - 2}`,
			1.5,
			detailOn(hf),
		);
	}
	return out;
}

function braid(x0, y0, x1, y1, hf, side, k) {
	const segs = 5;
	let out = "";
	for (let i = segs - 1; i >= 0; i--) {
		const t = (i + 0.5) / segs;
		const x = x0 + (x1 - x0) * t;
		const y = y0 + (y1 - y0) * t;
		const tilt = (i % 2 ? 22 : -22) * side;
		out += oval(x, y, 9.5, 12, hf, 3, tilt);
		out += ink(p`M${x - 5} ${y - 3}Q${x} ${y + 3} ${x + 5} ${y - 3}`, 1.5, detailOn(hf));
	}
	const tuft =
		p`M${x1 - 5} ${y1 + 6}L${x1 - 10} ${y1 + 23}` +
		p`Q${x1} ${y1 + 18} ${x1 + 10} ${y1 + 23}` +
		p`L${x1 + 5} ${y1 + 6}Z`;
	return out + shape(tuft, hf, 2.8) + oval(x1, y1 + 6, 7, 3.8, k.tieFill, 2.4);
}

// ------------------------------------------------------------------ headwear

function foreheadTufts(hf, y) {
	let out = "";
	for (const x of [-12, 4]) {
		out += shape(
			p`M${x - 6} ${y}Q${x - 3} ${y + 10} ${x + 3} ${y + 13}Q${x + 1} ${y + 6} ${x + 7} ${y}Z`,
			hf,
			2.4,
		);
	}
	return out;
}

const FRINGED = new Set(["curls", "spiky", "swoop", "afro"]);

const HATS = {
	beanie(h, k) {
		const { rx, ry } = h;
		const b = -ry * 0.22;
		const fill = k.hatFill;
		const dome =
			p`M${-(rx + 5)} ${b - 8}C${-(rx + 8)} ${-ry - 6} ${-rx * 0.56} ${-ry - 19} 0 ${-ry - 19}` +
			p`C${rx * 0.56} ${-ry - 19} ${rx + 8} ${-ry - 6} ${rx + 5} ${b - 8}Z`;
		let knit = shape(
			p`M${rx * 0.4} ${-ry - 30}C${rx * 0.75} ${-ry * 0.8} ${rx * 0.7} ${b} ${rx * 0.62} ${b}` +
				p`L${rx + 20} ${b}L${rx + 20} ${-ry - 30}Z`,
			darker(fill),
			0,
		);
		for (const t of [-0.62, -0.22, 0.2, 0.6]) {
			knit += ink(
				p`M${rx * t * 1.45} ${b - 10}Q${rx * t * 1.25} ${-ry * 0.68} ${rx * t * 0.45} ${-ry - 15}`,
				1.6,
			);
		}
		if (k.hatBand)
			knit += shape(
				p`M-90 ${-ry * 0.7}Q0 ${-ry * 0.84} 90 ${-ry * 0.7}` +
					p`L90 ${-ry * 0.52}Q0 ${-ry * 0.66} -90 ${-ry * 0.52}Z`,
				DD,
				0,
			);
		const cuff =
			p`M${-(rx + 8)} ${b + 8}C${-rx * 0.55} ${b - 6} ${rx * 0.55} ${b - 6} ${rx + 8} ${b + 8}` +
			p`L${rx + 6} ${b - 12}` +
			p`C${rx * 0.55} ${b - 27} ${-rx * 0.55} ${b - 27} ${-(rx + 6)} ${b - 12}` +
			p`Z`;
		let ribs = shape(
			p`M${rx * 0.5} ${b - 40}L${rx + 20} ${b - 40}L${rx + 20} ${b + 20}L${rx * 0.5} ${b + 20}Z`,
			darker(fill),
			0,
		);
		for (let x = -rx - 6; x <= rx + 6; x += 6.5)
			ribs += ink(p`M${x} ${b - 30}L${x} ${b + 12}`, 1.5);
		const pomD = puff(0, -ry - 30, 15, 12);
		const pom = clipped(pomD, W, 3.6, circle(8, -ry - 25, 15, DL) + circle(-3, -ry - 33, 12, W));
		const tufts = FRINGED.has(k.hair) ? foreheadTufts(k.hairFill, b - 3) : "";
		return { front: pom + clipped(dome, fill, 4.2, knit) + tufts + clipped(cuff, fill, 4.2, ribs) };
	},
	capBack(h, k) {
		const { rx, ry } = h;
		const s = k.side;
		const f0 = -ry * 0.3;
		const dome =
			p`M${-(rx + 4)} ${f0 + 10}C${-(rx + 7)} ${-ry - 4} ${-rx * 0.56} ${-ry - 16} 0 ${-ry - 16}` +
			p`C${rx * 0.56} ${-ry - 16} ${rx + 7} ${-ry - 4} ${rx + 4} ${f0 + 10}` +
			p`C${rx * 0.5} ${f0 - 6} ${-rx * 0.5} ${f0 - 6} ${-(rx + 4)} ${f0 + 10}Z`;
		const brim =
			p`M${s * rx * 0.2} ${-ry * 0.92}` +
			p`C${s * rx * 0.7} ${-ry * 1.14} ${s * (rx + 30)} ${-ry * 1.02}` +
			p` ${s * (rx + 40)} ${-ry * 0.7}` +
			p`C${s * (rx + 24)} ${-ry * 0.52} ${s * rx * 0.7} ${-ry * 0.58}` +
			p` ${s * rx * 0.2} ${-ry * 0.92}Z`;
		const panel =
			shape(
				p`M${rx * 0.45} ${-ry - 30}` +
					p`C${rx * 0.8} ${-ry * 0.8} ${rx * 0.75} ${f0} ${rx * 0.65} ${f0 + 4}` +
					p`L${rx + 20} ${f0 + 20}L${rx + 20} ${-ry - 30}Z`,
				darker(k.hatFill),
				0,
			) +
			ink(
				p`M0 ${-ry - 15}Q${-rx * 0.36} ${-ry * 0.72} ${-rx * 0.44} ${f0 - 1}` +
					p`M0 ${-ry - 15}Q${rx * 0.36} ${-ry * 0.72} ${rx * 0.44} ${f0 - 1}`,
				2,
			);
		const win =
			p`M-15 ${f0 - 1}L-15 ${f0 - 14}Q0 ${f0 - 33} 15 ${f0 - 14}` +
			p`L15 ${f0 - 1}Q0 ${f0 - 3} -15 ${f0 - 1}Z`;
		let strap = shape(p`M-17 ${f0 - 2}L17 ${f0 - 2}L17 ${f0 - 9}L-17 ${f0 - 9}Z`, DD, 2.2);
		for (const x of [-10, -4, 2, 8]) strap += circle(x, f0 - 5.5, 1.4, W);
		return {
			behind: shape(brim, DD, 3.8),
			front:
				clipped(dome, k.hatFill, 4.2, panel) +
				shape(win, k.hairFill, 2.6) +
				strap +
				circle(0, -ry - 15, 4, k.hatFill, 2.4),
		};
	},
	helmet(h, k) {
		const { rx, ry, ryb } = h;
		const e0 = -ry * 0.04;
		const fr = -ry * 0.4;
		const shell =
			p`M${-(rx + 9)} ${e0}C${-(rx + 14)} ${-ry * 0.9} ${-rx * 0.62} ${-ry - 26} 0 ${-ry - 26}` +
			p`C${rx * 0.62} ${-ry - 26} ${rx + 14} ${-ry * 0.9} ${rx + 9} ${e0}` +
			p`L${rx + 3} ${e0 + 2}C${rx * 0.6} ${fr - 8} ${-rx * 0.6} ${fr - 8} ${-(rx + 3)} ${e0 + 2}Z`;
		let inner = shape(
			p`M${rx * 0.5} ${-ry - 40}` +
				p`C${rx * 0.85} ${-ry * 0.8} ${rx * 0.85} ${fr} ${rx * 0.8} ${e0 + 10}` +
				p`L${rx + 30} ${e0 + 10}L${rx + 30} ${-ry - 40}Z`,
			DL,
			0,
		);
		inner += shape(p`M-9 ${-ry - 40}L9 ${-ry - 40}L11 ${fr}L-11 ${fr}Z`, k.hatFill, 0);
		for (const s of [-1, 1]) {
			for (const [t, top, low] of [
				[0.3, -ry - 18, -ry * 0.5],
				[0.64, -ry * 0.92, -ry * 0.3],
			]) {
				const x = s * rx * t;
				inner += taper(x - s * 2, top, x + s * 3, (top + low) / 2, x + s * 5, low, 5.4);
			}
		}
		inner += ink(p`M${-rx * 0.8} ${fr + 2}Q0 ${fr - 16} ${rx * 0.8} ${fr + 2}`, 2.2);
		const lip =
			p`M${-rx * 0.5} ${fr - 6}Q0 ${fr - 14} ${rx * 0.5} ${fr - 6}` +
			p`L${rx * 0.56} ${fr + 1}Q0 ${fr - 8} ${-rx * 0.56} ${fr + 1}Z`;
		let straps = "";
		for (const s of [-1, 1]) {
			const d = p`M${s * (rx + 2)} ${e0}Q${s * (rx - 3)} ${ryb * 0.72} ${s * 9} ${ryb + 2}`;
			straps += ink(d, 4.4) + ink(d, 1.4, W);
		}
		straps += shape(roundRect(-7, ryb - 2, 14, 8, 2), W, 2.4);
		return { front: clipped(shell, W, 4.4, inner) + shape(lip, DD, 2.4) + straps };
	},
	flowers(h, k) {
		let out = ink(smooth(arc(h, 196, 344, 3, 12), false), 2.2);
		const pts = arc(h, 202, 338, 3, 22.7);
		pts.forEach(([x, y], i) => {
			if (i > 0) {
				const [px, py] = pts[i - 1];
				const mx = (x + px) / 2;
				const my = (y + py) / 2 - 2;
				const a = (Math.atan2(y - py, x - px) * 180) / Math.PI;
				out += group(
					shape("M0 0Q6 -7 14 0Q6 7 0 0Z", k.hatFill, 1.8),
					`translate(${f(mx - 6)} ${f(my)}) rotate(${f(a - 25)})`,
				);
			}
		});
		pts.forEach(([x, y], i) => {
			const at = `translate(${f(x)} ${f(y)}) scale(${i % 2 ? 0.78 : 1})`;
			out += `<use href="#flower" transform="${at}"/>`;
		});
		return { front: out };
	},
	headphones(h, k) {
		const { rx, ry } = h;
		const g = faceGeo(h, k);
		const outer = arc(h, 190, 350, 14, 10);
		const inner = arc(h, 350, 190, 6, 10);
		outer[0] = [...outer[0], true];
		outer[outer.length - 1] = [...outer[outer.length - 1], true];
		inner[0] = [...inner[0], true];
		inner[inner.length - 1] = [...inner[inner.length - 1], true];
		let out = shape(smooth([...outer, ...inner]), k.hatFill, 3.4);
		out += ink(smooth(arc(h, 205, 335, 10, 10), false), 1.5);
		for (const s of [-1, 1]) {
			const x = s * (rx + 6);
			out += ink(p`M${s * (rx + 9)} ${-ry * 0.22}L${x} ${g.ey - 15}`, 5);
			out += shape(roundRect(s > 0 ? rx - 5 : -rx - 3, g.ey - 16, 8, 34, 4), W, 2.6);
			out += shape(roundRect(x - 10, g.ey - 20, 20, 42, 9), INK, 3);
			out += ink(p`M${x - 4} ${g.ey - 12}L${x - 4} ${g.ey + 4}`, 2.4, W);
		}
		return { front: out };
	},
	bandana(h, k) {
		const { rx, ry } = h;
		const s = k.side;
		const w0 = -ry * 0.1;
		const wrap =
			p`M${-(rx + 6)} ${w0}C${-(rx + 8)} ${-ry - 4} ${-rx * 0.56} ${-ry - 13} 0 ${-ry - 13}` +
			p`C${rx * 0.56} ${-ry - 13} ${rx + 8} ${-ry - 4} ${rx + 6} ${w0}` +
			p`C${rx * 0.5} ${w0 - 20} ${-rx * 0.5} ${w0 - 20} ${-(rx + 6)} ${w0}Z`;
		const shadeIn =
			shape(
				p`M${rx * 0.45} ${-ry - 30}C${rx * 0.8} ${-ry * 0.7} ${rx * 0.7} ${w0} ${rx * 0.6} ${w0}` +
					p`L${rx + 20} ${w0 + 10}L${rx + 20} ${-ry - 30}Z`,
				DD,
				0,
			) +
			ink(
				p`M${-(rx + 5)} ${w0 - 7}` +
					p`C${-rx * 0.5} ${w0 - 26} ${rx * 0.5} ${w0 - 26} ${rx + 5} ${w0 - 7}`,
				1.8,
			) +
			ink(p`M${-rx * 0.5} ${-ry * 0.7}Q${-rx * 0.2} ${-ry * 0.9} ${rx * 0.15} ${-ry * 0.82}`, 1.6);
		const k0 = [s * (rx + 4), w0 - 7];
		const tails =
			shape(
				p`M${k0[0]} ${k0[1] - 3}L${s * (rx + 32)} ${w0 + 4}` +
					p`Q${s * (rx + 25)} ${w0 + 11} ${s * (rx + 28)} ${w0 + 19}` +
					p`L${k0[0]} ${k0[1] + 5}Z`,
				PO,
				3,
			) +
			shape(
				p`M${k0[0]} ${k0[1] + 1}L${s * (rx + 13)} ${w0 + 32}` +
					p`L${s * (rx + 22)} ${w0 + 27}L${k0[0] + s * 4} ${k0[1] + 2}Z`,
				PO,
				3,
			);
		return {
			front: clipped(wrap, PO, 4.2, shadeIn) + tails + oval(k0[0], k0[1], 8, 7, PO, 3),
		};
	},
	goggles(h) {
		const { rx, ry } = h;
		const g0 = -ry * 0.46;
		let out = shape(
			p`M${-(rx + 4)} ${g0 + 6}C${-rx * 0.5} ${g0 - 8} ${rx * 0.5} ${g0 - 8} ${rx + 4} ${g0 + 6}` +
				p`L${rx + 3} ${g0 - 4}` +
				p`C${rx * 0.5} ${g0 - 18} ${-rx * 0.5} ${g0 - 18} ${-(rx + 3)} ${g0 - 4}` +
				p`Z`,
			DD,
			2.6,
		);
		for (const s of [-1, 1]) {
			const x = s * 17;
			out += circle(x, g0 - 10, 14, W, 4.2);
			out += circle(x, g0 - 10, 9.5, DL, 1.8);
			out += ink(p`M${x - 6} ${g0 - 12}Q${x - 4} ${g0 - 17} ${x + 1} ${g0 - 17}`, 2.4, W);
			out += circle(x + s * 10, g0 - 19, 1.3, INK);
		}
		out += ink(p`M-4 ${g0 - 13}Q0 ${g0 - 16} 4 ${g0 - 13}`, 3.6);
		return { front: out };
	},
	hood(h, k) {
		const { rx, ry, ryb } = h;
		const s = k.side;
		const raw = [
			[-(rx + 15), ryb * 0.75],
			[-(rx + 16), -ry * 0.05],
			[-(rx * 0.85 + 11), -ry * 0.72],
			[-rx * 0.35, -ry - 12],
			[rx * 0.12, -ry - 34],
			[rx * 0.66, -ry - 62, true],
			[rx * 0.48, -ry - 28],
			[rx * 0.8, -ry * 0.82],
			[rx + 16, -ry * 0.05],
			[rx + 15, ryb * 0.75],
			[rx * 0.6, ryb + 16],
			[0, ryb + 21],
			[-rx * 0.6, ryb + 16],
		];
		const pts = raw.map(([x, y, c]) => [x * s, y, c]);
		const oy = ry * 0.1;
		const orx = rx * 0.84;
		const ory = ry * 0.88;
		const d = smooth(pts) + ellipsePath(0, oy, orx, ory);
		let inner = shape(
			p`M${rx * 0.4} ${-ry - 80}L${rx + 40} ${-ry - 80}` +
				p`L${rx + 40} ${ryb + 40}L${rx * 0.5} ${ryb + 40}` +
				p`C${rx * 0.8} ${ryb * 0.4} ${rx * 0.8} ${-ry * 0.5} ${rx * 0.4} ${-ry - 80}Z`,
			darker(k.hatFill),
			0,
		);
		inner += oval(0, oy, orx + 7, ory + 7, "none", 2.2);
		for (const [x, y, r] of [
			[-rx - 4, -ry * 0.25, 6],
			[s * rx * 0.25, -ry - 20, 5],
			[-rx * 0.62, ryb * 0.9, 4.5],
			[rx + 4, ryb * 0.5, 5],
		]) {
			inner += shape(starPath(x, y, r, r * 0.42, 4), W, 1.4);
		}
		const tip = shape(starPath(s * rx * 0.66, -ry - 64, 8, 3.6, 5), W, 2.6);
		return { front: clipped(d, k.hatFill, 4.2, inner, true) + tip };
	},
	bucket(h, k) {
		const { rx, ry } = h;
		const c0 = -ry * 0.4;
		const b1 = -ry * 0.05;
		const crown =
			p`M${-rx * 0.74} ${c0 + 2}C${-rx * 0.78} ${-ry - 6} ${-rx * 0.56} ${-ry - 20} 0 ${-ry - 20}` +
			p`C${rx * 0.56} ${-ry - 20} ${rx * 0.78} ${-ry - 6} ${rx * 0.74} ${c0 + 2}Z`;
		const crownIn =
			shape(
				p`M${rx * 0.3} ${-ry - 30}C${rx * 0.6} ${-ry * 0.8} ${rx * 0.55} ${c0} ${rx * 0.5} ${c0}` +
					p`L${rx} ${c0 + 10}L${rx} ${-ry - 30}Z`,
				darker(k.hatFill),
				0,
			) +
			shape(p`M-90 ${c0 - 11}Q0 ${c0 - 20} 90 ${c0 - 11}L90 ${c0 + 10}L-90 ${c0 + 10}Z`, DD, 0) +
			dashed(p`M${-rx * 0.6} ${-ry * 0.82}Q0 ${-ry - 14} ${rx * 0.6} ${-ry * 0.82}`);
		const brim =
			p`M${-rx * 0.76} ${c0 + 2}Q0 ${c0 - 10} ${rx * 0.76} ${c0 + 2}` +
			p`C${rx + 10} ${c0 + 6} ${rx + 22} ${b1 - 2} ${rx + 25} ${b1 + 7}` +
			p`Q0 ${b1 - 30} ${-(rx + 25)} ${b1 + 7}` +
			p`C${-(rx + 22)} ${b1 - 2} ${-(rx + 10)} ${c0 + 6} ${-rx * 0.76} ${c0 + 2}Z`;
		const brimIn =
			shape(
				p`M${rx * 0.55} ${c0 - 20}L${rx + 40} ${c0 - 20}` +
					p`L${rx + 40} ${b1 + 20}L${rx * 0.62} ${b1 + 20}Z`,
				darker(k.hatFill),
				0,
			) + dashed(p`M${-(rx + 16)} ${b1 - 1}Q0 ${b1 - 27} ${rx + 16} ${b1 - 1}`);
		const shadow = shape(
			p`M${-(rx + 25)} ${b1 + 2}Q0 ${b1 - 34} ${rx + 25} ${b1 + 2}` +
				p`L${rx + 25} ${b1 + 13}Q0 ${b1 - 21} ${-(rx + 25)} ${b1 + 13}Z`,
			k.skin.sh,
			0,
		);
		return {
			shadow,
			front: clipped(crown, k.hatFill, 4.2, crownIn) + clipped(brim, k.hatFill, 4.2, brimIn),
		};
	},
	bow(h, k) {
		const s = k.side;
		const loops =
			shape("M0 0C-6 -15 -25 -19 -28 -4C-30 9 -12 12 0 0Z", k.hatFill, 3) +
			shape("M0 0C6 -15 25 -19 28 -4C30 9 12 12 0 0Z", k.hatFill, 3) +
			ink("M-6 -3Q-14 -6 -21 -4M6 -3Q14 -6 21 -4", 1.6) +
			shape("M-3 4L-11 22L-4 20L0 7Z", k.hatFill, 2.6) +
			shape("M3 4L11 22L4 20L0 7Z", k.hatFill, 2.6) +
			oval(0, 0, 6.5, 7.5, k.hatFill, 3);
		return {
			front: group(loops, `translate(${f(s * h.rx * 0.5)} ${f(-h.ry * 0.86)}) rotate(${s * 18})`),
		};
	},
	crown(h, k) {
		const { rx, ry } = h;
		const k0 = -ry * 0.62;
		const tips = [-0.66, -0.33, 0, 0.33, 0.66];
		const pts = [[-rx * 0.84, k0 + 4, true]];
		tips.forEach((t, i) => {
			if (i > 0) pts.push([rx * (t - 0.165), k0 - 14 - Math.abs(t) * -4, true]);
			pts.push([rx * t, k0 - 36 - (t === 0 ? 7 : 0) + Math.abs(t) * 6, true]);
		});
		pts.push([rx * 0.84, k0 + 4, true], [0, k0 - 4]);
		let inner = shape(
			p`M${rx * 0.5} ${k0 - 60}L${rx} ${k0 - 60}L${rx} ${k0 + 20}L${rx * 0.5} ${k0 + 20}Z`,
			DL,
			0,
		);
		inner += ink(p`M${-rx * 0.84} ${k0 - 6}Q0 ${k0 - 15} ${rx * 0.84} ${k0 - 6}`, 1.8);
		inner +=
			shape(starPath(-rx * 0.33, k0 - 4, 5, 2.2), INK, 0) +
			shape(heartPath(rx * 0.33, k0 - 4, 4), INK, 0);
		inner += circle(0, k0 - 4, 3.6, W, 1.8);
		let balls = "";
		tips.forEach((t) => {
			balls += circle(rx * t, k0 - 38 - (t === 0 ? 7 : 0) + Math.abs(t) * 6, 4.4, DD, 2.2);
		});
		return {
			front: group(clipped(smooth(pts), W, 3.4, inner) + balls, `rotate(${k.side * 7} 0 ${f(k0)})`),
		};
	},
	bearHood(h, k) {
		const { rx, ry, ryb } = h;
		const pts = [
			...arc(h, 150, 390, 13, 12),
			[rx * 0.82, ryb + 14],
			[0, ryb + 20],
			[-rx * 0.82, ryb + 14],
		];
		const oy = ry * 0.1;
		const orx = rx * 0.84;
		const ory = ry * 0.88;
		let ears = "";
		for (const a of [232, 308]) {
			const [x, y] = headPoint(h, a, 12);
			ears +=
				circle(x, y, 19, k.hatFill, 4.2) + circle(x, y + 1, 10, k.hatFill === DL ? DM : DL, 2.6);
		}
		let inner = shape(
			p`M${rx * 0.4} ${-ry - 40}L${rx + 40} ${-ry - 40}` +
				p`L${rx + 40} ${ryb + 40}L${rx * 0.5} ${ryb + 40}` +
				p`C${rx * 0.8} ${ryb * 0.4} ${rx * 0.8} ${-ry * 0.5} ${rx * 0.4} ${-ry - 40}Z`,
			darker(k.hatFill),
			0,
		);
		inner += oval(0, oy, orx + 7, ory + 7, "none", 2.2);
		inner += ink(
			p`M${-rx * 0.4} ${-ry - 6}l3 5M${-rx * 0.1} ${-ry - 10}l2 5M${rx * 0.3} ${-ry - 8}l-1 5`,
			1.5,
		);
		return {
			front:
				ears + clipped(smooth(pts) + ellipsePath(0, oy, orx, ory), k.hatFill, 4.2, inner, true),
		};
	},
};

// ------------------------------------------------------------------ torsos

function torsoPath(yn, tw) {
	return (
		p`M-18 ${yn - 12}C${-tw * 0.45} ${yn - 8} ${-tw + 10} ${yn + 2} ${-tw} ${yn + 24}` +
		p`C${-tw - 14} ${yn + 40} ${-tw - 20} ${yn + 80} ${-tw - 23} ${yn + 130}` +
		p`L${-tw - 25} ${yn + 290}L${tw + 25} ${yn + 290}` +
		p`L${tw + 23} ${yn + 130}C${tw + 20} ${yn + 80} ${tw + 14} ${yn + 40} ${tw} ${yn + 24}` +
		p`C${tw - 10} ${yn + 2} ${tw * 0.45} ${yn - 8} 18 ${yn - 12}Z`
	);
}

function chestPrint(kind, x, y) {
	switch (kind) {
		case "star":
			return shape(starPath(x, y, 14, 6.4), DM, 2.6);
		case "heart":
			return shape(heartPath(x, y, 12), DD, 2.6);
		case "bolt":
			return shape(
				p`M${x + 4} ${y - 15}L${x - 8} ${y + 2}` +
					p`L${x} ${y + 2}L${x - 4} ${y + 15}L${x + 9} ${y - 3}` +
					p`L${x + 1} ${y - 3}Z`,
				DD,
				2.4,
			);
		case "planet":
			return (
				circle(x, y, 9, DM, 2.4) +
				oval(x, y, 17, 5, "none", 2.4, -18) +
				circle(x - 3, y - 3, 2.4, W)
			);
		case "moon":
			return (
				shape(
					p`M${x + 2} ${y - 13}A13 13 0 1 0 ${x + 8} ${y + 10}A10 10 0 1 1 ${x + 2} ${y - 13}Z`,
					DD,
					2.4,
				) + circle(x + 9, y - 8, 1.6, INK)
			);
		case "rainbow":
			return ink(
				p`M${x - 15} ${y + 7}A15 15 0 0 1 ${x + 15} ${y + 7}` +
					p`M${x - 10} ${y + 7}A10 10 0 0 1 ${x + 10} ${y + 7}` +
					p`M${x - 5} ${y + 7}A5 5 0 0 1 ${x + 5} ${y + 7}`,
				2.6,
			);
		default:
			return (
				circle(x, y, 11, W, 2.4) +
				circle(x - 4, y - 2, 1.6, INK) +
				circle(x + 4, y - 2, 1.6, INK) +
				ink(p`M${x - 5} ${y + 3}Q${x} ${y + 7} ${x + 5} ${y + 3}`, 1.8)
			);
	}
}

function pin(kind, x, y) {
	const base = circle(x, y, 7.5, kind === "dark" ? DD : W, 2.4);
	if (kind === "star") return base + shape(starPath(x, y, 5, 2.2), INK, 0);
	if (kind === "heart") return base + shape(heartPath(x, y + 0.5, 3.6), INK, 0);
	if (kind === "dark") return base + circle(x - 2, y - 2, 2, W);
	return base + ink(p`M${x} ${y - 4}L${x} ${y + 1}`, 2) + circle(x, y + 3.6, 1.1, INK);
}

function scarf(yn, k) {
	const s = k.side;
	const fill = k.scarfFill;
	let tail = shape(
		p`M${s * 12} ${yn + 10}L${s * 34} ${yn + 10}L${s * 38} ${yn + 84}L${s * 18} ${yn + 87}Z`,
		fill,
		3.6,
	);
	tail += shape(
		p`M${s * 14} ${yn + 34}L${s * 35} ${yn + 34}L${s * 36} ${yn + 46}L${s * 15} ${yn + 47}Z`,
		DD,
		0,
	);
	tail += shape(
		p`M${s * 16} ${yn + 60}L${s * 37} ${yn + 59}L${s * 37} ${yn + 71}L${s * 17} ${yn + 72}Z`,
		DD,
		0,
	);
	tail += ink(
		p`M${s * 21} ${yn + 87}L${s * 21} ${yn + 95}` +
			p`M${s * 27} ${yn + 86}L${s * 28} ${yn + 94}` +
			p`M${s * 33} ${yn + 85}L${s * 35} ${yn + 93}`,
		2,
	);
	const wrap =
		p`M-41 ${yn - 15}C-22 ${yn - 4} 22 ${yn - 4} 41 ${yn - 15}` +
		p`L45 ${yn + 10}C22 ${yn + 25} -22 ${yn + 25} -45 ${yn + 10}Z`;
	let bands = "";
	for (const x of [-30, -8, 14, 36])
		bands += shape(
			p`M${x} ${yn - 30}L${x + 9} ${yn - 30}L${x + 7} ${yn + 40}L${x - 2} ${yn + 40}Z`,
			DD,
			0,
		);
	bands += ink(p`M-40 ${yn - 2}C-20 ${yn + 10} 20 ${yn + 10} 40 ${yn - 2}`, 1.6);
	return tail + clipped(wrap, fill, 3.8, bands);
}

function drawTorso(k, yn) {
	const { tw, cloth } = k;
	const out = [];
	const base = cloth.type === "stripes" ? W : cloth.fill;
	const inner = [];
	if (cloth.type === "stripes") {
		for (let y = yn + 8; y < yn + 300; y += 22) {
			inner.push(
				shape(p`M-160 ${y}Q0 ${y + 10} 160 ${y}L160 ${y + 10}Q0 ${y + 20} -160 ${y + 10}Z`, DD, 0),
			);
		}
	} else {
		// dark clothes only get a narrow solid-ink rim, so they never read as a black slab
		const edge = base === DD ? 0.7 : 0.54;
		const shadow = base === DD ? INK : darker(base);
		inner.push(
			shape(
				p`M${tw * edge} ${yn - 20}` +
					p`C${tw * (edge - 0.17)} ${yn + 60} ${tw * (edge - 0.07)} ${yn + 150}` +
					p` ${tw * (edge + 0.03)} ${yn + 300}` +
					p`L${tw + 40} ${yn + 300}L${tw + 40} ${yn - 20}Z`,
				shadow,
				0,
			),
		);
	}
	if (cloth.type === "puffer") {
		for (const y of [yn + 46, yn + 98, yn + 150])
			inner.push(ink(p`M-160 ${y}Q0 ${y + 14} 160 ${y}`, 2.6));
	}
	if (cloth.type === "sweater") {
		for (const cx of [-27, 27]) {
			inner.push(
				ink(
					p`M${cx - 9} ${yn + 12}L${cx - 9} ${yn + 200}M${cx + 9} ${yn + 12}L${cx + 9} ${yn + 200}`,
					1.6,
				),
			);
			for (let y = yn + 18; y < yn + 200; y += 13) {
				inner.push(ink(p`M${cx - 6} ${y}Q${cx} ${y + 2} ${cx + 5} ${y + 9}`, 1.8));
			}
		}
		for (let y = yn + 26; y < yn + 200; y += 12)
			inner.push(ink(p`M-5 ${y}L0 ${y + 5}L5 ${y}`, 1.6));
	}
	for (const s of [-1, 1]) {
		inner.push(
			ink(
				p`M${s * (tw - 5)} ${yn + 38}Q${s * (tw - 8)} ${yn + 90} ${s * (tw - 6)} ${yn + 170}`,
				2.6,
			),
		);
	}
	const fold = base === DD || base === DM ? W : INK;
	inner.push(taper(-tw + 14, yn + 50, -tw + 22, yn + 62, -tw + 20, yn + 80, 2.2, fold));
	inner.push(taper(-tw + 24, yn + 30, -tw + 30, yn + 38, -tw + 30, yn + 50, 1.8, fold));
	inner.push(taper(tw - 30, yn + 70, tw - 22, yn + 84, tw - 24, yn + 104, 2.2, fold));
	if (cloth.type === "overalls") {
		const bib = p`M-38 ${yn + 46}L38 ${yn + 46}L42 ${yn + 300}L-42 ${yn + 300}Z`;
		inner.push(shape(bib, cloth.bib, 3.4));
		inner.push(dashed(p`M-33 ${yn + 52}L33 ${yn + 52}`));
		inner.push(
			shape(
				p`M-16 ${yn + 66}L16 ${yn + 66}L15 ${yn + 92}Q0 ${yn + 96} -15 ${yn + 92}Z`,
				cloth.bib,
				2.4,
			),
		);
		inner.push(dashed(p`M-12 ${yn + 72}L12 ${yn + 72}`, 1.2));
	}
	out.push(clipped(torsoPath(yn, tw), base, 4.2, inner.join("")));
	if (cloth.type === "tee" || cloth.type === "stripes") {
		if (cloth.print) out.push(chestPrint(cloth.print, k.printX, yn + 46));
	}
	if (cloth.type === "overalls") {
		for (const s of [-1, 1]) {
			out.push(
				shape(
					p`M${s * 38} ${yn + 50}L${s * 25} ${yn + 50}L${s * 32} ${yn - 5}L${s * 46} ${yn - 2}Z`,
					cloth.bib,
					3,
				),
			);
			out.push(circle(s * 31, yn + 51, 5, W, 2.4) + circle(s * 31, yn + 51, 1.4, INK));
		}
	}
	if (k.straps) {
		for (const s of [-1, 1]) {
			out.push(
				shape(
					p`M${s * (tw - 16)} ${yn + 12}L${s * (tw - 31)} ${yn + 4}` +
						p`L${s * (tw - 40)} ${yn + 170}L${s * (tw - 25)} ${yn + 174}Z`,
					DM,
					3,
				),
			);
			out.push(shape(roundRect(s * (tw - 28) - 9, yn + 50, 18, 10, 2.5), W, 2.2));
		}
	}
	return out.join("");
}

/** Neck plus the neckline that tucks it into the clothes. */
function drawNeck(k, h, yn) {
	const { skin, cloth } = k;
	const out = [];
	const neck = p`M-13 ${h.ryb - 16}L-13.5 ${yn + 2}Q0 ${yn + 10} 13.5 ${yn + 2}L13 ${h.ryb - 16}Z`;
	const chinShade = shape(
		p`M-20 ${h.ryb - 20}L20 ${h.ryb - 20}L20 ${h.ryb + 3}Q0 ${h.ryb + 15} -20 ${h.ryb + 3}Z`,
		skin.sh,
		0,
	);
	out.push(clipped(neck, skin.lt, 3.4, chinShade));
	const fill = cloth.type === "stripes" || cloth.type === "overalls" ? W : cloth.fill;
	const skinV = shape(p`M-17 ${yn - 11}L0 ${yn + 17}L17 ${yn - 11}Z`, skin.lt, 0);
	switch (cloth.type) {
		case "hoodie":
			out.push(
				shape(
					p`M0 ${yn + 30}C-12 ${yn + 30} -44 ${yn + 26} -52 ${yn + 6}` +
						p`C-58 ${yn - 10} -42 ${yn - 24} -22 ${yn - 20}` +
						p`L-15 ${yn}Q0 ${yn + 10} 15 ${yn}L22 ${yn - 20}` +
						p`C42 ${yn - 24} 58 ${yn - 10} 52 ${yn + 6}` +
						p`C44 ${yn + 26} 12 ${yn + 30} 0 ${yn + 30}Z`,
					fill,
					3.6,
				),
			);
			out.push(
				ink(
					p`M-42 ${yn + 2}Q-32 ${yn + 16} -14 ${yn + 22}M42 ${yn + 2}Q32 ${yn + 16} 14 ${yn + 22}`,
					1.8,
				),
			);
			out.push(
				ink(
					p`M-7 ${yn + 22}Q-9 ${yn + 44} -8 ${yn + 64}M7 ${yn + 22}Q9 ${yn + 40} 9 ${yn + 56}`,
					2.4,
				),
			);
			out.push(
				shape(roundRect(-10.5, yn + 62, 5, 9, 1.5), INK, 0) +
					shape(roundRect(6.5, yn + 54, 5, 9, 1.5), INK, 0),
			);
			break;
		case "shirt":
			out.push(skinV);
			for (const s of [-1, 1]) {
				out.push(
					shape(
						p`M${s * 1} ${yn + 16}L${s * 20} ${yn - 10}` +
							p`Q${s * 28} ${yn + 4} ${s * 34} ${yn + 18}` +
							p`Q${s * 16} ${yn + 22} ${s * 1} ${yn + 16}Z`,
						W,
						3,
					),
				);
			}
			out.push(
				ink(p`M0 ${yn + 17}L0 ${yn + 140}`, 2.2) +
					circle(-0.5, yn + 34, 3.2, W, 2) +
					circle(-0.5, yn + 58, 3.2, W, 2),
			);
			if (k.bowtie) {
				out.push(
					shape(p`M0 ${yn + 12}L-15 ${yn + 3}L-15 ${yn + 21}Z`, k.bowtie, 2.6) +
						shape(p`M0 ${yn + 12}L15 ${yn + 3}L15 ${yn + 21}Z`, k.bowtie, 2.6) +
						circle(0, yn + 12, 4.5, k.bowtie, 2.4),
				);
			}
			break;
		case "puffer":
			out.push(
				shape(
					p`M-29 ${yn - 16}L-31 ${yn + 10}Q0 ${yn + 23} 31 ${yn + 10}` +
						p`L29 ${yn - 16}Q0 ${yn - 6} -29 ${yn - 16}Z`,
					fill,
					3.4,
				),
			);
			out.push(ink(p`M0 ${yn + 17}L0 ${yn + 200}`, 2.6));
			for (let y = yn + 22; y < yn + 140; y += 5) out.push(ink(p`M-2 ${y}L2 ${y}`, 1.3));
			out.push(
				shape(roundRect(-3, yn + 20, 6, 12, 2), W, 2) + circle(0, yn + 35, 2.5, "none", 1.6),
			);
			break;
		case "raincoat":
			out.push(skinV);
			for (const s of [-1, 1]) {
				out.push(
					shape(
						p`M${s * 2} ${yn + 20}L${s * 22} ${yn - 12}` +
							p`Q${s * 38} ${yn - 2} ${s * 46} ${yn + 18}` +
							p`Q${s * 20} ${yn + 30} ${s * 2} ${yn + 20}Z`,
						HA,
						3.2,
					),
				);
			}
			for (const y of [yn + 44, yn + 74]) {
				out.push(
					shape(roundRect(-9, y - 3, 18, 6, 3), W, 2) +
						ink(p`M-12 ${y}L-9 ${y}M9 ${y}L12 ${y}`, 1.6),
				);
			}
			break;
		case "sweater":
			out.push(
				shape(
					p`M-27 ${yn - 9}Q0 ${yn + 30} 27 ${yn - 9}L19 ${yn - 11}Q0 ${yn + 12} -19 ${yn - 11}Z`,
					fill,
					3,
				),
			);
			for (const t of [-0.75, -0.45, -0.15, 0.15, 0.45, 0.75]) {
				out.push(
					ink(
						p`M${t * 21} ${yn - 4 + (1 - t * t) * 9}L${t * 27} ${yn - 1 + (1 - t * t) * 13}`,
						1.4,
					),
				);
			}
			break;
		case "vneck":
			out.push(skinV);
			out.push(
				shape(
					p`M-24 ${yn - 10}L0 ${yn + 28}L24 ${yn - 10}L17 ${yn - 11}L0 ${yn + 16}L-17 ${yn - 11}Z`,
					fill,
					3,
				),
			);
			break;
		default:
			out.push(
				shape(
					p`M-24 ${yn - 6}Q0 ${yn + 22} 24 ${yn - 6}L19 ${yn - 8}Q0 ${yn + 12} -19 ${yn - 8}Z`,
					fill,
					3,
				),
			);
	}
	if (k.scarf) out.push(scarf(yn, k));
	if (k.necklace) {
		out.push(ink(p`M-21 ${yn - 6}Q0 ${yn + 36} 21 ${yn - 6}`, 1.6));
		out.push(
			shape(
				p`M0 ${yn + 13}C-6 ${yn + 13} -6 ${yn + 23} 0 ${yn + 26}` +
					p`C6 ${yn + 23} 6 ${yn + 13} 0 ${yn + 13}Z`,
				DM,
				2,
			) + ink(p`M-4 ${yn + 14}L4 ${yn + 14}`, 2.4),
		);
	}
	for (const [kind, x, y] of k.pins) out.push(pin(kind, x, yn + y));
	return out.join("");
}

// ------------------------------------------------------------------ figures

function drawEars(h, k) {
	const g = faceGeo(h, k);
	let out = "";
	for (const s of [-1, 1]) {
		const x = s * (h.rx - 1);
		out += oval(x, g.ey + 5, 10, 12.5, s < 0 ? k.skin.lt : k.skin.sh, 3.6);
		out += ink(p`M${x + s * 1} ${g.ey}Q${x + s * 5} ${g.ey + 5} ${x + s * 1} ${g.ey + 11}`, 2);
		if (k.earring) {
			const y = g.ey + 17;
			out +=
				k.earring === "hoop"
					? circle(x + s * 1.5, y + 3, 3.6, "none", 2)
					: circle(x + s * 1.5, y, 2.6, INK);
		}
	}
	return out;
}

function drawHead(h, k, shadow = "") {
	const light = oval(-h.rx * 0.11, -h.ry * 0.12, h.rx * 1.0, h.ry * 1.0, k.skin.lt);
	return clipped(headPath(h), k.skin.sh, 4.4, light + shadow);
}

function kid(k) {
	const h = k.h;
	const yn = h.ryb + 6;
	const hair = HAIR[k.hair](h, k.hairFill, k.side, k);
	const hat = k.hat ? HATS[k.hat](h, k) : {};
	const tilt = headTurn(k, h.ryb);
	const hide =
		k.eyewear === "shades" ? [true, true] : k.eyewear === "patch" ? [false, true] : [false, false];
	const head = [
		drawEars(h, k),
		hat.behind ?? "",
		drawHead(h, k, hat.shadow),
		drawFace(h, k, hide),
		eyewear(h, k),
		hair.front ?? "",
		hat.front ?? "",
	].join("");
	return (
		group((hair.back ?? "") + (hat.back ?? ""), tilt) +
		drawTorso(k, yn) +
		drawNeck(k, h, yn) +
		group(hair.mid ?? "", tilt) +
		group(head, tilt)
	);
}

function robot(k) {
	const s = k.side;
	const yn = 58;
	const out = [];
	const body =
		p`M-60 ${yn}L60 ${yn}Q80 ${yn} 84 ${yn + 22}` +
		p`L94 ${yn + 290}L-94 ${yn + 290}L-84 ${yn + 22}` +
		p`Q-80 ${yn} -60 ${yn}Z`;
	let bodyIn = shape(p`M40 ${yn - 10}L120 ${yn - 10}L120 ${yn + 300}L52 ${yn + 300}Z`, DM, 0);
	bodyIn += ink(p`M-72 ${yn + 40}L-76 ${yn + 200}M72 ${yn + 40}L76 ${yn + 200}`, 2.4);
	for (const x of [-70, -50, 50, 70]) bodyIn += circle(x, yn + 12, 2.2, INK);
	out.push(clipped(body, W, 4.2, bodyIn));
	out.push(shape(roundRect(-32, yn + 22, 64, 48, 8), DL, 3.2));
	out.push(
		circle(-17, yn + 37, 6, DD, 2.4) +
			circle(0, yn + 37, 6, W, 2.4) +
			circle(17, yn + 37, 6, INK, 2.4),
	);
	out.push(ink(p`M-22 ${yn + 58}L22 ${yn + 58}`, 2.4) + ink(p`M-22 ${yn + 63}L8 ${yn + 63}`, 2.4));
	for (const y of [44, 50]) out.push(shape(roundRect(-20, y, 40, 8, 3), DM, 2.6));
	const g = { ex: 21, ey: -6 };
	const hd = roundRect(-60, -58, 120, 108, 18);
	let hIn = shape(p`M34 -70L80 -70L80 60L46 60C58 20 52 -30 34 -70Z`, DL, 0);
	hIn += ink("M-50 -40L-50 30", 1.6);
	const head = [];
	for (const side of [-1, 1]) {
		head.push(shape(roundRect(side > 0 ? 56 : -70, -20, 14, 34, 4), DM, 3.2));
		head.push(ink(p`M${side * 63} -12L${side * 63} 6`, 1.8));
	}
	head.push(shape(roundRect(s * 15 - 7, -66, 14, 10, 3), DM, 2.6));
	head.push(ink(p`M${s * 15} -66L${s * 17} -84Q${s * 19} -92 ${s * 32} -97`, 3.4));
	head.push(circle(s * 34, -98, 7, DD, 3));
	head.push(clipped(hd, W, 4.4, hIn));
	head.push(shape(roundRect(-44, -38, 88, 64, 13), INK, 3));
	head.push(ink("M-37 -26l9 -6M-38 -16l3.5 -2.4", 2.4, W));
	const expr = EXPRESSIONS[k.expr];
	[-1, 1].forEach((side, i) => {
		const x = side * g.ex;
		if (expr.eyes[i] === "happy" || expr.eyes[i] === "calm") {
			head.push(ink(p`M${x - 8} ${g.ey + 3}Q${x} ${g.ey - 11} ${x + 8} ${g.ey + 3}`, 4.2, W));
		} else {
			const screenEye = oval(x, g.ey, 7, 9, W) + circle(x + 2, g.ey - 3, 2.6, INK);
			head.push(blinker("open", screenEye, x, g.ey));
		}
	});
	head.push(ink(p`M-9 ${g.ey + 15}Q0 ${g.ey + 23} 9 ${g.ey + 15}`, 3.4, W));
	head.push(ink(p`M-36 ${g.ey + 12}l5 0M31 ${g.ey + 12}l5 0`, 3, W));
	for (const [x, y] of [
		[-50, -48],
		[50, -48],
		[-50, 40],
		[50, 40],
		[0, -50],
	])
		head.push(circle(x, y, 2.4, INK));
	out.push(group(head.join(""), headTurn(k, 50)));
	return out.join("");
}

function frog(k) {
	const yn = 44;
	const out = [drawTorso(k, yn)];
	out.push(
		shape(p`M0 ${yn + 8}L-15 ${yn - 1}L-15 ${yn + 17}Z`, k.bowtie, 2.6) +
			shape(p`M0 ${yn + 8}L15 ${yn - 1}L15 ${yn + 17}Z`, k.bowtie, 2.6) +
			circle(0, yn + 8, 4.5, k.bowtie, 2.4),
	);
	const head = [];
	const expr = EXPRESSIONS[k.expr];
	// eye bulbs sit on the crown; the head outline crosses their lower half
	for (const s of [-1, 1]) {
		const bulb = ellipsePath(s * 31, -38, 23, 22);
		head.push(clipped(bulb, k.skin.sh, 4.4, circle(s * 31 - 5, -42, 21, k.skin.lt)));
	}
	const d =
		p`M-66 4C-68 -22 -50 -36 -30 -32Q0 -26 30 -32` +
		p`C50 -36 68 -22 66 4C64 32 36 50 0 50` +
		p`C-36 50 -64 32 -66 4Z`;
	let inner = oval(-14, -10, 62, 52, k.skin.lt);
	for (const [x, y, r] of [
		[-48, 4, 5.5],
		[50, 10, 6.5],
		[-40, 26, 3.6],
		[44, -12, 3.4],
	]) {
		inner += oval(x, y, r * 1.25, r, DM, 1.6);
	}
	head.push(clipped(d, k.skin.sh, 4.4, inner));
	[-1, 1].forEach((s, i) => {
		const kind = expr.eyes[i] === "calm" ? "happy" : expr.eyes[i];
		const x = s * 31 + k.look;
		head.push(blinker(kind, eye(kind, x, -44, 9.4, 11.4, s), x, -44));
		head.push(circle(s * 6, -14, 2, INK));
		head.push(oval(s * 44, 16, 9.5, 6, DM));
	});
	head.push(ink("M-42 2Q0 34 42 2", 3.4) + ink("M-45 -2Q-43 2 -39 5M45 -2Q43 2 39 5", 2.4));
	if (expr.mouth === "tongue" || expr.mouth === "open" || expr.mouth === "grin") {
		head.push(shape("M-7 18C-8 30 8 30 7 18Z", W, 2.4) + ink("M0 20L0 25", 1.5));
	}
	out.push(group(head.join(""), headTurn(k, 50)));
	return out.join("");
}

function fox(k) {
	const h = { rx: 60, ry: 58, ryb: 54, n: 2, nb: 2 };
	const yn = 60;
	const pts = [
		[-58, -30],
		[-34, -54],
		[0, -60],
		[34, -54],
		[58, -30],
		[63, -4],
		[73, 16, true],
		[58, 21],
		[65, 35, true],
		[46, 40],
		[24, 52],
		[0, 57],
		[-24, 52],
		[-46, 40],
		[-65, 35, true],
		[-58, 21],
		[-73, 16, true],
		[-63, -4],
	];
	const g = faceGeo(h, k);
	const ears = [];
	for (const s of [-1, 1]) {
		const outer = smooth([
			[s * 22, -50],
			[s * 46, -104, true],
			[s * 63, -34],
		]);
		ears.push(
			clipped(
				outer,
				HA,
				4.2,
				shape(
					smooth([
						[s * 30, -52],
						[s * 45, -90, true],
						[s * 55, -42],
					]),
					DD,
					2.4,
				) + shape(p`M${s * 20} -84L${s * 70} -84L${s * 70} -120L${s * 20} -120Z`, INK, 0),
			),
		);
	}
	const top = g.ey - g.eh - 6;
	const mask =
		p`M-90 -6C-56 -10 -40 ${top - 2} -22 ${top}` +
		p`Q-6 ${top + 2} 0 ${g.ey + 8}Q6 ${top + 2} 22 ${top}` +
		p`C40 ${top - 2} 56 -10 90 -6L90 90L-90 90Z`;
	let inner =
		shape(p`M30 -80L90 -80L90 0L52 -6C50 -40 44 -60 30 -80Z`, CH, 0) + shape(mask, W, 2.6);
	inner += shape(p`M30 ${top}C52 ${top + 10} 62 20 70 40L90 40L90 ${top}Z`, DL, 0);
	const head = [ears.join(""), clipped(smooth(pts), HA, 4.4, inner)];
	head.push(ink("M-60 24l8 -2M-62 32l7 0M60 24l-8 -2M62 32l-7 0", 1.6));
	const expr = EXPRESSIONS[k.expr];
	for (const [i, s] of [-1, 1].entries()) {
		const x = s * g.ex + g.lx;
		head.push(blinker(expr.eyes[i], eye(expr.eyes[i], x, g.ey, g.er, g.eh, s), x, g.ey));
	}
	const ny = g.ey + g.eh + 4;
	head.push(
		shape(p`M-7 ${ny}Q0 ${ny - 3} 7 ${ny}Q4 ${ny + 7} 0 ${ny + 8}Q-4 ${ny + 7} -7 ${ny}Z`, INK, 0),
	);
	head.push(oval(-2.4, ny + 0.5, 2, 1.2, W));
	head.push(
		ink(
			p`M0 ${ny + 8}L0 ${ny + 11}M-8 ${ny + 13}` +
				p`Q-4 ${ny + 17} 0 ${ny + 11}Q4 ${ny + 17} 8 ${ny + 13}`,
			2.4,
		),
	);
	head.push(oval(-g.ex - 11, g.my - 2, 8, 5, DL) + oval(g.ex + 11, g.my - 2, 8, 5, DL));
	const torso =
		drawTorso(k, yn) +
		clipped(p`M-13 40L-13.5 ${yn + 2}Q0 ${yn + 10} 13.5 ${yn + 2}L13 40Z`, HA, 3.4, "") +
		scarf(yn, k);
	return torso + group(head.join(""), headTurn(k, h.ryb));
}

function shroom(k) {
	const h = { rx: 50, ry: 48, ryb: 46, n: 2, nb: 2.2 };
	const yn = h.ryb + 6;
	const out = [drawTorso(k, yn), drawNeck({ ...k, cloth: { type: "tee", fill: W } }, h, yn)];
	for (let i = 0; i < 7; i++) {
		const a = -160 + i * 23;
		const rad = (a * Math.PI) / 180;
		const x = Math.cos(rad) * 30;
		const y = yn + 8 + Math.sin(rad) * -10;
		out.push(
			group(
				shape("M0 0C-10 8 -10 26 0 34C10 26 10 8 0 0Z", i % 2 ? DM : HA, 2.6) +
					ink("M0 4L0 28", 1.4),
				`translate(${f(x)} ${f(y - 4)}) rotate(${f(a + 90)})`,
			),
		);
	}
	const { rx, ry } = h;
	const c0 = -ry * 0.42;
	const cap =
		p`M${-(rx + 40)} ${c0}C${-(rx + 44)} ${-ry - 34} ${-rx * 0.62} ${-ry - 58} 0 ${-ry - 58}` +
		p`C${rx * 0.62} ${-ry - 58} ${rx + 44} ${-ry - 34} ${rx + 40} ${c0}` +
		p`C${rx * 0.7} ${c0 + 14} ${-rx * 0.7} ${c0 + 14} ${-(rx + 40)} ${c0}Z`;
	let capIn = shape(
		p`M${rx * 0.4} ${-ry - 70}` +
			p`C${rx + 10} ${-ry - 40} ${rx + 30} ${-ry * 0.6} ${rx + 20} ${c0 + 10}` +
			p`L${rx + 60} ${c0 + 10}L${rx + 60} ${-ry - 70}Z`,
		DD,
		0,
	);
	for (const [x, y, r] of [
		[-rx * 0.9, -ry * 0.75, 9],
		[-rx * 0.25, -ry - 34, 11],
		[rx * 0.42, -ry - 22, 8],
		[rx + 18, -ry * 0.62, 7],
		[-rx * 0.35, -ry * 0.62, 6],
		[rx * 0.2, -ry * 0.6, 5],
	]) {
		capIn += circle(x, y, r, W, 2.2);
	}
	capIn += ink(
		p`M${-(rx + 36)} ${c0 - 3}C${-rx * 0.7} ${c0 + 9} ${rx * 0.7} ${c0 + 9} ${rx + 36} ${c0 - 3}`,
		1.6,
	);
	const head = [
		drawHead(
			h,
			k,
			shape(
				p`M-80 ${c0 - 20}L80 ${c0 - 20}L80 ${c0 + 12}Q0 ${c0 + 26} -80 ${c0 + 12}Z`,
				k.skin.sh,
				0,
			),
		),
		drawFace(h, k),
		shape(p`M-2 ${-ry - 56}Q-4 ${-ry - 70} 2 ${-ry - 76}`, "none", 2.6),
		shape(
			p`M2 ${-ry - 76}C10 ${-ry - 86} 24 ${-ry - 82} 26 ${-ry - 72}` +
				p`C16 ${-ry - 66} 6 ${-ry - 68} 2 ${-ry - 76}Z`,
			DM,
			2.4,
		),
		clipped(cap, DM, 4.4, capIn),
	];
	out.push(group(head.join(""), headTurn(k, h.ryb)));
	return out.join("");
}

// ------------------------------------------------------------------ casting

const SKINS = [
	{ lt: W, sh: DL, tone: 0 },
	{ lt: DL, sh: DM, tone: 1 },
	{ lt: DT, sh: DM, tone: 2 },
	{ lt: DM, sh: DD, tone: 3 },
];
const HAIR_FILLS = [
	[INK, 36],
	[DD, 17],
	[DM, 12],
	[HA, 15],
	[W, 20],
];
const HAT_BLOCKS = {
	beanie: ["bun", "puffs"],
	capBack: ["bun", "puffs", "afro"],
	helmet: ["bun", "puffs", "afro", "spiky"],
	flowers: [],
	headphones: ["bun", "puffs"],
	bandana: ["bun", "puffs", "afro"],
	goggles: ["puffs"],
	hood: ["afro", "puffs", "bun", "ponytail"],
	bucket: ["bun", "puffs", "spiky"],
	bow: ["buzz", "spiky"],
	crown: ["bun", "puffs"],
	bearHood: ["afro", "puffs", "bun", "ponytail"],
};
const TALL = new Set(["beanie", "hood", "crown", "flowers", "bow", "helmet", "bucket", "bearHood"]);
const TALL_HAIR = new Set(["afro", "puffs", "bun", "spiky"]);

function makeHead(kind) {
	if (kind === "oval") {
		const rx = between(53, 56);
		return { rx, ry: rx * between(1.1, 1.15), ryb: rx * between(1.0, 1.05), n: 2, nb: 2.1 };
	}
	if (kind === "square") {
		const rx = between(56, 59);
		return { rx, ry: rx * 0.98, ryb: rx * 0.92, n: 2.7, nb: 2.6 };
	}
	if (kind === "chubby") {
		const rx = between(58, 61);
		return { rx, ry: rx * 0.96, ryb: rx * 0.9, n: 2.1, nb: 2.8 };
	}
	const r = between(57, 60);
	return { rx: r, ry: r * between(0.98, 1.02), ryb: r * between(0.9, 0.95), n: 2, nb: 2.2 };
}

const BUNDLE = ["hat", "hair", "hairFill", "hatFill", "hatBand", "side", "tieFill"];

function swapBundle(a, b) {
	for (const key of BUNDLE) [a[key], b[key]] = [b[key], a[key]];
}

function castCrowd() {
	// Separate random streams, so changing one casting rule never reshuffles the rest.
	plan = mulberry32(SEED);
	const slots = [];
	ROWS.forEach((row, r) => {
		for (let x = r % 2 ? 53 : -30; x < 1670; x += STEP) {
			slots.push({
				r,
				x: x + between(-12, 12),
				y: row.y + between(-7, 7),
				s: row.s * between(0.97, 1.03),
			});
		}
	});

	plan = mulberry32(SEED + 1);
	const creatures = shuffle([
		"robot",
		"robot",
		"frog",
		"fox",
		"fox",
		"bearKid",
		"bearKid",
		"shroom",
	]);
	const chosen = [];
	while (chosen.length < creatures.length) {
		const i = Math.floor(plan() * slots.length);
		const apart = chosen.every((j) => {
			const dr = Math.abs(slots[i].r - slots[j].r);
			return dr > 1 || Math.abs(slots[i].x - slots[j].x) > STEP * 2.2;
		});
		const topRow = chosen.filter((j) => slots[j].r === 0).length;
		const inside = slots[i].x > 110 && slots[i].x < 1490;
		if (apart && inside && !(slots[i].r === 0 && topRow >= 2)) chosen.push(i);
	}
	for (const k of slots) k.kind = "kid";
	chosen.forEach((i, n) => {
		slots[i].kind = creatures[n];
	});
	const kids = slots.filter((k) => k.kind === "kid");

	plan = mulberry32(SEED + 2);
	const skins = deck(
		SKINS.map((s) => [s, 1]),
		slots.length,
	);
	const hats = deck(
		[
			["beanie", 3],
			["capBack", 3],
			["helmet", 3],
			["flowers", 3],
			["headphones", 3],
			["bandana", 2],
			["goggles", 3],
			["hood", 2],
			["bucket", 3],
			["bow", 3],
			["crown", 3],
			[null, 24],
		],
		kids.length,
	);
	const hairs = deck(
		Object.keys(HAIR).map((k) => [k, k === "buzz" ? 0.5 : 1]),
		slots.length,
	);
	const exprs = deck(
		Object.keys(EXPRESSIONS).map((k) => [k, 1]),
		slots.length,
	);
	const wear = deck(
		[
			["glasses", 8],
			["shades", 3],
			["patch", 2],
			[null, 50],
		],
		slots.length,
	);
	const cloths = deck(
		["tee", "stripes", "hoodie", "shirt", "overalls", "sweater", "puffer", "raincoat", "vneck"].map(
			(c) => [c, 1],
		),
		slots.length,
	);
	const prints = ["star", "heart", "bolt", "planet", "moon", "rainbow", "smiley"];
	slots.forEach((k, i) => {
		plan = mulberry32(SEED * 7 + i * 104729);
		k.side = chance(0.5) ? 1 : -1;
		k.tilt = between(-7, 7);
		k.eye = between(7.8, 9.2);
		k.look = pick([-2.5, 0, 0, 2.5]);
		k.skin = skins[i];
		k.expr = exprs[i];
		k.hair = hairs[i];
		k.hairFill = pick(HAIR_FILLS.flatMap(([v, w]) => Array(w).fill(v)));
		if (k.skin.tone === 3 && k.hairFill === DM) k.hairFill = INK;
		k.eyewear = wear[i];
		k.shadeStyle = chance(0.4) ? "heart" : "round";
		k.tw = between(84, 92);
		const type = cloths[i];
		const fill = type === "raincoat" ? HA : pick([W, W, W, W, DL, DL, HA, DM, DD]);
		const print = type === "tee" || type === "stripes" ? pick(prints) : null;
		k.cloth = { type, fill, bib: pick([DM, HA, DD]), print };
		k.printX = between(-10, 10);
		k.cheeks = chance(0.75);
		k.freckles = chance(0.3);
		k.bandAid = chance(0.1) ? pick([-1, 1]) : 0;
		k.earring = chance(0.18) ? pick(["hoop", "stud"]) : null;
		k.scarf = chance(0.14) && type !== "hoodie" && type !== "puffer";
		k.scarfFill = pick([W, DL, HA]);
		k.straps = chance(0.16) && type !== "overalls" && type !== "raincoat";
		k.necklace = chance(0.07) && type === "tee" && !k.scarf;
		k.bowtie = type === "shirt" && chance(0.5) ? pick([DD, PO, INK]) : null;
		k.tieFill = pick([DD, W]);
		k.pins = [];
		if (chance(0.3) && !k.scarf)
			k.pins.push([pick(["star", "heart", "dark", "bang"]), k.side * 28, 34]);
		if (chance(0.12) && !k.scarf) k.pins.push([pick(["star", "heart"]), k.side * -26, 50]);
		k.hatFill = pick([W, W, DL, HA, DM]);
		k.hatBand = chance(0.4);
		k.h = makeHead(pick(["round", "round", "oval", "square", "chubby"]));
		k.hat = k.kind === "kid" ? hats[kids.indexOf(k)] : null;
		if (k.kind === "bearKid") {
			k.hat = "bearHood";
			k.hatFill = pick([DL, HA, DM]);
			k.cloth = { type: "hoodie", fill: k.hatFill };
		}
		if (k.kind === "frog") {
			k.expr = pick(["smile", "grin", "tongue", "gappy"]);
			k.skin = SKINS[1];
			k.cloth = { type: "stripes", fill: W, print: null };
			k.bowtie = pick([DD, PO]);
		}
		if (k.kind === "fox") k.cloth = { type: "sweater", fill: pick([W, DL]) };
		if (k.kind === "shroom") {
			k.skin = pick([SKINS[0], SKINS[1]]);
			k.cloth = { type: "tee", fill: W };
			k.pins = [];
			k.scarf = false;
		}
		if (k.kind !== "kid" && k.kind !== "bearKid") {
			k.eyewear = null;
			k.straps = false;
		}
		if (k.hat === "flowers") k.hatFill = pick([DM, INK]);
		if (k.hat === "bow" || k.hat === "bandana") k.hatFill = pick([PO, DD, INK]);
		if (k.hat === "helmet") k.hatFill = DD;
		if (k.hat === "hood") k.hatFill = pick([DM, HA, DD]);
		if (k.hat === "headphones") k.hatFill = pick([DM, DD]);
		if (k.eyewear === "shades" && ["calm", "laugh", "beam", "wink"].includes(k.expr))
			k.expr = "grin";
		while (k.hat && HAT_BLOCKS[k.hat].includes(k.hair)) k.hair = pick(Object.keys(HAIR));
	});

	plan = mulberry32(SEED + 3);
	// No identical hat or hairstyle side by side. The back row makes the silhouette against
	// the black band, so there every hat and hairstyle is different and every head carries
	// something tall (a hat, big hair or ears).
	const isTall = (k) => TALL.has(k.hat) || TALL_HAIR.has(k.hair);
	const top = kids.filter((k) => k.r === 0);
	const lower = kids.filter((k) => k.r > 1);
	const same = (a, b) => (a.hat && a.hat === b.hat) || a.hair === b.hair;
	const clash = (k) => {
		const row = slots.filter((o) => o !== k && o.r === k.r && o.kind === "kid");
		if (row.some((o) => Math.abs(o.x - k.x) < STEP * 1.5 && same(k, o))) return true;
		return k.r === 0 && (!isTall(k) || top.some((o) => o !== k && same(k, o)));
	};
	for (let pass = 0; pass < 3; pass++) {
		for (const k of kids) {
			for (let tries = 0; tries < 80 && clash(k); tries++) {
				const o = lower[Math.floor(plan() * lower.length)];
				if (o === k) continue;
				swapBundle(k, o);
				if (clash(k) || clash(o)) swapBundle(k, o);
			}
		}
	}
	// Spread the eyewear out: no two matching pairs of glasses near each other.
	const near = (a, b) => a !== b && Math.abs(a.r - b.r) <= 1 && Math.abs(a.x - b.x) < STEP * 1.6;
	const crowded = (k) => k.eyewear && kids.some((o) => near(k, o) && o.eyewear === k.eyewear);
	for (const k of kids) {
		for (let tries = 0; tries < 60 && crowded(k); tries++) {
			const o = kids[Math.floor(plan() * kids.length)];
			if (o.eyewear || near(k, o)) continue;
			[k.eyewear, o.eyewear] = [o.eyewear, k.eyewear];
			if (crowded(o)) [k.eyewear, o.eyewear] = [o.eyewear, k.eyewear];
		}
	}
	for (const k of kids) {
		if (k.eyewear === "shades" && ["calm", "laugh", "beam", "wink"].includes(k.expr))
			k.expr = "grin";
	}
	return slots;
}

// ------------------------------------------------------------------ assembly

/** An opaque halftone or hatch tile: white backing plus `mark`, optionally turned 45 degrees. */
function tile(id, size, mark, turned = true) {
	const turn = turned ? ' patternTransform="rotate(45)"' : "";
	return (
		`<pattern id="${id}" width="${size}" height="${size}" patternUnits="userSpaceOnUse"${turn}>` +
		`<rect width="${size}" height="${size}" fill="#fff"/>${mark}</pattern>`
	);
}

const dot = (c, r) => `<circle cx="${c}" cy="${c}" r="${r}" fill="#111"/>`;
const PETALS = [
	[0, -6],
	[5.7, -1.9],
	[3.5, 4.9],
	[-3.5, 4.9],
	[-5.7, -1.9],
];

const INK_WOBBLE = [
	'<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>',
	'<feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" ' +
		'yChannelSelector="G"/>',
];

const DEFS = [
	"<defs>",
	'<filter id="ink" x="-3%" y="-3%" width="106%" height="106%">',
	...INK_WOBBLE,
	"</filter>",
	// White outline round the whole crowd, so the back row's ink edge shows on the black band.
	'<filter id="halo" x="-3%" y="-6%" width="106%" height="112%">',
	'<feMorphology in="SourceAlpha" operator="dilate" radius="3.2" result="d"/>',
	'<feFlood flood-color="#fff" result="w"/>',
	'<feComposite in="w" in2="d" operator="in" result="wd"/>',
	'<feMerge><feMergeNode in="wd"/><feMergeNode in="SourceGraphic"/></feMerge>',
	"</filter>",
	tile("dots-light", 7, dot(3.5, 1.05), false),
	tile("dots-tan", 6, dot(3, 1.25)),
	tile("dots-mid", 6, dot(3, 1.55)),
	tile("dots-dark", 5, dot(2.5, 1.95)),
	tile("hatch", 6, '<line x1="0" y1="0" x2="0" y2="6" stroke="#111" stroke-width="1.4"/>'),
	tile("crosshatch", 7, '<path d="M0 0V7M0 0H7" stroke="#111" stroke-width="1.3"/>'),
	tile("polka", 12, dot(3, 2.2) + dot(9, 2.2), false),
	'<g id="flower" stroke="#111" stroke-width="2">' +
		PETALS.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5.4" fill="#fff"/>`).join("") +
		'<circle cx="0" cy="0" r="3.6" fill="url(#dots-dark)"/></g>',
	"</defs>",
].join("\n");

const DRAW = { kid, bearKid: kid, robot, frog, fox, shroom };

function describe(k) {
	if (k.kind !== "kid") return k.kind;
	return [k.hat ?? "bare", k.hair, k.eyewear, k.expr].filter(Boolean).join(", ");
}

// ------------------------------------------------------------------ motion layer

// The open eyes again, alone on a transparent sheet laid over the base. A pivot on each face's
// eye line, tilted with the head, squashes its eyes shut for a blink. A third of the faces also
// glance now and then, inside the `sf-look` group that the page moves to follow the cursor. The
// eyes are drawn in root space under their own small ink filter, so at rest their wobble is
// exactly the base's.

const seconds = (ms) => String(+(ms / 1000).toFixed(2));
const pct = (ms, dur) => `${+((ms / dur) * 100).toFixed(2)}%`;
const nudge = ([x, y]) => (x || y ? `translate(${f(x)}px,${f(y)}px)` : "none");

/** A loop that rests open, then blinks at each start (ms): 70 ms shut, 60 held, 100 open. */
function blinkKeys(name, dur, starts) {
	const open = starts.flatMap((t) => [pct(t, dur), pct(t + 230, dur)]);
	const shut = starts.flatMap((t) => [pct(t + 70, dur), pct(t + 130, dur)]);
	const rest = ["0%", ...open, "100%"].join(",");
	return `@keyframes ${name}{${rest}{transform:none}${shut.join(",")}{transform:scaleY(.1)}}`;
}

/** A loop that rests centred and passes through each [ms, [dx, dy]] stop in turn. */
function glanceKeys(name, dur, stops) {
	const steps = stops.map(([t, at]) => `${pct(t, dur)}{transform:${nudge(at)}}`);
	return `@keyframes ${name}{0%,100%{transform:none}${steps.join("")}}`;
}

/** Head-space point (x, y) of figure `k`, tilted `tilt` degrees about (0, cy), in root space. */
function rootPoint(k, tilt, cy, x, y) {
	const a = (tilt * Math.PI) / 180;
	const s = Number(k.s.toFixed(3));
	const dx = x * Math.cos(a) - (y - cy) * Math.sin(a);
	const dy = cy + x * Math.sin(a) + (y - cy) * Math.cos(a);
	return [Number(f(k.x)) + s * dx, Number(f(k.y)) + s * dy];
}

/** Wraps root-space `body` in a pivot on root point (x, y), turned `tilt` degrees. */
function pivot(cls, [x, y], tilt, body) {
	return (
		`<g transform="translate(${f(x)} ${f(y)}) rotate(${f(tilt)})"><g class="${cls}">` +
		`<g transform="rotate(${f(-tilt)}) translate(${f(-x)} ${f(-y)})">${body}</g></g></g>`
	);
}

function motionLayer(faces, crowd) {
	for (const face of faces) {
		const { k, eyes, tilt, cy } = face;
		const x = eyes.reduce((sum, e) => sum + e.x, 0) / eyes.length;
		face.pivot = rootPoint(k, tilt, cy, x, eyes[0].y);
	}
	// Glancers: a third of each row, one in each band across the picture, among faces whose eyes
	// are inside it with both eyes open (or one beside an eye patch).
	plan = mulberry32(SEED + 4);
	const lookers = new Set();
	const canLook = ({ k, eyes, pivot: [x] }) =>
		k.kind !== "robot" && (eyes.length === 2 || k.eyewear === "patch") && x > 40 && x < 1560;
	ROWS.forEach((_, r) => {
		const quota = Math.round(crowd.filter((k) => k.r === r).length / 3);
		for (let band = 0; band < quota; band++) {
			const free = faces.filter((face) => face.k.r === r && canLook(face) && !lookers.has(face));
			const inBand = free.filter(
				(face) => Math.floor(((face.pivot[0] - 40) / 1520) * quota) === band,
			);
			const pool = inBand.length ? inBand : free;
			if (pool.length) lookers.add(pick(pool));
		}
	});
	const rules = [];
	const keys = [];
	const parts = faces.map((face, n) => {
		const { k, eyes, tilt, cy } = face;
		plan = mulberry32(SEED * 11 + n * 7907);
		const dur = Math.round(between(4, 9) * 100) * 10;
		const starts = chance(0.22) ? [dur / 2, dur / 2 + 370] : [dur / 2];
		const delay = Math.round(between(0, dur) / 10) * 10;
		const timing = `${seconds(dur)}s ease-in-out -${seconds(delay)}s infinite`;
		rules.push(`.cr-b${n}{animation:cr-b${n} ${timing}}`);
		keys.push(blinkKeys(`cr-b${n}`, dur, starts));
		const blink = `cr-blink cr-b${n}`;
		const frame = `${face.at} rotate(${f(tilt)} 0 ${f(cy)})`;
		// Each eye's first shape is the eyeball. Its catch-lights (or a screen eye's pupil) squash
		// a second time inside it, so a shut eye reads as one solid line.
		const cut = eyes.map(({ markup }) => markup.indexOf("/>") + 2);
		const balls = eyes.map(({ markup }, i) => markup.slice(0, cut[i])).join("");
		const lights = eyes.map(({ markup }, i) => markup.slice(cut[i])).join("");
		const inner = pivot(blink, face.pivot, tilt, `<g transform="${frame}">${lights}</g>`);
		let part = `<g filter="url(#ink)"><g transform="${frame}">${balls}</g>${inner}</g>`;
		if (lookers.has(face)) {
			// Solid ink eyes shift a little within the face; glasses leave less room above and below.
			const reach = (k.kind === "frog" ? 4 : k.eyewear === "glasses" ? 2.6 : 3.4) * k.s;
			const look = Number(f(reach));
			const glance = Math.round(between(6, 9) * 100) * 10;
			const side = chance(0.5) ? 1 : -1;
			const first = [side * look * between(0.85, 1), look * between(-0.3, 0.25)];
			let t = Math.round(between(0.08, 0.3) * glance);
			const stops = [[t, [0, 0]]];
			const hold = (ms, at) => {
				stops.push([(t += 380), at], [(t += ms), at]);
			};
			hold(between(1000, 1700), first);
			if (chance(0.3)) {
				hold(between(600, 900), [-first[0] * between(0.7, 0.95), look * between(-0.25, 0.25)]);
			}
			stops.push([t + 420, [0, 0]]);
			const lag = Math.round(between(0, glance) / 10) * 10;
			rules.push(
				`.cr-g${n}{animation:cr-g${n} ${seconds(glance)}s cubic-bezier(.45,0,.55,1) ` +
					`-${seconds(lag)}s infinite}`,
			);
			keys.push(glanceKeys(`cr-g${n}`, glance, stops));
			part = `<g class="sf-look" data-look="${look}"><g class="cr-glance cr-g${n}">${part}</g></g>`;
		}
		return `<!-- ${describe(k)} -->${pivot(blink, face.pivot, tilt, part)}`;
	});
	return [
		'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1100" width="1600" height="1100" ' +
			'aria-hidden="true">',
		"<defs>",
		'<filter id="ink" x="-30%" y="-30%" width="160%" height="160%">',
		...INK_WOBBLE,
		"</filter>",
		"</defs>",
		"<style>",
		".cr-blink{transform-origin:0 0}",
		...rules,
		...keys,
		"@media (prefers-reduced-motion: reduce) {",
		".cr-blink,.cr-glance{animation:none!important}",
		"}",
		"</style>",
		...parts,
		"</svg>",
		"",
	].join("\n");
}

function build() {
	const crowd = castCrowd();
	const faces = [];
	const rows = ROWS.map((_, r) => {
		const figures = crowd
			.map((k, i) => [k, i])
			.filter(([k]) => k.r === r)
			.map(([k, i]) => {
				jit = mulberry32(SEED + i * 7919);
				figure = { eyes: [], tilt: 0, cy: 0 };
				const body = DRAW[k.kind](k);
				const at = `translate(${f(k.x)} ${f(k.y)}) scale(${k.s.toFixed(3)})`;
				const { eyes } = figure;
				if (eyes.length) faces.push({ ...figure, k, at });
				// [still, base]: the base leaves out every eye that moves
				return [true, false].map((open) => {
					const drawn = body.replace(EYE_TOKEN, (_, n) => (open ? eyes[n].markup : ""));
					return `<!-- ${describe(k)} --><g transform="${at}">${drawn}</g>`;
				});
			});
		return [0, 1].map(
			(j) => `<!-- row ${r + 1} -->\n<g>${figures.map((g) => g[j]).join("\n")}</g>`,
		);
	});
	// Paper behind every row below the back row's shoulders, so no black shows through.
	const top = ROWS[0];
	const underTop = Math.round(top.y + top.s * 128);
	const page = (j) =>
		[
			'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1100" width="1600" ' +
				'height="1100" role="img">',
			"<title>A dense, cheerful crowd of original Storyfolk kids and creatures in hats, hoods, " +
				"glasses and headphones, with two robots, two foxes, a frog, bear-hooded kids and a " +
				"mushroom sprite peeking out among them</title>",
			DEFS,
			`<rect x="-40" y="${underTop}" width="1680" height="${1140 - underTop}" fill="#fff"/>`,
			'<g filter="url(#halo)">' +
				'<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">',
			rows.map((row) => row[j]).join("\n"),
			"</g></g>",
			"</svg>",
			"",
		].join("\n");
	return { still: page(0), base: page(1), motion: motionLayer(faces, crowd) };
}

const out = build();
for (const [path, svg] of [
	[OUT, out.still],
	[OUT_BASE, out.base],
	[OUT_MOTION, out.motion],
]) {
	writeFileSync(path, svg);
	console.log(`wrote ${path} (${(svg.length / 1024).toFixed(0)} KB)`);
}
