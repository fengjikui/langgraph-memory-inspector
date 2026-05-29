from __future__ import annotations

import json
from typing import Sequence

from scripts import launch_status
from scripts.launch_status import LaunchStatusError, collect_launch_status


def test_launch_status_marks_manual_social_preview_gate() -> None:
    checks = collect_launch_status(_fake_runner)
    by_name = {check.name: check for check in checks}

    assert by_name["local git status"].status == "pass"
    assert by_name["repository visibility"].status == "pass"
    assert by_name["repository discoverability"].status == "pass"
    assert by_name["latest main CI"].status == "pass"
    assert by_name["v0.1.0 release"].status == "pass"
    assert by_name["#20 feedback issue"].status == "pass"
    assert by_name["public roadmap issues"].status == "pass"
    assert by_name["#23 social preview upload"].status == "manual"
    assert by_name["repository OpenGraph image"].status == "manual"


def test_launch_status_reports_probe_failures_without_aborting() -> None:
    checks = collect_launch_status(_flaky_runner)
    by_name = {check.name: check for check in checks}

    assert by_name["local git status"].status == "pass"
    assert by_name["repository visibility"].status == "fail"
    assert "temporary gh failure" in by_name["repository visibility"].detail
    assert by_name["repository discoverability"].status == "pass"
    assert by_name["latest main CI"].status == "pass"
    assert by_name["public roadmap issues"].status == "pass"
    assert by_name["#23 social preview upload"].status == "manual"


def test_launch_status_reports_missing_discoverability_topics() -> None:
    checks = collect_launch_status(_missing_topic_runner)
    by_name = {check.name: check for check in checks}

    assert by_name["repository discoverability"].status == "fail"
    assert "missing topics" in by_name["repository discoverability"].detail
    assert "langchain" in by_name["repository discoverability"].detail


def test_launch_status_reports_missing_roadmap_labels() -> None:
    checks = collect_launch_status(_missing_roadmap_label_runner)
    by_name = {check.name: check for check in checks}

    assert by_name["public roadmap issues"].status == "fail"
    assert "#29 missing labels" in by_name["public roadmap issues"].detail
    assert "good first issue" in by_name["public roadmap issues"].detail


def test_launch_status_retries_transient_gh_failures(monkeypatch) -> None:
    calls = 0

    def fake_run_once(command: Sequence[str]) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LaunchStatusError("unexpected EOF")
        assert command == ("gh", "repo", "view")
        return "{}"

    monkeypatch.setattr(launch_status, "_run_once", fake_run_once)
    monkeypatch.setattr(launch_status.time, "sleep", lambda seconds: None)

    assert launch_status._run(("gh", "repo", "view")) == "{}"
    assert calls == 2


def _fake_runner(command: Sequence[str]) -> str:
    command_text = " ".join(command)
    if command_text == "git status --branch --short":
        return "## main...origin/main\n"
    if command_text.startswith("gh repo view") and "visibility,url" in command_text:
        return json.dumps({"visibility": "PUBLIC", "url": "https://github.com/fengjikui/langgraph-memory-inspector"})
    if command_text.startswith("gh repo view") and "description,repositoryTopics" in command_text:
        return json.dumps(
            {
                "description": "Local-first DevTools for debugging LangGraph checkpoints and agent memory.",
                "repositoryTopics": [
                    {"name": "agent-memory"},
                    {"name": "ai-agents"},
                    {"name": "checkpoints"},
                    {"name": "debugging"},
                    {"name": "developer-tools"},
                    {"name": "langchain"},
                    {"name": "langgraph"},
                    {"name": "llmops"},
                    {"name": "observability"},
                    {"name": "postgres"},
                    {"name": "python"},
                    {"name": "rag"},
                    {"name": "react"},
                    {"name": "sqlite"},
                ],
            }
        )
    if command_text.startswith("gh repo view") and "openGraphImageUrl" in command_text:
        return json.dumps({"openGraphImageUrl": "https://opengraph.githubassets.com/default/fengjikui/langgraph-memory-inspector"})
    if command_text.startswith("gh run list"):
        return json.dumps(
            [
                {
                    "status": "completed",
                    "conclusion": "success",
                    "displayTitle": "Add release smoke gate",
                    "url": "https://github.com/fengjikui/langgraph-memory-inspector/actions/runs/1",
                }
            ]
        )
    if command_text.startswith("gh release view"):
        return json.dumps({"tagName": "v0.1.0", "url": "https://github.com/fengjikui/langgraph-memory-inspector/releases/tag/v0.1.0"})
    if command_text.startswith("gh issue view 20"):
        return json.dumps({"state": "OPEN", "title": "Looking for real LangGraph checkpoint bug patterns", "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/20"})
    if command_text.startswith("gh issue list"):
        return _roadmap_issue_list()
    if command_text.startswith("gh issue view 23"):
        return json.dumps({"state": "OPEN", "title": "Set a custom GitHub social preview image", "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/23"})
    raise AssertionError(f"Unexpected command: {command_text}")


def _flaky_runner(command: Sequence[str]) -> str:
    command_text = " ".join(command)
    if command_text.startswith("gh repo view") and "visibility,url" in command_text:
        raise LaunchStatusError("temporary gh failure")
    return _fake_runner(command)


def _missing_topic_runner(command: Sequence[str]) -> str:
    command_text = " ".join(command)
    if command_text.startswith("gh repo view") and "description,repositoryTopics" in command_text:
        return json.dumps(
            {
                "description": "Local-first DevTools for debugging LangGraph checkpoints and agent memory.",
                "repositoryTopics": [{"name": "langgraph"}],
            }
        )
    return _fake_runner(command)


def _missing_roadmap_label_runner(command: Sequence[str]) -> str:
    command_text = " ".join(command)
    if command_text.startswith("gh issue list"):
        issues = json.loads(_roadmap_issue_list())
        for issue in issues:
            if issue["number"] == 29:
                issue["labels"] = [{"name": "diagnostic"}, {"name": "user-research"}]
        return json.dumps(issues)
    return _fake_runner(command)


def _roadmap_issue_list() -> str:
    return json.dumps(
        [
            {
                "number": 27,
                "title": "Add large-store metadata search for checkpoint timelines",
                "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/27",
                "labels": [
                    {"name": "enhancement"},
                    {"name": "help wanted"},
                    {"name": "user-research"},
                ],
            },
            {
                "number": 28,
                "title": "Collect schema-only evidence for more LangGraph checkpointer variants",
                "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/28",
                "labels": [
                    {"name": "enhancement"},
                    {"name": "help wanted"},
                    {"name": "user-research"},
                ],
            },
            {
                "number": 29,
                "title": "Create a small contributor fixture from a safe checkpoint pattern",
                "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/29",
                "labels": [
                    {"name": "good first issue"},
                    {"name": "diagnostic"},
                    {"name": "user-research"},
                ],
            },
        ]
    )
