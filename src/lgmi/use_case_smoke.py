from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lgmi.analysis import run_diagnostics
from lgmi.checkpoint_reader import SQLiteCheckpointReader


@dataclass
class UseCaseEvidence:
    db_path: Path
    thread_id: str
    checkpoint_count: int
    write_count: int
    final_checkpoint_id: str
    final_selected_city: str | None
    latest_residence_city: str | None
    residence_values: list[str]
    retrieved_cities: list[str]
    diagnostics: list[dict[str, Any]]
    first_conflict_checkpoint_id: str | None
    first_stale_checkpoint_id: str | None
    hangzhou_write_checkpoint_id: str | None

    @property
    def passed(self) -> bool:
        diagnostic_ids = {item["id"] for item in self.diagnostics}
        return (
            self.latest_residence_city == "Hangzhou"
            and self.final_selected_city == "Shanghai"
            and "Shanghai" in self.retrieved_cities
            and "conflicting_residence_memory" in diagnostic_ids
            and "stale_selected_city" in diagnostic_ids
            and self.first_conflict_checkpoint_id is not None
            and self.first_stale_checkpoint_id is not None
            and self.hangzhou_write_checkpoint_id is not None
        )

    def to_report(self) -> dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "thread_id": self.thread_id,
            "checkpoint_count": self.checkpoint_count,
            "write_count": self.write_count,
            "final_checkpoint_id": self.final_checkpoint_id,
            "final_selected_city": self.final_selected_city,
            "latest_residence_city": self.latest_residence_city,
            "residence_values": self.residence_values,
            "retrieved_cities": self.retrieved_cities,
            "diagnostics": [
                {
                    "id": str(item["id"]),
                    "severity": str(item["severity"]),
                    "title": str(item["title"]),
                }
                for item in self.diagnostics
            ],
            "diagnostic_ids": [str(item["id"]) for item in self.diagnostics],
            "first_conflict_checkpoint_id": self.first_conflict_checkpoint_id,
            "first_stale_checkpoint_id": self.first_stale_checkpoint_id,
            "hangzhou_write_checkpoint_id": self.hangzhou_write_checkpoint_id,
            "passed": self.passed,
            "privacy": (
                "This proof report excludes diagnostic evidence payloads, "
                "message content, prompts, tokens, and raw database rows."
            ),
        }


def collect_use_case_evidence(db_path: Path) -> UseCaseEvidence:
    reader = SQLiteCheckpointReader(db_path)
    summary = reader.summary()
    threads = reader.list_threads()
    if not threads:
        raise RuntimeError("No threads found in checkpoint database.")

    demo = _load_relocation_demo()
    preferred_thread_id = getattr(demo, "THREAD_ID", None)
    thread_id = (
        preferred_thread_id
        if preferred_thread_id and any(item["thread_id"] == preferred_thread_id for item in threads)
        else threads[0]["thread_id"]
    )
    checkpoints = reader.list_checkpoints(thread_id)
    full_checkpoints = [
        checkpoint
        for checkpoint in (
            reader.get_checkpoint(thread_id, item["checkpoint_id"])
            for item in checkpoints
        )
        if checkpoint is not None
    ]
    final_checkpoint = full_checkpoints[-1]
    final_state = _state_from_checkpoint(final_checkpoint)

    all_writes = [
        write
        for checkpoint in checkpoints
        for write in reader.list_writes(thread_id, checkpoint["checkpoint_id"])
    ]
    diagnostics = run_diagnostics(final_state, writes=all_writes, checkpoints=checkpoints)

    return UseCaseEvidence(
        db_path=db_path,
        thread_id=thread_id,
        checkpoint_count=int(summary["checkpoint_count"]),
        write_count=int(summary["write_count"]),
        final_checkpoint_id=str(final_checkpoint["checkpoint_id"]),
        final_selected_city=_optional_str(final_state.get("selected_city")),
        latest_residence_city=_latest_residence_city(final_state),
        residence_values=_residence_values(final_state),
        retrieved_cities=_retrieved_cities(final_state),
        diagnostics=diagnostics,
        first_conflict_checkpoint_id=_first_checkpoint_matching(full_checkpoints, _has_conflicting_residence),
        first_stale_checkpoint_id=_first_checkpoint_matching(full_checkpoints, _has_stale_selected_city),
        hangzhou_write_checkpoint_id=_first_write_checkpoint(all_writes, "memory_events", "Hangzhou"),
    )


def reset_demo_checkpoint_data() -> Path:
    demo = _load_relocation_demo()
    if demo is None:
        raise RuntimeError(
            "Relocation demo source not found. Run from a source checkout of "
            "langgraph-memory-inspector."
        )
    with contextlib.redirect_stdout(io.StringIO()):
        demo.run_demo(reset=True, use_llm=False)
    return Path(demo.DB_PATH)


def default_demo_db_path() -> Path:
    demo = _load_relocation_demo()
    if demo is None:
        raise RuntimeError(
            "Relocation demo source not found. Run from a source checkout of "
            "langgraph-memory-inspector."
        )
    return Path(demo.DB_PATH)


