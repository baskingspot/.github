#!/usr/bin/env python3
"""Align the org's Zig dependencies across the checkouts in one directory.

Every repo that depends on `baskingspot/stdx` or `baskingspot/testingx` pins a
commit and a content hash in a `build.zig.zon`. Two different commits in one
build graph are two copies of the package, so all of them must name the same
commit. This updates every `build.zig.zon` under --root to one commit per
dependency, using `zig fetch --save` so Zig writes the hash.

By default a dependency resolves to its newest `vX.Y.Z` release tag, or to the
default branch when it has no releases. --ref forces one ref for every
dependency, which is how a core release pins its dependents to the new tag.

    python3 update-deps.py --dry-run
    python3 update-deps.py --dep testingx
    python3 update-deps.py --ref v0.2.0 --commit --push
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ORG = "baskingspot"
SKIP = ("zig-pkg", "zig-out", ".zig-cache", ".git", "node_modules")
TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(f"{' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def git_top(path: Path) -> Path:
    return Path(run("git", "-C", str(path), "rev-parse", "--show-toplevel").strip())


def dirty(repo: Path) -> bool:
    return bool(run("git", "-C", str(repo), "status", "--porcelain").strip())


def remotes(dep: str) -> dict[str, str]:
    """ref name => commit for the dependency's tags and HEAD, without a clone."""
    url = f"https://github.com/{ORG}/{dep}.git"
    refs: dict[str, str] = {}
    for line in run("git", "ls-remote", url).splitlines():
        sha, ref = line.split("\t", 1)
        refs[ref] = sha
    return refs


def newest_tag(refs: dict[str, str]) -> tuple[str, str] | None:
    best: tuple[tuple[int, int, int], str, str] | None = None
    for ref, sha in refs.items():
        if not ref.startswith("refs/tags/"):
            continue
        name = ref.removeprefix("refs/tags/")
        match = TAG.match(name)
        if match is None:
            continue
        version = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if best is None or version > best[0]:
            best = (version, name, sha)
    return None if best is None else (best[1], best[2])


def resolve(dep: str, wanted: str | None) -> tuple[str, str]:
    """The ref name and commit a dependency should be pinned to."""
    refs = remotes(dep)
    if wanted:
        if re.fullmatch(r"[0-9a-f]{40}", wanted):
            return wanted[:12], wanted
        for ref in (f"refs/tags/{wanted}", f"refs/heads/{wanted}"):
            if ref in refs:
                return wanted, refs[ref]
        sys.exit(f"{ORG}/{dep} has no ref named {wanted}")
    tag = newest_tag(refs)
    if tag is not None:
        return tag
    head = refs.get("HEAD")
    if head is None:
        sys.exit(f"{ORG}/{dep} has no HEAD")
    return "main", head


def zon_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("build.zig.zon"):
        if any(part in SKIP for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root", type=Path, default=Path.home() / "code" / "baskingspot"
    )
    parser.add_argument(
        "--dep", action="append", help="Limit to a dependency. Repeatable."
    )
    parser.add_argument("--ref", help="Pin every dependency to this tag or commit.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--commit", action="store_true", help="One signed commit per repo."
    )
    parser.add_argument(
        "--push", action="store_true", help="Push each commit. Implies --commit."
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        sys.exit(f"{args.root} is not a directory")
    commit = args.commit or args.push

    wanted = args.dep or []
    targets: dict[str, tuple[str, str]] = {}
    files = zon_files(args.root)
    if not files:
        sys.exit(f"no build.zig.zon under {args.root}")
    for zon in files:
        for dep in re.findall(rf"github\.com/{ORG}/([a-z0-9-]+)", zon.read_text()):
            if dep not in targets and (not wanted or dep in wanted):
                targets[dep] = resolve(dep, args.ref)
    if wanted:
        missing = sorted(set(wanted) - set(targets))
        if missing:
            sys.exit(f"no build.zig.zon depends on: {', '.join(missing)}")

    affected = {
        git_top(zon.parent)
        for zon in files
        for dep in targets
        if f"github.com/{ORG}/{dep}" in zon.read_text()
    }
    dirty_repos = {repo for repo in affected if dirty(repo)}
    if commit and dirty_repos:
        names = ", ".join(sorted(repo.name for repo in dirty_repos))
        sys.exit(f"uncommitted changes in: {names}. Commit or stash them first.")

    changed: dict[Path, list[str]] = {}
    for zon in files:
        repo = git_top(zon.parent)
        text = zon.read_text()
        for dep, (ref, sha) in sorted(targets.items()):
            if f"github.com/{ORG}/{dep}" not in text:
                continue
            url = f"git+https://github.com/{ORG}/{dep}#{sha}"
            if f"github.com/{ORG}/{dep}#{sha}" in text:
                continue
            before = text
            print(f"{zon.relative_to(args.root)}: {dep} -> {ref} ({sha[:12]})")
            if args.dry_run:
                continue
            run(
                "nix",
                "develop",
                str(repo),
                "--command",
                "zig",
                "fetch",
                "--save",
                url,
                cwd=zon.parent,
            )
            text = zon.read_text()
            if text != before:
                changed.setdefault(repo, []).append(str(zon.relative_to(repo)))

    if args.dry_run:
        return 0
    if not args.push:
        return 0
    for repo, paths in sorted(changed.items()):
        summary = ", ".join(f"{dep} {ref}" for dep, (ref, _) in sorted(targets.items()))
        run("git", "-C", str(repo), "add", *paths)
        run("git", "-C", str(repo), "commit", "-m", f"deps: align {summary}")
        run("git", "-C", str(repo), "push")
        print(f"{repo.name}: pushed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
