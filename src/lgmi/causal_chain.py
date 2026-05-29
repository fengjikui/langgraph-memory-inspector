from __future__ import annotations

from typing import Any, Mapping

from lgmi.adapters import CheckpointReader


DIAGNOSTIC_TARGETS: dict[str, dict[str, list[str]]] = {
    "conflicting_residence_memory": {
        "state_paths": ["memory_events[type=residence_city]"],
        "write_channels": ["memory_events"],
    },
    "stale_selected_city": {
        "state_paths": [
            "memory_events[type=residence_city]",
            "selected_city",
            "retrieved_docs",
            "messages",
        ],
        "write_channels": ["memory_events", "selected_city", "retrieved_docs", "messages"],
    },
    "reducer_append_duplicate_state": {
        "state_paths": ["messages", "memory_events"],
        "write_channels": ["messages", "memory_events"],
    },
    "oversized_message_history": {
        "state_paths": ["messages"],
        "write_channels": ["messages"],
    },
    "repeated_retrieved_context": {
        "state_paths": ["retrieved_docs"],
        "write_channels": ["retrieved_docs"],
    },
    "stale_retrieved_context": {
        "state_paths": [
            "memory_events[type=residence_city]",
            "query_context",
            "active_context",
            "retrieved_docs",
        ],
        "write_channels": ["memory_events", "query_context", "retrieved_docs"],
    },
    "checkpoint_size_spike": {
        "state_paths": ["checkpoint.byte_size"],
        "write_channels": [],
    },
    "unexpected_parent_checkpoint": {
        "state_paths": ["checkpoint.parent_checkpoint_id"],
        "write_channels": [],
    },
    "checkpoint_namespace_confusion": {
        "state_paths": ["checkpoint.checkpoint_ns"],
        "write_channels": [],
    },
}


def build_causal_chain(
    reader: CheckpointReader,
    *,
    thread_id: str,
    checkpoint_id: str,
    diagnostic_id: str,
    checkpoint_ns: str | None = None,
    max_steps: int = 8,
) -> dict[str, Any]:
    """Build a deterministic checkpoint-to-write evidence chain for a diagnostic."""
    checkpoints = reader.list_checkpoints(thread_id, checkpoint_ns)
    selected_index = next(
        (index for index, item in enumerate(checkpoints) if item.get("checkpoint_id") == checkpoint_id),
        None,
    )
    if selected_index is None:
        raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    target = DIAGNOSTIC_TARGETS.get(diagnostic_id, {})
    state_paths = target.get("state_paths", [])
    write_channels = target.get("write_channels", [])
    channel_names = {_channel_from_state_path(path) for path in state_paths}
    channel_names.update(write_channels)
    channel_names.discard("")

    previous_diagnostic_active = False
    steps: list[dict[str, Any]] = []
    scanned = checkpoints[: selected_index + 1]

    for ordinal, checkpoint_summary in enumerate(scanned, start=1):
        current_checkpoint_id = str(checkpoint_summary.get("checkpoint_id", ""))
        detail = reader.get_checkpoint(thread_id, current_checkpoint_id, checkpoint_ns) or checkpoint_summary
        state = _state_from_checkpoint(detail)
        writes = reader.list_writes(thread_id, current_checkpoint_id, checkpoint_ns)
        relevant_writes = [
            _summarize_write(write)
            for write in writes
            if str(_get(write, "channel", "")) in channel_names
        ]
        updated_channels = [str(item) for item in _as_list(detail.get("updated_channels") or checkpoint_summary.get("updated_channels"))]
        changed_channels = sorted(set(updated_channels) & channel_names)
        diagnostic_active = _diagnostic_active(diagnostic_id, state)
        introduced_diagnostic = diagnostic_active and not previous_diagnostic_active
        previous_diagnostic_active = diagnostic_active

        relevant_nodes = {
            str(write.get("node") or "")
            for write in relevant_writes
            if str(write.get("node") or "")
        }
        if (
            len(relevant_nodes) > 1
            and not introduced_diagnostic
            and current_checkpoint_id != checkpoint_id
        ):
            continue

        if not relevant_writes and not changed_channels and not introduced_diagnostic and current_checkpoint_id != checkpoint_id:
            continue

        relation = "selected_checkpoint" if current_checkpoint_id == checkpoint_id else "related_write"
        if introduced_diagnostic:
            relation = "introduced_diagnostic"

        steps.append(
            {
                "checkpoint_id": current_checkpoint_id,
                "checkpoint_ns": detail.get("checkpoint_ns", checkpoint_summary.get("checkpoint_ns", "")),
                "ordinal": ordinal,
                "node": _node_for_step(relevant_writes, changed_channels, diagnostic_id),
                "relation": relation,
                "action": _step_action(relevant_writes, changed_channels, relation),
                "state_paths": state_paths,
                "write_channels": sorted({write["channel"] for write in relevant_writes}),
                "updated_channels": changed_channels,
                "writes": relevant_writes,
                "state_preview": _state_preview(state, state_paths),
            }
        )

    if diagnostic_id == "stale_selected_city":
        introduced_index = next(
            (
                index
                for index, step in enumerate(steps)
                if step["relation"] == "introduced_diagnostic"
            ),
            None,
        )
        if introduced_index is not None:
            steps = steps[introduced_index:]

    if len(steps) > max_steps:
        steps = steps[-max_steps:]

    node_path = _node_path(steps)
    return {
        "thread_id": thread_id,
        "checkpoint_ns": checkpoint_ns if checkpoint_ns is not None else "",
        "diagnostic_id": diagnostic_id,
        "selected_checkpoint_id": checkpoint_id,
        "headline": _headline(diagnostic_id, steps, node_path),
        "node_path": node_path,
        "next_action": _next_action(steps),
        "state_paths": state_paths,
        "write_channels": write_channels,
        "range": {
            "from_checkpoint_id": checkpoints[0].get("checkpoint_id") if checkpoints else None,
            "to_checkpoint_id": checkpoint_id,
            "scanned_checkpoint_count": len(scanned),
            "returned_step_count": len(steps),
        },
        "steps": steps,
        "summary": _summary(diagnostic_id, steps),
    }


