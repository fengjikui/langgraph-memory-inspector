from __future__ import annotations

import json
from typing import Sequence

from scripts.launch_status import collect_launch_status


def test_launch_status_marks_manual_social_preview_gate() -> None:
    checks = collect_launch_status(_fake_runner)
    by_name = {check.name: check for check in checks}

    assert by_name["local git status"].status == "pass"
    assert by_name["repository visibility"].status == "pass"
    assert by_name["latest main CI"].status == "pass"
    assert by_name["v0.1.0 release"].status == "pass"
    assert by_name["#20 feedback issue"].status == "pass"
    assert by_name["#23 social preview upload"].status == "manual"
    assert by_name["repository OpenGraph image"].status == "manual"


def _fake_runner(command: Sequence[str]) -> str:
    command_text = " ".join(command)
    if command_text == "git status --branch --short":
        return "## main...origin/main\n"
    if command_text.startswith("gh repo view") and "visibility,url" in command_text:
        return json.dumps({"visibility": "PUBLIC", "url": "https://github.com/fengjikui/langgraph-memory-inspector"})
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
    if command_text.startswith("gh issue view 23"):
        return json.dumps({"state": "OPEN", "title": "Set a custom GitHub social preview image", "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/23"})
    raise AssertionError(f"Unexpected command: {command_text}")
