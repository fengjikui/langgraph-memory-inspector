from __future__ import annotations

from pathlib import Path

from examples.relocation_policy_agent.run_demo import DB_PATH, run_demo
from lgmi.causal_chain import build_causal_chain
from lgmi.checkpoint_reader import SQLiteCheckpointReader
from lgmi.use_case_smoke import collect_use_case_evidence


def test_relocation_use_case_smoke_detects_stale_memory_path(tmp_path: Path) -> None:
    run_demo(reset=True, use_llm=False)

    evidence = collect_use_case_evidence(DB_PATH)

    assert evidence.passed
    assert evidence.latest_residence_city == "Hangzhou"
    assert evidence.final_selected_city == "Shanghai"
    assert evidence.retrieved_cities == ["Shanghai"]
    assert {item["id"] for item in evidence.diagnostics} >= {
        "conflicting_residence_memory",
        "stale_selected_city",
    }


def test_relocation_demo_causal_chain_links_final_failure_to_memory_write(tmp_path: Path) -> None:
    run_demo(reset=True, use_llm=False)

    reader = SQLiteCheckpointReader(DB_PATH)
    evidence = collect_use_case_evidence(DB_PATH)
    chain = build_causal_chain(
        reader,
        thread_id=evidence.thread_id,
        checkpoint_id=evidence.final_checkpoint_id,
        diagnostic_id="conflicting_residence_memory",
    )

    assert chain["selected_checkpoint_id"] == evidence.final_checkpoint_id
    assert chain["state_paths"] == ["memory_events[type=residence_city]"]
    assert chain["write_channels"] == ["memory_events"]
    assert chain["range"]["scanned_checkpoint_count"] == evidence.checkpoint_count
    assert any(step["relation"] == "introduced_diagnostic" for step in chain["steps"])
    assert any(
        write["channel"] == "memory_events" and "Hangzhou" in write["value_preview"]
        for step in chain["steps"]
        for write in step["writes"]
    )
