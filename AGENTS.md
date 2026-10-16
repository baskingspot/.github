# AGENTS.md

Working notes for AI coding agents in baskingspot/.github.

## What this is

The org's own repo. It holds the profile README, the voice guide, the LLM disclosure page, the brand work, and the defaults every org repo inherits. It is the reference implementation: what is built here gets copied into every other repo, so it has to be a pattern worth copying.

## Environment

The flake is the tool contract. `nix develop` provides every tool, and the `.envrc` loads it through direnv. Nothing comes from the system PATH. If a tool is missing, add it to the flake.

The justfile is the command interface:

```
just lint
just ci
```

`just ci` runs what the CI workflow runs. Run `just fmt` before you commit.

## Layout

- `profile/README.md` renders on the org's overview page. It names no projects yet, and it says work in progress.
- `docs/VOICE.md` is the voice guide. Read all of it before you write anything public.
- `docs/AI.md` is the disclosure page. Every statement on it must be true.
- `brand/` holds the brand: the system in `README.md`, the org's files in `assets/`, and the generator in `tools/`. Never edit an SVG in `assets/` by hand. Change the tool and run `just brand-org`.
- `audit/audit.py` checks the whole org for conformance. `just audit` runs it, and the `baskingspot-audit` skill says how to read the report. Its rules mirror the house shape, so change the rule and the script together.
- `templates/program/release-notes.md` is the template for `docs/releases/vX.Y.Z.md` in a repo that ships a program. The release workflow uses that file as the release notes and adds the install section.
- `templates/library/README.md` is the README every library starts from. `just new-library` fills it in.
- `.github/workflows/` calls the shared `ci` and `zizmor` workflows in `baskingspot/gh-actions`, pinned by commit SHA. The maintenance job in that repo keeps `flake.lock` and the pins current, so this repo has no update workflow of its own.

## Conventions

- Recipes carry a `[doc("...")]` directive and a `[group("...")]`. Do not document a recipe with a `#` comment. A recipe parameter is uppercase. `[private] default` lists the recipes.
- Commit messages are one line, `area: summary`, like `docs: LLM disclosure page`. Add a short body only when the why needs it.
- Every commit is signed. Do not rewrite pushed history.
- Pin every Action by SHA with a version comment, and pin the runner label in any workflow that sets one. `just pin` pins a new one and `just update` moves them to the newest release. Other owners' releases must be at least three days old, and our own `baskingspot/` actions are exempt. Both need `GITHUB_TOKEN`. A hand pin to another owner's release younger than three days makes `just update` exit 2 until it ages. zizmor must pass.
- Format Nix with `nix fmt`, never `nixfmt` directly.
- Public text follows the voice guide. Name no project until the repo has moved into the org.
- A claim about how the work is made belongs on `docs/AI.md`, and nowhere else.
