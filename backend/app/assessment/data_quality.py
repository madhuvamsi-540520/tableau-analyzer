"""Data-quality analyzer: nullable/mismatched join keys, missing relationships.

Checks that need actual data values (duplicate keys, orphan records) cannot be
confirmed from metadata; the potential is surfaced via missing-PK / nullable-key
findings rather than asserted as fact.
"""
from __future__ import annotations

from .finding import Finding, HIGH, MEDIUM
from .util import find_column, isolated_tables, split_ref


def analyze(wb) -> list[Finding]:
    findings: list[Finding] = []

    for ds in wb.data_sources:
        for r in ds.relationships:
            for c in r.conditions:
                lt, lc = split_ref(c.left)
                rt, rc = split_ref(c.right)
                lcol = find_column(ds, lt, lc)
                rcol = find_column(ds, rt, rc)

                # Nullable join keys -> dropped / unmatched rows.
                for tname, cname, col in ((lt, lc, lcol), (rt, rc, rcol)):
                    if col is not None and col.nullable is True:
                        findings.append(Finding(
                            "data-quality", f"Nullable join key: {tname}.{cname}", HIGH,
                            "NULLs in a join key drop rows (inner join) or create unmatched rows (outer).",
                            "Enforce NOT NULL on keys, or clean NULLs before joining.",
                            [f"{tname}.{cname}"],
                        ))

                # Data-type mismatch across a join key.
                if lcol and rcol and lcol.data_type != rcol.data_type:
                    findings.append(Finding(
                        "data-quality", "Join key data-type mismatch", HIGH,
                        "Type mismatches force implicit casts, hurting performance and correctness.",
                        "Align key data types on both sides of the join.",
                        [f"{lt}.{lc} ({lcol.data_type}) vs {rt}.{rc} ({rcol.data_type})"],
                    ))

        # Missing relationships (isolated tables in a multi-table source).
        isolated = isolated_tables(ds.tables, ds.relationships)
        if isolated:
            findings.append(Finding(
                "data-quality", "Isolated tables (no relationships)", MEDIUM,
                "Unrelated tables cannot be analyzed together and may indicate a missing join.",
                "Add the missing relationship, or remove the unused table.", isolated,
            ))

    return findings
