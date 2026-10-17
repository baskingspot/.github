#!/usr/bin/env python3
"""Read, check, and apply the org's repository settings.

    repo_settings.py [--org] [--repo NAME ...] [--apply]

`settings.json` is the single list of settings the org wants, for the org
itself and for every repo. With no flag this checks: it prints each setting
that differs and exits 1. With `--apply` it changes them and checks again. The
audit calls the same code, so the audit and the tool cannot disagree.

It reads and writes with `gh api`, so it needs a token that administers the
org and its repos. A setting that GitHub does not offer for a repo, such as a
feature a private repo on the free plan lacks, is shown as unavailable and is
not drift.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

ORG = "baskingspot"
CONFIG = json.loads(
    (Path(__file__).parent / "settings.json").read_text(encoding="utf-8")
)

# A repo setting that has no value to read: the repo is private, or the plan
# lacks the feature. It is never drift.
UNAVAILABLE = "unavailable"


class Api(Protocol):
    def get(self, path: str) -> Any: ...
    def send(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> None: ...


class ApiError(RuntimeError):
    def __init__(self, message: str, status: int | None) -> None:
        super().__init__(message)
        self.status = status


class GhApi:
    """`gh api`, which carries the user's token."""

    def get(self, path: str) -> Any:
        return self._run("GET", path, None)

    def send(self, method: str, path: str, body: dict[str, Any] | None = None) -> None:
        self._run(method, path, body)

    @staticmethod
    def _run(method: str, path: str, body: dict[str, Any] | None) -> Any:
        args = ["gh", "api", "-i", "--method", method, path]
        if body is not None:
            args += ["--input", "-"]
        result = subprocess.run(
            args,
            input=json.dumps(body) if body is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
        # Headers, a blank line, then the body. Text mode turns CRLF into LF.
        parts = re.split(r"\r?\n\r?\n", result.stdout, maxsplit=1)
        head, text = parts[0], parts[1] if len(parts) > 1 else ""
        status_line = head.splitlines()[0] if head else ""
        status = int(status_line.split()[1]) if status_line.startswith("HTTP") else None
        if result.returncode != 0 or (status is not None and status >= 400):
            raise ApiError(
                f"{method} {path}: {(text or result.stderr).strip()[:200]}", status
            )
        return json.loads(text) if text.strip() else {"_status": status}


@dataclass(frozen=True)
class Drift:
    key: str
    want: Any
    have: Any

    def __str__(self) -> str:
        return f"{self.key} is {self.have!r}, want {self.want!r}"


def flatten(section: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """{"fields": {"a": 1}} as {"fields.a": 1}. A scalar section key stays as it is."""
    flat: dict[str, Any] = {}
    for key, value in section.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, f"{name}."))
        else:
            flat[name] = value
    return flat


def diff(want: dict[str, Any], have: dict[str, Any]) -> list[Drift]:
    """The settings whose value differs. An unavailable setting is skipped."""
    drifts = []
    for key, wanted in want.items():
        found = have.get(key, UNAVAILABLE)
        if found == UNAVAILABLE:
            continue
        if found != wanted:
            drifts.append(Drift(key, wanted, found))
    return drifts


def _optional(call: Any) -> Any:
    """A read that GitHub may refuse for this repo, as the UNAVAILABLE marker."""
    try:
        return call()
    except ApiError as error:
        if error.status in (402, 403, 404, 409, 422):
            return UNAVAILABLE
        raise


def read_repo(api: Api, repo: str) -> dict[str, Any]:
    """The current value of every setting in the repo section, by flat key."""
    base = f"repos/{ORG}/{repo}"
    meta = api.get(base)
    have: dict[str, Any] = {}
    for name in CONFIG["repo"]["fields"]:
        have[f"fields.{name}"] = meta.get(name, UNAVAILABLE)
    analysis = meta.get("security_and_analysis") or {}
    for name in CONFIG["repo"]["security_and_analysis"]:
        have[f"security_and_analysis.{name}"] = (analysis.get(name) or {}).get(
            "status", UNAVAILABLE
        )

    def alerts() -> bool:
        try:
            api.get(f"{base}/vulnerability-alerts")
        except ApiError as error:
            if error.status == 404:
                return False
            raise
        return True

    have["vulnerability_alerts"] = _optional(alerts)
    have["automated_security_fixes"] = _optional(
        lambda: api.get(f"{base}/automated-security-fixes")["enabled"]
    )
    have["private_vulnerability_reporting"] = _optional(
        lambda: api.get(f"{base}/private-vulnerability-reporting")["enabled"]
    )
    have["code_scanning_default_setup"] = _optional(
        lambda: api.get(f"{base}/code-scanning/default-setup")["state"]
    )
    perms = _optional(lambda: api.get(f"{base}/actions/permissions"))
    for name in CONFIG["repo"]["actions"]:
        have[f"actions.{name}"] = (
            UNAVAILABLE if perms == UNAVAILABLE else perms.get(name, UNAVAILABLE)
        )
    workflow = _optional(lambda: api.get(f"{base}/actions/permissions/workflow"))
    for name in CONFIG["repo"]["actions_workflow"]:
        have[f"actions_workflow.{name}"] = (
            UNAVAILABLE if workflow == UNAVAILABLE else workflow.get(name, UNAVAILABLE)
        )
    return have


