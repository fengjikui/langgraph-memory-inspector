from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence


REPO = "fengjikui/langgraph-memory-inspector"

PATTERN_KEYWORDS = {
    "stale_memory_or_profile": ("stale memory", "profile", "residence", "selected_city"),
    "stale_retrieved_context": ("stale retrieved", "retrieved_docs", "retrieval", "rag"),
    "reducer_append_or_merge": ("reducer", "append", "merge", "duplicate"),
    "wrong_resume_or_lineage": ("resume", "parent checkpoint", "lineage", "wrong checkpoint"),
    "namespace_confusion": ("checkpoint_ns", "namespace", "namespaces"),
    "oversized_history": ("oversized", "message history", "bloat", "long history"),
    "production_store_safety": ("production", "large store", "postgres", "migration", "schema"),
}

BACKEND_KEYWORDS = {
    "sqlite": ("sqlite", "checkpoints.sqlite"),
    "postgres": ("postgres", "postgressaver", "postgresql"),
    "redis_or_custom": ("redis", "custom saver", "custom checkpoint"),
}

SAFE_EVIDENCE_KEYWORDS = {
    "redacted_debug_bundle": ("redacted bundle", "debug bundle", "export-debug-bundle"),
    "synthetic_fixture": ("synthetic", "fixture"),
    "schema_only_snapshot": ("schema-only", "schema only", "schema snapshot"),
}

RISK_KEYWORDS = ("raw production", "unredacted", "secret", "token", "password")


Runner = Callable[[Sequence[str]], str]


@dataclass(frozen=True)
class FeedbackIntake:
    issue_number: int
    title: str
    url: str
    state: str
    likely_patterns: list[str]
    likely_backends: list[str]
    safe_evidence: list[str]
    risk_flags: list[str]
    comment_count: int


def collect_feedback_intake(
    issue_number: int,
    *,
    repo: str = REPO,
    runner: Runner | None = None,
) -> FeedbackIntake:
    run = runner or _run
    raw = run(
        (
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repo,
            "--comments",
            "--json",
            "title,state,url,body,comments",
        )
    )
    issue = json.loads(raw)
    text = _issue_text(issue)

    return FeedbackIntake(
        issue_number=issue_number,
        title=str(issue.get("title", "")),
        url=str(issue.get("url", "")),
        state=str(issue.get("state", "")),
        likely_patterns=_matches(text, PATTERN_KEYWORDS) or ["needs_manual_classification"],
        likely_backends=_matches(text, BACKEND_KEYWORDS) or ["unknown_backend"],
        safe_evidence=_matches(text, SAFE_EVIDENCE_KEYWORDS) or ["no_safe_evidence_yet"],
        risk_flags=[keyword for keyword in RISK_KEYWORDS if keyword in text],
        comment_count=len(issue.get("comments", []) or []),
    )


def render_markdown(report: FeedbackIntake) -> str:
    risk_line = (
        ", ".join(f"`{item}`" for item in report.risk_flags)
        if report.risk_flags
        else "None detected from issue text. Still review attachments manually."
    )
    return "\n".join(
        [
            f"# Feedback Intake #{report.issue_number}",
            "",
            f"- Issue: [{report.title}]({report.url})",
            f"- State: `{report.state}`",
            f"- Comments: `{report.comment_count}`",
            f"- Likely patterns: {_csv_code(report.likely_patterns)}",
            f"- Likely backends: {_csv_code(report.likely_backends)}",
            f"- Safe evidence signals: {_csv_code(report.safe_evidence)}",
            f"- Risk flags: {risk_line}",
            "",
            "## Triage Checklist",
            "",
            "- [ ] Confirm no raw production checkpoint store, prompts, tokens, credentials, or unredacted user state were attached.",
            "- [ ] Ask for `doctor --issue`, a redacted debug bundle, a synthetic fixture, or schema-only backend details if evidence is missing.",
            "- [ ] Decide whether this is a new diagnostic, a fixture for an existing diagnostic, an adapter bug, or documentation friction.",
            "- [ ] If the pattern is recurring or high-impact, open a follow-up issue with one acceptance test and one validation command.",
            "- [ ] When adding a fixture or diagnostic, update `docs/diagnostic_matrix.md` in the same change.",
            "- [ ] Reply to the user with the next safe evidence step instead of asking for raw checkpoint data.",
            "",
            "## Suggested Next Reply",
            "",
            "Thanks, this looks useful for the inspector's fixture-driven diagnostic loop. "
            "Could you confirm the checkpoint backend, the state path or write channel that first showed the problem, "
            "and whether you can share a redacted bundle, synthetic fixture, or schema-only snapshot? "
            "Please do not attach raw production checkpoint data.",
        ]
    )


def _matches(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    return [name for name, keywords in groups.items() if any(keyword in text for keyword in keywords)]


def _issue_text(issue: dict[str, object]) -> str:
    comments = issue.get("comments", []) or []
    comment_text = "\n".join(
        str(comment.get("body", ""))
        for comment in comments
        if isinstance(comment, dict)
    )
    return f"{issue.get('title', '')}\n{issue.get('body', '')}\n{comment_text}".lower()


def _csv_code(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items)


def _run(command: Sequence[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Turn a GitHub feedback issue into a safe fixture/diagnostic intake checklist."
    )
    parser.add_argument("issue_number", type=int, help="GitHub issue number to triage.")
    parser.add_argument("--repo", default=REPO, help=f"GitHub repository. Defaults to {REPO}.")
    args = parser.parse_args()

    print(render_markdown(collect_feedback_intake(args.issue_number, repo=args.repo)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
