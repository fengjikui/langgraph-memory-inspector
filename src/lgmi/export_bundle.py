from __future__ import annotations

import copy
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Literal

from lgmi.analysis import run_diagnostics
from lgmi.adapters import CheckpointReader


DEFAULT_EXPORT_DIR = Path("exports")
EXPORT_SCHEMA_VERSION = 1
REDACTION_PLACEHOLDER = "[REDACTED]"
RedactionMode = Literal["raw", "redacted"]

SENSITIVE_KEY_PATTERN = re.compile(
    r"(api[_-]?key|authorization|cookie|credential|password|secret|token)",
    re.IGNORECASE,
)
DEFAULT_REDACT_KEYS = {
    "content",
    "evidence",
    "input",
    "output",
    "preview",
    "profile_text",
    "prompt",
    "raw_text",
    "text",
    "transcript",
    "user_text",
}
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d .().-]{7,}\d)(?!\d)")
TOKEN_PATTERN = re.compile(r"\b(?:sk|sk-proj|ghp|github_pat)_[A-Za-z0-9_=-]{12,}\b")


def export_debug_bundle(
    reader: CheckpointReader,
    *,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str | None = None,
    output_dir: str | Path = DEFAULT_EXPORT_DIR,
    context: int = 2,
    generated_at: dt.datetime | None = None,
    redaction_mode: RedactionMode = "raw",
    redact_paths: list[str] | None = None,
    keep_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Write a shareable checkpoint debug bundle and return file metadata."""
    generated = _coerce_utc(generated_at or _utc_now())
    bundle = build_debug_bundle(
        reader,
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
        context=context,
        generated_at=generated,
        redaction_mode=redaction_mode,
        redact_paths=redact_paths,
        keep_paths=keep_paths,
    )
    export_dir = Path(output_dir).expanduser()
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / _bundle_filename(thread_id, checkpoint_id, checkpoint_ns, generated)
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "path": str(path.resolve()),
        "file_size_bytes": path.stat().st_size,
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_ns": bundle["thread"]["checkpoint_ns"],
        "diagnostic_ids": [item.get("id") for item in bundle["diagnostics"]],
        "schema_version": EXPORT_SCHEMA_VERSION,
        "redaction_mode": bundle["privacy"]["redaction_mode"],
        "redacted_paths": bundle["privacy"]["redacted_paths"],
        "redaction_count": bundle["privacy"]["redaction_count"],
    }


def build_debug_bundle(
    reader: CheckpointReader,
    *,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str | None = None,
    context: int = 2,
    generated_at: dt.datetime | None = None,
    redaction_mode: RedactionMode = "raw",
    redact_paths: list[str] | None = None,
    keep_paths: list[str] | None = None,
) -> dict[str, Any]:
    redaction = _normalize_redaction(
        redaction_mode,
        redact_paths=redact_paths,
        keep_paths=keep_paths,
    )
    summary = reader.summary()
    checkpoints = reader.list_checkpoints(thread_id, checkpoint_ns)
    checkpoint = reader.get_checkpoint(thread_id, checkpoint_id, checkpoint_ns)
    if checkpoint is None:
        raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    writes = reader.list_writes(thread_id, checkpoint_id, checkpoint_ns)
    state = _state_from_checkpoint(checkpoint)
    diagnostics = run_diagnostics(state, writes=writes, checkpoints=checkpoints)
    timeline_slice = _timeline_slice(checkpoints, checkpoint_id, context)
    generated = _coerce_utc(generated_at or _utc_now())

    bundle = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": generated.isoformat().replace("+00:00", "Z"),
        "privacy": {
            "redaction_mode": redaction["mode"],
            "redacted_paths": [],
            "redaction_count": 0,
            "requested_redact_paths": redaction["redact_paths"],
            "requested_keep_paths": redaction["keep_paths"],
        },
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
    return _apply_redaction(bundle, redaction)


def _normalize_redaction(
    redaction_mode: RedactionMode,
    *,
    redact_paths: list[str] | None,
    keep_paths: list[str] | None,
) -> dict[str, Any]:
    mode = redaction_mode.lower()
    if mode not in {"raw", "redacted"}:
        raise ValueError("redaction_mode must be 'raw' or 'redacted'")
    return {
        "mode": mode,
        "redact_paths": _clean_paths(redact_paths),
        "keep_paths": _clean_paths(keep_paths),
    }


def _clean_paths(paths: list[str] | None) -> list[str]:
    if not paths:
        return []
    return sorted({path.strip().strip(".") for path in paths if path.strip().strip(".")})


def _apply_redaction(bundle: dict[str, Any], redaction: dict[str, Any]) -> dict[str, Any]:
    if redaction["mode"] == "raw":
        return bundle

    redacted_paths: set[str] = set()
    redacted_bundle = _redact_value(
        copy.deepcopy(bundle),
        path="",
        redact_paths=set(redaction["redact_paths"]),
        keep_paths=set(redaction["keep_paths"]),
        redacted_paths=redacted_paths,
    )
    assert isinstance(redacted_bundle, dict)
    redacted_bundle["privacy"] = {
        **redacted_bundle["privacy"],
        "redacted_paths": sorted(redacted_paths),
        "redaction_count": len(redacted_paths),
    }
    return redacted_bundle


def _redact_value(
    value: Any,
    *,
    path: str,
    redact_paths: set[str],
    keep_paths: set[str],
    redacted_paths: set[str],
) -> Any:
    if _matches_path(path, keep_paths):
        return value
    if path and _matches_path(path, redact_paths):
        redacted_paths.add(path)
        return REDACTION_PLACEHOLDER

    if isinstance(value, dict):
        next_value: dict[str, Any] = {}
        for key, item in value.items():
            item_path = _join_path(path, str(key))
            if _is_default_sensitive_key(str(key)) and not _matches_path(item_path, keep_paths):
                next_value[key] = REDACTION_PLACEHOLDER
                redacted_paths.add(item_path)
            else:
                next_value[key] = _redact_value(
                    item,
                    path=item_path,
                    redact_paths=redact_paths,
                    keep_paths=keep_paths,
                    redacted_paths=redacted_paths,
                )
        return next_value

    if isinstance(value, list):
        if (
            len(value) == 2
            and isinstance(value[0], str)
            and _is_default_sensitive_key(value[0])
            and not _matches_path(f"{path}[1]", keep_paths)
        ):
            redacted_paths.add(f"{path}[1]")
            return [value[0], REDACTION_PLACEHOLDER]
        return [
            _redact_value(
                item,
                path=f"{path}[{index}]",
                redact_paths=redact_paths,
                keep_paths=keep_paths,
                redacted_paths=redacted_paths,
            )
            for index, item in enumerate(value)
        ]

    if isinstance(value, str):
        redacted = _redact_string_patterns(value)
        if redacted != value:
            redacted_paths.add(path)
        return redacted

    return value


def _is_default_sensitive_key(key: str) -> bool:
    return key.lower() in DEFAULT_REDACT_KEYS or bool(SENSITIVE_KEY_PATTERN.search(key))


def _redact_string_patterns(value: str) -> str:
    redacted = EMAIL_PATTERN.sub(REDACTION_PLACEHOLDER, value)
    redacted = PHONE_PATTERN.sub(REDACTION_PLACEHOLDER, redacted)
    return TOKEN_PATTERN.sub(REDACTION_PLACEHOLDER, redacted)


def _matches_path(path: str, candidates: set[str]) -> bool:
    return any(
        path == candidate
        or path.startswith(f"{candidate}.")
        or path.startswith(f"{candidate}[")
        for candidate in candidates
    )


def _join_path(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else key


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
    if "stale_retrieved_context" in diagnostic_ids:
        notes.append("stale_retrieved_context indicates retrieved_docs contains context that does not match the latest user or query context.")
    if "repeated_retrieved_context" in diagnostic_ids:
        notes.append("repeated_retrieved_context indicates retrieval may need source/content deduplication before context packing.")
    if "reducer_append_duplicate_state" in diagnostic_ids:
        notes.append("reducer_append_duplicate_state indicates a reducer-backed channel may have appended duplicate semantic state.")
    if "oversized_message_history" in diagnostic_ids:
        notes.append("oversized_message_history indicates state.messages may need trimming, summarization, or task-scoped checkpointing.")
    if "unexpected_parent_checkpoint" in diagnostic_ids:
        notes.append("unexpected_parent_checkpoint indicates checkpoint lineage jumps; confirm whether this was an intentional branch or a wrong resume point.")
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


def _bundle_filename(
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str | None,
    generated_at: dt.datetime,
) -> str:
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    namespace = f"-{_slug(checkpoint_ns)}" if checkpoint_ns else ""
    return f"lgmi-debug-{_slug(thread_id)}{namespace}-{_slug(checkpoint_id)}-{stamp}.json"


def _slug(value: str, *, max_length: int = 48) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return (slug or "item")[:max_length]


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def _coerce_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC, microsecond=0)
    return value.astimezone(dt.UTC).replace(microsecond=0)
