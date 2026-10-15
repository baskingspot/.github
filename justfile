# baskingspot/.github: the org profile, the voice guide, the brand, and the
# shared defaults. README.md says what lives here. AGENTS.md holds the
# working conventions.

# The brand recipes run in this repo's devshell, from any directory. Inside it
# already, BASKINGSPOT_BRAND_SHELL is set and the prefix is empty.
brand := if env("BASKINGSPOT_BRAND_SHELL", "") == "1" { "" } else { "nix develop " + justfile_directory() + " --command" }
tools := justfile_directory() + "/brand/tools/brand.py"

[private]
default:
    @just --list

[doc("Check formatting of the Nix, the Markdown, and this justfile")]
[group("lint")]
lint:
    nixfmt --check flake.nix
    oxfmt --check README.md AGENTS.md brand/README.md docs profile templates
    just --fmt --check

[doc("Format everything lint checks")]
[group("lint")]
fmt:
    nixfmt flake.nix
    oxfmt README.md AGENTS.md brand/README.md docs profile templates
    just --fmt

[doc("Everything CI runs")]
[group("ci")]
ci: lint

[doc("Render each SVG under DIR to a PNG next to it, with the pinned fonts")]
[group("brand")]
brand-render DIR="brand":
    fd -e svg . {{ DIR }} -x resvg --skip-system-fonts --use-fonts-dir "$BRAND_FONT_DIR" {} {.}.png

[doc("Show an SVG in the terminal, rendered with the pinned fonts. For a PNG, run chafa on it")]
[group("brand")]
brand-view FILE:
    resvg --skip-system-fonts --use-fonts-dir "$BRAND_FONT_DIR" {{ FILE }} -c | chafa -

[doc("Write the org assets to brand/assets: avatar, logos, favicon, badge, and social card")]
[group("brand")]
brand-org:
    {{ brand }} python3 {{ tools }} org

[doc("Write logos, a favicon, a social card, and a README for a new library into DIR, which defaults to the current directory")]
[group("brand")]
[no-cd]
new-library NAME TAGLINE DIR=".":
    {{ brand }} python3 {{ tools }} library {{ NAME }} {{ quote(TAGLINE) }} {{ quote(DIR) }}
