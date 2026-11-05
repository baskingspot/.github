#!/usr/bin/env python3
"""Start a new Zig library in the org, ready to hack on.

    incubate.py NAME DIR [--description TEXT] [--private] [--local] [--zig-dual]

DIR is where the project goes. It must not exist or must be empty, and its
last part must be NAME, because `zig init` names the package after the
directory. The script makes a git repo from the zig-library flake template,
adds what every org repo has (a license, a README, AGENTS.md, a justfile, CI),
runs `zig init`, checks that `just ci` passes, makes one signed commit, then
creates baskingspot/NAME, marks it `stage` = incubating, applies the org's
settings, and pushes.

`--zig-dual` starts a library that also builds on the previous Zig release:
the zig-library-dual template, a `check` recipe, and the CI lane that runs it
in the `zig-old` shell.

An incubating repo is skipped by norm and the audit. It has no logos and no
docs site, so there is nothing to design before you start. `--local` stops
before GitHub.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ORG = "baskingspot"
HOLDER = "baskingspot contributors"
TEMPLATE_FLAKE = f"github:{ORG}/nix"
TEMPLATE_SINGLE = "zig-library"
TEMPLATE_DUAL = "zig-library-dual"
NAME_RE = re.compile(r"[a-z][a-z0-9_-]*")
DEFAULT_DESCRIPTION = "An incubating Zig library."
AUDIT_DIR = Path(__file__).resolve().parent.parent / "audit"

MIT = """MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

ACTIONLINT = """# actionlint does not know the ubuntu-26.04 hosted label yet. List it here so
# the lint passes. Remove this file once the actionlint in nixpkgs knows it.
self-hosted-runner:
  labels:
    - ubuntu-26.04
"""

ZIGLINT = """.{
    .paths = .{ "build.zig", "src" },
}
"""

# A single-version repo, and the paragraph that tells it how to become a dual
# one. `--zig-dual` creates the second shape, so its paragraph states it.
ENVIRONMENT = """Zig 0.17, the current stable. The flake is the tool contract, from `baskingspot/nix`: `nix develop` provides Zig, `ziglint`, and the base tools, and nothing comes from the system PATH. The justfile is the command interface: `just test`, `just lint`, `just ci`. Run `just fmt` before you commit.

A repo that must also build on the previous release follows the dual-version pattern: import `zig."0.16"` and `zig."0.17"`, give the older one its own `zig-old` shell, hold the shims in `src/compat.zig`, run `just ci` on the default shell and `just check` on the compatibility lane, and set `minimum_zig_version` to the older one. `baskingspot/cli`, `baskingspot/json5`, and `baskingspot/toml` do that today. Write down which versions the repo supports here, in this paragraph, so there is one place to look."""

ENVIRONMENT_DUAL = """Zig 0.16 and 0.17, one behavior on both. The flake is the tool contract, from `baskingspot/nix`: `nix develop` provides Zig 0.17, the current stable, and `nix develop .#zig-old` provides Zig 0.16. Both provide `ziglint` and the base tools, and nothing comes from the system PATH. The justfile is the command interface: `just test`, `just check`, `just lint`, `just ci`. CI runs `just ci` on the default shell and `just check` on `zig-old`. `build.zig.zon` sets `minimum_zig_version` to 0.16.0, `build.zig`'s `passthruArgs` helper is the one place the two compilers disagree, and a shim that only the older version needs goes in `src/compat.zig`. Run `just fmt` before you commit."""

# The gate the compatibility lane runs. `just ci` includes it, so the default
# shell runs it too.
CHECK_RECIPE = """[doc("The per-version gate: the unit tests, on the previous Zig")]
[group("ci")]
check: test

"""

# gh-actions' ci.yml reads this file when the calling repo has one, and runs
# each entry as a job in the named devshell.
CI_CONFIG = """# The full gate runs on the default shell, the current stable Zig. The
# compatibility lane has to compile and pass the suite on the previous one.
jobs:
  - recipe: ci
  - recipe: check
    shell: zig-old
"""

# The line in `zig init`'s build.zig that changes between the two compilers.
# Zig 0.17 moved the program's arguments onto the Run step and removed
# `b.args`; the helper below covers both.
ARGS_BLOCK = """    if (b.args) |args| {
        run_cmd.addArgs(args);
    }
"""

