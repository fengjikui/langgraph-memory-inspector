from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping


MESSAGE_HISTORY_THRESHOLD = 6
CHECKPOINT_SIZE_SPIKE_RATIO = 2.0
TRACKED_REDUCER_CHANNELS = ("messages", "memory_events")

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
                "evidence": _message_history_evidence(messages, writes),
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

    stale_retrieved_context = _find_stale_retrieved_context(state)
    if stale_retrieved_context:
        diagnostics.append(
            {
                "id": "stale_retrieved_context",
                "severity": "error",
                "title": "Retrieved context is stale",
                "description": "retrieved_docs contains city-scoped context that does not match the latest user residence memory or active query context.",
                "evidence": {
                    **stale_retrieved_context,
                    "write_summary": summarize_writes(writes) if writes is not None else [],
                    "checkpoint_context": _checkpoint_context_for_evidence(_as_list(checkpoints)),
                },
            }
        )

    reducer_duplicates = _find_reducer_append_duplicates(state)
    if reducer_duplicates:
        diagnostics.append(
            {
                "id": "reducer_append_duplicate_state",
                "severity": "warning",
                "title": "Reducer append may be duplicating state",
                "description": "One or more reducer-backed state channels contain duplicate semantic entries. This often happens when a reducer appends old state again instead of adding only new items.",
                "evidence": {
                    "duplicates": reducer_duplicates,
                    "write_summary": summarize_writes(writes) if writes is not None else [],
                },
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

    parent_anomalies = _find_unexpected_parent_checkpoints(_as_list(checkpoints))
    if parent_anomalies:
        diagnostics.append(
            {
                "id": "unexpected_parent_checkpoint",
                "severity": "warning",
                "title": "Checkpoint parent jumps in the timeline",
                "description": "A checkpoint parent does not match the previous checkpoint in the current ordered timeline. This can be normal branching, but it is a useful signal when debugging wrong resume points.",
                "evidence": {
                    "anomalies": parent_anomalies,
                    "false_positive_note": "LangGraph branches and namespaces can intentionally create non-linear parent links. Confirm the thread_id and checkpoint_ns before treating this as a bug.",
                },
            }
        )

    namespace_confusions = _find_checkpoint_namespace_confusion(_as_list(checkpoints))
    if namespace_confusions:
        diagnostics.append(
            {
                "id": "checkpoint_namespace_confusion",
                "severity": "warning",
                "title": "Checkpoint namespaces diverge for the same thread",
                "description": "The same thread has multiple checkpoint namespaces with different latest state signatures. Confirm the active checkpoint_ns before treating missing or stale state as a graph bug.",
                "evidence": {
                    "threads": namespace_confusions,
                    "false_positive_note": "Multiple namespaces can be intentional for replay, forks, or experiments. This diagnostic is a navigation hint when the inspected namespace does not match the user's expected run.",
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


def _message_history_evidence(messages: list[Any], writes: Iterable[Any] | None) -> dict[str, Any]:
    message_summaries = [_message_summary(message) for message in messages]
    role_counts = Counter(summary["type"] for summary in message_summaries)
    total_content_chars = sum(len(str(_get(message, "content", ""))) for message in messages)
    evidence: dict[str, Any] = {
        "state_path": "messages",
        "message_count": len(messages),
        "threshold": MESSAGE_HISTORY_THRESHOLD,
        "role_counts": dict(sorted(role_counts.items())),
        "total_content_chars": total_content_chars,
        "first_message": message_summaries[0] if message_summaries else None,
        "last_messages": message_summaries[-3:],
        "suggested_action": "Inspect message-writing nodes and consider trimming, summarizing, or checkpointing only task-relevant history before the next model call.",
    }
    if writes is not None:
        message_writes = [
            write
            for write in writes
            if str(_get(write, "channel", "")) == "messages"
        ]
        evidence["write_summary"] = summarize_writes(message_writes)
    return evidence


def _find_stale_retrieved_context(state: Mapping[str, Any]) -> dict[str, Any] | None:
    docs = _as_list(state.get("retrieved_docs"))
    if not docs:
        return None

    expected_city = _expected_retrieval_city(state)
    if not expected_city:
        return None

    stale_docs: list[dict[str, Any]] = []
    matching_docs = 0
    for index, doc in enumerate(docs):
        doc_city = _doc_city(doc)
        if not doc_city:
            continue
        if doc_city == expected_city["city"]:
            matching_docs += 1
            continue
        stale_docs.append(
            {
                "index": index,
                "city": doc_city,
                "source": _get(doc, "source", None),
                "content_preview": _preview(_get(doc, "content", "")),
            }
        )

    if not stale_docs:
        return None

    return {
        "expected_city": expected_city["city"],
        "expected_city_source": expected_city["source"],
        "stale_docs": stale_docs,
        "matching_doc_count": matching_docs,
        "retrieved_doc_count": len(docs),
        "state_path": "retrieved_docs",
        "suggested_action": "Inspect the retrieval node writes and compare retrieved_docs city/source against the latest residence or active query context.",
    }


def _expected_retrieval_city(state: Mapping[str, Any]) -> dict[str, str] | None:
    residence_values = _residence_values(_as_list(state.get("memory_events")))
    if residence_values:
        return {
            "city": residence_values[-1],
            "source": "memory_events[type=residence_city][-1]",
        }

    for field in ("query_context", "active_context", "current_context", "current_user_context"):
        context = state.get(field)
        if not isinstance(context, Mapping):
            continue
        city = context.get("city") or context.get("residence_city") or context.get("location")
        if city:
            return {
                "city": str(city),
                "source": field,
            }

    selected_city = state.get("selected_city")
    if selected_city:
        return {
            "city": str(selected_city),
            "source": "selected_city",
        }

    return None


def _doc_city(doc: Any) -> str | None:
    city = _get(doc, "city", None)
    if city:
        return str(city)
    metadata = _get(doc, "metadata", None)
    if isinstance(metadata, Mapping):
        metadata_city = metadata.get("city") or metadata.get("residence_city") or metadata.get("location")
        if metadata_city:
            return str(metadata_city)
    return None


def _checkpoint_context_for_evidence(checkpoints: list[Any]) -> list[dict[str, Any]]:
    context = []
    for checkpoint in checkpoints[-3:]:
        state = _state_from_checkpoint_like(checkpoint)
        residence_values = _residence_values(_as_list(state.get("memory_events")))
        context.append(
            {
                "checkpoint_id": _checkpoint_id(checkpoint),
                "parent_checkpoint_id": _parent_checkpoint_id(checkpoint),
                "checkpoint_ns": _get(checkpoint, "checkpoint_ns", None),
                "retrieved_doc_cities": [
                    city
                    for city in (_doc_city(doc) for doc in _as_list(state.get("retrieved_docs")))
                    if city
                ],
                "latest_residence_city": residence_values[-1] if residence_values else None,
            }
        )
    return context


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


def _find_reducer_append_duplicates(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    duplicates: list[dict[str, Any]] = []
    for channel in TRACKED_REDUCER_CHANNELS:
        values = _as_list(state.get(channel))
        if len(values) < 2:
            continue
        signatures: defaultdict[str, list[int]] = defaultdict(list)
        for index, item in enumerate(values):
            signatures[_state_item_identity(channel, item)].append(index)
        for signature, indexes in signatures.items():
            if len(indexes) < 2:
                continue
            if channel == "messages" and not _has_adjacent_indexes(indexes):
                continue
            duplicates.append(
                {
                    "state_path": channel,
                    "identity": signature,
                    "indexes": indexes,
                    "count": len(indexes),
                    "first_value_preview": _preview(_jsonable(values[indexes[0]])),
                }
            )
    return duplicates


def _has_adjacent_indexes(indexes: list[int]) -> bool:
    return any(right == left + 1 for left, right in zip(indexes, indexes[1:]))


def _find_unexpected_parent_checkpoints(checkpoints: list[Any]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    seen_ids = {_checkpoint_id(item) for item in checkpoints if _checkpoint_id(item)}
    for previous, current in zip(checkpoints, checkpoints[1:]):
        current_id = _checkpoint_id(current)
        parent_id = _parent_checkpoint_id(current)
        previous_id = _checkpoint_id(previous)
        checkpoint_ns = _get(current, "checkpoint_ns", None)
        previous_checkpoint_ns = _get(previous, "checkpoint_ns", None)
        if not current_id or not parent_id:
            continue
        if parent_id == previous_id:
            continue
        anomalies.append(
            {
                "checkpoint_id": current_id,
                "parent_checkpoint_id": parent_id,
                "expected_previous_checkpoint_id": previous_id,
                "parent_present_in_timeline": parent_id in seen_ids,
                "checkpoint_ns": checkpoint_ns,
                "previous_checkpoint_ns": previous_checkpoint_ns,
                "same_namespace_as_previous": checkpoint_ns == previous_checkpoint_ns,
                "suggested_action": "Confirm the intended resume checkpoint, checkpoint_ns, and branch before treating this lineage jump as application state corruption.",
            }
        )
    return anomalies


def _find_checkpoint_namespace_confusion(checkpoints: list[Any]) -> list[dict[str, Any]]:
    by_thread: defaultdict[str, list[tuple[int, Any]]] = defaultdict(list)
    for index, checkpoint in enumerate(checkpoints):
        thread_id = str(_get(checkpoint, "thread_id", "") or "__unknown_thread__")
        by_thread[thread_id].append((index, checkpoint))

    findings: list[dict[str, Any]] = []
    for thread_id, indexed_checkpoints in sorted(by_thread.items()):
        by_namespace: defaultdict[str, list[tuple[int, Any]]] = defaultdict(list)
        for index, checkpoint in indexed_checkpoints:
            namespace = str(_get(checkpoint, "checkpoint_ns", "") or "")
            by_namespace[namespace].append((index, checkpoint))

        if len(by_namespace) < 2:
            continue

        latest_by_namespace: list[dict[str, Any]] = []
        signatures: set[str] = set()
        for namespace, items in sorted(by_namespace.items()):
            latest_index, latest_checkpoint = max(
                items,
                key=lambda item: _checkpoint_order_key(item[1], item[0]),
            )
            summary = _namespace_latest_summary(namespace, latest_checkpoint, latest_index)
            signatures.add(summary["state_signature"])
            latest_by_namespace.append(summary)

        duplicated_checkpoint_ids = _checkpoint_ids_shared_across_namespaces(by_namespace)
        if len(signatures) < 2 and not duplicated_checkpoint_ids:
            continue

        findings.append(
            {
                "thread_id": None if thread_id == "__unknown_thread__" else thread_id,
                "namespaces": sorted(by_namespace),
                "latest_by_namespace": [
                    {
                        key: value
                        for key, value in summary.items()
                        if key != "state_signature"
                    }
                    for summary in latest_by_namespace
                ],
                "duplicated_checkpoint_ids": duplicated_checkpoint_ids,
                "suggested_action": "Switch checkpoint_ns deliberately and compare the latest checkpoint before debugging state as missing or stale.",
            }
        )

    return findings


def _checkpoint_ids_shared_across_namespaces(
    by_namespace: Mapping[str, list[tuple[int, Any]]]
) -> list[dict[str, Any]]:
    namespaces_by_checkpoint: defaultdict[str, set[str]] = defaultdict(set)
    for namespace, items in by_namespace.items():
        for _, checkpoint in items:
            checkpoint_id = _checkpoint_id(checkpoint)
            if checkpoint_id:
                namespaces_by_checkpoint[checkpoint_id].add(namespace)
    return [
        {"checkpoint_id": checkpoint_id, "namespaces": sorted(namespaces)}
        for checkpoint_id, namespaces in sorted(namespaces_by_checkpoint.items())
        if len(namespaces) > 1
    ]


def _namespace_latest_summary(namespace: str, checkpoint: Any, index: int) -> dict[str, Any]:
    state = _state_from_checkpoint_like(checkpoint)
    channel_names = _checkpoint_channel_names(checkpoint, state)
    state_summary = {
        "channel_names": channel_names,
        "selected_city": state.get("selected_city") if isinstance(state, Mapping) else None,
        "memory_event_values": [
            _get(event, "value")
            for event in _as_list(state.get("memory_events") if isinstance(state, Mapping) else None)
            if _get(event, "value") is not None
        ],
        "retrieved_doc_cities": [
            _get(doc, "city")
            for doc in _as_list(state.get("retrieved_docs") if isinstance(state, Mapping) else None)
            if _get(doc, "city") is not None
        ],
    }
    return {
        "checkpoint_ns": namespace,
        "checkpoint_id": _checkpoint_id(checkpoint),
        "parent_checkpoint_id": _parent_checkpoint_id(checkpoint),
        "rowid": _get(checkpoint, "rowid", None),
        "ordinal": _get(checkpoint, "ordinal", _get(checkpoint, "step", index)),
        "state_summary": _jsonable(state_summary),
        "state_signature": repr(_jsonable(state_summary)),
    }


def _state_from_checkpoint_like(checkpoint: Any) -> Mapping[str, Any]:
    state = _get(checkpoint, "state", None)
    if isinstance(state, Mapping):
        return state

    raw_checkpoint = _get(checkpoint, "checkpoint", None)
    if isinstance(raw_checkpoint, Mapping):
        value = raw_checkpoint.get("value")
        if isinstance(value, Mapping) and isinstance(value.get("channel_values"), Mapping):
            return value["channel_values"]
        if isinstance(raw_checkpoint.get("channel_values"), Mapping):
            return raw_checkpoint["channel_values"]
    return {}


def _checkpoint_channel_names(checkpoint: Any, state: Mapping[str, Any]) -> list[str]:
    channel_names = _get(checkpoint, "channel_names", None)
    if isinstance(channel_names, list):
        return sorted(str(item) for item in channel_names)
    return sorted(str(key) for key in state.keys())


def _checkpoint_order_key(checkpoint: Any, fallback_index: int) -> tuple[int, int]:
    for priority, key in ((3, "rowid"), (2, "ordinal"), (1, "step")):
        value = _to_int(_get(checkpoint, key, None))
        if value is not None:
            return (priority, value)
    return (0, fallback_index)


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


def _state_item_identity(channel: str, item: Any) -> str:
    if channel == "messages":
        summary = _message_summary(item)
        return f"{summary.get('type', '')}:{summary.get('content_preview', '')}"
    if channel == "memory_events":
        return _memory_event_identity(_jsonable(item))
    if channel == "retrieved_docs":
        return _doc_identity(_doc_summary(item))
    return _preview(_jsonable(item))


def _checkpoint_id(checkpoint: Any) -> str | None:
    value = _get(checkpoint, "checkpoint_id", _get(checkpoint, "id", None))
    return str(value) if value else None


def _parent_checkpoint_id(checkpoint: Any) -> str | None:
    value = _get(checkpoint, "parent_checkpoint_id", _get(checkpoint, "parentId", None))
    return str(value) if value else None


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
