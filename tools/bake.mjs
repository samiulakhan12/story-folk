// Storyfolk ink bake: rewrites an SVG so that it draws without any runtime SVG filter.
//
// The drawings get their hand-inked wobble from an "ink" filter (feTurbulence feeding
// feDisplacementMap) and, around some characters, a white outline from a "halo" filter
// (feMorphology dilate under a white flood). Browsers re-run those filters on every raster tile
// and on every frame of a moving part, mostly on the CPU in Safari and Firefox, which made them
// the dominant rendering cost. This tool bakes both into plain geometry:
//
//   ink    Every shape under an ink filter has its points moved by the same noise the filter
//          used: the SVG specification's seeded Perlin turbulence, reproduced exactly from the
//          filter's own baseFrequency, numOctaves, seed and scale. The noise is read in each
//          shape's local coordinates (its own attribute values, ignoring parent transforms), so
//          a shape that the still, the base and the motion file write with the same path data
//          gets the same wobble in all three. Segments are split wherever the noise bends them
//          (a split straight line becomes a smooth curve through its moved points, so straight
//          edges wobble too); arcs become cubics; circles, ellipses and rects become paths unless
//          the noise moves them whole (dots, rivets); lines, polylines and polygons become paths.
//          Shapes inside <clipPath> and <mask> are baked too, so their edges stay on the art
//          they mirror. <pattern> contents (the halftone tiles) and <style> are never touched.
//   halo   The group becomes a plain group that first paints a white copy of its content (every
//          fill white, every stroke white and widened to reach as far as the dilation did), then
//          the content itself. Copied shapes that end up hidden under opaque content, under
//          white copies already kept, or over paper that is already white are dropped, and long
//          outlines are trimmed to the stretches that show (a coarse raster of what covers what
//          decides), so in the end only the rim of each silhouette is copied.
//
// Any other kind of filter is reported and left alone, unreferenced filters are removed, numbers
// in baked geometry are rounded to 1 decimal, outlines drawn more than once (a clip path, a fill
// and a stroke of the same shape) are written once and drawn with <use>, and comments and
// indentation are stripped. The output is deterministic, and a file without filters (a baked
// one, say) is left as it is, byte for byte.
//
// usage: node tools/bake.mjs <in.svg> [out.svg]        (writes to stdout without out.svg)
//        node tools/bake.mjs --in-place assets/*.svg

