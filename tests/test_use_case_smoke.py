from __future__ import annotations

from pathlib import Path

from examples.relocation_policy_agent.run_demo import DB_PATH, run_demo
from scripts.use_case_smoke import collect_use_case_evidence


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
