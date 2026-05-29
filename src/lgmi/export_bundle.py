from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from lgmi.analysis import run_diagnostics
from lgmi.adapters import CheckpointReader


DEFAULT_EXPORT_DIR = Path("exports")
EXPORT_SCHEMA_VERSION = 1


def export_debug_bundle(
    reader: CheckpointReader,
    *,
    thread_id: str,
    checkpoint_id: str,
    output_dir: str | Path = DEFAULT_EXPORT_DIR,
    context: int = 2,
    generated_at: dt.datetime | None = None,
) -> dict[str, Any]:
    """Write a shareable checkpoint debug bundle and return file metadata."""
    generated = _coerce_utc(generated_at or _utc_now())
    bundle = build_debug_bundle(
        reader,
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        context=context,
        generated_at=generated,
    )
    export_dir = Path(output_dir).expanduser()
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / _bundle_filename(thread_id, checkpoint_id, generated)
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "path": str(path.resolve()),
        "file_size_bytes": path.stat().st_size,
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id,
        "diagnostic_ids": [item.get("id") for item in bundle["diagnostics"]],
        "schema_version": EXPORT_SCHEMA_VERSION,
    }


def build_debug_bundle(
    reader: CheckpointReader,
    *,
    thread_id: str,
    checkpoint_id: str,
    context: int = 2,
    generated_at: dt.datetime | None = None,
) -> dict[str, Any]:
    summary = reader.summary()
    checkpoints = reader.list_checkpoints(thread_id)
    checkpoint = reader.get_checkpoint(thread_id, checkpoint_id)
    if checkpoint is None:
        raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    writes = reader.list_writes(thread_id, checkpoint_id)
    state = _state_from_checkpoint(checkpoint)
    diagnostics = run_diagnostics(state, writes=writes, checkpoints=checkpoints)
    timeline_slice = _timeline_slice(checkpoints, checkpoint_id, context)
    generated = _coerce_utc(generated_at or _utc_now())

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": generated.isoformat().replace("+00:00", "Z"),
        "summary": summary,
        "thread": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_ns": checkpoint.get("checkpoint_ns", ""),
        },
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_ns": checkpoint.get("checkpoint_ns", ""),
        "selected_checkpoint": checkpoint,
        "timeline_slice": timeline_slice,
        "writes": writes,
        "diagnostics": diagnostics,
        "reproduction_notes": _reproduction_notes(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            diagnostics=diagnostics,
            writes=writes,
            state=state,
        ),
    }


def _timeline_slice(
    checkpoints: list[dict[str, Any]],
    checkpoint_id: str,
    context: int,
) -> list[dict[str, Any]]:
    if context < 0:
        raise ValueError("context must be >= 0")
    index = next(
        (position for position, item in enumerate(checkpoints) if item.get("checkpoint_id") == checkpoint_id),
        None,
    )
    if index is None:
        return checkpoints[-((context * 2) + 1):]
    start = max(index - context, 0)
    end = min(index + context + 1, len(checkpoints))
    return checkpoints[start:end]


def _reproduction_notes(
    *,
    thread_id: str,
    checkpoint_id: str,
    diagnostics: list[dict[str, Any]],
    writes: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[str]:
    notes = [
        f"Inspect thread {thread_id} and checkpoint {checkpoint_id}.",
        "Open the selected checkpoint, then compare its state, writes, and diagnostics.",
    ]
    diagnostic_ids = {str(item.get("id")) for item in diagnostics}
    write_channels = {str(item.get("channel")) for item in writes}
    if "conflicting_residence_memory" in diagnostic_ids:
        notes.append("conflicting_residence_memory indicates multiple active residence_city memories.")
    if "stale_selected_city" in diagnostic_ids:
        notes.append("stale_selected_city indicates selected_city does not match the latest residence memory.")
    if "memory_events" in write_channels:
        notes.append("state.memory_events writes are included as direct evidence for profile memory changes.")
    if state.get("selected_city"):
        notes.append(f"selected_city at this checkpoint is {state['selected_city']!r}.")
    return notes


def _state_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    value = checkpoint.get("checkpoint", {}).get("value", {})
    if not isinstance(value, dict):
        return {}
    channel_values = value.get("channel_values", {})
    return channel_values if isinstance(channel_values, dict) else {}


def _bundle_filename(thread_id: str, checkpoint_id: str, generated_at: dt.datetime) -> str:
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    return f"lgmi-debug-{_slug(thread_id)}-{_slug(checkpoint_id)}-{stamp}.json"


def _slug(value: str, *, max_length: int = 48) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return (slug or "item")[:max_length]


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def _coerce_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC, microsecond=0)
    return value.astimezone(dt.UTC).replace(microsecond=0)
