from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from examples.relocation_policy_agent.run_demo import THREAD_ID, build_graph
from lgmi.checkpoint_reader import SQLiteCheckpointReader
from lgmi.cli import main
from lgmi.bundle_audit import audit_debug_bundle
from lgmi.export_bundle import (
    REDACTION_PLACEHOLDER,
    _redact_string_patterns,
    build_debug_bundle,
    export_debug_bundle,
)


def test_debug_bundle_exports_shareable_stale_memory_evidence(tmp_path: Path) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)
    generated_at = dt.datetime(2026, 5, 29, 12, 0, tzinfo=dt.UTC)

    result = export_debug_bundle(
        reader,
        thread_id=THREAD_ID,
        checkpoint_id=checkpoint_id,
        output_dir=tmp_path / "exports",
        generated_at=generated_at,
    )

    path = Path(result["path"])
    assert path.exists()
    assert result["file_size_bytes"] == path.stat().st_size
    assert path.name.startswith(f"lgmi-debug-{THREAD_ID}-")

    bundle = json.loads(path.read_text(encoding="utf-8"))
    state = bundle["selected_checkpoint"]["checkpoint"]["value"]["channel_values"]
    diagnostic_ids = {item["id"] for item in bundle["diagnostics"]}

    assert bundle["schema_version"] == 1
    assert bundle["generated_at"] == "2026-05-29T12:00:00Z"
    assert bundle["thread"]["thread_id"] == THREAD_ID
    assert bundle["thread"]["checkpoint_id"] == checkpoint_id
    assert "conflicting_residence_memory" in diagnostic_ids
    assert state["memory_events"][-1]["value"] == "Hangzhou"
    assert "memory_events" in {write["channel"] for write in bundle["writes"]}
    assert any("state.memory_events" in note for note in bundle["reproduction_notes"])


def test_build_debug_bundle_rejects_unknown_checkpoint(tmp_path: Path) -> None:
    reader = SQLiteCheckpointReader(_write_demo_db(tmp_path))

    try:
        build_debug_bundle(reader, thread_id=THREAD_ID, checkpoint_id="missing")
    except ValueError as exc:
        assert "Checkpoint not found: missing" in str(exc)
    else:
        raise AssertionError("Expected missing checkpoint to raise ValueError")


def test_redacted_debug_bundle_masks_private_fields_without_mutating_db(tmp_path: Path) -> None:
    db_path = _write_demo_db(tmp_path)
    before_hash = _sha256(db_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)

    result = export_debug_bundle(
        reader,
        thread_id=THREAD_ID,
        checkpoint_id=checkpoint_id,
        output_dir=tmp_path / "exports",
        redaction_mode="redacted",
        redact_paths=["selected_checkpoint.checkpoint.value.channel_values.selected_city"],
    )

    assert _sha256(db_path) == before_hash
    assert result["redaction_mode"] == "redacted"
    assert result["redaction_count"] > 0
    assert "selected_checkpoint.checkpoint.value.channel_values.selected_city" in result["redacted_paths"]

    bundle = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    state = bundle["selected_checkpoint"]["checkpoint"]["value"]["channel_values"]
    serialized = json.dumps(bundle, ensure_ascii=False)

    assert bundle["privacy"]["redaction_mode"] == "redacted"
    assert bundle["generated_at"] != "[REDACTED]"
    assert bundle["checkpoint_id"] == checkpoint_id
    assert bundle["thread"]["checkpoint_id"] == checkpoint_id
    assert bundle["selected_checkpoint"]["checkpoint_id"] == checkpoint_id
    assert state["selected_city"] == "[REDACTED]"
    assert state["memory_events"][-1]["value"] == "Hangzhou"
    assert state["memory_events"][-1]["evidence"] == "[REDACTED]"
    assert "I moved to Hangzhou last week" not in serialized


def test_redacted_debug_bundle_can_keep_explicit_paths(tmp_path: Path) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)

    bundle = build_debug_bundle(
        reader,
        thread_id=THREAD_ID,
        checkpoint_id=checkpoint_id,
        redaction_mode="redacted",
        keep_paths=["selected_checkpoint.checkpoint.value.channel_values.memory_events"],
    )

    state = bundle["selected_checkpoint"]["checkpoint"]["value"]["channel_values"]
    assert state["memory_events"][-1]["evidence"] == "I moved to Hangzhou last week. Please remember that."
    assert not any(
        path.startswith("selected_checkpoint.checkpoint.value.channel_values.memory_events")
        for path in bundle["privacy"]["redacted_paths"]
    )


