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
        },
        {
            "task_id": "task-chat-6",
            "channel": "messages",
            "node": "chat_model",
            "value": state["messages"][-1:],
        },
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
        "stale_retrieved_context",
        "stale_selected_city",
    }
    assert by_id["conflicting_residence_memory"]["severity"] == "error"
    assert by_id["conflicting_residence_memory"]["evidence"]["values"] == ["Shanghai", "Hangzhou"]
    assert any(
        item["channel"] == "memory_events"
        for item in by_id["conflicting_residence_memory"]["evidence"]["write_summary"]
    )
    assert by_id["stale_selected_city"]["evidence"]["latest_residence_city"] == "Hangzhou"
    assert by_id["oversized_message_history"]["evidence"]["message_count"] == 6
    assert by_id["oversized_message_history"]["evidence"]["state_path"] == "messages"
    assert by_id["oversized_message_history"]["evidence"]["role_counts"] == {"human": 6}
    assert by_id["oversized_message_history"]["evidence"]["write_summary"][0]["channel"] == "messages"
    assert "trimming" in by_id["oversized_message_history"]["evidence"]["suggested_action"]
    assert by_id["repeated_retrieved_context"]["evidence"]["duplicates"][0]["count"] == 2
    assert by_id["stale_retrieved_context"]["evidence"]["expected_city"] == "Hangzhou"
    assert by_id["stale_retrieved_context"]["evidence"]["stale_docs"][0]["city"] == "Shanghai"
    assert by_id["stale_retrieved_context"]["evidence"]["state_path"] == "retrieved_docs"
    assert by_id["checkpoint_size_spike"]["evidence"]["spikes"][0]["to_checkpoint_id"] == "cp-3"


def test_run_diagnostics_detects_stale_rag_context_from_query_context() -> None:
    state = {
        "query_context": {
            "city": "Hangzhou",
            "task": "answer local benefits question",
        },
        "retrieved_docs": [
            {
                "city": "Shanghai",
                "source": "benefits/shanghai-legacy",
                "content": "Shanghai local benefits require district-level application.",
            },
            {
                "city": "Hangzhou",
                "source": "benefits/hangzhou-current",
                "content": "Hangzhou benefits depend on Zhejiang registration.",
            },
        ],
    }
    writes = [
        {
            "task_id": "task-rag",
            "channel": "retrieved_docs",
            "node": "retrieve_benefits",
            "value": state["retrieved_docs"],
        }
    ]
    checkpoints = [
        {
            "checkpoint_id": "cp-before-rag",
            "parent_checkpoint_id": None,
            "state": {
                "query_context": state["query_context"],
                "retrieved_docs": [],
            },
        },
        {
            "checkpoint_id": "cp-after-rag",
            "parent_checkpoint_id": "cp-before-rag",
            "state": state,
        },
    ]

    diagnostics = run_diagnostics(state, writes=writes, checkpoints=checkpoints)
    by_id = {item["id"]: item for item in diagnostics}

    assert "stale_retrieved_context" in by_id
    evidence = by_id["stale_retrieved_context"]["evidence"]
    assert evidence["expected_city"] == "Hangzhou"
    assert evidence["expected_city_source"] == "query_context"
    assert evidence["retrieved_doc_count"] == 2
    assert evidence["matching_doc_count"] == 1
    assert evidence["stale_docs"] == [
        {
            "index": 0,
            "city": "Shanghai",
            "source": "benefits/shanghai-legacy",
            "content_preview": "Shanghai local benefits require district-level application.",
        }
    ]
    assert evidence["write_summary"][0]["channel"] == "retrieved_docs"
    assert evidence["checkpoint_context"][-1]["checkpoint_id"] == "cp-after-rag"
    assert evidence["checkpoint_context"][-1]["retrieved_doc_cities"] == ["Shanghai", "Hangzhou"]


def test_run_diagnostics_detects_reducer_append_duplicates() -> None:
    duplicate_memory = {
        "type": "profile_fact",
        "value": "prefers subway",
        "source": "extract_profile",
        "evidence": "I usually take the subway.",
    }
    state = {
        "messages": [
            {"type": "human", "content": "I usually take the subway."},
            {"type": "human", "content": "I usually take the subway."},
        ],
        "memory_events": [
            duplicate_memory,
            duplicate_memory,
        ],
        "retrieved_docs": [],
    }
    writes = [
        {
            "task_id": "task-reducer",
            "channel": "memory_events",
            "node": "extract_profile",
            "value": state["memory_events"],
        }
    ]

    diagnostics = run_diagnostics(state, writes=writes)
    by_id = {item["id"]: item for item in diagnostics}

    assert "reducer_append_duplicate_state" in by_id
    duplicates = by_id["reducer_append_duplicate_state"]["evidence"]["duplicates"]
    assert {item["state_path"] for item in duplicates} >= {"messages", "memory_events"}
    assert duplicates[0]["indexes"] == [0, 1]
    assert by_id["reducer_append_duplicate_state"]["evidence"]["write_summary"][0]["channel"] == "memory_events"


