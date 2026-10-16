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

[doc("Check formatting, lint the workflows, and audit them with zizmor")]
[group("lint")]
lint:
    nix fmt -- --ci
    oxfmt --check README.md AGENTS.md brand/README.md docs profile templates brand/tools .github
    oxlint brand/tools
    ruff check brand/tools
    ruff format --check brand/tools
    ty check brand/tools
    actionlint
    zizmor .
    just --fmt --check

[doc("Format everything lint checks")]
[group("lint")]
fmt:
    nix fmt
    oxfmt README.md AGENTS.md brand/README.md docs profile templates brand/tools .github
    ruff format brand/tools
    just --fmt

[doc("Everything CI runs")]
[group("ci")]
ci: lint

[doc("Render each SVG under DIR to a PNG next to it, with the pinned fonts")]
[group("brand")]
brand-render DIR="brand":
    {{ brand }} fd -e svg . {{ DIR }} -x resvg --skip-system-fonts --use-fonts-dir "$BRAND_FONT_DIR" {} {.}.png

[doc("Show an SVG in the terminal, rendered with the pinned fonts. For a PNG, run chafa on it")]
[group("brand")]
brand-view FILE:
    {{ brand }} sh -c 'resvg --skip-system-fonts --use-fonts-dir "$BRAND_FONT_DIR" "$1" -c | chafa -' _ {{ FILE }}

[doc("Pin every Action to a commit SHA, leaving versions as they are. Needs GITHUB_TOKEN")]
[group("actions")]
pin:
    pinact run

# Three days of trailing age for other people's actions, so a hijacked tag has
# time to be caught. Our own org's actions skip the age rule, so a release in
# baskingspot/gh-actions reaches every repo at once.
[doc("Pin every Action to its newest release. Outside baskingspot, at least three days old. Needs GITHUB_TOKEN")]
[group("actions")]
update:
    pinact run --update --min-age 3 --exclude '^baskingspot/'
    pinact run --update --include '^baskingspot/'

[doc("Write the org assets to brand/assets: avatar, logos, favicon, badge, and social card")]
[group("brand")]
brand-org:
    {{ brand }} python3 {{ tools }} org

[doc("Write logos, a favicon, a social card, and a README for a new library into DIR, which defaults to the current directory")]
[group("brand")]
[no-cd]
new-library NAME TAGLINE DIR=".":
    {{ brand }} python3 {{ tools }} library {{ NAME }} {{ quote(TAGLINE) }} {{ quote(DIR) }}
