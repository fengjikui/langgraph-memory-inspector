from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
from pathlib import Path
from typing import Any

from lgmi.cli import main as lgmi_main
from lgmi.use_case_smoke import collect_use_case_evidence, reset_demo_checkpoint_data


PRIVATE_DEMO_PHRASES = (
    "I live in Shanghai",
    "I moved to Hangzhou last week",
    "Which local benefits should I check first",
)


def run_issue_bundle_smoke(output_dir: Path | None = None) -> dict[str, Any]:
    """Prove the public issue handoff path with a redacted demo bundle."""
    db_path = reset_demo_checkpoint_data()
    evidence = collect_use_case_evidence(db_path)
    checkpoint_id = evidence.first_stale_checkpoint_id or evidence.final_checkpoint_id
    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = output_dir or Path(tmpdir) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        export_stdout = io.StringIO()
        export_stderr = io.StringIO()
        with contextlib.redirect_stdout(export_stdout), contextlib.redirect_stderr(export_stderr):
            export_exit = lgmi_main(
                [
                    "export-debug-bundle",
                    str(db_path),
                    "--thread-id",
                    evidence.thread_id,
                    "--checkpoint-id",
                    checkpoint_id,
                    "--issue",
                    "--output-dir",
                    str(export_dir),
                ]
            )
        if export_exit != 0:
            raise RuntimeError(f"export-debug-bundle --issue failed: {export_stderr.getvalue().strip()}")

        bundle_paths = sorted(export_dir.glob("lgmi-debug-*.json"))
        if len(bundle_paths) != 1:
            raise RuntimeError(f"expected one debug bundle, found {len(bundle_paths)}")
        bundle_path = bundle_paths[0]

        audit_stdout = io.StringIO()
        audit_stderr = io.StringIO()
        with contextlib.redirect_stdout(audit_stdout), contextlib.redirect_stderr(audit_stderr):
            audit_exit = lgmi_main(["audit-debug-bundle", str(bundle_path)])
        if audit_exit != 0:
            raise RuntimeError(f"audit-debug-bundle failed: {audit_stderr.getvalue().strip()}")

        bundle_text = bundle_path.read_text(encoding="utf-8")
        export_text = export_stdout.getvalue()
        audit_text = audit_stdout.getvalue()
        _assert_safe_issue_output(export_text, audit_text, bundle_text, export_dir)
        bundle = json.loads(bundle_text)

        return {
            "bundle_path": str(bundle_path),
            "thread_id": evidence.thread_id,
            "checkpoint_id": checkpoint_id,
            "diagnostic_ids": [item.get("id") for item in bundle.get("diagnostics", [])],
            "redaction_mode": bundle.get("privacy", {}).get("redaction_mode"),
            "redaction_count": bundle.get("privacy", {}).get("redaction_count"),
            "export_summary_lines": len(export_text.splitlines()),
            "audit_summary_lines": len(audit_text.splitlines()),
            "passed": True,
        }


def _assert_safe_issue_output(
    export_text: str,
    audit_text: str,
    bundle_text: str,
    export_dir: Path,
) -> None:
    combined = "\n".join([export_text, audit_text, bundle_text])
    for phrase in PRIVATE_DEMO_PHRASES:
        if phrase in combined:
            raise RuntimeError(f"private demo phrase leaked into issue bundle path: {phrase!r}")

    if str(export_dir) in export_text:
        raise RuntimeError("issue Markdown summary leaked the absolute export directory")
    if "Redaction mode: `redacted`" not in export_text:
        raise RuntimeError("issue Markdown summary did not report redacted mode")
    if "no automatic blocker found" not in audit_text:
        raise RuntimeError("bundle audit did not report a clean result")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test issue-safe debug bundle export and audit.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable smoke output.")
    args = parser.parse_args()

    report = run_issue_bundle_smoke()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Issue-safe debug bundle smoke passed:")
        print(f"- checkpoint_id: {report['checkpoint_id']}")
        print(f"- diagnostics: {', '.join(str(item) for item in report['diagnostic_ids'])}")
        print(f"- redaction: {report['redaction_mode']} ({report['redaction_count']} paths)")
        print(f"- bundle: {Path(str(report['bundle_path'])).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