def test_run_diagnostics_detects_unexpected_parent_checkpoint() -> None:
    checkpoints = [
        {"checkpoint_id": "cp-1", "checkpoint_ns": "main", "parent_checkpoint_id": None, "byte_size": 100},
        {"checkpoint_id": "cp-2", "checkpoint_ns": "main", "parent_checkpoint_id": "cp-1", "byte_size": 120},
        {"checkpoint_id": "cp-4", "checkpoint_ns": "main", "parent_checkpoint_id": "cp-1", "byte_size": 130},
    ]

    diagnostics = run_diagnostics({}, checkpoints=checkpoints)
    by_id = {item["id"]: item for item in diagnostics}

    assert "unexpected_parent_checkpoint" in by_id
    anomaly = by_id["unexpected_parent_checkpoint"]["evidence"]["anomalies"][0]
    assert anomaly["checkpoint_id"] == "cp-4"
    assert anomaly["parent_checkpoint_id"] == "cp-1"
    assert anomaly["expected_previous_checkpoint_id"] == "cp-2"
    assert anomaly["parent_present_in_timeline"] is True
    assert anomaly["same_namespace_as_previous"] is True
    assert "resume checkpoint" in anomaly["suggested_action"]


def test_run_diagnostics_detects_checkpoint_namespace_confusion() -> None:
    checkpoints = [
        {
            "thread_id": "thread-ns-demo",
            "checkpoint_ns": "production",
            "checkpoint_id": "prod-cp-1",
            "parent_checkpoint_id": None,
            "rowid": 1,
            "checkpoint": {
                "value": {
                    "channel_values": {
                        "selected_city": "Shanghai",
                        "memory_events": [{"type": "residence_city", "value": "Shanghai"}],
                    }
                }
            },
        },
        {
            "thread_id": "thread-ns-demo",
            "checkpoint_ns": "production",
            "checkpoint_id": "prod-cp-2",
            "parent_checkpoint_id": "prod-cp-1",
            "rowid": 2,
            "checkpoint": {
                "value": {
                    "channel_values": {
                        "selected_city": "Hangzhou",
                        "memory_events": [{"type": "residence_city", "value": "Hangzhou"}],
                    }
                }
            },
        },
        {
            "thread_id": "thread-ns-demo",
            "checkpoint_ns": "shadow_replay",
            "checkpoint_id": "shadow-cp-1",
            "parent_checkpoint_id": None,
            "rowid": 3,
            "checkpoint": {
                "value": {
                    "channel_values": {
                        "messages": [{"type": "human", "content": "replay only"}],
                    }
                }
            },
        },
    ]

    diagnostics = run_diagnostics({}, checkpoints=checkpoints)
    by_id = {item["id"]: item for item in diagnostics}

    assert "checkpoint_namespace_confusion" in by_id
    evidence = by_id["checkpoint_namespace_confusion"]["evidence"]["threads"][0]
    assert evidence["thread_id"] == "thread-ns-demo"
    assert evidence["namespaces"] == ["production", "shadow_replay"]
    latest_by_ns = {item["checkpoint_ns"]: item for item in evidence["latest_by_namespace"]}
    assert latest_by_ns["production"]["state_summary"]["selected_city"] == "Hangzhou"
    assert latest_by_ns["shadow_replay"]["state_summary"]["channel_names"] == ["messages"]


def test_run_diagnostics_does_not_flag_matching_namespaces() -> None:
    checkpoints = [
        {
            "thread_id": "thread-ns-demo",
            "checkpoint_ns": namespace,
            "checkpoint_id": f"{namespace}-cp-1",
            "rowid": rowid,
            "state": {
                "selected_city": "Hangzhou",
                "memory_events": [{"type": "residence_city", "value": "Hangzhou"}],
            },
        }
        for rowid, namespace in enumerate(["production", "shadow_replay"], start=1)
    ]

    diagnostics = run_diagnostics({}, checkpoints=checkpoints)

    assert "checkpoint_namespace_confusion" not in {item["id"] for item in diagnostics}


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
