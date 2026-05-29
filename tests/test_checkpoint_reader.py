from __future__ import annotations

import sqlite3
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