def test_cli_export_debug_bundle_reports_path_and_size(tmp_path: Path, capsys) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)
    output_dir = tmp_path / "cli-exports"

    exit_code = main(
        [
            "export-debug-bundle",
            str(db_path),
            "--thread-id",
            THREAD_ID,
            "--checkpoint-id",
            checkpoint_id,
            "--output-dir",
            str(output_dir),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Debug bundle:" in output
    assert "File size:" in output
    assert "Redaction: raw" in output
    assert "conflicting_residence_memory" in output
    assert list(output_dir.glob("lgmi-debug-*.json"))


def test_cli_export_debug_bundle_can_redact(tmp_path: Path, capsys) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)
    output_dir = tmp_path / "cli-redacted-exports"

    exit_code = main(
        [
            "export-debug-bundle",
            str(db_path),
            "--thread-id",
            THREAD_ID,
            "--checkpoint-id",
            checkpoint_id,
            "--output-dir",
            str(output_dir),
            "--redact",
        ]
    )

    output = capsys.readouterr().out
    bundle_path = next(output_dir.glob("lgmi-debug-*.json"))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Redaction: redacted" in output
    assert bundle["privacy"]["redaction_mode"] == "redacted"


def test_string_redaction_preserves_structural_ids_and_timestamps() -> None:
    checkpoint_id = "1f15b739-6741-66e0-8007-516937504e51"
    timestamp = "2026-05-29T15:32:56Z"

    assert _redact_string_patterns(checkpoint_id) == checkpoint_id
    assert _redact_string_patterns(timestamp) == timestamp
    assert _redact_string_patterns("Call +1 (555) 123-4567") == f"Call {REDACTION_PLACEHOLDER}"


def test_cli_export_debug_bundle_issue_report_defaults_to_redacted(tmp_path: Path, capsys) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)
    output_dir = tmp_path / "cli-issue-exports"

    exit_code = main(
        [
            "export-debug-bundle",
            str(db_path),
            "--thread-id",
            THREAD_ID,
            "--checkpoint-id",
            checkpoint_id,
            "--output-dir",
            str(output_dir),
            "--issue",
        ]
    )

    output = capsys.readouterr().out
    bundle_path = next(output_dir.glob("lgmi-debug-*.json"))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "### LangGraph Memory Inspector debug bundle" in output
    assert "- Redaction mode: `redacted`" in output
    assert "<summary>Redacted path samples</summary>" in output
    assert "more path(s) listed in the generated JSON bundle" in output
    assert "Privacy note:" in output
    assert str(output_dir) not in output
    assert "I moved to Hangzhou last week" not in json.dumps(bundle)
    assert bundle["privacy"]["redaction_mode"] == "redacted"


def test_cli_export_debug_bundle_issue_report_rejects_raw_mode(tmp_path: Path, capsys) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)

    exit_code = main(
        [
            "export-debug-bundle",
            str(db_path),
            "--thread-id",
            THREAD_ID,
            "--checkpoint-id",
            checkpoint_id,
            "--issue",
            "--redaction-mode",
            "raw",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "`--issue` is for public reports" in captured.err


def test_cli_export_debug_bundle_reports_missing_checkpoint_without_traceback(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = _write_demo_db(tmp_path)

    exit_code = main(
        [
            "export-debug-bundle",
            str(db_path),
            "--thread-id",
            THREAD_ID,
            "--checkpoint-id",
            "missing-checkpoint",
            "--issue",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Could not export debug bundle: Checkpoint not found: missing-checkpoint" in captured.err
    assert "Traceback" not in captured.err


def test_audit_debug_bundle_accepts_redacted_issue_bundle(tmp_path: Path, capsys) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)
    result = export_debug_bundle(
        reader,
        thread_id=THREAD_ID,
        checkpoint_id=checkpoint_id,
        output_dir=tmp_path / "exports",
        redaction_mode="redacted",
    )

    report = audit_debug_bundle(result["path"])
    assert report["safe_to_share"] is True
    assert {check["status"] for check in report["checks"]} <= {"OK", "WARN"}

    exit_code = main(["audit-debug-bundle", result["path"]])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "debug bundle audit" in output
    assert "no automatic blocker found" in output


def test_audit_debug_bundle_rejects_raw_bundle(tmp_path: Path) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)
    checkpoint_id = _checkpoint_with_second_memory_write(reader)
    result = export_debug_bundle(
        reader,
        thread_id=THREAD_ID,
        checkpoint_id=checkpoint_id,
        output_dir=tmp_path / "exports",
        redaction_mode="raw",
    )

    report = audit_debug_bundle(result["path"])
    assert report["safe_to_share"] is False
    assert any(
        check["name"] == "Redaction mode" and check["status"] == "ERROR"
        for check in report["checks"]
    )


def test_audit_debug_bundle_rejects_obvious_private_values(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "privacy": {"redaction_mode": "redacted", "redaction_count": 1},
                "thread": {},
                "selected_checkpoint": {},
                "diagnostics": [],
                "leak": "contact me at private@example.com",
            }
        ),
        encoding="utf-8",
    )

    report = audit_debug_bundle(path)
    assert report["safe_to_share"] is False
    assert any(
        check["name"] == "Suspicious private values" and check["status"] == "ERROR"
        for check in report["checks"]
    )


def _write_demo_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "checkpoints.sqlite"
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        checkpointer = SqliteSaver(conn)
        app = build_graph(use_llm=False).compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": THREAD_ID}}
        state = {
            "messages": [],
            "memory_events": [],
            "retrieved_docs": [],
            "diagnostics": [],
            "selected_city": None,
        }
        for user_text in (
            "I live in Shanghai and want help tracking local benefits.",
            "I moved to Hangzhou last week. Please remember that.",
        ):
            state["messages"] = [HumanMessage(content=user_text)]
            output = app.invoke(state, config=config)
            state = {
                "messages": output["messages"],
                "memory_events": output.get("memory_events", []),
                "retrieved_docs": output.get("retrieved_docs", []),
                "diagnostics": output.get("diagnostics", []),
                "selected_city": output.get("selected_city"),
            }
        assert any(isinstance(message, AIMessage) for message in state["messages"])
    finally:
        conn.close()
    return db_path


def _checkpoint_with_second_memory_write(reader: SQLiteCheckpointReader) -> str:
    for listed_checkpoint in reader.list_checkpoints(THREAD_ID):
        checkpoint_id = listed_checkpoint["checkpoint_id"]
        checkpoint = reader.get_checkpoint(THREAD_ID, checkpoint_id)
        assert checkpoint is not None
        value = checkpoint["checkpoint"]["value"]
        state = value["channel_values"]
        if (
            "memory_events" in value.get("updated_channels", [])
            and len(state.get("memory_events", [])) > 1
        ):
            return str(checkpoint_id)
    raise AssertionError("No checkpoint with a second memory_events write found")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
