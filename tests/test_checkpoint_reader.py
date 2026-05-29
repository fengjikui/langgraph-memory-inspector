from __future__ import annotations

import sqlite3
import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from examples.relocation_policy_agent.run_demo import THREAD_ID, build_graph
from lgmi.checkpoint_reader import SQLiteCheckpointReader


def test_reader_lists_demo_threads_checkpoints_and_writes(tmp_path: Path) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)

    summary = reader.summary()
    assert summary["thread_count"] == 1
    assert summary["checkpoint_count"] > 0
    assert summary["write_count"] > 0

    threads = reader.list_threads()
    assert [thread["thread_id"] for thread in threads] == [THREAD_ID]

    checkpoints = reader.list_checkpoints(THREAD_ID)
    assert checkpoints
    assert all(checkpoint["checkpoint"]["byte_size"] > 0 for checkpoint in checkpoints)

    checkpoint_id = checkpoints[-1]["checkpoint_id"]
    checkpoint = reader.get_checkpoint(THREAD_ID, checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["checkpoint"]["decoded"] is True
    assert "channel_values" in checkpoint["checkpoint"]["value"]

    writes = []
    for listed_checkpoint in checkpoints:
        writes = reader.list_writes(THREAD_ID, listed_checkpoint["checkpoint_id"])
        if writes:
            break
    assert writes
    assert {write["channel"] for write in writes}


def test_reader_lists_writes_that_created_checkpoint_snapshot(tmp_path: Path) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)

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
            writes = reader.list_writes(THREAD_ID, checkpoint_id)
            assert "memory_events" in {write["channel"] for write in writes}
            break
    else:
        raise AssertionError("No checkpoint with a second memory_events write found")


def test_reader_paginates_and_filters_checkpoints(tmp_path: Path) -> None:
    db_path = _write_demo_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)

    total_count = reader.count_checkpoints(THREAD_ID)
    page = reader.list_checkpoints(THREAD_ID, limit=3, offset=2)

    assert total_count > 3
    assert len(page) == 3
    assert page[0]["checkpoint_id"] == reader.list_checkpoints(THREAD_ID)[2]["checkpoint_id"]

    diagnostic_count = reader.count_checkpoints(THREAD_ID, diagnostic=True)
    diagnostic_page = reader.list_checkpoints(THREAD_ID, diagnostic=True)
    assert diagnostic_count == len(diagnostic_page)
    assert diagnostic_count > 0

    memory_event_page = reader.list_checkpoints(THREAD_ID, changed_path="state.memory_events")
    assert memory_event_page
    assert all("memory_events" in item.get("updated_channels", []) for item in memory_event_page)


def test_reader_summarizes_bad_blobs_without_crashing(tmp_path: Path) -> None:
    db_path = tmp_path / "bad.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table checkpoints (
                thread_id text,
                checkpoint_ns text,
                checkpoint_id text,
                parent_checkpoint_id text,
                type text,
                checkpoint blob,
                metadata blob
            );
            create table writes (
                thread_id text,
                checkpoint_ns text,
                checkpoint_id text,
                task_id text,
                idx integer,
                channel text,
                type text,
                value blob
            );
            """
        )
        conn.execute(
            """
            insert into checkpoints values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "thread-bad",
                "",
                "checkpoint-bad",
                None,
                "msgpack",
                b"\xc1",
                b'{"source": "test", "step": 1, "parents": {}}',
            ),
        )
        conn.execute(
            """
            insert into writes values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "thread-bad",
                "",
                "checkpoint-bad",
                "task-bad",
                0,
                "bad_channel",
                "msgpack",
                b"\xc1",
            ),
        )

    reader = SQLiteCheckpointReader(db_path)
    checkpoint = reader.get_checkpoint("thread-bad", "checkpoint-bad")
    assert checkpoint is not None
    assert checkpoint["checkpoint"]["decoded"] is False
    assert checkpoint["checkpoint"]["byte_size"] == len(b"\xc1")
    assert checkpoint["checkpoint"]["preview"]

    writes = reader.list_writes("thread-bad", "checkpoint-bad")
    assert writes[0]["value"]["decoded"] is False
    assert writes[0]["value"]["preview"]


def test_reader_filters_multi_namespace_checkpoint_store(tmp_path: Path) -> None:
    db_path = _write_multi_namespace_db(tmp_path)
    reader = SQLiteCheckpointReader(db_path)

    summary = reader.summary()
    assert summary["checkpoint_namespaces"] == ["ns-a", "ns-b"]

    threads = reader.list_threads()
    assert threads[0]["namespace_count"] == 2
    assert [item["checkpoint_ns"] for item in threads[0]["checkpoint_namespaces"]] == ["ns-a", "ns-b"]

    assert [item["checkpoint_ns"] for item in reader.list_checkpoints("thread-1", "ns-a")] == ["ns-a"]
    assert [item["checkpoint_ns"] for item in reader.list_checkpoints("thread-1", "ns-b")] == ["ns-b"]

    checkpoint = reader.get_checkpoint("thread-1", "checkpoint-1", "ns-b")
    assert checkpoint is not None
    state = checkpoint["checkpoint"]["value"]["channel_values"]
    assert state["selected_city"] == "Hangzhou"

    writes = reader.list_writes("thread-1", "checkpoint-1", "ns-b")
    assert [write["checkpoint_ns"] for write in writes] == ["ns-b"]
    assert writes[0]["value"]["value"] == "Hangzhou"


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


def _write_multi_namespace_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "multi_namespace.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table checkpoints (
                thread_id text,
                checkpoint_ns text,
                checkpoint_id text,
                parent_checkpoint_id text,
                type text,
                checkpoint blob,
                metadata blob
            );
            create table writes (
                thread_id text,
                checkpoint_ns text,
                checkpoint_id text,
                task_id text,
                idx integer,
                channel text,
                type text,
                value blob
            );
            """
        )
        for namespace, city in (("ns-a", "Shanghai"), ("ns-b", "Hangzhou")):
            checkpoint = {
                "channel_values": {"selected_city": city},
                "updated_channels": ["selected_city"],
                "ts": f"2026-05-29T10:00:00+08:00-{namespace}",
            }
            conn.execute(
                "insert into checkpoints values (?, ?, ?, ?, ?, ?, ?)",
                (
                    "thread-1",
                    namespace,
                    "checkpoint-1",
                    None,
                    "json",
                    json.dumps(checkpoint).encode("utf-8"),
                    b'{"source": "test", "step": 1, "parents": {}}',
                ),
            )
            conn.execute(
                "insert into writes values (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "thread-1",
                    namespace,
                    "checkpoint-1",
                    f"task-{namespace}",
                    0,
                    "selected_city",
                    "json",
                    json.dumps(city).encode("utf-8"),
                ),
            )
    return db_path
