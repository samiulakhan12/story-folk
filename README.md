# Storyfolk

A static one-page website for Storyfolk, a fictional independent creative collective
that makes characters and adventure stories for kids and grown-ups. It is drawn in a
black-and-white, hand-inked comic-book style: ink (`#111111`) on paper (`#ffffff`),
halftone dot shading and chunky lettering.

There is no build step and no JavaScript library. The page is plain HTML and CSS, with
one short inline script that opens and closes the phone menu. The fonts (Outfit and
Lora) come from Google Fonts, and the page falls back to system fonts without them.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The page: header, hero, about band, universe, crowd band, together, join, footer |
| `styles.css` | All styles: design tokens, layout, the CSS halftone band, breakpoints at 1024px and 760px |
| `assets/logo-mark.svg` | The logo mark and favicon: a face peeking over an open book |
| `assets/hero-letters.svg` | Hero layer 1 (1600x900): the hand-lettered STORY / FOLK wordmark |
| `assets/hero-cast.svg` | Hero layer 2 (1600x900): the cast perched on the letters, stacked exactly over layer 1 |
| `assets/caravan.svg` | The snail caravan (1000x800), in the halftone band |
| `assets/lineup.svg` | Character line-up (1600x700): Juniper, Moss, Nib, Captain Ribbit and Bolt |
| `assets/crowd.svg` | Crowd of portraits (1600x1100) under the giant "staycurious" wordmark |
| `assets/treehouse.svg` | The treehouse village (1400x1000), bleeding off the left edge |
| `assets/duo.svg` | Pip and Juniper setting out (700x820), in the join section |
| `assets/reader.svg` | Wren reading on a stack of books (800x800), in the footer |
| `tools/` | Scripts that regenerate some of the illustrations (see below) |

Every `<img>` carries its width and height, so the layout holds its shape while the
drawings load.

## Preview

Open `index.html` in a browser, or serve the folder:

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

The Python generators need Python 3 with shapely installed (`pip install shapely`).
Of those, `generate-hero-letters.py` and `generate-treehouse.py` import shapely; the others
use just the standard library.

To regenerate the crowd:

```sh
node tools/generate-crowd.mjs
```

## Originality

All characters (Pip, Juniper, Moss, Bolt, Nib, Captain Ribbit and Wren), all drawings and
all copy on this site are original work made for Storyfolk. None of them recreates,
traces or imitates an existing character, mascot or brand.
