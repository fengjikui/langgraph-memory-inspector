from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

import uvicorn

from lgmi.api import create_app


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "inspect":
        return _run_inspect(args)
    raise SystemExit(f"Unknown command: {args.command}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lgmi",
        description="LangGraph Memory Inspector backend tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Start a local API server for a LangGraph SQLite checkpoint DB.",
    )
    inspect_parser.add_argument("db_path", help="Path to checkpoints.sqlite.")
    inspect_parser.add_argument("--host", default="127.0.0.1")
    inspect_parser.add_argument("--port", default=8000, type=int)
    inspect_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the API URL in a browser.",
    )
    return parser.parse_args(argv)


def _run_inspect(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).expanduser().resolve()
    if not db_path.exists():
        print(f"Checkpoint database not found: {db_path}", file=sys.stderr)
        return 2

    app = create_app(db_path)
    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{display_host}:{args.port}/api/summary"
    print(f"LangGraph Memory Inspector API: {url}")
    print(f"Checkpoint DB: {db_path}")

    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
