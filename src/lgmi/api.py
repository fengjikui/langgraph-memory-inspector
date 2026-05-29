from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from lgmi.analysis import diff_states
from lgmi.adapters import CheckpointReader
from lgmi.checkpoint_reader import SQLiteCheckpointReader
from lgmi.export_bundle import export_debug_bundle


class DebugBundleRequest(BaseModel):
    thread_id: str
    checkpoint_id: str
    context: int = Field(default=2, ge=0, le=20)


def create_app(source: str | Path | CheckpointReader) -> FastAPI:
    reader: CheckpointReader
    if isinstance(source, (str, Path)):
        reader = SQLiteCheckpointReader(source)
    else:
        reader = source
    app = FastAPI(
        title="LangGraph Memory Inspector API",
        version="0.1.0",
        description="Local API for inspecting LangGraph checkpoints.",
    )
    app.state.db_path = str(getattr(reader, "db_path", ""))
    app.state.reader = reader

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/summary")
    def summary() -> dict[str, Any]:
        return _read_or_404(reader.summary)

    @app.get("/api/threads")
    def threads() -> list[dict[str, Any]]:
        return _read_or_404(reader.list_threads)

    @app.get("/api/threads/{thread_id}/checkpoints")
    def checkpoints(thread_id: str) -> list[dict[str, Any]]:
        return _read_or_404(lambda: reader.list_checkpoints(thread_id))

    @app.get("/api/threads/{thread_id}/checkpoints/{checkpoint_id}")
    def checkpoint(thread_id: str, checkpoint_id: str) -> dict[str, Any]:
        item = _read_or_404(lambda: reader.get_checkpoint(thread_id, checkpoint_id))
        if item is None:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        return item

    @app.get("/api/threads/{thread_id}/checkpoints/{checkpoint_id}/writes")
    def writes(thread_id: str, checkpoint_id: str) -> list[dict[str, Any]]:
        return _read_or_404(lambda: reader.list_writes(thread_id, checkpoint_id))

    @app.get("/api/threads/{thread_id}/diff")
    def diff(
        thread_id: str,
        from_checkpoint_id: str = Query(alias="from"),
        to_checkpoint_id: str = Query(alias="to"),
    ) -> dict[str, Any]:
        before = _read_or_404(lambda: reader.get_checkpoint(thread_id, from_checkpoint_id))
        after = _read_or_404(lambda: reader.get_checkpoint(thread_id, to_checkpoint_id))
        if before is None or after is None:
            raise HTTPException(status_code=404, detail="Checkpoint not found")

        return {
            "from_checkpoint_id": from_checkpoint_id,
            "to_checkpoint_id": to_checkpoint_id,
            "diff": diff_states(_state_from_checkpoint(before), _state_from_checkpoint(after)),
        }

    @app.post("/api/exports/debug-bundle")
    def debug_bundle(request: DebugBundleRequest) -> dict[str, Any]:
        return _read_or_404(
            lambda: export_debug_bundle(
                reader,
                thread_id=request.thread_id,
                checkpoint_id=request.checkpoint_id,
                context=request.context,
            )
        )

    return app


def _read_or_404(func: Callable[[], Any]) -> Any:
    try:
        return func()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _state_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    value = checkpoint.get("checkpoint", {}).get("value", {})
    if not isinstance(value, dict):
        return {}
    channel_values = value.get("channel_values", {})
    return channel_values if isinstance(channel_values, dict) else {}
