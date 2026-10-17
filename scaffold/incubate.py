#!/usr/bin/env python3
"""Start a new Zig library in the org, ready to hack on.

    incubate.py NAME DIR [--description TEXT] [--private] [--local]

DIR is where the project goes. It must not exist or must be empty, and its
last part must be NAME, because `zig init` names the package after the
directory. The script makes a git repo from the zig-library flake template,
adds what every org repo has (a license, a README, AGENTS.md, a justfile, CI),
runs `zig init`, checks that `just ci` passes, makes one signed commit, then
creates baskingspot/NAME, marks it `stage` = incubating, applies the org's
settings, and pushes.

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


def render_agents(name: str, description: str) -> str:
    return f"""# AGENTS.md

Working notes for AI coding agents in baskingspot/{name}.

## What this is

{description} It is incubating: unstable, with no promises about its API.

## Environment

Zig 0.16 only. The flake is the tool contract, from `baskingspot/nix`: `nix develop` provides Zig, `ziglint`, and the base tools, and nothing comes from the system PATH. The justfile is the command interface: `just test`, `just lint`, `just ci`. Run `just fmt` before you commit.

## Rules

- Commit messages are one line, `area: summary`, and every commit is signed. Do not rewrite pushed history.
- Gate commands on their exit codes, and claim only what you ran.
- Format with `zig fmt` and lint with `ziglint`. `just fmt` and `just lint` run both.
- This repo's GitHub settings come from `baskingspot/.github`, with `just settings`. Do not change them by hand.
- To graduate the project, follow the `baskingspot-new-repo` skill: logos, a real README, and the audit passing.
"""


def render_justfile(name: str, description: str) -> str:
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
    ziglint
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

[doc("Everything CI runs")]
[group("ci")]
ci: test lint
"""


def render_ci(sha: str, tag: str) -> str:
    return f"""name: ci

on:
  push:
    branches: [main]
  pull_request:

permissions: {{}}

jobs:
  ci:
    permissions:
      contents: read
    uses: baskingspot/gh-actions/.github/workflows/ci.yml@{sha} # {tag}
    secrets:
      CACHIX_AUTH_TOKEN: ${{{{ secrets.CACHIX_AUTH_TOKEN }}}}
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


def scaffold(name: str, directory: Path, description: str, tag: str, sha: str) -> None:
    """Everything up to the first commit. No GitHub."""
    step(f"making {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    run("git", "init", "-q", "-b", "main", ".", cwd=directory)
    run("nix", "flake", "init", "-t", f"github:{ORG}/nix#zig-library", cwd=directory)
    write(directory, "LICENSE", render_license(datetime.now(timezone.utc).year))
    write(directory, "README.md", render_readme(name, description))
    write(directory, "AGENTS.md", render_agents(name, description))
    write(directory, "justfile", render_justfile(name, description))
    write(directory, ".ziglint.zon", ZIGLINT)
    write(directory, ".github/actionlint.yaml", ACTIONLINT)
    write(directory, ".github/workflows/ci.yml", render_ci(sha, tag))
    write(directory, ".github/workflows/zizmor.yml", render_zizmor(sha, tag))
    # Nix reads only tracked files, and the global git ignore hides .envrc.
    run("git", "add", "-N", ".", cwd=directory)
    run("git", "add", "-f", "-N", ".envrc", cwd=directory)
    step("zig init")
    run("nix", "develop", "--command", "zig", "init", cwd=directory)
    run("git", "add", "-N", ".", cwd=directory)
    step("just fmt, then just ci")
    run("nix", "develop", "--command", "just", "fmt", cwd=directory)
    run("nix", "develop", "--command", "just", "ci", cwd=directory)


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
    run("gh", "repo", "edit", f"{ORG}/{name}", "--add-topic", "zig")
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
    args = parser.parse_args()
    directory = args.directory.expanduser().resolve()
    check_name(args.name, directory)
    description = args.description.strip()
    if not description.endswith("."):
        raise SystemExit("the description is one sentence and ends with a period")
    tag, sha = latest_release()
    scaffold(args.name, directory, description, tag, sha)
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