PASSTHRU_HELPER = """
fn passthruArgs(b: *std.Build, run: *std.Build.Step.Run) void {
    if (comptime @hasDecl(std.Build.Step.Run, "addPassthruArgs")) {
        run.addPassthruArgs();
    } else if (b.args) |args| {
        run.addArgs(args);
    }
}
"""


def check_name(name: str, directory: Path) -> None:
    """Stop early on a name or directory the rest of the script cannot use."""
    if not NAME_RE.fullmatch(name):
        raise SystemExit(
            f"{name!r} is not a name: use lowercase letters, digits, - and _"
        )
    if directory.name != name:
        raise SystemExit(
            f"the last part of DIR is {directory.name!r}, but the name is {name!r}. "
            "`zig init` names the package after the directory, so they must match."
        )
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit(f"{directory} is not empty")


def render_license(year: int) -> str:
    return MIT.format(year=year, holder=HOLDER)


def render_readme(name: str, description: str) -> str:
    return f"""# {name}

{description}

This project is incubating. It is unstable, its API will change, and it is not ready to depend on.

## Work on it

`nix develop` provides the toolchain, and `just ci` runs what CI runs.

## License

MIT. See `LICENSE`.
"""


def render_agents(name: str, description: str, dual: bool = False) -> str:
    environment = ENVIRONMENT_DUAL if dual else ENVIRONMENT
    lint_rule = (
        "- Lint with `ziglint-0-16`, not `ziglint`: the wrapper points ziglint at "
        "the 0.16 standard library, so 0.17-only deprecations do not fire while "
        "0.16 is supported.\n"
        if dual
        else ""
    )
    return f"""# AGENTS.md

Working notes for AI coding agents in baskingspot/{name}.

## What this is

{description} It is incubating: unstable, with no promises about its API.

## Environment

{environment}

## Rules

{lint_rule}- Commit messages are one line, `area: summary`, and every commit is signed. Do not rewrite pushed history.
- Gate commands on their exit codes, and claim only what you ran.
- Format with `zig fmt` and lint with `ziglint`. `just fmt` and `just lint` run both.
- A dependency a user does not need is lazy. Call `b.lazyDependency`, and put every use that needs a value inside `if (dep) |d| {{ ... }}`. The first configure pass returns null, and the build runner fetches the package after it. An unwrap outside that block panics, and it reads as a broken build script. A warm `zig-pkg` hides this, so check with `rm -rf zig-pkg .zig-cache && zig build test`.
- This repo's GitHub settings come from `baskingspot/.github`, with `just settings`. Do not change them by hand.
- To graduate the project, follow the `baskingspot-new-repo` skill: logos, a real README, and the audit passing.

## Changelog

`CHANGELOG.md` is one file, Keep a Changelog format, newest first. Add a bullet
under `## [Unreleased]` in the same change that alters something a user can
notice: the public API, expected behavior, performance a benchmark row would
show, a supported backend, or the build requirements. Docs, CI, and internal
refactors do not need one unless they change how someone uses the package.

Write from the user's side: what changed, and what they must do about it. Name
the symbol, flag, or error. One line, under Added, Changed, Fixed, or Removed.

To release, run `release-prep.py VERSION` in the repo, with the script from
`baskingspot/.github`, review the diff, commit it signed, push, then
`gh workflow run release.yml -f version=X.Y.Z`. The prep moves the Unreleased
section into a dated heading, sets `.version` in `build.zig.zon`, and points the
install command at the tag. The workflow changes no files and creates no commit,
and it refuses a version the changelog does not carry. Do not tag by hand.
"""


def render_justfile(name: str, description: str, dual: bool = False) -> str:
    check = CHECK_RECIPE if dual else ""
    gate_on = "check" if dual else "test"
    # A dual repo lints against the older standard library, so an API the
    # newer Zig deprecated still passes.
    zlint = "ziglint-0-16" if dual else "ziglint"
    return f"""# {name}: {description.rstrip(".")}. `just --list` shows the recipes.
# AGENTS.md holds the working conventions.

[private]
default:
    @just --list

[doc("Unit tests")]
[group("test")]
test:
    zig build test --summary all

[doc("Lint Zig, Nix, Markdown, the workflows, and this justfile: ziglint, zig fmt, nix fmt, oxfmt, actionlint, zizmor, and just --fmt")]
[group("lint")]
lint:
    {zlint}
    zig fmt --check src build.zig
    nix fmt -- --ci
    oxfmt --check README.md AGENTS.md .github
    actionlint
    zizmor .
    just --fmt --check

[doc("Format everything lint checks")]
[group("lint")]
fmt:
    zig fmt src build.zig
    nix fmt
    oxfmt README.md AGENTS.md .github
    just --fmt

{check}[doc("Everything CI runs")]
[group("ci")]
ci: {gate_on} lint
"""


