# Formatters and linters

**The rule.** Every language that carries load-bearing code in a baskingspot repo has a sanctioned formatter and a sanctioned linter. Both are wired into the repo's `just fmt`, `just lint`, and `just ci` before the load-bearing code lands. A repo with a Python service but no `ruff` is not finished.

**Load-bearing** code is code that ships, or that other code and CI depend on to be right: a library, a service, a Lambda, an infrastructure module, build and release tooling. It is also code that someone will maintain for a year.

**Not load-bearing:** a one-off script, an analysis notebook, a comparison or test driver for a competitor library, a fixture generator, generated code, and vendored code. This code may be rough. It needs no linter, and it does not need a line in `AGENTS.md`. If a directory of it would confuse an agent, name the directory in `AGENTS.md` in one line, for example "`bench/drivers/` is throwaway comparison code".

**Always checked, whatever the load:** shell scripts and Dockerfiles. A direnv `.envrc` is configuration, not a script, so it is exempt. They are cheap to check and easy to get wrong, so they get `shellcheck`, `shfmt`, and `hadolint` every time.

When unsure whether code is load-bearing, lint it. If the tool costs more than the code is worth, skip it and say so in one line.

The rule exists for robots as much as for people. A formatter ends the argument about style and keeps diffs small. A linter catches the mistake an agent makes at the end of a long session. Both give an agent a command that says "done" or "not done" without a human reading the code.

## Sanctioned tools

| Language                        | Formatter                          | Linter or checker                   | Comes from                                                   |
| ------------------------------- | ---------------------------------- | ----------------------------------- | ------------------------------------------------------------ |
| Zig                             | `zig fmt`                          | `ziglint`                           | the flake, `zig` module                                      |
| Nix                             | `nixfmt`, through `nix fmt`        | `statix`, `deadnix`                 | the flake, `base` module                                     |
| Python                          | `ruff format`                      | `ruff check`, and `ty` for types    | `uvx` when a `pyproject.toml` exists, else the flake         |
| Shell                           | `shfmt`                            | `shellcheck`, always                | the flake, `shell` module                                    |
| OpenTofu, Terraform (HCL)       | `tofu fmt`                         | `tflint`, and `tofu validate`       | the flake, `terraform` module                                |
| GitHub Actions workflows        | `oxfmt`                            | `actionlint`, `zizmor`              | the flake, `base` module                                     |
| Markdown, YAML, JSON, TOML, CSS | `oxfmt`                            | none. The voice guide governs prose | the flake                                                    |
| JavaScript, TypeScript          | `oxfmt`                            | `oxlint`                            | `bunx` or `npx` when a `package.json` exists, else the flake |
| Go                              | `gofumpt`, through `golangci-lint` | `golangci-lint`                     | `go.mod` tooling, else the flake                             |
| Rust                            | `rustfmt`                          | `clippy`                            | the repo's toolchain file, else the flake                    |
| C, C++                          | `clang-format`                     | `clang-tidy`                        | the flake                                                    |
| Dockerfile                      | none                               | `hadolint`, always                  | the flake                                                    |
| justfile                        | `just --fmt`                       | `just --fmt --check`                | the flake                                                    |
| SVG                             | `svgo`                             | none                                | the flake                                                    |

Where a language ecosystem has a manifest, its own toolchain runs the tool and pins the version: `uvx` with a `pyproject.toml`, `bunx` or `npx` with a `package.json`. The flake carries the tool when there is no manifest. `nix fmt` handles Nix files only. Every other language runs from the repo's justfile.

Each language has its own module in `baskingspot/nix`: `zig`, `terraform`, and `shell` so far. A repo imports the modules for the languages it has, and composes their shells with `inputsFrom`. Where no module exists yet, a repo adds the tool to its own `packages`, and a module is the next piece to write.

## How to apply it

1. List the languages in the repo: `git ls-files | sed -E 's/.*\.//' | sort | uniq -c | sort -rn`. Mark which hold load-bearing code, and always include shell and Dockerfiles.
2. For each of those languages, find its row. Add the tools to the flake, or to the manifest.
3. Put the format step in `fmt`, and the check in `lint`. `ci` runs `lint`.
4. Pin each tool through its manifest or the flake, so a new release cannot break CI.
5. For a load-bearing language with no row, propose one here, or opt out in `AGENTS.md`.

A new load-bearing language in an existing repo gets its tools in the same change that adds the language.

## Changing this table

A new tool or a swap is a change to this file, with the reason. Adopting a repo or adding a language is where gaps show up. Both are a prompt to ask whether the table needs a new row.
