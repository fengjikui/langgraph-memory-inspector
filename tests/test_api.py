from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from lgmi.api import create_app


class FakeCheckpointReader:
    def summary(self) -> dict[str, Any]:
        return {
            "db_path": "fake://checkpoint-store",
            "checkpoint_count": 1,
            "write_count": 1,
            "thread_count": 1,
            "diagnostics_count": 0,
        }

    def list_threads(self) -> list[dict[str, Any]]:
        return [
            {
                "thread_id": "thread-1",
                "checkpoint_count": 1,
                "latest_checkpoint": {"checkpoint_id": "checkpoint-1"},
            }
        ]

    def list_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        assert thread_id == "thread-1"
        return [{"checkpoint_id": "checkpoint-1", "checkpoint": {"preview": "{}"}}]

    def get_checkpoint(self, thread_id: str, checkpoint_id: str) -> dict[str, Any] | None:
        assert thread_id == "thread-1"
        assert checkpoint_id == "checkpoint-1"
        return {
            "checkpoint_id": checkpoint_id,
            "checkpoint": {"value": {"channel_values": {"selected_city": "Hangzhou"}}},
        }

    def list_writes(self, thread_id: str, checkpoint_id: str) -> list[dict[str, Any]]:
        assert thread_id == "thread-1"
        assert checkpoint_id == "checkpoint-1"
        return [{"channel": "selected_city", "value": {"decoded": True, "value": "Hangzhou"}}]


def test_api_accepts_checkpoint_reader_adapter() -> None:
    client = TestClient(create_app(FakeCheckpointReader()))

    assert client.get("/api/summary").json()["thread_count"] == 1
    assert client.get("/api/threads").json()[0]["thread_id"] == "thread-1"
    assert client.get("/api/threads/thread-1/checkpoints").json()[0]["checkpoint_id"] == "checkpoint-1"
    assert (
        client.get("/api/threads/thread-1/checkpoints/checkpoint-1").json()["checkpoint"]["value"]["channel_values"][
            "selected_city"
        ]
        == "Hangzhou"
    )
    assert client.get("/api/threads/thread-1/checkpoints/checkpoint-1/writes").json()[0]["channel"] == "selected_city"
