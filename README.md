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
| `tools/` | Scripts that regenerate some of the illustrations (see below) |

Every `<img>` carries its width and height, so the layout holds its shape while the
drawings load.

## Preview

Open `index.html` in a browser to see the still drawings, or serve the folder to see them
move (the motion layer fetches its files, which browsers do not allow from `file://`):

```sh
npx serve .
```

## How each illustration is made

Every drawing is an SVG of hand-placed path data, with ink outlines, halftone and hatch
patterns and a light turbulence filter for the hand-inked wobble. Some are written out
by a script in `tools/`, which assembles the groups, clips and repeated texture marks;
for those, edit the script and re-run it rather than editing the SVG. Run every script
from the repository root.

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

To regenerate the crowd:

```sh
node tools/generate-crowd.mjs
```

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
animation inside an SVG repaints the whole SVG every frame, and with the ink filters that
drops large drawings to about 10 fps. Keeping the static plate in an `<img>` lets only the
small motion layer repaint.

### How the page upgrades

The HTML carries only the stills. Each animated `<img>` names its motion files in
`data-motion-base` and `data-motion` and sits in a positioned `.sf-frame` that takes its
layout box. When motion is on, `motion.js` waits for the page to load, then for each one:

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
inked pupils stay crisp, and holds the idle glances meanwhile. After 2.5 s without movement, or when the pointer leaves the window, the eyes
go back to their own glances. `.sf-look` is reserved for this: the motion files never
animate it, and the script touches nothing else.

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

## Originality

All characters (Pip, Juniper, Moss, Bolt, Nib, Captain Ribbit and Wren), all drawings and
all copy on this site are original work made for Storyfolk. None of them recreates,
traces or imitates an existing character, mascot or brand.
