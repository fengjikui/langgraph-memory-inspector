from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from examples.relocation_policy_agent.run_demo import THREAD_ID, build_graph
from lgmi.checkpoint_reader import SQLiteCheckpointReader
from lgmi.cli import main
from lgmi.export_bundle import build_debug_bundle, export_debug_bundle


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
    assert "conflicting_residence_memory" in output
    assert list(output_dir.glob("lgmi-debug-*.json"))


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
