from __future__ import annotations

import argparse
from pathlib import Path

from lgmi.use_case_smoke import (
    collect_use_case_evidence,
    default_demo_db_path,
    render_report,
    reset_demo_checkpoint_data,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the relocation stale-memory use-case smoke test.")
    parser.add_argument(
        "--db-path",
        default=None,
        help="LangGraph SQLite checkpoint database path.",
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Regenerate demo checkpoint data before testing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db_path).expanduser().resolve() if args.db_path else default_demo_db_path()
    if args.reset_demo:
        db_path = reset_demo_checkpoint_data()

    evidence = collect_use_case_evidence(db_path)
    render_report(evidence)
    return 0 if evidence.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