def render_ci_config() -> str:
    """The lanes for a repo that supports two Zig versions."""
    return CI_CONFIG


def render_ci(sha: str, tag: str) -> str:
    return f"""name: ci

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions: {{}}

jobs:
  ci:
    permissions:
      contents: read
    uses: baskingspot/gh-actions/.github/workflows/ci.yml@{sha} # {tag}
    secrets:
      CACHIX_AUTH_TOKEN: ${{{{ secrets.CACHIX_AUTH_TOKEN }}}}
"""


def render_changelog(name: str) -> str:
    return f"""# Changelog

All notable changes to {name} are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
"""


def render_release(sha: str, tag: str) -> str:
    return f"""name: release

on:
  workflow_dispatch:
    inputs:
      version:
        description: The version without the leading v, such as 0.1.0
        required: true

permissions: {{}}

jobs:
  release:
    permissions:
      contents: write
    uses: baskingspot/gh-actions/.github/workflows/release-library.yml@{sha} # {tag}
    with:
      version: ${{{{ inputs.version }}}}
"""


def render_zizmor(sha: str, tag: str) -> str:
    return f"""name: zizmor

on:
  push:
    branches: [main]
  pull_request:

permissions: {{}}

jobs:
  zizmor:
    permissions:
      security-events: write
      contents: read
      actions: read
    uses: baskingspot/gh-actions/.github/workflows/zizmor.yml@{sha} # {tag}
"""


def run(*args: str, cwd: Path | None = None, stdin: str | None = None) -> str:
    result = subprocess.run(
        args, cwd=cwd, input=stdin, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-12:]
        raise SystemExit(f"`{' '.join(args)}` failed:\n" + "\n".join(tail))
    return result.stdout


def step(text: str) -> None:
    print(f"==> {text}", flush=True)


def latest_release() -> tuple[str, str]:
    tag = json.loads(run("gh", "api", f"repos/{ORG}/gh-actions/releases/latest"))[
        "tag_name"
    ]
    sha = run(
        "gh", "api", f"repos/{ORG}/gh-actions/commits/{tag}", "--jq", ".sha"
    ).strip()
    return tag, sha


