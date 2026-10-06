"""Modeling-risk analyzer: missing PKs, non-key joins (fan/grain), chasm traps, ambiguous joins."""
from __future__ import annotations

from collections import defaultdict

from .finding import Finding, HIGH, MEDIUM
from .util import graph, is_key_name, split_ref


def analyze(wb) -> list[Finding]:
    findings: list[Finding] = []

    for ds in wb.data_sources:
        names, edges, adj, degree = graph(ds.tables, ds.relationships)
        facts = set(ds.classification.get("factTables", []))

        # Missing primary keys.
        for t in ds.tables:
            if not any(is_key_name(c.name) or is_key_name(c.original_name) for c in t.columns):
                findings.append(Finding(
                    "modeling-risk", f"Table '{t.name}' has no identifiable primary key", MEDIUM,
                    "Without a key, grain is unclear and joins may duplicate rows.",
                    "Define or confirm a primary key / unique business key.", [t.name],
                ))

        # Joins on non-key columns -> grain / fan-out / many-to-many risk.
        for r in ds.relationships:
            for c in r.conditions:
                lcol = split_ref(c.left)[1]
                rcol = split_ref(c.right)[1]
                if not (is_key_name(lcol) or is_key_name(rcol)):
                    findings.append(Finding(
                        "modeling-risk", "Join on non-key column (grain / many-to-many risk)", HIGH,
                        "Joining on non-unique columns can multiply rows (fan-out) and inflate measures.",
                        "Join on unique keys; verify cardinality and grain.",
                        [f"{r.left_table}.{lcol} = {r.right_table}.{rcol}"],
                    ))
                    break

        # Chasm trap: a dimension shared by two or more fact tables.
        for t in ds.tables:
            fact_neighbors = [n for n in adj[t.name] if n in facts]
            if len(fact_neighbors) >= 2:
                findings.append(Finding(
                    "modeling-risk", "Chasm trap risk (dimension shared by multiple facts)", HIGH,
                    "Two fact tables sharing a dimension can double-count through the shared path.",
                    "Separate the queries or use relationship-aware (LOD) measures.",
                    [f"{t.name} shared by {', '.join(fact_neighbors)}"],
                ))

        # Ambiguous joins: more than one join path between the same pair of tables.
        pairs: dict[frozenset, int] = defaultdict(int)
        for r in ds.relationships:
            pairs[frozenset([r.left_table, r.right_table])] += 1
        for pair, count in pairs.items():
            if count > 1 and len(pair) == 2:
                a, b = tuple(pair)
                findings.append(Finding(
                    "modeling-risk", "Ambiguous join (multiple paths between tables)", MEDIUM,
                    "Multiple joins between the same tables create ambiguous query paths.",
                    "Consolidate to a single, well-defined relationship.",
                    [f"{a} ↔ {b} ({count} paths)"],
                ))

    return findings
