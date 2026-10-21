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
// None of this work happens while the page scrolls. Once the page has loaded, the drawings
// within a few viewports of the screen are prepared, nearest first, whenever the page is
// calm (no scroll for CALM_MS, and the browser idle): first the still, then, with motion
// on, the motion layer. Each heavy step (loading, parsing, inserting) gets a turn of its
// own, one per frame. The still shows until the swap, so waiting costs nothing visible.
//
// With JS the page opens behind a loading screen (the last section below), and all of that
// preparation happens there, up front: every drawing, nearest first, before the reveal.
(() => {
	"use strict";

	const KEY = "sf-motion";
	const CALM_MS = 200; // the page counts as calm once it hasn't scrolled for this long
	// How far ahead, in viewports, drawings are prepared. Stills go further: a still is what
	// shows during a scroll, so decoding it in the middle of one would stall the scroll. An
	// upgrade never runs mid-scroll anyway, so it only needs to be ready by arrival.
	const STILL_AHEAD = 3;
	const MOTION_AHEAD = 1.5;
	const root = document.documentElement;
	const reduce = matchMedia("(prefers-reduced-motion: reduce)");
	const finePointer = matchMedia("(hover: hover) and (pointer: fine)");
	const images = [...document.querySelectorAll("img[data-motion][data-motion-base]")];
	const toggle = document.querySelector(".motion-toggle");
	const overlays = []; // { svg, img, ownFit, looks, onScreen } for each motion layer on the page
	// The drawings in the first screen (no loading="lazy": the hero), noted before this script
	// makes any of the others eager.
	const firstScreen = new Set(images.filter((img) => img.getAttribute("loading") !== "lazy"));
	const pending = new Set(images); // drawings whose upgrade hasn't started yet
	const near = new Set(); // ...those of them within STILL_AHEAD of the screen
	const close = new Set(); // ...and within MOTION_AHEAD
	const asked = new Set(); // drawings whose still has been asked for
	// The loading screen, up from the first paint (the head script set .is-loading).
	const loader = document.querySelector(".loader");
	let loading = !!loader && root.classList.contains("is-loading");

	// A stored "on" or "off" wins; without one, follow the system setting.
	// Storage can throw (private windows, blocked cookies), so every access is guarded.
	let choice = null;
	try { choice = localStorage.getItem(KEY); } catch {}
	let on = false;
	let loaded = document.readyState === "complete";

	function apply() {
		on = choice === "on" || (choice !== "off" && !reduce.matches);
		root.classList.toggle("motion-off", !on);
		// Back on, every unparked overlay's loops were just recreated, on their authored phases;
		// those in view start at once, as at the reveal (see start()). (Marked again, in case
		// motion went off while an overlay was being inserted: off, it had no loops to mark.)
		if (on) for (const o of overlays) mark(o.svg);
		if (on) for (const o of overlays) if (o.onScreen && !parked(o)) start(o);
		if (toggle) {
			// The label names the action, like a video player's button, so no aria-pressed:
			// "Play animations, pressed" would read as a contradiction.
			toggle.dataset.state = on ? "playing" : "paused";
			toggle.querySelector(".motion-label").textContent = on ? "Pause animations" : "Play animations";
		}
		if (!on) stopTracking();
		watch();
	}

	// Calm: no scroll for CALM_MS, then an idle period, checked again since a scroll can start
	// while waiting for one. (Safari has no requestIdleCallback: there it is just after a frame.)
	let lastScroll = -Infinity;
	const scrolling = () => performance.now() - lastScroll < CALM_MS;
	const idle = window.requestIdleCallback ? (go) => requestIdleCallback(go, { timeout: 1000 }) : (go) => setTimeout(go, 0);
	function whenCalm(go) {
		if (scrolling()) setTimeout(() => whenCalm(go), lastScroll + CALM_MS - performance.now());
		else idle(() => (scrolling() ? whenCalm(go) : go()));
	}

	// Each heavy step waits for a turn: a frame, then calm. One step per turn, so two big SVGs
	// are never parsed or inserted in the same frame, and none of it lands in a scroll. Behind
	// the loading screen nobody can scroll or see the page, and the screen's own animation
	// runs off the main thread, so there a turn is just a new task (the bar still updates).
	let turns = Promise.resolve();
	const turn = () => (turns = turns.then(() => new Promise((go) => (loading ? setTimeout(go, 0) : requestAnimationFrame(() => whenCalm(go))))));

	// Which drawings to prepare. Watching starts once the page's own images and fonts have
	// loaded, so motion never delays them. The drawing in the first screen is always wanted;
	// any other while its frame is within reach of the screen.
	const watcher = (set, viewports) =>
		new IntersectionObserver((entries) => {
			for (const { target, isIntersecting } of entries) {
				if (pending.has(target) && (isIntersecting || firstScreen.has(target))) set.add(target);
				else set.delete(target);
			}
			work();
		}, { rootMargin: `${viewports * 100}% 0px` });
	const watchers = [watcher(near, STILL_AHEAD), watcher(close, MOTION_AHEAD)];

	function watch() {
		if (!loaded || loading) return; // the loading screen prepares everything itself
		for (const w of watchers) {
			for (const img of pending) {
				w.unobserve(img); // observing again reports where it is now
				w.observe(img);
			}
		}
	}
	if (!loaded) {
		addEventListener("load", () => {
			loaded = true;
			watch();
		}, { once: true });
	}

	// One drawing at a time, nearest first, while any is left to prepare: a still to load
	// (with motion on or off), or, with motion on and within MOTION_AHEAD (anywhere, behind
	// the loading screen), an upgrade. A drawing whose files are slow to arrive gets a few
	// seconds, then keeps loading on its own while the next one starts.
	// Behind the loading screen with motion on, the still is skipped: the base and the motion
	// layer replace it before anyone could see it.
	const stillDue = (img) => !asked.has(img) && !img.complete && !(loading && on);
	const upgradeDue = (img) => on && pending.has(img) && (loading || close.has(img));
	const atMost = (promise, ms) => Promise.race([promise, new Promise((done) => setTimeout(done, ms))]);
	let working = false;
	async function work() {
		if (working) return;
		working = true;
		for (;;) {
			await turn();
			const img = nearest();
			if (!img) break;
			await atMost(prepare(img), 3000);
		}
		working = false;
	}

	// The nearest drawing with something due. A turn starts just after a frame, so these
	// layout reads are cheap.
	const distance = (img) => {
		const r = img.getBoundingClientRect();
		return Math.max(0, r.top - innerHeight, -r.bottom);
	};
	function nearest() {
		let best = null, least = Infinity;
		for (const img of loading ? images : new Set([...near, ...close])) {
			if (!stillDue(img) && !upgradeDue(img)) continue;
			const d = distance(img);
			if (d < least) [best, least] = [img, d];
		}
		return best;
	}

	async function prepare(img) {
		// The still comes first: it is what shows until the swap, and loading it now, while
		// the page is calm, keeps its decode out of the next scroll.
		if (stillDue(img)) {
			asked.add(img);
			img.loading = "eager";
			await img.decode().catch(() => {});
			if (upgradeDue(img)) await turn();
		}
		reached(img, "still");
		if (upgradeDue(img)) await upgrade(img);
	}

	// Ids get a per-file prefix: every motion file has its own halftone patterns and clip
	// paths, say, and they all end up in one document.
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

	// A drawing's motion files, asked for once: the motion layer's text and the base, decoded.
	const files = new Map();
	function filesOf(img) {
		if (!files.has(img)) {
			const base = new Image();
			base.src = img.dataset.motionBase;
			const text = fetch(img.dataset.motion).then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status} ${r.url}`))));
			files.set(img, Promise.all([text, base.decode().then(() => base)]));
		}
		return files.get(img);
	}

	async function upgrade(img) {
		pending.delete(img);
		near.delete(img);
		close.delete(img);
		for (const w of watchers) w.unobserve(img);
		let svg = null;
		try {
			const [text, base] = await filesOf(img);
			reached(img, "files");
			const name = img.dataset.motion.replace(/^.*\//, "").replace(/(-motion)?\.svg$/, "");
			await turn();
			const doc = new DOMParser().parseFromString(prefixIds(text, `sf-${name}-`), "image/svg+xml");
			if (doc.documentElement.localName !== "svg" || doc.querySelector("parsererror")) throw new Error(`bad SVG in ${img.dataset.motion}`);
			reached(img, "parse");
			await turn();
			// Adopted, not imported: the parsed tree moves into the page instead of being copied.
			svg = document.adoptNode(doc.documentElement);
			// It starts parked (see the overlay watches below), until it comes near the screen.
			svg.classList.add("sf-motion", "sf-paused");
			svg.setAttribute("aria-hidden", "true");
			svg.setAttribute("focusable", "false");
			svg.removeAttribute("role");
			const overlay = { svg, img, ownFit: svg.getAttribute("preserveAspectRatio"), looks: [...svg.querySelectorAll(".sf-look")], onScreen: false };
			// A turn starts just after a frame, so the layout is clean and this read is cheap.
			place(overlay, measure(overlay));
			// One synchronous step, with the base already decoded: overlay and base appear
			// in the same frame, so the drawing never flickers or doubles up.
			img.decoding = "sync";
			img.after(svg);
			dropReducedMotionRules(svg);
			mark(svg); // (so the parked rule holds every part at rest from this frame on)
			img.src = base.src;
			// The base is in memory already: don't let the browser's own lazy-loading distance,
			// which can be shorter than ours, hold it back.
			img.loading = "eager";
			overlays.push(overlay);
			for (const w of overlayWatches) w.observe(svg);
			reached(img, "insert");
		} catch (error) {
			// Anything wrong (missing file, bad markup): keep the still.
			if (svg) svg.remove();
			img.loading = "eager"; // (skipped behind the loading screen, so it may not be in yet)
			console.warn("Storyfolk motion: keeping the still image.", error);
			for (const step of ["files", "parse", "insert"]) reached(img, step); // the loader stops waiting
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

	// Mark every animated element, so parking (.sf-paused .sf-a in the CSS) restyles only those:
	// the crowd has 328 of them among 6900 elements.
	function mark(svg) {
		for (const a of svg.getAnimations({ subtree: true })) a.effect.target.classList.add("sf-a");
	}

	// The files desynchronise their loops with negative delays, the designed steady state: a
	// loop (re)created out of sight starts mid-cycle, as if it had always been running. Where a
	// restart is seen, that would make parts jump, so there the loops rest-start: each cycle
	// starts and ends at rest, and the matching positive delay holds the part at rest, then
	// joins its loop at exactly the same phase. That is for the glances when cursor tracking
	// ends, and for drawings that never kick (see start()).
	function settle(svg, only = null) {
		const anims = svg.getAnimations({ subtree: true });
		// When only some loops restart (the glances), the ones that kept running say how far the
		// layer's shared timeline has got, so the restarted ones rejoin it in step, give or take
		// the frame or two a new animation waits before it starts. (Every loop new: this is 0.)
		const elapsed = Math.max(0, ...anims.map((a) => a.currentTime ?? 0));
		// Every timing is read before any is written: each read flushes pending style, so
		// alternating them recalculated style once per animation (about 5x slower).
		const fixes = [];
		for (const a of only || anims) {
			const { delay } = a.effect.getTiming();
			const { duration, iterations, direction } = a.effect.getComputedTiming();
			if (!(delay < 0 && duration > 0 && iterations === Infinity)) continue;
			const period = direction.includes("alternate") ? 2 * duration : duration;
			const d = (elapsed - delay) % period;
			fixes.push([a, d === 0 ? 0 : period - d]);
		}
		for (const [a, delay] of fixes) a.effect.updateTiming({ delay });
	}

	// Where a loop's motion starts, as a fraction of its cycle: the last keyframe still at the
	// rest pose (keyframe 0) before the first that differs, in transform or opacity. Null for
	// a loop that never holds the rest pose (no two keyframes at rest in a row), such as Nib's
	// float or a flame: it moves all the time.
	function motionStart(a) {
		const keyframes = a.effect.getKeyframes();
		let start = null;
		for (const p of ["transform", "opacity"]) {
			const kfs = keyframes.filter((k) => k[p] !== undefined);
			const rest = kfs[0]?.[p];
			if (kfs.length < 2 || kfs.every((k) => k[p] === rest)) continue;
			if (!kfs.some((k, i) => i && k[p] === rest && kfs[i - 1][p] === rest && k.computedOffset > kfs[i - 1].computedOffset)) return null;
			let s = 0;
			for (let i = 1; kfs[i][p] === rest; i++) s = kfs[i].computedOffset;
			start = start === null ? s : Math.min(start, s);
		}
		return start;
	}

	// Curtain up: every gesture of an overlay in view starts now, instead of wherever its loop
	// happens to be. Parts that share a duration and a delay make one gesture (Moss's arm, his
	// trailing hand and his brows), so each such group is shifted as one, keeping the parts in
	// step: its earliest motion start comes now, or up to KICK_RIPPLE_MS later from left to
	// right across the drawing. A gesture starts from the rest pose by design, so nothing
	// jumps. Loops that never hold the rest pose keep their phase: they move anyway. Seen while
	// it happens (gentle: a still swapped in view, an overlay unparked in view), those
	// rest-start instead, so that they don't jump either.
	const KICK_RIPPLE_MS = 150;
	function kick(svg, gentle = false) {
		const groups = new Map();
		for (const a of svg.getAnimations({ subtree: true })) {
			const { delay } = a.effect.getTiming();
			const { duration, iterations } = a.effect.getComputedTiming();
			if (!(duration > 0 && iterations === Infinity)) continue;
			const key = `${duration} ${delay}`;
			if (!groups.has(key)) groups.set(key, { duration, anims: [] });
			groups.get(key).anims.push(a);
		}
		// Every read before any write (see settle()).
		const box = svg.getBoundingClientRect();
		const shifts = [], loops = [];
		for (const { duration, anims } of groups.values()) {
			const starts = anims.map(motionStart);
			if (starts.includes(null)) {
				loops.push(...anims);
				continue;
			}
			const x = anims.reduce((sum, a) => { const r = a.effect.target.getBoundingClientRect(); return sum + r.left + r.width / 2; }, 0) / anims.length;
			const ripple = KICK_RIPPLE_MS * Math.min(1, Math.max(0, (x - box.left) / box.width));
			shifts.push([anims, Math.min(...starts) * duration - ripple]);
		}
		if (gentle) settle(svg, loops);
		for (const [anims, time] of shifts) {
			for (const a of anims) {
				a.effect.updateTiming({ delay: 0 });
				a.currentTime = time; // (below 0: at rest until then)
			}
		}
	}

	// Eyes follow the cursor. Each .sf-look carries data-look: its largest offset, in its
	// file's viewBox units. Only those transforms are ever touched. The tracking costs
	// nothing unless eyes are on screen and the pointer moved in the last IDLE_MS, and it
	// holds still while the page scrolls: the eyes re-aim once, when the scroll settles.
	const IDLE_MS = 2500;
	const REACH_PX = 300; // pointer distance at which the eyes reach their full offset
	const rest = new Map(); // .sf-look -> its rest centre and matrix, in its overlay's units
	let pointer = null, lastMove = 0, frame = 0, idleTimer = 0, reaim = 0, eyesOnScreen = false;
	const schedule = () => {
		if (!pointer || !eyesOnScreen || frame) return;
		if (!scrolling()) frame = requestAnimationFrame(follow);
		else if (!reaim) reaim = setTimeout(() => ((reaim = 0), schedule()), lastScroll + CALM_MS - performance.now());
	};

	// Overlays away from the screen are parked (.sf-paused: their parts rest and run no
	// animation at all), so they cost nothing, not even a compositor layer per part. One unparks
	// as soon as it comes within UNPARK_AHEAD of the screen, mid-scroll or not, so it is already
	// moving when it appears: its loops come back on their authored phases, mid-rhythm. It parks
	// again only once it is beyond PARK_BEYOND, so one that hovers near the edge doesn't churn.
	// Nothing unparks behind the loading screen; its reveal starts what is near (see reveal()).
	// A drawing marked data-motion-calm (the crowd) unparks only once the page is calm: each of
	// its 328 moving parts is a compositor layer, and every frame of a scroll past them would
	// have to draw them all (a fifth of those frames ran late). Overlays in view also get their
	// eyes aimed, if the cursor leads.
	const UNPARK_AHEAD = 0.5; // viewports
	const PARK_BEYOND = 1.5;
	const parked = (o) => o.svg.classList.contains("sf-paused");
	const overlayWatch = (viewports, react) =>
		new IntersectionObserver((entries) => {
			for (const { target, isIntersecting } of entries) react(overlays.find((o) => o.svg === target), isIntersecting);
		}, { rootMargin: `${viewports * 100}% 0px` });
	// (Created in this order, they report in this order: onScreen is current when unparking.)
	const overlayWatches = [
		overlayWatch(0, (o, inView) => {
			o.onScreen = inView;
			eyesOnScreen = overlays.some((o) => o.onScreen && o.looks.length);
			schedule();
		}),
		overlayWatch(UNPARK_AHEAD, (o, near) => (o.near = near) && unpark(o)),
		overlayWatch(PARK_BEYOND, (o, near) => near || o.svg.classList.add("sf-paused")),
	];
	const calmOnly = (o) => "motionCalm" in o.img.dataset;
	function unpark(o) {
		if (loading || !parked(o)) return;
		if (calmOnly(o) && scrolling()) {
			if (!o.waiting) {
				o.waiting = true;
				whenCalm(() => {
					o.waiting = false;
					if (o.near) unpark(o);
				});
			}
			return;
		}
		o.svg.classList.remove("sf-paused");
		// Unparked in view (a still swapped on screen after the loading screen gave up, a jump
		// past UNPARK_AHEAD in one go): start from rest, nothing jumping.
		if (o.onScreen) start(o, true);
	}
	// Starting an overlay in view: a kick, except for a calm-only drawing, which rest-starts and
	// so keeps its designed phases: the crowd, whose 5.4 s choreography keeps only a third of
	// the band moving at any moment (a kick would set the whole band off at once).
	const start = (o, gentle = false) => (calmOnly(o) ? settle(o.svg) : kick(o.svg, gentle));

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
		if (scrolling()) return schedule(); // a scroll began: hold still, re-aim once it settles
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
				// whole device pixels (a pupil held at a fractional offset blurs).
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
		else if (scrolling()) idleTimer = setTimeout(checkIdle, CALM_MS); // not in mid-scroll
		else stopTracking();
	}

	// Hand the eyes back to their idle glances.
	function stopTracking() {
		clearTimeout(idleTimer);
		clearTimeout(reaim);
		cancelAnimationFrame(frame);
		idleTimer = reaim = frame = 0;
		pointer = null;
		for (const { svg, looks } of overlays) {
			for (const el of looks) el.style.removeProperty("transform");
			if (!svg.classList.contains("sf-tracking")) continue;
			svg.classList.remove("sf-tracking");
			settle(svg); // the glances restart
		}
	}

	addEventListener("pointermove", (event) => {
		if (loading || !on || !finePointer.matches || event.pointerType === "touch") return;
		pointer = { x: event.clientX, y: event.clientY };
		lastMove = performance.now();
		schedule();
	}, { passive: true });
	document.addEventListener("pointerout", (event) => {
		if (!event.relatedTarget && pointer) stopTracking(); // left the window
	}, { passive: true });
	// Note when the page last scrolled: heavy work and eye tracking wait for calm.
	addEventListener("scroll", () => {
		lastScroll = performance.now();
		schedule();
	}, { passive: true });
	// The layout changed: refit every overlay, once per frame however many events arrive.
	let refitting = 0;
	function refit() {
		if (refitting) return;
		refitting = requestAnimationFrame(() => {
			refitting = 0;
			const boxes = overlays.map(measure);
			overlays.forEach((o, i) => place(o, boxes[i]));
			schedule();
		});
	}
	addEventListener("resize", refit, { passive: true });
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

	// ---------------------------------------------------------------------------------------
	// Loading screen
	//
	// The head script puts the screen up before the first paint (.is-loading; it shows only
	// with JS). Behind it the page is inert and busy while this prepares, in order: the web
	// fonts, the first screen's images, then every drawing, nearest first: with motion on, its
	// motion layer (inserted parked; the still is skipped, as the base replaces it unseen),
	// with motion off, its still. The bar shows the share of those milestones reached. Once
	// all are, and at least MIN_MS after navigation began, or after MAX_MS whatever is left
	// (the calm-time preparation then finishes it), Nib makes one last hop and the screen
	// lifts away; without motion it fades. The head script removes it after 12 s in any
	// case, should this script never run.
	const MIN_MS = 1000;
	const MAX_MS = 10000;
	const reachedSteps = new Set();
	let expected = null; // the milestones the screen waits for, while it is up
	let behind = []; // the page under the screen: inert and busy meanwhile

	function reached(what, step) {
		reachedSteps.add(typeof what === "string" ? what : `${what.dataset.motion} ${step}`);
		if (loading && expected) showProgress();
	}

	function showProgress() {
		let n = 0;
		for (const step of expected) if (reachedSteps.has(step)) n++;
		loader.querySelector(".loader-fill").style.transform = `scaleX(${n / expected.size})`;
		loader.querySelector(".loader-pct").textContent = `${Math.round((100 * n) / expected.size)}%`;
		if (n === expected.size) setTimeout(reveal, Math.max(0, MIN_MS - performance.now()));
	}

	function reveal() {
		if (!loading) return;
		loading = false;
		for (const el of behind) {
			el.inert = false;
			el.removeAttribute("aria-busy");
		}
		root.classList.remove("is-loading");
		refit(); // should the scrollbar's return have moved the layout
		lift();
		watch(); // the usual calm-time preparation takes over anything left
		// Curtain up: every overlay near the screen unparks, on its authored phases, and those in
		// view kick off together (see kick()). The sheet still covers them as they start.
		for (const o of overlays) {
			const d = distance(o.img);
			if (d > UNPARK_AHEAD * innerHeight || !parked(o)) continue;
			o.svg.classList.remove("sf-paused");
			if (d === 0 && !calmOnly(o)) kick(o.svg);
		}
	}

	// With motion: one last big hop, then the paper lifts away. Without: a short fade.
	// Either way the screen then leaves the DOM.
	function lift() {
		const gone = () => loader.remove();
		loader.addEventListener("transitionend", (event) => event.target === loader && gone());
		setTimeout(gone, 1500);
		if (!on) {
			loader.classList.add("is-leaving");
			return;
		}
		// From wherever Nib is in his bounce: down into a squash, then a leap, his shadow
		// spreading as he lands and shrinking away as he goes (still only transforms and
		// opacity on whole <svg> elements, so the compositor runs them).
		const nib = loader.querySelector(".loader-nib");
		const shadow = loader.querySelector(".loader-shadow");
		const from = getComputedStyle(nib).transform;
		const { transform: shadowFrom, opacity: shadowOpacity } = getComputedStyle(shadow);
		loader.classList.add("is-done");
		const land = { offset: 0.2, easing: "cubic-bezier(0.2, 0.7, 0.4, 1)" };
		const timing = { duration: 560, easing: "cubic-bezier(0.4, 0, 0.6, 1)", fill: "forwards" };
		nib.animate([{ transform: from }, { transform: "translateY(0) scale(1.2, 0.78)", ...land }, { transform: "translateY(-220px) scale(0.94, 1.08)" }], timing);
		shadow.animate([{ transform: shadowFrom, opacity: shadowOpacity }, { transform: "scale(1.2, 1)", opacity: 1, ...land }, { transform: "scale(0.2, 0.5)", opacity: 0 }], timing);
		setTimeout(() => loader.classList.add("is-leaving"), 140);
	}

	if (loader && !loading) loader.remove(); // up without .is-loading: nothing to wait for
	if (loading) {
		behind = [...document.body.children].filter((el) => el !== loader);
		for (const el of behind) {
			el.inert = true;
			el.setAttribute("aria-busy", "true");
		}
		// The milestones: the fonts, each image of the first screen, then for every drawing
		// either its motion layer's three steps (motion on) or its still (motion off).
		const first = [...document.images].filter((img) => !loader.contains(img) && img.getAttribute("loading") !== "lazy");
		expected = new Set(["fonts", ...first.map((img, i) => `first ${i}`)]);
		for (const img of images) {
			if (on) for (const step of ["files", "parse", "insert"]) expected.add(`${img.dataset.motion} ${step}`);
			else if (!firstScreen.has(img)) {
				expected.add(`${img.dataset.motion} still`);
				// However the still arrives (the browser may load it on its own first).
				img.decode().catch(() => {}).then(() => reached(img, "still"));
			}
		}
		showProgress();
		setTimeout(reveal, Math.max(0, MAX_MS - performance.now()));
		(async () => {
			await document.fonts.ready;
			reached("fonts");
			await Promise.all(first.map((img, i) => img.decode().catch(() => {}).then(() => reached(`first ${i}`))));
			// Every motion file is wanted now: ask for them all at once, nearest first, so the
			// network stays busy while the main thread parses and inserts them one by one.
			if (on) for (const img of [...images].sort((a, b) => distance(a) - distance(b))) filesOf(img).catch(() => {});
			work(); // every drawing, nearest first (see nearest() and upgradeDue() while loading)
		})();
	}
})();
