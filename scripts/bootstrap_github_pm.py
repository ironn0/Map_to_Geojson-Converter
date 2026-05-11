"""
Bootstrap GitHub PM resources (labels + milestones) in an idempotent way.

Usage:
    python scripts/bootstrap_github_pm.py
    python scripts/bootstrap_github_pm.py --repo owner/name
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from urllib.parse import quote

LABELS: dict[str, tuple[str, str]] = {
    "type:bug": ("d73a4a", "Defect or regression"),
    "type:feature": ("0e8a16", "New capability or enhancement"),
    "type:tech-debt": ("6f42c1", "Refactor, cleanup, or maintenance work"),
    "area:backend": ("1d76db", "Backend/API related work"),
    "area:frontend": ("a2eeef", "Frontend/UI related work"),
    "area:docs": ("fef2c0", "Documentation work"),
    "prio:P0": ("b60205", "Highest urgency"),
    "prio:P1": ("d93f0b", "High priority"),
    "prio:P2": ("fbca04", "Normal priority"),
    "ready": ("0e8a16", "Ready to pull into active execution"),
}

MILESTONES: tuple[str, ...] = (
    "M1 Core Reliability",
    "M2 Quality Baseline Expansion",
    "M3 Architecture Cleanup",
    "M4 v1 Product Readiness",
)


def run_gh(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *cmd],
        check=False,
        text=True,
        capture_output=True,
    )


def parse_json(stdout: str) -> object:
    return json.loads(stdout) if stdout.strip() else {}


def resolve_repo(cli_repo: str | None) -> str:
    if cli_repo:
        return cli_repo
    cp = run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if cp.returncode != 0:
        raise RuntimeError(
            "Unable to detect repository via gh. Pass --repo owner/name.\n"
            f"{cp.stderr.strip()}"
        )
    repo = cp.stdout.strip()
    if not repo:
        raise RuntimeError("Empty repository value returned by gh repo view.")
    return repo


def upsert_label(repo: str, name: str, color: str, description: str) -> None:
    encoded = quote(name, safe="")
    patch = run_gh(
        [
            "api",
            f"/repos/{repo}/labels/{encoded}",
            "--method",
            "PATCH",
            "-f",
            f"name={name}",
            "-f",
            f"color={color}",
            "-f",
            f"description={description}",
        ]
    )
    if patch.returncode == 0:
        print(f"updated label: {name}")
        return

    post = run_gh(
        [
            "api",
            f"/repos/{repo}/labels",
            "--method",
            "POST",
            "-f",
            f"name={name}",
            "-f",
            f"color={color}",
            "-f",
            f"description={description}",
        ]
    )
    if post.returncode != 0:
        raise RuntimeError(f"Failed to create label '{name}': {post.stderr.strip()}")
    print(f"created label: {name}")


def fetch_existing_milestones(repo: str) -> set[str]:
    cp = run_gh(["api", f"/repos/{repo}/milestones?state=all&per_page=100"])
    if cp.returncode != 0:
        raise RuntimeError(f"Failed to list milestones: {cp.stderr.strip()}")
    data = parse_json(cp.stdout)
    if not isinstance(data, list):
        return set()
    return {item.get("title", "") for item in data if isinstance(item, dict)}


def ensure_milestones(repo: str) -> None:
    existing = fetch_existing_milestones(repo)
    for title in MILESTONES:
        if title in existing:
            print(f"exists milestone: {title}")
            continue
        cp = run_gh(
            [
                "api",
                f"/repos/{repo}/milestones",
                "--method",
                "POST",
                "-f",
                f"title={title}",
            ]
        )
        if cp.returncode != 0:
            raise RuntimeError(f"Failed to create milestone '{title}': {cp.stderr.strip()}")
        print(f"created milestone: {title}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap GitHub PM labels and milestones.")
    parser.add_argument("--repo", help="Repository in owner/name format.")
    args = parser.parse_args()

    auth = run_gh(["auth", "status"])
    if auth.returncode != 0:
        print("gh is not authenticated. Run: gh auth login", file=sys.stderr)
        return 1

    try:
        repo = resolve_repo(args.repo)
        print(f"repository: {repo}")
        for name, (color, description) in LABELS.items():
            upsert_label(repo, name, color, description)
        ensure_milestones(repo)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("PM bootstrap completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
