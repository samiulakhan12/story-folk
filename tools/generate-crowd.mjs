// Storyfolk crowd band: a dense crowd of original kid and creature busts for the black
// "staycurious" band. A seeded PRNG picks every part, so the output is stable from run to run.
// Run from any directory: node tools/generate-crowd.mjs. One run writes three files:
//   assets/crowd.svg         the complete still (motion off, no-JS fallback, reference)
//   assets/crowd-base.svg    the still minus every head, which leaves the shoulders and collars
//   assets/crowd-motion.svg  every head again, which tilt, nod and bounce while their faces
//                            blink, glance, squeeze and laugh and their hats and trinkets wiggle;
//                            base + motion at rest reproduce the still

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

// ------------------------------------------------------------------ drawing passes

// Every figure is drawn up to three times from the same seed, so its shapes come out identical:
// once for the still (and the base), once for the motion layer, where MOTION wraps each moving
// part in its animated group and adds the motion-only shapes (glints, notes, sparkles), and once
// more with SIL set for the heads that meet the black band, which turns every shape into a bare
// white silhouette for their white outline.
let MOTION = false;
let SIL = false;

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

/** Fill and stroke attributes; a silhouette paints whatever is drawn in plain white. */
function paint(fill, sw, color = INK) {
	const stroke = sw ? ` stroke="${SIL ? W : color}" stroke-width="${f(sw)}"` : "";
	return ` fill="${SIL && fill !== "none" ? W : fill}"${stroke}`;
}

function shape(d, fill = W, sw = 4.2) {
	return `<path d="${d}"${paint(fill, sw)}/>`;
}

/** A bare line. A silhouette leaves lines out: they sit inside the shapes that it fills. */
function ink(d, sw = 2.6, color = INK) {
	if (SIL) return "";
	return `<path d="${d}"${paint("none", sw, color)}/>`;
}

function dashed(d, sw = 1.4) {
	if (SIL) return "";
	const stroke = `stroke="${INK}" stroke-width="${f(sw)}" stroke-dasharray="3 3.5"`;
	return `<path d="${d}" fill="none" ${stroke}/>`;
}

function circle(cx, cy, r, fill = W, sw = 0) {
	return `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(r)}"${paint(fill, sw)}/>`;
}

function oval(cx, cy, rx, ry, fill = W, sw = 0, rot = 0) {
	const turn = rot ? ` transform="rotate(${f(rot)} ${f(cx)} ${f(cy)})"` : "";
	const at = `cx="${f(cx)}" cy="${f(cy)}" rx="${f(rx)}" ry="${f(ry)}"`;
	return `<ellipse ${at}${paint(fill, sw)}${turn}/>`;
}

function group(body, transform) {
	return body ? `<g transform="${transform}">${body}</g>` : "";
}

let uid = 0;

