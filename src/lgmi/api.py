from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal

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
    checkpoint_ns: str | None = None
    context: int = Field(default=2, ge=0, le=20)
    redaction_mode: Literal["raw", "redacted"] = "raw"
    redact_paths: list[str] = Field(default_factory=list)
    keep_paths: list[str] = Field(default_factory=list)


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
    def checkpoints(
        thread_id: str,
        checkpoint_ns: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        from_end: bool = Query(default=False),
        diagnostic: bool | None = Query(default=None),
        changed_path: str | None = Query(default=None),
    ) -> dict[str, Any]:
        return _read_or_404(
            lambda: _checkpoint_page(
                reader,
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                limit=limit,
                offset=offset,
                from_end=from_end,
                diagnostic=diagnostic,
                changed_path=changed_path,
            )
        )

    @app.get("/api/threads/{thread_id}/checkpoints/{checkpoint_id}")
    def checkpoint(
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = Query(default=None),
    ) -> dict[str, Any]:
        item = _read_or_404(
            lambda: reader.get_checkpoint(thread_id, checkpoint_id, checkpoint_ns)
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        return item

    @app.get("/api/threads/{thread_id}/checkpoints/{checkpoint_id}/writes")
    def writes(
        thread_id: str,
        checkpoint_id: str,
        checkpoint_ns: str | None = Query(default=None),
    ) -> list[dict[str, Any]]:
        return _read_or_404(
            lambda: reader.list_writes(thread_id, checkpoint_id, checkpoint_ns)
        )

    @app.get("/api/threads/{thread_id}/diff")
    def diff(
        thread_id: str,
        from_checkpoint_id: str = Query(alias="from"),
        to_checkpoint_id: str = Query(alias="to"),
        checkpoint_ns: str | None = Query(default=None),
    ) -> dict[str, Any]:
        before = _read_or_404(
            lambda: reader.get_checkpoint(thread_id, from_checkpoint_id, checkpoint_ns)
        )
        after = _read_or_404(
            lambda: reader.get_checkpoint(thread_id, to_checkpoint_id, checkpoint_ns)
        )
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
                checkpoint_ns=request.checkpoint_ns,
                context=request.context,
                redaction_mode=request.redaction_mode,
                redact_paths=request.redact_paths,
                keep_paths=request.keep_paths,
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


def _checkpoint_page(
    reader: CheckpointReader,
    *,
    thread_id: str,
    checkpoint_ns: str | None,
    limit: int,
    offset: int,
    from_end: bool,
    diagnostic: bool | None,
    changed_path: str | None,
) -> dict[str, Any]:
    total_count = reader.count_checkpoints(
        thread_id,
        checkpoint_ns,
        diagnostic=diagnostic,
        changed_path=changed_path,
    )
    resolved_offset = max(total_count - limit, 0) if from_end else offset
    resolved_offset = min(resolved_offset, total_count)
    items = reader.list_checkpoints(
        thread_id,
        checkpoint_ns,
        limit=limit,
        offset=resolved_offset,
        diagnostic=diagnostic,
        changed_path=changed_path,
    )
    returned_count = len(items)
    next_offset = resolved_offset + returned_count
    return {
        "items": items,
        "pagination": {
            "limit": limit,
            "offset": resolved_offset,
            "returned_count": returned_count,
            "total_count": total_count,
            "has_previous": resolved_offset > 0,
            "has_next": next_offset < total_count,
            "previous_offset": max(resolved_offset - limit, 0) if resolved_offset > 0 else None,
            "next_offset": next_offset if next_offset < total_count else None,
        },
        "filters": {
            "checkpoint_ns": checkpoint_ns,
            "diagnostic": diagnostic,
            "changed_path": changed_path,
        },
    }


def _state_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    value = checkpoint.get("checkpoint", {}).get("value", {})
    if not isinstance(value, dict):
        return {}
    channel_values = value.get("channel_values", {})
    return channel_values if isinstance(channel_values, dict) else {}
