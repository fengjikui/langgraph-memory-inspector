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


class LaunchStatusError(RuntimeError):
    """A launch status probe failed but should not abort the full report."""


Runner = Callable[[Sequence[str]], str]


def collect_launch_status(runner: Runner | None = None) -> list[Check]:
    """Collect local and GitHub launch gates for the first public posting."""
    run = runner or _run
    probes = [
        ("local git status", _git_status_check),
        ("repository visibility", _repo_visibility_check),
        ("latest main CI", _latest_ci_check),
        ("v0.1.0 release", _release_check),
        ("#20 feedback issue", _feedback_issue_check),
        ("#23 social preview upload", _social_preview_issue_check),
        ("repository OpenGraph image", _open_graph_check),
    ]
    return [_safe_check(name, probe, run) for name, probe in probes]


def _safe_check(name: str, probe: Callable[[Runner], Check], run: Runner) -> Check:
    try:
        return probe(run)
    except (LaunchStatusError, json.JSONDecodeError, KeyError, IndexError) as exc:
        return Check(name=name, status="fail", detail=str(exc))


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
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LaunchStatusError(f"invalid JSON from command: {exc}") from exc


def _run(command: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        command_text = " ".join(command)
        if detail:
            raise LaunchStatusError(f"`{command_text}` failed: {detail}") from exc
        raise LaunchStatusError(f"`{command_text}` failed with exit code {exc.returncode}") from exc
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
