from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping


MESSAGE_HISTORY_THRESHOLD = 6
CHECKPOINT_SIZE_SPIKE_RATIO = 2.0

SUMMARY_FIELDS = (
    "messages",
    "memory_events",
    "retrieved_docs",
    "selected_city",
    "diagnostics",
)

_MISSING = object()


def diff_states(before: Mapping[str, Any] | None, after: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a top-level state diff with focused summaries for known agent fields."""
    before_state = dict(before or {})
    after_state = dict(after or {})
    before_keys = set(before_state)
    after_keys = set(after_state)

    added = {key: _jsonable(after_state[key]) for key in sorted(after_keys - before_keys)}
    removed = {key: _jsonable(before_state[key]) for key in sorted(before_keys - after_keys)}
    changed: dict[str, dict[str, Any]] = {}

    for key in sorted(before_keys & after_keys):
        before_value = _jsonable(before_state[key])
        after_value = _jsonable(after_state[key])
        if before_value != after_value:
            changed[key] = {"before": before_value, "after": after_value}

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": {
            field: _summarize_field(field, before_state.get(field, _MISSING), after_state.get(field, _MISSING))
            for field in SUMMARY_FIELDS
        },
    }


def run_diagnostics(
    state: Mapping[str, Any] | None,
    writes: Iterable[Any] | None = None,
    checkpoints: Iterable[Any] | None = None,
) -> list[dict[str, Any]]:
    """Inspect a LangGraph state snapshot for memory/debugging risks."""
    state = state or {}
    diagnostics: list[dict[str, Any]] = []

    residence_events = [
        event
        for event in _as_list(state.get("memory_events"))
        if _get(event, "type") == "residence_city"
    ]
    residence_values = [_get(event, "value") for event in residence_events if _get(event, "value") is not None]
    distinct_values = list(dict.fromkeys(str(value) for value in residence_values))

    if len(distinct_values) > 1:
        diagnostics.append(
            {
                "id": "conflicting_residence_memory",
                "severity": "error",
                "title": "Conflicting residence memories",
                "description": "The state contains more than one residence_city value, so retrieval may ground answers in stale local context.",
                "evidence": {
                    "values": distinct_values,
                    "events": [_jsonable(event) for event in residence_events],
                    "write_summary": summarize_writes(writes) if writes is not None else [],
                },
            }
        )

    latest_residence = distinct_values[-1] if distinct_values else None
    selected_city = state.get("selected_city")
    if latest_residence and selected_city and str(selected_city) != latest_residence:
        diagnostics.append(
            {
                "id": "stale_selected_city",
                "severity": "error",
                "title": "Selected city is stale",
                "description": "selected_city does not match the newest residence_city memory.",
                "evidence": {
                    "selected_city": selected_city,
                    "latest_residence_city": latest_residence,
                    "latest_residence_event": _jsonable(residence_events[-1]) if residence_events else None,
                },
            }
        )

    messages = _as_list(state.get("messages"))
    if len(messages) >= MESSAGE_HISTORY_THRESHOLD:
        diagnostics.append(
            {
                "id": "oversized_message_history",
                "severity": "warning",
                "title": "Message history is large",
                "description": "The message history is at or above the MVP threshold and may increase checkpoint size or context cost.",
                "evidence": {
                    "message_count": len(messages),
                    "threshold": MESSAGE_HISTORY_THRESHOLD,
                    "last_messages": [_message_summary(message) for message in messages[-3:]],
                },
            }
        )

    repeated_docs = _find_repeated_docs(_as_list(state.get("retrieved_docs")))
    if repeated_docs:
        diagnostics.append(
            {
                "id": "repeated_retrieved_context",
                "severity": "warning",
                "title": "Retrieved context repeats",
                "description": "retrieved_docs contains repeated source/content combinations that can waste context and hide useful evidence.",
                "evidence": {"duplicates": repeated_docs},
            }
        )

    size_spikes = _find_checkpoint_size_spikes(_as_list(checkpoints))
    if size_spikes:
        diagnostics.append(
            {
                "id": "checkpoint_size_spike",
                "severity": "warning",
                "title": "Checkpoint size spike",
                "description": "One or more adjacent checkpoints grew sharply in byte_size.",
                "evidence": {
                    "ratio_threshold": CHECKPOINT_SIZE_SPIKE_RATIO,
                    "spikes": size_spikes,
                },
            }
        )

    return diagnostics


def summarize_writes(writes: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Group LangGraph node writes by channel and task_id for UI display."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    for index, write in enumerate(writes or []):
        channel = str(_get(write, "channel", "unknown") or "unknown")
        task_id = str(_get(write, "task_id", "unknown") or "unknown")
        key = (channel, task_id)
        group = grouped.setdefault(
            key,
            {
                "channel": channel,
                "task_id": task_id,
                "count": 0,
                "nodes": [],
                "writes": [],
            },
        )

        node = _get(write, "node", None) or _get(write, "task_path", None) or _get(write, "source", None)
        group["count"] += 1
        if node and node not in group["nodes"]:
            group["nodes"].append(node)
        group["writes"].append(_write_summary(write, index))

    return [
        {
            **group,
            "nodes": sorted(group["nodes"]),
        }
        for group in sorted(grouped.values(), key=lambda item: (item["channel"], item["task_id"]))
    ]


def _summarize_field(field: str, before: Any, after: Any) -> dict[str, Any]:
    if field == "messages":
        return _summarize_messages(before, after)
    if field == "memory_events":
        return _summarize_memory_events(before, after)
    if field == "retrieved_docs":
        return _summarize_retrieved_docs(before, after)
    if field == "selected_city":
        return _summarize_scalar(before, after)
    if field == "diagnostics":
        return _summarize_diagnostics(before, after)
    return _summarize_scalar(before, after)


def _summarize_messages(before: Any, after: Any) -> dict[str, Any]:
    before_messages = [_message_summary(message) for message in _as_list(before)]
    after_messages = [_message_summary(message) for message in _as_list(after)]
    before_ids = [_message_identity(message) for message in before_messages]
    after_ids = [_message_identity(message) for message in after_messages]
    return {
        "before_count": len(before_messages),
        "after_count": len(after_messages),
        "delta": len(after_messages) - len(before_messages),
        "added": _counter_delta(after_ids, before_ids),
        "removed": _counter_delta(before_ids, after_ids),
        "last_before": before_messages[-1] if before_messages else None,
        "last_after": after_messages[-1] if after_messages else None,
    }


def _summarize_memory_events(before: Any, after: Any) -> dict[str, Any]:
    before_events = [_jsonable(event) for event in _as_list(before)]
    after_events = [_jsonable(event) for event in _as_list(after)]
    before_ids = [_memory_event_identity(event) for event in before_events]
    after_ids = [_memory_event_identity(event) for event in after_events]
    before_residence = _residence_values(before_events)
    after_residence = _residence_values(after_events)
    return {
        "before_count": len(before_events),
        "after_count": len(after_events),
        "delta": len(after_events) - len(before_events),
        "added": _counter_delta(after_ids, before_ids),
        "removed": _counter_delta(before_ids, after_ids),
        "residence_city_values": after_residence,
        "latest_residence_city": after_residence[-1] if after_residence else None,
        "introduced_conflict": len(set(after_residence)) > 1 and len(set(before_residence)) <= 1,
    }


def _summarize_retrieved_docs(before: Any, after: Any) -> dict[str, Any]:
    before_docs = [_doc_summary(doc) for doc in _as_list(before)]
    after_docs = [_doc_summary(doc) for doc in _as_list(after)]
    before_ids = [_doc_identity(doc) for doc in before_docs]
    after_ids = [_doc_identity(doc) for doc in after_docs]
    return {
        "before_count": len(before_docs),
        "after_count": len(after_docs),
        "delta": len(after_docs) - len(before_docs),
        "added": _counter_delta(after_ids, before_ids),
        "removed": _counter_delta(before_ids, after_ids),
        "sources": sorted({doc.get("source") for doc in after_docs if doc.get("source")}),
        "cities": sorted({doc.get("city") for doc in after_docs if doc.get("city")}),
    }


def _summarize_diagnostics(before: Any, after: Any) -> dict[str, Any]:
    before_ids = [_diagnostic_identity(item) for item in _as_list(before)]
    after_ids = [_diagnostic_identity(item) for item in _as_list(after)]
    return {
        "before_count": len(before_ids),
        "after_count": len(after_ids),
        "added": _counter_delta(after_ids, before_ids),
        "removed": _counter_delta(before_ids, after_ids),
        "active": after_ids,
    }


def _summarize_scalar(before: Any, after: Any) -> dict[str, Any]:
    return {
        "before": None if before is _MISSING else _jsonable(before),
        "after": None if after is _MISSING else _jsonable(after),
        "changed": before is _MISSING or after is _MISSING or _jsonable(before) != _jsonable(after),
    }


def _find_repeated_docs(docs: list[Any]) -> list[dict[str, Any]]:
    signatures: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    for index, doc in enumerate(docs):
        source = str(_get(doc, "source", "") or "")
        content = str(_get(doc, "content", "") or "")
        signatures[(source, content)].append(index)

    duplicates = []
    for (source, content), indexes in signatures.items():
        if len(indexes) > 1:
            duplicates.append(
                {
                    "source": source,
                    "content_preview": _preview(content),
                    "indexes": indexes,
                    "count": len(indexes),
                }
            )
    return duplicates


def _find_checkpoint_size_spikes(checkpoints: list[Any]) -> list[dict[str, Any]]:
    spikes = []
    for previous, current in zip(checkpoints, checkpoints[1:]):
        previous_size = _to_int(_get(previous, "byte_size"))
        current_size = _to_int(_get(current, "byte_size"))
        if previous_size is None or current_size is None or previous_size <= 0:
            continue
        ratio = current_size / previous_size
        if ratio >= CHECKPOINT_SIZE_SPIKE_RATIO:
            spikes.append(
                {
                    "from_checkpoint_id": _get(previous, "checkpoint_id", _get(previous, "id", None)),
                    "to_checkpoint_id": _get(current, "checkpoint_id", _get(current, "id", None)),
                    "from_byte_size": previous_size,
                    "to_byte_size": current_size,
                    "ratio": round(ratio, 2),
                }
            )
    return spikes


def _write_summary(write: Any, index: int) -> dict[str, Any]:
    value = _get(write, "value", _get(write, "blob", _get(write, "data", None)))
    return {
        "index": _get(write, "idx", index),
        "channel": _get(write, "channel", "unknown"),
        "task_id": _get(write, "task_id", "unknown"),
        "node": _get(write, "node", None) or _get(write, "task_path", None) or _get(write, "source", None),
        "value_preview": _preview(_jsonable(value)),
    }


def _message_summary(message: Any) -> dict[str, Any]:
    message_type = _get(message, "type", None) or _get(message, "role", None) or message.__class__.__name__
    content = _get(message, "content", message)
    return {
        "type": str(message_type),
        "content_preview": _preview(content),
    }


def _doc_summary(doc: Any) -> dict[str, Any]:
    return {
        "city": _get(doc, "city", None),
        "source": _get(doc, "source", None),
        "content_preview": _preview(_get(doc, "content", "")),
    }


def _jsonable(value: Any) -> Any:
    if value is _MISSING:
        return None
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "dict"):
        try:
            return _jsonable(value.dict())
        except TypeError:
            pass
    return repr(value)


def _as_list(value: Any) -> list[Any]:
    if value is _MISSING or value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _preview(value: Any, limit: int = 180) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = repr(value)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _counter_delta(left: Iterable[Any], right: Iterable[Any]) -> list[Any]:
    left_counts = Counter(left)
    right_counts = Counter(right)
    values = []
    for item, count in (left_counts - right_counts).items():
        values.extend([item] * count)
    return values


def _message_identity(message: Mapping[str, Any]) -> str:
    return f"{message.get('type', '')}:{message.get('content_preview', '')}"


def _memory_event_identity(event: Mapping[str, Any]) -> str:
    return f"{event.get('type', '')}:{event.get('value', '')}:{event.get('source', '')}"


def _doc_identity(doc: Mapping[str, Any]) -> str:
    return f"{doc.get('source', '')}:{doc.get('content_preview', '')}"


def _diagnostic_identity(diagnostic: Any) -> str:
    if isinstance(diagnostic, Mapping):
        return str(diagnostic.get("id") or diagnostic.get("title") or diagnostic)
    return str(diagnostic)


def _residence_values(events: list[Any]) -> list[str]:
    return [
        str(_get(event, "value"))
        for event in events
        if _get(event, "type") == "residence_city" and _get(event, "value") is not None
    ]


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