def write(directory: Path, rel: str, text: str) -> None:
    path = directory / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_once(path: Path, old: str, new: str) -> None:
    """Swap the one text Zig writes, and stop if Zig's output changed shape."""
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(
            f"{path} does not carry the text this script patches. Zig changed its "
            f"output, or the tree was edited by hand:\n{old}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


def template_ref(dual: bool, override: str | None) -> str:
    """The flake ref the new repo starts from."""
    if override:
        return override
    return f"{TEMPLATE_FLAKE}#{TEMPLATE_DUAL if dual else TEMPLATE_SINGLE}"


def patch_zig_init(directory: Path, dual: bool) -> None:
    """Fix what `zig init` writes that a baskingspot repo does not ship."""
    # ziglint Z034: a print with no placeholders is a writeAll.
    replace_once(
        directory / "src" / "root.zig",
        'try writer.print("Run `zig build test` to run the tests.\\n", .{});',
        'try writer.writeAll("Run `zig build test` to run the tests.\\n");',
    )
    if not dual:
        return
    build_zig = directory / "build.zig"
    replace_once(build_zig, ARGS_BLOCK, "    passthruArgs(b, run_cmd);\n")
    with build_zig.open("a", encoding="utf-8") as f:
        f.write(PASSTHRU_HELPER)


def scaffold(
    name: str,
    directory: Path,
    description: str,
    tag: str,
    sha: str,
    template: str,
    dual: bool,
) -> None:
    """Everything up to the first commit. No GitHub."""
    step(f"making {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    run("git", "init", "-q", "-b", "main", ".", cwd=directory)
    run("nix", "flake", "init", "-t", template, cwd=directory)
    write(directory, "LICENSE", render_license(datetime.now(timezone.utc).year))
    write(directory, "README.md", render_readme(name, description))
    write(directory, "AGENTS.md", render_agents(name, description, dual))
    write(directory, "CHANGELOG.md", render_changelog(name))
    write(directory, "justfile", render_justfile(name, description, dual))
    write(directory, ".ziglint.zon", ZIGLINT)
    write(directory, ".github/actionlint.yaml", ACTIONLINT)
    write(directory, ".github/workflows/ci.yml", render_ci(sha, tag))
    write(directory, ".github/workflows/zizmor.yml", render_zizmor(sha, tag))
    write(directory, ".github/workflows/release.yml", render_release(sha, tag))
    if dual:
        write(directory, ".github/ci.yaml", render_ci_config())
    # Nix reads only tracked files, and the global git ignore hides .envrc.
    run("git", "add", "-N", ".", cwd=directory)
    run("git", "add", "-f", "-N", ".envrc", cwd=directory)
    step("zig init")
    # The dual template's older compiler writes the build.zig that both
    # compilers can run, once passthruArgs is in it.
    old_shell = [".#zig-old"] if dual else []
    run("nix", "develop", *old_shell, "--command", "zig", "init", cwd=directory)
    patch_zig_init(directory, dual)
    run("git", "add", "-N", ".", cwd=directory)
    step("just fmt, then just ci")
    run("nix", "develop", "--command", "just", "fmt", cwd=directory)
    run("nix", "develop", "--command", "just", "ci", cwd=directory)
    if dual:
        # The same gate on the older compiler, so the first commit is proven
        # on both versions and not just on the default one.
        step("just check on the older Zig")
        run("nix", "develop", ".#zig-old", "--command", "just", "check", cwd=directory)


def publish(name: str, directory: Path, description: str, private: bool) -> None:
    step("committing")
    run("git", "add", "-A", cwd=directory)
    run("git", "commit", "-q", "-m", "repo: a Zig library to hack on", cwd=directory)
    if "gpgsig" not in run("git", "cat-file", "commit", "HEAD", cwd=directory):
        raise SystemExit(
            "the first commit is not signed. Fix git's signing setup and retry."
        )
    step(f"creating {ORG}/{name}")
    visibility = "--private" if private else "--public"
    run(
        "gh", "repo", "create", f"{ORG}/{name}", visibility,
        "--description", description, "--source", str(directory), "--remote", "origin",
    )  # fmt: skip
    run(
        "gh", "repo", "edit", f"{ORG}/{name}",
        "--add-topic", "zig", "--add-topic", "zig-lang", "--add-topic", "zig-package",
    )  # fmt: skip
    step("stage = incubating")
    run(
        "gh", "api", "-X", "PATCH", f"repos/{ORG}/{name}/properties/values",
        "-f", "properties[][property_name]=stage", "-f", "properties[][value]=incubating",
    )  # fmt: skip
    step("applying the org's settings")
    run(sys.executable, str(AUDIT_DIR / "repo_settings.py"), "--repo", name, "--apply")
    step("pushing")
    run("git", "push", "-u", "origin", "main", cwd=directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name")
    parser.add_argument("directory", type=Path, help="where the project goes")
    parser.add_argument("--description", default=DEFAULT_DESCRIPTION)
    parser.add_argument("--private", action="store_true", help="a private repo")
    parser.add_argument("--local", action="store_true", help="stop before GitHub")
    parser.add_argument(
        "--zig-dual",
        action="store_true",
        help="the library also builds on the previous Zig: start from the "
        "zig-library-dual template, with its `check` recipe and zig-old CI lane",
    )
    parser.add_argument(
        "--template",
        help="the flake ref to start from. Defaults to "
        f"{TEMPLATE_FLAKE}#{TEMPLATE_SINGLE}, or #{TEMPLATE_DUAL} with "
        "--zig-dual. Override it to try a template that is not merged yet",
    )
    args = parser.parse_args()
    directory = args.directory.expanduser().resolve()
    check_name(args.name, directory)
    description = args.description.strip()
    if not description.endswith("."):
        raise SystemExit("the description is one sentence and ends with a period")
    tag, sha = latest_release()
    template = template_ref(args.zig_dual, args.template)
    scaffold(args.name, directory, description, tag, sha, template, args.zig_dual)
    if args.local:
        step(f"done, locally. {directory} has no commit and no remote.")
        return 0
    publish(args.name, directory, description, args.private)
    print(f"\nhttps://github.com/{ORG}/{args.name}\n{directory}")
    print(
        "Next: `cd` in, `direnv allow`, and hack. It is incubating, so norm and the audit skip it."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
