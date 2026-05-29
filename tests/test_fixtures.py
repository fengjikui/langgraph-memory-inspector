from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lgmi.analysis import run_diagnostics


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
ALLOWED_SOURCE_SAFETY = {"synthetic", "redacted", "schema_only"}
ALLOWED_BACKENDS = {"sqlite", "postgres", "debug_bundle", "synthetic_json"}
MAX_PUBLIC_FIXTURE_BYTES = 2 * 1024 * 1024
SUSPICIOUS_PRIVATE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),
    re.compile(r"\b1[3-9]\d{9}\b"),
]


def test_synthetic_fixtures_produce_expected_diagnostics() -> None:
    fixture_paths = sorted((FIXTURE_ROOT / "synthetic").glob("*.json"))
    assert fixture_paths

    for path in fixture_paths:
        fixture = _load_fixture(path)
        diagnostics = run_diagnostics(
            fixture.get("state"),
            writes=fixture.get("writes"),
            checkpoints=fixture.get("checkpoints"),
        )
        diagnostic_ids = {item["id"] for item in diagnostics}
        assert set(fixture["expected_diagnostics"]) <= diagnostic_ids


def test_public_fixtures_have_safe_metadata_and_content() -> None:
    fixture_paths = sorted(FIXTURE_ROOT.glob("*/*.json"))
    assert fixture_paths

    for path in fixture_paths:
        fixture = _load_fixture(path)
        assert path.stat().st_size <= MAX_PUBLIC_FIXTURE_BYTES
        assert fixture["fixture_id"]
        assert fixture["source_safety"] in ALLOWED_SOURCE_SAFETY
        assert fixture["backend"] in ALLOWED_BACKENDS
        assert fixture["state_channels"]
        assert fixture["bug_pattern_tags"]
        assert fixture["expected_diagnostics"]
        _assert_no_suspicious_private_values(path)


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_suspicious_private_values(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in SUSPICIOUS_PRIVATE_PATTERNS:
        assert not pattern.search(text), f"{path} contains suspicious private data"
