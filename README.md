# Storyfolk

A static one-page website for Storyfolk, a fictional independent creative collective
that makes characters and adventure stories for kids and grown-ups. It is drawn in a
black-and-white, hand-inked comic-book style: ink (`#111111`) on paper (`#ffffff`),
halftone dot shading and chunky lettering.

There is no build step and no JavaScript library. The page is plain HTML and CSS, with
one short inline script that opens and closes the phone menu and one small script,
`motion.js`, that brings the drawings to life (see [Motion](#motion)). The fonts (Outfit
and Lora) come from Google Fonts, and the page falls back to system fonts without them.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The page: header, hero, about band, universe, crowd band, together, join, footer |
| `styles.css` | All styles: design tokens, layout, the CSS halftone band, breakpoints at 1024px and 760px |
| `motion.js` | The motion layer: inlines the animated parts over the drawings, the pause toggle, eyes that follow the cursor |
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
drawings load. Drawings below the first screen load lazily (see [Performance](#performance)).

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

## Motion

The characters blink, look around, wave, sway and bob. Seven drawings are animated:
`hero-cast`, `caravan`, `lineup`, `crowd`, `treehouse`, `duo` and `reader`.

### Three files per drawing

| File | What it holds |
| --- | --- |
| `x.svg` | The complete still. Shown without JavaScript, with motion off or reduced, and while the page loads. |
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
layout box. When motion is on, `motion.js` waits for the page to load, then upgrades the
hero at once and every other drawing as its frame comes near the screen, whenever the page
is calm (see [Performance](#performance)). For each one it:

1. fetches `x-motion.svg` and preloads and decodes `x-base.svg`, in parallel;
2. prefixes every id in the motion file (`id`, `url(#…)`, `href` and `xlink:href`), so the
   seven inlined files cannot clash, and drops its `prefers-reduced-motion` rules, because
   the page decides that instead;
3. inlines it as live SVG (`.sf-motion`, `aria-hidden`) exactly over the image, on the
   image's box snapped to whole device pixels (the way the browser draws the image). An
   image cropped with `object-fit: cover` (the crowd) gets the matching
   `preserveAspectRatio` slice. Both are re-read on resize;
4. turns each loop's negative `animation-delay` into the equivalent positive one, so every
   part starts at rest and joins its loop in phase, one by one, instead of jumping;
5. swaps the image to `x-base.svg` in the same step, so the switch is invisible.

If anything fails, the still stays. Turning motion off just stops the animations
(`html.motion-off`): every part returns to its rest pose, which with the base is the still.
Turning it back on starts every part from rest again, the same way.

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
- Drawings scrolled out of view pause, so they cost nothing.
- Touch screens get the idle animation but no eye tracking.

### Writing a motion file

- Prefix every class and `@keyframes` name with the drawing's prefix (`hc-`, `cv-`, `lu-`,
  `cr-`, `th-`, `du-`, `rd-`): all seven files share one page, so nothing global.
- Animate only `transform` and `opacity`, and start and end every keyframe sequence at the
  rest pose, so `animation: none` gives back the still.
- An element animated by CSS carries no `transform` attribute; pivot with a
  `translate(px py)` wrapper and `transform-origin: 0 0`.
- Ids can be anything; the page prefixes them.
- Write every shape the still also draws with the same element and attribute values, in the
  same local coordinates, under the same ink and halo filters. The bake moves identical path
  data identically, which keeps base plus motion at rest equal to the still.
- Draw with the filters and let the bake remove them; a generator never moves points itself.

## Performance

Most of the page's weight and work is in the drawings: eight large SVG stills and seven
motion layers that repaint while they animate. The page keeps that cost to what is on screen,
and keeps every one-off cost out of scrolling.

- **Lazy loading.** Only the first screen loads eagerly: the logo, the hero letters
  (`fetchpriority="high"`; they are the largest paint) and the hero cast. Every drawing
  below has `loading="lazy"` and `decoding="async"`, and every `<img>` keeps its `width`
  and `height`, so nothing shifts as they arrive.
- **Nothing heavy while scrolling.** Each one-off step of a drawing (loading its still,
  loading its base and motion file, parsing the motion file, inserting it) waits until the
  page is calm: no scroll for 200 ms, and the browser idle (`requestIdleCallback`; just after
  a frame in Safari). The steps take turns, one per frame. The still shows until the swap, so
  waiting costs nothing visible: motion just starts a moment after the scroll stops.
- **Looking ahead.** Whenever the page is calm, `motion.js` prepares the nearest drawings
  first. It loads and decodes the still of every drawing within 3 viewports of the screen, so
  no still is decoded in the middle of a scroll, and upgrades every drawing within 1.5
  viewports, so the next ones already move when they arrive. The hero upgrades as soon as
  the page has loaded. Nothing further away is fetched, and nothing for motion while motion
  is off.
- **Offscreen pausing.** An overlay pauses as soon as it leaves the screen, and plays again
  once it is back on screen and the page is calm. Pausing restyles only its animated elements
  (`.sf-a`, marked by the script), not the thousands of shapes around them.
- **Cheap frames.** Each overlay is its own compositor layer with `contain: strict`. The
  script never reads layout after writing it: it reads every animation's timing before
  changing any, reads every overlay's box before refitting any, and keeps each eye's rest
  centre in its overlay's own units, so scrolling and resizing need no re-measuring. Its
  scroll, resize and pointer listeners are all passive. Eye tracking does nothing unless eyes
  are on screen and the pointer moved in the last 2.5 s, and holds still during a scroll.
- **Filters baked into the art.** The ink wobble and the white halos used to be SVG filters,
  and filters were the main cost of every repaint and every tile rastered while scrolling.
  Filters are baked into the geometry by `tools/bake.mjs`, so none runs at draw time.

Measured in headless Chromium (no GPU), cold load with the cache disabled, median of 3 runs,
on the page before this work (every drawing and motion layer loaded up front) and now:

| | Desktop 1440x900 @2x | Phone 390x844 @3x |
| --- | --- | --- |
| Bytes in the first 5 s | 4775 KB -> 2242 KB | 4775 KB -> 2520 KB |
| Requests in the first 5 s | 38 -> 23 | 38 -> 24 |
| Long-task time in the first 6 s | 381 ms -> 51 ms | 191 ms -> 53 ms |
| Main thread busy in the first 6 s | 1670 ms -> 739 ms | 1429 ms -> 753 ms |
| Scroll-through, frames over 20 ms | 0.4% -> 0% | 0% -> 0% |

Loading the drawings lazily first moved their one-off work into the first scroll: the page
loaded 1441 KB (desktop) and 2238 KB (phone) in its first 5 s, but 5.1% and 3.7% of the frames
of a scroll-through ran over 20 ms (5.8% and 3.7% after 3 s at the hero). Preparing drawings
ahead, and only while the page is calm, brought all four back to 0%, for the extra bytes
above. A drawing a visitor scrolls past without stopping keeps its still; motion is fetched
only near where they pause. Byte counts are uncompressed, as the test server sent them.

## Originality

All characters (Pip, Juniper, Moss, Bolt, Nib, Captain Ribbit and Wren), all drawings and
all copy on this site are original work made for Storyfolk. None of them recreates,
traces or imitates an existing character, mascot or brand.
