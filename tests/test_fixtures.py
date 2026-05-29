from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lgmi.analysis import run_diagnostics


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
MATRIX_PATH = Path(__file__).resolve().parents[1] / "docs" / "diagnostic_matrix.md"
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


def test_fixture_metadata_is_listed_in_diagnostic_matrix() -> None:
    rows = _parse_diagnostic_matrix()
    fixture_paths = sorted(FIXTURE_ROOT.glob("*/*.json"))
    assert fixture_paths

    for path in fixture_paths:
        fixture = _load_fixture(path)
        for diagnostic_id in fixture["expected_diagnostics"]:
            matches = [
                row
                for row in rows
                if row["Diagnostic ID"] == diagnostic_id
                and row["Fixture ID"] == fixture["fixture_id"]
            ]
            assert matches, f"{fixture['fixture_id']} / {diagnostic_id} is missing from diagnostic matrix"
            row = matches[0]
            assert row["Backend Shape"] == fixture["backend"]
            assert row["Source Safety"] == fixture["source_safety"]
            for channel in fixture["state_channels"]:
                assert channel in row["State Channels"]
            assert row["Validation Command"].startswith("uv run ")


def test_diagnostic_matrix_tracks_demo_and_unit_only_gaps() -> None:
    rows = _parse_diagnostic_matrix()
    by_diagnostic = {row["Diagnostic ID"]: row for row in rows}

    assert by_diagnostic["conflicting_residence_memory"]["Fixture ID"] == "relocation_demo_checkpoint_db"
    assert by_diagnostic["stale_selected_city"]["Fixture ID"] == "relocation_demo_checkpoint_db"
    assert by_diagnostic["reducer_append_duplicate_state"]["Fixture ID"] == (
        "synthetic_reducer_append_duplicate_memory_v1"
    )
    assert by_diagnostic["unexpected_parent_checkpoint"]["Fixture ID"] == (
        "synthetic_unexpected_parent_checkpoint_v1"
    )
    assert by_diagnostic["repeated_retrieved_context"]["Fixture ID"] == (
        "synthetic_repeated_retrieved_context_v1"
    )
    assert all("Unit-only coverage" not in row["Status"] for row in rows)


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_suspicious_private_values(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in SUSPICIOUS_PRIVATE_PATTERNS:
        assert not pattern.search(text), f"{path} contains suspicious private data"


def _parse_diagnostic_matrix() -> list[dict[str, str]]:
    lines = MATRIX_PATH.read_text(encoding="utf-8").splitlines()
    header_index = next(
        index
        for index, line in enumerate(lines)
        if line.startswith("| Diagnostic ID | Fixture ID | Backend Shape |")
    )
    headers = _split_markdown_row(lines[header_index])
    rows: list[dict[str, str]] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        values = _split_markdown_row(line)
        row = {
            header: value.strip().strip("`")
            for header, value in zip(headers, values, strict=True)
        }
        rows.append(row)
    return rows


def _split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]
