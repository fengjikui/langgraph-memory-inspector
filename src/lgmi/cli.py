from __future__ import annotations

import argparse
import importlib.util
import sys
import webbrowser
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit, urlunsplit

import uvicorn

from lgmi.api import create_app


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "demo":
        return _run_demo(args)
    if args.command == "inspect":
        return _run_inspect(args)
    if args.command == "inspect-postgres":
        return _run_inspect_postgres(args)
    if args.command == "export-debug-bundle":
        return _run_export_debug_bundle(args)
    raise SystemExit(f"Unknown command: {args.command}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lgmi",
        description="LangGraph Memory Inspector backend tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser(
        "demo",
        help="Prepare the relocation stale-memory demo and start the local API.",
    )
    demo_parser.add_argument("--host", default="127.0.0.1")
    demo_parser.add_argument("--port", default=8765, type=int)
    demo_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the API URL in a browser.",
    )
    demo_parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Keep any existing demo checkpoint database instead of resetting it first.",
    )
    demo_parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use OpenAI for the demo answer node when OPENAI_API_KEY is set.",
    )
    demo_parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Generate demo checkpoint data and print startup steps without serving the API.",
    )

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
    postgres_parser = subparsers.add_parser(
        "inspect-postgres",
        help="Start a local API server for a LangGraph Postgres checkpoint store.",
    )
    postgres_parser.add_argument("conninfo", help="Postgres connection string or conninfo.")
    postgres_parser.add_argument("--schema", default="public")
    postgres_parser.add_argument("--host", default="127.0.0.1")
    postgres_parser.add_argument("--port", default=8000, type=int)
    postgres_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the API URL in a browser.",
    )
    export_parser = subparsers.add_parser(
        "export-debug-bundle",
        help="Export a shareable JSON evidence bundle from a SQLite checkpoint DB.",
    )
    export_parser.add_argument("db_path", help="Path to checkpoints.sqlite.")
    export_parser.add_argument("--thread-id", required=True)
    export_parser.add_argument("--checkpoint-id", required=True)
    export_parser.add_argument(
        "--checkpoint-ns",
        default=None,
        help="Checkpoint namespace to export. Use an empty string for the default namespace.",
    )
    export_parser.add_argument("--output-dir", default="exports")
    export_parser.add_argument("--context", default=2, type=int)
    export_parser.add_argument(
        "--redact",
        action="store_true",
        help="Export a redacted bundle using the default privacy denylist.",
    )
    export_parser.add_argument(
        "--redaction-mode",
        choices=["raw", "redacted"],
        default=None,
        help="Choose raw or redacted export output. Overrides --redact.",
    )
    export_parser.add_argument(
        "--redact-path",
        action="append",
        default=[],
        help="Additional dot path to redact. Can be passed multiple times.",
    )
    export_parser.add_argument(
        "--keep-path",
        action="append",
        default=[],
        help="Dot path to keep even in redacted mode. Can be passed multiple times.",
    )
    return parser.parse_args(argv)


def _run_demo(args: argparse.Namespace) -> int:
    demo = _load_relocation_demo()
    if demo is None:
        print(
            "Relocation demo source not found. Run `lgmi demo` from a source checkout "
            "of langgraph-memory-inspector.",
            file=sys.stderr,
        )
        return 2

    DB_PATH = demo.DB_PATH
    run_demo = demo.run_demo

    run_demo(reset=not args.no_reset, use_llm=args.use_llm)
    _print_demo_next_steps(DB_PATH, args.host, args.port, args.prepare_only)

    if args.prepare_only:
        return 0

    return _serve_app(
        create_app(DB_PATH),
        args,
        f"Demo checkpoint DB: {DB_PATH.resolve()}",
    )


def _run_inspect(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).expanduser().resolve()
    if not db_path.exists():
        print(f"Checkpoint database not found: {db_path}", file=sys.stderr)
        return 2

    return _serve_app(create_app(db_path), args, f"Checkpoint DB: {db_path}")


def _run_inspect_postgres(args: argparse.Namespace) -> int:
    from lgmi.postgres_reader import PostgresCheckpointReader

    reader = PostgresCheckpointReader(args.conninfo, schema=args.schema)
    return _serve_app(
        create_app(reader),
        args,
        f"Checkpoint store: {_redact_conninfo(args.conninfo)} schema={args.schema}",
    )


def _run_export_debug_bundle(args: argparse.Namespace) -> int:
    from lgmi.checkpoint_reader import SQLiteCheckpointReader
    from lgmi.export_bundle import export_debug_bundle

    db_path = Path(args.db_path).expanduser().resolve()
    if not db_path.exists():
        print(f"Checkpoint database not found: {db_path}", file=sys.stderr)
        return 2

    redaction_mode = args.redaction_mode or ("redacted" if args.redact else "raw")
    result = export_debug_bundle(
        SQLiteCheckpointReader(db_path),
        thread_id=args.thread_id,
        checkpoint_id=args.checkpoint_id,
        checkpoint_ns=args.checkpoint_ns,
        output_dir=args.output_dir,
        context=args.context,
        redaction_mode=redaction_mode,
        redact_paths=args.redact_path,
        keep_paths=args.keep_path,
    )
    print(f"Debug bundle: {result['path']}")
    print(f"File size: {result['file_size_bytes']} bytes")
    print(
        f"Redaction: {result['redaction_mode']}"
        f" ({result['redaction_count']} path(s) redacted)"
    )
    print(f"Diagnostics: {', '.join(str(item) for item in result['diagnostic_ids'])}")
    return 0


def _serve_app(app: object, args: argparse.Namespace, source_label: str) -> int:
    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{display_host}:{args.port}/api/summary"
    print(f"LangGraph Memory Inspector API: {url}", flush=True)
    print(source_label, flush=True)

    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _print_demo_next_steps(db_path: Path, host: str, port: int, prepare_only: bool) -> None:
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print(flush=True)
    print("Demo checkpoint data is ready.", flush=True)
    print(f"Checkpoint DB: {db_path.resolve()}", flush=True)
    print(
        "Debugging path: click `conflicting_residence_memory`, open Writes, then inspect the Causal chain.",
        flush=True,
    )
    if prepare_only:
        print(flush=True)
        print("Start the Inspector API:", flush=True)
        print(f"uv run lgmi inspect {db_path} --no-browser --port {port}", flush=True)
    else:
        print(flush=True)
        print(f"Inspector API will start at: http://{display_host}:{port}/api/summary", flush=True)
    print(flush=True)
    print("Start the web UI in another terminal:", flush=True)
    print("cd web", flush=True)
    print("npm install", flush=True)
    print("npm run dev", flush=True)
    print(flush=True)
    print("Open: http://127.0.0.1:5173/", flush=True)


def _load_relocation_demo() -> ModuleType | None:
    repo_root = Path(__file__).resolve().parents[2]
    demo_path = repo_root / "examples" / "relocation_policy_agent" / "run_demo.py"
    if not demo_path.exists():
        return None

    spec = importlib.util.spec_from_file_location("lgmi_relocation_demo", demo_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _redact_conninfo(conninfo: str) -> str:
    if "://" not in conninfo:
        return "<postgres conninfo>"
    try:
        parsed = urlsplit(conninfo)
    except ValueError:
        return "<postgres conninfo>"
    if "@" not in parsed.netloc:
        return conninfo
    host = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, f"***@{host}", parsed.path, parsed.query, parsed.fragment))


if __name__ == "__main__":
    raise SystemExit(main())