/** Filled shape whose inner shading is clipped to it, outlined last (path data written once). */
function clipped(d, fill, sw, inner, evenodd = false) {
	if (SIL) return `<path d="${d}"${evenodd ? ' fill-rule="evenodd"' : ""}${paint(fill, sw)}/>`;
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

// ------------------------------------------------------------------ moving parts

// While a figure is drawn, `figure` holds its number in the crowd, its head's tilt about the
// neck point (0, cy) and, in the motion pass, the open eyes its face has drawn so far.
let figure = { n: 0, eyes: [], tilt: 0, cy: 0 };
const OPEN_EYES = new Set(["open", "wide"]);

/** An eye centred on (x, y) in head space; in the motion pass open ones are kept for `eyePair`. */
function blinker(kind, markup, x, y) {
	if (!MOTION || !OPEN_EYES.has(kind)) return markup;
	figure.eyes.push({ markup, x, y });
	return "";
}

/** The head's tilt about its neck point (0, cy), remembered for the head's own pivot. */
function headTurn(k, cy) {
	figure.tilt = Number(f(k.tilt));
	figure.cy = Number(f(cy));
	return `rotate(${f(k.tilt)} 0 ${f(cy)})`;
}

// Every animated group gets a family class (for the shared rules) and its own class, named after
// its figure, whose keyframes and timing are made once from a PRNG seeded by that name. Poses are
// kept too, so the motion layer can work out how far each part can reach.
const ANIMS = new Map();

function seedOf(name) {
	let h = SEED;
	for (const c of name) h = Math.imul(h ^ c.charCodeAt(0), 2654435761) >>> 0;
	return h;
}

/** A pose: translate (x, y), then rotate `r` degrees, then scale (sx, sy), about the pivot. */
const P = (x = 0, y = 0, r = 0, sx = 1, sy = sx) => ({ x, y, r, sx, sy });
const REST = P();
const num = (v) => String(+v.toFixed(2));

function poseCss(p, fns) {
	if (p === REST) return "none";
	const out = [];
	const px = (v) => (num(v) === "0" ? "0" : `${num(v)}px`);
	if (fns.includes("t")) out.push(`translate(${px(p.x)},${px(p.y)})`);
	if (fns.includes("r")) out.push(`rotate(${num(p.r)}deg)`);
	if (fns.includes("s")) out.push(`scale(${num(p.sx)},${num(p.sy)})`);
	return out.join(" ");
}

/**
 * Keyframes for one loop of `dur` ms that rests at REST and passes through `stops`, each
 * [ms, pose, { o: opacity, ease: timing into the next stop }]. `fns` lists the transform
 * functions every pose writes (t, r, s), so the browser interpolates them one by one; an empty
 * `fns` animates opacity alone. `rest` is the opacity at rest when opacity is animated too.
 */
function loopKeys(name, dur, stops, fns, rest) {
	const fade = rest !== undefined;
	const all = [[0, REST, { o: rest }], ...stops];
	if (all[all.length - 1][0] < dur) all.push([dur, REST, { o: rest }]);
	// While a part is invisible it jumps to its next pose at once and holds it, instead of
	// drifting there unseen: a change the eye can't see still costs a redraw, and outside the
	// part's turn of the clock. The jump comes right after an event, or right before the first.
	for (let i = all.length - 2; fade && i >= 0; i--) {
		const [[ms, pose, opt = {}], [next, to, nopt = {}]] = [all[i], all[i + 1]];
		const hidden = (opt.o ?? rest) === 0 && (nopt.o ?? rest) === 0;
		if (!hidden || pose === to || next - ms <= 20) continue;
		all.splice(i + 1, 0, ms > 0 ? [ms + 10, to, { o: 0 }] : [next - 10, pose, { o: 0 }]);
	}
	const blocks = new Map();
	for (const [ms, pose, opt = {}] of all) {
		const decl = [];
		if (fns) decl.push(`transform:${poseCss(pose, fns)}`);
		if (fade) decl.push(`opacity:${opt.o ?? rest}`);
		if (opt.ease) decl.push(`animation-timing-function:${opt.ease}`);
		const body = decl.join(";");
		const at = `${+((ms / dur) * 100).toFixed(2)}%`;
		blocks.set(body, [...(blocks.get(body) ?? []), at]);
	}
	const css = [...blocks].map(([body, at]) => `${at.join(",")}{${body}}`).join("");
	return `@keyframes ${name}{${css}}`;
}

const SPRING = "cubic-bezier(.34,1.56,.64,1)";
const SMOOTH = "cubic-bezier(.45,0,.55,1)";

/**
 * Registers the animation `cls` once. `make()`, with `plan` seeded from the name, returns
 * { dur, stops, fns, rest, ease, lag, keys, reaches }: the loop in ms, its stops (see loopKeys),
 * how far into the loop it starts (random unless `lag` is given), to share another animation's
 * keyframes, their name in `keys`, and any poses it never plays but can be seen in (`reaches`).
 * The rule, keyframes and poses are kept.
 */
function register(cls, family, make) {
	if (ANIMS.has(cls)) return;
	plan = mulberry32(seedOf(cls));
	const a = make();
	const delay = a.lag ?? Math.round(between(0, a.dur) / 10) * 10;
	const name = a.keys ?? cls;
	const rule =
		`.${cls}{animation:${name} ${seconds(a.dur)}s ${a.ease ?? "ease-in-out"} ` +
		`-${seconds(delay)}s infinite}`;
	const keys = a.keys ? "" : loopKeys(cls, a.dur, a.stops, a.fns, a.rest);
	const poses = [REST, ...a.stops.map(([, pose]) => pose), ...(a.reaches ?? [])];
	ANIMS.set(cls, { family, rule, keys, poses, a, delay });
}

const seconds = (ms) => String(+(ms / 1000).toFixed(2));

/** The pivot pattern: `body` in local units, turned and moved about local point (x, y). */
function pivot(cls, [x, y], body, attrs = "") {
	if (!x && !y) return `<g class="${cls}"${attrs}>${body}</g>`;
	return (
		`<g transform="translate(${f(x)} ${f(y)})"><g class="${cls}"${attrs}>` +
		`<g transform="translate(${f(-x)} ${f(-y)})">${body}</g></g></g>`
	);
}

/**
 * A part that moves on its own: in the motion pass `body` is wrapped in the group that
 * `cr-<code><figure><sub>` animates about head-space point `at`; the still draws `body` as it is.
 */
function moving(code, family, at, body, make, { sub = "", attrs = "" } = {}) {
	if (!MOTION || !body) return body;
	const cls = `cr-${code}${figure.n}${sub}`;
	register(cls, family, make);
	return pivot(`cr-${family} ${cls}`, at, body, attrs);
}

/** A shape that exists only in the motion layer (a glint, a note): invisible at rest. */
function extra(code, family, at, body, make, sub = "") {
	if (!MOTION || SIL) return "";
	return moving(code, family, at, body, make, { sub, attrs: ' opacity="0"' });
}

const SUBS = "abcdefghij";

// ------------------------------------------------------------------ the slice clock

// A software-rendered browser redraws, every frame, one box round everything that changed in it,
// with every layer inside that box. Small changes all over the band made every frame a redraw of
// the whole band, at half the frame rate. So the crowd keeps a clock: the band is cut into
// thirds, and each third changes only in its own turn of every 5.4 s, in the order left, right,
// middle, so each frame redraws about a third of the band. Every change (a head move, a blink, a
// twinkle) fits in one turn of 1.68 s, and every loop is a whole multiple of the clock, so it
// keeps to its turns for ever.
const CLOCK = 5400;
const TURNS = { L: [60, 1740], R: [1860, 3540], M: [3660, 5340] };

const ms10 = (lo, hi) => Math.round(between(lo, hi) / 10) * 10;
const flip = () => (chance(0.5) ? 1 : -1);
const sideOf = (k) => (k.x < 533 ? "L" : k.x > 1067 ? "R" : "M");

/** A loop of about `lo`-`hi` ms: a whole multiple of the clock. */
function loopLen(lo, hi) {
	const fits = [];
	for (let n = 1; n <= 6; n++) {
		if (n * CLOCK >= lo - CLOCK / 4 && n * CLOCK <= hi + CLOCK / 4) fits.push(n * CLOCK);
	}
	return fits.length ? pick(fits) : Math.max(1, Math.round((lo + hi) / 2 / CLOCK)) * CLOCK;
}

/** Whether a change from local time `t` for `len` ms keeps to the figure's turns. */
function inTurn(t, len, dur, lag, side = figure.side) {
	if (t < 20 || t + len > dur - 20) return false;
	const g = (((t - lag) % CLOCK) + CLOCK) % CLOCK;
	return g >= TURNS[side][0] && g + len <= TURNS[side][1];
}

/**
 * Start times, in the loop's own time, for changes `lengths` ms long in a loop of `dur` ms that
 * runs `lag` ms ahead of the clock: one in each equal share of the loop where it can, each
 * inside one of the figure's turns and at least `gap` ms after the one before.
 */
function slots(dur, lag, lengths, gap = 300, side = figure.side) {
	const out = [];
	let from = 20;
	lengths.forEach((len, i) => {
		const any = [];
		const share = [];
		for (let t = from; t + len <= dur - 20; t += 10) {
			if (!inTurn(t, len, dur, lag, side)) continue;
			any.push(t);
			if (t >= (i * dur) / lengths.length && t < ((i + 1) * dur) / lengths.length) share.push(t);
		}
		const pool = share.length ? share : any;
		if (!pool.length) return;
		const t = pool[Math.floor(plan() * pool.length)];
		out.push(t);
		from = t + len + gap;
	});
	return out;
}

/**
 * How far ahead of the clock a `dur` ms loop runs, picked by `u` (0-1) among the lags that keep
 * every one of the figure's turns whole inside the loop, none of them cut by the loop's end.
 */
function alignedLag(dur, u, side = figure.side) {
	const [a, b] = TURNS[side];
	const steps = Math.floor((CLOCK - (b - a) - 40) / 10) + 1; // where a turn may start, in 10s
	const k = Math.floor(u * steps * (dur / CLOCK));
	return ((((20 + (k % steps) * 10 - a) % CLOCK) + CLOCK) % CLOCK) + Math.floor(k / steps) * CLOCK;
}

/** A loop for one figure's part and how far ahead of the clock it runs. */
function cycle(lo, hi) {
	const dur = loopLen(lo, hi);
	return { dur, lag: alignedLag(dur, plan()) };
}

/** One change ([ms, pose] frames) placed in a `lo`-`hi` ms loop, with `extras` (fns, rest...). */
function oneShot(lo, hi, extras, frames) {
	const { dur, lag } = cycle(lo, hi);
	const [t] = slots(dur, lag, [frames[frames.length - 1][0]]);
	if (t === undefined) throw new Error(`no turn fits a ${frames[frames.length - 1][0]} ms change`);
	return { dur, lag, stops: frames.map(([ms, ...rest]) => [t + ms, ...rest]), ...extras };
}

// ------------------------------------------------------------------ faces in motion

const SHUT = P(0, 0, 0, 1, 0.08);

/** When a face blinks: once (sometimes a double blink) every 5.4 s, its own way for each face. */
function blinkPlan() {
	plan = mulberry32(seedOf(`blink${figure.n}`));
	const { dur, lag } = cycle(3500, 7500);
	const double = chance(0.22);
	const n = dur >= 6400 && chance(0.6) ? 2 : 1;
	const starts = slots(dur, lag, Array(n).fill(double ? 680 : 280), 1400);
	return { dur, lag, starts: starts.flatMap((t) => (double ? [t, t + 400] : [t])) };
}

/** A blink: 70 ms to shut, 110 ms held shut, 100 ms to open. */
function blinkMake() {
	const { dur, starts, lag } = blinkPlan();
	const stops = starts.flatMap((t) => [
		[t, REST],
		[t + 70, SHUT],
		[t + 180, SHUT],
		[t + 280, REST],
	]);
	return { dur, stops, fns: "s", lag };
}

/** An idle look to one side (sometimes across to the other), `reach` head units at most. */
function glanceMake(reach) {
	const { dur, lag } = cycle(6000, 9500);
	const side = flip();
	const first = P(side * reach * between(0.85, 1), reach * between(-0.3, 0.25));
	const frames = chance(0.3)
		? [
				[0, REST],
				[360, first],
				[760, first],
				[1180, P(-first.x * between(0.7, 0.95), reach * between(-0.25, 0.25))],
				[1380, null],
				[1680, REST],
			]
		: [
				[0, REST],
				[360, first],
				[360 + ms10(500, 900), first],
				[0, REST],
			];
	if (frames.length === 4) frames[3][0] = frames[2][0] + 400;
	else frames[4][1] = frames[3][1];
	const [t] = slots(dur, lag, [frames[frames.length - 1][0]]);
	const stops = frames.map(([ms, pose]) => [t + ms, pose]);
	// while the cursor leads, the page holds the glance at rest and moves its .sf-look instead,
	// up to `reach` any way: those poses count where the eyes can reach (for the covers)
	const reaches = [...Array(16)].map((_, i) => {
		const [a, r] = [(i / 16) * Math.PI * 2, reach / Math.cos(Math.PI / 16)];
		return P(r * Math.cos(a), r * Math.sin(a));
	});
	return { dur, lag, stops, fns: "t", ease: SMOOTH, reaches };
}

/**
 * The open eyes kept so far as one pair: [pivot] > blink > sf-look > glance > eyeballs and
 * catch-lights (a shut eye squashes its catch-lights to a sliver too thin to see at page size).
 * `reach` is the glance in head units; screen eyes keep their whites still and glance with
 * their pupils only.
 */
function eyePair(reach, screen = false) {
	const eyes = figure.eyes;
	figure.eyes = [];
	if (!eyes.length || SIL) return "";
	const at = [eyes.reduce((sum, e) => sum + e.x, 0) / eyes.length, eyes[0].y];
	const cut = eyes.map(({ markup }) => markup.indexOf("/>") + 2);
	const balls = eyes.map(({ markup }, i) => markup.slice(0, cut[i])).join("");
	const lights = eyes.map(({ markup }, i) => markup.slice(cut[i])).join("");
	const blink = (body) => moving("b", "blink", at, body, blinkMake);
	const look = (body) =>
		`<g class="sf-look" data-look="${f(reach * figure.s)}">` +
		`${moving("g", "glance", [0, 0], body, () => glanceMake(reach))}</g>`;
	return screen ? blink(balls + look(lights)) : blink(look(balls + lights));
}

/** When a happy face laughs: a squeeze (sometimes two), shared by its eyes and its mouth. */
function laughPlan() {
	plan = mulberry32(seedOf(`laugh${figure.n}`));
	const { dur, lag } = cycle(4000, 7500);
	const n = dur >= 6400 && chance(0.6) ? 2 : 1;
	return { dur, lag, starts: slots(dur, lag, Array(n).fill(820), 900) };
}

/** Eye arcs, brows and cheeks lift and squeeze about the eye line (head units). */
function squeezeMake() {
	const { dur, starts, lag } = laughPlan();
	const up = P(0, -2.5, 0, 1.03, 0.97);
	const stops = starts.flatMap((t) => [
		[t, REST],
		[t + 200, up],
		[t + 520, P(0, -2.2, 0, 1.025, 0.975)],
		[t + 820, REST],
	]);
	return { dur, stops, fns: "ts", lag };
}

/** A laughing mouth: three quick "ha"s about its top edge while the eyes squeeze. */
function mouthMake() {
	const { dur, starts, lag } = laughPlan();
	const ha = P(0, 0.5, 0, 1.06, 1.17);
	const half = P(0, 0.2, 0, 1.02, 1.05);
	const stops = starts.flatMap((t) => [
		[t, REST],
		[t + 110, ha],
		[t + 230, half],
		[t + 350, ha],
		[t + 470, half],
		[t + 600, ha],
		[t + 820, REST],
	]);
	return { dur, stops, fns: "ts", lag };
}

/** Shades (and the brows above them) nudge up a little now and then. */
function nudgeMake() {
	const up = P(0, -2.6, chance(0.5) ? 1.5 : -1.5);
	return oneShot(6000, 10000, { fns: "tr" }, [
		[0, REST],
		[180, up, { ease: SPRING }],
		[760, up],
		[1000, REST],
	]);
}

/** A streak of light slides `travel` units across a lens every few seconds, fading in and out. */
function glintMake(travel) {
	return oneShot(4200, 7200, { fns: "t", rest: 0 }, [
		[0, REST, { o: 0 }],
		[90, P(travel * 0.15), { o: 0.95 }],
		[420, P(travel * 0.85), { o: 0.95 }],
		[520, P(travel), { o: 0 }],
	]);
}

/**
 * A white glint for a lens centred on (x, y): two slanted streaks `h` tall that slide `travel`
 * units across it. They are sized to stay inside the lens all the way, so they need no clip
 * (a clip round a moving part would be redrawn every frame). Motion-only.
 */
function glint(x, y, h, travel) {
	if (!MOTION || SIL) return "";
	const x0 = x - 2.85 - travel / 2;
	const bar = (x1, w) =>
		shape(p`M${x1 + h * 0.15} ${y - h / 2}l${w} 0l${-h * 0.3} ${h}l${-w} 0Z`, W, 0);
	return extra("s", "glint", [0, 0], bar(x0, 3) + bar(x0 + 4.5, 1.2), () => glintMake(travel));
}

/** A twinkle that pops on a pale goggle lens, where a white streak wouldn't show. */
function twinkleMake() {
	return oneShot(4200, 7200, { fns: "rs", rest: 0 }, [
		[0, P(0, 0, 0, 0.2), { o: 0 }],
		[140, P(0, 0, 30, 1.1), { o: 1 }],
		[320, P(0, 0, 50, 0.95), { o: 1 }],
		[500, P(0, 0, 75, 0.2), { o: 0 }],
	]);
}

/** A small white star on a goggle lens's rim at (x, y), outlined so it reads on white too. */
function lensTwinkle(x, y, sub) {
	if (!MOTION || SIL) return "";
	const star = shape(starPath(x, y, 5, 1.3, 4), W, 1.2);
	return extra("s", "glint", [x, y], star, twinkleMake, sub);
}

const LAUGHS = new Set(["laugh", "beam"]);

/** In the motion pass, a happy face's squeeze group, about the eye line at (x, y). */
const squeeze = (body, at) => moving("q", "squeeze", at, body, squeezeMake);
const laughing = (body, at) => moving("m", "mouth", at, body, mouthMake);
const nudged = (body, at) => moving("n", "nudge", at, body, nudgeMake);

// ------------------------------------------------------------------ trinkets in motion

/** A pom-pom hops off its beanie, lands squashed and settles. */
function pomMake() {
	const s = flip();
	return oneShot(3600, 6200, { fns: "trs" }, [
		[0, REST],
		[170, P(0, -3.4, 5 * s, 0.94, 1.06)],
		[340, P(0, 0.3, 0, 1.12, 0.86)],
		[500, P(0, -1.5, -3 * s, 0.98, 1.02)],
		[650, P(0, 0, 0, 1.05, 0.95)],
		[800, REST],
	]);
}

/** A quick shake that dies away: rotations of `amp` degrees, `step` ms apart. */
function shakeMake(lo, hi, amp, step, decay = [1, -0.72, 0.45, -0.22]) {
	const s = flip();
	const frames = [[0, REST], ...decay.map((k, i) => [(i + 1) * step, P(0, 0, amp * k * s)])];
	frames.push([(decay.length + 1) * step, REST]);
	return oneShot(lo, hi, { fns: "r" }, frames);
}

/** The `n` flowers of a crown bob one after another, 120 ms apart, like a wave along it. */
function crownWave(n) {
	plan = mulberry32(seedOf(`wave${figure.n}`));
	const { dur, lag } = cycle(4400, 7200);
	const [t] = slots(dur, lag, [720 + 120 * (n - 1)]);
	return { dur, t, lag, s: flip() };
}

function flowerMake(i, n) {
	const { dur, t, lag, s } = crownWave(n);
	const stops = [
		[t, REST],
		[t + 240, P(0, -1.8, 6 * s)],
		[t + 480, P(0, 0.5, -3 * s)],
		[t + 720, REST],
	];
	const keys = i ? `cr-f${figure.n}a` : undefined;
	return { dur, stops, fns: "tr", keys, lag: (lag - i * 120 + dur) % dur };
}

/** A music note drifts up and away from an ear cup, fading in and out, on a shared loop. */
function noteMake(side, at, dur, lag) {
	const dx = side * between(5, 10);
	const turn = side * between(8, 14);
	const stops = [
		[at, REST, { o: 0 }],
		[at + 200, P(dx * 0.1, -3, turn * 0.3), { o: 1 }],
		[at + 760, P(dx * 0.45, -12, -turn * 0.4), { o: 1 }],
		[at + 1240, P(dx * 0.8, -20, turn * 0.5), { o: 0.9 }],
		[at + 1600, P(dx, -26, 0), { o: 0 }],
	];
	return { dur, stops, fns: "tr", rest: 0, lag, ease: "linear" };
}

/**
 * An original music-note glyph with its notehead at the origin: a single quaver or a beamed
 * pair, solid ink on a white backing so it reads over hair and the black band alike.
 */
function noteGlyph(pair) {
	const heads = pair
		? [
				[0, 0],
				[8, -2.4],
			]
		: [[0, 0]];
	let back = "";
	let front = "";
	for (const [x, y] of heads) {
		const e = `cx="${x}" cy="${y}" rx="3.4" ry="2.6" transform="rotate(-24 ${x} ${y})"`;
		back += `<ellipse ${e} fill="${W}" stroke="${W}" stroke-width="4"/>`;
		front += `<ellipse ${e} fill="${INK}"/>`;
	}
	const stems = heads.map(([x, y]) => `M${f(x + 2.9)} ${f(y - 1)}L${f(x + 2.9)} ${f(y - 13)}`);
	back += `<path d="${stems.join("")}" fill="none" stroke="${W}" stroke-width="5.6"/>`;
	front += `<path d="${stems.join("")}" fill="none" stroke="${INK}" stroke-width="1.6"/>`;
	const flag = pair
		? "M2.9 -13L10.9 -15.4L10.9 -11.6L2.9 -9.2Z"
		: "M2.9 -13C4.5 -9.5 9.5 -9 7.5 -3.5C7.6 -7.4 5.2 -8.4 2.9 -9.4Z";
	back += `<path d="${flag}" fill="${W}" stroke="${W}" stroke-width="4"/>`;
	front += `<path d="${flag}" fill="${INK}"/>`;
	return back + front;
}

/** Three notes that float out of a pair of headphones' ear cups in turn (motion-only). */
function notes(rx, ey) {
	if (!MOTION || SIL) return "";
	plan = mulberry32(seedOf(`notes${figure.n}`));
	const { dur, lag } = cycle(14500, 17000);
	const starts = slots(dur, lag, [1600, 1600, 1600], 500);
	const sides = [flip(), 0, 0];
	sides[1] = -sides[0];
	sides[2] = flip();
	const pairs = [chance(0.5), chance(0.5), chance(0.5)];
	return starts
		.map((at, i) => {
			const s = sides[i];
			const [x, y] = [s * (rx + 15), ey - 6 - i * 3];
			const glyph = `<g transform="translate(${f(x)} ${f(y)})">${noteGlyph(pairs[i])}</g>`;
			return extra("t", "note", [x, y], glyph, () => noteMake(s, at, dur, lag), SUBS[i]);
		})
		.join("");
}

/** A sparkle at a crown point: it pops up, turns and shrinks away. */
function sparkMake() {
	return oneShot(3800, 7000, { fns: "rs", rest: 0 }, [
		[0, P(0, 0, 0, 0.2), { o: 0 }],
		[150, P(0, 0, 25, 1.1), { o: 1 }],
		[300, P(0, 0, 45, 0.9), { o: 1 }],
		[460, P(0, 0, 70, 0.2), { o: 0 }],
	]);
}

/** Small four-point sparkles that twinkle by three of a paper crown's points (motion-only). */
function sparkles(rx, k0, tips) {
	if (!MOTION || SIL) return "";
	plan = mulberry32(seedOf(`spark${figure.n}`));
	const chosen = shuffle(tips.map((_, i) => i)).slice(0, 3);
	return chosen
		.map((i, j) => {
			const t = tips[i];
			const x = rx * t + 5;
			const y = k0 - 46 - (t === 0 ? 7 : 0) + Math.abs(t) * 6;
			const star = shape(starPath(x, y, 5.5, 1.5, 4), W, 1.4);
			return extra("k", "spark", [x, y], star, sparkMake, SUBS[j]);
		})
		.join("");
}

/** A hoop earring swings as its head moves, on the head's own loop and within its turn. */
function earringMake(side) {
	const { dur, lag, events } = figure.head;
	const stops = [];
	for (const e of events) {
		const t = e.start + 120;
		let len = 1100;
		while (len > 400 && !inTurn(t, len, dur, lag)) len -= 50;
		const step = len / 5;
		const swing = [10, -7, 4.5, -2.5].map((a, i) => [t + step * (i + 1), P(0, 0, a * side)]);
		stops.push([t, REST], ...swing, [t + len, REST]);
	}
	return { dur, stops, fns: "r", lag };
}

/** A pointed hood's top sways to one side and back, like a soft cone of cloth. */
function tipMake(side) {
	return oneShot(5000, 8200, { fns: "r", ease: SMOOTH }, [
		[0, REST],
		[380, P(0, 0, 5 * side)],
		[800, P(0, 0, -3.6 * side)],
		[1180, P(0, 0, 1.8 * side)],
		[1520, REST],
	]);
}

/** An ear twitch: a flick out, a small rebound and back (sometimes twice). */
function twitchMake(amp, side) {
	const flick = [
		[0, REST],
		[70, P(0, 0, amp * side)],
		[160, P(0, 0, -amp * 0.3 * side)],
		[250, P(0, 0, amp * 0.5 * side)],
		[370, REST],
	];
	const frames = chance(0.4)
		? [...flick, ...flick.slice(1).map(([ms, p]) => [ms + 450, p])]
		: flick;
	return oneShot(4200, 8200, { fns: "r" }, frames);
}

/** A mushroom cap wobbles like jelly after a little hop. */
function capMake() {
	const s = flip();
	return oneShot(5000, 8000, { fns: "trs" }, [
		[0, REST],
		[200, P(0, -1.2, 3.2 * s, 1.02, 0.98)],
		[440, P(0, 0, -2.4 * s, 0.99, 1.01)],
		[680, P(0, -0.4, 1.5 * s)],
		[920, P(0, 0, -0.7 * s)],
		[1160, REST],
	]);
}

/** A frog's throat swells twice (motion-only, so it rests invisible). */
function sacMake() {
	const tiny = P(0, 0, 0, 0.3, 0.2);
	return oneShot(4200, 7000, { fns: "s", rest: 0 }, [
		[0, tiny, { o: 0 }],
		[60, P(0, 0, 0, 0.4, 0.3), { o: 1 }],
		[260, P(0, 0, 0, 1, 1), { o: 1 }],
		[420, P(0, 0, 0, 0.62, 0.5), { o: 1 }],
		[620, P(0, 0, 0, 1.06, 1.06), { o: 1 }],
		[820, tiny, { o: 1 }],
		[860, tiny, { o: 0 }],
	]);
}

/** A frog's eye bulbs duck a little while its eyes blink. */
function bulbMake() {
	const { dur, starts, lag } = blinkPlan();
	const dip = P(0, 0, 0, 1.04, 0.86);
	const stops = starts.flatMap((t) => [
		[t, REST],
		[t + 80, dip],
		[t + 180, dip],
		[t + 300, REST],
	]);
	return { dur, stops, fns: "s", lag };
}

/** A robot screen's highlight flickers: two quick dips in brightness. */
function flickerMake() {
	return oneShot(3000, 6000, { fns: "", rest: 1 }, [
		[0, REST, { o: 1 }],
		[40, REST, { o: 0.15 }],
		[90, REST, { o: 1 }],
		[150, REST, { o: 0.35 }],
		[210, REST, { o: 1 }],
	]);
}

/** A faint scanline rolls down a robot screen now and then (motion-only). */
function scanMake(height) {
	return oneShot(5000, 8500, { fns: "t", rest: 0, ease: "linear" }, [
		[0, REST, { o: 0 }],
		[80, REST, { o: 0.75 }],
		[900, P(0, height), { o: 0.75 }],
		[960, P(0, height), { o: 0 }],
	]);
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

/**
 * Eyes, brows, nose, mouth and cheek marks for a kid-type face. The motion pass draws the same
 * shapes in a different order, which changes nothing at rest because none of the regrouped
 * parts overlap: shut eyes squeeze up with the brows and cheeks (and laughing mouths bounce),
 * open eyes blink and glance as one pair, and shades push the brows up with them.
 */
function drawFace(h, k, hide = [false, false]) {
	if (SIL) return "";
	const g = faceGeo(h, k);
	const ex = EXPRESSIONS[k.expr];
	const cheeks = [];
	const tone = k.skin.tone;
	if (tone < 2 && k.cheeks) {
		const blush = tone === 0 ? DL : DM;
		for (const s of [-1, 1]) {
			if (k.bandAid !== s) cheeks.push(oval(s * (g.ex + 11), g.my - 4, 8.5, 5.4, blush));
		}
	}
	if (tone >= 2) {
		cheeks.push(
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
				cheeks.push(circle(s * (g.ex + dx) + g.lx * 0.5, g.my + dy, 1.05, INK));
			}
		}
	}
	const eyes = [];
	const brows = [];
	[-1, 1].forEach((s, i) => {
		const x = s * g.ex + g.lx;
		const kind = ex.eyes[i];
		eyes.push(hide[i] ? "" : blinker(kind, eye(kind, x, g.ey, g.er, g.eh, s), x, g.ey));
		const by = g.ey - g.eh - 8 + (ex.brow ?? 0);
		brows.push(taper(x - 7, by + 1.5, x + s * 0.5, by - 2.6, x + 7, by + 1.5, 2.6));
	});
	const nose = ink(
		p`M${-3 + g.lx * 0.6} ${g.ey + g.eh + 1}` +
			p`Q${g.lx * 0.6} ${g.ey + g.eh + 4} ${3 + g.lx * 0.6} ${g.ey + g.eh + 1}`,
		2.2,
	);
	const lipsAt = [g.lx * 0.5, g.my];
	const lips = mouth(ex.mouth, ...lipsAt);
	const aid = k.bandAid ? bandAid(k.bandAid * (g.ex + 12), g.my - 6, k.bandAid * -28) : "";
	if (!MOTION) return [...cheeks, eyes[0], brows[0], eyes[1], brows[1], nose, lips, aid].join("");
	if (!ex.eyes.some((e) => OPEN_EYES.has(e))) {
		const lift = squeeze([...cheeks, ...eyes, ...brows, aid].join(""), [g.lx, g.ey]);
		return lift + nose + (LAUGHS.has(k.expr) ? laughing(lips, lipsAt) : lips);
	}
	const brow = k.eyewear === "shades" ? nudged(brows.join(""), shadesAt(g)) : brows.join("");
	const reach = k.eyewear === "glasses" ? 2.6 : 3.4;
	return cheeks.join("") + eyes.join("") + brow + nose + lips + eyePair(reach) + aid;
}

/** Where a pair of shades turns when it nudges up: the middle of its bridge. */
const shadesAt = (g) => [g.lx, g.ey - 4];

// ------------------------------------------------------------------ eyewear

function eyewear(h, k) {
	if (SIL) return "";
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
			out.push(k.shadeStyle === "heart" ? glint(x, g.ey + 2, 8, 8) : glint(x, g.ey, 11, 14));
			out.push(ink(p`M${x + s * 15} ${g.ey - 4}L${s * (h.rx - 2)} ${g.ey - 3}`, 2.8));
		}
		out.push(
			ink(
				p`M${-g.ex + 14 + g.lx} ${g.ey - 4}Q${g.lx} ${g.ey - 9} ${g.ex - 14 + g.lx} ${g.ey - 4}`,
				3.2,
			),
		);
		return nudged(out.join(""), shadesAt(g));
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
		const pom = moving(
			"p",
			"pom",
			[0, -ry - 16],
			clipped(pomD, W, 3.6, circle(8, -ry - 25, 15, DL) + circle(-3, -ry - 33, 12, W)),
			pomMake,
		);
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
			const flower = `<use href="#${SIL ? "flower-sil" : "flower"}" transform="${at}"/>`;
			out += moving("f", "flower", [x, y], flower, () => flowerMake(i, pts.length), {
				sub: SUBS[i],
			});
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
		return { front: out + notes(rx, g.ey) };
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
		const flap = moving("x", "flap", k0, tails, () => shakeMake(4200, 7200, 9, 170));
		return {
			front: clipped(wrap, PO, 4.2, shadeIn) + flap + oval(k0[0], k0[1], 8, 7, PO, 3),
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
			out += lensTwinkle(x + 6, g0 - 16, SUBS[(s + 1) / 2]);
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
		const hood = clipped(d, k.hatFill, 4.2, inner, true);
		if (!MOTION) return { front: hood + tip };
		// The pointed top sways about a cut across the cone: two copies of the hood, each clipped
		// to its side of the cut (the lower one reaching a little past it, so no seam shows).
		const cut = -ry - 30;
		const box = (y0, y1) => {
			uid += 1;
			const at = `x="${f(-rx - 40)}" y="${f(y0)}" width="${f(2 * rx + 80)}" height="${f(y1 - y0)}"`;
			return [`<clipPath id="h${uid}"><rect ${at}/></clipPath>`, `clip-path="url(#h${uid})"`];
		};
		const [lowClip, low] = box(cut - 1.5, ryb + 30);
		const [topClip, top] = box(-ry - 90, cut);
		const cone = `${topClip}<g ${top}>${clipped(d, k.hatFill, 4.2, inner, true)}</g>${tip}`;
		return {
			front:
				`${lowClip}<g ${low}>${hood}</g>` +
				moving("y", "tip", [s * rx * 0.24, cut], cone, () => tipMake(s)),
		};
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
		const [x, y] = [s * h.rx * 0.5, -h.ry * 0.86];
		const bow = group(loops, `translate(${f(x)} ${f(y)}) rotate(${s * 18})`);
		return { front: moving("w", "bow", [x, y], bow, () => shakeMake(4200, 7000, 11, 150)) };
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
			front: group(
				clipped(smooth(pts), W, 3.4, inner) + balls + sparkles(rx, k0, tips),
				`rotate(${k.side * 7} 0 ${f(k0)})`,
			),
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
		for (const [i, a] of [232, 308].entries()) {
			const [x, y] = headPoint(h, a, 12);
			const ear =
				circle(x, y, 19, k.hatFill, 4.2) + circle(x, y + 1, 10, k.hatFill === DL ? DM : DL, 2.6);
			// each ear flicks about a point inside the hood, below its centre
			const side = i ? 1 : -1;
			const make = () => twitchMake(10, side);
			ears += moving("e", "ear", headPoint(h, a, -5), ear, make, { sub: SUBS[i] });
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
			if (k.earring !== "hoop") out += circle(x + s * 1.5, y, 2.6, INK);
			else if (k.hat === "hood" || k.hat === "bearHood")
				out += circle(x + s * 1.5, y + 3, 3.6, "none", 2);
			else {
				// a hoop swings from the earlobe; studs (and hoops under a hood) stay put
				const hoop = circle(x + s * 1.5, y + 3, 3.6, "none", 2);
				const sub = SUBS[(s + 1) / 2];
				out += moving("r", "earring", [x + s * 1.5, y - 0.6], hoop, () => earringMake(s), { sub });
			}
		}
	}
	return out;
}

