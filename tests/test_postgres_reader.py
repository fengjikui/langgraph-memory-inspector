from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from examples.relocation_policy_agent.run_demo import THREAD_ID, build_graph
from lgmi.postgres_reader import PostgresCheckpointReader


class FakeCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[tuple[Any, tuple[Any, ...] | None]] = []

    def execute(self, query: Any, params: tuple[Any, ...] | None = None) -> None:
        self.calls.append((query, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


def test_postgres_reader_rejects_unsafe_schema_identifier() -> None:
    with pytest.raises(ValueError, match="Unsafe Postgres schema"):
        PostgresCheckpointReader("postgresql://unused", schema="public;drop schema public")


def test_postgres_reader_hydrates_checkpoint_blob_channel() -> None:
    reader = PostgresCheckpointReader("postgresql://unused")
    blob_type, blob = reader._serde.dumps_typed(
        [{"type": "residence_city", "value": "Hangzhou"}]
    )
    cursor = FakeCursor(
        [
            {
                "channel": "memory_events",
                "version": "0001",
                "type": blob_type,
                "blob": blob,
            }
        ]
    )

    item = reader._checkpoint_row_to_dict(
        cursor,
        {
            "thread_id": "thread-1",
            "checkpoint_ns": "",
            "checkpoint_id": "checkpoint-2",
            "parent_checkpoint_id": "checkpoint-1",
            "type": "jsonb",
            "checkpoint": {
                "id": "checkpoint-2",
                "ts": "2026-05-29T10:00:00+08:00",
                "channel_values": {"memory_events": True, "selected_city": "Shanghai"},
                "channel_versions": {"memory_events": "0001"},
                "updated_channels": ["memory_events"],
            },
            "metadata": {"source": "loop", "step": 2},
        },
        include_checkpoint=True,
    )

    state = item["checkpoint"]["value"]["channel_values"]
    assert state["memory_events"] == [{"type": "residence_city", "value": "Hangzhou"}]
    assert state["selected_city"] == "Shanghai"
    assert item["updated_channels"] == ["memory_events"]
    assert item["source"] == "loop"


def test_postgres_reader_decodes_checkpoint_write_blob() -> None:
    reader = PostgresCheckpointReader("postgresql://unused")
    blob_type, blob = reader._serde.dumps_typed({"selected_city": "Shanghai"})

    write = reader._write_row_to_dict(
        {
            "thread_id": "thread-1",
            "checkpoint_ns": "",
            "checkpoint_id": "checkpoint-1",
            "task_id": "task-1",
            "task_path": "retrieve_policy",
            "idx": 0,
            "channel": "selected_city",
            "type": blob_type,
            "blob": blob,
        }
    )

    assert write["id"] == "checkpoint-1:task-1:0"
    assert write["task_path"] == "retrieve_policy"
    assert write["channel"] == "selected_city"
    assert write["value"]["decoded"] is True
    assert write["value"]["value"] == {"selected_city": "Shanghai"}


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("LGMI_POSTGRES_TEST_DSN"),
    reason="Set LGMI_POSTGRES_TEST_DSN to run the real PostgresSaver integration test.",
)
def test_postgres_reader_integrates_with_real_postgres_saver() -> None:
    psycopg = pytest.importorskip("psycopg")
    pytest.importorskip("langgraph.checkpoint.postgres")
    from psycopg import sql
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres import PostgresSaver

    dsn = os.environ["LGMI_POSTGRES_TEST_DSN"]
    schema = f"lgmi_test_{uuid.uuid4().hex}"
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as admin:
        admin.execute(sql.SQL("create schema {}").format(sql.Identifier(schema)))
    try:
        with psycopg.connect(
            dsn,
            autocommit=True,
            row_factory=dict_row,
            options=f"-c search_path={schema}",
        ) as conn:
            saver = PostgresSaver(conn)
            saver.setup()
            app = build_graph(use_llm=False).compile(checkpointer=saver)
            state: dict[str, Any] = {
                "messages": [],
                "memory_events": [],
                "retrieved_docs": [],
                "diagnostics": [],
                "selected_city": None,
            }
            config = {"configurable": {"thread_id": THREAD_ID, "checkpoint_ns": ""}}
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

        reader = PostgresCheckpointReader(dsn, schema=schema)
        assert reader.summary()["checkpoint_count"] > 0
        checkpoints = reader.list_checkpoints(THREAD_ID)
        assert checkpoints

        for checkpoint in checkpoints:
            checkpoint_id = checkpoint["checkpoint_id"]
            detail = reader.get_checkpoint(THREAD_ID, checkpoint_id)
            assert detail is not None
            checkpoint_value = detail["checkpoint"]["value"]
            state = checkpoint_value["channel_values"]
            if (
                "memory_events" in checkpoint_value.get("updated_channels", [])
                and len(state.get("memory_events", [])) > 1
            ):
                assert state["memory_events"][-1]["value"] == "Hangzhou"
                writes = reader.list_writes(THREAD_ID, checkpoint_id)
                assert "memory_events" in {write["channel"] for write in writes}
                assert all(write["value"]["decoded"] for write in writes)
                break
        else:
            raise AssertionError("No hydrated Postgres checkpoint with Hangzhou memory_events found")
    finally:
        with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as admin:
            admin.execute(sql.SQL("drop schema if exists {} cascade").format(sql.Identifier(schema)))
