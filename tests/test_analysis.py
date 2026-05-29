from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lgmi.analysis import diff_states, run_diagnostics, summarize_writes


def test_diff_states_summarizes_relocation_demo_fields() -> None:
    before = {
        "messages": [{"type": "human", "content": "I live in Shanghai."}],
        "memory_events": [
            {
                "type": "residence_city",
                "value": "Shanghai",
                "source": "extract_profile",
                "evidence": "I live in Shanghai.",
            }
        ],
        "retrieved_docs": [],
        "diagnostics": [],
        "selected_city": "Shanghai",
    }
    after = {
        "messages": [
            {"type": "human", "content": "I live in Shanghai."},
            {"type": "human", "content": "I moved to Hangzhou last week."},
        ],
        "memory_events": [
            {
                "type": "residence_city",
                "value": "Shanghai",
                "source": "extract_profile",
                "evidence": "I live in Shanghai.",
            },
            {
                "type": "residence_city",
                "value": "Hangzhou",
                "source": "extract_profile",
                "evidence": "I moved to Hangzhou last week.",
            },
        ],
        "retrieved_docs": [
            {
                "city": "Shanghai",
                "source": "local_policy_fixture/shanghai",
                "content": "Shanghai residency services often depend on residence permit status.",
            }
        ],
        "diagnostics": ["conflicting_residence_memory"],
        "selected_city": "Shanghai",
        "extra_debug": {"checkpoint": "after-retrieve"},
    }

    diff = diff_states(before, after)

    assert diff["added"] == {"extra_debug": {"checkpoint": "after-retrieve"}}
    assert set(diff["changed"]) == {"diagnostics", "memory_events", "messages", "retrieved_docs"}
    assert diff["summary"]["messages"]["delta"] == 1
    assert diff["summary"]["memory_events"]["latest_residence_city"] == "Hangzhou"
    assert diff["summary"]["memory_events"]["introduced_conflict"] is True
    assert diff["summary"]["retrieved_docs"]["sources"] == ["local_policy_fixture/shanghai"]
    assert diff["summary"]["selected_city"]["changed"] is False
    assert diff["summary"]["diagnostics"]["added"] == ["conflicting_residence_memory"]


def test_run_diagnostics_detects_memory_staleness_growth_and_duplicates() -> None:
    state = {
        "messages": [
            {"type": "human", "content": f"turn {index}"}
            for index in range(6)
        ],
        "memory_events": [
            {
                "type": "residence_city",
                "value": "Shanghai",
                "source": "extract_profile",
                "evidence": "I live in Shanghai.",
            },
            {
                "type": "residence_city",
                "value": "Hangzhou",
                "source": "extract_profile",
                "evidence": "I moved to Hangzhou last week.",
            },
        ],
        "retrieved_docs": [
            {
                "city": "Shanghai",
                "source": "local_policy_fixture/shanghai",
                "content": "Shanghai residency services often depend on residence permit status.",
            },
            {
                "city": "Shanghai",
                "source": "local_policy_fixture/shanghai",
                "content": "Shanghai residency services often depend on residence permit status.",
            },
        ],
        "diagnostics": [],
        "selected_city": "Shanghai",
    }
    writes = [
        {
            "task_id": "task-profile-2",
            "channel": "memory_events",
            "node": "extract_profile",
            "value": state["memory_events"],
        }
    ]
    checkpoints = [
        {"checkpoint_id": "cp-1", "byte_size": 1000},
        {"checkpoint_id": "cp-2", "byte_size": 1600},
        {"checkpoint_id": "cp-3", "byte_size": 4000},
    ]

    diagnostics = run_diagnostics(state, writes=writes, checkpoints=checkpoints)
    by_id = {item["id"]: item for item in diagnostics}

    assert set(by_id) == {
        "checkpoint_size_spike",
        "conflicting_residence_memory",
        "oversized_message_history",
        "repeated_retrieved_context",
        "stale_selected_city",
    }
    assert by_id["conflicting_residence_memory"]["severity"] == "error"
    assert by_id["conflicting_residence_memory"]["evidence"]["values"] == ["Shanghai", "Hangzhou"]
    assert by_id["conflicting_residence_memory"]["evidence"]["write_summary"][0]["channel"] == "memory_events"
    assert by_id["stale_selected_city"]["evidence"]["latest_residence_city"] == "Hangzhou"
    assert by_id["oversized_message_history"]["evidence"]["message_count"] == 6
    assert by_id["repeated_retrieved_context"]["evidence"]["duplicates"][0]["count"] == 2
    assert by_id["checkpoint_size_spike"]["evidence"]["spikes"][0]["to_checkpoint_id"] == "cp-3"


def test_summarize_writes_groups_by_channel_and_task_id() -> None:
    writes = [
        {
            "task_id": "task-a",
            "channel": "memory_events",
            "node": "extract_profile",
            "idx": 0,
            "value": {"type": "residence_city", "value": "Shanghai"},
        },
        {
            "task_id": "task-a",
            "channel": "memory_events",
            "node": "extract_profile",
            "idx": 1,
            "value": {"type": "residence_city", "value": "Hangzhou"},
        },
        {
            "task_id": "task-b",
            "channel": "selected_city",
            "node": "retrieve_policy",
            "idx": 0,
            "value": "Shanghai",
        },
    ]

    summary = summarize_writes(writes)

    assert summary == [
        {
            "channel": "memory_events",
            "task_id": "task-a",
            "count": 2,
            "nodes": ["extract_profile"],
            "writes": [
                {
                    "index": 0,
                    "channel": "memory_events",
                    "task_id": "task-a",
                    "node": "extract_profile",
                    "value_preview": "{'type': 'residence_city', 'value': 'Shanghai'}",
                },
                {
                    "index": 1,
                    "channel": "memory_events",
                    "task_id": "task-a",
                    "node": "extract_profile",
                    "value_preview": "{'type': 'residence_city', 'value': 'Hangzhou'}",
                },
            ],
        },
        {
            "channel": "selected_city",
            "task_id": "task-b",
            "count": 1,
            "nodes": ["retrieve_policy"],
            "writes": [
                {
                    "index": 0,
                    "channel": "selected_city",
                    "task_id": "task-b",
                    "node": "retrieve_policy",
                    "value_preview": "Shanghai",
                }
            ],
        },
    ]
