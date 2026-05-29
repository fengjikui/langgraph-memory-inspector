from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lgmi.export_bundle import EMAIL_PATTERN, PHONE_PATTERN, TOKEN_PATTERN


@dataclass(frozen=True)
class AuditCheck:
    status: str
    name: str
    detail: str


def audit_debug_bundle(path: str | Path) -> dict[str, Any]:
    bundle_path = Path(path).expanduser()
    checks: list[AuditCheck] = []

    if not bundle_path.exists():
        checks.append(AuditCheck("ERROR", "Bundle file", f"not found: {bundle_path}"))
        return _report(bundle_path, checks)

    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        checks.append(AuditCheck("ERROR", "Bundle JSON", str(exc)))
        return _report(bundle_path, checks)

    if not isinstance(bundle, dict):
        checks.append(AuditCheck("ERROR", "Bundle JSON", "top-level value must be an object"))
        return _report(bundle_path, checks)

    checks.extend(_schema_checks(bundle))
    checks.extend(_privacy_checks(bundle))
    checks.extend(_suspicious_value_checks(bundle))
    return _report(bundle_path, checks)


def _schema_checks(bundle: dict[str, Any]) -> list[AuditCheck]:
    checks: list[AuditCheck] = []
    if bundle.get("schema_version") == 1:
        checks.append(AuditCheck("OK", "Schema version", "1"))
    else:
        checks.append(AuditCheck("ERROR", "Schema version", f"expected 1, got {bundle.get('schema_version')!r}"))

    for key in ("thread", "selected_checkpoint", "diagnostics", "privacy"):
        status = "OK" if key in bundle else "ERROR"
        detail = "present" if key in bundle else "missing"
        checks.append(AuditCheck(status, f"Required key: {key}", detail))
    return checks


def _privacy_checks(bundle: dict[str, Any]) -> list[AuditCheck]:
    privacy = bundle.get("privacy")
    if not isinstance(privacy, dict):
        return [AuditCheck("ERROR", "Privacy metadata", "missing or not an object")]

    mode = privacy.get("redaction_mode")
    checks = [
        AuditCheck(
            "OK" if mode == "redacted" else "ERROR",
            "Redaction mode",
            str(mode),
        )
    ]
    redaction_count = privacy.get("redaction_count")
    if isinstance(redaction_count, int) and redaction_count > 0:
        checks.append(AuditCheck("OK", "Redaction count", str(redaction_count)))
    else:
        checks.append(AuditCheck("WARN", "Redaction count", f"expected > 0, got {redaction_count!r}"))
    return checks


def _suspicious_value_checks(bundle: dict[str, Any]) -> list[AuditCheck]:
    findings: list[str] = []
    for path, value in _walk_strings(bundle):
        if TOKEN_PATTERN.search(value):
            findings.append(f"{path}: token-like value")
        elif EMAIL_PATTERN.search(value):
            findings.append(f"{path}: email-like value")
        elif PHONE_PATTERN.search(value):
            findings.append(f"{path}: phone-like value")

    if not findings:
        return [AuditCheck("OK", "Suspicious private values", "no token/email/phone-like strings found")]

    sample = "; ".join(findings[:5])
    remaining = len(findings) - 5
    detail = sample if remaining <= 0 else f"{sample}; ... {remaining} more"
    return [AuditCheck("ERROR", "Suspicious private values", detail)]


def _walk_strings(value: Any, *, path: str = "$") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        items: list[tuple[str, str]] = []
        for key, item in value.items():
            items.extend(_walk_strings(item, path=f"{path}.{key}"))
        return items
    if isinstance(value, list):
        items = []
        for index, item in enumerate(value):
            items.extend(_walk_strings(item, path=f"{path}[{index}]"))
        return items
    return []


def _report(bundle_path: Path, checks: list[AuditCheck]) -> dict[str, Any]:
    has_error = any(check.status == "ERROR" for check in checks)
    return {
        "path": str(bundle_path),
        "safe_to_share": not has_error,
        "checks": [check.__dict__ for check in checks],
    }