function drawHead(h, k, shadow = "") {
	const light = oval(-h.rx * 0.11, -h.ry * 0.12, h.rx * 1.0, h.ry * 1.0, k.skin.lt);
	return clipped(headPath(h), k.skin.sh, 4.4, light + shadow);
}

// Each figure is drawn as parts in the still's order: `fixed` ones (torso, neck, collar) stay in
// the base, and the moving ones (the head with its face and hat, and the hair hanging behind the
// shoulders or beside them) move together in the motion layer.
const fixed = (markup) => ({ markup, move: false });
const moves = (markup) => ({ markup, move: true });

function kid(k) {
	const h = k.h;
	const yn = h.ryb + 6;
	const hair = HAIR[k.hair](h, k.hairFill, k.side, k);
	const hat = k.hat ? HATS[k.hat](h, k) : {};
	const tilt = headTurn(k, h.ryb);
	const hide =
		k.eyewear === "shades" ? [true, true] : k.eyewear === "patch" ? [false, true] : [false, false];
	const face = [
		drawEars(h, k),
		hat.behind ?? "",
		drawHead(h, k, hat.shadow),
		drawFace(h, k, hide),
		eyewear(h, k),
		hair.front ?? "",
		hat.front ?? "",
	].join("");
	return [
		moves(group((hair.back ?? "") + (hat.back ?? ""), tilt)),
		fixed(drawTorso(k, yn)),
		fixed(drawNeck(k, h, yn)),
		moves(group(hair.mid ?? "", tilt)),
		moves(group(face, tilt)),
	];
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
	const screen = roundRect(-44, -38, 88, 64, 13);
	head.push(shape(screen, INK, 3));
	// the screen's highlight flickers now and then
	const shine = ink("M-37 -26l9 -6M-38 -16l3.5 -2.4", 2.4, W);
	head.push(SIL ? "" : moving("o", "flicker", [0, 0], shine, flickerMake));
	const expr = EXPRESSIONS[k.expr];
	const arcs = [];
	[-1, 1].forEach((side, i) => {
		const x = side * g.ex;
		if (expr.eyes[i] === "happy" || expr.eyes[i] === "calm") {
			arcs.push(ink(p`M${x - 8} ${g.ey + 3}Q${x} ${g.ey - 11} ${x + 8} ${g.ey + 3}`, 4.2, W));
		} else {
			const screenEye = oval(x, g.ey, 7, 9, W) + circle(x + 2, g.ey - 3, 2.6, INK);
			arcs.push(blinker("open", screenEye, x, g.ey));
		}
	});
	const happy = !expr.eyes.some((e) => OPEN_EYES.has(e));
	head.push(happy ? squeeze(arcs.join(""), [0, g.ey]) : arcs.join(""));
	const smile = ink(p`M-9 ${g.ey + 15}Q0 ${g.ey + 23} 9 ${g.ey + 15}`, 3.4, W);
	head.push(LAUGHS.has(k.expr) ? laughing(smile, [0, g.ey + 15]) : smile);
	head.push(ink(p`M-36 ${g.ey + 12}l5 0M31 ${g.ey + 12}l5 0`, 3, W));
	for (const [x, y] of [
		[-50, -48],
		[50, -48],
		[-50, 40],
		[50, 40],
		[0, -50],
	])
		head.push(circle(x, y, 2.4, INK));
	head.push(eyePair(2.2, true));
	head.push(scanline());
	const parts = out.map(fixed);
	parts.push(moves(group(head.join(""), headTurn(k, 50))));
	return parts;
}

