"""Scalability analyzer: join count, custom-SQL complexity, extract size, calc volume."""
from __future__ import annotations

from .constants import COMPLEX_SQL_SCORE, EXCESSIVE_JOINS, LARGE_TABLE_ROWS, MANY_CALCS
from .finding import Finding, LOW, MEDIUM


def analyze(wb) -> list[Finding]:
    findings: list[Finding] = []
    cx = wb.complexity()

    if cx["joins"] >= EXCESSIVE_JOINS:
        findings.append(Finding(
            "scalability", "High join count", MEDIUM,
            "Query cost grows with joins; performance degrades as data volume rises.",
            "Pre-join/aggregate in the warehouse or use a star-schema extract.",
            [f"{cx['joins']} joins across the workbook"],
        ))

    for ds in wb.data_sources:
        for s in ds.custom_sql:
            a = s.analysis or {}
            score = len(a.get("ctes", [])) + a.get("subqueryCount", 0) + len(a.get("windowFunctions", []))
            if score >= COMPLEX_SQL_SCORE:
                findings.append(Finding(
                    "scalability", f"Complex custom SQL: {s.name}", MEDIUM,
                    "Complex SQL is hard to optimize and scale, and pushes work to query time.",
                    "Materialize the logic as a view/table in the warehouse.",
                    [
                        f"{len(a.get('ctes', []))} CTE(s), {a.get('subqueryCount', 0)} subquery(ies), "
                        f"{len(a.get('windowFunctions', []))} window fn(s)"
                    ],
                ))

    for ds in wb.data_sources:
        for t in ds.tables:
            if t.row_count and t.row_count >= LARGE_TABLE_ROWS:
                findings.append(Finding(
                    "scalability", f"Large table: {t.name}", MEDIUM,
                    "Large tables slow extracts, refreshes and query response.",
                    "Use incremental extracts, aggregation, or partitioning.",
                    [f"{t.name}: {t.row_count:,} rows"],
                ))

    if cx["calculatedFields"] > MANY_CALCS:
        findings.append(Finding(
            "scalability", "High number of calculated fields", LOW,
            "Many calculations increase maintenance burden and query overhead.",
            "Rationalize calculations; push stable logic to the data source.",
            [f"{cx['calculatedFields']} calculated fields"],
        ))

    return findings
