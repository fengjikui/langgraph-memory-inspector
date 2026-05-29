from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from lgmi import cli


def test_demo_prepare_only_generates_checkpoint_data(capsys: Any) -> None:
    result = cli.main(["demo", "--prepare-only"])

    output = capsys.readouterr().out
    assert result == 0
    assert "Demo checkpoint data is ready." in output
    assert "conflicting_residence_memory" in output
    assert "uv run lgmi inspect" in output
    assert "npm run dev" in output


def test_demo_serves_generated_database(monkeypatch: Any) -> None:
    served: dict[str, Any] = {}

    def fake_create_app(source: Path) -> object:
        served["source"] = source
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
    assert served["port"] == 8766
    assert "Demo checkpoint DB:" in served["source_label"]
