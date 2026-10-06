"""Helpers to fold existing assessment findings into WAF checks (no duplication)."""
from __future__ import annotations

from .pillar import Check, FAIL, WARN

# critical/high findings fail a check; medium/low/info warn.
_FAIL_SEV = {"critical", "high"}


def check_from_finding(finding: dict) -> Check:
    sev = finding.get("severity", "info")
    return Check(
        id=(finding.get("title") or "finding")[:60],
        title=finding.get("title", "Finding"),
        status=FAIL if sev in _FAIL_SEV else WARN,
        severity=sev,
        detail=finding.get("businessImpact", ""),
        recommendation=finding.get("recommendation", ""),
        evidence=finding.get("evidence", []) or [],
    )


def checks_from_sections(assessment: dict, *section_keys: str) -> list[Check]:
    out: list[Check] = []
    for key in section_keys:
        for finding in assessment.get(key, []) or []:
            out.append(check_from_finding(finding))
    return out