def render_report(evidence: UseCaseEvidence) -> None:
    console = Console()
    console.print(
        Panel.fit(
            "Use case: a developer is debugging an agent that remembered the "
            "user moved to Hangzhou, but still answered from Shanghai context.",
            title="LangGraph Memory Inspector Proof",
        )
    )

    summary = Table(title="Observed Evidence")
    summary.add_column("Question")
    summary.add_column("Observation")
    summary.add_column("Why it matters")
    summary.add_row("Latest residence memory", evidence.latest_residence_city or "(missing)", "Confirms the newest user profile state.")
    summary.add_row("Final selected_city", evidence.final_selected_city or "(missing)", "Shows the retrieval bug is still visible.")
    summary.add_row("Retrieved document cities", ", ".join(evidence.retrieved_cities), "Shows the answer stayed grounded in stale context.")
    summary.add_row("Checkpoint rows", str(evidence.checkpoint_count), "Gives the inspector a real timeline.")
    summary.add_row("Write rows", str(evidence.write_count), "Provides node/channel attribution evidence.")
    console.print(summary)

    timeline = Table(title="Diagnostic Path")
    timeline.add_column("Step")
    timeline.add_column("Checkpoint")
    timeline.add_column("Evidence")
    timeline.add_row("1", evidence.hangzhou_write_checkpoint_id or "(not found)", "Hangzhou appears in a memory_events write.")
    timeline.add_row("2", evidence.first_conflict_checkpoint_id or "(not found)", "Two active residence_city values exist together.")
    timeline.add_row("3", evidence.first_stale_checkpoint_id or "(not found)", "selected_city first diverges from the latest residence.")
    timeline.add_row("4", evidence.final_checkpoint_id, "The final answer checkpoint is still grounded in Shanghai.")
    console.print(timeline)

    diagnostics = Table(title="Diagnostics")
    diagnostics.add_column("ID")
    diagnostics.add_column("Severity")
    diagnostics.add_column("Safe summary")
    for item in evidence.diagnostics:
        diagnostics.add_row(item["id"], item["severity"], _diagnostic_safe_summary(item))
    console.print(diagnostics)

    if evidence.passed:
        console.print("[bold green]PASS[/bold green] The checkpoint evidence proves the stale-memory failure path.")
    else:
        console.print("[bold red]FAIL[/bold red] The use-case evidence chain is incomplete.")


def _load_relocation_demo() -> ModuleType | None:
    repo_root = Path(__file__).resolve().parents[2]
    demo_path = repo_root / "examples" / "relocation_policy_agent" / "run_demo.py"
    if not demo_path.exists():
        return None

    spec = importlib.util.spec_from_file_location("lgmi_relocation_use_case_demo", demo_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _state_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    payload = checkpoint.get("checkpoint", {}).get("value", {})
    if not isinstance(payload, dict):
        return {}
    channel_values = payload.get("channel_values", {})
    return channel_values if isinstance(channel_values, dict) else {}


def _residence_values(state: dict[str, Any]) -> list[str]:
    return [
        str(event["value"])
        for event in state.get("memory_events", [])
        if isinstance(event, dict)
        and event.get("type") == "residence_city"
        and event.get("value") is not None
    ]


def _latest_residence_city(state: dict[str, Any]) -> str | None:
    values = _residence_values(state)
    return values[-1] if values else None


def _retrieved_cities(state: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(doc["city"])
            for doc in state.get("retrieved_docs", [])
            if isinstance(doc, dict) and doc.get("city") is not None
        }
    )


def _has_conflicting_residence(state: dict[str, Any]) -> bool:
    return len(set(_residence_values(state))) > 1


def _has_stale_selected_city(state: dict[str, Any]) -> bool:
    latest = _latest_residence_city(state)
    selected = state.get("selected_city")
    return latest is not None and selected is not None and str(selected) != latest


def _first_checkpoint_matching(
    checkpoints: list[dict[str, Any]],
    predicate: Any,
) -> str | None:
    for checkpoint in checkpoints:
        if predicate(_state_from_checkpoint(checkpoint)):
            return str(checkpoint["checkpoint_id"])
    return None


def _first_write_checkpoint(writes: list[dict[str, Any]], channel: str, needle: str) -> str | None:
    for write in writes:
        if write.get("channel") != channel:
            continue
        if needle in str(write.get("value", {}).get("value", "")):
            return str(write["checkpoint_id"])
    return None


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _diagnostic_safe_summary(diagnostic: dict[str, Any]) -> str:
    evidence = diagnostic.get("evidence")
    if not isinstance(evidence, dict):
        return "No structured evidence summary."

    diagnostic_id = diagnostic.get("id")
    if diagnostic_id == "conflicting_residence_memory":
        values = evidence.get("values", [])
        return f"Residence values: {', '.join(str(value) for value in values)}"
    if diagnostic_id == "stale_selected_city":
        selected = evidence.get("selected_city")
        latest = evidence.get("latest_residence_city")
        return f"selected_city={selected}; latest_residence_city={latest}"
    if diagnostic_id == "oversized_message_history":
        return f"message_count={evidence.get('message_count')}; threshold={evidence.get('threshold')}"
    if diagnostic_id == "checkpoint_size_spike":
        spikes = evidence.get("spikes", [])
        return f"spike_count={len(spikes) if isinstance(spikes, list) else 'unknown'}"
    return "Evidence payload hidden; use the UI or a redacted bundle for details."
