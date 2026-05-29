from __future__ import annotations

import argparse
import os
import re
import sqlite3
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "checkpoints.sqlite"
THREAD_ID = "relocation-demo-user-001"

CITY_ALIASES = {
    "shanghai": "Shanghai",
    "上海": "Shanghai",
    "hangzhou": "Hangzhou",
    "杭州": "Hangzhou",
}

POLICY_SNIPPETS = {
    "Shanghai": [
        "Shanghai residency services often depend on residence permit status, social insurance records, and district-level rules.",
        "For public services, Shanghai users should first check residence permit renewal, social insurance continuity, and district service windows.",
    ],
    "Hangzhou": [
        "Hangzhou local benefits often depend on Zhejiang residence registration, social insurance, and talent or district-specific programs.",
        "For a recent move to Hangzhou, users should first check residence registration updates, social insurance transfer, and local talent subsidy eligibility.",
    ],
}


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    memory_events: list[dict[str, Any]]
    retrieved_docs: list[dict[str, str]]
    diagnostics: list[str]
    selected_city: str | None


def _latest_human_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _extract_city(text: str) -> str | None:
    lowered = text.lower()
    for alias, city in CITY_ALIASES.items():
        if alias in lowered or alias in text:
            return city
    return None


def extract_profile(state: AgentState) -> dict[str, Any]:
    """Intentionally append-only to create conflicting memory for the demo."""
    text = _latest_human_text(state["messages"])
    city = _extract_city(text)
    if not city:
        return {}

    event = {
        "type": "residence_city",
        "value": city,
        "source": "extract_profile",
        "evidence": text,
    }
    memory_events = [*state.get("memory_events", []), event]
    return {"memory_events": memory_events}


def audit_memory(state: AgentState) -> dict[str, Any]:
    residence_values = [
        event["value"]
        for event in state.get("memory_events", [])
        if event.get("type") == "residence_city"
    ]
    diagnostics = list(state.get("diagnostics", []))

    if len(set(residence_values)) > 1:
        marker = "conflicting_residence_memory"
        if marker not in diagnostics:
            diagnostics.append(marker)

    if len(state.get("messages", [])) >= 6:
        marker = "oversized_message_history_risk"
        if marker not in diagnostics:
            diagnostics.append(marker)

    return {"diagnostics": diagnostics}


def retrieve_policy(state: AgentState) -> dict[str, Any]:
    residence_events = [
        event
        for event in state.get("memory_events", [])
        if event.get("type") == "residence_city"
    ]
    if not residence_events:
        return {"retrieved_docs": [], "selected_city": None}

    # Demo bug: this should choose the newest residence, but it uses the first.
    selected_city = residence_events[0]["value"]
    snippets = POLICY_SNIPPETS[selected_city]
    docs = [
        {
            "city": selected_city,
            "source": f"local_policy_fixture/{selected_city.lower()}",
            "content": snippet,
        }
        for snippet in snippets
    ]
    return {"retrieved_docs": docs, "selected_city": selected_city}


def _deterministic_answer(state: AgentState) -> str:
    selected_city = state.get("selected_city") or "your current city"
    docs = state.get("retrieved_docs", [])
    diagnostics = state.get("diagnostics", [])

    lines = [
        f"I would first check {selected_city} residence services, social insurance transfer, and district-level benefit requirements.",
    ]
    if docs:
        lines.append(f"My retrieved context is from {docs[0]['source']}.")
    if diagnostics:
        lines.append(f"Internal diagnostic markers: {', '.join(diagnostics)}.")
    return " ".join(lines)


def answer(state: AgentState, use_llm: bool = False) -> dict[str, Any]:
    if use_llm and os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        prompt = [
            SystemMessage(
                content=(
                    "You are a concise relocation policy assistant. Answer from "
                    "the retrieved context. If diagnostics mention memory conflict, "
                    "warn that the profile may be stale."
                )
            ),
            HumanMessage(
                content=(
                    f"User question: {_latest_human_text(state['messages'])}\n"
                    f"Selected city: {state.get('selected_city')}\n"
                    f"Retrieved docs: {state.get('retrieved_docs', [])}\n"
                    f"Diagnostics: {state.get('diagnostics', [])}"
                )
            ),
        ]
        response = model.invoke(prompt)
        return {"messages": [response]}

    return {"messages": [AIMessage(content=_deterministic_answer(state))]}


