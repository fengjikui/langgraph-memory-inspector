from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]


DEFAULT_GATES = (
    Gate("python tests", ("uv", "run", "pytest", "-q")),
    Gate("social preview asset", ("uv", "run", "python", "scripts/validate_social_preview.py")),
    Gate("launch copy guardrails", ("uv", "run", "python", "scripts/validate_launch_copy.py")),
    Gate("stale-memory proof", ("uv", "run", "lgmi", "prove-demo", "--reset-demo")),
    Gate("issue-safe debug bundle", ("uv", "run", "python", "scripts/issue_bundle_smoke.py")),
)

WEB_GATES = (
    Gate("web build", ("npm", "run", "build")),
    Gate("web e2e", ("npm", "run", "test:e2e")),
)


def run_release_smoke(*, include_web: bool = False) -> list[dict[str, str]]:
    """Run the release-candidate smoke gates used before public posting."""
    results: list[dict[str, str]] = []
    gates = list(DEFAULT_GATES)
    if include_web:
        gates.extend(WEB_GATES)

    for gate in gates:
        cwd = "web" if gate in WEB_GATES else None
        printable = " ".join(gate.command)
        print(f"\n==> {gate.name}: {printable}", flush=True)
        subprocess.run(gate.command, cwd=cwd, check=True)
        results.append({"name": gate.name, "command": printable, "status": "ok"})

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run release-candidate smoke checks.")
    parser.add_argument(
        "--include-web",
        action="store_true",
        help="Also run web build and Playwright e2e from the web/ directory.",
    )
    args = parser.parse_args()

    try:
        results = run_release_smoke(include_web=args.include_web)
    except subprocess.CalledProcessError as exc:
        print(f"\nFAILED: {' '.join(str(part) for part in exc.cmd)}", file=sys.stderr)
        return int(exc.returncode or 1)

    print("\nRelease smoke passed:")
    for result in results:
        print(f"- {result['name']}: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
