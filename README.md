# Storyfolk

A static one-page website for Storyfolk, a fictional independent creative collective
that makes characters and adventure stories for kids and grown-ups. It is drawn in a
black-and-white, hand-inked comic-book style: ink (`#111111`) on paper (`#ffffff`),
halftone dot shading and chunky lettering.

There is no build step and no JavaScript library. The page is plain HTML and CSS, with
one short inline script that puts up the loading screen and opens and closes the phone menu,
and one small script, `motion.js`, that gets the page ready behind the loading screen and
brings the drawings to life (see [Loading screen](#loading-screen) and [Motion](#motion)).
The fonts (Outfit and Lora) come from Google Fonts, and the page falls back to system fonts
without them.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The page: loading screen, header, hero, about band, universe, crowd band, together, join, footer |
| `styles.css` | All styles: design tokens, layout, the CSS halftone band, breakpoints at 1024px and 760px |
| `motion.js` | The motion layer: inlines the animated parts over the drawings, the pause toggle, eyes that follow the cursor; and the loading screen's logic |
| `assets/logo-mark.svg` | The logo mark and favicon: a face peeking over an open book |
| `assets/hero-letters.svg` | Hero layer 1 (1600x900): the hand-lettered STORY / FOLK wordmark |
| `assets/hero-cast.svg` | Hero layer 2 (1600x900): the cast perched on the letters, stacked exactly over layer 1 |
| `assets/caravan.svg` | The snail caravan (1000x800), in the halftone band |
| `assets/lineup.svg` | Character line-up (1600x700): Juniper, Moss, Nib, Captain Ribbit and Bolt |
| `assets/crowd.svg` | Crowd of portraits (1600x1100) under the giant "staycurious" wordmark |
| `assets/treehouse.svg` | The treehouse village (1400x1000), bleeding off the left edge |
| `assets/duo.svg` | Pip and Juniper setting out (700x820), in the join section |
| `assets/reader.svg` | Wren reading on a stack of books (800x800), in the footer |
| `assets/*-base.svg`, `assets/*-motion.svg` | The motion files of the seven animated drawings (see [Motion](#motion)) |
| `tools/generate-*.py`, `tools/generate-crowd.mjs` | The generators that write the illustrations (see below) |
| `tools/build.mjs` | Rebuilds all of the art in one command: runs every generator, then bakes every drawing |
| `tools/bake.mjs` | Bakes the ink wobble and the white halos into plain geometry, so no SVG filter runs at draw time |

Every `<img>` carries its width and height, so the layout holds its shape while the
drawings load. In the HTML the drawings below the first screen load lazily; with JavaScript
the loading screen prepares them all up front (see [Loading screen](#loading-screen)).

## Preview

Open `index.html` in a browser to see the still drawings, or serve the folder to see them
move (the motion layer fetches its files, which browsers do not allow from `file://`):

```sh
npx serve .
```

## How each illustration is made

Every drawing is an SVG of hand-placed path data, with ink outlines and halftone and hatch
patterns. Most are written out by a script in `tools/`, which assembles the groups, clips
and repeated texture marks; for those, edit the script and rebuild rather than editing the
SVG. The scripts draw the hand-inked wobble and the white outlines around some characters
as SVG filters (`url(#ink)`, a light turbulence displacement, and `url(#halo)`, a white
dilation). `tools/bake.mjs` then bakes both into the geometry, so the published files
carry no filters (see [The bake](#the-bake)). Run every script from the repository root.

| Illustration | How it is produced |
| --- | --- |
| `assets/logo-mark.svg` | Written by hand as SVG; no generator |
| `assets/hero-letters.svg` | `python3 tools/generate-hero-letters.py` (needs shapely) |
| `assets/hero-cast.svg` | `python3 tools/generate-hero-cast.py`; its contact points are measured from the letter outlines, so regenerate it after changing the letters |
| `assets/caravan.svg` | `python3 tools/generate-caravan.py` |
| `assets/lineup.svg` | `python3 tools/generate-lineup.py` |
| `assets/crowd.svg` | `node tools/generate-crowd.mjs` (Node, no dependencies; a fixed random seed gives the same crowd every run) |
| `assets/treehouse.svg` | `python3 tools/generate-treehouse.py` (needs shapely) |
| `assets/duo.svg` | `python3 tools/generate-duo.py` |
| `assets/reader.svg` | `python3 tools/generate-reader.py` |

The generators of the seven animated drawings (all of the above except the logo and the
hero letters) write all three of their motion files in one run: `x.svg`, `x-base.svg` and
`x-motion.svg`. Regenerate all three together, never one by hand.

The Python generators need Python 3 with shapely installed (`pip install shapely`).
Of those, `generate-hero-letters.py` and `generate-treehouse.py` import shapely; the others
use just the standard library.

To rebuild all of the art:

```sh
node tools/build.mjs
```

It runs every generator (the hero letters first), then bakes every `assets/*.svg` in place.
It first checks that python3 can import shapely and stops with a message if not, before
anything is rewritten; for a shapely installed elsewhere, run
`PYTHONPATH=/path/to/site-packages node tools/build.mjs`.

To rebuild one drawing, run its generator, then bake the files it wrote:

```sh
node tools/generate-crowd.mjs
node tools/bake.mjs --in-place assets/crowd.svg assets/crowd-base.svg assets/crowd-motion.svg
```

A generator's output is not finished until it is baked. Never edit a baked SVG by hand:
change the generator and rebuild. Baking is deterministic and safe to repeat (a baked file
passes through unchanged), so `node tools/bake.mjs --in-place assets/*.svg` is always safe.

### The bake

- **Ink.** Every shape under the ink filter has its points moved by the same noise the
  filter used: the SVG specification's seeded turbulence, read from the filter's own
  settings (base frequency 0.035, 2 octaves, seed 7, scale 2.6, so at most about ±1.3
  units). The noise is read in each shape's own coordinates, ignoring parent transforms, so
  a shape written with the same path data in `x.svg`, `x-base.svg` and `x-motion.svg`
  wobbles the same in all three. Long segments are split where the noise bends them, so
  straight edges wobble too. Arcs become curves. Circles, ellipses and rects become paths,
  except dots and rivets, which only move. Lines, polylines and polygons become paths.
  Shapes in `<clipPath>` and `<mask>` are baked too, so clip edges stay on the art.
- **Halo.** A halo group first paints a white copy of its content (every fill and stroke
  white, strokes widened by the filter's radius), baked the same way, then the content.
  Copies hidden under the art or over white paper are dropped. A group whose filter draws
  only the halo keeps just the copy, plus the clip paths and masks it refers to.
- **Kept as they are:** patterns (the halftone and hatch tiles), `<style>`, classes, ids,
  transforms and element order. Outlines drawn more than once are written once in `<defs>`
  and reused with `<use>` (ids `bk1`, `bk2`…). Unused filters are removed and any other
  filter is reported and kept.

## Loading screen

With JavaScript, the page opens on a loading screen. Nib, the ink drop of the cast, bounces
on a hand-inked line: his halftone shadow shrinks as he rises, and ink drops flick off at
every landing. Under him are the wordmark, "Inking the pages…" and a hand-drawn ink bar
with a percentage. Behind the screen the page gets everything ready. Then Nib makes one last
big hop, and the sheet lifts away, its inked edge sliding up off the top.

- **What it waits for**, in order: the web fonts; the first screen's images (logo, hero
  letters, hero cast); then every drawing, nearest first. With motion on, that means its
  motion layer: base decoded, motion file parsed and inlined, parked. At the reveal, every
  drawing near the screen starts, and those in view all at once (see
  [When the drawings move](#when-the-drawings-move)).
  The still is skipped, as the base replaces it unseen. With motion off, it means the still.
  The bar shows the share of these steps done, and each heavy step gets a task of its own,
  so the bar keeps moving.
- **Timing.** The screen stays at least 1 s from the start of navigation, so it never just
  flashes, and at most 10 s. After that the page shows anyway, and the calm-time preparation
  finishes the rest (see [Performance](#performance)). Should `motion.js` never run, the
  inline script in `<head>` takes the screen down after 12 s.
- **While it shows,** scrolling is locked, the page behind is `inert` and
  `aria-busy="true"`, and the screen is a `role="status"` reading "Loading Storyfolk" (the
  percentage is hidden from screen readers). All of it is undone at the reveal. After a
  reload mid-page, the page is revealed where it was.
- **Motion.** Every animation on the screen moves only `transform` and `opacity`, of HTML
  elements or of whole `<svg>` elements (never of shapes inside one), so the compositor
  keeps it smooth while the main thread prepares the page. With motion off (reduced motion,
  or the toggle saved off), Nib stands still and the screen fades out in 0.28 s.
- **Without JavaScript** there is no loading screen: the page shows at once, with its
  stills, as before.

The markup is at the top of `<body>` (`.loader`), the styles are section 10 of `styles.css`
and the logic is the last section of `motion.js`. This Nib is a compact inline SVG (2 KB)
drawn for the screen after the Nib of the hero (`nib()` in `tools/generate-hero-cast.py`):
the same teardrop of ink with its white highlight, pen-nib tuft with slit and breather hole,
big eyes and halftone cheeks, here with both arms up.

## Motion

The characters blink, look around, wave, sway and bob. Seven drawings are animated:
`hero-cast`, `caravan`, `lineup`, `crowd`, `treehouse`, `duo` and `reader`.

### Three files per drawing

| File | What it holds |
| --- | --- |
| `x.svg` | The complete still. Shown without JavaScript, with motion off or reduced, and until the motion layer is in, should the page show first. |
| `x-base.svg` | The still minus every moving part, with whatever a moving part reveals drawn in (the body behind a waving arm, the skin under the eyes). |
| `x-motion.svg` | Only the moving parts, on a transparent canvas of the same size, animated by its own internal `<style>`. |

At rest, `x-base.svg` plus `x-motion.svg` is exactly `x.svg`. The split is for speed: a CSS
animation inside an SVG repaints the whole SVG every frame. With the runtime ink filters this
used to drop large drawings to about 10 fps; the filters are now baked out, but repainting
a large drawing still costs, so only the small motion layer repaints.

In the crowd, every one of the 63 portraits moves. Each head bounces, nods, giggles, tilts,
looks around or does a double-take, with its hair, hat and accessories. Faces blink, squeeze
or glint, and accessories wiggle. The changes are staged across thirds of the band on a
shared 5.4 s clock, so only part of it repaints at a time.

### How the page upgrades

The HTML carries only the stills. Each animated `<img>` names its motion files in
`data-motion-base` and `data-motion` and sits in a positioned `.sf-frame` that takes its
layout box. When motion is on, `motion.js` upgrades every drawing behind the loading
screen, nearest first (see [Loading screen](#loading-screen)). Any drawing still waiting
when the screen lifts (it gives up after 10 s) is upgraded as its frame comes near the
screen, whenever the page is calm (see [Performance](#performance)). For each one it:

1. fetches `x-motion.svg` and preloads and decodes `x-base.svg`, in parallel;
2. prefixes every id in the motion file (`id`, `url(#…)`, `href` and `xlink:href`), so the
   seven inlined files cannot clash, and drops its `prefers-reduced-motion` rules, because
   the page decides that instead;
3. inlines it as live SVG (`.sf-motion`, `aria-hidden`) exactly over the image, on the
   image's box snapped to whole device pixels (the way the browser draws the image). An
   image cropped with `object-fit: cover` (the crowd) gets the matching
   `preserveAspectRatio` slice. Both are re-read on resize;
4. inserts it parked (`.sf-paused`): every animated part (marked `.sf-a`) at rest and running
   no animation, so base plus overlay is exactly the still;
5. swaps the image to `x-base.svg` in the same step, so the switch is invisible.

If anything fails, the still stays. Turning motion off just stops the animations
(`html.motion-off`): every part returns to its rest pose, which with the base is the still.

### When the drawings move

- **Parked and unparked.** An overlay away from the screen is parked: its parts rest and run
  no animation at all. (Paused instead, every animated part would keep a compositor layer of
  its own, about 800 for the seven drawings.) It unparks as soon as it comes within half a
  viewport of the screen, mid-scroll or not, and parks again only once it is a viewport and a
  half away, so a drawing near the edge doesn't churn. Unparked out of sight, its loops come
  back on their authored phases (the files desynchronise them with negative
  `animation-delay`s), so the drawing is already mid-rhythm when it appears.
- **Curtain up.** When the loading screen lifts, and when motion is turned back on, every
  drawing in view starts at once. Each gesture is shifted so that its motion begins within
  the next 0.3 s, in a quick ripple from left to right across the drawing. The parts of one
  gesture share a duration and a delay (Moss's arm, his trailing hand and his brows), so each
  such group moves as one and keeps its parts in step. Its motion begins where its keyframes
  first leave the rest pose of keyframe 0, so nothing jumps. Loops that never hold the rest
  pose (Nib's float, a flame) keep their phase: they move anyway.
- **Starting in view.** A drawing that starts while in view at any other moment (a still
  swapped on screen after the loading screen gave up, or a jump past the half-viewport
  margin in one go) is kicked the same way, except that its continuous loops hold at rest
  until their loop comes round, so that nothing jumps. The glances that restart after cursor
  tracking also hold, then rejoin their drawing in step.
- **The crowd** (`data-motion-calm` on its image) unparks only once the page is calm, and
  never kicks. Each of its 328 moving parts is a compositor layer, and every frame of a
  scroll past them would have to draw them all: about a fifth of those frames ran late. Its
  5.4 s choreography keeps only a third of the band moving at any moment, so it always runs
  on its designed phases: mid-rhythm if it starts out of sight, holding at rest until each
  loop comes round if it starts in view.

### Eyes that follow the cursor

Pupils that can look around sit in a `<g class="sf-look" data-look="R">`, where R is their
largest offset in the file's viewBox units. With a mouse or trackpad, `motion.js` moves
them towards the pointer (fully at 300 px away and beyond), in whole device pixels so the
inked pupils stay crisp, and holds the idle glances meanwhile. While the page scrolls the
eyes hold still, and they re-aim once it settles. After 2.5 s without movement, or when the
pointer leaves the window, the eyes go back to their own glances, in step with the rest of
their drawing. `.sf-look` is reserved for this: the motion files never animate it, and the
script touches nothing else.

### Accessibility

- With no saved choice, motion follows the system setting: visitors who ask for reduced
  motion see the stills, and the page follows the setting if it changes.
- The "Pause animations" / "Play animations" button under the hero's "Apply to Join" stops
  and starts all animation on the page (WCAG 2.2.2), and remembers the choice in
  `localStorage` (`sf-motion` = `on` or `off`). A saved choice wins over the system setting.
  The button appears only when the script runs.
- Drawings scrolled out of view stop moving, so they cost nothing.
- Touch screens get the idle animation but no eye tracking.
- The loading screen follows the same choice: with motion off, Nib stands still and the
  screen fades instead of lifting.

### Writing a motion file

- Prefix every class and `@keyframes` name with the drawing's prefix (`hc-`, `cv-`, `lu-`,
  `cr-`, `th-`, `du-`, `rd-`): all seven files share one page, so nothing global.
- Animate only `transform` and `opacity`, and start and end every keyframe sequence at the
  rest pose, so `animation: none` gives back the still.
- An element animated by CSS carries no `transform` attribute; pivot with a
  `translate(px py)` wrapper and `transform-origin: 0 0`.
- Ids can be anything; the page prefixes them.
- Give the parts of one gesture the same duration and delay: the page starts them together
  (see [When the drawings move](#when-the-drawings-move)). A gesture holds the rest pose of
  keyframe 0 before it moves, or after; a loop that never holds it counts as continuous.
- Write every shape the still also draws with the same element and attribute values, in the
  same local coordinates, under the same ink and halo filters. The bake moves identical path
  data identically, which keeps base plus motion at rest equal to the still.
- Draw with the filters and let the bake remove them; a generator never moves points itself.

## Performance

Most of the page's weight and work is in the drawings: eight large SVG stills and seven
motion layers that repaint while they animate. With JavaScript, the page does all of its
one-off work up front, behind the loading screen, so that once it shows there is nothing
left to load, parse or insert while the visitor scrolls. From then on it keeps the cost of
each frame to what is on screen.

- **Up front, behind the loading screen.** Once the fonts and the first screen are in,
  `motion.js` asks for every motion file at once, nearest drawing first, so the network
  stays busy while the main thread parses and inlines them one by one. Nobody can see or
  scroll the page meanwhile, so these steps skip the calm-time waiting below, but each still
  gets a task of its own, which keeps the bar moving (see [Loading screen](#loading-screen)).
- **Lazy loading in the HTML.** Only the first screen loads eagerly: the logo, the hero
  letters (`fetchpriority="high"`; they are the largest paint) and the hero cast. Every
  drawing below has `loading="lazy"` and `decoding="async"`, and every `<img>` keeps its
  `width` and `height`, so nothing shifts as they arrive. This is the page a visitor without
  JavaScript gets.
- **Nothing heavy while scrolling.** Should the loading screen lift before everything is
  ready (its 10 s maximum), or motion be switched on later, each remaining one-off step of a
  drawing (loading its still, loading its base and motion file, parsing the motion file,
  inserting it) waits until the page is calm: no scroll for 200 ms, and the browser idle
  (`requestIdleCallback`; just after a frame in Safari). The steps take turns, one per
  frame. The still shows until the swap, so waiting costs nothing visible.
- **Looking ahead.** In that case, whenever the page is calm, `motion.js` prepares the
  nearest drawings first: the still of every drawing within 3 viewports of the screen, so no
  still is decoded in the middle of a scroll, and the motion layer of every drawing within
  1.5 viewports, so the next ones already move when they arrive.
- **Offscreen parking.** An overlay more than a viewport and a half from the screen is
  parked: its parts rest and run no animation at all. (Merely pausing them would not do:
  Chrome gives every part with a transform animation, even a paused one, a compositor layer
  of its own, and with all seven overlays in, that made about 800 layers to draw in every
  scrolled frame; parked, there are about 115.) It unparks half a viewport ahead of the
  screen, even mid-scroll, so it is already moving when it appears. Parking and unparking
  restyle only its animated elements (`.sf-a`, marked by the script), not the thousands of
  shapes around them.
- **Cheap frames.** Each overlay is its own compositor layer with `contain: strict`. The
  script never reads layout after writing it: it reads every animation's timing before
  changing any, reads every overlay's box before refitting any, and keeps each eye's rest
  centre in its overlay's own units, so scrolling and resizing need no re-measuring. Its
  scroll, resize and pointer listeners are all passive. Eye tracking does nothing unless eyes
  are on screen and the pointer moved in the last 2.5 s, and holds still during a scroll.
- **Filters baked into the art.** The ink wobble and the white halos used to be SVG filters,
  and filters were the main cost of every repaint and every tile rastered while scrolling.
  Filters are baked into the geometry by `tools/bake.mjs`, so none runs at draw time.

Time to reveal, from the start of navigation until the screen starts to lift (normally with
every drawing ready), measured in headless Chromium (no GPU), median of 3 cold loads. The
first two columns are with the cache disabled and the files as the test server
(`http-server`) sends them, uncompressed. The last two are the same files gzipped, as static
hosts serve SVG (about a quarter of the size), on a first visit with an empty cache.

| Network | Desktop 1440x900 @2x | Phone 390x844 @3x | Desktop, gzipped | Phone, gzipped |
| --- | --- | --- | --- | --- |
| No throttling | 1.6 s | 1.4 s | 1.5 s | 1.3 s |
| Fast 4G (9 Mbps, 60 ms RTT) | 3.5 s | 3.8 s | 1.8 s | 1.8 s |
| Slow 4G (1.6 Mbps, 150 ms RTT) | 10.0 s (the maximum) | 10.0 s (the maximum) | 4.6 s | 5.0 s |
| Received by the reveal, Fast 4G | 3.0 MB | 3.5 MB | 0.6 MB | 0.7 MB |

Uncompressed, Slow 4G cannot bring in the 2.3 MB of drawings within 10 s, so the screen
lifts at its maximum with three or four of the seven drawings ready, and the calm-time
preparation brings in the rest. The byte counts include two costs that are not the page's
own: with the cache disabled each base is downloaded a second time when the image swaps to
it (about 1 MB; a normal visit takes it from memory), and the browser starts loading the
stills nearest the first screen by itself before `motion.js` runs (0.3 MB on desktop,
0.8 MB on phone). With motion off the screen waits for the stills only: it lifts at its
1 s minimum unthrottled, at about 2.1 s on Fast 4G and at 9.4 to 9.5 s on Slow 4G
(uncompressed).

This is more up front than before, by design. Before the loading screen, the page painted at
0.5 to 0.7 s and loaded lazily: 2.1 to 2.5 MB in all, with motion fetched only near where the
visitor paused. Now the visitor waits a moment longer, and every drawing's motion is loaded
even if they never scroll to it. In exchange nothing is left to do once the page shows. The
one-off work now happens behind the screen, whose own animation runs on the compositor:
334 ms of long tasks in the first 6 s on desktop (56 ms before) and 217 ms on phone (52 ms).

Since the drawings unpark half a viewport ahead, they also animate while the page scrolls,
which costs the renderer about three times the CPU during a scroll (550 ms per second rather
than 190 on desktop) and twice as much at rest near the bottom of the page. Scrolling stays
smooth: in a scroll-through of the whole page right after the reveal (20 px per frame,
median of 3 runs), no frame ran over 20 ms at either size, nor after 3 s at the hero, and
0.4% did with the mouse moving (0.7% before). Letting the crowd unpark mid-scroll too made
14% of the frames on desktop run late (a fifth of those with the crowd on screen), hence its
calm-only start. A stricter test, Chrome's own synthetic scroll gesture measured on the
compositor, drops about 5% of frames, around the moments a drawing unparks (none before).

## Originality

All characters (Pip, Juniper, Moss, Bolt, Nib, Captain Ribbit and Wren), all drawings and
all copy on this site are original work made for Storyfolk. None of them recreates,
traces or imitates an existing character, mascot or brand.
