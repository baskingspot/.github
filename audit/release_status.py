#!/usr/bin/env python3
"""Report which released repos have work waiting for a tag.

Run it with `just release-status`. For each repo in the org it prints the
latest tag, how many commits are on the default branch since that tag, and
what the changelog holds in `[Unreleased]`, with a suggested next version.

The suggestion is a reading of the changelog, not a decision: an `Added`
section is a feature, so the middle number moves; `Changed`, `Removed`, or
`Deprecated` on a 0.x version also move the middle number, because every
breaking change before 1.0 is a minor bump; `Fixed` and `Security` alone are a
patch. A repo with no bullets has nothing to release.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from typing import Any

ORG = "baskingspot"
MINOR_SECTIONS = ("Added", "Changed", "Removed", "Deprecated")
PATCH_SECTIONS = ("Fixed", "Security")


def gh(path: str) -> Any | None:
    out = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        return None
    return json.loads(out.stdout)


def unreleased(repo: str) -> dict[str, int] | None:
    blob = gh(f"repos/{ORG}/{repo}/contents/CHANGELOG.md")
    if not blob or "content" not in blob:
        return None
    text = base64.b64decode(blob["content"]).decode("utf-8", "replace")
    match = re.search(r"## \[Unreleased\][^\n]*\n(.*?)(?=\n## \[|\Z)", text, re.DOTALL)
    if not match:
        return {}
    sections: dict[str, int] = {}
    current = None
    for line in match.group(1).splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            sections.setdefault(current, 0)
        elif line.startswith("- ") and current:
            sections[current] += 1
    return sections


def bump(tag: str, sections: dict[str, int]) -> str:
    if not any(sections.values()):
        return "-"
    parts = tag.lstrip("v").split(".")
    try:
        major, minor, patch = (int(p) for p in parts[:3])
    except ValueError:
        return "?"
    if major > 0:
        if any(sections.get(name) for name in MINOR_SECTIONS):
            return f"{major}.{minor + 1}.0"
        return f"{major}.{minor}.{patch + 1}"
    if any(sections.get(name) for name in MINOR_SECTIONS):
        return f"0.{minor + 1}.0"
    return f"0.{minor}.{patch + 1}"


def main() -> int:
    repos = sys.argv[1:] or [
        item["name"] for item in (gh(f"orgs/{ORG}/repos?per_page=100&type=all") or [])
    ]
    print(f"{'repo':16} {'tag':8} {'ahead':6} {'unreleased':34} {'next':8}")
    for repo in repos:
        info = gh(f"repos/{ORG}/{repo}")
        if not info or info.get("archived"):
            continue
        branch = info.get("default_branch", "main")
        release = gh(f"repos/{ORG}/{repo}/releases/latest")
        if not release:
            continue
        tag = release["tag_name"]
        compare = gh(f"repos/{ORG}/{repo}/compare/{tag}...{branch}")
        ahead = compare["ahead_by"] if compare else 0
        sections = unreleased(repo)
        if sections is None:
            summary = "(no changelog)"
            nxt = "-"
        elif not sections:
            summary = "(empty)"
            nxt = "-"
        else:
            summary = (
                ", ".join(
                    f"{name} {count}" for name, count in sections.items() if count
                )
                or "(headings only)"
            )
            nxt = bump(tag, sections)
        print(f"{repo:16} {tag:8} {ahead:<6} {summary[:33]:34} {nxt:8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
