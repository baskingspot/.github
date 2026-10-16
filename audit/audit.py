#!/usr/bin/env python3
"""Audit the baskingspot org for conformance.

Run it with `just audit`. The baskingspot-audit skill says what to do with the
report. The script checks what a machine can check: repo metadata, the files
every repo has, justfile and workflow style, README hygiene, the brand marks,
and the registration of docs sites. It also lists files and recipes that
repeat across repos, as candidates to move into a shared repo.

It reads the org's public repos over HTTPS (a private repo, such as `internal`, is out of scope) with `gh` and `git`, and changes nothing.
Exit status 1 means at least one error finding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ORG = "baskingspot"
PALETTE = {"#16191d", "#f4f1ec", "#d4412b", "#58616c"}
BIO = "Zig is cold-blooded. Come bask. Libraries between std and your application."
# The repo that carries the org's own brand, not a project mark.
META_REPO = ".github"
BRAND_DIR = Path(__file__).resolve().parent.parent / "brand" / "tools" / "brand.py"

STANDARD_FILES = [
    "flake.nix",
    "flake.lock",
    ".envrc",
    "justfile",
    "AGENTS.md",
    "README.md",
    "LICENSE",
    ".gitignore",
    ".github/workflows/ci.yml",
    ".github/workflows/zizmor.yml",
]
BRAND_FILES = ["logo.svg", "logo-dark.svg", "favicon.svg", "social.png", "LICENSE"]
# Words the voice guide lists. One hit is not a tell, so these are warnings.
VOICE_WORDS = [
    "delve",
    "underscore",
    "showcase",
    "foster",
    "leverage",
    "utilize",
    "streamline",
    "empower",
    "elevate",
    "pivotal",
    "crucial",
    "robust",
    "seamless",
    "comprehensive",
    "cutting-edge",
    "tapestry",
    "furthermore",
    "moreover",
    "additionally",
]
STATUS_WORDS = ["currently", "not yet", "recently", "coming soon", "work in progress"]
# Files that repeat on purpose or are generated. They are not dedupe candidates.
DEDUPE_SKIP = {
    "LICENSE",
    "flake.lock",
    "README.md",
    "AGENTS.md",
    "social.png",
    "social.svg",
}


@dataclass
class Finding:
    level: str  # error, warn, or info
    repo: str
    check: str
    message: str


@dataclass
class Repo:
    name: str
    meta: dict[str, Any]
    path: Path
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, check: str, message: str) -> None:
        self.findings.append(Finding(level, self.name, check, message))

    def read(self, rel: str) -> str | None:
        file = self.path / rel
        return (
            file.read_text(encoding="utf-8", errors="replace")
            if file.is_file()
            else None
        )


def run(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def gh_json(path: str) -> Any:
    return json.loads(run("gh", "api", "--paginate", path) or "null")


def normal(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".").strip()


def readme_tagline(readme: str) -> str | None:
    """The first paragraph after the logo header."""
    body = re.sub(r"^\s*<h1>.*?</h1>\s*", "", readme, count=1, flags=re.DOTALL)
    for paragraph in re.split(r"\n\s*\n", body):
        text = paragraph.strip()
        if text and not text.startswith(("#", "<", "|", "-", "`")):
            return text
    return None


def latest_release() -> tuple[str, str]:
    tag = str(gh_json(f"repos/{ORG}/gh-actions/releases/latest")["tag_name"])
    sha = run(
        "gh", "api", f"repos/{ORG}/gh-actions/commits/{tag}", "--jq", ".sha"
    ).strip()
    return tag, sha


def check_metadata(repo: Repo, roster: dict[str, dict[str, str]]) -> None:
    meta = repo.meta
    description = str(meta.get("description") or "")
    topics = meta.get("topics") or []
    if not description:
        repo.add("error", "about", "no description")
    else:
        if not description[0].isupper():
            repo.add("warn", "about", "the description does not start with a capital")
        if not description.endswith("."):
            repo.add(
                "error",
                "about",
                f"the description does not end with a period: {description!r}",
            )
    if not topics and repo.name != META_REPO:
        repo.add("error", "topics", "no topics")
    if (repo.path / "build.zig").is_file() and "zig" not in topics:
        repo.add("error", "topics", "a Zig repo needs the topic `zig`")
    homepage = str(meta.get("homepage") or "")
    want = f"https://baskingspot.dev/{repo.name}/" if repo.name in roster else ""
    if want and homepage != want:
        repo.add("error", "homepage", f"want {want}, have {homepage or 'none'}")
    if not want and homepage:
        repo.add(
            "info",
            "homepage",
            f"has a homepage but is not in the site roster: {homepage}",
        )
    expect = {"has_wiki": False, "has_projects": False, "delete_branch_on_merge": True}
    for key, value in expect.items():
        if meta.get(key) != value:
            repo.add("error", "settings", f"{key} is {meta.get(key)}, want {value}")
    if meta.get("default_branch") != "main":
        repo.add("error", "settings", f"default branch is {meta.get('default_branch')}")
    license_info = meta.get("license") or {}
    if (license_info or {}).get("spdx_id") != "MIT":
        repo.add("error", "license", "GitHub does not detect an MIT license")
    perms = gh_json(f"repos/{ORG}/{repo.name}/actions/permissions/workflow")
    if perms.get("default_workflow_permissions") != "read":
        repo.add("error", "settings", "default workflow permissions are not read-only")
    check_social(repo)


def check_social(repo: Repo) -> None:
    """GitHub has no API for the social preview, but the repo page names it.

    The page's og:image points at opengraph.githubassets.com while the repo
    has no uploaded image, and at repository-images.githubusercontent.com once
    one is uploaded.
    """
    if repo.name == META_REPO:
        # The profile repo is not a project. It has no card of its own.
        return
    asset = "docs/static/social.png"
    try:
        with urllib.request.urlopen(
            f"https://github.com/{ORG}/{repo.name}", timeout=30
        ) as page:
            html = page.read().decode("utf-8", errors="replace")
    except OSError as error:
        repo.add(
            "info",
            "social",
            f"could not read the repo page to check the social preview: {error}",
        )
        return
    match = re.search(r'<meta property="og:image" content="([^"]*)"', html)
    image = match.group(1) if match else ""
    if "repository-images.githubusercontent.com" not in image:
        repo.add(
            "warn",
            "social",
            f"no custom social preview. Upload {asset} in the repo's settings",
        )


def check_files(repo: Repo) -> None:
    for rel in STANDARD_FILES:
        if not (repo.path / rel).is_file():
            repo.add("error", "files", f"missing {rel}")
    if repo.name != META_REPO:
        for name in BRAND_FILES:
            if not (repo.path / "docs" / "static" / name).is_file():
                repo.add("error", "brand", f"missing docs/static/{name}")
    if (repo.path / "Justfile").is_file():
        repo.add("error", "files", "the justfile must be lowercase")
    gitignore = repo.read(".gitignore") or ""
    for line in (".direnv/", ".envrc.local"):
        if line not in gitignore:
            repo.add("warn", "files", f".gitignore lacks {line}")
    envrc = repo.read(".envrc") or ""
    if "use flake" not in envrc:
        repo.add("error", "files", ".envrc does not `use flake`")
    license_text = repo.read("LICENSE") or ""
    if license_text and "MIT License" not in license_text:
        repo.add("error", "license", "LICENSE is not MIT")
    elif license_text and "and contributors" not in license_text:
        people = gh_json(f"repos/{ORG}/{repo.name}/contributors?per_page=100")
        humans = [p["login"] for p in people if p.get("type") == "User"]
        if len(humans) > 1:
            repo.add(
                "warn",
                "license",
                f"{len(humans)} people have contributed ({', '.join(humans)}), "
                'so the copyright line should end with "and contributors"',
            )
    brand_license = repo.read("docs/static/LICENSE")
    if brand_license is not None and "All rights reserved" not in brand_license:
        repo.add("error", "license", "docs/static/LICENSE does not reserve the logos")


def check_flake(repo: Repo) -> None:
    flake = repo.read("flake.nix")
    if flake is None:
        return
    if "nixConfig" in flake:
        repo.add("error", "flake", "nixConfig prompts for trust on every direnv entry")
    if repo.name != "nix" and f"github:{ORG}/nix" not in flake:
        repo.add("error", "flake", f"the flake does not use github:{ORG}/nix")


def recipes(repo: Repo) -> dict[str, Any]:
    justfile = repo.path / "justfile"
    if not justfile.is_file():
        return {}
    out = run(
        "just",
        "--justfile",
        str(justfile),
        "--dump",
        "--dump-format",
        "json",
        check=False,
    )
    try:
        return json.loads(out)["recipes"]
    except (json.JSONDecodeError, KeyError):
        repo.add("error", "justfile", "`just --dump` failed")
        return {}


def check_justfile(repo: Repo) -> None:
    table = recipes(repo)
    if not table:
        return
    if "ci" not in table:
        repo.add("error", "justfile", "no `ci` recipe")
    default = table.get("default")
    if default is None or "private" not in default.get("attributes", []):
        repo.add(
            "error",
            "justfile",
            "`default` must be a [private] recipe that lists the recipes",
        )
    for name, recipe in table.items():
        attributes = recipe.get("attributes", [])
        kinds = {next(iter(a)) if isinstance(a, dict) else a for a in attributes}
        if name != "default" and not recipe.get("private"):
            if "doc" not in kinds:
                repo.add("warn", "justfile", f"recipe `{name}` has no [doc(...)]")
            if "group" not in kinds:
                repo.add("warn", "justfile", f"recipe `{name}` has no [group(...)]")
        for param in recipe.get("parameters", []):
            if param["name"] != param["name"].upper():
                repo.add(
                    "warn",
                    "justfile",
                    f"recipe `{name}` has a lowercase parameter `{param['name']}`",
                )
    fmt = subprocess.run(
        ["just", "--justfile", str(repo.path / "justfile"), "--fmt", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    if fmt.returncode != 0:
        repo.add("error", "justfile", "`just --fmt --check` fails")


def check_workflows(repo: Repo, release: tuple[str, str]) -> None:
    folder = repo.path / ".github" / "workflows"
    if not folder.is_dir():
        return
    tag, sha = release
    for file in sorted(folder.glob("*.yml")):
        text = file.read_text(encoding="utf-8")
        rel = f".github/workflows/{file.name}"
        if not re.search(r"^permissions: \{\}\s*$", text, flags=re.MULTILINE):
            repo.add(
                "error", "workflows", f"{rel} does not start with `permissions: {{}}`"
            )
        for line in text.splitlines():
            uses = re.match(r"\s*-?\s*uses:\s*(\S+)(.*)$", line)
            if uses and not uses.group(1).startswith("./"):
                if not re.search(
                    r"@[0-9a-f]{40}$", uses.group(1)
                ) or "#" not in uses.group(2):
                    repo.add(
                        "error",
                        "workflows",
                        f"{rel}: not pinned by SHA with a version comment: {uses.group(1)}",
                    )
                if uses.group(1).startswith(
                    f"{ORG}/gh-actions/"
                ) and sha not in uses.group(1):
                    repo.add(
                        "warn", "workflows", f"{rel}: gh-actions pin is behind {tag}"
                    )
            if re.search(r"runs-on:\s*ubuntu-latest", line):
                repo.add(
                    "error",
                    "workflows",
                    f"{rel}: runs-on ubuntu-latest, want ubuntu-26.04",
                )
    ci_text = repo.read(".github/workflows/ci.yml") or ""
    # gh-actions defines those inputs, so it is the one repo that names them.
    if repo.name != "gh-actions" and re.search(
        r"^\s+(recipes|runners|non-blocking):", ci_text, flags=re.MULTILINE
    ):
        repo.add(
            "warn",
            "workflows",
            "ci.yml passes recipes, runners, or non-blocking. List the jobs in .github/ci.yaml",
        )
    for stale in ("deploy-docs.yml", "update-flake-lock.yml", "update-actions.yml"):
        if (folder / stale).is_file() and repo.name not in {"gh-actions"}:
            repo.add(
                "warn",
                "workflows",
                f"{stale} duplicates what the shared workflows or norm do",
            )


def check_readme(repo: Repo) -> None:
    readme = repo.read("README.md")
    if readme is None:
        return
    if repo.name != META_REPO:
        if not readme.lstrip().startswith("<h1>"):
            repo.add("error", "readme", "the README does not open with the logo header")
        if "docs/AI.md" not in readme:
            repo.add("error", "readme", "no link to AI.md")
        if "badge.svg" not in readme:
            repo.add("error", "readme", "no baskingspot badge")
    if "TODO" in readme:
        repo.add("error", "readme", "the README has a TODO left in it")
    dashes = readme.count("\u2014")
    if dashes:
        repo.add(
            "warn",
            "voice",
            f"README has {dashes} em dash(es). The voice guide bans them in new prose",
        )
    lower = readme.lower()
    hits = [w for w in VOICE_WORDS if re.search(rf"\b{re.escape(w)}", lower)]
    if hits:
        repo.add(
            "warn",
            "voice",
            f"README uses words from the voice guide's list: {', '.join(hits)}",
        )
    status = [w for w in STATUS_WORDS if w in lower]
    if status:
        repo.add("warn", "voice", f"README has status words: {', '.join(status)}")
    description = str(repo.meta.get("description") or "")
    tagline = readme_tagline(readme)
    if (
        repo.name != META_REPO
        and tagline
        and description
        and normal(tagline) != normal(description)
    ):
        repo.add(
            "error",
            "coherence",
            f"README's first paragraph differs from the About text: {tagline!r}",
        )


def check_brand(repo: Repo, scratch: Path) -> None:
    static = repo.path / "docs" / "static"
    for file in list(static.glob("*.svg")) + list(
        (repo.path / "router" / "static").glob("*.svg")
    ):
        colors = {
            c.lower()
            for c in re.findall(r"#[0-9a-fA-F]{6}\b", file.read_text(encoding="utf-8"))
        }
        stray = colors - PALETTE
        if stray:
            repo.add(
                "error",
                "brand",
                f"{file.relative_to(repo.path)} uses colors outside the palette: {sorted(stray)}",
            )
    if repo.name == META_REPO or not static.is_dir():
        return
    out = scratch / "reference" / repo.name
    result = subprocess.run(
        [sys.executable, str(BRAND_DIR), "library", repo.name, "audit", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        repo.add(
            "warn",
            "brand",
            f"could not generate the reference marks: {result.stderr.strip()[:120]}",
        )
        return
    for name in ("logo.svg", "logo-dark.svg", "favicon.svg"):
        have, want = static / name, out / "docs" / "static" / name
        if have.is_file() and have.read_bytes() != want.read_bytes():
            repo.add(
                "error",
                "brand",
                f"docs/static/{name} differs from what `just new-library {repo.name}` writes",
            )


def check_site(
    repo: Repo, roster: dict[str, dict[str, str]], router: str | None
) -> None:
    config = repo.read("docs/config.toml")
    registered = repo.name in roster
    if config is None:
        if registered:
            repo.add(
                "error", "site", "registered in sites.json but has no docs/config.toml"
            )
        return
    if not registered:
        repo.add(
            "warn",
            "site",
            "has a docs site but is not in baskingspot/site's sites.json",
        )
        return
    if 'theme = "baskingspot"' not in config:
        repo.add("error", "site", 'docs/config.toml does not set theme = "baskingspot"')
    wrangler = repo.read("wrangler.jsonc") or ""
    if f'"name": "baskingspot-dev-{repo.name}"' not in wrangler:
        repo.add(
            "error", "site", f"wrangler.jsonc name is not baskingspot-dev-{repo.name}"
        )
    ci = repo.read(".github/workflows/ci.yml") or ""
    if "deploy-docs.yml" not in ci:
        repo.add("error", "site", "ci.yml has no deploy job calling deploy-docs.yml")
    if router is not None and f"baskingspot-dev-{repo.name}" not in router:
        repo.add("error", "site", "the router has no service binding for this site")
    description = str(repo.meta.get("description") or "")
    entry = roster[repo.name].get("description", "")
    if normal(entry) != normal(description):
        repo.add(
            "error",
            "coherence",
            f"sites.json description differs from the About text: {entry!r}",
        )
    site_desc = re.search(r'^description = "(.*)"$', config, flags=re.MULTILINE)
    if site_desc and normal(site_desc.group(1)) != normal(description):
        repo.add(
            "error",
            "coherence",
            "docs/config.toml description differs from the About text",
        )


def check_docker(repo: Repo) -> None:
    dockerfile = repo.read("Dockerfile")
    if dockerfile is None:
        return
    for line in dockerfile.splitlines():
        match = re.match(r"\s*FROM\s+(?:--\S+\s+)?(\S+)", line, flags=re.IGNORECASE)
        image = match.group(1) if match else ""
        if (
            image
            and image != "scratch"
            and "$" not in image
            and "@sha256:" not in image
        ):
            repo.add("warn", "docker", f"base image not pinned by digest: {image}")
    if "hadolint" not in (repo.read("justfile") or ""):
        repo.add("error", "docker", "the lint recipe does not run hadolint")


def check_org(site: Repo | None, repos: dict[str, Repo]) -> list[Finding]:
    findings: list[Finding] = []
    org = json.loads(run("gh", "api", f"orgs/{ORG}"))
    if org.get("description") != BIO:
        findings.append(
            Finding(
                "error",
                "(org)",
                "coherence",
                f"the org bio is {org.get('description')!r}",
            )
        )
    if org.get("blog") != "https://baskingspot.dev":
        findings.append(
            Finding(
                "warn", "(org)", "coherence", f"the org website is {org.get('blog')!r}"
            )
        )
    if site is not None:
        landing = site.read("router/index.html") or ""
        if BIO not in landing:
            findings.append(
                Finding(
                    "error",
                    "(org)",
                    "coherence",
                    "the landing page meta description is not the bio",
                )
            )
    meta = repos.get(META_REPO)
    if meta is not None:
        profile = meta.read("profile/README.md") or ""
        if "Zig is cold-blooded. Come bask." not in profile:
            findings.append(
                Finding(
                    "error",
                    "(org)",
                    "coherence",
                    "the profile README lacks the tagline",
                )
            )
    return findings


def dedupe(repos: dict[str, Repo]) -> list[str]:
    """Files and recipes that repeat across repos, as candidates for a shared home."""
    lines: list[str] = []
    wanted = {"ci.yml", "zizmor.yml", "wrangler.jsonc", "actionlint.yaml"}
    variants: dict[str, dict[str, list[str]]] = {}
    for repo in repos.values():
        for file in repo.path.rglob("*"):
            rel = file.relative_to(repo.path)
            if not file.is_file() or file.name not in wanted or rel.parts[0] == ".git":
                continue
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            variants.setdefault(str(rel), {}).setdefault(digest, []).append(repo.name)
    for rel, groups in sorted(variants.items()):
        total = sum(len(names) for names in groups.values())
        if total < 2:
            continue
        shown = " | ".join(", ".join(sorted(names)) for names in groups.values())
        count = len(groups)
        label = "identical in" if count == 1 else f"{count} variants:"
        lines.append(f"`{rel}` {label} {shown}")
    bodies: dict[str, list[str]] = {}
    for repo in repos.values():
        for name, recipe in recipes(repo).items():
            body = json.dumps(recipe.get("body"))
            if len(body) > 120 and name != "default":
                bodies.setdefault(body, []).append(f"{repo.name}:{name}")
    for names in bodies.values():
        if len(names) > 1:
            lines.append(f"recipe body identical in {', '.join(sorted(names))}")
    return lines


def clone(name: str, into: Path) -> Path:
    dest = into / name
    run(
        "git",
        "clone",
        "--quiet",
        "--depth",
        "1",
        f"https://github.com/{ORG}/{name}.git",
        str(dest),
    )
    return dest


def report(repos: dict[str, Repo], org: list[Finding], repeated: list[str]) -> int:
    errors = warns = 0
    out: list[str] = ["# baskingspot conformance", ""]
    groups = [("(org)", org)] + [
        (name, repo.findings) for name, repo in sorted(repos.items())
    ]
    for name, findings in groups:
        out.append(f"## {name}")
        if not findings:
            out.append("clean")
        for finding in sorted(
            findings, key=lambda f: ("error", "warn", "info").index(f.level)
        ):
            out.append(f"- **{finding.level}** [{finding.check}] {finding.message}")
            errors += finding.level == "error"
            warns += finding.level == "warn"
        out.append("")
    out.append("## Repeated across repos")
    out.extend(f"- {line}" for line in repeated or ["nothing repeats"])
    out.append("")
    out.append(f"{errors} errors, {warns} warnings, {len(repos)} repos.")
    print("\n".join(out))
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="audit one repo, by name")
    args = parser.parse_args()
    release = latest_release()
    with tempfile.TemporaryDirectory(prefix="baskingspot-audit-") as tmp:
        scratch = Path(tmp)
        listing = gh_json(f"orgs/{ORG}/repos?type=all&per_page=100")
        metas = {
            m["name"]: m
            for m in listing
            if not m["archived"] and not m["fork"] and not m["private"]
        }
        repos: dict[str, Repo] = {}
        for name in sorted(metas):
            if args.repo and name != args.repo:
                continue
            # The list endpoint omits some settings, so read each repo itself.
            detail = gh_json(f"repos/{ORG}/{name}")
            repos[name] = Repo(name, detail, clone(name, scratch))
        # The roster and the router come from `site`, even for a one-repo run.
        site = repos.get("site") or Repo("site", metas["site"], clone("site", scratch))
        roster = json.loads(site.read("sites.json") or "{}").get("sites", {})
        router = site.read("router/wrangler.jsonc")
        for repo in repos.values():
            check_metadata(repo, roster)
            check_files(repo)
            check_flake(repo)
            check_justfile(repo)
            check_workflows(repo, release)
            check_readme(repo)
            check_brand(repo, scratch)
            check_site(repo, roster, router)
            check_docker(repo)
        org = [] if args.repo else check_org(site, repos)
        repeated = [] if args.repo else dedupe(repos)
        return report(repos, org, repeated)


if __name__ == "__main__":
    sys.exit(main())
