// Storyfolk motion layer.
//
// Each animated illustration x ships as three files: x.svg (the complete still),
// x-base.svg (the still minus its moving parts) and x-motion.svg (only the moving parts,
// animated by their own internal CSS). The page shows the stills. When motion is on, this
// script lays each motion file, inlined as live SVG, exactly over its image and swaps the
// image to the base, so only the small motion layer repaints. Turning motion off just
// stops the animations: every part falls back to its rest pose, and base plus rest pose
// is the still, so nothing needs swapping back.
(() => {
	"use strict";

	const KEY = "sf-motion";
	const root = document.documentElement;
	const reduce = matchMedia("(prefers-reduced-motion: reduce)");
	const finePointer = matchMedia("(hover: hover) and (pointer: fine)");
	const images = [...document.querySelectorAll("img[data-motion][data-motion-base]")];
	const toggle = document.querySelector(".motion-toggle");
	const overlays = []; // { svg, img, ownFit, looks } for each motion layer on the page

	// A stored "on" or "off" wins; without one, follow the system setting.
	// Storage can throw (private windows, blocked cookies), so every access is guarded.
	let choice = null;
	try { choice = localStorage.getItem(KEY); } catch {}
	let on = false, upgraded = false;

	function apply() {
		on = choice === "on" || (choice !== "off" && !reduce.matches);
		root.classList.toggle("motion-off", !on);
		if (on) overlays.forEach((o) => settle(o.svg)); // animations were just recreated
		if (toggle) {
			// The label names the action, like a video player's button, so no aria-pressed:
			// "Play animations, pressed" would read as a contradiction.
			toggle.dataset.state = on ? "playing" : "paused";
			toggle.querySelector(".motion-label").textContent = on ? "Pause animations" : "Play animations";
		}
		if (!on) stopTracking();
		else if (!upgraded) {
			upgraded = true;
			// Wait for the page's own images and fonts, so motion never delays them.
			if (document.readyState === "complete") images.forEach(upgrade);
			else addEventListener("load", () => images.forEach(upgrade), { once: true });
		}
	}

	// Ids get a per-file prefix: every motion file has its own "ink" filter, say, and
	// they all end up in one document.
	const prefixIds = (text, p) =>
		text
			.replace(/(\sid=["'])/g, `$1${p}`)
			.replace(/(\s(?:xlink:)?href=["']#)/g, `$1${p}`)
			.replace(/(url\(\s*(?:["']|&quot;)?#)/g, `$1${p}`);

	// Crop the overlay exactly as the image is cropped: object-fit cover or contain plus an
	// object-position become preserveAspectRatio slice or meet with the same alignment
	// ("50% 0%" -> "xMidYMin slice"). Re-run on resize, in case a breakpoint changes them.
	function fit(o) {
		const { objectFit, objectPosition } = getComputedStyle(o.img);
		const [x, y] = objectPosition.split(" ").map((v) => (parseFloat(v) <= 0 ? "Min" : parseFloat(v) >= 100 ? "Max" : "Mid"));
		const mode = { cover: "slice", contain: "meet" }[objectFit];
		const value = mode ? `x${x}Y${y} ${mode}` : o.ownFit;
		if (value) o.svg.setAttribute("preserveAspectRatio", value);
		else o.svg.removeAttribute("preserveAspectRatio");
		// The browser draws the image into its box snapped to whole device pixels, but scales
		// inline SVG to the exact box: nudge the overlay onto the image's snapped box, so a
		// frame at a fractional position doesn't leave the layers up to a pixel apart. The
		// nudges stay relative to the frame, so a stale one is off by under a pixel at most.
		const dpr = devicePixelRatio || 1;
		const snap = (v) => Math.round(v * dpr) / dpr;
		const r = o.img.getBoundingClientRect();
		const [left, top] = [r.left + scrollX, r.top + scrollY];
		const [dx, dy] = [snap(left) - left, snap(top) - top];
		Object.assign(o.svg.style, {
			left: `${dx}px`,
			top: `${dy}px`,
			width: `calc(100% + ${snap(left + r.width) - snap(left) - r.width}px)`,
			height: `calc(100% + ${snap(top + r.height) - snap(top) - r.height}px)`,
		});
	}

	async function upgrade(img) {
		let svg = null;
		try {
			const base = new Image();
			base.src = img.dataset.motionBase;
			const load = fetch(img.dataset.motion).then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status} ${r.url}`))));
			const [text] = await Promise.all([load, base.decode()]);
			const name = img.dataset.motion.replace(/^.*\//, "").replace(/(-motion)?\.svg$/, "");
			const doc = new DOMParser().parseFromString(prefixIds(text, `sf-${name}-`), "image/svg+xml");
			if (doc.documentElement.localName !== "svg" || doc.querySelector("parsererror")) throw new Error(`bad SVG in ${img.dataset.motion}`);
			svg = document.importNode(doc.documentElement, true);
			svg.classList.add("sf-motion");
			svg.setAttribute("aria-hidden", "true");
			svg.setAttribute("focusable", "false");
			svg.removeAttribute("role");
			const overlay = { svg, img, ownFit: svg.getAttribute("preserveAspectRatio"), looks: [...svg.querySelectorAll(".sf-look")] };
			fit(overlay);
			// One synchronous step, with the base already decoded: overlay and base appear
			// in the same frame, so the drawing never flickers or doubles up.
			img.decoding = "sync";
			img.after(svg);
			dropReducedMotionRules(svg);
			settle(svg);
			img.src = base.src;
			overlays.push(overlay);
			offscreen.observe(svg);
		} catch (error) {
			// Anything wrong (missing file, bad markup): keep the still.
			if (svg) svg.remove();
			console.warn("Storyfolk motion: keeping the still image.", error);
		}
	}

	// The motion files stop themselves under prefers-reduced-motion. Inlined here, the page
	// decides instead (html.motion-off), so a visitor who presses Play does get motion.
	function dropReducedMotionRules(svg) {
		for (const { sheet } of svg.querySelectorAll("style")) {
			for (let i = sheet ? sheet.cssRules.length - 1 : -1; i >= 0; i--) {
				if (/prefers-reduced-motion/.test(sheet.cssRules[i].media?.mediaText)) sheet.deleteRule(i);
			}
		}
	}

	// The files desynchronise their loops with negative delays, which would start every part
	// mid-cycle the moment it appears. Each cycle starts and ends at rest, so the matching
	// positive delay holds the part at rest, then joins its loop at exactly the same phase.
	// Run whenever animations are (re)created: on insertion, motion on, tracking over.
	function settle(svg) {
		for (const a of svg.getAnimations({ subtree: true })) {
			const { delay } = a.effect.getTiming();
			const { duration, iterations, direction } = a.effect.getComputedTiming();
			if (!(delay < 0 && duration > 0 && iterations === Infinity)) continue;
			const period = direction.includes("alternate") ? 2 * duration : duration;
			const d = -delay % period;
			a.effect.updateTiming({ delay: d === 0 ? 0 : period - d });
		}
	}

	// Eyes follow the cursor. Each .sf-look carries data-look: its largest offset, in its
	// file's viewBox units. Only those transforms are ever touched.
	const IDLE_MS = 2500;
	const REACH_PX = 300; // pointer distance at which the eyes reach their full offset
	let rest = new Map(); // .sf-look -> its rest centre and matrix, until scroll or resize
	let pointer = null, frame = 0, idle = 0;
	const schedule = () => {
		if (pointer && !frame) frame = requestAnimationFrame(follow);
	};

	// Overlays out of view pause, so they cost nothing. One that comes into view while the
	// cursor leads gets its eyes re-aimed.
	const offscreen = new IntersectionObserver((entries) => {
		for (const entry of entries) entry.target.classList.toggle("sf-paused", !entry.isIntersecting);
		schedule();
	});

	// The rest-pose matrix from an element's user space to the viewport: the overlay's
	// screen matrix times each transform attribute on the way down. CSS animations (a
	// blink's scaleY, a sway) are left out on purpose, so a mid-blink reading can't skew it.
	function restMatrix(el, svg) {
		let m = new DOMMatrix();
		for (let n = el; n !== svg; n = n.parentNode) {
			const t = n.transform?.baseVal.consolidate();
			if (t) m = DOMMatrix.fromMatrix(t.matrix).multiply(m);
		}
		return DOMMatrix.fromMatrix(svg.getScreenCTM()).multiply(m);
	}

	function restOf(el, svg) {
		if (!rest.has(el)) {
			const parent = restMatrix(el.parentNode, svg); // the parent's getScreenCTM(), at rest
			const box = el.getBBox();
			const c = new DOMPoint(box.x + box.width / 2, box.y + box.height / 2).matrixTransform(parent);
			const px = Math.hypot(svg.getScreenCTM().a, svg.getScreenCTM().b); // px per viewBox unit
			rest.set(el, { x: c.x, y: c.y, inverse: parent.inverse(), reach: (parseFloat(el.dataset.look) || 0) * px });
		}
		return rest.get(el);
	}

	function follow() {
		frame = 0;
		if (!pointer) return;
		const dpr = devicePixelRatio || 1;
		for (const { svg, looks } of overlays) {
			if (svg.classList.contains("sf-paused") || !looks.length) continue;
			svg.classList.add("sf-tracking"); // also settles the glances before measuring
			for (const el of looks) {
				const r = restOf(el, svg);
				const vx = pointer.x - r.x;
				const vy = pointer.y - r.y;
				const dist = Math.hypot(vx, vy);
				// Screen offset: up to `reach` px towards the pointer, full at REACH_PX away, in
				// whole device pixels (an ink-filtered part held at a fractional offset blurs).
				const k = dist < 0.5 ? 0 : (r.reach * Math.min(1, dist / REACH_PX)) / dist;
				const sx = Math.round(vx * k * dpr) / dpr;
				const sy = Math.round(vy * k * dpr) / dpr;
				const m = r.inverse; // ...then mapped into the element's local units
				el.style.transform = `translate(${(m.a * sx + m.c * sy).toFixed(3)}px, ${(m.b * sx + m.d * sy).toFixed(3)}px)`;
			}
		}
	}

	// Hand the eyes back to their idle glances.
	function stopTracking() {
		clearTimeout(idle);
		cancelAnimationFrame(frame);
		frame = 0;
		pointer = null;
		for (const { svg, looks } of overlays) {
			for (const el of looks) el.style.removeProperty("transform");
			if (!svg.classList.contains("sf-tracking")) continue;
			svg.classList.remove("sf-tracking");
			settle(svg); // the glances restart
		}
	}

	const onMove = (event) => {
		if (!on || !finePointer.matches || event.pointerType === "touch") return;
		pointer = { x: event.clientX, y: event.clientY };
		clearTimeout(idle);
		idle = setTimeout(stopTracking, IDLE_MS);
		schedule();
	};
	addEventListener("pointermove", onMove, { passive: true });
	document.addEventListener("pointerout", (event) => {
		if (!event.relatedTarget && pointer) stopTracking(); // left the window
	});
	// Layout moved: drop the cached centres, and keep watching a pointer that stays put.
	const forget = () => {
		rest = new Map();
		schedule();
	};
	addEventListener("scroll", forget, { passive: true });
	addEventListener("resize", () => {
		overlays.forEach(fit);
		forget();
	});
	finePointer.addEventListener("change", stopTracking);

	// Follow the system setting live while no choice is stored.
	reduce.addEventListener("change", apply);

	if (toggle) {
		toggle.hidden = false;
		toggle.addEventListener("click", () => {
			choice = on ? "off" : "on";
			try { localStorage.setItem(KEY, choice); } catch {}
			apply();
		});
	}
	apply();
})();
