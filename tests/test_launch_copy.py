from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_launch_copy import validate_launch_copy


def test_public_launch_copy_keeps_feedback_and_privacy_guardrails() -> None:
    results = validate_launch_copy()

    assert {item["status"] for item in results} == {"ok"}
    assert len(results) == 3


def test_launch_copy_rejects_missing_feedback_issue(tmp_path: Path) -> None:
    path = tmp_path / "launch.md"
    path.write_text(
        "\n".join(
            [
                "https://github.com/fengjikui/langgraph-memory-inspector",
                "docs/fixture_policy.md",
                "redacted evidence only",
                "audit-debug-bundle",
                "no raw production data",
                "real bug patterns",
                "not asking for stars",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="feedback_issue"):
        validate_launch_copy((path,))


def test_launch_copy_rejects_raw_checkpoint_requests(tmp_path: Path) -> None:
    path = tmp_path / "launch.md"
    path.write_text(
        "\n".join(
            [
                "https://github.com/fengjikui/langgraph-memory-inspector",
                "https://github.com/fengjikui/langgraph-memory-inspector/issues/20",
                "docs/fixture_policy.md",
                "redacted evidence only",
                "audit-debug-bundle",
                "no raw production data",
                "real bug patterns",
                "not asking for stars",
                "please share raw production checkpoint data",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden"):
        validate_launch_copy((path,))
