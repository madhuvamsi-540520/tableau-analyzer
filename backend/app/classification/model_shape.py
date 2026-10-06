"""Deterministic data-model classification.

Classifies a data source's table graph as Flat / Star / Snowflake / Galaxy /
Hybrid using the relationship graph and where the measures live. The result is
reproducible (same input -> same output) and carries the reasoning + the
identified fact/dimension tables so the assessment is auditable, not a guess.

Heuristics (no live data, so this is structural):
- Fact tables carry measures and act as hubs (high relationship degree).
- Dimensions are the tables joined to facts.
- Dimension-to-dimension links => normalization => Snowflake.
- Multiple facts sharing dimensions => Galaxy (fact constellation).
"""
from __future__ import annotations

from collections import defaultdict


def classify(tables, relationships) -> dict:
    names = [t.name for t in tables]
    nameset = set(names)
    measures = {t.name: sum(1 for c in t.columns if c.role == "measure") for t in tables}

    edges = [
        (r.left_table, r.right_table)
        for r in relationships
        if r.left_table in nameset and r.right_table in nameset and r.left_table != r.right_table
    ]

    n, m = len(names), len(edges)

    if n == 0:
        return _result("Flat Model", ["No tables were found in this data source."], [], [])
    if n == 1:
        return _result(
            "Flat Model",
            [f"A single table ('{names[0]}') with no joins — a flat, denormalized model."],
            [],
            names,
        )
    if m == 0:
        return _result(
            "Flat Model",
            [f"{n} tables with no joins or relationships — independent flat tables."],
            [],
            names,
        )

    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    degree = {t: len(adj[t]) for t in names}

    measure_tables = [t for t in names if measures.get(t, 0) > 0]
    if measure_tables:
        hubs = [t for t in measure_tables if degree[t] >= 2]
        if hubs:
            facts = hubs
        else:
            top = max(degree[t] for t in measure_tables)
            facts = [t for t in measure_tables if degree[t] == top]
    else:
        top = max(degree.values())
        facts = [t for t in names if degree[t] == top] if top >= 2 else []

    dims = [t for t in names if t not in facts]

    if not facts:
        return _result(
            "Hybrid Model",
            [
                f"{n} tables and {m} join(s), but no clear fact table (no measures and no central "
                "hub) — the model does not match a canonical star/snowflake shape."
            ],
            facts,
            dims,
        )

    dim_dim_links = [(a, b) for a, b in edges if a not in facts and b not in facts]

    if len(facts) >= 2:
        shared = _shared_dimensions(facts, dims, adj)
        if shared:
            return _result(
                "Galaxy Schema (Fact Constellation)",
                [
                    f"{len(facts)} fact tables ({_join(facts)}) share dimension table(s) "
                    f"({_join(sorted(shared))}) — a fact constellation.",
                ],
                facts,
                dims,
            )
        return _result(
            "Hybrid Model",
            [f"{len(facts)} candidate fact tables ({_join(facts)}) that do not clearly share dimensions."],
            facts,
            dims,
        )

    fact = facts[0]
    if dim_dim_links:
        return _result(
            "Snowflake Schema",
            [
                f"Central fact '{fact}' with {len(dims)} dimension(s), some further normalized "
                f"(dimension-to-dimension links: {_links(dim_dim_links)}).",
            ],
            facts,
            dims,
        )
    return _result(
        "Star Schema",
        [
            f"Central fact '{fact}' joined directly to {len(dims)} dimension table(s) "
            f"({_join(dims)}); dimensions are not interlinked.",
        ],
        facts,
        dims,
    )


def _shared_dimensions(facts, dims, adj) -> set[str]:
    shared = set()
    for d in dims:
        if len([f for f in facts if f in adj[d]]) >= 2:
            shared.add(d)
    return shared


def _join(items) -> str:
    return ", ".join(items) if items else "—"


def _links(pairs) -> str:
    return ", ".join(f"{a}–{b}" for a, b in pairs)


def _result(model_type: str, reasoning: list[str], facts: list[str], dims: list[str]) -> dict:
    return {
        "type": model_type,
        "reasoning": reasoning,
        "factTables": facts,
        "dimensionTables": dims,
    }