/** A faint line that rolls down a robot's screen, inside its edges all the way (motion-only). */
function scanline() {
	if (!MOTION || SIL) return "";
	return extra("v", "scan", [0, 0], ink("M-38 -34L38 -34", 1.6, W), () => scanMake(56));
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
	// eye bulbs sit on the crown; the head outline crosses their lower half. They duck a little
	// while the eyes blink.
	for (const s of [-1, 1]) {
		const bulb = ellipsePath(s * 31, -38, 23, 22);
		const dome = clipped(bulb, k.skin.sh, 4.4, circle(s * 31 - 5, -42, 21, k.skin.lt));
		head.push(moving("z", "bulb", [s * 31, -24], dome, bulbMake));
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
	head.push(eyePair(4));
	// a throat sac swells under the smile now and then
	const sac = oval(0, 41, 17, 10, DL, 2.6) + ink("M-9 37Q-4 33 3 34", 2, W);
	head.push(extra("u", "sac", [0, 33], sac, sacMake));
	const parts = out.map(fixed);
	parts.push(moves(group(head.join(""), headTurn(k, 50))));
	return parts;
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
	for (const [i, s] of [-1, 1].entries()) {
		const outer = smooth([
			[s * 22, -50],
			[s * 46, -104, true],
			[s * 63, -34],
		]);
		const ear = clipped(
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
		);
		// each ear twitches about its root, hidden under the head
		const make = () => twitchMake(8, s);
		ears.push(moving("e", "ear", [s * 42, -40], ear, make, { sub: SUBS[i] }));
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
	const eyes = [];
	for (const [i, s] of [-1, 1].entries()) {
		const x = s * g.ex + g.lx;
		eyes.push(blinker(expr.eyes[i], eye(expr.eyes[i], x, g.ey, g.er, g.eh, s), x, g.ey));
	}
	const cheeks = oval(-g.ex - 11, g.my - 2, 8, 5, DL) + oval(g.ex + 11, g.my - 2, 8, 5, DL);
	// shut eyes squeeze up with the cheeks (which the still draws last; nothing overlaps them)
	const happy = MOTION && !expr.eyes.some((e) => OPEN_EYES.has(e));
	head.push(happy ? squeeze(eyes.join("") + cheeks, [g.lx, g.ey]) : eyes.join(""));
	const ny = g.ey + g.eh + 4;
	head.push(
		shape(p`M-7 ${ny}Q0 ${ny - 3} 7 ${ny}Q4 ${ny + 7} 0 ${ny + 8}Q-4 ${ny + 7} -7 ${ny}Z`, INK, 0),
	);
	head.push(oval(-2.4, ny + 0.5, 2, 1.2, W));
	const lips = ink(
		p`M0 ${ny + 8}L0 ${ny + 11}M-8 ${ny + 13}` +
			p`Q-4 ${ny + 17} 0 ${ny + 11}Q4 ${ny + 17} 8 ${ny + 13}`,
		2.4,
	);
	head.push(LAUGHS.has(k.expr) ? laughing(lips, [0, ny + 9]) : lips);
	head.push(happy ? "" : cheeks);
	head.push(eyePair(3.4));
	const torso =
		drawTorso(k, yn) +
		clipped(p`M-13 40L-13.5 ${yn + 2}Q0 ${yn + 10} 13.5 ${yn + 2}L13 40Z`, HA, 3.4, "") +
		scarf(yn, k);
	return [fixed(torso), moves(group(head.join(""), headTurn(k, h.ryb)))];
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
		// the cap wobbles with the sprout growing out of it
		moving(
			"c",
			"cap",
			[0, c0 + 8],
			shape(p`M-2 ${-ry - 56}Q-4 ${-ry - 70} 2 ${-ry - 76}`, "none", 2.6) +
				shape(
					p`M2 ${-ry - 76}C10 ${-ry - 86} 24 ${-ry - 82} 26 ${-ry - 72}` +
						p`C16 ${-ry - 66} 6 ${-ry - 68} 2 ${-ry - 76}Z`,
					DM,
					2.4,
				) +
				clipped(cap, DM, 4.4, capIn),
			capMake,
		),
	];
	const parts = out.map(fixed);
	parts.push(moves(group(head.join(""), headTurn(k, h.ryb))));
	return parts;
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

// ------------------------------------------------------------------ head moves

// Each head plays one or two short moves in a loop of 7-13 s, about its neck point, in root
// units and degrees. A move lists [fraction of its length, pose] after resting at 0.
const HEAD_MOVES = {
	tilt(s) {
		const a = s * between(3, 5);
		return [
			[0.3, P(0, 0, a)],
			[0.5, P(0, 0, a * 0.9)],
			[0.72, P(0, 0, a * 0.95)],
		];
	},
	nod: (s) => [
		[0.18, P(0, 2.6, s * 0.8)],
		[0.36, P(0, 0.3, 0)],
		[0.54, P(0, 2.2, s * 0.6)],
		[0.76, REST],
	],
	bounce() {
		const up = -between(4, 6);
		return [
			[0.12, P(0, 1.2)],
			[0.38, P(0, up)],
			[0.62, P(0, 1)],
			[0.8, P(0, -0.6)],
		];
	},
	look: (s) => [
		[0.2, P(3 * s, 0, 2 * s)],
		[0.42, P(3 * s, 0, 2 * s)],
		[0.62, P(-3 * s, 0, -2 * s)],
		[0.82, P(-3 * s, 0, -2 * s)],
	],
	giggle: (s) => [
		[0.12, P(0, -2, -1.2 * s)],
		[0.26, P(0, 0.4)],
		[0.4, P(0, -2, 1.2 * s)],
		[0.54, P(0, 0.4)],
		[0.68, P(0, -1.2, -0.6 * s)],
		[0.84, REST],
	],
	doubleTake: (s) => [
		[0.12, P(1.6 * s, 0, 1.5 * s)],
		[0.24, REST],
		[0.42, REST],
		[0.5, P(3.4 * s, -1.4, 4.2 * s)],
		[0.58, P(3 * s, -0.8, 3.6 * s)],
		[0.82, P(3 * s, -0.8, 3.6 * s)],
	],
};
// Every move fits in one turn of the clock (see the slice clock above).
const MOVE_MS = {
	tilt: [1300, 1660],
	nod: [1200, 1500],
	bounce: [1200, 1400],
	look: [1400, 1660],
	giggle: [1200, 1450],
	doubleTake: [1400, 1660],
};

const moveAt = (moves, t) => moves.some((m) => t >= m.start && t < m.start + m.ms);

/**
 * Picks every head's moves and loop, then spreads the loops' phases so that about the same
 * number of heads move at any moment: each head in turn takes, from 24 candidate phases (each
 * with its moves placed in the turns that phase gives it), the one that adds least to the squared
 * count of heads already moving over the first four minutes.
 */
function planHeads(crowd) {
	const plans = crowd.map((k, n) => {
		figure = { n, side: sideOf(k) };
		plan = mulberry32(seedOf(`head${n}`));
		const kinds = shuffle(Object.keys(HEAD_MOVES));
		const moves = kinds.slice(0, chance(0.08) ? 2 : 1).map((type) => ({
			type,
			ms: ms10(...MOVE_MS[type]),
			frames: HEAD_MOVES[type](flip()),
		}));
		return { side: figure.side, dur: loopLen(7000, 13000), moves };
	});
	plan = mulberry32(SEED + 5);
	const STEP = 100;
	const load = new Float64Array(240000 / STEP);
	for (const n of shuffle(plans.map((_, i) => i))) {
		const p = plans[n];
		let best = null;
		for (let c = 0; c < 24; c++) {
			const lag = alignedLag(p.dur, (c + plan()) / 24, p.side);
			const starts = slots(
				p.dur,
				lag,
				p.moves.map((m) => m.ms),
				1500,
				p.side,
			);
			const moves = starts.map((start, i) => ({ ...p.moves[i], start }));
			let cost = 0;
			for (let b = 0; b < load.length; b++) {
				if (moveAt(moves, (b * STEP + lag) % p.dur)) cost += 2 * load[b] + 1;
			}
			// a phase that leaves a move out only wins when none fits them all
			cost += (p.moves.length - moves.length) * 1e9;
			if (moves.length && (!best || cost < best.cost)) best = { lag, moves, cost };
		}
		p.lag = best.lag;
		p.moves = best.moves;
		for (let b = 0; b < load.length; b++)
			if (moveAt(p.moves, (b * STEP + p.lag) % p.dur)) load[b]++;
	}
	crowd.forEach((k, n) => {
		const { dur, lag, moves } = plans[n];
		k.move = { dur, lag, events: moves.map(({ type, start, ms }) => ({ type, start, ms })) };
		const stops = moves.flatMap((m) => [
			[m.start, REST],
			...m.frames.map(([at, pose]) => [m.start + Math.round(at * m.ms), pose]),
			[m.start + m.ms, REST],
		]);
		figure = { n, side: sideOf(k) };
		register(`cr-h${n}`, "head", () => ({ dur, stops, fns: "tr", lag }));
	});
	return plans;
}

/** How many heads move at each tenth of a second over `secs` seconds (for the report). */
function headLoad(plans, secs) {
	const counts = [];
	for (let t = 0; t < secs * 1000; t += 100) {
		counts.push(plans.filter((p) => moveAt(p.moves, (t + p.lag) % p.dur)).length);
	}
	return counts;
}

// ------------------------------------------------------------------ reach

// To keep the right shapes in front of a moving head, the motion layer needs to know how far
// every part can reach. A small evaluator walks the markup this file writes (paths, circles,
// ellipses, rects, uses, groups with transforms, clip paths) and returns its box in root units,
// taking every animated group through each pose of its keyframes.

const NONE = [Infinity, Infinity, -Infinity, -Infinity];
const isEmpty = (b) => !(b[0] < b[2] && b[1] < b[3]);
const hasPoints = (b) => b[0] <= b[2] && b[1] <= b[3];
const join = (a, b) => [
	Math.min(a[0], b[0]),
	Math.min(a[1], b[1]),
	Math.max(a[2], b[2]),
	Math.max(a[3], b[3]),
];
const meet = (a, b) => [
	Math.max(a[0], b[0]),
	Math.max(a[1], b[1]),
	Math.min(a[2], b[2]),
	Math.min(a[3], b[3]),
];
const grow = (b, m) => [b[0] - m, b[1] - m, b[2] + m, b[3] + m];

// 2D affine matrices [a, b, c, d, e, f]: x' = a x + c y + e, y' = b x + d y + f
const ID = [1, 0, 0, 1, 0, 0];
const mul = (m, n) => [
	m[0] * n[0] + m[2] * n[1],
	m[1] * n[0] + m[3] * n[1],
	m[0] * n[2] + m[2] * n[3],
	m[1] * n[2] + m[3] * n[3],
	m[0] * n[4] + m[2] * n[5] + m[4],
	m[1] * n[4] + m[3] * n[5] + m[5],
];
const apply = (m, [x, y]) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
const scaleOf = (m) => Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2]));

