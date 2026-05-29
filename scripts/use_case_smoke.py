from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from examples.relocation_policy_agent.run_demo import DB_PATH, THREAD_ID, run_demo
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


def collect_use_case_evidence(db_path: Path) -> UseCaseEvidence:
    reader = SQLiteCheckpointReader(db_path)
    summary = reader.summary()
    threads = reader.list_threads()
    if not threads:
        raise RuntimeError("No threads found in checkpoint database.")

    thread_id = THREAD_ID if any(item["thread_id"] == THREAD_ID for item in threads) else threads[0]["thread_id"]
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


def render_report(evidence: UseCaseEvidence) -> None:
    console = Console()
    console.print(
        Panel.fit(
            "用例：开发者正在排查一个 Agent。它已经记住用户搬到了杭州，"
            "但最终回答仍然基于上海检索上下文。",
            title="LangGraph Memory Inspector 用例冒烟测试",
        )
    )

    summary = Table(title="观察到的证据")
    summary.add_column("问题")
    summary.add_column("观察结果")
    summary.add_column("为什么重要")
    summary.add_row("最新居住地记忆", evidence.latest_residence_city or "（缺失）", "确认用户最新画像状态。")
    summary.add_row("最终 selected_city", evidence.final_selected_city or "（缺失）", "说明检索 bug 仍然可见。")
    summary.add_row("检索文档城市", ", ".join(evidence.retrieved_cities), "说明回答依据仍停留在 stale 上下文。")
    summary.add_row("checkpoint 行数", str(evidence.checkpoint_count), "给检查器提供真实时间线。")
    summary.add_row("write 行数", str(evidence.write_count), "提供 node/channel 归因证据。")
    console.print(summary)

    timeline = Table(title="诊断路径")
    timeline.add_column("步骤")
    timeline.add_column("Checkpoint")
    timeline.add_column("证据")
    timeline.add_row("1", evidence.hangzhou_write_checkpoint_id or "（未找到）", "Hangzhou 出现在一次 memory_events 写入中。")
    timeline.add_row("2", evidence.first_conflict_checkpoint_id or "（未找到）", "两个 residence_city 值同时处于 active 状态。")
    timeline.add_row("3", evidence.first_stale_checkpoint_id or "（未找到）", "selected_city 与最新居住地开始不一致。")
    timeline.add_row("4", evidence.final_checkpoint_id, "最终回答 checkpoint 仍然基于 Shanghai。")
    console.print(timeline)

    diagnostics = Table(title="诊断结果")
    diagnostics.add_column("ID")
    diagnostics.add_column("严重程度")
    diagnostics.add_column("证据")
    for item in evidence.diagnostics:
        diagnostics.add_row(item["id"], item["severity"], _shorten(item.get("evidence")))
    console.print(diagnostics)

    if evidence.passed:
        console.print("[bold green]PASS[/bold green] 检查器证据链已经证明 stale memory 故障路径。")
    else:
        console.print("[bold red]FAIL[/bold red] 用例证据链不完整。")


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


def _shorten(value: Any) -> str:
    text = str(value)
    return f"{text[:180]}..." if len(text) > 180 else text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行搬家记忆故障用例冒烟测试。")
    parser.add_argument(
        "--db-path",
        default=str(DB_PATH),
        help="LangGraph SQLite checkpoint 数据库路径。",
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="测试前重新生成 demo checkpoint 数据库。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db_path).expanduser().resolve()
    if args.reset_demo:
        run_demo(reset=True, use_llm=False)

    evidence = collect_use_case_evidence(db_path)
    render_report(evidence)
    return 0 if evidence.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
