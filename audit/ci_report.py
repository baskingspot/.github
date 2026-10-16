#!/usr/bin/env python3
"""Report where CI time goes, per repo.

Run it with `just ci-report`. For each repo it takes the latest successful `ci`
run on the default branch and prints each job's wall time, its slowest steps,
and the critical path: the job the run waited on. A job that takes most of the
run's time is the one to split. A repo with a single job that runs `just ci`
has nothing to parallelise until its recipe is split.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from typing import Any

ORG = "baskingspot"
SLOW_STEP_SECONDS = 20


def gh_json(path: str) -> Any:
    out = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def seconds(start: str | None, end: str | None) -> int:
    if not start or not end:
        return 0
    start_at = datetime.fromisoformat(start)
    end_at = datetime.fromisoformat(end)
    return int((end_at - start_at).total_seconds())


def report(repo: str) -> list[str]:
    runs = gh_json(
        f"repos/{ORG}/{repo}/actions/workflows/ci.yml/runs?branch=main&status=success&per_page=1"
    )["workflow_runs"]
    if not runs:
        return [f"## {repo}", "no successful ci run on main", ""]
    run = runs[0]
    jobs = gh_json(f"repos/{ORG}/{repo}/actions/runs/{run['id']}/jobs?per_page=100")[
        "jobs"
    ]
    timed = sorted(
        ((seconds(j["started_at"], j["completed_at"]), j) for j in jobs),
        key=lambda pair: -pair[0],
    )
    out = [f"## {repo}", f"run {run['id']} on {run['head_sha'][:7]}", ""]
    for total, job in timed:
        slow = [
            f"{step['name'][:40]} {seconds(step['started_at'], step['completed_at'])}s"
            for step in job["steps"]
            if seconds(step["started_at"], step["completed_at"]) >= SLOW_STEP_SECONDS
        ]
        out.append(
            f"- {job['name']}: {total}s" + (f" ({'; '.join(slow)})" if slow else "")
        )
    ci_jobs = [pair for pair in timed if "deploy" not in pair[1]["name"]]
    if ci_jobs:
        total, job = ci_jobs[0]
        everything = sum(t for t, _ in ci_jobs)
        out.append("")
        out.append(
            f"critical path: {job['name']}, {total}s of {everything}s of CI job time"
        )
        if len(ci_jobs) == 1 and total > 120:
            out.append(
                "one job holds all of CI: split its recipe so the parts run in parallel"
            )
    out.append("")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", help="one repo, by name")
    args = parser.parse_args()
    repos = (
        [args.repo]
        if args.repo
        else [
            r["name"]
            for r in gh_json(f"orgs/{ORG}/repos?per_page=100")
            if not r["archived"] and not r["private"] and r["name"] != ".github"
        ]
    )
    print("# CI time\n")
    for repo in sorted(repos):
        print("\n".join(report(repo)))


if __name__ == "__main__":
    main()
