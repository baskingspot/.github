"""Brand assets for baskingspot and for any library under it.

Run inside the devshell from the repo root, through the justfile:

    just brand-org
    just new-library NAME "Tagline." DIR

The mark is a 16-unit tile with a disc of r 5 in its lower left corner. A
project mark is the same tile followed by the project name, so nothing is
assigned and nothing runs out. Text is set from Hanken Grotesk and written
out as paths, so no SVG depends on a font.
"""

import argparse
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import lettering

INK = "#16191d"
PAPER = "#f4f1ec"
HEAT = "#d4412b"
SLATE = "#58616c"

ORG = "baskingspot"
LETTERINGS = {"hanken": lettering.HANKEN, "round": lettering.ROUND}

# Lockup grid: 10 svg units per grid unit. The tile is 160 square. The
# baseline runs along its bottom edge, the ascender along its top edge, and
# the x-height (100) along the top of the disc. The name starts 60 after it.
U = 10
GAP = 60
DESCENT = 204  # the lockup's height: room under the baseline for g, p, q, y

MARK_GRID = (
    "16-unit grid. A 16 square tile, the cold world. A disc of r 5 rests in its lower left corner, "
    "touching the floor and the wall, and its top sits 10 units up."
)


def n(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def svg(viewbox, comment, *els):
    vb = " ".join(n(v) for v in viewbox)
    inner = "\n".join("  " + e for e in els if e)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">\n  <!--! {comment} -->\n{inner}\n</svg>'


def plate(x, y, w, h, fill, r=0):
    rr = f' rx="{n(r)}"' if r else ""
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"{rr} fill="{fill}"/>'


def mark(cold, heat, s=1.0, ox=0.0, oy=0.0, knockout=False):
    """The tile and the disc at scale s, offset (ox, oy). knockout: one color,
    with the disc cut out of the tile."""
    t = 16 * s
    cx, cy, r = ox + 5 * s, oy + 11 * s, 5 * s
    if knockout:
        d = (
            f"M{n(ox)} {n(oy)}h{n(t)}v{n(t)}h{n(-t)}z"
            f"M{n(cx)} {n(cy - r)}a{n(r)} {n(r)} 0 1 0 0 {n(2 * r)}a{n(r)} {n(r)} 0 1 0 0 {n(-2 * r)}z"
        )
        return [f'<path fill="{cold}" fill-rule="evenodd" d="{d}"/>']
    return [
        f'<path fill="{cold}" d="M{n(ox)} {n(oy)}h{n(t)}v{n(t)}h{n(-t)}z"/>',
        f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{heat}"/>',
    ]


def lockup(let, text, cold, heat, ink, ox=0.0, oy=0.0):
    els = mark(cold, heat, U, ox, oy)
    d, right = let.line(text, ox + 160 + GAP, 160 + oy, 100)
    return els + [f'<path fill="{ink}" d="{d}"/>'], right


def lockup_note(let):
    if let.name == "round":
        return "Lettering: Hanken Grotesk Thin's skeleton at one constant stroke with round ends, ascenders at 1.6 x-heights, hand spacing."
    return "Lettering: Hanken Grotesk 600, re-cut: ascenders at 1.6 x-heights, a flat-topped t, square tittles, hand spacing."


def lockup_comment(let):
    return (
        "Lockup, 10 svg units per grid unit. The tile is 160 square. The baseline runs along its bottom edge, "
        "the ascender (160) along its top edge, and the x-height (100) along the top of the disc. "
        f"The name starts 60 after the tile. {lockup_note(let)}"
    )


def logo(let, name, dark):
    """The lockup on a transparent ground, for a README header: height 48."""
    cold, ink = (SLATE, PAPER) if dark else (INK, INK)
    els, right = lockup(let, name, cold, HEAT, ink)
    return svg((0, 0, math.ceil(right), DESCENT), lockup_comment(let), *els)


def favicon():
    tile, disc = mark(INK, HEAT)
    tile = tile.replace(f'fill="{INK}"', 'class="c"')
    style = f"<style>.c{{fill:{INK}}}@media (prefers-color-scheme:dark){{.c{{fill:{SLATE}}}}}</style>"
    return svg(
        (0, 0, 16, 16),
        MARK_GRID
        + " At 16 px the tile edges sit on pixels. Dark tab bars get a slate tile.",
        style,
        tile,
        disc,
    )


def avatar():
    return svg(
        (-4, -4, 24, 24),
        MARK_GRID + " Avatar: 4 units of paper around it.",
        plate(-4, -4, 24, 24, PAPER),
        *mark(INK, HEAT),
    )


def avatar_round():
    return svg(
        (-6, -6, 28, 28),
        MARK_GRID
        + " Round avatar for circular crops, such as Discord and Slack: 6 units of paper around the tile, so the corners stay inside the circle.",
        plate(-6, -6, 28, 28, PAPER),
        *mark(INK, HEAT),
    )


def mark_mono():
    return svg(
        (0, 0, 16, 16),
        MARK_GRID + " One color: the disc is cut out of the tile.",
        *mark(INK, INK, knockout=True),
    )


def badge(let):
    """The org lockup on its own ink plate, for README footers."""
    els, right = lockup(let, ORG, SLATE, HEAT, PAPER)
    w = math.ceil(right) + 80
    return svg(
        (-80, -60, w + 80, 280),
        "README footer badge. The lockup on its own ink plate, corner radius 40. Show it 20 to 28 px tall.",
        plate(-80, -60, w + 80, 280, INK, 40),
        *els,
    )


def social(let, name):
    """A 1280 by 640 card for the GitHub social preview. The lockup is centered
    on paper at no more than 1.5 times its grid size."""
    els, right = lockup(let, name, INK, HEAT, INK)
    k = min(880 / right, 1.5)
    x, y = 640 - right * k / 2, 320 - DESCENT * k / 2
    group = (
        f'<g transform="translate({n(x)} {n(y)}) scale({n(k)})">'
        + "".join(els)
        + "</g>"
    )
    return svg(
        (0, 0, 1280, 640),
        "GitHub social preview, 1280 by 640. " + lockup_comment(let),
        plate(0, 0, 1280, 640, PAPER),
        group,
    )


def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.strip() + "\n")


