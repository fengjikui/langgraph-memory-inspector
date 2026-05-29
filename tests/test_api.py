from __future__ import annotations

from pathlib import Path
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

    def list_checkpoints(
        self,
        thread_id: str,
        checkpoint_ns: str | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
        diagnostic: bool | None = None,
        changed_path: str | None = None,
    ) -> list[dict[str, Any]]:
        assert thread_id == "thread-1"
        assert checkpoint_ns in {None, "ns-a"}
        rows = [
            {
                "checkpoint_id": f"checkpoint-{index}",
                "checkpoint_ns": checkpoint_ns or "",
                "updated_channels": ["memory_events"] if index == 3 else ["selected_city"],
                "checkpoint": {"preview": "{}"},
            }
            for index in range(1, 7)
        ]
        if diagnostic is True:
            rows = [rows[2], rows[4]]
        if changed_path == "state.memory_events":
            rows = [row for row in rows if "memory_events" in row["updated_channels"]]
        if limit is None:
            return rows[offset:]
        return rows[offset : offset + limit]

    def count_checkpoints(
        self,
        thread_id: str,
        checkpoint_ns: str | None = None,
        *,
        diagnostic: bool | None = None,
        changed_path: str | None = None,
    ) -> int:
        return len(
            self.list_checkpoints(
                thread_id,
                checkpoint_ns,
                diagnostic=diagnostic,
                changed_path=changed_path,
            )
        )

    def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> dict[str, Any] | None:
        assert thread_id == "thread-1"
        assert checkpoint_id in {f"checkpoint-{index}" for index in range(1, 7)}
        assert checkpoint_ns in {None, "ns-a"}
        memory_events = [
            {"type": "residence_city", "value": "Shanghai", "source": "extract_profile"}
        ]
        selected_city = "Hangzhou" if checkpoint_id == "checkpoint-1" else "Shanghai"
        diagnostics: list[str] = []
        updated_channels = ["selected_city"]
        if checkpoint_id in {"checkpoint-3", "checkpoint-4", "checkpoint-5", "checkpoint-6"}:
            memory_events.append(
                {"type": "residence_city", "value": "Hangzhou", "source": "extract_profile"}
            )
            diagnostics = ["conflicting_residence_memory"]
            updated_channels = ["memory_events"] if checkpoint_id == "checkpoint-3" else ["selected_city"]
        return {
            "checkpoint_id": checkpoint_id,
            "checkpoint_ns": checkpoint_ns or "",
            "updated_channels": updated_channels,
            "checkpoint": {
                "value": {
                    "channel_values": {
                        "selected_city": selected_city,
                        "messages": [{"role": "user", "content": "email me at user@example.com"}],
                        "memory_events": memory_events,
                        "diagnostics": diagnostics,
                    }
                }
            },
        }

    def list_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = None,
    ) -> list[dict[str, Any]]:
        assert thread_id == "thread-1"
        assert checkpoint_id in {f"checkpoint-{index}" for index in range(1, 7)}
        assert checkpoint_ns in {None, "ns-a"}
        if checkpoint_id == "checkpoint-3":
            return [
                {
                    "rowid": 3,
                    "task_id": "task-profile-2",
                    "idx": 0,
                    "channel": "memory_events",
                    "value": {"decoded": True, "value": [{"type": "residence_city", "value": "Hangzhou"}]},
                }
            ]
        return [{"channel": "selected_city", "value": {"decoded": True, "value": "Hangzhou"}}]


def test_api_accepts_checkpoint_reader_adapter() -> None:
    client = TestClient(create_app(FakeCheckpointReader()))

    assert client.get("/api/summary").json()["thread_count"] == 1
    assert client.get("/api/threads").json()[0]["thread_id"] == "thread-1"
    response = client.get("/api/threads/thread-1/checkpoints")
    assert response.json()["items"][0]["checkpoint_id"] == "checkpoint-1"
    assert response.json()["pagination"]["total_count"] == 6
    assert (
        client.get("/api/threads/thread-1/checkpoints/checkpoint-1").json()["checkpoint"]["value"]["channel_values"][
            "selected_city"
        ]
        == "Hangzhou"
    )
    assert client.get("/api/threads/thread-1/checkpoints/checkpoint-1/writes").json()[0]["channel"] == "selected_city"


