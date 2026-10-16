# Brand

The baskingspot mark is a cold square with one warm disc resting in its lower left corner. Cold is square and warm is round. The disc is the basking spot.

## The mark

The grid is 16 units. The tile is 16 units square. The disc has a radius of 5 and touches the floor and the wall. In a lockup the disc is one x-height tall, so it sits on the baseline like a letter, and the ascenders reach the top of the tile.

## Projects

A project mark is the unchanged tile followed by the project name, in the same lettering, at the same size, with the same gap. Nothing is assigned, so nothing runs out. Project 40 is the same drawing as project 3 with a different word.

## Palette

- ink `#16191d`, a cold blue-black.
- paper `#f4f1ec`, a warm off-white.
- heat `#d4412b`, the red of an infrared reptile lamp. It is 29 degrees of hue redder than Zig's `#f7a41d` and much darker.
- slate `#58616c`, the tile on dark backgrounds.

### Text on the web

Heat is 4.1:1 on paper and 3.9:1 on ink, under the 4.5:1 that text needs, and a page of orange links is loud. So heat is not a text color. Docs sites keep it for the logo, the selection, and the underline of a link. A link takes the text color, and turns `#b8321d` on paper or `#e8604a` on ink (both above 5:1) on hover. Body text is ink on paper, or paper on ink. Muted text, such as a contents sidebar, is slate on paper and `#a3abb5` on ink. Code surfaces are the text color mixed 7% into the page.

## Lettering

The lettering is Hanken Grotesk 600, re-cut. The ascenders of b, d, f, h, k, and l reach 1.6 x-heights. The t has a flat top, and the dots of i and j are squares. The spacing is set by hand. A rounded monoline variant exists: run the tool with `--lettering round`.

All text ships as paths, so no SVG needs a font.

## Files

`assets/` holds the org's files, written by `just brand-org`:

- `avatar.svg` and `avatar.png` (500 px) for the GitHub org avatar.
- `avatar-round.svg` and `avatar-round.png` (512 px) for circular crops, such as Discord and Slack. The tile has more paper around it, so the corners stay inside the circle.
- `logo.svg` and `logo-dark.svg`, the lockup on a transparent ground, for a README header at 48 px high.
- `favicon.svg`, which turns its tile slate in a dark tab bar.
- `mark-mono.svg`, for one-color use.
- `badge.svg`, a small lockup on its own plate for README footers.
- `social.svg` and `social.png`, the 1280 by 640 GitHub social preview.

`tools/` holds the generator. `lettering.py` builds the letters from the font. `brand.py` writes the files.

## A new library

```sh
just new-library NAME "One sentence about it." DIR
```

This writes `docs/static/logo.svg`, `logo-dark.svg`, `favicon.svg`, `social.svg`, `social.png`, and a `LICENSE` that reserves the logos, into DIR, and a `README.md` from `templates/library/`. It refuses to overwrite existing files. Fill every `TODO` in the README before you publish. Upload `social.png` as the repo's social preview.

## License

The marks are all rights reserved, and the code that draws them is MIT. See `assets/LICENSE`.
