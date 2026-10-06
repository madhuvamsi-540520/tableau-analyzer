"""Optimization opportunities: recommendations derived from structure (all informational)."""
from __future__ import annotations

from .constants import LARGE_TABLE_ROWS, MANY_CALCS
from .finding import Finding, INFO


def _rec(title, impact, rec, evidence):
    return Finding("optimization", title, INFO, impact, rec, evidence)


def analyze(wb) -> list[Finding]:
    findings: list[Finding] = []
    cx = wb.complexity()

    for ds in wb.data_sources:
        model = ds.classification.get("type", "")
        if "Snowflake" in model or "Hybrid" in model:
            findings.append(_rec(
                "Consider a star-schema redesign",
                "A star schema simplifies joins and improves query performance and usability.",
                "Denormalize snowflaked dimensions into conformed dimensions around the fact.",
                [f"{ds.caption or ds.name}: {model}"],
            ))
        if ds.is_extract:
            findings.append(_rec(
                "Use incremental extract refresh",
                "Full extract refreshes are slow and costly as data grows.",
                "Configure incremental refresh keyed on a date/sequence column.",
                [ds.caption or ds.name],
            ))
        big = [t.name for t in ds.tables if t.row_count and t.row_count >= LARGE_TABLE_ROWS]
        if big:
            findings.append(_rec(
                "Add aggregation tables / materialized views",
                "Pre-aggregation dramatically reduces scan volume for dashboards.",
                "Create summary tables/materialized views at common grains; consider partitioning & indexing.",
                big,
            ))

    if len(wb.data_sources) > 1:
        findings.append(_rec(
            "Consolidate data sources",
            "Multiple overlapping data sources fragment logic and governance.",
            "Consolidate into a shared, certified/published data source where possible.",
            [ds.caption or ds.name for ds in wb.data_sources],
        ))

    if cx["calculatedFields"] > MANY_CALCS:
        findings.append(_rec(
            "Optimize / rationalize calculations",
            "Redundant or heavy calculations slow queries and raise maintenance cost.",
            "Consolidate duplicate logic and push stable calculations to the warehouse.",
            [f"{cx['calculatedFields']} calculated fields"],
        ))

    return findings
