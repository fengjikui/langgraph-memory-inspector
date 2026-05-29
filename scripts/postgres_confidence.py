from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.relocation_policy_agent.run_demo import THREAD_ID, build_graph
from langchain_core.messages import AIMessage, HumanMessage

from lgmi import cli
from lgmi.postgres_reader import PostgresCheckpointReader


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    dsn = args.dsn or os.environ.get("LGMI_POSTGRES_TEST_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit(
            "Provide --dsn, LGMI_POSTGRES_TEST_DSN, or DATABASE_URL for a local/safe Postgres instance."
        )

    schema = args.schema or f"lgmi_confidence_{uuid.uuid4().hex[:12]}"
    if not _safe_identifier(schema):
        raise SystemExit(f"Unsafe schema name: {schema}")

    created_schema = False
    try:
        if not args.use_existing_schema:
            _create_schema(dsn, schema)
            created_schema = True

        _write_demo_checkpoints(dsn, schema)
        reader = PostgresCheckpointReader(dsn, schema=schema)
        summary = reader.summary()
        checkpoints = reader.list_checkpoints(THREAD_ID)
        if not checkpoints:
            raise RuntimeError("PostgresSaver wrote no checkpoints.")

        doctor_report = _doctor_report(dsn, schema)
        if not doctor_report["ready"]:
            raise RuntimeError("lgmi doctor did not mark the Postgres store ready.")

        _print_report(schema, summary, doctor_report, args.keep_schema)
        return 0
    finally:
        if created_schema and not args.keep_schema:
            _drop_schema(dsn, schema)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a tiny LangGraph PostgresSaver checkpoint store, validate it "
            "with LGMI, and print safe next commands."
        )
    )
    parser.add_argument(
        "--dsn",
        default=None,
        help="Postgres connection string. Defaults to LGMI_POSTGRES_TEST_DSN or DATABASE_URL.",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Schema to create/use. Defaults to a temporary lgmi_confidence_* schema.",
    )
    parser.add_argument(
        "--use-existing-schema",
        action="store_true",
        help="Use an existing empty schema instead of creating a new one.",
    )
    parser.add_argument(
        "--keep-schema",
        action="store_true",
        help="Keep the generated schema so you can open it with inspect-postgres.",
    )
    return parser.parse_args(argv)


def _create_schema(dsn: str, schema: str) -> None:
    from psycopg import sql

    with _connect(dsn) as conn:
        conn.execute(sql.SQL("create schema {}").format(sql.Identifier(schema)))


def _drop_schema(dsn: str, schema: str) -> None:
    from psycopg import sql

    with _connect(dsn) as conn:
        conn.execute(sql.SQL("drop schema if exists {} cascade").format(sql.Identifier(schema)))


def _write_demo_checkpoints(dsn: str, schema: str) -> None:
    from langgraph.checkpoint.postgres import PostgresSaver

    with _connect(dsn, schema=schema) as conn:
        saver = PostgresSaver(conn)
        saver.setup()
        app = build_graph(use_llm=False).compile(checkpointer=saver)
        state: dict[str, Any] = {
            "messages": [],
            "memory_events": [],
            "retrieved_docs": [],
            "diagnostics": [],
            "selected_city": None,
        }
        config = {"configurable": {"thread_id": THREAD_ID, "checkpoint_ns": ""}}
        for user_text in (
            "I live in Shanghai and want help tracking local benefits.",
            "I moved to Hangzhou last week. Please remember that.",
            "Which local benefits should I check first?",
        ):
            state["messages"] = [HumanMessage(content=user_text)]
            output = app.invoke(state, config=config)
            state = {
                "messages": output["messages"],
                "memory_events": output.get("memory_events", []),
                "retrieved_docs": output.get("retrieved_docs", []),
                "diagnostics": output.get("diagnostics", []),
                "selected_city": output.get("selected_city"),
            }

        if not any(isinstance(message, AIMessage) for message in state["messages"]):
            raise RuntimeError("Demo graph did not produce an AIMessage.")


def _doctor_report(dsn: str, schema: str) -> dict[str, Any]:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = cli.main(
            [
                "doctor",
                "--skip-demo",
                "--skip-web",
                "--postgres-conninfo",
                dsn,
                "--postgres-schema",
                schema,
                "--json",
            ]
        )
    report = json.loads(buffer.getvalue())
    if result != 0:
        report["ready"] = False
    return report


def _print_report(
    schema: str,
    summary: dict[str, Any],
    doctor_report: dict[str, Any],
    keep_schema: bool,
) -> None:
    redacted_conninfo = doctor_report["postgres"]["conninfo"]
    print("LangGraph Memory Inspector Postgres confidence check")
    print("=" * 55)
    print(f"Schema: {schema}")
    print(f"Connection: {redacted_conninfo}")
    print(
        "Store: "
        f"{summary['thread_count']} thread(s), "
        f"{summary['checkpoint_count']} checkpoint(s), "
        f"{summary['write_count']} write(s), "
        f"{summary['blob_count']} blob(s)"
    )
    print(doctor_report["readiness"])
    print()
    print("Doctor command:")
    print(
        'uv run --extra postgres lgmi doctor --postgres-conninfo "$DATABASE_URL" '
        f"--postgres-schema {schema}"
    )
    print()
    print("Inspector command:")
    print(
        'uv run --extra postgres lgmi inspect-postgres "$DATABASE_URL" '
        f"--schema {schema} --build-ui"
    )
    print()
    if keep_schema:
        print("Cleanup command:")
        print(f"drop schema {schema} cascade;")
    else:
        print("Cleanup: generated schema was dropped. Re-run with --keep-schema to inspect it in the UI.")


def _connect(dsn: str, schema: str | None = None):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Postgres dependencies are missing. Run this with `uv run --extra postgres "
            "python scripts/postgres_confidence.py ...`."
        ) from exc

    kwargs: dict[str, Any] = {
        "autocommit": True,
        "row_factory": dict_row,
    }
    if schema:
        kwargs["options"] = f"-c search_path={schema}"
    return psycopg.connect(dsn, **kwargs)


def _safe_identifier(value: str) -> bool:
    return bool(value) and value.replace("_", "").isalnum() and not value[0].isdigit()


if __name__ == "__main__":
    raise SystemExit(main())
