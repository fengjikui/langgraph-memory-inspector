from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence


REPO = "fengjikui/langgraph-memory-inspector"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


Runner = Callable[[Sequence[str]], str]


def collect_launch_status(runner: Runner | None = None) -> list[Check]:
    """Collect local and GitHub launch gates for the first public posting."""
    run = runner or _run
    checks = [
        _git_status_check(run),
        _repo_visibility_check(run),
        _latest_ci_check(run),
        _release_check(run),
        _feedback_issue_check(run),
        _social_preview_issue_check(run),
        _open_graph_check(run),
    ]
    return checks


def _git_status_check(run: Runner) -> Check:
    output = run(("git", "status", "--branch", "--short")).strip()
    clean = output == "## main...origin/main"
    return Check(
        name="local git status",
        status="pass" if clean else "warn",
        detail=output or "empty git status output",
    )


def _repo_visibility_check(run: Runner) -> Check:
    data = _json(run(("gh", "repo", "view", REPO, "--json", "visibility,url")))
    visibility = str(data.get("visibility", ""))
    return Check(
        name="repository visibility",
        status="pass" if visibility == "PUBLIC" else "fail",
        detail=f"{visibility} {data.get('url', '')}".strip(),
    )


def _latest_ci_check(run: Runner) -> Check:
    runs = _json(run(("gh", "run", "list", "--branch", "main", "--limit", "1", "--json", "status,conclusion,displayTitle,url")))
    latest = runs[0] if runs else {}
    status = latest.get("status")
    conclusion = latest.get("conclusion")
    passed = status == "completed" and conclusion == "success"
    return Check(
        name="latest main CI",
        status="pass" if passed else "fail",
        detail=f"{latest.get('displayTitle', 'missing run')} ({status}/{conclusion}) {latest.get('url', '')}",
    )


def _release_check(run: Runner) -> Check:
    data = _json(run(("gh", "release", "view", "v0.1.0", "--json", "tagName,url")))
    tag = str(data.get("tagName", ""))
    return Check(
        name="v0.1.0 release",
        status="pass" if tag == "v0.1.0" else "fail",
        detail=f"{tag} {data.get('url', '')}".strip(),
    )


def _feedback_issue_check(run: Runner) -> Check:
    data = _json(run(("gh", "issue", "view", "20", "--json", "state,title,url")))
    state = str(data.get("state", ""))
    return Check(
        name="#20 feedback issue",
        status="pass" if state == "OPEN" else "fail",
        detail=f"{state} {data.get('title', '')} {data.get('url', '')}".strip(),
    )


def _social_preview_issue_check(run: Runner) -> Check:
    data = _json(run(("gh", "issue", "view", "23", "--json", "state,title,url")))
    state = str(data.get("state", ""))
    status = "manual" if state == "OPEN" else "pass"
    return Check(
        name="#23 social preview upload",
        status=status,
        detail=f"{state} {data.get('title', '')} {data.get('url', '')}".strip(),
    )


def _open_graph_check(run: Runner) -> Check:
    data = _json(run(("gh", "repo", "view", REPO, "--json", "openGraphImageUrl")))
    image_url = str(data.get("openGraphImageUrl", ""))
    default_like = "opengraph.githubassets.com" in image_url
    status = "manual" if default_like else "pass"
    detail = image_url or "missing openGraphImageUrl"
    return Check(
        name="repository OpenGraph image",
        status=status,
        detail=detail,
    )


def _json(text: str) -> object:
    return json.loads(text)


def _run(command: Sequence[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Show launch readiness status from local git and GitHub.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    checks = collect_launch_status()
    if args.json:
        print(json.dumps([check.__dict__ for check in checks], indent=2))
    else:
        print("Launch status:")
        for check in checks:
            print(f"- {check.status.upper():6} {check.name}: {check.detail}")

    return 1 if any(check.status == "fail" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
