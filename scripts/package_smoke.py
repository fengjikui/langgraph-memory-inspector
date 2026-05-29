from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REQUIRED_HELP_MARKERS = (
    "doctor",
    "prove-demo",
    "export-debug-bundle",
    "audit-debug-bundle",
)


def run_package_smoke() -> dict[str, str]:
    """Build the package, install the wheel into a temp venv, and verify lgmi."""
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    _run(("uv", "build"))
    wheels = sorted(dist_dir.glob("langgraph_memory_inspector-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one wheel in dist/, found {len(wheels)}")
    wheel = wheels[0]

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = Path(tmpdir) / "venv"
        python = venv_dir / ("Scripts/python.exe" if _is_windows() else "bin/python")
        lgmi = venv_dir / ("Scripts/lgmi.exe" if _is_windows() else "bin/lgmi")

        _run(("uv", "venv", str(venv_dir)))
        _run(("uv", "pip", "install", "--python", str(python), str(wheel)))
        help_output = _run((str(lgmi), "--help"))

    missing = [marker for marker in REQUIRED_HELP_MARKERS if marker not in help_output]
    if missing:
        raise RuntimeError(f"installed lgmi --help is missing: {', '.join(missing)}")

    return {
        "wheel": str(wheel),
        "status": "ok",
    }


def _run(command: tuple[str, ...]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout


def _is_windows() -> bool:
    return os.name == "nt"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and install the package in a temporary venv.")
    parser.parse_args()
    result = run_package_smoke()
    print("Package smoke passed:")
    print(f"- wheel: {result['wheel']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