def read_org(api: Api) -> dict[str, Any]:
    meta = api.get(f"orgs/{ORG}")
    have = {
        f"fields.{name}": meta.get(name, UNAVAILABLE)
        for name in CONFIG["org"]["fields"]
    }
    perms = api.get(f"orgs/{ORG}/actions/permissions")
    for name in CONFIG["org"]["actions"]:
        have[f"actions.{name}"] = perms.get(name, UNAVAILABLE)
    return have


def want_repo() -> dict[str, Any]:
    return flatten(CONFIG["repo"])


def want_org() -> dict[str, Any]:
    return flatten(CONFIG["org"])


def _toggle(api: Api, path: str, on: bool) -> None:
    api.send("PUT" if on else "DELETE", path)


def apply_repo(api: Api, repo: str, drifts: list[Drift]) -> None:
    """Change the drifted settings. Each group goes to the endpoint that owns it."""
    base = f"repos/{ORG}/{repo}"
    keys = {drift.key: drift.want for drift in drifts}
    patch: dict[str, Any] = {}
    for key, value in keys.items():
        group, _, name = key.partition(".")
        if group == "fields" and name != "has_pages":
            patch[name] = value
        elif group == "security_and_analysis":
            patch.setdefault("security_and_analysis", {})[name] = {"status": value}
    if patch:
        api.send("PATCH", base, patch)
    if keys.get("fields.has_pages") is False:
        api.send("DELETE", f"{base}/pages")
    if "vulnerability_alerts" in keys:
        _toggle(api, f"{base}/vulnerability-alerts", bool(keys["vulnerability_alerts"]))
    if "automated_security_fixes" in keys:
        _toggle(
            api,
            f"{base}/automated-security-fixes",
            bool(keys["automated_security_fixes"]),
        )
    if "private_vulnerability_reporting" in keys:
        _toggle(
            api,
            f"{base}/private-vulnerability-reporting",
            bool(keys["private_vulnerability_reporting"]),
        )
    if "code_scanning_default_setup" in keys:
        api.send(
            "PATCH",
            f"{base}/code-scanning/default-setup",
            {"state": keys["code_scanning_default_setup"]},
        )
    if any(key.startswith("actions.") for key in keys):
        api.send("PUT", f"{base}/actions/permissions", dict(CONFIG["repo"]["actions"]))
    if any(key.startswith("actions_workflow.") for key in keys):
        api.send(
            "PUT",
            f"{base}/actions/permissions/workflow",
            dict(CONFIG["repo"]["actions_workflow"]),
        )


def apply_org(api: Api, drifts: list[Drift]) -> None:
    keys = {drift.key: drift.want for drift in drifts}
    patch = {
        key.split(".", 1)[1]: value
        for key, value in keys.items()
        if key.startswith("fields.")
    }
    if patch:
        api.send("PATCH", f"orgs/{ORG}", patch)
    if any(key.startswith("actions.") for key in keys):
        api.send(
            "PUT", f"orgs/{ORG}/actions/permissions", dict(CONFIG["org"]["actions"])
        )


def repo_names(api: Api) -> list[str]:
    repos = api.get(f"orgs/{ORG}/repos?per_page=100&type=all")
    return sorted(r["name"] for r in repos if not r["archived"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--org", action="store_true", help="the org's own settings")
    parser.add_argument("--repo", action="append", default=[], help="one repo, by name")
    parser.add_argument("--apply", action="store_true", help="change what differs")
    args = parser.parse_args()
    api = GhApi()
    everything = not args.org and not args.repo
    drift_found = False

    def handle(label: str, read: Any, want: dict[str, Any], apply: Any) -> None:
        nonlocal drift_found
        drifts = diff(want, read())
        if drifts and args.apply:
            apply(drifts)
            for drift in drifts:
                print(
                    f"{label}: set {drift.key} to {drift.want!r} (was {drift.have!r})"
                )
            drifts = diff(want, read())
        for drift in drifts:
            drift_found = True
            print(f"{label}: {drift}")
        if not drifts:
            print(f"{label}: matches")

    if args.org or everything:
        handle(
            "org",
            lambda: read_org(api),
            want_org(),
            lambda drifts: apply_org(api, drifts),
        )
    for name in repo_names(api) if everything else args.repo:
        handle(
            name,
            lambda name=name: read_repo(api, name),
            want_repo(),
            lambda drifts, name=name: apply_repo(api, name, drifts),
        )
    return 1 if drift_found else 0


if __name__ == "__main__":
    sys.exit(main())