function parseTransform(text = "") {
	let m = ID;
	for (const [, fn, args] of text.matchAll(/(\w+)\(([^)]*)\)/g)) {
		const v = args
			.split(/[\s,]+/)
			.filter(Boolean)
			.map(Number);
		if (fn === "translate") m = mul(m, [1, 0, 0, 1, v[0], v[1] ?? 0]);
		else if (fn === "scale") m = mul(m, [v[0], 0, 0, v[1] ?? v[0], 0, 0]);
		else if (fn === "rotate") {
			const a = (v[0] * Math.PI) / 180;
			const [cx = 0, cy = 0] = v.slice(1);
			m = mul(m, [1, 0, 0, 1, cx, cy]);
			m = mul(m, [Math.cos(a), Math.sin(a), -Math.sin(a), Math.cos(a), 0, 0]);
			m = mul(m, [1, 0, 0, 1, -cx, -cy]);
		} else if (fn === "matrix") m = mul(m, v);
	}
	return m;
}

/** Points on an SVG arc from (x1, y1) to (x2, y2) (endpoint parameterisation, sampled). */
function arcPoints(x1, y1, rx, ry, phi, large, sweep, x2, y2, out) {
	out.push([x2, y2]);
	rx = Math.abs(rx);
	ry = Math.abs(ry);
	if (!rx || !ry) return;
	const a = (phi * Math.PI) / 180;
	const [ca, sa] = [Math.cos(a), Math.sin(a)];
	const [dx, dy] = [(x1 - x2) / 2, (y1 - y2) / 2];
	const [xp, yp] = [ca * dx + sa * dy, -sa * dx + ca * dy];
	const fit = (xp * xp) / (rx * rx) + (yp * yp) / (ry * ry);
	if (fit > 1) [rx, ry] = [rx * Math.sqrt(fit), ry * Math.sqrt(fit)];
	const top = rx * rx * ry * ry - rx * rx * yp * yp - ry * ry * xp * xp;
	let k = Math.sqrt(Math.max(0, top / (rx * rx * yp * yp + ry * ry * xp * xp)));
	if (large === sweep) k = -k;
	const [cxp, cyp] = [(k * rx * yp) / ry, (-k * ry * xp) / rx];
	const cx = ca * cxp - sa * cyp + (x1 + x2) / 2;
	const cy = sa * cxp + ca * cyp + (y1 + y2) / 2;
	const angle = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
	const t1 = angle(1, 0, (xp - cxp) / rx, (yp - cyp) / ry);
	let dt = angle((xp - cxp) / rx, (yp - cyp) / ry, (-xp - cxp) / rx, (-yp - cyp) / ry);
	if (!sweep && dt > 0) dt -= 2 * Math.PI;
	else if (sweep && dt < 0) dt += 2 * Math.PI;
	for (let i = 1; i < 24; i++) {
		const t = t1 + (dt * i) / 24;
		const [ex, ey] = [rx * Math.cos(t), ry * Math.sin(t)];
		out.push([cx + ca * ex - sa * ey, cy + sa * ex + ca * ey]);
	}
}

