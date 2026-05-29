from __future__ import annotations

import argparse
from pathlib import Path


LAUNCH_DOCS = (
    Path("docs/langchain_forum_launch_post.md"),
    Path("docs/public_launch_packet.md"),
    Path("docs/community_launch_playbook.md"),
)

REQUIRED_PHRASES = {
    "repo_url": "https://github.com/fengjikui/langgraph-memory-inspector",
    "feedback_issue": "https://github.com/fengjikui/langgraph-memory-inspector/issues/20",
    "fixture_policy": "docs/fixture_policy.md",
    "redacted_evidence": "redacted",
    "no_raw_production": "raw production",
    "real_bug_patterns": "real",
    "not_star_cta": "not",
}

FORBIDDEN_PHRASES = (
    "please star",
    "star the repo",
    "give it a star",
    "please upload your production checkpoint",
    "please share raw production checkpoint",
    "share your raw production checkpoint",
    "upload your production checkpoint",
    "paste raw checkpoint",
)


def validate_launch_copy(paths: tuple[Path, ...] = LAUNCH_DOCS) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for key, phrase in REQUIRED_PHRASES.items():
            if phrase.lower() not in lowered:
                raise ValueError(f"{path} is missing required launch copy marker {key!r}: {phrase!r}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                raise ValueError(f"{path} contains forbidden launch copy phrase: {phrase!r}")
        results.append({"path": str(path), "status": "ok"})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate public launch copy guardrails.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional launch copy paths. Defaults to the Forum post, launch packet, and playbook.",
    )
    args = parser.parse_args()
    paths = tuple(Path(path) for path in args.paths) if args.paths else LAUNCH_DOCS
    results = validate_launch_copy(paths)
    for result in results:
        print(f"OK: {result['path']} keeps launch copy guardrails.")


if __name__ == "__main__":
    main()