import { readFileSync, realpathSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// ------------------------------------------------------------------ tuning

// How far a baked edge may stray from the exact wobble the filter drew, in user units of the
// shape's own coordinates. A segment whose moved ends and control points would bend further
// than this from the truly moved segment is split, so long edges wobble along their length like
// the filtered ones did while short or gently bent pieces cost no extra points. At the site's
// sizes half a unit is under a CSS pixel; the output's 1-decimal rounding adds 0.05.
const TOLERANCE = 0.5;
// The same for curves, whose bends already read as hand drawn: their wobble may be looser.
const CURVE_TOLERANCE = 1;
// Deepest split of one original segment (2^7 = 128 pieces).
const MAX_DEPTH = 7;
// A curve whose first control point lies this close to the mirror of the previous curve's last
// one is written with the s or t shorthand (shifting the curve by under half of this).
const SMOOTH = 0.15;
// Circles, ellipses and rects at most this big keep their element and only move: dots, rivets
// and pupils would gain bytes but no visible wobble as paths. So do bigger ones whose whole
// outline the noise moves alike, to within TOLERANCE.
const TINY = 6;
// feMorphology dilates with a square kernel: its white reaches r straight out from an edge but
// up to r * sqrt(2) along a diagonal, 4r / pi on average around a curve. A round white stroke
// of 2 * 1.2r covers the same white as the filter did (measured over the black crowd band).
const HALO_REACH = 1.2;
// Fixed-point iterations of the inverse displacement (the filter samples the source at
// P + d(P), so a point Q of the art shows up at the P where P + d(P) = Q).
const INVERSE_STEPS = 4;
// Halo culling: raster cell size in root units, and how far around the copy a cell must still
// count as covered before the copy is dropped.
const CELL = 1;
const CULL_MARGIN = 1.5;

// ------------------------------------------------------------------ XML

// Elements whose text is content (a <style> sheet, a <title>): their whitespace is kept.
const KEEP_SPACE = new Set(["style", "title", "desc", "text", "tspan", "textPath", "script"]);

const XML_NAME = /<([^\s/>!?]+)/y;
const XML_ATTR = /\s*([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/y;
const XML_END = /\s*(\/?)>/y;

/**
 * Parses XML into nodes: elements {type: "el", name, attrs: [[name, raw value]], kids}, text
 * {type: "text", text} and verbatim {type: "raw", text} (declaration, doctype, CDATA). Comments
 * are dropped, and so is whitespace between elements outside the KEEP_SPACE ones.
 */
function parseXml(src) {
	const root = { type: "el", name: "#document", attrs: [], kids: [] };
	const stack = [root];
	const top = () => stack[stack.length - 1];
	const text = (t) => {
		if (/\S/.test(t) || stack.some((el) => KEEP_SPACE.has(el.name)))
			top().kids.push({ type: "text", text: t });
	};
	let i = 0;
	while (i < src.length) {
		const lt = src.indexOf("<", i);
		if (lt < 0) {
			text(src.slice(i));
			break;
		}
		if (lt > i) text(src.slice(i, lt));
		const until = (marker, from) => {
			const end = src.indexOf(marker, from);
			if (end < 0) throw new Error(`unterminated markup at offset ${lt}`);
			return end + marker.length;
		};
		if (src.startsWith("<!--", lt)) {
			i = until("-->", lt + 4);
		} else if (src.startsWith("<![CDATA[", lt)) {
			i = until("]]>", lt);
			top().kids.push({ type: "raw", text: src.slice(lt, i) });
		} else if (src.startsWith("<?", lt)) {
			i = until("?>", lt);
			top().kids.push({ type: "raw", text: src.slice(lt, i) });
		} else if (src.startsWith("<!", lt)) {
			// A doctype, which may carry an internal subset in brackets.
			let depth = 0;
			let j = lt + 2;
			for (; j < src.length; j++) {
				if (src[j] === "[") depth++;
				else if (src[j] === "]") depth--;
				else if (src[j] === ">" && depth === 0) break;
			}
			i = j + 1;
			top().kids.push({ type: "raw", text: src.slice(lt, i) });
		} else if (src[lt + 1] === "/") {
			i = until(">", lt);
			const name = src.slice(lt + 2, i - 1).trim();
			if (top().name !== name) throw new Error(`</${name}> closes <${top().name}>`);
			stack.pop();
		} else {
			XML_NAME.lastIndex = lt;
			const name = XML_NAME.exec(src);
			if (!name) throw new Error(`bad tag at offset ${lt}`);
			const el = { type: "el", name: name[1], attrs: [], kids: [] };
			let at = XML_NAME.lastIndex;
			for (;;) {
				XML_ATTR.lastIndex = at;
				const a = XML_ATTR.exec(src);
				if (!a) break;
				el.attrs.push([a[1], a[2] ?? a[3].replace(/"/g, "&quot;")]);
				at = XML_ATTR.lastIndex;
			}
			XML_END.lastIndex = at;
			const end = XML_END.exec(src);
			if (!end) throw new Error(`bad tag <${el.name}> at offset ${lt}`);
			i = XML_END.lastIndex;
			top().kids.push(el);
			if (!end[1]) stack.push(el);
		}
	}
	if (stack.length > 1) throw new Error(`<${top().name}> is never closed`);
	return root;
}

function serializeXml(node, out = []) {
	for (const kid of node.kids) {
		if (kid.type !== "el") out.push(kid.text);
		else {
			out.push("<", kid.name);
			for (const [k, v] of kid.attrs) out.push(" ", k, '="', v, '"');
			if (!kid.kids.length) out.push("/>");
			else {
				out.push(">");
				serializeXml(kid, out);
				out.push("</", kid.name, ">");
			}
		}
	}
	return out;
}

const getAttr = (el, k) => el.attrs.find((a) => a[0] === k)?.[1];
const delAttr = (el, ...ks) => (el.attrs = el.attrs.filter((a) => !ks.includes(a[0])));
function setAttr(el, k, v) {
	const a = el.attrs.find((x) => x[0] === k);
	if (a) a[1] = v;
	else el.attrs.push([k, v]);
}
const element = (name, attrs = [], kids = []) => ({ type: "el", name, attrs, kids });
const elements = (node) => node.kids.filter((k) => k.type === "el");
const decode = (v) =>
	v
		.replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
		.replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d))
		.replace(/&quot;/g, '"')
		.replace(/&apos;/g, "'")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&amp;/g, "&");
const urlRef = (v) =>
	v ? /^\s*url\(\s*['"]?#([^'")\s]+)['"]?\s*\)/.exec(decode(v))?.[1] : undefined;
const hrefRef = (el) => {
	const v = getAttr(el, "href") ?? getAttr(el, "xlink:href");
	return v && decode(v).startsWith("#") ? decode(v).slice(1) : undefined;
};

// ------------------------------------------------------------------ styles and paint

const SHAPES = new Set(["path", "circle", "ellipse", "rect", "line", "polyline", "polygon"]);
// Containers whose children are drawn, and elements that are never drawn where they stand.
const GROUPS = new Set(["g", "a", "switch"]);

/** Every never-drawn element (clip path, mask, defs...) among `kids` and their descendants,
 * without looking inside the ones it finds. */
function definitionsIn(kids) {
	const found = [];
	for (const k of kids) {
		if (k.type !== "el") continue;
		if (NOT_DRAWN.has(k.name)) found.push(k);
		else found.push(...definitionsIn(k.kids ?? []));
	}
	return found;
}
const NOT_DRAWN = new Set([
	"defs",
	"clipPath",
	"mask",
	"pattern",
	"filter",
	"marker",
	"symbol",
	"style",
	"title",
	"desc",
	"metadata",
	"linearGradient",
	"radialGradient",
	"script",
]);
const INHERITED = [
	"fill",
	"stroke",
	"stroke-width",
	"stroke-linejoin",
	"stroke-linecap",
	"fill-opacity",
	"stroke-opacity",
	"fill-rule",
	"visibility",
];

/** Presentation properties of one element: its attributes, overridden by its style="". */
function ownStyle(el) {
	const props = {};
	for (const [k, v] of el.attrs) props[k] = decode(v).trim();
	const style = getAttr(el, "style");
	if (style) {
		for (const decl of decode(style).split(";")) {
			const c = decl.indexOf(":");
			if (c > 0) props[decl.slice(0, c).trim()] = decl.slice(c + 1).trim();
		}
	}
	return props;
}

/** The inherited paint state after `el`, from its parent's state `inh`. */
function inherit(inh, el) {
	const own = ownStyle(el);
	const out = { ...inh };
	for (const k of INHERITED) if (own[k] !== undefined && own[k] !== "inherit") out[k] = own[k];
	return out;
}

const isNone = (paint) => paint === undefined || paint === "none" || paint === "transparent";
const isWhite = (paint) =>
	/^(#fff|#ffffff|white|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))$/i.test(paint ?? "");

// ------------------------------------------------------------------ transforms

const IDENTITY = [1, 0, 0, 1, 0, 0];
const mul = (m, n) => [
	m[0] * n[0] + m[2] * n[1],
	m[1] * n[0] + m[3] * n[1],
	m[0] * n[2] + m[2] * n[3],
	m[1] * n[2] + m[3] * n[3],
	m[0] * n[4] + m[2] * n[5] + m[4],
	m[1] * n[4] + m[3] * n[5] + m[5],
];
const apply = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
// Uniform scale of a matrix (the square root of its area factor).
const scaleOf = (m) => Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2]));
// Largest stretch of a matrix (its largest singular value).
function stretchOf(m) {
	const [a, b, c, d] = m;
	const s = (a * a + b * b + c * c + d * d) / 2;
	const det = a * d - b * c;
	return Math.sqrt(s + Math.sqrt(Math.max(0, s * s - det * det)));
}

/** Parses a transform attribute into a matrix [a b c d e f]. */
function parseTransform(text) {
	let m = IDENTITY;
	if (!text) return m;
	const re = /(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)/g;
	for (let t; (t = re.exec(text)); ) {
		const v = (t[2].match(/[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/gi) || []).map(Number);
		const rad = ((v[0] || 0) * Math.PI) / 180;
		let n;
		if (t[1] === "matrix") n = v.length === 6 ? v : IDENTITY;
		else if (t[1] === "translate") n = [1, 0, 0, 1, v[0] || 0, v[1] || 0];
		else if (t[1] === "scale") n = [v[0] ?? 1, 0, 0, v[1] ?? v[0] ?? 1, 0, 0];
		else if (t[1] === "skewX") n = [1, 0, Math.tan(rad), 1, 0, 0];
		else if (t[1] === "skewY") n = [1, Math.tan(rad), 0, 1, 0, 0];
		else {
			const [cx, cy] = [v[1] || 0, v[2] || 0];
			const r = [Math.cos(rad), Math.sin(rad), -Math.sin(rad), Math.cos(rad), 0, 0];
			n = mul(mul([1, 0, 0, 1, cx, cy], r), [1, 0, 0, 1, -cx, -cy]);
		}
		m = mul(m, n);
	}
	return m;
}

/** The transform a nested <svg> applies: its x and y, and its viewBox fitted to its size. */
function viewportOf(svg) {
	const a = ownStyle(svg);
	const box = (a.viewBox ?? "").split(/[\s,]+/).map(Number);
	const x = parseFloat(a.x ?? "0") || 0;
	const y = parseFloat(a.y ?? "0") || 0;
	if (box.length !== 4 || !box.every(Number.isFinite) || box[2] <= 0 || box[3] <= 0)
		return [1, 0, 0, 1, x, y];
	const w = parseFloat(a.width ?? "") || box[2];
	const h = parseFloat(a.height ?? "") || box[3];
	const [align = "xMidYMid", fit = "meet"] = (a.preserveAspectRatio ?? "")
		.trim()
		.split(/\s+/)
		.filter(Boolean);
	let sx = w / box[2];
	let sy = h / box[3];
	let tx = x - box[0] * sx;
	let ty = y - box[1] * sy;
	if (align !== "none") {
		const k = fit === "slice" ? Math.max(sx, sy) : Math.min(sx, sy);
		const at = (part, size, span) =>
			part === "Min" ? 0 : part === "Max" ? size - span : (size - span) / 2;
		tx = x + at(align.slice(1, 4), w, box[2] * k) - box[0] * k;
		ty = y + at(align.slice(5, 8), h, box[3] * k) - box[1] * k;
		sx = sy = k;
	}
	return [sx, 0, 0, sy, tx, ty];
}

// ------------------------------------------------------------------ path geometry

// A path is a list of subpaths {x, y, segs, closed}; a segment is {t: "L", p}, {t: "Q", c, p}
// or {t: "C", c1, c2, p}, every point an absolute [x, y].

const PATH_NUM = /[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/y;

/** Parses path data into absolute subpaths of lines, quadratics and cubics (arcs -> cubics). */
function parsePath(d) {
	const subs = [];
	let i = 0;
	let x = 0;
	let y = 0;
	let sub = null;
	let lastC = null; // second control point of the previous cubic, for S
	let lastQ = null; // control point of the previous quadratic, for T
	const skip = () => {
		while (i < d.length && " \t\n\r\f,".includes(d[i])) i++;
	};
	const num = () => {
		skip();
		PATH_NUM.lastIndex = i;
		const m = PATH_NUM.exec(d);
		if (!m) throw new Error(`bad path data near "${d.slice(i, i + 16)}"`);
		i = PATH_NUM.lastIndex;
		return parseFloat(m[0]);
	};
	const flag = () => {
		skip();
		if (d[i] !== "0" && d[i] !== "1") throw new Error(`bad arc flag near "${d.slice(i, i + 16)}"`);
		return d[i++] === "1";
	};
	const more = () => {
		skip();
		return i < d.length && /[\d+\-.]/.test(d[i]);
	};
	const push = (seg) => {
		if (!sub || sub.closed) {
			// Drawing on after a close starts a new subpath at the closed one's start.
			sub = { x, y, segs: [], closed: false };
			subs.push(sub);
		}
		sub.segs.push(seg);
		[x, y] = seg.p;
	};
	while ((skip(), i < d.length)) {
		let cmd = d[i++];
		if (!/[MmLlHhVvCcSsQqTtAaZz]/.test(cmd)) throw new Error(`bad path command "${cmd}"`);
		do {
			const rel = cmd >= "a";
			const ox = rel ? x : 0;
			const oy = rel ? y : 0;
			const C = cmd.toUpperCase();
			let nextC = null;
			let nextQ = null;
			if (C === "M") {
				x = ox + num();
				y = oy + num();
				sub = { x, y, segs: [], closed: false };
				subs.push(sub);
				cmd = rel ? "l" : "L";
			} else if (C === "L") push({ t: "L", p: [ox + num(), oy + num()] });
			else if (C === "H") push({ t: "L", p: [ox + num(), y] });
			else if (C === "V") push({ t: "L", p: [x, oy + num()] });
			else if (C === "C") {
				const c1 = [ox + num(), oy + num()];
				const c2 = [ox + num(), oy + num()];
				push({ t: "C", c1, c2, p: [ox + num(), oy + num()] });
				nextC = c2;
			} else if (C === "S") {
				const c1 = lastC ? [2 * x - lastC[0], 2 * y - lastC[1]] : [x, y];
				const c2 = [ox + num(), oy + num()];
				push({ t: "C", c1, c2, p: [ox + num(), oy + num()] });
				nextC = c2;
			} else if (C === "Q") {
				const c = [ox + num(), oy + num()];
				push({ t: "Q", c, p: [ox + num(), oy + num()] });
				nextQ = c;
			} else if (C === "T") {
				const c = lastQ ? [2 * x - lastQ[0], 2 * y - lastQ[1]] : [x, y];
				push({ t: "Q", c, p: [ox + num(), oy + num()] });
				nextQ = c;
			} else if (C === "A") {
				const [rx, ry, rot, large, sweep] = [num(), num(), num(), flag(), flag()];
				const p = [ox + num(), oy + num()];
				for (const seg of arcToCubics(x, y, rx, ry, rot, large, sweep, p[0], p[1])) push(seg);
			} else {
				if (sub) {
					sub.closed = true;
					[x, y] = [sub.x, sub.y];
				}
			}
			lastC = nextC;
			lastQ = nextQ;
		} while (cmd.toUpperCase() !== "Z" && more());
	}
	return subs;
}

/** An SVG arc as cubics of at most 90 degrees each (SVG implementation notes, F.6.5). */
function arcToCubics(x1, y1, rx, ry, rotation, large, sweep, x2, y2) {
	if (x1 === x2 && y1 === y2) return [];
	rx = Math.abs(rx);
	ry = Math.abs(ry);
	if (!rx || !ry) return [{ t: "L", p: [x2, y2] }];
	const phi = (rotation * Math.PI) / 180;
	const cos = Math.cos(phi);
	const sin = Math.sin(phi);
	const hx = (x1 - x2) / 2;
	const hy = (y1 - y2) / 2;
	const xp = cos * hx + sin * hy;
	const yp = -sin * hx + cos * hy;
	const lambda = (xp * xp) / (rx * rx) + (yp * yp) / (ry * ry);
	if (lambda > 1) {
		rx *= Math.sqrt(lambda);
		ry *= Math.sqrt(lambda);
	}
	const num = rx * rx * ry * ry - rx * rx * yp * yp - ry * ry * xp * xp;
	const den = rx * rx * yp * yp + ry * ry * xp * xp;
	const co = (large === sweep ? -1 : 1) * Math.sqrt(Math.max(0, num / den));
	const cxp = (co * rx * yp) / ry;
	const cyp = (-co * ry * xp) / rx;
	const cx = cos * cxp - sin * cyp + (x1 + x2) / 2;
	const cy = sin * cxp + cos * cyp + (y1 + y2) / 2;
	const angle = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
	const ux = (xp - cxp) / rx;
	const uy = (yp - cyp) / ry;
	let start = angle(1, 0, ux, uy);
	let delta = angle(ux, uy, (-xp - cxp) / rx, (-yp - cyp) / ry);
	if (!sweep && delta > 0) delta -= 2 * Math.PI;
	else if (sweep && delta < 0) delta += 2 * Math.PI;
	const n = Math.max(1, Math.ceil(Math.abs(delta) / (Math.PI / 2) - 1e-9));
	const step = delta / n;
	const k = (4 / 3) * Math.tan(step / 4);
	const at = (u, v) => [cx + rx * u * cos - ry * v * sin, cy + rx * u * sin + ry * v * cos];
	const segs = [];
	for (let s = 0; s < n; s++, start += step) {
		const [ca, sa, cb, sb] = [
			Math.cos(start),
			Math.sin(start),
			Math.cos(start + step),
			Math.sin(start + step),
		];
		segs.push({
			t: "C",
			c1: at(ca - k * sa, sa + k * ca),
			c2: at(cb + k * sb, sb - k * cb),
			p: s === n - 1 ? [x2, y2] : at(cb, sb),
		});
	}
	return segs;
}

/** An ellipse as a closed path, from 3 o'clock clockwise like the element itself. */
function ellipseSubs(cx, cy, rx, ry) {
	const k = 0.5522847498307936;
	const pts = [
		[1, 0],
		[0, 1],
		[-1, 0],
		[0, -1],
		[1, 0],
	];
	const segs = [];
	for (let q = 0; q < 4; q++) {
		const [ax, ay] = pts[q];
		const [bx, by] = pts[q + 1];
		segs.push({
			t: "C",
			c1: [cx + rx * (ax - k * ay), cy + ry * (ay + k * ax)],
			c2: [cx + rx * (bx + k * by), cy + ry * (by - k * bx)],
			p: [cx + rx * bx, cy + ry * by],
		});
	}
	return [{ x: cx + rx, y: cy, segs, closed: true }];
}

/** A rect, with its rounded corners, as a closed path (SVG's equivalent path). */
function rectSubs(x, y, w, h, rx, ry) {
	if (rx === undefined && ry === undefined) rx = ry = 0;
	rx = Math.min(Math.abs(rx ?? ry), w / 2);
	ry = Math.min(Math.abs(ry ?? rx), h / 2);
	const L = (px, py) => ({ t: "L", p: [px, py] });
	if (!rx || !ry) {
		return [{ x, y, segs: [L(x + w, y), L(x + w, y + h), L(x, y + h), L(x, y)], closed: true }];
	}
	const arc = (x1, y1, x2, y2) => arcToCubics(x1, y1, rx, ry, 0, false, true, x2, y2);
	const segs = [
		L(x + w - rx, y),
		...arc(x + w - rx, y, x + w, y + ry),
		L(x + w, y + h - ry),
		...arc(x + w, y + h - ry, x + w - rx, y + h),
		L(x + rx, y + h),
		...arc(x + rx, y + h, x, y + h - ry),
		L(x, y + ry),
		...arc(x, y + ry, x + rx, y),
	];
	return [{ x: x + rx, y, segs, closed: true }];
}

const dist = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];

/** Splits a segment starting at p0 in two at parameter t (de Casteljau). */
function splitAt(p0, seg, t) {
	if (seg.t === "L") return [{ t: "L", p: lerp(p0, seg.p, t) }, seg];
	if (seg.t === "Q") {
		const a = lerp(p0, seg.c, t);
		const b = lerp(seg.c, seg.p, t);
		return [
			{ t: "Q", c: a, p: lerp(a, b, t) },
			{ t: "Q", c: b, p: seg.p },
		];
	}
	const a = lerp(p0, seg.c1, t);
	const b = lerp(seg.c1, seg.c2, t);
	const c = lerp(seg.c2, seg.p, t);
	const ab = lerp(a, b, t);
	const bc = lerp(b, c, t);
	return [
		{ t: "C", c1: a, c2: ab, p: lerp(ab, bc, t) },
		{ t: "C", c1: bc, c2: c, p: seg.p },
	];
}

/** The parameter that halves a curve's arc length (from 16 chords), so pieces come out even. */
function halfway(ctrl) {
	if (ctrl.length === 2) return 0.5;
	const n = 16;
	const acc = [0];
	let prev = ctrl[0];
	for (let k = 1; k <= n; k++) {
		const p = bezierAt(ctrl, k / n);
		acc.push(acc[k - 1] + dist(prev, p));
		prev = p;
	}
	const half = acc[n] / 2;
	let k = 1;
	while (k < n && acc[k] < half) k++;
	const span = acc[k] - acc[k - 1];
	return span > 0 ? (k - 1 + (half - acc[k - 1]) / span) / n : 0.5;
}

const controls = (p0, seg) =>
	seg.t === "L" ? [p0, seg.p] : seg.t === "Q" ? [p0, seg.c, seg.p] : [p0, seg.c1, seg.c2, seg.p];

/** The point at parameter t of a Bezier curve (or line) given by its control points. */
function bezierAt(ctrl, t) {
	let pts = ctrl;
	while (pts.length > 1) {
		const next = [];
		for (let k = 1; k < pts.length; k++) next.push(lerp(pts[k - 1], pts[k], t));
		pts = next;
	}
	return pts[0];
}

/**
 * Bakes a subpath: every end and control point goes through `move`, and a segment is first
 * split wherever the curve through the moved points would stray more than the tolerance from
 * the truly moved segment (checked every 2 units or so along it). A closed subpath's closing
 * line becomes an explicit segment first, so it wobbles too. A straight line that needed
 * splitting is drawn through its moved split points as a smooth curve (see smoothLine), not as
 * a polyline with corners.
 */
function bakeSubpath(sub, move) {
	const m = (p) => move(p[0], p[1]);
	const [x, y] = m([sub.x, sub.y]);
	const out = { x, y, segs: [], closed: sub.closed };
	const all = [...sub.segs];
	const start = [sub.x, sub.y];
	if (sub.closed && all.length && dist(all[all.length - 1].p, start) > 1e-9)
		all.push({ t: "L", p: start });
	const emit = (p0, seg, depth) => {
		const ctrl = controls(p0, seg);
		const moved = ctrl.map(m);
		const tolerance = seg.t === "L" ? TOLERANCE : CURVE_TOLERANCE;
		let length = 0;
		for (let k = 1; k < ctrl.length; k++) length += dist(ctrl[k - 1], ctrl[k]);
		const samples = Math.max(2, Math.ceil(length / 2));
		let worst = 0;
		for (let k = 1; k < samples && worst <= tolerance; k++) {
			const t = k / samples;
			worst = Math.max(worst, dist(m(bezierAt(ctrl, t)), bezierAt(moved, t)));
		}
		if (worst > tolerance && depth < MAX_DEPTH) {
			const [a, b] = splitAt(p0, seg, halfway(ctrl));
			emit(p0, a, depth + 1);
			emit(a.p, b, depth + 1);
			return;
		}
		const [, ...rest] = moved;
		out.segs.push(
			seg.t === "L"
				? { t: "L", p: rest[0] }
				: seg.t === "Q"
					? { t: "Q", c: rest[0], p: rest[1] }
					: { t: "C", c1: rest[0], c2: rest[1], p: rest[2] },
		);
	};
	let p0 = start;
	for (const seg of all) {
		if (seg.t !== "L") emit(p0, seg, 0);
		else {
			// A line is split into equal pieces (a smooth chain needs even spacing): as few as
			// keep every chord within the tolerance of the moved line.
			const length = dist(p0, seg.p);
			let points = null;
			for (let n = 1; !points && n <= 1 << MAX_DEPTH; n++) {
				const at = [...Array(n + 1).keys()].map((k) => lerp(p0, seg.p, k / n));
				const moved = at.map(m);
				const steps = Math.max(2, Math.ceil(length / n / 2));
				let fine = true;
				for (let k = 0; k < n && fine; k++) {
					for (let j = 1; j < steps && fine; j++) {
						const t = j / steps;
						fine = dist(m(lerp(at[k], at[k + 1], t)), lerp(moved[k], moved[k + 1], t)) <= TOLERANCE;
					}
				}
				if (fine || n === 1 << MAX_DEPTH) points = moved;
			}
			if (points.length === 2) out.segs.push({ t: "L", p: points[1] });
			else out.segs.push(...smoothLine(points));
		}
		p0 = seg.p;
	}
	return out;
}

/**
 * A smooth curve for a split straight line, through its moved split points D0..Dn: a chain of
 * quadratics from D0 to Dn whose k-th piece passes through Dk at its middle, and whose control
 * points mirror each other across the joints, so the chain is smooth and, after the first q,
 * every piece is written as a bare t endpoint (no more numbers than a polyline). The control
 * points solve a small tridiagonal system; the joints are then picked in whole tenths so that,
 * after rounding, each mirrored control point lands within a tenth of where it should be.
 */
function smoothLine(points) {
	const n = points.length - 1;
	const D = points.map(([x, y]) => [x * 10, y * 10]);
	// Piece k (1..n-1) runs from joint k-1 to joint k around control point Ck, where the inner
	// joints are the midpoints of neighbouring control points and the ends are D0 and Dn. Its
	// middle (start + 2Ck + end) / 4 must be Dk, which for the Ck reads
	//   piece 1:   2.5 C1 + 0.5 C2 = 4 D1 - D0      (only 2 C1 = 4 D1 - D0 - D2 when n = 2)
	//   inner:     0.5 Ck-1 + 3 Ck + 0.5 Ck+1 = 4 Dk
	//   piece n-1: 0.5 Cn-2 + 2.5 Cn-1 = 4 Dn-1 - Dn
	const m = n - 1;
	const C = [];
	for (const axis of [0, 1]) {
		const lo = [];
		const mid = [];
		const hi = [];
		const rhs = [];
		for (let k = 1; k <= m; k++) {
			const first = k === 1;
			const last = k === m;
			lo.push(first ? 0 : 0.5);
			hi.push(last ? 0 : 0.5);
			mid.push(first && last ? 2 : first || last ? 2.5 : 3);
			rhs.push(4 * D[k][axis] - (first ? D[0][axis] : 0) - (last ? D[n][axis] : 0));
		}
		// Thomas algorithm (the system is diagonally dominant, so no pivoting is needed).
		for (let k = 1; k < m; k++) {
			const w = lo[k] / mid[k - 1];
			mid[k] -= w * hi[k - 1];
			rhs[k] -= w * rhs[k - 1];
		}
		const x = new Array(m);
		x[m - 1] = rhs[m - 1] / mid[m - 1];
		for (let k = m - 2; k >= 0; k--) x[k] = (rhs[k] - hi[k] * x[k + 1]) / mid[k];
		x.forEach((v, k) => ((C[k] ??= [])[axis] = v));
	}
	const segs = [];
	let c = C[0].map(Math.round);
	for (let k = 0; k < m; k++) {
		const p =
			k === m - 1
				? D[n].map(Math.round)
				: [0, 1].map((i) => Math.floor((c[i] + C[k + 1][i]) / 2 + 0.5));
		segs.push({ t: "Q", c: [c[0] / 10, c[1] / 10], p: [p[0] / 10, p[1] / 10] });
		c = [2 * p[0] - c[0], 2 * p[1] - c[1]];
	}
	return segs;
}

// ------------------------------------------------------------------ path output

/** A coordinate in tenths of a unit, as short as SVG allows: 1.5, .5, -.5, 12. */
function tenths(t) {
	const a = Math.abs(t);
	const ip = Math.floor(a / 10);
	const fp = a % 10;
	const s = fp ? (ip ? `${ip}.${fp}` : `.${fp}`) : `${ip}`;
	return t < 0 ? `-${s}` : s;
}

/**
 * Writes subpaths as compact path data: absolute or relative moves (whichever is shorter),
 * relative segments, implicit repeats and no separators where the syntax allows. Coordinates
 * are rounded to tenths first and every relative step is taken between rounded points, so
 * rounding never accumulates along a path. Where a curve's first control point is within
 * SMOOTH of the mirror image of the previous one (a smooth joint, as between the pieces of a
 * split curve), it is written as s or t and the mirror image is drawn instead.
 */
function formatPath(subs) {
	let out = "";
	let cmd = "";
	let prev = "";
	let cx = 0;
	let cy = 0;
	const T = (v) => Math.round(v * 10) || 0;
	const put = (n) => {
		const s = tenths(n);
		if (prev && !(s[0] === "-" || (s[0] === "." && prev.includes(".")))) out += " ";
		out += s;
		prev = s;
	};
	const command = (c, force) => {
		if (force || c !== cmd) {
			out += c;
			prev = "";
		}
		cmd = c;
	};
	const rel = (p) => {
		put(p[0] - cx);
		put(p[1] - cy);
	};
	const near = (a, b) => b && Math.hypot(a[0] - b[0], a[1] - b[1]) <= SMOOTH * 10;
	for (const sub of subs) {
		const sx = T(sub.x);
		const sy = T(sub.y);
		const absolute = tenths(sx) + tenths(sy);
		const relative = tenths(sx - cx) + tenths(sy - cy);
		if (!out || absolute.length <= relative.length) {
			command("M", true);
			put(sx);
			put(sy);
		} else {
			command("m", true);
			put(sx - cx);
			put(sy - cy);
		}
		cmd = ""; // after a move, a bare pair would mean a line: always name the next command
		[cx, cy] = [sx, sy];
		let segs = sub.segs;
		// The closing piece back to the start is drawn by z itself.
		const last = segs[segs.length - 1];
		const back = last?.t === "L" && T(last.p[0]) === sx && T(last.p[1]) === sy;
		if (sub.closed && back && segs.length > 1) segs = segs.slice(0, -1);
		let lastC = null; // the previous cubic's second control point, in tenths
		let lastQ = null; // the previous quadratic's control point, in tenths
		for (const s of segs) {
			const p = [T(s.p[0]), T(s.p[1])];
			const mirror = (c) => c && [2 * cx - c[0], 2 * cy - c[1]];
			if (s.t === "C") {
				const c1 = [T(s.c1[0]), T(s.c1[1])];
				const c2 = [T(s.c2[0]), T(s.c2[1])];
				if (near(c1, mirror(lastC))) command("s");
				else {
					command("c");
					rel(c1);
				}
				rel(c2);
				lastC = c2;
				lastQ = null;
			} else if (s.t === "Q") {
				const c = [T(s.c[0]), T(s.c[1])];
				const m = mirror(lastQ);
				if (near(c, m)) {
					command("t");
					lastQ = m;
				} else {
					command("q");
					rel(c);
					lastQ = c;
				}
				lastC = null;
			} else {
				command("l");
				lastC = lastQ = null;
			}
			rel(p);
			[cx, cy] = p;
		}
		if (sub.closed) {
			command("z", true);
			[cx, cy] = [sx, sy];
		}
	}
	return out;
}

const fmt = (v) => String(Math.round(v * 10) / 10 || 0);

// ------------------------------------------------------------------ the ink noise

/**
 * feTurbulence exactly as the SVG specification's reference code computes it (and Chrome and
 * Firefox follow it): Park-Miller seeded gradients and lattice, smoothstep Perlin noise per
 * colour channel, summed over octaves. Returns turb(channel, x, y) -> raw sum.
 */
function makeTurbulence(seedValue, freqX, freqY, octaves, fractal) {
	const B = 256;
	const RAND_M = 2147483647;
	const random = (s) => {
		const r = 16807 * (s % 127773) - 2836 * Math.floor(s / 127773);
		return r <= 0 ? r + RAND_M : r;
	};
	let seed = Math.trunc(seedValue);
	if (seed <= 0) seed = -(seed % (RAND_M - 1)) + 1;
	if (seed > RAND_M - 1) seed = RAND_M - 1;
	const lattice = new Int32Array(B + B + 2);
	const grad = [0, 1, 2, 3].map(() => new Float64Array((B + B + 2) * 2));
	let i;
	for (let k = 0; k < 4; k++) {
		for (i = 0; i < B; i++) {
			lattice[i] = i;
			for (let j = 0; j < 2; j++) grad[k][i * 2 + j] = (((seed = random(seed)) % (B + B)) - B) / B;
			const len = Math.hypot(grad[k][i * 2], grad[k][i * 2 + 1]);
			grad[k][i * 2] /= len;
			grad[k][i * 2 + 1] /= len;
		}
	}
	while (--i) {
		const k = lattice[i];
		const j = (seed = random(seed)) % B;
		lattice[i] = lattice[j];
		lattice[j] = k;
	}
	for (i = 0; i < B + 2; i++) {
		lattice[B + i] = lattice[i];
		for (let k = 0; k < 4; k++) {
			grad[k][(B + i) * 2] = grad[k][i * 2];
			grad[k][(B + i) * 2 + 1] = grad[k][i * 2 + 1];
		}
	}
	const curve = (t) => t * t * (3 - 2 * t);
	function noise2(g, vx, vy) {
		const tx = vx + 4096;
		const ty = vy + 4096;
		const bx0 = Math.trunc(tx) & 255;
		const by0 = Math.trunc(ty) & 255;
		const bx1 = (bx0 + 1) & 255;
		const by1 = (by0 + 1) & 255;
		const rx0 = tx - Math.trunc(tx);
		const ry0 = ty - Math.trunc(ty);
		const rx1 = rx0 - 1;
		const ry1 = ry0 - 1;
		const li = lattice[bx0];
		const lj = lattice[bx1];
		const b00 = lattice[li + by0] * 2;
		const b10 = lattice[lj + by0] * 2;
		const b01 = lattice[li + by1] * 2;
		const b11 = lattice[lj + by1] * 2;
		const sx = curve(rx0);
		let u = rx0 * g[b00] + ry0 * g[b00 + 1];
		let v = rx1 * g[b10] + ry0 * g[b10 + 1];
		const a = u + sx * (v - u);
		u = rx0 * g[b01] + ry1 * g[b01 + 1];
		v = rx1 * g[b11] + ry1 * g[b11 + 1];
		const b = u + sx * (v - u);
		return a + curve(ry0) * (b - a);
	}
	return (channel, x, y) => {
		let sum = 0;
		let vx = x * freqX;
		let vy = y * freqY;
		for (let o = 0, ratio = 1; o < octaves; o++, ratio *= 2, vx *= 2, vy *= 2) {
			const n = noise2(grad[channel], vx, vy);
			sum += (fractal ? n : Math.abs(n)) / ratio;
		}
		return sum;
	};
}

/**
 * The displacement of one ink filter as a point mover: move(x, y) is where the filter shows the
 * art's point (x, y), i.e. the P with P + d(P) = (x, y), where d is feDisplacementMap's offset
 * scale * (channel value - 0.5) read from the turbulence at P.
 */
function makeMover(ink) {
	const turb = makeTurbulence(ink.seed, ink.freqX, ink.freqY, ink.octaves, ink.fractal);
	const value = (ch, x, y) => {
		const s = turb(ch, x, y);
		return Math.min(1, Math.max(0, ink.fractal ? (s + 1) / 2 : s)) - 0.5;
	};
	const cache = new Map();
	return (x, y) => {
		const key = `${x},${y}`;
		let p = cache.get(key);
		if (!p) {
			let px = x;
			let py = y;
			for (let k = 0; k < INVERSE_STEPS; k++) {
				const dx = ink.scale * value(ink.xch, px, py);
				const dy = ink.scale * value(ink.ych, px, py);
				[px, py] = [x - dx, y - dy];
			}
			p = [px, py];
			cache.set(key, p);
		}
		return p;
	};
}

// ------------------------------------------------------------------ filters

const CHANNEL = { R: 0, G: 1, B: 2, A: 3 };

/**
 * Reads a <filter> as a recipe for baking. Its primitives are evaluated symbolically, and the
 * result must be a stack of layers that are either the content or a white dilated silhouette
 * of it, each optionally displaced by turbulence:
 *   {layers: [{kind: "content" | "halo", r, ink}], region} or {other: "reason"}.
 * This covers the ink filter, the halo filter, and combinations such as a displaced white rim.
 */
function readFilter(filter) {
	const results = new Map();
	let last = { kind: "src" };
	const input = (name) => {
		if (!name) return last;
		if (name === "SourceGraphic") return { kind: "src" };
		if (name === "SourceAlpha") return { kind: "alpha", of: { kind: "src" } };
		return results.get(name) ?? { kind: "unknown", name };
	};
	for (const p of elements(filter)) {
		const a = ownStyle(p);
		let v;
		if (p.name === "feTurbulence") {
			const f = (a.baseFrequency ?? "0").split(/[\s,]+/).map(Number);
			if (a.stitchTiles === "stitch") v = { kind: "unknown", name: "stitched turbulence" };
			else {
				v = {
					kind: "noise",
					freqX: f[0] || 0,
					freqY: f.length > 1 ? f[1] : f[0] || 0,
					octaves: Math.max(0, Math.trunc(Number(a.numOctaves ?? 1))),
					seed: Number(a.seed ?? 0),
					fractal: a.type === "fractalNoise",
				};
			}
		} else if (p.name === "feDisplacementMap") {
			const noise = input(a.in2);
			const src = input(a.in);
			if (noise.kind !== "noise" || src.ink) v = { kind: "unknown", name: "displacement" };
			else {
				const ink = {
					...noise,
					scale: Number(a.scale ?? 0),
					xch: CHANNEL[a.xChannelSelector ?? "A"],
					ych: CHANNEL[a.yChannelSelector ?? "A"],
				};
				v = { ...src, ink };
			}
		} else if (p.name === "feMorphology") {
			const src = input(a.in);
			const r = (a.radius ?? "0").split(/[\s,]+/).map(Number);
			const base = src.kind === "alpha" ? src.of : src;
			if (a.operator !== "dilate" || base.kind !== "src")
				v = { kind: "unknown", name: "morphology" };
			else v = { kind: "dilate", r: Math.max(...r), ink: base.ink };
		} else if (p.name === "feFlood") {
			const color = (a["flood-color"] ?? "black").toLowerCase();
			const white = isWhite(color) && Number(a["flood-opacity"] ?? 1) === 1;
			v = white ? { kind: "white" } : { kind: "unknown", name: `flood ${color}` };
		} else if (p.name === "feComposite") {
			const [x, y] = [input(a.in), input(a.in2)];
			if ((a.operator ?? "over") === "in" && x.kind === "white" && y.kind === "dilate")
				v = { kind: "halo", r: y.r, ink: y.ink };
			else v = { kind: "unknown", name: "composite" };
		} else if (p.name === "feMerge") {
			v = { kind: "stack", layers: elements(p).map((n) => input(getAttr(n, "in"))) };
		} else v = { kind: "unknown", name: p.name };
		if (a.result) results.set(a.result, v);
		last = v;
	}
	const layers = last.kind === "stack" ? last.layers : [last];
	const out = [];
	for (const l of layers) {
		if (l.kind === "src") out.push({ kind: "content", ink: l.ink });
		else if (l.kind === "halo") out.push({ kind: "halo", r: l.r, ink: l.ink });
		else return { other: l.kind === "unknown" ? l.name : l.kind };
	}
	if (out.filter((l) => l.kind === "content").length > 1) return { other: "content drawn twice" };
	const units = ownStyle(filter).filterUnits;
	const region =
		units === "userSpaceOnUse"
			? ["x", "y", "width", "height"].map((k) => parseFloat(getAttr(filter, k)))
			: null;
	return { layers: out, region: region?.every(Number.isFinite) ? region : null };
}

const inkKey = (ink) =>
	[ink.freqX, ink.freqY, ink.octaves, ink.seed, ink.fractal, ink.scale, ink.xch, ink.ych].join();

// ------------------------------------------------------------------ the bake

/**
 * Bakes one SVG document (a string). Returns {svg, notes}: the new text, and a list of notes
 * (what was baked, and anything left alone that a person should look at).
 */
export function bakeSvg(src) {
	const notes = [];
	if (!/<filter[\s>]|\sfilter\s*=|filter\s*:/.test(src))
		return { svg: src, notes: ["no filters: unchanged"] };
	const doc = parseXml(src);
	const ids = new Map();
	(function index(node) {
		for (const el of elements(node)) {
			const id = getAttr(el, "id");
			if (id) ids.set(decode(id), el);
			index(el);
		}
	})(doc);

	// Read every filter once; keep one mover per distinct set of noise parameters.
	const recipes = new Map();
	const movers = new Map();
	const moverFor = (ink) => {
		const key = inkKey(ink);
		if (!movers.has(key)) movers.set(key, makeMover(ink));
		return movers.get(key);
	};
	for (const [id, el] of ids) {
		if (el.name !== "filter") continue;
		const recipe = readFilter(el);
		recipes.set(id, recipe);
		if (recipe.other)
			notes.push(`left filter #${id} alone: not an ink or halo filter (${recipe.other})`);
	}

	const stats = {
		shapes: 0,
		converted: 0,
		moved: 0,
		halos: 0,
		copies: 0,
		culled: 0,
		trimmed: 0,
		uses: 0,
		shared: 0,
		sharedUses: 0,
	};
	const halos = [];
	let defaultInk = null;
	let clipCount = 0;

	// 1. Replace every ink or halo filter reference by marks on the tree (node.ink = mover for
	// the subtree, null to stop an outer one) and by the halo copies.
	(function expand(node, inh) {
		for (const el of elements(node)) {
			if (el.name === "pattern") continue;
			// Halo copies carry the noise parameters of nested ink filters; make them movers.
			if (el.ink && typeof el.ink !== "function") el.ink = moverFor(el.ink);
			const state = inherit(inh, el);
			const ref = urlRef(ownStyle(el).filter);
			const recipe = ref && recipes.get(ref);
			if (ref && !recipe) notes.push(`<${el.name}> refers to a missing filter #${ref}`);
			if (recipe && !recipe.other) {
				delAttr(el, "filter");
				if (getAttr(el, "style"))
					setAttr(el, "style", stripStyle(getAttr(el, "style"), ["filter"]));
				const content = recipe.layers.find((l) => l.kind === "content");
				const halo = recipe.layers.find((l) => l.kind === "halo");
				for (const l of recipe.layers) if (l.ink && !defaultInk) defaultInk = l.ink;
				if (content?.ink) el.ink = moverFor(content.ink);
				if (halo) {
					const reach = halo.r * HALO_REACH;
					const copy = element("g", [], copyForHalo(el.kids, reach, state, 1, ids, recipes, notes));
					copy.ink = halo.ink ? moverFor(halo.ink) : content?.ink ? null : undefined;
					const order = recipe.layers.map((l) => (l.kind === "halo" ? [copy] : el.kids)).flat();
					// A halo-only filter draws no content, but the copy still refers to the clip
					// paths and masks defined inside it, at any depth, so those are kept. Moving them
					// up is safe: user-space clip and mask content is placed by whoever refers to it.
					let defs = [];
					if (!content) {
						defs = definitionsIn(el.kids);
						for (const d of defs) if (d.ink === undefined) d.ink = copy.ink;
					}
					el.kids = content ? order : [copy, ...defs];
					const entry = { el, copy, parent: el };
					halos.push(entry);
					stats.halos++;
					// A filter region in user units clips the result; keep that clip for the halo,
					// which may well rely on it (a rim kept to the band above the crowd, say).
					if (recipe.region) {
						const id = `bake-region-${++clipCount}`;
						const [x, y, w, h] = recipe.region;
						const rect = element("rect", [
							["x", fmt(x)],
							["y", fmt(y)],
							["width", fmt(w)],
							["height", fmt(h)],
						]);
						const clip = element("clipPath", [["id", id]], [rect]);
						ids.set(id, clip);
						entry.parent = element("g", [["clip-path", `url(#${id})`]], el.kids);
						el.kids = [clip, entry.parent];
						if (el.ink !== undefined) [entry.parent.ink, el.ink] = [el.ink, undefined];
						notes.push(`kept the filter region of #${ref} as a clip`);
					}
				}
			}
			expand(el, state);
		}
	})(doc, {});

	// 2. Find every shape to bake: under an ink mark, inside a clip path or mask (with the
	// file's ink), or reached through a <use> from either.
	const todo = new Map();
	const defaultMover = defaultInk ? moverFor(defaultInk) : null;
	const seenTargets = new Set();
	const visit = (node, mover, inClip) => {
		for (const el of elements(node)) {
			if (el.name === "pattern" || el.name === "style") continue;
			let m = el.ink !== undefined ? el.ink : mover;
			let clip = inClip;
			if ((el.name === "clipPath" || el.name === "mask") && defaultMover) {
				const units = ownStyle(el)[el.name === "mask" ? "maskContentUnits" : "clipPathUnits"];
				if (units === "objectBoundingBox") {
					notes.push(`left <${el.name}> ${getAttr(el, "id") ?? ""} alone: objectBoundingBox units`);
					continue;
				}
				m = m || defaultMover;
				clip = true;
			}
			if (SHAPES.has(el.name)) {
				// A rect drawn in a clip or mask but outside any ink is a region box, not art.
				if (m && !todo.has(el) && !(clip && el.name === "rect" && !inkAbove(el))) todo.set(el, m);
			} else if (el.name === "use") {
				const target = ids.get(hrefRef(el));
				if (m && target && !seenTargets.has(target)) {
					seenTargets.add(target);
					stats.uses++;
					if (SHAPES.has(target.name)) {
						if (!todo.has(target)) todo.set(target, m);
					} else visit({ kids: [target] }, m, clip);
				}
			} else visit(el, m, clip);
		}
	};
	// Marks can only come from expand(), so "under ink" means an ancestor carries .ink.
	const inkHolders = new Set();
	(function mark(node, on) {
		for (const el of elements(node)) {
			const here = el.ink !== undefined ? !!el.ink : on;
			if (here) inkHolders.add(el);
			mark(el, here);
		}
	})(doc, false);
	const inkAbove = (el) => inkHolders.has(el);
	visit(doc, undefined, false);

	for (const [el, mover] of todo) bakeShape(el, mover, stats, notes);

	// 3. Drop the halo copies nobody can see, write repeated outlines once, and drop the
	// filters nobody uses any more.
	for (const h of halos) cullHalo(doc, h, ids, stats);
	shareGeometry(doc, ids, stats);
	removeUnusedFilters(doc, notes);

	const kept = stats.copies - stats.culled;
	notes.unshift(
		`baked ${stats.shapes} shapes (${stats.converted} turned into paths, ` +
			`${stats.moved} tiny ones moved, ${stats.sharedUses} drawn as <use> ` +
			`of ${stats.shared} shared outlines)` +
			(stats.halos
				? `; ${stats.halos} halos: kept ${kept} of ${stats.copies} white copies ` +
					`(${stats.trimmed} trimmed to their rim)`
				: ""),
	);
	const trailing = /\n$/.test(src) ? "\n" : "";
	return { svg: serializeXml(doc).join("") + trailing, notes };
}

function stripStyle(style, props) {
	return decode(style)
		.split(";")
		.filter((d) => d.trim() && !props.includes(d.split(":")[0].trim()))
		.join(";");
}

/** True if moving a shape as a whole, by its centre's offset, keeps every one of its `rim`
 * points within TOLERANCE of where the noise puts it: such a shape keeps its element. */
function movesWhole(move, centre, rim) {
	const [cx, cy] = move(centre[0], centre[1]);
	const [dx, dy] = [cx - centre[0], cy - centre[1]];
	return rim.every(([x, y]) => dist(move(x, y), [x + dx, y + dy]) <= TOLERANCE);
}

// Geometry attributes of each shape, which a baked path replaces with d.
const GEOMETRY = {
	path: ["d"],
	circle: ["cx", "cy", "r"],
	ellipse: ["cx", "cy", "rx", "ry"],
	rect: ["x", "y", "width", "height", "rx", "ry"],
	line: ["x1", "y1", "x2", "y2"],
	polyline: ["points"],
	polygon: ["points"],
};

/** Bakes one shape in place: subdivide, displace, and write it back as a path (or move it). */
function bakeShape(el, move, stats, notes) {
	const n = (k, fallback = 0) => {
		const v = parseFloat(getAttr(el, k) ?? "");
		return Number.isFinite(v) ? v : fallback;
	};
	let subs;
	try {
		if (el.name === "path") subs = parsePath(decode(getAttr(el, "d") ?? ""));
		else if (el.name === "circle" || el.name === "ellipse") {
			const rx = el.name === "circle" ? n("r") : n("rx", n("ry"));
			const ry = el.name === "circle" ? n("r") : n("ry", n("rx"));
			if (rx <= 0 || ry <= 0) return;
			const rim = [...Array(16).keys()].map((k) => [
				n("cx") + rx * Math.cos((k * Math.PI) / 8),
				n("cy") + ry * Math.sin((k * Math.PI) / 8),
			]);
			if (2 * Math.max(rx, ry) <= TINY || movesWhole(move, [n("cx"), n("cy")], rim)) {
				const [x, y] = move(n("cx"), n("cy"));
				setAttr(el, "cx", fmt(x));
				setAttr(el, "cy", fmt(y));
				stats.shapes++;
				stats.moved++;
				return;
			}
			subs = ellipseSubs(n("cx"), n("cy"), rx, ry);
		} else if (el.name === "rect") {
			const [x, y, w, h] = [n("x"), n("y"), n("width"), n("height")];
			if (w <= 0 || h <= 0) return;
			const rim = [
				[x, y],
				[x + w / 2, y],
				[x + w, y],
				[x + w, y + h / 2],
				[x + w, y + h],
				[x + w / 2, y + h],
				[x, y + h],
				[x, y + h / 2],
			];
			if (Math.max(w, h) <= TINY || movesWhole(move, [x + w / 2, y + h / 2], rim)) {
				const [mx, my] = move(x + w / 2, y + h / 2);
				setAttr(el, "x", fmt(mx - w / 2));
				setAttr(el, "y", fmt(my - h / 2));
				stats.shapes++;
				stats.moved++;
				return;
			}
			const rx = getAttr(el, "rx") === undefined ? undefined : n("rx");
			const ry = getAttr(el, "ry") === undefined ? undefined : n("ry");
			subs = rectSubs(x, y, w, h, rx, ry);
		} else if (el.name === "line") {
			subs = [{ x: n("x1"), y: n("y1"), segs: [{ t: "L", p: [n("x2"), n("y2")] }], closed: false }];
		} else {
			const v = (
				decode(getAttr(el, "points") ?? "").match(/[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/gi) || []
			).map(Number);
			if (v.length < 4) return;
			const segs = [];
			for (let k = 2; k + 1 < v.length; k += 2) segs.push({ t: "L", p: [v[k], v[k + 1]] });
			subs = [{ x: v[0], y: v[1], segs, closed: el.name === "polygon" }];
		}
	} catch (e) {
		notes.push(`left a <${el.name}> unbaked: ${e.message}`);
		return;
	}
	const d = formatPath(subs.map((s) => bakeSubpath(s, move)));
	const geometry = GEOMETRY[el.name];
	const at = el.attrs.findIndex((a) => geometry.includes(a[0]));
	const attrs = el.attrs.filter((a) => !geometry.includes(a[0]));
	attrs.splice(at < 0 ? 0 : at, 0, ["d", d]);
	if (el.name !== "path") stats.converted++;
	el.name = "path";
	el.attrs = attrs;
	el.baked = true;
	stats.shapes++;
}

// ------------------------------------------------------------------ halo copies

/**
 * The white copy under a halo: the same shapes with every fill that isn't none made white and
 * every stroke white and widened by 2r, r being how far the dilation reached (in the halo's user
 * units, so divided by the scale of any transform in between); unstroked shapes get a white
 * stroke of 2r. <use> is inlined when its target sets its own paint, and kept as a reference
 * otherwise (it then inherits the white paint). Clip paths, masks, classes and transforms are
 * kept, so the copy sits and moves exactly like the content; ids are dropped, and nested ink
 * marks carry over.
 */
function copyForHalo(kids, r, inh, scale, ids, recipes, notes, depth = 0) {
	const out = [];
	for (const el of kids) {
		if (el.type !== "el" || NOT_DRAWN.has(el.name)) continue;
		const own = ownStyle(el);
		if (own.display === "none" || own.visibility === "hidden" || Number(own.opacity ?? 1) === 0)
			continue;
		const state = inherit(inh, el);
		const s = scale * scaleOf(parseTransform(own.transform));
		let ink;
		let radius = r;
		const ref = urlRef(own.filter);
		const recipe = ref && recipes.get(ref);
		if (recipe && !recipe.other) {
			for (const l of recipe.layers) {
				if (l.kind === "halo") radius += l.r * s; // a nested halo widens this one
				if (l.ink) ink = l.ink;
			}
		}
		// Fresh [name, value] pairs: baking moves a shape by rewriting its pairs in place, and the
		// copy must never move its source.
		const strip = ["id", "filter", "fill", "stroke", "stroke-width", "style"];
		const attrs = el.attrs.filter((a) => !strip.includes(a[0])).map(([k, v]) => [k, v]);
		if (getAttr(el, "style")) {
			const style = stripStyle(getAttr(el, "style"), ["filter", "fill", "stroke", "stroke-width"]);
			if (style) attrs.push(["style", style]);
		}
		let copy = null;
		if (GROUPS.has(el.name) || el.name === "svg") {
			// A nested <svg> keeps its viewport, so its copy is placed and clipped like it.
			const inner = copyForHalo(
				el.kids,
				radius,
				state,
				s * scaleOf(viewportOf(el)),
				ids,
				recipes,
				notes,
				depth,
			);
			if (inner.length) copy = element(el.name, attrs, inner);
		} else if (el.name === "use") {
			const target = ids.get(hrefRef(el));
			if (!target || depth > 8) continue;
			// A target that sets no paint of its own (and no transform, which would scale the
			// widened stroke) can stay shared: the white paint on the use reaches it.
			if (!setsPaint(target) && !ownStyle(target).transform) {
				copy = element("use", attrs);
				whitePaint(copy, state, (2 * radius) / s);
			} else {
				// Inline: the use's transform and x/y, then a copy of the target.
				const [x, y] = [
					parseFloat(getAttr(el, "x") ?? "0") || 0,
					parseFloat(getAttr(el, "y") ?? "0") || 0,
				];
				const t = [getAttr(el, "transform"), x || y ? `translate(${fmt(x)} ${fmt(y)})` : ""]
					.filter(Boolean)
					.join(" ");
				const keep = attrs.filter(
					(a) => !["href", "xlink:href", "x", "y", "width", "height", "transform"].includes(a[0]),
				);
				const inner = copyForHalo([target], radius, state, s, ids, recipes, notes, depth + 1);
				if (inner.length) copy = element("g", t ? [["transform", t], ...keep] : keep, inner);
			}
		} else if (SHAPES.has(el.name)) {
			if (isNone(state.fill) && isNone(state.stroke)) continue;
			copy = element(el.name, attrs);
			whitePaint(copy, state, (2 * radius) / s);
		} else if (el.name === "symbol") {
			notes.push("halo copy: a <symbol> under a halo is not supported; skipped");
		}
		if (!copy) continue;
		if (ink) copy.ink = ink; // turned into a mover by the caller's expand pass
		copy.source = el;
		out.push(copy);
	}
	return out;
}

/** True if any element of the tree sets fill, stroke or stroke width itself. */
function setsPaint(el) {
	if (el.type !== "el") return false;
	const own = ownStyle(el);
	if (own.fill !== undefined || own.stroke !== undefined || own["stroke-width"] !== undefined)
		return true;
	return el.kids.some(setsPaint);
}

/** White paint for a halo copy whose content has the paint state `state` (its round joins and
 * ends come from the copy's group, see tidyCopy). */
function whitePaint(copy, state, extra) {
	const stroked = !isNone(state.stroke);
	const width = (stroked ? parseFloat(state["stroke-width"] ?? "1") || 0 : 0) + extra;
	delAttr(copy, "stroke-linejoin", "stroke-linecap");
	copy.attrs.push(
		["fill", isNone(state.fill) ? "none" : "#fff"],
		["stroke", "#fff"],
		["stroke-width", fmt(width)],
	);
}

// ------------------------------------------------------------------ halo culling

/**
 * Drops the parts of a halo copy that cannot show. The copy is painted under the content, so a
 * copied shape is invisible where opaque content covers its whole white footprint, where the
 * paper under it is already white, or where a bigger copy kept before it paints white anyway.
 * The covers are rasterized in root space on a grid of CELL units (a cell counts only if its
 * centre is inside an opaque fill, and the cover is then shrunk by a cell), and a copied shape
 * is dropped only if every point of its footprint lies at least its white half-width plus
 * CULL_MARGIN cells inside them; a long outline that shows only in places is trimmed to those
 * stretches. Moving parts (anything with a class, in a file with a <style>) never count as cover
 * and are never dropped.
 */
function cullHalo(doc, halo, ids, stats) {
	const animated = !!findFirst(doc, (el) => el.name === "style");
	// Every drawn shape in paint order, with its matrix, paint and situation. A shape drawn
	// through a <use> belongs to that use: the use is what a copy keeps or drops.
	const items = [];
	const walk = (node, ctm, inh, f) => {
		for (const el of elements(node)) {
			if (NOT_DRAWN.has(el.name)) continue;
			const own = ownStyle(el);
			if (own.display === "none") continue;
			// A nested <svg> maps its viewBox onto its viewport and clips to it.
			const nested = el.name === "svg" && node !== doc;
			const m = mul(mul(ctm, parseTransform(own.transform)), nested ? viewportOf(el) : IDENTITY);
			const state = inherit(inh, el);
			const clipEl = ids.get(urlRef(own["clip-path"]));
			const g = {
				clipped: f.clipped || !!own["clip-path"] || !!own.mask || nested,
				// The innermost clip path, with the matrix of its user space, bounds what a
				// shape can paint (the outer ones only cut that down further).
				clip: clipEl?.name === "clipPath" ? { el: clipEl, m } : f.clip,
				masked: f.masked || !!own.mask,
				faded: f.faded || Number(own.opacity ?? 1) < 1,
				moving: f.moving || (animated && !!own.class),
				inHalo: f.inHalo || el === halo.el,
				inCopy: f.inCopy || el === halo.copy,
				unit: f.unit,
			};
			if (SHAPES.has(el.name)) items.push({ el, m, state, f: g, unit: g.unit ?? el });
			else if (el.name === "use") {
				const target = ids.get(hrefRef(el));
				if (!target) continue;
				const x = parseFloat(getAttr(el, "x") ?? "0") || 0;
				const y = parseFloat(getAttr(el, "y") ?? "0") || 0;
				walk({ kids: [target] }, mul(m, [1, 0, 0, 1, x, y]), state, { ...g, unit: g.unit ?? el });
			} else walk(el, m, state, g);
		}
	};
	walk(
		doc,
		IDENTITY,
		{},
		{
			clipped: false,
			clip: null,
			masked: false,
			faded: false,
			moving: false,
			inHalo: false,
			inCopy: false,
		},
	);
	const copies = items.filter((it) => it.f.inCopy);
	const units = new Set(copies.map((it) => it.unit));
	stats.copies += units.size;
	if (!copies.length) return;

	const geometry = new Map();
	const geo = (it) => {
		if (!geometry.has(it.el)) geometry.set(it.el, flatten(it.el));
		return geometry.get(it.el);
	};
	const reach = (it) => halfWidth(it) * stretchOf(it.m);
	// The grid spans the copy's footprint, with a margin of uncovered cells all round.
	let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
	for (const it of copies) {
		const pad = reach(it) + 2;
		for (const poly of geo(it).polys) {
			for (const [px, py] of poly) {
				const [x, y] = apply(it.m, px, py);
				x0 = Math.min(x0, x - pad);
				y0 = Math.min(y0, y - pad);
				x1 = Math.max(x1, x + pad);
				y1 = Math.max(y1, y + pad);
			}
		}
	}
	if (!Number.isFinite(x0)) return;
	const grid = makeGrid(x0 - 4 * CELL, y0 - 4 * CELL, x1 + 4 * CELL, y1 + 4 * CELL);
	const cover = new Uint8Array(grid.nx * grid.ny);
	const opaque = (it, paint) => {
		if (isNone(paint) || it.f.clipped || it.f.faded || it.f.moving) return false;
		if (Number(it.state["fill-opacity"] ?? 1) < 1 || it.state.visibility === "hidden") return false;
		const ref = urlRef(paint);
		if (ref) return isOpaquePattern(ids.get(ref));
		return !/^(rgba|hsla|transparent)/i.test(paint);
	};
	const white = isWhite;
	// Paper under the halo: what was painted before it, in order (white sets, anything else
	// clears); then everything opaque in the halo's own content covers.
	let inside = false;
	const content = [];
	for (const it of items) {
		if (it.f.inHalo) {
			inside = true;
			if (!it.f.inCopy) content.push(it);
			continue;
		}
		if (inside) break; // painted after the halo, so on top of it: not paper
		const fill = it.state.fill ?? "black";
		if (white(fill) && opaque(it, fill))
			fillCells(grid, geo(it), it.m, ruleOf(it), (k) => (cover[k] = 1));
		else if (!isNone(fill)) {
			fillCells(grid, geo(it), it.m, "nonzero", (k) => (cover[k] = 0));
			bandCells(grid, geo(it), it.m, CELL, (k) => (cover[k] = 0));
		}
		if (!isNone(it.state.stroke))
			bandCells(grid, geo(it), it.m, reach(it) + CELL, (k) => (cover[k] = 0));
	}
	for (const it of content) {
		if (opaque(it, it.state.fill ?? "black"))
			fillCells(grid, geo(it), it.m, ruleOf(it), (k) => (cover[k] = 1));
	}
	const solid = erode(cover, grid);
	const view = {
		grid,
		solid,
		depth: distanceInside(solid, grid),
		white: new Uint8Array(grid.nx * grid.ny),
	};
	// A clipped copy can only paint inside its clip path: the cells outside that (grown by two
	// cells, to stay on the safe side) need no cover.
	const regions = new Map();
	view.regionOf = (it) => {
		const clip = !it.f.masked && it.f.clip;
		if (!clip) return null;
		const key = clip.m.join();
		let byM = regions.get(clip.el);
		if (!byM) regions.set(clip.el, (byM = new Map()));
		if (!byM.has(key)) {
			const region = new Uint8Array(grid.nx * grid.ny);
			const shapes = [];
			const collect = (node, m) => {
				for (const el of elements(node)) {
					const t = mul(m, parseTransform(ownStyle(el).transform));
					if (SHAPES.has(el.name)) shapes.push([el, t]);
					else if (el.name === "use" && ids.get(hrefRef(el))) {
						const x = parseFloat(getAttr(el, "x") ?? "0") || 0;
						const y = parseFloat(getAttr(el, "y") ?? "0") || 0;
						collect({ kids: [ids.get(hrefRef(el))] }, mul(t, [1, 0, 0, 1, x, y]));
					} else if (GROUPS.has(el.name)) collect(el, t);
				}
			};
			collect(clip.el, clip.m);
			for (const [el, t] of shapes) {
				const geo = flatten(el);
				fillCells(grid, geo, t, "nonzero", (k) => (region[k] = 1));
				bandCells(grid, geo, t, 2 * CELL, (k) => (region[k] = 1));
			}
			byM.set(key, region);
		}
		return byM.get(key);
	};
	// A copy whose source is drawn opaque needs no fill: the source paints over exactly that.
	const byContentUnit = new Map();
	for (const it of content) byContentUnit.set(it.unit, [...(byContentUnit.get(it.unit) ?? []), it]);
	view.coveredFill = (it) => {
		const unit = it.unit.source;
		const el = it.unit === it.el ? unit : it.el;
		const src = byContentUnit.get(unit)?.find((c) => c.el === el);
		return !!src && opaque(src, src.state.fill ?? "black");
	};

	// Decide per copy unit, biggest first. A unit is dropped if its white footprint is covered
	// by the content, the paper or the copies kept so far; else it is kept, or (a lone path)
	// trimmed to the stretches of outline whose white band can still show. An opaque shape
	// covers its own copy's fill, so a trimmed copy keeps only its wide white stroke, as open
	// runs with round ends. What a kept copy paints joins the cover for the next ones.
	const byUnit = new Map();
	for (const it of copies) byUnit.set(it.unit, [...(byUnit.get(it.unit) ?? []), it]);
	const order = [...byUnit].map(([unit, list]) => ({ unit, list, size: sizeOf(list) }));
	order.sort((p, q) => q.size - p.size); // a stable sort: ties stay in document order
	const keep = new Set();
	const trims = new Map();
	for (const { unit, list } of order) {
		const it = list[0];
		const dashed = list.some((x) => !isNone(x.state["stroke-dasharray"]));
		const own = list.length === 1 && unit === it.el && it.el.name === "path" && !dashed;
		const moving = list.some((x) => x.f.moving);
		const plan = moving ? { keep: true, lines: null } : footprint(view, list, own);
		if (!plan.keep) continue;
		keep.add(unit);
		if (plan.d) trims.set(unit, plan.d);
		if (!moving && !dashed && list.every((x) => !x.f.clipped && !x.f.faded))
			paintWhite(view, list, plan);
	}
	let dropped = 0;
	(function prune(node) {
		node.kids = node.kids.filter((k) => {
			if (k.type !== "el") return true;
			if (units.has(k) && !keep.has(k)) {
				dropped++;
				return false;
			}
			prune(k);
			return !(GROUPS.has(k.name) && !k.kids.length);
		});
	})(halo.copy);
	for (const [el, d] of trims) {
		setAttr(el, "d", d);
		setAttr(el, "fill", "none");
		setAttr(el, "stroke-linecap", "round");
		setAttr(el, "stroke-linejoin", "round");
	}
	stats.culled += dropped;
	stats.trimmed += trims.size;
	if (!halo.copy.kids.length) halo.parent.kids = halo.parent.kids.filter((k) => k !== halo.copy);
	else tidyCopy(halo.copy);
}

/**
 * Writes a copy's paint once instead of on every shape. The whole copy is white with round
 * joins and ends (a dilation rounds every corner), so the copy's group carries fill, stroke,
 * joins and caps, and each shape keeps only what differs: fill="none" for a copied stroke, and
 * its stroke width, which moves up to a group wherever all of that group's children share it.
 */
function tidyCopy(copy) {
	const PAINT = {
		fill: "#fff",
		stroke: "#fff",
		"stroke-linejoin": "round",
		"stroke-linecap": "round",
	};
	const JOINS = ["stroke", "stroke-linejoin", "stroke-linecap", "stroke-miterlimit"];
	(function strip(node) {
		for (const el of elements(node)) {
			el.attrs = el.attrs.filter(([k, v]) => PAINT[k] !== v && !JOINS.includes(k));
			strip(el);
		}
	})(copy);
	(function hoist(node) {
		const kids = elements(node);
		kids.forEach(hoist);
		const widths = new Set(kids.map((k) => getAttr(k, "stroke-width")));
		if (
			kids.length &&
			widths.size === 1 &&
			!widths.has(undefined) &&
			getAttr(node, "stroke-width") === undefined
		) {
			for (const k of kids) delAttr(k, "stroke-width");
			setAttr(node, "stroke-width", [...widths][0]);
		}
	})(copy);
	copy.attrs = [...Object.entries(PAINT), ...copy.attrs];
}

/** Rough size of a copy unit's footprint: the area of its bounding box in root units. */
function sizeOf(list) {
	let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
	for (const it of list) {
		const pad = halfWidth(it) * stretchOf(it.m);
		for (const poly of flatten(it.el).polys) {
			for (const [px, py] of poly) {
				const [x, y] = apply(it.m, px, py);
				[x0, y0, x1, y1] = [
					Math.min(x0, x - pad),
					Math.min(y0, y - pad),
					Math.max(x1, x + pad),
					Math.max(y1, y + pad),
				];
			}
		}
	}
	return Number.isFinite(x0) ? (x1 - x0) * (y1 - y0) : 0;
}

/** Calls fn(cell) for the cells within `r` cells of points along a root-space polyline; stops
 * and returns false as soon as fn returns false. */
function aroundLine(grid, pts, r, fn) {
	let ok = true;
	forSamples(pts, CELL / 2, (x, y) => {
		if (!ok) return;
		const ci = (x - grid.x0) / CELL - 0.5;
		const cj = (y - grid.y0) / CELL - 0.5;
		for (let j = Math.floor(cj - r); j <= Math.ceil(cj + r) && ok; j++) {
			for (let i = Math.floor(ci - r); i <= Math.ceil(ci + r) && ok; i++) {
				if ((i - ci) ** 2 + (j - cj) ** 2 > r * r) continue;
				const k = i < 0 || j < 0 || i >= grid.nx || j >= grid.ny ? -1 : j * grid.nx + i;
				if (fn(k) === false) ok = false;
			}
		}
	});
	return ok;
}

/** A copy item's outline pieces in root space: one polyline per segment (or per subpath). */
function piecesOf(it) {
	return parsePath(ownStyle(it.el).d ?? "").map((sub) => {
		const start = [sub.x, sub.y];
		const segs = [...sub.segs];
		if (sub.closed && segs.length && dist(segs[segs.length - 1].p, start) > 1e-9)
			segs.push({ t: "L", p: start });
		let p0 = start;
		const lines = segs.map((seg) => {
			const ctrl = controls(p0, seg);
			p0 = seg.p;
			let length = 0;
			for (let k = 1; k < ctrl.length; k++) length += dist(ctrl[k - 1], ctrl[k]);
			const steps = ctrl.length === 2 ? 1 : Math.max(2, Math.ceil(length / 0.5));
			const pts = [];
			for (let k = 0; k <= steps; k++) pts.push(apply(it.m, ...bezierAt(ctrl, k / steps)));
			return pts;
		});
		return { sub, segs, lines: segs.length ? lines : [[apply(it.m, sub.x, sub.y)]] };
	});
}

/**
 * What a copy unit's white footprint needs: {keep: false} if it is covered all over (each
 * fill's inside, and a band of the white half-width plus CULL_MARGIN cells around each
 * outline), {keep: true} to keep it whole, or, for a lone path that may be trimmed (`own`),
 * {keep: true, d} with only the segments whose band is not covered (when the fill's inside
 * is). `lines` lists the root-space outline that stays, for paintWhite.
 */
function footprint(view, list, own) {
	const { grid, solid, depth, white } = view;
	let whole = false;
	const lines = [];
	let trimmedRuns = null;
	for (const it of list) {
		const region = view.regionOf(it);
		const ok = (k) =>
			k >= 0 && (solid[k] === 1 || white[k] === 1 || (region !== null && region[k] === 0));
		const geo = flatten(it.el);
		const filled = !isNone(it.state.fill);
		let inside = true;
		if (filled && !view.coveredFill(it)) {
			fillCells(grid, geo, it.m, "nonzero", (k) => {
				if (!ok(k)) inside = false;
			});
		}
		const r = (halfWidth(it) * stretchOf(it.m)) / CELL + CULL_MARGIN;
		const covered = (pts) => {
			let fine = true;
			forSamples(pts, CELL / 2, (x, y) => {
				if (!fine) return;
				const i = Math.floor((x - grid.x0) / CELL);
				const j = Math.floor((y - grid.y0) / CELL);
				if (i < 0 || j < 0 || i >= grid.nx || j >= grid.ny) fine = false;
				else if (depth[j * grid.nx + i] < r + 1) fine = aroundLine(grid, [[x, y]], r, ok);
			});
			return fine;
		};
		if (!own) {
			const polys = geo.polys.map((poly, p) => {
				const pts = poly.map(([x, y]) => apply(it.m, x, y));
				if ((filled || geo.closed[p]) && pts.length > 1) pts.push(pts[0]);
				return pts;
			});
			lines.push(...polys);
			if (!inside || !polys.every(covered)) whole = true;
			continue;
		}
		// A lone path: test it segment by segment, a close being an explicit last line.
		const runs = piecesOf(it).map((piece) => ({
			...piece,
			need: piece.lines.map((pts) => !covered(pts)),
		}));
		const any = runs.some((p) => p.need.some(Boolean));
		const all = runs.every((p) => p.need.every(Boolean));
		if (!any && inside) return { keep: false };
		if (!any || all || !inside) {
			for (const p of runs) lines.push(...p.lines);
			return { keep: true, lines, filled };
		}
		for (const p of runs) p.lines.forEach((pts, k) => p.need[k] && lines.push(pts));
		trimmedRuns = runs;
	}
	if (trimmedRuns) return { keep: true, d: trimmed(trimmedRuns), lines };
	return whole ? { keep: true, lines, filled: true } : { keep: false };
}

/** Adds what a kept copy paints white to the cover (shrunk by a cell to stay on the safe side). */
function paintWhite(view, list, plan) {
	const { grid, white } = view;
	for (const it of list) {
		const r = (halfWidth(it) * stretchOf(it.m)) / CELL - 1;
		const mark = (k) => {
			if (k >= 0) white[k] = 1;
		};
		if (r > 0) for (const pts of plan.lines ?? []) aroundLine(grid, pts, r, mark);
		if (plan.filled && !plan.d && !isNone(it.state.fill))
			fillCells(grid, flatten(it.el), it.m, "nonzero", (k) => (white[k] = 1));
	}
}

/** Path data for just the needed segments of each subpath, as open runs. */
function trimmed(runs) {
	const out = [];
	for (const { sub, segs, need } of runs) {
		if (!segs.length) {
			if (need[0]) out.push({ x: sub.x, y: sub.y, segs: [], closed: false });
			continue;
		}
		if (need.every(Boolean)) {
			out.push({ ...sub, segs });
			continue;
		}
		const ends = [[sub.x, sub.y], ...segs.map((s) => s.p)];
		const n = segs.length;
		// On a closed outline, start right after a gap, so a run can wrap past the start.
		let first = 0;
		if (sub.closed) while (need[(first + n - 1) % n]) first++;
		let run = null;
		for (let k = 0; k < n; k++) {
			const i = (first + k) % n;
			if (!need[i]) run = null;
			else {
				if (!run) {
					run = { x: ends[i][0], y: ends[i][1], segs: [], closed: false };
					out.push(run);
				}
				run.segs.push(segs[i]);
			}
		}
	}
	return formatPath(out);
}

function findFirst(node, test) {
	for (const el of elements(node)) {
		if (test(el)) return el;
		const hit = findFirst(el, test);
		if (hit) return hit;
	}
	return null;
}

const halfWidth = (it) =>
	isNone(it.state.stroke) ? 0 : (parseFloat(it.state["stroke-width"] ?? "1") || 0) / 2;
const ruleOf = (it) => (/evenodd/.test(it.state["fill-rule"] ?? "") ? "evenodd" : "nonzero");

/** A pattern counts as opaque if its first tile shape is an opaque rect covering the tile. */
function isOpaquePattern(p) {
	if (!p || p.name !== "pattern") return false;
	const first = elements(p)[0];
	if (!first || first.name !== "rect") return false;
	const a = ownStyle(first);
	const w = parseFloat(getAttr(p, "width"));
	const h = parseFloat(getAttr(p, "height"));
	const opaquePaint = !isNone(a.fill) && !urlRef(a.fill) && Number(a["fill-opacity"] ?? 1) === 1;
	const covers =
		(parseFloat(a.x ?? "0") || 0) <= 0 &&
		(parseFloat(a.y ?? "0") || 0) <= 0 &&
		parseFloat(a.width) >= w &&
		parseFloat(a.height) >= h;
	return opaquePaint && Number(a.opacity ?? 1) === 1 && covers;
}

/** A shape as polylines in its own coordinates (curves finely flattened), and which close. */
function flatten(el) {
	const a = ownStyle(el);
	const n = (k) => parseFloat(a[k] ?? "0") || 0;
	const opt = (k) => (a[k] === undefined ? undefined : n(k));
	let subs = [];
	try {
		if (el.name === "path") subs = parsePath(a.d ?? "");
		else if (el.name === "circle") subs = ellipseSubs(n("cx"), n("cy"), n("r"), n("r"));
		else if (el.name === "ellipse") subs = ellipseSubs(n("cx"), n("cy"), n("rx"), n("ry"));
		else if (el.name === "rect")
			subs = rectSubs(n("x"), n("y"), n("width"), n("height"), opt("rx"), opt("ry"));
		else if (el.name === "line")
			subs = [{ x: n("x1"), y: n("y1"), segs: [{ t: "L", p: [n("x2"), n("y2")] }] }];
		else {
			const v = (a.points?.match(/[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/gi) || []).map(Number);
			const segs = [];
			for (let k = 2; k + 1 < v.length; k += 2) segs.push({ t: "L", p: [v[k], v[k + 1]] });
			if (v.length >= 2) subs = [{ x: v[0], y: v[1], segs, closed: el.name === "polygon" }];
		}
	} catch {
		subs = [];
	}
	const polys = [];
	const closed = [];
	for (const sub of subs) {
		const poly = [[sub.x, sub.y]];
		let p0 = [sub.x, sub.y];
		for (const s of sub.segs) {
			if (s.t === "L") poly.push(s.p);
			else {
				const ctrl = s.t === "Q" ? [p0, s.c, s.p] : [p0, s.c1, s.c2, s.p];
				let len = 0;
				for (let k = 1; k < ctrl.length; k++) len += dist(ctrl[k - 1], ctrl[k]);
				const steps = Math.max(2, Math.ceil(len / 0.5));
				for (let k = 1; k <= steps; k++) poly.push(bezierAt(ctrl, k / steps));
			}
			p0 = s.p;
		}
		polys.push(poly);
		closed.push(!!sub.closed);
	}
	return { polys, closed };
}

function makeGrid(x0, y0, x1, y1) {
	return {
		x0,
		y0,
		nx: Math.max(1, Math.ceil((x1 - x0) / CELL)),
		ny: Math.max(1, Math.ceil((y1 - y0) / CELL)),
	};
}

/** Calls fn(cell index) for every cell whose centre is inside the shape's fill (scanlines). */
function fillCells(grid, geo, m, rule, fn) {
	const edges = [];
	for (const poly of geo.polys) {
		const pts = poly.map(([x, y]) => apply(m, x, y));
		for (let k = 0; k < pts.length; k++) {
			const a = pts[k];
			const b = pts[(k + 1) % pts.length]; // a fill closes every subpath
			if (a[1] !== b[1]) edges.push(a[1] < b[1] ? [a, b, 1] : [b, a, -1]);
		}
	}
	if (!edges.length) return;
	let lo = Infinity;
	let hi = -Infinity;
	for (const [a, b] of edges) {
		lo = Math.min(lo, a[1]);
		hi = Math.max(hi, b[1]);
	}
	const j0 = Math.max(0, Math.floor((lo - grid.y0) / CELL - 0.5));
	const j1 = Math.min(grid.ny - 1, Math.ceil((hi - grid.y0) / CELL - 0.5));
	for (let j = j0; j <= j1; j++) {
		const yc = grid.y0 + (j + 0.5) * CELL;
		const xs = [];
		for (const [a, b, w] of edges) {
			if (yc >= a[1] && yc < b[1])
				xs.push([a[0] + ((yc - a[1]) * (b[0] - a[0])) / (b[1] - a[1]), w]);
		}
		xs.sort((p, q) => p[0] - q[0]);
		let wind = 0;
		for (let k = 0; k + 1 < xs.length; k++) {
			wind += xs[k][1];
			if (rule === "evenodd" ? k % 2 === 1 : wind === 0) continue;
			const i0 = Math.max(0, Math.ceil((xs[k][0] - grid.x0) / CELL - 0.5));
			const i1 = Math.min(grid.nx - 1, Math.floor((xs[k + 1][0] - grid.x0) / CELL - 0.5));
			for (let i = i0; i <= i1; i++) fn(j * grid.nx + i);
		}
	}
}

/** Calls fn(cell index) for every cell within `radius` root units of the shape's outline. */
function bandCells(grid, geo, m, radius, fn) {
	const r = radius / CELL + 1;
	for (let p = 0; p < geo.polys.length; p++) {
		const pts = geo.polys[p].map(([x, y]) => apply(m, x, y));
		if (geo.closed[p] && pts.length > 1) pts.push(pts[0]);
		forSamples(pts, CELL / 2, (x, y) => {
			const ci = (x - grid.x0) / CELL - 0.5;
			const cj = (y - grid.y0) / CELL - 0.5;
			for (
				let j = Math.max(0, Math.floor(cj - r));
				j <= Math.min(grid.ny - 1, Math.ceil(cj + r));
				j++
			) {
				for (
					let i = Math.max(0, Math.floor(ci - r));
					i <= Math.min(grid.nx - 1, Math.ceil(ci + r));
					i++
				) {
					if ((i - ci) ** 2 + (j - cj) ** 2 <= r * r) fn(j * grid.nx + i);
				}
			}
		});
	}
}

/** Calls fn for points along a polyline no more than `step` apart, vertices included. */
function forSamples(pts, step, fn) {
	if (pts.length === 1) fn(pts[0][0], pts[0][1]);
	for (let k = 1; k < pts.length; k++) {
		const [a, b] = [pts[k - 1], pts[k]];
		const n = Math.max(1, Math.ceil(dist(a, b) / step));
		for (let s = k === 1 ? 0 : 1; s <= n; s++)
			fn(a[0] + ((b[0] - a[0]) * s) / n, a[1] + ((b[1] - a[1]) * s) / n);
	}
}

/** Keeps only cells whose 8 neighbours are covered too: a centre test can overreach a cell. */
function erode(cover, grid) {
	const { nx, ny } = grid;
	const out = new Uint8Array(nx * ny);
	for (let j = 1; j < ny - 1; j++) {
		for (let i = 1; i < nx - 1; i++) {
			let all = 1;
			for (let dj = -1; dj <= 1 && all; dj++)
				for (let di = -1; di <= 1; di++) all &= cover[(j + dj) * nx + i + di];
			out[j * nx + i] = all;
		}
	}
	return out;
}

/** Euclidean distance, in cells, from each cell to the nearest uncovered one (Felzenszwalb). */
function distanceInside(cover, grid) {
	const { nx, ny } = grid;
	const FAR = 1e12; // beyond any real squared distance, and still exact in doubles
	const d = new Float64Array(nx * ny);
	for (let k = 0; k < d.length; k++) d[k] = cover[k] ? FAR : 0;
	const n = Math.max(nx, ny);
	const f = new Float64Array(n);
	const v = new Int32Array(n);
	const z = new Float64Array(n + 1);
	// The lower envelope of the parabolas (q - p)^2 + f(p), along one row or column.
	const pass = (len, at) => {
		for (let q = 0; q < len; q++) f[q] = d[at(q)];
		let k = 0;
		v[0] = 0;
		z[0] = -Infinity;
		z[1] = Infinity;
		for (let q = 1; q < len; q++) {
			let s = (f[q] + q * q - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
			while (s <= z[k]) {
				k--;
				s = (f[q] + q * q - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
			}
			k++;
			v[k] = q;
			z[k] = s;
			z[k + 1] = Infinity;
		}
		k = 0;
		for (let q = 0; q < len; q++) {
			while (z[k + 1] < q) k++;
			d[at(q)] = (q - v[k]) ** 2 + f[v[k]];
		}
	};
	for (let i = 0; i < nx; i++) pass(ny, (j) => j * nx + i);
	for (let j = 0; j < ny; j++) pass(nx, (i) => j * nx + i);
	for (let k = 0; k < d.length; k++) d[k] = Math.sqrt(d[k]);
	return d;
}

// ------------------------------------------------------------------ clean-up

/**
 * Writes each baked outline that occurs more than once just once, as a bare <path> in a <defs>
 * at the top, and draws every occurrence as a <use> of it that keeps all its own attributes
 * (paint, clip, class, transform). The generators often draw one outline three times, as a
 * clip path, a white fill and an ink stroke, and baking keeps those identical. Paths with an
 * id, a style or a pathLength, and outlines too short to gain from it, stay as they are.
 */
function shareGeometry(doc, ids, stats) {
	const byPath = new Map();
	(function scan(node) {
		for (const el of elements(node)) {
			if (el.name === "pattern") continue;
			const plain = !el.attrs.some(([k]) => k === "id" || k === "style" || k === "pathLength");
			const d = el.baked && el.name === "path" && plain && getAttr(el, "d");
			if (d && d.length > 40) byPath.set(d, [...(byPath.get(d) ?? []), el]);
			scan(el);
		}
	})(doc);
	const shared = [];
	let n = 0;
	for (const [d, list] of byPath) {
		if (list.length < 2) continue;
		let id;
		do id = `bk${++n}`;
		while (ids.has(id));
		const path = element("path", [
			["id", id],
			["d", d],
		]);
		ids.set(id, path);
		shared.push(path);
		for (const el of list) {
			el.name = "use";
			el.attrs = el.attrs.map(([k, v]) => (k === "d" ? ["href", `#${id}`] : [k, v]));
		}
		stats.sharedUses += list.length;
	}
	stats.shared = shared.length;
	if (!shared.length) return;
	const svg = elements(doc).find((el) => el.name === "svg");
	let at = 0;
	while (
		at < svg.kids.length &&
		(svg.kids[at].type !== "el" || ["title", "desc"].includes(svg.kids[at].name))
	)
		at++;
	svg.kids.splice(at, 0, element("defs", [], shared));
}

/** Removes filters that nothing refers to any more, and <defs> left empty. */
function removeUnusedFilters(doc, notes) {
	const used = new Set();
	(function scan(node) {
		for (const kid of node.kids) {
			if (kid.type === "text" || kid.type === "raw") {
				for (const m of kid.text.matchAll(/url\(\s*['"]?#([^'")\s]+)/g)) used.add(m[1]);
				continue;
			}
			for (const [k, v] of kid.attrs) {
				for (const m of decode(v).matchAll(/url\(\s*['"]?#([^'")\s]+)/g)) used.add(m[1]);
				if (k === "href" || k === "xlink:href") used.add(decode(v).slice(1));
			}
			scan(kid);
		}
	})(doc);
	(function prune(node) {
		node.kids = node.kids.filter((k) => {
			if (k.type !== "el" || k.name !== "filter") return true;
			const id = decode(getAttr(k, "id") ?? "");
			if (used.has(id)) return true;
			const kinds = elements(k).map((p) => p.name);
			const known = kinds.includes("feDisplacementMap") || kinds.includes("feMorphology");
			if (!known) notes.push(`removed unused filter #${id} (${kinds.join(", ")})`);
			return false;
		});
		for (const k of elements(node)) prune(k);
		node.kids = node.kids.filter((k) => !(k.type === "el" && k.name === "defs" && !k.kids.length));
	})(doc);
}

// ------------------------------------------------------------------ command line

function main(args) {
	const inPlace = args[0] === "--in-place";
	const files = inPlace ? args.slice(1) : args.slice(0, 1);
	if (!files.length || (!inPlace && args.length > 2)) {
		console.error("usage: node tools/bake.mjs <in.svg> [out.svg]");
		console.error("       node tools/bake.mjs --in-place <file.svg>...");
		process.exit(2);
	}
	let failed = 0;
	for (const file of files) {
		const before = readFileSync(file, "utf8");
		let result;
		try {
			result = bakeSvg(before);
		} catch (e) {
			console.error(`${file}: not baked, ${e.message}`);
			failed++;
			continue;
		}
		const { svg, notes } = result;
		if (inPlace || args[1]) {
			const target = inPlace ? file : args[1];
			if (!inPlace || svg !== before) writeFileSync(target, svg);
			const kb = (s) => `${(Buffer.byteLength(s) / 1024).toFixed(1)} KB`;
			const what = svg === before ? "unchanged" : `${kb(before)} -> ${kb(svg)}`;
			console.error(`${file}: ${what}`);
			for (const note of notes) console.error(`  ${note}`);
		} else {
			process.stdout.write(svg);
			for (const note of notes) console.error(note);
		}
	}
	if (failed) process.exit(1);
}

// Run as a command, not when imported (tools/build.mjs imports bakeSvg).
const invoked = process.argv[1] && realpathSync(process.argv[1]);
if (invoked === realpathSync(fileURLToPath(import.meta.url))) main(process.argv.slice(2));
