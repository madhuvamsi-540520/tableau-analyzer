"""Performance analyzer: cartesian joins, nested SQL, multiple extracts, large dims, calc volume, pushdown."""
from __future__ import annotations

from .constants import LARGE_DIM_ROWS, MANY_CALCS
from .finding import Finding, CRITICAL, INFO, LOW, MEDIUM


def analyze(wb) -> list[Finding]:
    findings: list[Finding] = []

    for ds in wb.data_sources:
        dims = set(ds.classification.get("dimensionTables", []))

        # Cartesian product: a join with no conditions.
        for r in ds.relationships:
            if r.kind == "join" and not r.conditions:
                findings.append(Finding(
                    "performance", "Possible cartesian product (join without keys)", CRITICAL,
                    "A keyless join multiplies rows (N×M), exploding result size and time.",
                    "Add explicit join keys or remove the join.",
                    [f"{r.left_table} × {r.right_table}"],
                ))

        # Nested custom SQL (subqueries).
        for s in ds.custom_sql:
            if (s.analysis or {}).get("subqueryCount", 0) > 0:
                findings.append(Finding(
                    "performance", f"Nested subqueries in custom SQL: {s.name}", MEDIUM,
                    "Nested subqueries limit push-down and can be re-evaluated repeatedly.",
                    "Flatten into joins/CTEs or a materialized view.",
                    [f"{s.analysis.get('subqueryCount')} subquery(ies)"],
                ))

        # Large dimension tables.
        for t in ds.tables:
            if t.name in dims and t.row_count and t.row_count >= LARGE_DIM_ROWS:
                findings.append(Finding(
                    "performance", f"Large dimension table: {t.name}", LOW,
                    "Large dimensions slow relationship filtering and rendering.",
                    "Trim dimension attributes or snowflake rarely-used ones.",
                    [f"{t.name}: {t.row_count:,} rows"],
                ))

        # Filter push-down opportunity.
        if ds.filters and (ds.is_extract or ds.custom_sql):
            findings.append(Finding(
                "performance", "Filter push-down opportunity", INFO,
                "Filtering after extract/custom-SQL processes more data than needed.",
                "Push filters into the source query / extract definition.",
                [f.field for f in ds.filters],
            ))

    if wb.complexity()["calculatedFields"] > MANY_CALCS:
        findings.append(Finding(
            "performance", "Excessive calculated fields", LOW,
            "Row-level calculations executed at query time add latency.",
            "Move stable calculations upstream into the data source.",
            [f"{wb.complexity()['calculatedFields']} calculated fields"],
        ))

    return findings