def build_graph(use_llm: bool = False):
    graph = StateGraph(AgentState)
    graph.add_node("extract_profile", extract_profile)
    graph.add_node("audit_memory", audit_memory)
    graph.add_node("retrieve_policy", retrieve_policy)
    graph.add_node("answer", lambda state: answer(state, use_llm=use_llm))

    graph.set_entry_point("extract_profile")
    graph.add_edge("extract_profile", "audit_memory")
    graph.add_edge("audit_memory", "retrieve_policy")
    graph.add_edge("retrieve_policy", "answer")
    graph.add_edge("answer", END)
    return graph


def _initial_state() -> AgentState:
    return {
        "messages": [],
        "memory_events": [],
        "retrieved_docs": [],
        "diagnostics": [],
        "selected_city": None,
    }


def _checkpoint_count(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        try:
            return int(conn.execute("select count(*) from checkpoints").fetchone()[0])
        except sqlite3.Error:
            return 0


def _print_checkpoint_tables(console: Console, db_path: Path) -> None:
    table = Table(title="SQLite tables written by LangGraph")
    table.add_column("table")
    table.add_column("rows", justify="right")

    with sqlite3.connect(db_path) as conn:
        names = [
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table' order by name"
            ).fetchall()
        ]
        for name in names:
            safe_name = re.sub(r"[^a-zA-Z0-9_]", "", name)
            count = conn.execute(f"select count(*) from {safe_name}").fetchone()[0]
            table.add_row(name, str(count))

    console.print(table)


def run_demo(reset: bool = False, use_llm: bool = False) -> None:
    console = Console()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    for suffix in ("-shm", "-wal"):
        sidecar = Path(f"{DB_PATH}{suffix}")
        if reset and sidecar.exists():
            sidecar.unlink()

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    app = build_graph(use_llm=use_llm).compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": THREAD_ID}}
    turns = [
        "I live in Shanghai and want help tracking local benefits.",
        "I moved to Hangzhou last week. Please remember that.",
        "Which local benefits should I check first?",
    ]

    state: AgentState = _initial_state()
    console.print(Panel.fit("Running Relocation Policy Agent demo"))
    for index, user_text in enumerate(turns, start=1):
        console.print(f"\n[bold]Turn {index} user:[/bold] {user_text}")
        state["messages"] = [HumanMessage(content=user_text)]
        output = app.invoke(state, config=config)
        state = {
            "messages": output["messages"],
            "memory_events": output.get("memory_events", []),
            "retrieved_docs": output.get("retrieved_docs", []),
            "diagnostics": output.get("diagnostics", []),
            "selected_city": output.get("selected_city"),
        }
        ai_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage)]
        if ai_messages:
            console.print(f"[bold]Agent:[/bold] {ai_messages[-1].content}")

    console.print("\n[bold]Final state summary[/bold]")
    console.print(f"Memory events: {state['memory_events']}")
    console.print(f"Selected city used for retrieval: {state['selected_city']}")
    console.print(f"Diagnostics: {state['diagnostics']}")
    console.print(f"Checkpoint DB: {DB_PATH}")
    console.print(f"Checkpoint rows: {_checkpoint_count(DB_PATH)}")
    _print_checkpoint_tables(console, DB_PATH)

    console.print(
        Panel(
            "This is the bug the inspector should reveal: the newest residence is "
            "Hangzhou, but retrieval selected the first remembered city. A checkpoint "
            "timeline + state diff should point back to extract_profile and "
            "conflicting_residence_memory.",
            title="Why the inspector matters",
        )
    )

    conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete old demo DB first.")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use OpenAI for the answer node when OPENAI_API_KEY is set.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_demo(reset=args.reset, use_llm=args.use_llm)