def test_api_serves_built_static_ui(tmp_path: Path) -> None:
    ui_dir = tmp_path / "dist"
    assets_dir = ui_dir / "assets"
    assets_dir.mkdir(parents=True)
    (ui_dir / "index.html").write_text(
        '<div id="root"></div><script type="module" src="/assets/app.js"></script>',
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('lgmi')", encoding="utf-8")

    client = TestClient(create_app(FakeCheckpointReader(), ui_dir=ui_dir))

    assert client.get("/").status_code == 200
    assert '<div id="root"></div>' in client.get("/").text
    assert client.get("/assets/app.js").text == "console.log('lgmi')"
    assert client.get("/some/react/route").status_code == 200
    assert client.get("/api/summary").json()["thread_count"] == 1
    assert client.get("/api/does-not-exist").status_code == 404


def test_api_passes_checkpoint_namespace_to_reader() -> None:
    client = TestClient(create_app(FakeCheckpointReader()))

    assert client.get("/api/threads/thread-1/checkpoints?checkpoint_ns=ns-a").status_code == 200
    assert client.get("/api/threads/thread-1/checkpoints?checkpoint_ns=ns-a").json()["items"][0]["checkpoint_ns"] == "ns-a"
    detail = client.get("/api/threads/thread-1/checkpoints/checkpoint-1?checkpoint_ns=ns-a").json()
    assert detail["checkpoint_ns"] == "ns-a"
    assert (
        client.get("/api/threads/thread-1/checkpoints/checkpoint-1/writes?checkpoint_ns=ns-a").json()[0]["channel"]
        == "selected_city"
    )
    assert client.get("/api/threads/thread-1/diff?from=checkpoint-1&to=checkpoint-1&checkpoint_ns=ns-a").status_code == 200


def test_api_returns_paginated_checkpoint_contract() -> None:
    client = TestClient(create_app(FakeCheckpointReader()))

    response = client.get("/api/threads/thread-1/checkpoints?limit=2&offset=2")
    payload = response.json()

    assert response.status_code == 200
    assert [item["checkpoint_id"] for item in payload["items"]] == ["checkpoint-3", "checkpoint-4"]
    assert payload["pagination"] == {
        "limit": 2,
        "offset": 2,
        "returned_count": 2,
        "total_count": 6,
        "has_previous": True,
        "has_next": True,
        "previous_offset": 0,
        "next_offset": 4,
    }


def test_api_can_start_timeline_page_from_end() -> None:
    client = TestClient(create_app(FakeCheckpointReader()))

    payload = client.get("/api/threads/thread-1/checkpoints?limit=2&from_end=true").json()

    assert [item["checkpoint_id"] for item in payload["items"]] == ["checkpoint-5", "checkpoint-6"]
    assert payload["pagination"]["offset"] == 4
    assert payload["pagination"]["has_previous"] is True
    assert payload["pagination"]["has_next"] is False


def test_api_filters_checkpoint_page() -> None:
    client = TestClient(create_app(FakeCheckpointReader()))

    diagnostic_payload = client.get("/api/threads/thread-1/checkpoints?diagnostic=true").json()
    changed_payload = client.get("/api/threads/thread-1/checkpoints?changed_path=state.memory_events").json()

    assert [item["checkpoint_id"] for item in diagnostic_payload["items"]] == ["checkpoint-3", "checkpoint-5"]
    assert diagnostic_payload["pagination"]["total_count"] == 2
    assert [item["checkpoint_id"] for item in changed_payload["items"]] == ["checkpoint-3"]


def test_api_returns_diagnostic_causal_chain() -> None:
    client = TestClient(create_app(FakeCheckpointReader()))

    response = client.get(
        "/api/threads/thread-1/causal-chain"
        "?checkpoint_id=checkpoint-5&diagnostic=conflicting_residence_memory&checkpoint_ns=ns-a"
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["diagnostic_id"] == "conflicting_residence_memory"
    assert payload["selected_checkpoint_id"] == "checkpoint-5"
    assert payload["state_paths"] == ["memory_events[type=residence_city]"]
    assert payload["write_channels"] == ["memory_events"]
    assert payload["range"]["scanned_checkpoint_count"] == 5
    assert any(step["checkpoint_id"] == "checkpoint-3" for step in payload["steps"])
    write_steps = [step for step in payload["steps"] if step["writes"]]
    assert write_steps[0]["writes"][0]["channel"] == "memory_events"
    assert write_steps[0]["writes"][0]["state_path"] == "state.memory_events"
    assert write_steps[0]["writes"][0]["node"] == "extract_profile"


def test_api_exports_debug_bundle_only_when_requested(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(FakeCheckpointReader()))

    assert not (tmp_path / "exports").exists()
    response = client.post(
        "/api/exports/debug-bundle",
        json={
            "thread_id": "thread-1",
            "checkpoint_id": "checkpoint-1",
            "checkpoint_ns": "ns-a",
            "redaction_mode": "redacted",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["thread_id"] == "thread-1"
    assert payload["checkpoint_id"] == "checkpoint-1"
    assert payload["checkpoint_ns"] == "ns-a"
    assert payload["redaction_mode"] == "redacted"
    assert payload["redaction_count"] > 0
    assert payload["file_size_bytes"] > 0
    assert Path(payload["path"]).exists()
    assert Path(payload["path"]).parent == tmp_path / "exports"
    assert "user@example.com" not in Path(payload["path"]).read_text(encoding="utf-8")
