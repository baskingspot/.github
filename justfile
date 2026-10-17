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
    ruff check brand/tools audit scaffold
    ruff format --check brand/tools audit scaffold
    ty check brand/tools audit scaffold
    actionlint
    zizmor .
    just --fmt --check

[doc("Format everything lint checks")]
[group("lint")]
fmt:
    nix fmt
    oxfmt README.md AGENTS.md brand/README.md docs profile templates brand/tools .github
    ruff format brand/tools audit scaffold
    just --fmt

[doc("Run the tests for the audit and the settings tool, which need no network")]
[group("test")]
test:
    cd audit && python3 -m unittest -v test_repo_settings test_audit
    cd scaffold && python3 -m unittest -v test_incubate

[doc("Everything CI runs")]
[group("ci")]
ci: test lint

[doc("Start a new Zig library: a repo in DIR from the zig-library template with a license, README, AGENTS.md, justfile, and CI, created as baskingspot/NAME, marked incubating, with the org's settings applied. DIR is required and must end in NAME. DESCRIPTION is one sentence ending in a period. Add --private, or --local to stop before GitHub")]
[group("new")]
[no-cd]
incubate NAME DIR DESCRIPTION="An incubating Zig library." *FLAGS:
    {{ brand }} python3 {{ justfile_directory() }}/scaffold/incubate.py {{ NAME }} {{ quote(DIR) }} --description {{ quote(DESCRIPTION) }} {{ FLAGS }}

[doc("Check the org's settings and every repo's against audit/settings.json, the one list of them. Add --apply to change what differs, --org for the org alone, or --repo NAME for one repo. Needs gh and a token that administers the org. Exit 1 on drift")]
[group("audit")]
[no-cd]
settings *ARGS:
    {{ brand }} python3 {{ justfile_directory() }}/audit/repo_settings.py {{ ARGS }}

[doc("Audit every public repo in the org for conformance: metadata, files, justfile and workflow style, README hygiene, the brand marks, site registration, and files that repeat. Pass a repo name to audit one. Needs gh. Exit 1 on any error")]
[group("audit")]
[no-cd]
audit REPO="":
    {{ brand }} python3 {{ justfile_directory() }}/audit/audit.py {{ if REPO == "" { "" } else { "--repo " + REPO } }}

[doc("Report where CI time goes: each repo's jobs, their slowest steps, and the critical path of its latest successful run on main. Pass a repo name for one. Needs gh")]
[group("audit")]
[no-cd]
ci-report REPO="":
    {{ brand }} python3 {{ justfile_directory() }}/audit/ci_report.py {{ REPO }}

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