def _summary(diagnostic_id: str, steps: list[dict[str, Any]]) -> str:
    if not steps:
        return f"No direct write evidence found for {diagnostic_id}; inspect the selected state snapshot."
    write_count = sum(len(step["writes"]) for step in steps)
    return (
        f"{diagnostic_id} is linked to {len(steps)} checkpoint step(s)"
        f" and {write_count} relevant write(s)."
    )


def _headline(
    diagnostic_id: str,
    steps: list[dict[str, Any]],
    node_path: list[str],
) -> str:
    if not steps:
        return f"{diagnostic_id}: no direct write chain found"
    if node_path:
        return f"{diagnostic_id}: {' -> '.join(node_path)}"
    return f"{diagnostic_id}: {len(steps)} checkpoint step(s)"


def _node_path(steps: list[dict[str, Any]]) -> list[str]:
    path: list[str] = []
    seen: set[str] = set()
    for step in steps:
        node = str(step.get("node") or "")
        if not node or node == "diagnostic":
            continue
        if node in seen:
            continue
        seen.add(node)
        path.append(node)
    return path


def _next_action(steps: list[dict[str, Any]]) -> str:
    for step in reversed(steps):
        writes = step.get("writes")
        if not isinstance(writes, list) or not writes:
            continue
        write = writes[-1]
        if isinstance(write, Mapping):
            node = str(write.get("node") or step.get("node") or "unknown node")
            state_path = str(write.get("state_path") or "state")
            return f"Inspect {state_path} written by {node} at checkpoint {step['checkpoint_id']}."
    if steps:
        return f"Inspect checkpoint {steps[-1]['checkpoint_id']} and compare its state preview."
    return "Inspect the selected checkpoint state snapshot."


