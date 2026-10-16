# Formatters and linters

**The rule.** Every programming language in a baskingspot repo has a sanctioned formatter and a sanctioned linter. Both are wired into the repo's `just fmt`, `just lint`, and `just ci` before the first line of that language is committed. A repo with Python but no `ruff` is not finished.

A language with no industry-standard tool may opt out. Say so in the repo's `AGENTS.md`: the language, and why there is no tool. An opt-out is a decision written down, not an omission.

The rule exists for robots as much as for people. A formatter ends the argument about style and keeps diffs small. A linter catches the mistake an agent makes at the end of a long session. Both give an agent a command that says "done" or "not done" without a human reading the code.

## Sanctioned tools

| Language                  | Formatter                          | Linter or checker                   | Comes from                                                   |
| ------------------------- | ---------------------------------- | ----------------------------------- | ------------------------------------------------------------ |
| Zig                       | `zig fmt`                          | `ziglint`                           | the flake, `zig` module                                      |
| Nix                       | `nixfmt`, through `nix fmt`        | `statix`, `deadnix`                 | the flake, `base` module                                     |
| Python                    | `ruff format`                      | `ruff check`, and `ty` for types    | `uvx` when a `pyproject.toml` exists, else the flake         |
| Shell                     | `shfmt`                            | `shellcheck`                        | the flake                                                    |
| OpenTofu, Terraform (HCL) | `tofu fmt`                         | `tflint`, and `tofu validate`       | the flake                                                    |
| GitHub Actions workflows  | `oxfmt`                            | `actionlint`, `zizmor`              | the flake, `base` module                                     |
| Markdown, YAML, JSON, CSS | `oxfmt`                            | none. The voice guide governs prose | the flake                                                    |
| JavaScript, TypeScript    | `oxfmt`                            | `oxlint`                            | `bunx` or `npx` when a `package.json` exists, else the flake |
| Go                        | `gofumpt`, through `golangci-lint` | `golangci-lint`                     | `go.mod` tooling, else the flake                             |
| Rust                      | `rustfmt`                          | `clippy`                            | the repo's toolchain file, else the flake                    |
| C, C++                    | `clang-format`                     | `clang-tidy`                        | the flake                                                    |
| TOML                      | `taplo fmt`                        | `taplo check`                       | the flake                                                    |
| Dockerfile                | none                               | `hadolint`                          | the flake                                                    |
| justfile                  | `just --fmt`                       | `just --fmt --check`                | the flake                                                    |
| SVG                       | `svgo`                             | none                                | the flake                                                    |

Where a language ecosystem has a manifest, its own toolchain runs the tool and pins the version: `uvx` with a `pyproject.toml`, `bunx` or `npx` with a `package.json`. The flake carries the tool when there is no manifest. `nix fmt` handles Nix files only. Every other language runs from the repo's justfile.

Shell, `tflint`, and a few other tools are not in the `baskingspot/nix` `base` module yet. A repo that needs one adds it to its own `packages` until a module carries it.

## How to apply it

1. List the languages in the repo: `git ls-files | sed -E 's/.*\.//' | sort | uniq -c | sort -rn`.
2. For each language, find its row. Add the tools to the flake, or to the manifest.
3. Put the format step in `fmt`, and the check in `lint`. `ci` runs `lint`.
4. Pin each tool through its manifest or the flake, so a new release cannot break CI.
5. For a language with no row, propose one here, or opt out in `AGENTS.md`.

A new language in an existing repo gets its tools in the same change that adds the language.

## Changing this table

A new tool or a swap is a change to this file, with the reason. Adopting a repo or adding a language is where gaps show up. Both are a prompt to ask whether the table needs a new row.
