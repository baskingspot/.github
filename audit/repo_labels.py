"""Check every repo's labels against audit/labels.json, the one list of them.

Kind is not a label. It is the issue type that the org issue forms set, so
the labels here are priority and the few states a type cannot express.

Three buckets. A canonical label is created where it is missing and updated
where its color or description differs. A superseded label is deleted, since
the type and GitHub's close reasons now carry it. Anything else is reported
and left alone: tls keeps eighty topic labels that index its corpus, and a
tool that pruned them would delete real work.

Dry run by default. `--apply` changes what differs, `--repo NAME` reads one
repo, and the exit code is 1 when anything differs.
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_settings import ORG, Api, ApiError, GhApi, repo_names

LABELS = json.loads((Path(__file__).parent / "labels.json").read_text(encoding="utf-8"))

# Long enough to see the shape of a leftover list, short enough to read.
LEFTOVERS_SHOWN = 12


@dataclass(frozen=True)
class Change:
    """One label to write: create it, update it, or delete it."""

    action: str
    name: str
    body: dict[str, Any] | None = None

    def __str__(self) -> str:
        if self.action == "update":
            return f"update {self.name}"
        if self.action == "delete":
            return f"delete {self.name}"
        return f"create {self.name}"


def plan(have: dict[str, dict[str, str]]) -> tuple[list[Change], list[str]]:
    """What to change, and the labels that belong to nobody's scheme but a repo's."""
    canonical = {label["name"]: label for label in LABELS["canonical"]}
    superseded = set(LABELS["superseded"])
    changes: list[Change] = []
    for name, want in canonical.items():
        body = {"color": want["color"], "description": want["description"]}
        found = have.get(name)
        if found is None:
            changes.append(Change("create", name, body))
        elif (
            found.get("color") != want["color"]
            or found.get("description") != want["description"]
        ):
            changes.append(Change("update", name, body))
    for name in sorted(superseded & have.keys()):
        changes.append(Change("delete", name))
    leftovers = sorted(have.keys() - canonical.keys() - superseded)
    return changes, leftovers


def read_labels(api: Api, repo: str) -> dict[str, dict[str, str]]:
    """The repo's labels by name, with the two fields the tool compares."""
    have: dict[str, dict[str, str]] = {}
    page = 1
    while True:
        batch = api.get(
            f"repos/{ORG}/{repo}/labels?per_page=100&page={page}",
        )
        for label in batch:
            have[label["name"]] = {
                "color": label["color"],
                "description": label.get("description") or "",
            }
        if len(batch) < 100:
            return have
        page += 1


def apply_changes(api: Api, repo: str, changes: list[Change]) -> list[str]:
    """Make the changes. Returns what GitHub refused, one line each."""
    refused: list[str] = []
    for change in changes:
        # A label name can carry a colon, which is legal in a path once encoded.
        path = f"repos/{ORG}/{repo}/labels/{change.name}"
        try:
            if change.action == "create":
                body = {"name": change.name, **(change.body or {})}
                api.send("POST", f"repos/{ORG}/{repo}/labels", body)
            elif change.action == "update":
                api.send("PATCH", path, change.body)
            else:
                api.send("DELETE", path)
        except ApiError as error:
            refused.append(f"{change}: {error}")
    return refused


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", action="append", default=[], help="one repo, by name")
    parser.add_argument("--apply", action="store_true", help="change what differs")
    parser.add_argument(
        "--leftovers",
        action="store_true",
        help="list every label the tool leaves alone",
    )
    args = parser.parse_args()
    api = GhApi()
    drift_found = False

    for repo in args.repo or repo_names(api):
        changes, leftovers = plan(read_labels(api, repo))
        if changes and args.apply:
            for refusal in apply_changes(api, repo, changes):
                drift_found = True
                print(f"{repo}: {refusal}")
            # A read right after a write can be stale, so look again before
            # calling a label drift.
            for _ in range(4):
                changes, _ = plan(read_labels(api, repo))
                if not changes:
                    break
                time.sleep(2)
        for change in changes:
            drift_found = True
            print(f"{repo}: {change}")
        if leftovers:
            shown = leftovers if args.leftovers else leftovers[:LEFTOVERS_SHOWN]
            rest = len(leftovers) - len(shown)
            tail = f", and {rest} more (--leftovers lists them)" if rest > 0 else ""
            print(f"{repo}: left alone {', '.join(shown)}{tail}")
        if not changes:
            print(f"{repo}: matches")
    return 1 if drift_found else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:  # pragma: no cover - gh itself
        print(error, file=sys.stderr)
        sys.exit(1)
