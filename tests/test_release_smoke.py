from __future__ import annotations

from scripts.release_smoke import DEFAULT_GATES, WEB_GATES


def test_release_smoke_default_gates_match_release_checklist() -> None:
    commands = {" ".join(gate.command) for gate in DEFAULT_GATES}

    assert "uv run pytest -q" in commands
    assert "uv run python scripts/validate_social_preview.py" in commands
    assert "uv run python scripts/validate_launch_copy.py" in commands
    assert "uv run lgmi prove-demo --reset-demo" in commands


def test_release_smoke_web_gates_are_optional() -> None:
    commands = {" ".join(gate.command) for gate in WEB_GATES}

    assert commands == {"npm run build", "npm run test:e2e"}
