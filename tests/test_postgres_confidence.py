from __future__ import annotations

from typing import Any

import pytest

from scripts import postgres_confidence


class FakePostgresReader:
    def __init__(self, dsn: str, *, schema: str) -> None:
        self.dsn = dsn
        self.schema = schema

    def summary(self) -> dict[str, Any]:
        return {
            "thread_count": 1,
            "checkpoint_count": 18,
            "write_count": 41,
            "blob_count": 9,
        }

    def list_checkpoints(self, thread_id: str) -> list[dict[str, str]]:
        return [{"checkpoint_id": "checkpoint-1"}]


def test_postgres_confidence_drops_generated_schema(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/lgmi")
    monkeypatch.setattr(
        postgres_confidence,
        "_create_schema",
        lambda dsn, schema: calls.append(("create", schema)),
    )
    monkeypatch.setattr(
        postgres_confidence,
        "_write_demo_checkpoints",
        lambda dsn, schema: calls.append(("write", schema)),
    )
    monkeypatch.setattr(
        postgres_confidence,
        "_drop_schema",
        lambda dsn, schema: calls.append(("drop", schema)),
    )
    monkeypatch.setattr(postgres_confidence, "PostgresCheckpointReader", FakePostgresReader)
    monkeypatch.setattr(
        postgres_confidence,
        "_doctor_report",
        lambda dsn, schema: {
            "ready": True,
            "readiness": "READY: read-only Postgres inspection; 18 checkpoints; 41 writes.",
            "postgres": {"conninfo": "postgresql://***@localhost/lgmi"},
        },
    )

    result = postgres_confidence.main(["--schema", "lgmi_confidence_test"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [
        ("create", "lgmi_confidence_test"),
        ("write", "lgmi_confidence_test"),
        ("drop", "lgmi_confidence_test"),
    ]
    assert "Postgres confidence check" in output
    assert "inspect-postgres" in output
    assert "generated schema was dropped" in output
    assert "secret" not in output


def test_postgres_confidence_keeps_schema_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []

    monkeypatch.setenv("LGMI_POSTGRES_TEST_DSN", "postgresql://user:secret@localhost/lgmi")
    monkeypatch.setattr(
        postgres_confidence,
        "_create_schema",
        lambda dsn, schema: calls.append(("create", schema)),
    )
    monkeypatch.setattr(
        postgres_confidence,
        "_write_demo_checkpoints",
        lambda dsn, schema: calls.append(("write", schema)),
    )
    monkeypatch.setattr(
        postgres_confidence,
        "_drop_schema",
        lambda dsn, schema: calls.append(("drop", schema)),
    )
    monkeypatch.setattr(postgres_confidence, "PostgresCheckpointReader", FakePostgresReader)
    monkeypatch.setattr(
        postgres_confidence,
        "_doctor_report",
        lambda dsn, schema: {
            "ready": True,
            "readiness": "READY: read-only Postgres inspection; 18 checkpoints; 41 writes.",
            "postgres": {"conninfo": "postgresql://***@localhost/lgmi"},
        },
    )

    result = postgres_confidence.main(["--schema", "lgmi_confidence_keep", "--keep-schema"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [
        ("create", "lgmi_confidence_keep"),
        ("write", "lgmi_confidence_keep"),
    ]
    assert "drop schema lgmi_confidence_keep cascade;" in output


def test_postgres_confidence_rejects_unsafe_schema() -> None:
    with pytest.raises(SystemExit, match="Unsafe schema name"):
        postgres_confidence.main(
            [
                "--dsn",
                "postgresql://localhost/lgmi",
                "--schema",
                "public;drop schema public",
            ]
        )
