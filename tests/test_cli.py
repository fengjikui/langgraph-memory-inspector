from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from lgmi import cli
import lgmi.postgres_reader as postgres_reader


def test_demo_prepare_only_generates_checkpoint_data(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir: None)

    result = cli.main(["demo", "--prepare-only"])

    output = capsys.readouterr().out
    assert result == 0
    assert "Demo checkpoint data is ready." in output
    assert "conflicting_residence_memory" in output
    assert "uv run lgmi inspect" in output
    assert "npm run dev" in output


def test_demo_prepare_only_reports_built_ui(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    ui_dir = tmp_path / "dist"
    ui_dir.mkdir()
    (ui_dir / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir_arg: ui_dir)

    result = cli.main(["demo", "--prepare-only"])

    output = capsys.readouterr().out
    assert result == 0
    assert "Built web UI will be served from:" in output
    assert "Optional single-server mode" not in output


def test_doctor_skip_modes_report_ready(capsys: Any) -> None:
    result = cli.main(["doctor", "--skip-demo", "--skip-web"])

    output = capsys.readouterr().out
    assert result == 0
    assert "LangGraph Memory Inspector doctor" in output
    assert "[SKIP] Demo checkpoint" in output
    assert "[SKIP] Web UI" in output
    assert "READY: requested doctor checks passed" in output
    assert "Result: ready for the local demo path." in output


def test_doctor_reports_missing_demo_source(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(cli, "_load_relocation_demo", lambda: None)

    result = cli.main(["doctor", "--skip-web"])

    output = capsys.readouterr().out
    assert result == 1
    assert "[ERROR] Demo source" in output
    assert "Fix the ERROR item(s)" in output


def test_doctor_json_report_is_machine_readable(capsys: Any) -> None:
    result = cli.main(["doctor", "--skip-demo", "--skip-web", "--json"])

    report = json.loads(capsys.readouterr().out)
    assert result == 0
    assert report["tool"] == "langgraph-memory-inspector"
    assert report["ready"] is True
    assert report["readiness"].startswith("READY: requested doctor checks passed")
    assert report["checks"][0]["name"] == "Python"
    assert report["checks"][0]["status"] == "OK"
    assert "checkpoint state" in report["privacy"]


def test_doctor_prefers_build_ui_when_dist_is_missing(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir: None)

    result = cli.main(["doctor", "--json"])

    report = json.loads(capsys.readouterr().out)
    assert result == 0
    assert report["next_commands"][0] == "uv run lgmi demo --build-ui --no-browser"
    assert any(
        check["name"] == "Built web UI" and check["status"] == "WARN"
        for check in report["checks"]
    )


def test_doctor_json_report_preserves_error_exit(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(cli, "_load_relocation_demo", lambda: None)

    result = cli.main(["doctor", "--skip-web", "--json"])

    report = json.loads(capsys.readouterr().out)
    assert result == 1
    assert report["ready"] is False
    assert any(check["status"] == "ERROR" for check in report["checks"])


def test_doctor_issue_report_is_pasteable_markdown(capsys: Any) -> None:
    result = cli.main(["doctor", "--skip-demo", "--skip-web", "--issue"])

    output = capsys.readouterr().out
    assert result == 0
    assert "### LangGraph Memory Inspector doctor report" in output
    assert "```json" in output
    assert '"ready": true' in output
    assert "Privacy note:" in output


def test_doctor_validates_sqlite_checkpoint_db(tmp_path: Path, capsys: Any) -> None:
    db_path = tmp_path / "checkpoints.sqlite"
    _write_empty_checkpoint_db(db_path)

    result = cli.main(["doctor", "--skip-demo", "--skip-web", "--sqlite-db", str(db_path), "--json"])

    report = json.loads(capsys.readouterr().out)
    assert result == 0
    assert report["sqlite_db"]["path"] == str(db_path)
    assert report["sqlite_db"]["checkpoint_count"] == 0
    assert report["result"] == "ready for local SQLite checkpoint inspection"
    assert report["readiness"] == (
        "READY: read-only SQLite inspection; 0 checkpoints; 0 writes; "
        "report excludes checkpoint state, messages, prompts, tokens, and raw rows."
    )
    assert report["next_commands"][0] == f"uv run lgmi inspect {db_path} --build-ui --no-browser"
    assert any(
        check["name"] == "SQLite checkpoint DB" and check["status"] == "OK"
        for check in report["checks"]
    )


def test_doctor_reports_missing_sqlite_checkpoint_db(tmp_path: Path, capsys: Any) -> None:
    db_path = tmp_path / "missing.sqlite"

    result = cli.main(["doctor", "--skip-demo", "--skip-web", "--sqlite-db", str(db_path), "--json"])

    report = json.loads(capsys.readouterr().out)
    assert result == 1
    assert report["ready"] is False
    assert report["next_commands"] == []
    assert report["sqlite_db"]["exists"] is False
    assert any(
        check["name"] == "SQLite checkpoint DB" and check["status"] == "ERROR"
        for check in report["checks"]
    )


def test_doctor_validates_postgres_checkpoint_store(monkeypatch: Any, capsys: Any) -> None:
    class FakePostgresReader:
        def __init__(self, conninfo: str, *, schema: str = "public") -> None:
            assert conninfo == "postgresql://user:secret@localhost:5432/app"
            assert schema == "agent"

        def summary(self) -> dict[str, Any]:
            return {
                "adapter": "LangGraph Postgres Checkpointer",
                "checkpoint_count": 7,
                "write_count": 11,
                "blob_count": 13,
                "thread_count": 2,
                "diagnostics_count": 0,
                "diagnostics_count_mode": "not_scanned_for_postgres",
                "checkpoint_namespaces": ["", "research"],
                "checkpoint_migration_version": 5,
                "threads": [
                    {
                        "thread_id": "private-user-id",
                        "checkpoint_count": 4,
                        "latest_checkpoint_id": "private-checkpoint-id",
                    }
                ],
            }

    monkeypatch.setattr(postgres_reader, "PostgresCheckpointReader", FakePostgresReader)

    result = cli.main(
        [
            "doctor",
            "--skip-demo",
            "--skip-web",
            "--postgres-conninfo",
            "postgresql://user:secret@localhost:5432/app",
            "--postgres-schema",
            "agent",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert result == 0
    assert report["postgres"]["conninfo"] == "postgresql://***@localhost:5432/app"
    assert report["postgres"]["checkpoint_count"] == 7
    assert report["result"] == "ready for local Postgres checkpoint inspection"
    assert report["readiness"] == (
        "READY: read-only Postgres inspection; 7 checkpoints; 11 writes; "
        "report excludes checkpoint state, thread ids, messages, prompts, tokens, and raw rows."
    )
    assert report["postgres"]["sample_threads"] == [{"checkpoint_count": 4}]
    assert "private-user-id" not in json.dumps(report)
    assert "secret" not in json.dumps(report)
    assert report["next_commands"][0] == (
        "uv run --extra postgres lgmi inspect-postgres '<postgres-conninfo>' "
        "--schema agent --build-ui --no-browser"
    )


def test_doctor_reports_postgres_error_without_leaking_conninfo(
    monkeypatch: Any, capsys: Any
) -> None:
    class FailingPostgresReader:
        def __init__(self, conninfo: str, *, schema: str = "public") -> None:
            raise RuntimeError(f"could not connect to {conninfo}")

    monkeypatch.setattr(postgres_reader, "PostgresCheckpointReader", FailingPostgresReader)

    result = cli.main(
        [
            "doctor",
            "--skip-demo",
            "--skip-web",
            "--postgres-conninfo",
            "postgresql://user:secret@localhost:5432/app",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert result == 1
    assert report["ready"] is False
    assert report["next_commands"] == []
    assert "secret" not in json.dumps(report)
    assert "postgresql://***@localhost:5432/app" in json.dumps(report)


def test_doctor_redacts_keyword_postgres_password(
    monkeypatch: Any, capsys: Any
) -> None:
    class FailingPostgresReader:
        def __init__(self, conninfo: str, *, schema: str = "public") -> None:
            raise RuntimeError("could not connect with password=topsecret")

    monkeypatch.setattr(postgres_reader, "PostgresCheckpointReader", FailingPostgresReader)

    result = cli.main(
        [
            "doctor",
            "--skip-demo",
            "--skip-web",
            "--postgres-conninfo",
            "host=localhost user=agent password=topsecret dbname=app",
            "--json",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert result == 1
    assert "topsecret" not in json.dumps(report)
    assert "password=***" in json.dumps(report)
    assert report["postgres"]["conninfo"] == "<postgres conninfo>"


def test_doctor_rejects_multiple_checkpoint_store_inputs(capsys: Any) -> None:
    with pytest.raises(SystemExit):
        cli.main(
            [
                "doctor",
                "--sqlite-db",
                "checkpoints.sqlite",
                "--postgres-conninfo",
                "postgresql://unused",
            ]
        )

    assert "not allowed with argument" in capsys.readouterr().err


def test_demo_serves_generated_database(monkeypatch: Any) -> None:
    served: dict[str, Any] = {}
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir: None)

    def fake_create_app(source: Path, *, ui_dir: Path | None = None) -> object:
        served["source"] = source
        served["ui_dir"] = ui_dir
        return object()

    def fake_serve_app(app: object, args: argparse.Namespace, source_label: str) -> int:
        served["app"] = app
        served["port"] = args.port
        served["source_label"] = source_label
        return 0

    monkeypatch.setattr(cli, "create_app", fake_create_app)
    monkeypatch.setattr(cli, "_serve_app", fake_serve_app)

    result = cli.main(["demo", "--no-browser", "--port", "8766"])

    assert result == 0
    assert served["source"].name == "checkpoints.sqlite"
    assert served["ui_dir"] is None
    assert served["port"] == 8766
    assert "Demo checkpoint DB:" in served["source_label"]


def test_demo_serves_built_ui_when_available(monkeypatch: Any, tmp_path: Path) -> None:
    served: dict[str, Any] = {}
    ui_dir = tmp_path / "dist"
    ui_dir.mkdir()
    (ui_dir / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir_arg: ui_dir)

    def fake_create_app(source: Path, *, ui_dir: Path | None = None) -> object:
        served["source"] = source
        served["ui_dir"] = ui_dir
        return object()

    def fake_serve_app(app: object, args: argparse.Namespace, source_label: str) -> int:
        served["app"] = app
        served["port"] = args.port
        served["source_label"] = source_label
        return 0

    monkeypatch.setattr(cli, "create_app", fake_create_app)
    monkeypatch.setattr(cli, "_serve_app", fake_serve_app)

    result = cli.main(["demo", "--no-browser", "--port", "8766"])

    assert result == 0
    assert served["source"].name == "checkpoints.sqlite"
    assert served["ui_dir"] == ui_dir
    assert served["port"] == 8766


def test_demo_builds_ui_before_serving(monkeypatch: Any, tmp_path: Path) -> None:
    served: dict[str, Any] = {}
    ui_dir = tmp_path / "dist"
    ui_dir.mkdir()
    (ui_dir / "index.html").write_text("<div id='root'></div>", encoding="utf-8")

    def fake_build_web_ui() -> Path:
        served["built"] = True
        return ui_dir

    def fake_create_app(source: Path, *, ui_dir: Path | None = None) -> object:
        served["source"] = source
        served["ui_dir"] = ui_dir
        return object()

    def fake_serve_app(app: object, args: argparse.Namespace, source_label: str) -> int:
        served["port"] = args.port
        return 0

    monkeypatch.setattr(cli, "_build_web_ui", fake_build_web_ui)
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir_arg: ui_dir)
    monkeypatch.setattr(cli, "create_app", fake_create_app)
    monkeypatch.setattr(cli, "_serve_app", fake_serve_app)

    result = cli.main(["demo", "--build-ui", "--no-browser", "--port", "8766"])

    assert result == 0
    assert served["built"] is True
    assert served["source"].name == "checkpoints.sqlite"
    assert served["ui_dir"] == ui_dir
    assert served["port"] == 8766


def test_demo_build_ui_failure_exits_before_serving(monkeypatch: Any) -> None:
    served: dict[str, Any] = {}

    monkeypatch.setattr(cli, "_build_web_ui", lambda: None)
    monkeypatch.setattr(cli, "_serve_app", lambda *args: served.setdefault("served", True))

    result = cli.main(["demo", "--build-ui", "--no-browser"])

    assert result == 2
    assert "served" not in served


def test_inspect_builds_ui_before_serving(monkeypatch: Any, tmp_path: Path) -> None:
    db_path = tmp_path / "checkpoints.sqlite"
    _write_empty_checkpoint_db(db_path)
    ui_dir = tmp_path / "dist"
    ui_dir.mkdir()
    (ui_dir / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    served: dict[str, Any] = {}

    monkeypatch.setattr(cli, "_build_web_ui", lambda: ui_dir)
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir_arg: ui_dir)

    def fake_create_app(source: Path, *, ui_dir: Path | None = None) -> object:
        served["source"] = source
        served["ui_dir"] = ui_dir
        return object()

    def fake_serve_app(app: object, args: argparse.Namespace, source_label: str) -> int:
        served["port"] = args.port
        served["source_label"] = source_label
        return 0

    monkeypatch.setattr(cli, "create_app", fake_create_app)
    monkeypatch.setattr(cli, "_serve_app", fake_serve_app)

    result = cli.main(["inspect", str(db_path), "--build-ui", "--no-browser", "--port", "8766"])

    assert result == 0
    assert served["source"] == db_path.resolve()
    assert served["ui_dir"] == ui_dir
    assert served["port"] == 8766


def test_inspect_postgres_builds_ui_before_serving(monkeypatch: Any, tmp_path: Path) -> None:
    ui_dir = tmp_path / "dist"
    ui_dir.mkdir()
    (ui_dir / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    served: dict[str, Any] = {}

    class FakePostgresReader:
        def __init__(self, conninfo: str, *, schema: str = "public") -> None:
            served["conninfo"] = conninfo
            served["schema"] = schema

    monkeypatch.setattr(cli, "_build_web_ui", lambda: ui_dir)
    monkeypatch.setattr(cli, "_resolve_ui_dir", lambda ui_dir_arg: ui_dir)
    monkeypatch.setattr(postgres_reader, "PostgresCheckpointReader", FakePostgresReader)

    def fake_create_app(source: object, *, ui_dir: Path | None = None) -> object:
        served["source"] = source
        served["ui_dir"] = ui_dir
        return object()

    def fake_serve_app(app: object, args: argparse.Namespace, source_label: str) -> int:
        served["port"] = args.port
        served["source_label"] = source_label
        return 0

    monkeypatch.setattr(cli, "create_app", fake_create_app)
    monkeypatch.setattr(cli, "_serve_app", fake_serve_app)

    result = cli.main(
        [
            "inspect-postgres",
            "postgresql://user:secret@localhost:5432/app",
            "--schema",
            "agent",
            "--build-ui",
            "--no-browser",
            "--port",
            "8766",
        ]
    )

    assert result == 0
    assert served["conninfo"] == "postgresql://user:secret@localhost:5432/app"
    assert served["schema"] == "agent"
    assert served["ui_dir"] == ui_dir
    assert served["port"] == 8766
    assert "postgresql://***@localhost:5432/app" in served["source_label"]


def _write_empty_checkpoint_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            create table checkpoints (
                thread_id text,
                checkpoint_ns text,
                checkpoint_id text,
                parent_checkpoint_id text,
                type text,
                checkpoint blob,
                metadata blob
            );
            create table writes (
                thread_id text,
                checkpoint_ns text,
                checkpoint_id text,
                task_id text,
                idx integer,
                channel text,
                type text,
                value blob
            );
            """
        )