/** Every end and control point of path data `d` (a curve stays inside their hull). */
function pathPoints(d) {
	const tok = d.match(/[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/g) ?? [];
	const pts = [];
	let [i, cmd, x, y, sx, sy] = [0, "", 0, 0, 0, 0];
	const num = () => Number(tok[i++]);
	while (i < tok.length) {
		if (/[A-Za-z]/.test(tok[i])) cmd = tok[i++];
		const rel = cmd === cmd.toLowerCase();
		const [ox, oy] = rel ? [x, y] : [0, 0];
		switch (cmd.toUpperCase()) {
			case "Z":
				[x, y] = [sx, sy];
				break;
			case "M":
				[x, y] = [ox + num(), oy + num()];
				[sx, sy] = [x, y];
				pts.push([x, y]);
				cmd = rel ? "l" : "L";
				break;
			case "L":
			case "T":
				[x, y] = [ox + num(), oy + num()];
				pts.push([x, y]);
				break;
			case "H":
				x = ox + num();
				pts.push([x, y]);
				break;
			case "V":
				y = oy + num();
				pts.push([x, y]);
				break;
			case "C":
			case "S":
			case "Q": {
				const n = cmd.toUpperCase() === "C" ? 3 : 2;
				for (let j = 0; j < n; j++) pts.push([ox + num(), oy + num()]);
				[x, y] = pts[pts.length - 1];
				break;
			}
			case "A": {
				const [rx, ry, phi, large, sweep] = [num(), num(), num(), num(), num()];
				const [ex, ey] = [ox + num(), oy + num()];
				arcPoints(x, y, rx, ry, phi, large, sweep, ex, ey, pts);
				[x, y] = [ex, ey];
				break;
			}
			default:
				i++;
		}
	}
	return pts;
}

/** A tree of the elements in `text` (just tags and attributes, with their source spans). */
function parseSvg(text) {
	const root = { tag: "#root", attrs: {}, kids: [], start: 0, end: text.length };
	const stack = [root];
	for (const m of text.matchAll(/<(\/?)([a-zA-Z]+)((?:\s+[\w:-]+="[^"]*")*)\s*(\/?)>/g)) {
		const [all, close, tag, rest, self] = m;
		if (close) {
			stack.pop().end = m.index + all.length;
			continue;
		}
		const attrs = {};
		for (const [, key, value] of rest.matchAll(/([\w:-]+)="([^"]*)"/g)) attrs[key] = value;
		const node = { tag, attrs, kids: [], start: m.index, open: all };
		stack[stack.length - 1].kids.push(node);
		if (self) node.end = m.index + all.length;
		else stack.push(node);
	}
	return root;
}

function idsOf(node, ids = new Map()) {
	if (node.attrs.id) ids.set(node.attrs.id, node);
	for (const kid of node.kids) idsOf(kid, ids);
	return ids;
}

const HIDDEN = new Set(["defs", "clipPath", "pattern", "filter", "mask", "style", "title"]);

/** Each animation's poses as matrices, a little exaggerated to allow for in-between frames. */
function posesOf(cls) {
	for (const name of (cls ?? "").split(" ")) {
		const anim = ANIMS.get(name);
		if (!anim) continue;
		const more = (v, rest) => rest + (v - rest) * 1.15;
		return anim.poses.map((p) =>
			parseTransform(
				`translate(${more(p.x, 0)} ${more(p.y, 0)}) rotate(${more(p.r, 0)}) ` +
					`scale(${more(p.sx, 1)} ${more(p.sy, 1)})`,
			),
		);
	}
	return null;
}

/** The box (root units) that `node` paints under matrix `m`, through all its poses. */
function reach(node, m, ids, paint = { sw: 0, stroke: false }) {
	const a = node.attrs;
	if (HIDDEN.has(node.tag)) return NONE;
	const local = a.transform ? mul(m, parseTransform(a.transform)) : m;
	const own = {
		sw: a["stroke-width"] !== undefined ? Number(a["stroke-width"]) : paint.sw,
		stroke: a.stroke !== undefined ? a.stroke !== "none" : paint.stroke,
	};
	const poses = posesOf(a.class);
	if (poses) {
		const bare = { ...node, attrs: { ...a, class: "", transform: "" } };
		return poses.reduce((b, pm) => join(b, reach(bare, mul(local, pm), ids, own)), NONE);
	}
	let box = NONE;
	const add = (pts) => {
		for (const pt of pts) {
			const [x, y] = apply(local, pt);
			box = join(box, [x, y, x, y]);
		}
	};
	const n = (key) => Number(a[key] ?? 0);
	switch (node.tag) {
		case "path":
			add(pathPoints(a.d ?? ""));
			break;
		case "circle":
		case "ellipse": {
			const [rx, ry] = node.tag === "circle" ? [n("r"), n("r")] : [n("rx"), n("ry")];
			const pts = [];
			for (let i = 0; i < 16; i++) {
				const t = (i / 16) * Math.PI * 2;
				pts.push([
					n("cx") + (rx / Math.cos(Math.PI / 16)) * Math.cos(t),
					n("cy") + (ry / Math.cos(Math.PI / 16)) * Math.sin(t),
				]);
			}
			add(pts);
			break;
		}
		case "rect":
			add([
				[n("x"), n("y")],
				[n("x") + n("width"), n("y") + n("height")],
				[n("x"), n("y") + n("height")],
				[n("x") + n("width"), n("y")],
			]);
			break;
		case "use": {
			const target = ids.get((a.href ?? "").slice(1));
			if (target) box = reach(target, local, ids, own);
			break;
		}
		default:
			for (const kid of node.kids) box = join(box, reach(kid, local, ids, own));
	}
	if (own.stroke && hasPoints(box) && ["path", "circle", "ellipse", "rect"].includes(node.tag)) {
		box = grow(box, (own.sw / 2) * scaleOf(local));
	}
	const clip = /url\(#([^)]+)\)/.exec(a["clip-path"] ?? "");
	if (clip && ids.has(clip[1])) {
		const shape = ids.get(clip[1]).kids.reduce((b, kid) => join(b, reach(kid, local, ids)), NONE);
		box = meet(box, shape);
	}
	return box;
}

// ------------------------------------------------------------------ filters at the leaves

// Chromium moves animated SVG groups as compositor layers. A filter (or clip) with an animated
// group inside it becomes a render surface that is filtered again on every frame, which cost
// most of the frame budget. So no filter ever holds a moving part: each run of shapes that holds
// none gets its own filter, and the animated groups between them stay bare. A moving part's
// filters work in its own frame: the shipped files have the wobble baked into every shape's own
// coordinates (tools/bake.mjs), where the frame makes no difference, so this saves the pair of
// matrices that mapping each run back to root space would cost. The white outlines are still
// mapped back, as their viewports cut them off along the band.

const invert = ([a, b, c, d, e, g]) => {
	const det = a * d - b * c;
	return [d / det, -b / det, -c / det, a / det, (c * g - d * e) / det, (b * e - a * g) / det];
};
const matrix = (m) => `matrix(${m.map((v) => +v.toFixed(6)).join(" ")})`;
const isId = (m) => m.every((v, i) => Math.abs(v - ID[i]) < 1e-9);

const inkRun = (body) => `<g filter="url(#ink)">${body}</g>`;
// true maps every moving run back to root space too, so the unbaked files' wobble matches the
// still's at rest (about 41 KB more); the shipped, baked files don't need it
const ROOT_INK = false;

// shapes that exist only in the motion layer: drawn clean, with no filter (or layer) of their own
const EXTRAS = new Set(["note", "glint", "spark", "sac", "scan"]);
const animated = (node) =>
	node.attrs.class?.split(" ").some((c) => c === "sf-look" || ANIMS.has(c)) ?? false;
const familyOf = (node) => /\bcr-([a-z]+) cr-/.exec(node.attrs.class ?? "")?.[1];

/**
 * `markup` (root space) with every run of still shapes wrapped by `wrap(body, run, ctm)`, in the
 * run's own frame, or with `root` in root space at rest: `body` is then the run under its matrix
 * `ctm`, mapped back out again round the wrap.
 */
function pushFilters(markup, wrap, root = false) {
	const tree = parseSvg(markup);
	const moves = (node) => (node.moves ??= animated(node) || node.kids.some(moves));
	const walk = (nodes, ctm, bare = false) => {
		let out = "";
		let run = [];
		const flush = () => {
			const body = run.map((node) => markup.slice(node.start, node.end)).join("");
			if (!bare && run.some((node) => !HIDDEN.has(node.tag))) {
				out +=
					!root || isId(ctm)
						? wrap(body, run, ctm)
						: `<g transform="${matrix(invert(ctm))}">` +
							wrap(`<g transform="${matrix(ctm)}">${body}</g>`, run, ctm) +
							"</g>";
			} else out += body;
			run = [];
		};
		for (const node of nodes) {
			if (!moves(node)) {
				run.push(node);
				continue;
			}
			flush();
			const m = node.attrs.transform ? mul(ctm, parseTransform(node.attrs.transform)) : ctm;
			out += node.open + walk(node.kids, m, bare || EXTRAS.has(familyOf(node))) + `</${node.tag}>`;
		}
		flush();
		return out;
	};
	return walk(tree.kids, ID);
}

/** Consecutive top-level groups with the same transform (a head's hair and face) as one group. */
function joinTilts(markup) {
	const kids = parseSvg(markup).kids;
	let out = "";
	for (let i = 0; i < kids.length; i++) {
		const k = kids[i];
		const inner = (n) => markup.slice(n.start + n.open.length, n.end - 4);
		if (k.tag !== "g" || !k.attrs.transform) {
			out += markup.slice(k.start, k.end);
			continue;
		}
		let body = inner(k);
		while (kids[i + 1]?.tag === "g" && kids[i + 1].open === k.open) body += inner(kids[++i]);
		out += k.open + body + "</g>";
	}
	return out;
}

/**
 * `markup` (figure space, under matrix `m`) with each moving part taken as late in its group as
 * it can go: past every still shape after it that it can't touch, wherever it moves. Then fewer
 * still shapes follow a moving part, and those that do each need a compositor layer of their own.
 */
function floatUp(markup, m, ids) {
	const tree = parseSvg(markup);
	const pure = (node) =>
		animated(node) ||
		(node.kids.length > 0 && node.kids.every((kid) => HIDDEN.has(kid.tag) || pure(kid)));
	const still = (node) => !node.kids.some((kid) => animated(kid) || !still(kid)) && !animated(node);
	let out = "";
	for (const group of tree.kids) {
		const text = (node) => markup.slice(node.start, node.end);
		if (group.tag !== "g" || !group.kids.some(pure)) {
			out += text(group);
			continue;
		}
		const ctm = mul(m, parseTransform(group.attrs.transform));
		const boxes = new Map();
		const shapes = new Map();
		const boxesOf = (node) =>
			boxes.get(node) ?? boxes.set(node, leafBoxes(node, [ctm], ids)).get(node);
		const shapesOf = (node) =>
			shapes.get(node) ?? shapes.set(node, outlines(node, ctm, ids)).get(node);
		// a moving part may pass a still shape when none of its boxes touch that shape's outline;
		// a shape that itself holds moving parts is only passed when their boxes stay apart
		const apart = (a, b) =>
			still(b)
				? boxesOf(a).every((r) => shapesOf(b).every((sh) => !touches(r, sh)))
				: boxesOf(a).every((r) => boxesOf(b).every((q) => isEmpty(meet(r, q))));
		const order = [...group.kids];
		for (let changed = true; changed; ) {
			changed = false;
			for (let i = order.length - 2; i >= 0; i--) {
				const [a, b] = [order[i], order[i + 1]];
				if (pure(a) && !pure(b) && apart(a, b)) {
					[order[i], order[i + 1]] = [b, a];
					changed = true;
				}
			}
		}
		// neighbours that now share one animated group (shades and the brows above them) become one
		const merged = [];
		for (const node of order) {
			const last = merged[merged.length - 1];
			const wrap = (n) => pivotParts(markup, n);
			if (last && pure(node) && pure(last.node) && wrap(node) && wrap(node).open === last.open) {
				last.body += wrap(node).body;
				continue;
			}
			const w = pure(node) ? wrap(node) : null;
			merged.push(w ? { node, ...w } : { node, text: text(node) });
		}
		out += group.open + merged.map((x) => x.text ?? x.open + x.body + x.close).join("") + "</g>";
	}
	return out;
}

/** A pivot-pattern group split into its opening tags, its body and its closing tags. */
function pivotParts(markup, node) {
	const one = (n) => n.kids.length === 1 && n.kids[0];
	const inner = animated(node) ? node : one(node);
	if (!inner || !animated(inner)) return null;
	const back = inner === node ? null : one(inner);
	const body = back ?? inner;
	if (inner !== node && (!back || back.tag !== "g")) return null;
	const open = markup.slice(node.start, body.start + body.open.length);
	const close = markup.slice(body.end - 4, node.end);
	return { open, close, body: markup.slice(body.start + body.open.length, body.end - 4) };
}

// ------------------------------------------------------------------ overlap

// Whether a moving part can touch a still shape: the part as small boxes, one per shape and
// through every pose, the still shape as its real outline (filled polygons, stroked lines), so an
// eye can pass a hair cap above it, or a pair of glasses around it, without touching either.

const TOUCH = 3.5; // both shapes' ink wobble, plus antialiasing

/** One box per leaf shape of `node` through every pose of its animated groups, under `ms`. */
function leafBoxes(node, ms, ids, paint = { sw: 0, stroke: false }, out = []) {
	const a = node.attrs;
	if (HIDDEN.has(node.tag)) return out;
	let mats = a.transform ? ms.map((m) => mul(m, parseTransform(a.transform))) : ms;
	const poses = posesOf(a.class);
	if (poses) mats = mats.flatMap((m) => poses.map((pm) => mul(m, pm)));
	const own = {
		sw: a["stroke-width"] !== undefined ? Number(a["stroke-width"]) : paint.sw,
		stroke: a.stroke !== undefined ? a.stroke !== "none" : paint.stroke,
	};
	if (node.tag === "g" || node.tag === "svg") {
		for (const kid of node.kids) leafBoxes(kid, mats, ids, own, out);
	} else if (node.tag === "use") {
		const target = ids.get((a.href ?? "").slice(1));
		if (target) leafBoxes(target, mats, ids, own, out);
	} else {
		const bare = { ...node, attrs: { ...a, transform: "", class: "" } };
		const box = mats.reduce((b, m) => join(b, reach(bare, m, ids, own)), NONE);
		if (hasPoints(box)) out.push(grow(box, TOUCH));
	}
	return out;
}

/** Path data as polylines, its curves sampled, each with whether it closes. */
function flatten(d) {
	const tok = d.match(/[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/g) ?? [];
	const subs = [];
	let sub = null;
	let [i, cmd, x, y] = [0, "", 0, 0];
	const num = () => Number(tok[i++]);
	const to = (px, py) => {
		sub.pts.push([px, py]);
		[x, y] = [px, py];
	};
	while (i < tok.length) {
		if (/[A-Za-z]/.test(tok[i])) cmd = tok[i++];
		const rel = cmd === cmd.toLowerCase();
		const [ox, oy] = rel ? [x, y] : [0, 0];
		const C = cmd.toUpperCase();
		if (C === "M") {
			[x, y] = [ox + num(), oy + num()];
			sub = { pts: [[x, y]], closed: false };
			subs.push(sub);
			cmd = rel ? "l" : "L";
		} else if (C === "Z") {
			sub.closed = true;
			[x, y] = sub.pts[0];
		} else if (C === "L" || C === "T") to(ox + num(), oy + num());
		else if (C === "H") to(ox + num(), y);
		else if (C === "V") to(x, oy + num());
		else if (C === "C" || C === "S" || C === "Q") {
			const n = C === "C" ? 3 : 2;
			const pts = [[x, y]];
			for (let j = 0; j < n; j++) pts.push([ox + num(), oy + num()]);
			for (let s = 1; s <= 8; s++) {
				const t = s / 8;
				const c =
					n === 3
						? [(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3]
						: [(1 - t) ** 2, 2 * (1 - t) * t, t * t];
				sub.pts.push([0, 1].map((k) => pts.reduce((sum, p, j) => sum + p[k] * c[j], 0)));
			}
			[x, y] = pts[n];
		} else if (C === "A") {
			const [rx, ry, phi, large, sweep] = [num(), num(), num(), num(), num()];
			const [ex, ey] = [ox + num(), oy + num()];
			const arc = [];
			arcPoints(x, y, rx, ry, phi, large, sweep, ex, ey, arc);
			sub.pts.push(...arc.slice(1), arc[0]);
			[x, y] = [ex, ey];
		} else i++;
	}
	return subs;
}

/** The still shapes of `node` under matrix `m`: { subs, fill, evenodd, sw, box } each. */
function outlines(node, m, ids, paint = { sw: 0, stroke: false, fill: true }, out = []) {
	const a = node.attrs;
	if (HIDDEN.has(node.tag)) return out;
	const local = a.transform ? mul(m, parseTransform(a.transform)) : m;
	const own = {
		sw: a["stroke-width"] !== undefined ? Number(a["stroke-width"]) : paint.sw,
		stroke: a.stroke !== undefined ? a.stroke !== "none" : paint.stroke,
		fill: a.fill !== undefined ? a.fill !== "none" : paint.fill,
		evenodd: a["fill-rule"] !== undefined ? a["fill-rule"] === "evenodd" : paint.evenodd,
	};
	const clip = /url\(#([^)]+)\)/.exec(a["clip-path"] ?? "");
	if (clip && ids.has(clip[1])) {
		// whatever a clipped group draws stays inside its clip shape: take that shape, filled
		const fill = { sw: 0, stroke: false, fill: true };
		for (const kid of ids.get(clip[1]).kids) outlines(kid, local, ids, fill, out);
		return out;
	}
	const add = (subs) => {
		const pts = subs.map((s) => ({ ...s, pts: s.pts.map((p) => apply(local, p)) }));
		const sw = own.stroke ? own.sw * scaleOf(local) : 0;
		const box = pts.flatMap((s) => s.pts).reduce((b, [x, y]) => join(b, [x, y, x, y]), NONE);
		out.push({ subs: pts, fill: own.fill, evenodd: own.evenodd, sw, box: grow(box, sw / 2) });
	};
	const n = (key) => Number(a[key] ?? 0);
	if (node.tag === "path") add(flatten(a.d ?? ""));
	else if (node.tag === "circle" || node.tag === "ellipse") {
		const [rx, ry] = node.tag === "circle" ? [n("r"), n("r")] : [n("rx"), n("ry")];
		const pts = [];
		for (let i = 0; i < 24; i++) {
			const t = (i / 24) * Math.PI * 2;
			pts.push([n("cx") + rx * Math.cos(t), n("cy") + ry * Math.sin(t)]);
		}
		add([{ pts, closed: true }]);
	} else if (node.tag === "rect") {
		const [x, y, w, h] = [n("x"), n("y"), n("width"), n("height")];
		add([
			{
				pts: [
					[x, y],
					[x + w, y],
					[x + w, y + h],
					[x, y + h],
				],
				closed: true,
			},
		]);
	} else if (node.tag === "use") {
		const target = ids.get((a.href ?? "").slice(1));
		if (target) outlines(target, local, ids, own, out);
	} else for (const kid of node.kids) outlines(kid, local, ids, own, out);
	return out;
}

/** Whether segment p-q crosses box r (Liang-Barsky). */
function crosses([x1, y1], [x2, y2], r) {
	let [t0, t1] = [0, 1];
	const [dx, dy] = [x2 - x1, y2 - y1];
	for (const [p, q] of [
		[-dx, x1 - r[0]],
		[dx, r[2] - x1],
		[-dy, y1 - r[1]],
		[dy, r[3] - y1],
	]) {
		if (p === 0) {
			if (q < 0) return false;
		} else {
			const t = q / p;
			if (p < 0) t0 = Math.max(t0, t);
			else t1 = Math.min(t1, t);
			if (t0 > t1) return false;
		}
	}
	return true;
}

/** Whether point (x, y) is inside a filled shape's polygons (nonzero or even-odd). */
function inside([x, y], shape) {
	let wind = 0;
	for (const { pts } of shape.subs) {
		for (let i = 0; i < pts.length; i++) {
			const [a, b] = [pts[i], pts[(i + 1) % pts.length]];
			if (a[1] <= y && b[1] > y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) > 0)
				wind++;
			else if (a[1] > y && b[1] <= y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) < 0)
				wind--;
		}
	}
	return shape.evenodd ? wind % 2 !== 0 : wind !== 0;
}

/** Whether box `r` touches still shape `shape` (its fill or its stroke). */
function touches(r, shape) {
	if (isEmpty(meet(r, shape.box))) return false;
	if (shape.fill) {
		const corners = [
			[r[0], r[1]],
			[r[2], r[1]],
			[r[2], r[3]],
			[r[0], r[3]],
		];
		if (corners.some((c) => inside(c, shape))) return true;
		for (const { pts } of shape.subs) {
			for (let i = 0; i < pts.length; i++)
				if (crosses(pts[i], pts[(i + 1) % pts.length], r)) return true;
		}
	}
	if (shape.sw) {
		const wide = grow(r, shape.sw / 2);
		for (const { pts, closed } of shape.subs) {
			const end = closed ? pts.length : pts.length - 1;
			if (pts.length === 1 && crosses(pts[0], pts[0], wide)) return true;
			for (let i = 0; i < end; i++)
				if (crosses(pts[i], pts[(i + 1) % pts.length], wide)) return true;
		}
	}
	return false;
}

// ------------------------------------------------------------------ motion layer

// Every head again, alone on a transparent sheet laid over the base, in the still's order:
//  - a white outline (the base's halo filter only rings what stays put) for each head that meets
//    the black band, at the very bottom: its silhouettes dilated by the halo's 3.2 units, moving
//    with the head and clipped to the band;
//  - each moving part in its head's animated group, its runs of still shapes under ink filters;
//  - "covers": copies of the still shapes drawn after a moving part (its own collar and torso,
//    neighbours, the row in front) wherever that part can touch them or a white outline reaches,
//    clipped to those boxes, so they stay in front of it just as in the still.
// The shapes are written exactly as in the still, so baking the wobble into them gives all three
// files the same lines.

const BAND = Math.round(ROWS[0].y + ROWS[0].s * 128); // the white backing starts here
const SLACK = 2.5; // ink wobble and antialiasing round every box
const HALO = 3.2;

const MOTION_DEFS = [
	"<defs>",
	'<filter id="ink" x="-30%" y="-30%" width="160%" height="160%">',
	...INK_WOBBLE,
	"</filter>",
	// the still's ink and halo in one filter, without the drawing: only the white rim round a
	// head's wobbled white silhouette (one filter, as two nested ones would cost a layer and a
	// surface). Each run of silhouettes sits in a viewport that stops it just below the band.
	'<filter id="rim" x="-50%" y="-50%" width="200%" height="200%">',
	...INK_WOBBLE.map((line) =>
		line.replace("<feDisplacementMap ", '<feDisplacementMap result="w" '),
	),
	`<feMorphology in="w" operator="dilate" radius="${HALO}" result="d"/>`,
	'<feFlood flood-color="#fff"/>',
	'<feComposite in2="d" operator="in"/>',
	"</filter>",
	...DEFS.split("\n").filter((line) => /^(<pattern|<g id="flower")/.test(line)),
	'<g id="flower-sil" fill="#fff" stroke="#fff" stroke-width="2">' +
		PETALS.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5.4"/>`).join("") +
		"</g>",
	"</defs>",
];

/** `body` (root space) in figure `fig`'s head group, moving about its neck point. */
function headGroup(fig, body) {
	const [x, y] = fig.neck;
	return (
		`<g transform="translate(${f(x)} ${f(y)})"><g class="cr-head cr-h${fig.n}">` +
		`<g transform="translate(${f(-x)} ${f(-y)})">${body}</g></g></g>`
	);
}

/** The top-level shapes of `markup`, kept together where they share an id (a clipped shape). */
function pieces(markup) {
	const out = [];
	let open = null;
	for (const kid of parseSvg(markup).kids) {
		const text = markup.slice(kid.start, kid.end);
		const refs = [...text.matchAll(/(?:href="#|url\(#)([^")]+)/g)].map((m) => m[1]);
		if (open && refs.some((r) => open.ids.has(r))) {
			open.text += text;
			open.nodes.push(kid);
			idsOf(kid, open.ids);
			continue;
		}
		open = { text, nodes: [kid], ids: idsOf(kid) };
		out.push(open);
	}
	return out;
}

/**
 * The union of `rects` as disjoint rects: horizontal slabs between their edges, each split into
 * the runs of x it covers, with matching slabs joined back up.
 */
function disjoint(rects) {
	const ys = [...new Set(rects.flatMap((r) => [r[1], r[3]]))].sort((a, b) => a - b);
	const out = [];
	let open = [];
	for (let i = 0; i < ys.length - 1; i++) {
		const [y0, y1] = [ys[i], ys[i + 1]];
		const spans = rects
			.filter((r) => r[1] <= y0 && r[3] >= y1)
			.map((r) => [r[0], r[2]])
			.sort((a, b) => a[0] - b[0]);
		const merged = [];
		for (const [x0, x1] of spans) {
			const last = merged[merged.length - 1];
			if (last && x0 <= last[1]) last[1] = Math.max(last[1], x1);
			else merged.push([x0, x1]);
		}
		const next = [];
		for (const [x0, x1] of merged) {
			let r = open.find((o) => o[0] === x0 && o[2] === x1 && o[3] === y0);
			if (r) r[3] = y1;
			else out.push((r = [x0, y0, x1, y1]));
			next.push(r);
		}
		open = next;
	}
	return out;
}

/**
 * `body` (root space) clipped to box `b` by a nested <svg> viewport, a rect clip that the
 * compositor applies as it draws; a clipPath round a composited layer becomes a mask surface.
 */
function viewport(b, body) {
	const [x, y, w, h] = [b[0], b[1], b[2] - b[0], b[3] - b[1]].map(f);
	const view = `x="${x}" y="${y}" width="${w}" height="${h}" viewBox="${x} ${y} ${w} ${h}"`;
	return `<svg ${view} overflow="hidden">${body}</svg>`;
}

/**
 * The motion layer's items in the still's order: each moving part in its head group with the
 * box it can reach, and each still shape with its box. A figure's moving parts are joined into
 * one wherever the still shapes between them can't touch the earlier one (so the hair behind a
 * head moves in the head's own group, with no layers for the torso between them). Also sets
 * every figure's `reach`.
 */
function layout(figs) {
	const defsIds = idsOf(parseSvg(MOTION_DEFS.join("")));
	const items = [];
	const moverBox = (fig, markup) => {
		const tree = parseSvg(headGroup(fig, `<g transform="${fig.at}">${markup}</g>`));
		return grow(reach(tree, ID, new Map([...defsIds, ...idsOf(tree)])), SLACK);
	};
	for (const fig of figs) {
		fig.reach = NONE;
		const flat = [];
		for (const part of fig.parts) {
			if (!part.markup) continue;
			if (part.move) {
				flat.push({ move: true, markup: part.markup, box: moverBox(fig, part.markup) });
				continue;
			}
			for (const piece of pieces(part.markup)) {
				const ids = new Map([...defsIds, ...piece.ids]);
				const box = piece.nodes.reduce((b, node) => join(b, reach(node, fig.m, ids)), NONE);
				if (hasPoints(box)) flat.push({ fig, markup: piece.text, box: grow(box, SLACK) });
			}
		}
		for (let i = 0; i < flat.length; i++) {
			const j = flat.findIndex((x, k) => k > i && x.move);
			if (!flat[i].move || j < 0) continue;
			if (flat.slice(i + 1, j).every((x) => isEmpty(meet(x.box, flat[i].box)))) {
				const markup = flat[i].markup + flat[j].markup;
				flat[j] = { move: true, markup, box: join(flat[i].box, flat[j].box) };
				flat.splice(i--, 1);
			}
		}
		for (const item of flat) {
			if (!item.move) {
				items.push(item);
				continue;
			}
			const local = floatUp(
				joinTilts(item.markup),
				fig.m,
				new Map([...defsIds, ...idsOf(parseSvg(item.markup))]),
			);
			const markup = headGroup(
				fig,
				pushFilters(`<g transform="${fig.at}">${local}</g>`, inkRun, ROOT_INK),
			);
			items.push({ move: true, fig, markup, box: item.box });
			fig.reach = join(fig.reach, item.box);
		}
	}
	return items;
}

function assemble(figs, items) {
	// the white outlines, for the heads whose reach crosses into the black band: each run of
	// silhouettes in a viewport round it that stops a little below the band, where the white
	// backing starts (and the covers stop), whether its rim comes from the filter or is baked
	const defsIds = idsOf(parseSvg(MOTION_DEFS.join("")));
	const rims = [];
	for (const fig of figs) {
		if (!fig.sil) continue;
		const markup = `<g transform="${fig.at}">${fig.sil}</g>`;
		const ids = new Map([...defsIds, ...idsOf(parseSvg(markup))]);
		const rimRun = (body, run, ctm) => {
			const box = run.reduce((b, node) => join(b, reach(node, ctm, ids)), NONE);
			const clip = meet(grow(box, HALO + SLACK), [-Infinity, -Infinity, Infinity, BAND + 16]);
			return isEmpty(clip) ? "" : viewport(clip, `<g filter="url(#rim)">${body}</g>`);
		};
		const body = pushFilters(markup, rimRun, true);
		const box = meet(grow(fig.reach, HALO + SLACK), [-Infinity, -Infinity, Infinity, BAND + 26]);
		rims.push({ box, markup: headGroup(fig, body) });
	}
	// covers: every still shape drawn after a moving part, wherever that part (or any white
	// outline) can reach, clipped to those boxes; each run of them between two moving parts
	// shares one group, one clip and one filter
	const reached = [];
	const out = [];
	let run = [];
	let covers = 0;
	// A shape can show in more than one cover box: it is drawn in full in the first one, as a
	// group with an id, and <use>d in the others, so it is written (and baked) once and every id
	// stays unique. Neighbouring shapes of one figure share its transform.
	let shared = 0;
	const flush = () => {
		const rects = run.flatMap((item) => item.rects).map((b) => b.map((v) => Number(f(v))));
		const boxes = disjoint(rects)
			.map((box) => ({ box, inside: run.filter((item) => !isEmpty(meet(item.box, box))) }))
			.filter(({ inside }) => inside.length);
		const seen = new Map();
		for (const { inside } of boxes)
			for (const item of inside) seen.set(item, (seen.get(item) ?? 0) + 1);
		const ids = new Map();
		for (const { box, inside } of boxes) {
			covers += 1;
			let body = "";
			let at = null;
			for (const item of inside) {
				if (item.fig.at !== at) body += `${at ? "</g>" : ""}<g transform="${(at = item.fig.at)}">`;
				if (seen.get(item) === 1) body += item.markup;
				else if (ids.has(item)) body += `<use href="#${ids.get(item)}"/>`;
				else {
					ids.set(item, `c${++shared}`);
					body += `<g id="${ids.get(item)}">${item.markup}</g>`;
				}
			}
			out.push(viewport(box, `<g filter="url(#ink)">${body}</g></g>`));
		}
		run = [];
	};
	// A still shape needs a cover only where a moving part drawn before it can actually touch it
	// (any of the part's shapes, through all its poses): its cover box is the part of its own box
	// that those shapes reach. Under a white outline, which paints all over its box, every shape
	// in the box is covered.
	let last = null;
	for (const item of items) {
		if (item.move) {
			flush();
			if (item.fig !== last) out.push(`<!-- ${describe(item.fig.k)} -->`);
			last = item.fig;
			out.push(item.markup);
			const tree = parseSvg(item.markup);
			const leaves = leafBoxes(tree, [ID], new Map([...defsIds, ...idsOf(tree)]));
			reached.push({ box: item.box, leaves });
			continue;
		}
		let shapes = null;
		const rects = [];
		for (const { box, leaves } of reached) {
			if (isEmpty(meet(box, item.box))) continue;
			if (!shapes) {
				const tree = parseSvg(item.markup);
				const ids = new Map([...defsIds, ...idsOf(tree)]);
				shapes = tree.kids.flatMap((node) => outlines(node, item.fig.m, ids));
			}
			const hit = leaves.filter((r) => shapes.some((sh) => touches(r, sh)));
			const reach = meet(
				hit.reduce((b, r) => join(b, r), NONE),
				item.box,
			);
			if (!isEmpty(reach)) rects.push(reach);
		}
		for (const rim of rims)
			if (!isEmpty(meet(rim.box, item.box))) rects.push(meet(rim.box, item.box));
		if (rects.length) run.push({ ...item, rects });
	}
	flush();
	const anims = [...ANIMS.values()];
	const families = [...new Set(anims.map((a) => `.cr-${a.family}`))].join(",");
	const svg = [
		'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1100" width="1600" height="1100" ' +
			'aria-hidden="true">',
		...MOTION_DEFS,
		"<style>",
		`${families}{transform-origin:0 0}`,
		...anims.map((a) => a.rule),
		...anims.map((a) => a.keys).filter(Boolean),
		"@media (prefers-reduced-motion: reduce) {",
		`${families}{animation:none!important}`,
		"}",
		"</style>",
		'<g stroke-linecap="round" stroke-linejoin="round">',
		...rims.map((rim) => rim.markup),
		...out,
		"</g>",
		"</svg>",
		"",
	].join("\n");
	return { svg, covers, rims: rims.length };
}

function build() {
	const crowd = castCrowd();
	// pass 1: the still and the base, which leaves out every moving part
	const drawn = crowd.map((k, i) => {
		jit = mulberry32(SEED + i * 7919);
		figure = { n: i, s: Number(k.s.toFixed(3)), eyes: [], tilt: 0, cy: 0 };
		const at = `translate(${f(k.x)} ${f(k.y)}) scale(${k.s.toFixed(3)})`;
		const parts = DRAW[k.kind](k);
		const still = parts.map((part) => part.markup).join("");
		const base = parts
			.filter((part) => !part.move)
			.map((part) => part.markup)
			.join("");
		return [still, base].map((body) => `<!-- ${describe(k)} --><g transform="${at}">${body}</g>`);
	});
	const rows = ROWS.map((_, r) =>
		[0, 1].map((j) => {
			const figures = drawn.filter((_, i) => crowd[i].r === r).map((g) => g[j]);
			return `<!-- row ${r + 1} -->\n<g>${figures.join("\n")}</g>`;
		}),
	);
	// Paper behind every row below the back row's shoulders, so no black shows through.
	const page = (j) =>
		[
			'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1100" width="1600" ' +
				'height="1100" role="img">',
			"<title>A dense, cheerful crowd of original Storyfolk kids and creatures in hats, hoods, " +
				"glasses and headphones, with two robots, two foxes, a frog, bear-hooded kids and a " +
				"mushroom sprite peeking out among them</title>",
			DEFS,
			`<rect x="-40" y="${BAND}" width="1680" height="${1140 - BAND}" fill="#fff"/>`,
			'<g filter="url(#halo)">' +
				'<g stroke-linecap="round" stroke-linejoin="round" filter="url(#ink)">',
			rows.map((row) => row[j]).join("\n"),
			"</g></g>",
			"</svg>",
			"",
		].join("\n");

	// pass 2: every figure again, with its moving parts in their animated groups
	const plans = planHeads(crowd);
	MOTION = true;
	uid = 0;
	const begin = (k, i) => {
		jit = mulberry32(SEED + i * 7919);
		const side = sideOf(k);
		figure = { n: i, s: Number(k.s.toFixed(3)), eyes: [], tilt: 0, cy: 0, head: k.move, side };
	};
	const figs = crowd.map((k, i) => {
		begin(k, i);
		const parts = DRAW[k.kind](k);
		const s = Number(k.s.toFixed(3));
		const at = `translate(${f(k.x)} ${f(k.y)}) scale(${k.s.toFixed(3)})`;
		const neck = [Number(f(k.x)), Number(f(Number(f(k.y)) + s * figure.cy))];
		return { k, n: i, at, m: parseTransform(at), neck, parts, sil: "" };
	});
	const items = layout(figs);
	// pass 3: silhouettes of the heads that can reach the black band, for their white outline
	SIL = true;
	for (const fig of figs) {
		if (fig.reach[1] - HALO - SLACK >= BAND) continue;
		begin(fig.k, fig.n);
		fig.sil = DRAW[fig.k.kind](fig.k)
			.filter((part) => part.move)
			.map((part) => part.markup)
			.join("");
	}
	SIL = false;
	MOTION = false;
	const motion = assemble(figs, items);
	return { still: page(0), base: page(1), motion, plans, figs };
}

const out = build();
for (const [path, svg] of [
	[OUT, out.still],
	[OUT_BASE, out.base],
	[OUT_MOTION, out.motion.svg],
]) {
	writeFileSync(path, svg);
	console.log(`wrote ${path} (${(svg.length / 1024).toFixed(0)} KB)`);
}
const load = headLoad(out.plans, 600);
const mean = load.reduce((sum, v) => sum + v, 0) / load.length;
const sorted = [...load].sort((a, b) => a - b);
console.log(
	`${out.figs.length} heads move; ${ANIMS.size} animations; ${out.motion.covers} covers, ` +
		`${out.motion.rims} white outlines; heads moving at once over 10 min: mean ` +
		`${mean.toFixed(1)} (${((mean / out.figs.length) * 100).toFixed(0)}%), ` +
		`p95 ${sorted[Math.floor(sorted.length * 0.95)]}, max ${sorted[sorted.length - 1]}`,
);
