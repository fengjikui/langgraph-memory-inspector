from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lgmi import cli


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
