from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import platform
import re
import shlex
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import uvicorn

from lgmi.api import create_app


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "doctor":
        return _run_doctor(args)
    if args.command == "demo":
        return _run_demo(args)
    if args.command == "inspect":
        return _run_inspect(args)
    if args.command == "inspect-postgres":
        return _run_inspect_postgres(args)
    if args.command == "prove-demo":
        return _run_prove_demo(args)
    if args.command == "export-debug-bundle":
        return _run_export_debug_bundle(args)
    raise SystemExit(f"Unknown command: {args.command}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lgmi",
        description="LangGraph Memory Inspector backend tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check whether the local checkout is ready to run the demo and web UI.",
    )
    doctor_parser.add_argument(
        "--skip-demo",
        action="store_true",
        help="Do not generate or inspect the demo checkpoint database.",
    )
    doctor_parser.add_argument(
        "--skip-web",
        action="store_true",
        help="Skip Node.js, npm, and web UI dependency checks.",
    )
    doctor_store_group = doctor_parser.add_mutually_exclusive_group()
    doctor_store_group.add_argument(
        "--sqlite-db",
        default=None,
        help="Validate a LangGraph SQLite checkpoint database and include a safe summary.",
    )
    doctor_store_group.add_argument(
        "--postgres-conninfo",
        default=None,
        help="Validate a LangGraph Postgres checkpoint store and include a safe summary.",
    )
    doctor_parser.add_argument(
        "--postgres-schema",
        default="public",
        help="Postgres schema for --postgres-conninfo.",
    )
    output_group = doctor_parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable doctor report.",
    )
    output_group.add_argument(
        "--issue",
        action="store_true",
        help="Print a Markdown report that can be pasted into a GitHub issue.",
    )

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
    demo_ui_group = demo_parser.add_mutually_exclusive_group()
    demo_ui_group.add_argument(
        "--ui-dir",
        default=None,
        help="Directory containing a built web UI, such as web/dist. Defaults to web/dist when it exists.",
    )
    demo_ui_group.add_argument(
        "--build-ui",
        action="store_true",
        help="Install web dependencies if needed, build web/dist, and serve it with the demo API.",
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
    inspect_ui_group = inspect_parser.add_mutually_exclusive_group()
    inspect_ui_group.add_argument(
        "--ui-dir",
        default=None,
        help="Directory containing a built web UI, such as web/dist. Defaults to web/dist when it exists.",
    )
    inspect_ui_group.add_argument(
        "--build-ui",
        action="store_true",
        help="Install web dependencies if needed, build web/dist, and serve it with the inspector API.",
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
    postgres_ui_group = postgres_parser.add_mutually_exclusive_group()
    postgres_ui_group.add_argument(
        "--ui-dir",
        default=None,
        help="Directory containing a built web UI, such as web/dist. Defaults to web/dist when it exists.",
    )
    postgres_ui_group.add_argument(
        "--build-ui",
        action="store_true",
        help="Install web dependencies if needed, build web/dist, and serve it with the inspector API.",
    )
    prove_parser = subparsers.add_parser(
        "prove-demo",
        help="Run the stale-memory demo proof and report whether checkpoint evidence explains the bug.",
    )
    prove_parser.add_argument(
        "--db-path",
        default=None,
        help="Use an existing LangGraph SQLite checkpoint database instead of the default demo DB.",
    )
    prove_parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Regenerate deterministic demo checkpoint data before proving the use case.",
    )
    prove_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable evidence instead of the rich text report.",
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
    export_parser.add_argument(
        "--issue",
        action="store_true",
        help="Print a privacy-safe Markdown summary for a GitHub issue. Defaults to redacted export.",
    )
    return parser.parse_args(argv)


def _run_doctor(args: argparse.Namespace) -> int:
    report = _build_doctor_report(args)
    has_error = any(check["status"] == "ERROR" for check in report["checks"])

    if args.json:
        print(json.dumps(report, indent=2), flush=True)
    elif args.issue:
        _print_doctor_issue(report)
    else:
        _print_doctor_text(report)

    return 1 if has_error else 0


def _build_doctor_report(args: argparse.Namespace) -> dict[str, object]:
    from lgmi.checkpoint_reader import SQLiteCheckpointReader

    repo_root = Path(__file__).resolve().parents[2]
    checks: list[dict[str, str]] = []
    next_commands: list[str] = []

    def add(status: str, name: str, detail: str) -> None:
        checks.append({"status": status, "name": name, "detail": detail})

    add("OK", "Python", platform.python_version())
    add("OK", "CLI", "lgmi command imports successfully")

    demo = None
    if args.skip_demo:
        add("SKIP", "Demo checkpoint", "skipped by --skip-demo")
    else:
        demo = _load_relocation_demo()
        if demo is None:
            add(
                "ERROR",
                "Demo source",
                "examples/relocation_policy_agent/run_demo.py was not found; run from a source checkout",
            )
        else:
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    demo.run_demo(reset=True, use_llm=False)
                summary = SQLiteCheckpointReader(demo.DB_PATH).summary()
                add(
                    "OK",
                    "Demo checkpoint",
                    (
                        f"{summary['checkpoint_count']} checkpoints, "
                        f"{summary['write_count']} writes, "
                        f"{summary['diagnostics_count']} diagnostics"
                    ),
                )
            except Exception as exc:  # pragma: no cover - defensive CLI boundary
                add("ERROR", "Demo checkpoint", f"{type(exc).__name__}: {exc}")

    if args.skip_web:
        add("SKIP", "Web UI", "skipped by --skip-web")
    else:
        web_dir = repo_root / "web"
        package_json = web_dir / "package.json"
        if package_json.exists():
            add("OK", "Web source", "web/package.json exists")
        else:
            add("ERROR", "Web source", "web/package.json was not found")

        _add_command_check(checks, "Node.js", "node")
        _add_command_check(checks, "npm", "npm")

        node_modules = web_dir / "node_modules"
        if node_modules.exists():
            add("OK", "Web dependencies", "web/node_modules exists")
        else:
            add("WARN", "Web dependencies", "run `cd web && npm install` before `npm run dev`")

        web_dist = _resolve_ui_dir(None)
        if web_dist:
            add("OK", "Built web UI", "web/dist exists")
        else:
            add("WARN", "Built web UI", "run `uv run lgmi demo --build-ui` for single-server demo mode")

    has_error = any(check["status"] == "ERROR" for check in checks)
    if not has_error:
        if not args.skip_web:
            if _resolve_ui_dir(None):
                next_commands.append("uv run lgmi demo --no-browser")
            else:
                next_commands.append("uv run lgmi demo --build-ui --no-browser")
                if demo is not None:
                    next_commands.append("uv run lgmi demo --no-browser")
                next_commands.append("cd web && npm install && npm run dev")
        elif demo is not None:
            next_commands.append("uv run lgmi demo --no-browser")

    sqlite_db_summary: dict[str, object] | None = None
    if args.sqlite_db:
        sqlite_db_summary = _add_sqlite_db_checks(checks, next_commands, args.sqlite_db)
        has_error = any(check["status"] == "ERROR" for check in checks)
        if has_error:
            next_commands.clear()
    postgres_summary: dict[str, object] | None = None
    if args.postgres_conninfo:
        postgres_summary = _add_postgres_checks(
            checks,
            next_commands,
            args.postgres_conninfo,
            args.postgres_schema,
        )
        has_error = any(check["status"] == "ERROR" for check in checks)
        if has_error:
            next_commands.clear()

    ready = not has_error
    result = _doctor_result_message(
        ready=ready,
        has_sqlite_db=sqlite_db_summary is not None,
        has_postgres=postgres_summary is not None,
    )

    return {
        "tool": "langgraph-memory-inspector",
        "command": "lgmi doctor",
        "ready": ready,
        "result": result,
        "readiness": _doctor_readiness_summary(
            ready=ready,
            sqlite_db_summary=sqlite_db_summary,
            postgres_summary=postgres_summary,
            checks=checks,
        ),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "checks": checks,
        "next_commands": next_commands,
        "sqlite_db": sqlite_db_summary,
        "postgres": postgres_summary,
        "privacy": "This report does not include checkpoint state, message content, prompts, tokens, or production database rows. It may include local file paths when --sqlite-db is used and redacted host/schema details when --postgres-conninfo is used.",
    }


def _doctor_result_message(
    *,
    ready: bool,
    has_sqlite_db: bool,
    has_postgres: bool,
) -> str:
    if not ready:
        return "action required before the inspector is ready"
    if has_postgres:
        return "ready for local Postgres checkpoint inspection"
    if has_sqlite_db:
        return "ready for local SQLite checkpoint inspection"
    return "ready for the local demo path"


def _doctor_readiness_summary(
    *,
    ready: bool,
    sqlite_db_summary: dict[str, object] | None,
    postgres_summary: dict[str, object] | None,
    checks: list[dict[str, str]],
) -> str:
    if not ready:
        return "ERROR: fix listed ERROR checks before opening the inspector."

    if postgres_summary is not None:
        return (
            "READY: read-only Postgres inspection; "
            f"{postgres_summary['checkpoint_count']} checkpoints; "
            f"{postgres_summary['write_count']} writes; "
            "report excludes checkpoint state, thread ids, messages, prompts, tokens, and raw rows."
        )

    if sqlite_db_summary is not None:
        return (
            "READY: read-only SQLite inspection; "
            f"{sqlite_db_summary['checkpoint_count']} checkpoints; "
            f"{sqlite_db_summary['write_count']} writes; "
            "report excludes checkpoint state, messages, prompts, tokens, and raw rows."
        )

    demo_detail = next(
        (check["detail"] for check in checks if check["name"] == "Demo checkpoint"),
        "demo checkpoint checks passed",
    )
    if demo_detail.startswith("skipped by "):
        return "READY: requested doctor checks passed; demo checkpoint generation was skipped."
    return f"READY: local stale-memory demo path; {demo_detail}."


def _print_doctor_text(report: dict[str, object]) -> None:
    checks = list(report["checks"])  # type: ignore[index]
    next_commands = list(report["next_commands"])  # type: ignore[index]
    print("LangGraph Memory Inspector doctor", flush=True)
    print("=" * 38, flush=True)
    for check in checks:
        print(f"[{check['status']}] {check['name']}: {check['detail']}", flush=True)

    print(flush=True)
    print(str(report["readiness"]), flush=True)
    if not report["ready"]:
        print(f"Result: {report['result']}.", flush=True)
        print("Fix the ERROR item(s), then run `uv run lgmi doctor` again.", flush=True)
        return

    print(f"Result: {report['result']}.", flush=True)
    if len(next_commands) == 1:
        print("Next command:", flush=True)
        print(next_commands[0], flush=True)
    elif next_commands:
        print("Next commands:", flush=True)
        for command in next_commands:
            print(command, flush=True)


def _print_doctor_issue(report: dict[str, object]) -> None:
    print("### LangGraph Memory Inspector doctor report", flush=True)
    print(flush=True)
    print("```json", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print("```", flush=True)
    print(flush=True)
    print(
        "Privacy note: this report contains environment and demo health checks only. "
        "It does not include checkpoint state, message content, prompts, tokens, or production database rows. "
        "Review local file paths before posting publicly.",
        flush=True,
    )


def _add_command_check(
    checks: list[dict[str, str]],
    label: str,
    command: str,
) -> None:
    executable = shutil.which(command)
    if executable is None:
        checks.append({"status": "ERROR", "name": label, "detail": f"`{command}` was not found on PATH"})
        return

    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        checks.append(
            {
                "status": "ERROR",
                "name": label,
                "detail": f"could not run `{command} --version`: {exc}",
            }
        )
        return

    output_lines = (result.stdout or result.stderr).strip().splitlines()
    version = output_lines[0] if output_lines else ""
    if result.returncode == 0 and version:
        checks.append({"status": "OK", "name": label, "detail": version})
    elif result.returncode == 0:
        checks.append({"status": "OK", "name": label, "detail": executable})
    else:
        checks.append(
            {
                "status": "ERROR",
                "name": label,
                "detail": f"`{command} --version` exited {result.returncode}",
            }
        )


def _add_sqlite_db_checks(
    checks: list[dict[str, str]],
    next_commands: list[str],
    db_path: str,
) -> dict[str, object]:
    from lgmi.checkpoint_reader import SQLiteCheckpointReader

    path = Path(db_path).expanduser().resolve()
    summary: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        checks.append(
            {
                "status": "ERROR",
                "name": "SQLite checkpoint DB",
                "detail": f"database not found: {path}",
            }
        )
        return summary

    try:
        db_summary = SQLiteCheckpointReader(path).summary()
    except (FileNotFoundError, ValueError, OSError) as exc:
        checks.append(
            {
                "status": "ERROR",
                "name": "SQLite checkpoint DB",
                "detail": str(exc),
            }
        )
        summary["error"] = str(exc)
        return summary

    summary.update(
        {
            "file_size_bytes": db_summary["file_size_bytes"],
            "checkpoint_count": db_summary["checkpoint_count"],
            "write_count": db_summary["write_count"],
            "thread_count": db_summary["thread_count"],
            "diagnostics_count": db_summary["diagnostics_count"],
            "checkpoint_namespaces": db_summary["checkpoint_namespaces"],
            "sample_threads": [
                {
                    "checkpoint_count": item["checkpoint_count"],
                    "latest_rowid": item["latest_rowid"],
                }
                for item in db_summary["threads"][:5]
            ],
        }
    )
    checks.append(
        {
            "status": "OK",
            "name": "SQLite checkpoint DB",
            "detail": (
                f"{db_summary['thread_count']} threads, "
                f"{db_summary['checkpoint_count']} checkpoints, "
                f"{db_summary['write_count']} writes"
            ),
        }
    )
    next_commands.insert(0, f"uv run lgmi inspect {path} --build-ui --no-browser")
    return summary


def _add_postgres_checks(
    checks: list[dict[str, str]],
    next_commands: list[str],
    conninfo: str,
    schema: str,
) -> dict[str, object]:
    from lgmi.postgres_reader import PostgresCheckpointReader

    redacted_conninfo = _redact_conninfo(conninfo)
    summary: dict[str, object] = {
        "conninfo": redacted_conninfo,
        "schema": schema,
    }
    try:
        reader = PostgresCheckpointReader(conninfo, schema=schema)
        store_summary = reader.summary()
    except Exception as exc:  # noqa: BLE001 - doctor should turn any connection/schema issue into a report.
        message = _sanitize_sensitive(str(exc), conninfo)
        checks.append(
            {
                "status": "ERROR",
                "name": "Postgres checkpoint store",
                "detail": message,
            }
        )
        summary["error"] = message
        return summary

    summary.update(
        {
            "adapter": store_summary.get("adapter"),
            "checkpoint_count": store_summary["checkpoint_count"],
            "write_count": store_summary["write_count"],
            "blob_count": store_summary["blob_count"],
            "thread_count": store_summary["thread_count"],
            "diagnostics_count": store_summary["diagnostics_count"],
            "diagnostics_count_mode": store_summary["diagnostics_count_mode"],
            "checkpoint_namespaces": store_summary["checkpoint_namespaces"],
            "checkpoint_migration_version": store_summary["checkpoint_migration_version"],
            "sample_threads": [
                {
                    "checkpoint_count": item["checkpoint_count"],
                }
                for item in store_summary["threads"][:5]
            ],
        }
    )
    checks.append(
        {
            "status": "OK",
            "name": "Postgres checkpoint store",
            "detail": (
                f"{store_summary['thread_count']} threads, "
                f"{store_summary['checkpoint_count']} checkpoints, "
                f"{store_summary['write_count']} writes"
            ),
        }
    )
    next_commands.insert(
        0,
        "uv run --extra postgres lgmi inspect-postgres '<postgres-conninfo>' "
        f"--schema {shlex.quote(schema)} --build-ui --no-browser",
    )
    return summary


def _sanitize_sensitive(message: str, secret: str) -> str:
    sanitized = re.sub(
        r"(?i)(password\s*=\s*)(?:'[^']*'|\"[^\"]*\"|\S+)",
        r"\1***",
        message,
    )
    sanitized = re.sub(
        r"([a-z][a-z0-9+.-]*://)([^@\s]+@)",
        r"\1***@",
        sanitized,
    )
    if secret and secret in message:
        sanitized = sanitized.replace(secret, _redact_conninfo(secret))
    return sanitized


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

    if args.build_ui and not _build_web_ui():
        return 2

    run_demo(reset=not args.no_reset, use_llm=args.use_llm)
    ui_dir = _resolve_ui_dir(args.ui_dir)
    _print_demo_next_steps(DB_PATH, args.host, args.port, args.prepare_only, ui_dir)

    if args.prepare_only:
        return 0

    return _serve_app(
        create_app(DB_PATH, ui_dir=ui_dir),
        args,
        f"Demo checkpoint DB: {DB_PATH.resolve()}",
    )


def _run_inspect(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).expanduser().resolve()
    if not db_path.exists():
        print(f"Checkpoint database not found: {db_path}", file=sys.stderr)
        return 2

    if args.build_ui and not _build_web_ui():
        return 2

    return _serve_app(
        create_app(db_path, ui_dir=_resolve_ui_dir(args.ui_dir)),
        args,
        f"Checkpoint DB: {db_path}",
    )


def _run_inspect_postgres(args: argparse.Namespace) -> int:
    from lgmi.postgres_reader import PostgresCheckpointReader

    if args.build_ui and not _build_web_ui():
        return 2

    reader = PostgresCheckpointReader(args.conninfo, schema=args.schema)
    return _serve_app(
        create_app(reader, ui_dir=_resolve_ui_dir(args.ui_dir)),
        args,
        f"Checkpoint store: {_redact_conninfo(args.conninfo)} schema={args.schema}",
    )


def _run_prove_demo(args: argparse.Namespace) -> int:
    from lgmi.use_case_smoke import (
        collect_use_case_evidence,
        default_demo_db_path,
        render_report,
        reset_demo_checkpoint_data,
    )

    if args.reset_demo:
        db_path = reset_demo_checkpoint_data()
    elif args.db_path:
        db_path = Path(args.db_path).expanduser().resolve()
    else:
        db_path = default_demo_db_path()

    evidence = collect_use_case_evidence(db_path)
    if args.json:
        print(json.dumps(evidence.to_report(), indent=2), flush=True)
    else:
        render_report(evidence)
    return 0 if evidence.passed else 1


def _run_export_debug_bundle(args: argparse.Namespace) -> int:
    from lgmi.checkpoint_reader import SQLiteCheckpointReader
    from lgmi.export_bundle import export_debug_bundle

    db_path = Path(args.db_path).expanduser().resolve()
    if not db_path.exists():
        print(f"Checkpoint database not found: {db_path}", file=sys.stderr)
        return 2

    if args.issue and args.redaction_mode == "raw":
        print(
            "`--issue` is for public reports; use `--redact` or `--redaction-mode redacted`.",
            file=sys.stderr,
        )
        return 2

    redaction_mode = args.redaction_mode or ("redacted" if args.redact or args.issue else "raw")
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
    if args.issue:
        _print_debug_bundle_issue(result)
        return 0

    print(f"Debug bundle: {result['path']}")
    print(f"File size: {result['file_size_bytes']} bytes")
    print(
        f"Redaction: {result['redaction_mode']}"
        f" ({result['redaction_count']} path(s) redacted)"
    )
    print(f"Diagnostics: {', '.join(str(item) for item in result['diagnostic_ids'])}")
    return 0


def _print_debug_bundle_issue(result: dict[str, Any]) -> None:
    bundle_name = Path(str(result["path"])).name
    diagnostics = ", ".join(str(item) for item in result["diagnostic_ids"]) or "none"
    redacted_paths = list(result["redacted_paths"])
    print("### LangGraph Memory Inspector debug bundle", flush=True)
    print(flush=True)
    print(f"- Bundle file: `{bundle_name}`", flush=True)
    print(f"- Schema version: `{result['schema_version']}`", flush=True)
    print(f"- Thread ID: `{result['thread_id']}`", flush=True)
    print(f"- Checkpoint namespace: `{result['checkpoint_ns']}`", flush=True)
    print(f"- Checkpoint ID: `{result['checkpoint_id']}`", flush=True)
    print(f"- File size: `{result['file_size_bytes']} bytes`", flush=True)
    print(f"- Redaction mode: `{result['redaction_mode']}`", flush=True)
    print(f"- Redacted paths: `{result['redaction_count']}`", flush=True)
    print(f"- Diagnostics: `{diagnostics}`", flush=True)
    if redacted_paths:
        sample_size = 8
        print(flush=True)
        print("<details>", flush=True)
        print("<summary>Redacted path samples</summary>", flush=True)
        print(flush=True)
        for path in redacted_paths[:sample_size]:
            print(f"- `{path}`", flush=True)
        remaining = len(redacted_paths) - sample_size
        if remaining > 0:
            print(f"- ... {remaining} more path(s) listed in the generated JSON bundle", flush=True)
        print("</details>", flush=True)
    print(flush=True)
    print(
        "Privacy note: attach only the generated redacted bundle after reviewing it locally. "
        "Do not attach raw production checkpoint stores, unredacted messages, prompts, tokens, "
        "or proprietary tool outputs.",
        flush=True,
    )


def _serve_app(app: object, args: argparse.Namespace, source_label: str) -> int:
    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    api_url = f"http://{display_host}:{args.port}/api/summary"
    ui_dir = str(getattr(getattr(app, "state", object()), "ui_dir", ""))
    browser_url = f"http://{display_host}:{args.port}/" if ui_dir else api_url
    print(f"LangGraph Memory Inspector API: {api_url}", flush=True)
    if ui_dir:
        print(f"LangGraph Memory Inspector UI: {browser_url}", flush=True)
        print(f"Serving built web UI: {ui_dir}", flush=True)
    else:
        print("Built web UI not found; serve the React app with `cd web && npm run dev`.", flush=True)
    print(source_label, flush=True)

    if not args.no_browser:
        webbrowser.open(browser_url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _print_demo_next_steps(
    db_path: Path,
    host: str,
    port: int,
    prepare_only: bool,
    ui_dir: Path | None,
) -> None:
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
    if ui_dir:
        print(flush=True)
        print(f"Built web UI will be served from: {ui_dir}", flush=True)
        print(f"Open: http://{display_host}:{port}/", flush=True)
    else:
        print(flush=True)
        print("Start the web UI in another terminal:", flush=True)
        print("cd web", flush=True)
        print("npm install", flush=True)
        print("npm run dev", flush=True)
        print(flush=True)
        print("Open: http://127.0.0.1:5173/", flush=True)
        print(flush=True)
        print("Optional single-server mode:", flush=True)
        print("uv run lgmi demo --build-ui", flush=True)


def _resolve_ui_dir(ui_dir: str | None) -> Path | None:
    if ui_dir:
        candidate = Path(ui_dir).expanduser().resolve()
        return candidate if (candidate / "index.html").exists() else None

    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "web" / "dist"
    return candidate.resolve() if (candidate / "index.html").exists() else None


def _build_web_ui() -> Path | None:
    repo_root = Path(__file__).resolve().parents[2]
    web_dir = repo_root / "web"
    package_json = web_dir / "package.json"
    if not package_json.exists():
        print("Cannot build web UI: web/package.json was not found.", file=sys.stderr)
        return None

    if shutil.which("npm") is None:
        print("Cannot build web UI: `npm` was not found on PATH.", file=sys.stderr)
        return None

    if not (web_dir / "node_modules").exists():
        print("Installing web dependencies with `npm install`...", flush=True)
        install = subprocess.run(["npm", "install"], cwd=web_dir, check=False)
        if install.returncode != 0:
            print("Web dependency install failed.", file=sys.stderr)
            return None

    print("Building web UI with `npm run build`...", flush=True)
    build = subprocess.run(["npm", "run", "build"], cwd=web_dir, check=False)
    if build.returncode != 0:
        print("Web UI build failed.", file=sys.stderr)
        return None

    return _resolve_ui_dir(None)


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