def squeeze(paths):
    cfg = HERE / "svgo.config.mjs"
    subprocess.run(
        ["svgo", "--config", str(cfg), "--quiet", *map(str, paths)], check=True
    )


def render(src, dst, width):
    subprocess.run(["resvg", "-w", str(width), str(src), str(dst)], check=True)


def org(let):
    out = ROOT / "brand" / "assets"
    files = {
        "avatar.svg": avatar(),
        "avatar-round.svg": avatar_round(),
        "mark-mono.svg": mark_mono(),
        "favicon.svg": favicon(),
        "logo.svg": logo(let, ORG, False),
        "logo-dark.svg": logo(let, ORG, True),
        "badge.svg": badge(let),
        "social.svg": social(let, ORG),
    }
    for name, body in files.items():
        write(out / name, body)
    squeeze(out / name for name in files)
    render(out / "avatar.svg", out / "avatar.png", 500)
    render(out / "avatar-round.svg", out / "avatar-round.png", 512)
    render(out / "social.svg", out / "social.png", 1280)
    print(f"wrote {len(files) + 3} files to {out.relative_to(ROOT)}")


NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def library(let, name, tagline, dest, force):
    if not NAME_RE.match(name):
        sys.exit(
            f"name must be lowercase letters, digits, and hyphens, and start with a letter: {name!r}"
        )
    ident = name.replace("-", "_")
    static = dest / "docs" / "static"
    files = {
        "logo.svg": logo(let, name, False),
        "logo-dark.svg": logo(let, name, True),
        "favicon.svg": favicon(),
        "social.svg": social(let, name),
    }
    readme = dest / "README.md"
    clash = [
        p
        for p in [
            *(static / f for f in files),
            static / "social.png",
            static / "LICENSE",
            readme,
        ]
        if p.exists()
    ]
    if clash and not force:
        sys.exit(
            "refusing to overwrite (use --force): " + ", ".join(str(p) for p in clash)
        )
    for fname, body in files.items():
        write(static / fname, body)
    squeeze(static / fname for fname in files)
    render(static / "social.svg", static / "social.png", 1280)
    write(
        static / "LICENSE",
        (ROOT / "templates" / "library" / "static-LICENSE").read_text(),
    )

    text = (ROOT / "templates" / "library" / "README.md").read_text()
    text = (
        text.replace("{{name}}", name)
        .replace("{{ident}}", ident)
        .replace("{{tagline}}", tagline)
    )
    write(readme, text)
    print(f"wrote {len(files) + 3} files under {dest}. Fill every TODO in README.md.")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--lettering", choices=LETTERINGS, default="hanken")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("org", help="write the org assets to brand/assets")
    lib = sub.add_parser(
        "library", help="write the logo files and a README for a new library"
    )
    lib.add_argument("name")
    lib.add_argument("tagline")
    lib.add_argument("dest", nargs="?", default=".", type=Path)
    lib.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()
    let = LETTERINGS[args.lettering]
    if args.cmd == "org":
        org(let)
    else:
        library(let, args.name, args.tagline, args.dest.resolve(), args.force)


if __name__ == "__main__":
    main()