def _step_action(
    writes: list[dict[str, Any]],
    changed_channels: list[str],
    relation: str,
) -> str:
    if writes:
        nodes = _unique([str(write.get("node") or "unknown") for write in writes])
        state_paths = _unique(
            [
                str(write.get("state_path") or f"state.{write.get('channel')}")
                for write in writes
            ]
        )
        return f"{' / '.join(nodes)} wrote {', '.join(state_paths)}"
    if changed_channels:
        changed_paths = ", ".join(f"state.{channel}" for channel in changed_channels)
        return f"Checkpoint updated {changed_paths}"
    if relation == "introduced_diagnostic":
        return "Diagnostic first became active at this checkpoint"
    return "Checkpoint is part of the diagnostic range"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _summarize_write(write: Any) -> dict[str, Any]:
    channel = str(_get(write, "channel", "unknown") or "unknown")
    value = _get(write, "value", _get(write, "blob", _get(write, "data", None)))
    decoded_value = value.get("value") if isinstance(value, Mapping) and "value" in value else value
    return {
        "rowid": _get(write, "rowid", None),
        "task_id": str(_get(write, "task_id", "unknown") or "unknown"),
        "idx": _get(write, "idx", None),
        "channel": channel,
        "state_path": f"state.{channel}",
        "node": _get(write, "node", None) or _get(write, "task_path", None) or _infer_node(channel),
        "value_preview": _preview(_compact_preview_value(decoded_value)),
    }


def _state_preview(state: Mapping[str, Any], state_paths: list[str]) -> list[dict[str, str]]:
    previews = []
    for path in state_paths:
        channel = _channel_from_state_path(path)
        if channel == "checkpoint":
            continue
        previews.append(
            {
                "state_path": path,
                "value_preview": _preview(_compact_preview_value(state.get(channel))),
            }
        )
    return previews


def _diagnostic_active(diagnostic_id: str, state: Mapping[str, Any]) -> bool:
    diagnostics = state.get("diagnostics")
    if isinstance(diagnostics, list):
        for item in diagnostics:
            if item == diagnostic_id:
                return True
            if isinstance(item, Mapping) and item.get("id") == diagnostic_id:
                return True

    if diagnostic_id == "conflicting_residence_memory":
        values = {
            str(event.get("value"))
            for event in _as_list(state.get("memory_events"))
            if isinstance(event, Mapping)
            and event.get("type") == "residence_city"
            and event.get("value") is not None
        }
        return len(values) > 1

    if diagnostic_id == "stale_selected_city":
        selected_city = state.get("selected_city")
        residences = [
            event.get("value")
            for event in _as_list(state.get("memory_events"))
            if isinstance(event, Mapping)
            and event.get("type") == "residence_city"
            and event.get("value") is not None
        ]
        return bool(residences and selected_city and str(selected_city) != str(residences[-1]))

    return False


def _node_for_step(writes: list[dict[str, Any]], changed_channels: list[str], diagnostic_id: str) -> str:
    for write in writes:
        node = write.get("node")
        if node:
            return str(node)
    if changed_channels:
        return _infer_node(changed_channels[0])
    if diagnostic_id == "unexpected_parent_checkpoint":
        return "checkpoint lineage"
    return "diagnostic"


def _infer_node(channel: str) -> str:
    if channel == "memory_events":
        return "extract_profile"
    if channel in {"retrieved_docs", "selected_city"}:
        return "retrieve_policy"
    if channel == "messages":
        return "answer"
    return "unknown"


def _compact_preview_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_compact_preview_value(item) for item in value]
    if isinstance(value, Mapping):
        compact: dict[str, Any] = {}
        for key in ("type", "value", "source", "city", "role", "content"):
            if key in value:
                compact[key] = value[key]
        return compact or {str(key): _compact_preview_value(item) for key, item in value.items()}
    return value


def _state_from_checkpoint(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    value = _get(checkpoint.get("checkpoint", {}), "value", {})
    if not isinstance(value, Mapping):
        return {}
    channel_values = value.get("channel_values")
    return dict(channel_values) if isinstance(channel_values, Mapping) else {}


def _channel_from_state_path(path: str | None) -> str:
    if not path:
        return ""
    clean = path.removeprefix("state.").split("[", 1)[0].split(".", 1)[0]
    return clean


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


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
