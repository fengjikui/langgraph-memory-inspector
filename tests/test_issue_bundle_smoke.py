from __future__ import annotations

from pathlib import Path

from scripts.issue_bundle_smoke import run_issue_bundle_smoke


def test_issue_bundle_smoke_proves_public_feedback_path(tmp_path: Path) -> None:
    report = run_issue_bundle_smoke(tmp_path / "exports")

    assert report["passed"] is True
    assert report["redaction_mode"] == "redacted"
    assert report["redaction_count"] > 0
    assert "conflicting_residence_memory" in report["diagnostic_ids"]
    assert Path(report["bundle_path"]).exists()
