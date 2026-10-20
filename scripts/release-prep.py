#!/usr/bin/env python3
"""Prepare a library release in the current repository.

Moves the `[Unreleased]` section of CHANGELOG.md into `## [VERSION] - DATE`,
sets that version in build.zig.zon, and points the install command in the
README and the guide at `https://baskingspot.dev/NAME/vX.Y.Z`. It changes files and nothing
else: review them, commit with your own signature, push, then dispatch the
repository's release workflow with the same version.

    python3 release-prep.py 0.2.0
    git diff
    git commit -am "release: v0.2.0"
    git push
    gh workflow run release.yml -f version=0.2.0
"""

from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(f"{' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def github_repo() -> str:
    url = run("git", "remote", "get-url", "origin").strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if match is None:
        sys.exit(f"cannot read owner/repo from {url}")
    return match.group(1)


def stamp_changelog(version: str) -> None:
    path = Path("CHANGELOG.md")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## \[Unreleased\][^\n]*\n", text, re.MULTILINE)
    if match is None:
        sys.exit("CHANGELOG.md has no `## [Unreleased]` heading")
    before, rest = text[: match.start()], text[match.end() :]
    following = re.search(r"^## \[", rest, re.MULTILINE)
    body = rest[: following.start()] if following else rest
    tail = rest[following.start() :] if following else ""
    if not body.strip():
        sys.exit("the Unreleased section is empty; write the notes first")
    date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    stamped = f"{before}## [Unreleased]\n\n## [{version}] - {date}\n\n{body.strip()}\n"
    if tail:
        stamped += "\n" + tail
    path.write_text(stamped, encoding="utf-8")
    print(f"{path}: the Unreleased section is now [{version}]")


def set_manifest_version(version: str) -> None:
    path = Path("build.zig.zon")
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'^(\s*)\.version = "[^"]*"',
        rf'\1.version = "{version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        sys.exit("build.zig.zon has no .version field")
    path.write_text(updated, encoding="utf-8")
    print(f"{path}: .version = {version}")


def point_install_at_tag(version: str) -> None:
    repo = github_repo()
    archive = f"https://github.com/{repo}/archive/refs/tags/v{version}.tar.gz"
    url = re.compile(
        rf"(?:git\+)?https://github\.com/{re.escape(repo)}(?:[#/][^\s`\"']*)?"
    )
    for name in ("README.md", "docs/content/_index.md"):
        path = Path(name)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        lines = []
        changed = False
        for line in text.splitlines(keepends=True):
            if "zig fetch --save" in line:
                new = url.sub(archive, line)
                if new != line:
                    changed = True
                    line = new
            lines.append(line)
        if changed:
            path.write_text("".join(lines), encoding="utf-8")
            print(f"{path}: install names v{version}")


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("usage: release-prep.py VERSION, such as 0.2.0")
    version = sys.argv[1]
    if Path(".git").exists() and run("git", "tag", "-l", f"v{version}").strip():
        sys.exit(f"tag v{version} already exists")
    stamp_changelog(version)
    set_manifest_version(version)
    point_install_at_tag(version)
    print("review the diff, commit it, push, then dispatch release.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
