"""Governance analyzer: PII exposure, documentation completeness, ownership, naming."""
from __future__ import annotations

from collections import defaultdict

from .finding import Finding, HIGH, LOW, MEDIUM
from .util import all_columns, naming_style, pii_category


def analyze(wb) -> list[Finding]:
    findings: list[Finding] = []

    # Potential PII / sensitive columns (name-based; no data is read).
    pii: list[str] = []
    for _ds, t, c in all_columns(wb):
        cat = pii_category(c.name) or pii_category(c.original_name)
        if cat:
            pii.append(f"{t.name}.{c.name} ({cat})")
    if pii:
        findings.append(Finding(
            "governance", "Potential PII / sensitive columns detected", HIGH,
            "Unmanaged PII creates privacy and compliance exposure (GDPR / HIPAA).",
            "Classify, restrict, and mask these fields; confirm lawful basis and apply row/column security.",
            pii,
        ))

    # Missing data source descriptions.
    no_desc = [ds.caption or ds.name for ds in wb.data_sources if not (ds.description and ds.description.strip())]
    if no_desc:
        findings.append(Finding(
            "governance", "Data sources without descriptions", MEDIUM,
            "Missing documentation blocks certification and erodes self-service trust.",
            "Add clear descriptions/definitions for each data source and key field.",
            no_desc,
        ))

    # Ownership / stewardship metadata is not present in .twb.
    findings.append(Finding(
        "governance", "No ownership / stewardship metadata", LOW,
        "Unassigned ownership slows issue resolution and weakens accountability.",
        "Assign a data owner/steward and certify the data source in your catalog.",
        [],
    ))

    # Naming-convention consistency.
    styles: dict[str, list[str]] = defaultdict(list)
    for _ds, _t, c in all_columns(wb):
        styles[naming_style(c.name)].append(c.name)
    meaningful = {k: v for k, v in styles.items() if k != "empty"}
    if len(meaningful) > 1:
        examples = [f"{style}: {cols[0]}" for style, cols in list(meaningful.items())[:4]]
        findings.append(Finding(
            "governance", "Inconsistent naming conventions", LOW,
            "Mixed naming styles reduce readability and reuse across reports.",
            "Adopt a single naming standard for fields (e.g., consistent Title Case).",
            examples,
        ))

    return findings
