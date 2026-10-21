// Storyfolk motion layer.
//
// Each animated illustration x ships as three files: x.svg (the complete still),
// x-base.svg (the still minus its moving parts) and x-motion.svg (only the moving parts,
// animated by their own internal CSS). The page shows the stills. When motion is on, this
// script lays each motion file, inlined as live SVG, exactly over its image and swaps the
// image to the base, so only the small motion layer repaints. Turning motion off just
// stops the animations: every part falls back to its rest pose, and base plus rest pose
// is the still, so nothing needs swapping back.
//
// Nothing is fetched before it is needed. The hero upgrades as soon as the page has
// loaded; every other drawing only when its frame comes within about a viewport of the
// screen. The heavy steps (parsing a motion file, inserting it) take turns, one per frame.
(() => {
	"use strict";

	const KEY = "sf-motion";
	const root = document.documentElement;
	const reduce = matchMedia("(prefers-reduced-motion: reduce)");
	const finePointer = matchMedia("(hover: hover) and (pointer: fine)");
	const images = [...document.querySelectorAll("img[data-motion][data-motion-base]")];
	const toggle = document.querySelector(".motion-toggle");
	const overlays = []; // { svg, img, ownFit, looks, onScreen } for each motion layer on the page
	const waiting = new Set(images); // images whose upgrade hasn't started yet

	// A stored "on" or "off" wins; without one, follow the system setting.
	// Storage can throw (private windows, blocked cookies), so every access is guarded.
	let choice = null;
	try { choice = localStorage.getItem(KEY); } catch {}
	let on = false;
	let loaded = document.readyState === "complete";

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
		watch();
	}

	// When each image upgrades. First the page's own images and fonts load, so motion never
	// delays them. Then an image in the first screen (no loading="lazy": the hero) upgrades
	// at once, and a lazy one when its frame comes within a viewport of the screen. With
	// motion off nothing new starts; an upgrade already under way finishes, at rest.
	const nearby = new IntersectionObserver((entries) => {
		for (const entry of entries) if (entry.isIntersecting) upgrade(entry.target);
	}, { rootMargin: "100% 0px" });

	function watch() {
		if (!loaded) return;
		for (const img of waiting) {
			if (!on) nearby.unobserve(img);
			else if (img.getAttribute("loading") === "lazy") nearby.observe(img);
			else upgrade(img);
		}
	}
	if (!loaded) {
		addEventListener("load", () => {
			loaded = true;
			watch();
		}, { once: true });
	}

	// The heavy steps each wait for a turn: one turn per frame, in idle time when the
	// browser offers some, so two big SVGs are never parsed or inserted in the same frame.
	// (Safari has no requestIdleCallback: there a turn starts right after the frame.)
	const idle = window.requestIdleCallback ? (go) => requestIdleCallback(go, { timeout: 400 }) : (go) => setTimeout(go, 0);
	let turns = Promise.resolve();
	const turn = () => (turns = turns.then(() => new Promise((go) => requestAnimationFrame(() => idle(go)))));

	// Ids get a per-file prefix: every motion file has its own "ink" filter, say, and
	// they all end up in one document.
	const prefixIds = (text, p) =>
		text
			.replace(/(\sid=["'])/g, `$1${p}`)
			.replace(/(\s(?:xlink:)?href=["']#)/g, `$1${p}`)
			.replace(/(url\(\s*(?:["']|&quot;)?#)/g, `$1${p}`);

	// Crop the overlay exactly as the image is cropped: object-fit cover or contain plus an
	// object-position become preserveAspectRatio slice or meet with the same alignment
	// ("50% 0%" -> "xMidYMin slice"). Redone on resize, in case a breakpoint changes them.
	// Reading (measure) and writing (place) are separate, so that refitting every overlay
	// reads them all first and forces at most one layout.
	function measure(o) {
		const { objectFit, objectPosition } = getComputedStyle(o.img);
		const r = o.img.getBoundingClientRect();
		return { objectFit, objectPosition, left: r.left + scrollX, top: r.top + scrollY, width: r.width, height: r.height };
	}

	function place(o, { objectFit, objectPosition, left, top, width, height }) {
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
		Object.assign(o.svg.style, {
			left: `${snap(left) - left}px`,
			top: `${snap(top) - top}px`,
			width: `calc(100% + ${snap(left + width) - snap(left) - width}px)`,
			height: `calc(100% + ${snap(top + height) - snap(top) - height}px)`,
		});
	}

	async function upgrade(img) {
		if (!waiting.delete(img)) return; // already under way
		nearby.unobserve(img);
		let svg = null;
		try {
			const base = new Image();
			base.src = img.dataset.motionBase;
			const load = fetch(img.dataset.motion).then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status} ${r.url}`))));
			const [text] = await Promise.all([load, base.decode()]);
			const name = img.dataset.motion.replace(/^.*\//, "").replace(/(-motion)?\.svg$/, "");
			await turn();
			const doc = new DOMParser().parseFromString(prefixIds(text, `sf-${name}-`), "image/svg+xml");
			if (doc.documentElement.localName !== "svg" || doc.querySelector("parsererror")) throw new Error(`bad SVG in ${img.dataset.motion}`);
			await turn();
			// Adopted, not imported: the parsed tree moves into the page instead of being copied.
			svg = document.adoptNode(doc.documentElement);
			// It starts paused; the offscreen observer below starts it once it is in view.
			svg.classList.add("sf-motion", "sf-paused");
			svg.setAttribute("aria-hidden", "true");
			svg.setAttribute("focusable", "false");
			svg.removeAttribute("role");
			const overlay = { svg, img, ownFit: svg.getAttribute("preserveAspectRatio"), looks: [...svg.querySelectorAll(".sf-look")], onScreen: false };
			// A turn starts right after a frame, so the layout is clean and this read is cheap.
			place(overlay, measure(overlay));
			// One synchronous step, with the base already decoded: overlay and base appear
			// in the same frame, so the drawing never flickers or doubles up.
			img.decoding = "sync";
			img.after(svg);
			dropReducedMotionRules(svg);
			settle(svg);
			img.src = base.src;
			// The base is in memory already: don't let the browser's own lazy-loading distance,
			// which can be shorter than ours, hold it back.
			img.loading = "eager";
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
		const anims = svg.getAnimations({ subtree: true });
		// When only some loops restart (the glances, after cursor tracking), the ones that kept
		// running say how far the layer's shared timeline has got, so the restarted ones rejoin
		// it in step, give or take the frame or two a new animation waits before it starts.
		// (On insertion, or motion back on, every loop is new and this is 0.)
		const elapsed = Math.max(0, ...anims.map((a) => a.currentTime ?? 0));
		// Every timing is read before any is written: each read flushes pending style, so
		// alternating them recalculated style once per animation (about 5x slower).
		const fixes = [];
		for (const a of anims) {
			const { delay } = a.effect.getTiming();
			const { duration, iterations, direction } = a.effect.getComputedTiming();
			if (!(delay < 0 && duration > 0 && iterations === Infinity)) continue;
			const period = direction.includes("alternate") ? 2 * duration : duration;
			const d = (elapsed - delay) % period;
			fixes.push([a, d === 0 ? 0 : period - d]);
		}
		for (const [a, delay] of fixes) a.effect.updateTiming({ delay });
	}

	// Eyes follow the cursor. Each .sf-look carries data-look: its largest offset, in its
	// file's viewBox units. Only those transforms are ever touched. The tracking costs
	// nothing unless eyes are on screen and the pointer moved in the last IDLE_MS.
	const IDLE_MS = 2500;
	const REACH_PX = 300; // pointer distance at which the eyes reach their full offset
	const rest = new Map(); // .sf-look -> its rest centre and matrix, in its overlay's units
	let pointer = null, lastMove = 0, frame = 0, idleTimer = 0, eyesOnScreen = false;
	const schedule = () => {
		if (pointer && eyesOnScreen && !frame) frame = requestAnimationFrame(follow);
	};

	// Overlays out of view pause, so they cost nothing. One that comes into view while the
	// cursor leads gets its eyes aimed.
	const offscreen = new IntersectionObserver((entries) => {
		for (const entry of entries) {
			const o = overlays.find((o) => o.svg === entry.target);
			o.onScreen = entry.isIntersecting;
			o.svg.classList.toggle("sf-paused", !o.onScreen);
		}
		eyesOnScreen = overlays.some((o) => o.onScreen && o.looks.length);
		schedule();
	});

	// The rest-pose matrix from an element's user space to its overlay's: each transform
	// attribute on the way up. CSS animations (a blink's scaleY, a sway) are left out on
	// purpose, so a mid-blink reading can't skew it.
	function localMatrix(el, svg) {
		let m = new DOMMatrix();
		for (let n = el; n !== svg; n = n.parentNode) {
			const t = n.transform?.baseVal.consolidate();
			if (t) m = DOMMatrix.fromMatrix(t.matrix).multiply(m);
		}
		return m;
	}

	// Measured once per eye, at rest, in its overlay's own units, which scrolling and resizing
	// don't change: only the overlay's screen matrix does, and that is read every frame.
	function restOf(el, svg) {
		if (!rest.has(el)) {
			const local = localMatrix(el.parentNode, svg); // the parent's matrix, at rest
			const box = el.getBBox();
			const centre = new DOMPoint(box.x + box.width / 2, box.y + box.height / 2).matrixTransform(local);
			rest.set(el, { local, centre, look: parseFloat(el.dataset.look) || 0 });
		}
		return rest.get(el);
	}

	function follow() {
		frame = 0;
		if (!pointer) return;
		if (performance.now() - lastMove > IDLE_MS) return stopTracking();
		const live = overlays.filter((o) => o.onScreen && o.looks.length);
		// Every read before any write, so no layout is forced in between.
		for (const { svg } of live) svg.classList.add("sf-tracking"); // also settles the glances before measuring
		const reads = live.map((o) => ({ o, screen: DOMMatrix.fromMatrix(o.svg.getScreenCTM()), eyes: o.looks.map((el) => restOf(el, o.svg)) }));
		const dpr = devicePixelRatio || 1;
		for (const { o, screen, eyes } of reads) {
			const px = Math.hypot(screen.a, screen.b); // px per viewBox unit
			o.looks.forEach((el, i) => {
				const r = eyes[i];
				const c = r.centre.matrixTransform(screen);
				const vx = pointer.x - c.x;
				const vy = pointer.y - c.y;
				const dist = Math.hypot(vx, vy);
				// Screen offset: up to `reach` px towards the pointer, full at REACH_PX away, in
				// whole device pixels (an ink-filtered part held at a fractional offset blurs).
				const k = dist < 0.5 ? 0 : (r.look * px * Math.min(1, dist / REACH_PX)) / dist;
				const sx = Math.round(vx * k * dpr) / dpr;
				const sy = Math.round(vy * k * dpr) / dpr;
				const m = screen.multiply(r.local).inverse(); // ...then mapped into the element's local units
				el.style.transform = `translate(${(m.a * sx + m.c * sy).toFixed(3)}px, ${(m.b * sx + m.d * sy).toFixed(3)}px)`;
			});
		}
		// One timer per IDLE_MS, not one per pointer move.
		if (!idleTimer) idleTimer = setTimeout(checkIdle, IDLE_MS);
	}

	function checkIdle() {
		const left = lastMove + IDLE_MS - performance.now();
		if (left > 0) idleTimer = setTimeout(checkIdle, left);
		else stopTracking();
	}

	// Hand the eyes back to their idle glances.
	function stopTracking() {
		clearTimeout(idleTimer);
		cancelAnimationFrame(frame);
		idleTimer = frame = 0;
		pointer = null;
		for (const { svg, looks } of overlays) {
			for (const el of looks) el.style.removeProperty("transform");
			if (!svg.classList.contains("sf-tracking")) continue;
			svg.classList.remove("sf-tracking");
			settle(svg); // the glances restart
		}
	}

	addEventListener("pointermove", (event) => {
		if (!on || !finePointer.matches || event.pointerType === "touch") return;
		pointer = { x: event.clientX, y: event.clientY };
		lastMove = performance.now();
		schedule();
	}, { passive: true });
	document.addEventListener("pointerout", (event) => {
		if (!event.relatedTarget && pointer) stopTracking(); // left the window
	}, { passive: true });
	// The page scrolled under a pointer that stays put: re-aim. Nothing to re-measure.
	addEventListener("scroll", schedule, { passive: true });
	// The layout changed: refit every overlay, once per frame however many events arrive.
	let refitting = 0;
	addEventListener("resize", () => {
		if (refitting) return;
		refitting = requestAnimationFrame(() => {
			refitting = 0;
			const boxes = overlays.map(measure);
			overlays.forEach((o, i) => place(o, boxes[i]));
			schedule();
		});
	}, { passive: true });
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
