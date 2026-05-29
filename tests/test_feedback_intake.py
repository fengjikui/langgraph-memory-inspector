from __future__ import annotations

import json
from typing import Sequence

from scripts.feedback_intake import collect_feedback_intake, render_markdown


def test_feedback_intake_classifies_safe_checkpoint_pattern() -> None:
    report = collect_feedback_intake(42, runner=_fake_issue_runner)

    assert report.title == "Stale retrieved context in PostgresSaver"
    assert report.likely_patterns == ["stale_retrieved_context", "production_store_safety"]
    assert report.likely_backends == ["postgres"]
    assert report.safe_evidence == ["redacted_debug_bundle", "schema_only_snapshot"]
    assert report.risk_flags == []
    assert report.comment_count == 1


def test_feedback_intake_markdown_keeps_privacy_and_matrix_steps() -> None:
    markdown = render_markdown(collect_feedback_intake(42, runner=_fake_issue_runner))

    assert "# Feedback Intake #42" in markdown
    assert "docs/diagnostic_matrix.md" in markdown
    assert "Please do not attach raw production checkpoint data." in markdown
    assert "redacted bundle, synthetic fixture, or schema-only snapshot" in markdown


def test_feedback_intake_flags_raw_or_secret_language() -> None:
    report = collect_feedback_intake(7, runner=_risky_issue_runner)

    assert "raw production" in report.risk_flags
    assert "token" in report.risk_flags


def _fake_issue_runner(command: Sequence[str]) -> str:
    assert command[:3] == ("gh", "issue", "view")
    return json.dumps(
        {
            "title": "Stale retrieved context in PostgresSaver",
            "state": "OPEN",
            "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/42",
            "body": (
                "The RAG answer reused retrieved_docs from an older checkpoint. "
                "Backend is PostgresSaver. I can share a redacted debug bundle "
                "and a schema-only snapshot."
            ),
            "comments": [{"body": "This matters for a production large store."}],
        }
    )


def _risky_issue_runner(command: Sequence[str]) -> str:
    assert command[:3] == ("gh", "issue", "view")
    return json.dumps(
        {
            "title": "Raw production SQLite checkpoint includes token",
            "state": "OPEN",
            "url": "https://github.com/fengjikui/langgraph-memory-inspector/issues/7",
            "body": "I attached raw production data and there may be a token in it.",
            "comments": [],
        }
    )
