from __future__ import annotations

from scripts.package_smoke import REQUIRED_HELP_MARKERS
from scripts.release_smoke import DEFAULT_GATES


def test_package_smoke_requires_public_cli_commands() -> None:
    assert {"doctor", "prove-demo", "export-debug-bundle", "audit-debug-bundle"} <= set(
        REQUIRED_HELP_MARKERS
    )


def test_release_smoke_runs_package_install_gate() -> None:
    commands = {" ".join(gate.command) for gate in DEFAULT_GATES}

    assert "uv run python scripts/package_smoke.py" in commands
