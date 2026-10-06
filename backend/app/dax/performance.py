"""Performance Analyzer — deterministic cost/risk rating for a calculation.

Scores signals that make a Tableau calc expensive to evaluate (and expensive to
migrate): table calcs, LOD grain shifts, nested braces, multiple aggregations,
row-level scripts, deep dependency chains and heavy reuse. No hardcoded formula
names — signals come from the already-classified metadata plus the formula text.
"""
from __future__ import annotations

import re

_AGG = re.compile(r"\b(SUM|AVG|COUNT|COUNTD|MIN|MAX|MEDIAN|ATTR|STDEV|VAR|PERCENTILE)\s*\(", re.I)


def assess(*, formula: str, categories: list[str], lod: str | None, table_calc: bool,
           dep_depth: int, child_count: int) -> dict:
    f = formula or ""
    cats = categories or []
    signals: list[str] = []
    score = 0

    if table_calc:
        score += 3
        signals.append("Table calculation — evaluated per partition/addressing; maps to a costly DAX window pattern.")
    if lod:
        score += 2
        signals.append(f"LOD ({lod}) — introduces a separate aggregation grain (CALCULATE with modified filter context).")
    if f.count("{") > 1:
        score += 2
        signals.append("Nested level-of-detail braces — multiple grains evaluated together.")
    if any(c.startswith("RAWSQL") for c in cats):
        score += 3
        signals.append("RAWSQL / SCRIPT — pushed to the source engine; no native Power BI equivalent.")

    agg_count = len(_AGG.findall(f))
    if agg_count >= 3:
        score += 1
        signals.append(f"{agg_count} aggregations in one expression.")

    if dep_depth >= 3:
        score += 2
        signals.append(f"Deep dependency chain (depth {dep_depth}) — nested calc-on-calc evaluation.")
    elif dep_depth == 2:
        score += 1

    if child_count >= 3:
        score += 1
        signals.append(f"Reused by {child_count} other calculations — recomputed in many contexts.")

    if score <= 1:
        rating, risk = "Efficient", "Low"
        rec = "Standard translation; no special performance handling expected."
    elif score <= 4:
        rating, risk = "Moderate", "Medium"
        rec = "Validate filter context and consider a dedicated measure; test with representative data volumes."
    else:
        rating, risk = "Expensive", "High"
        rec = ("Redesign for Power BI: replace window/LOD logic with explicit CALCULATE/"
               "relationship patterns, precompute where possible, and profile before shipping.")

    return {
        "rating": rating,          # Efficient | Moderate | Expensive
        "riskLevel": risk,         # Low | Medium | High
        "score": score,
        "signals": signals,
        "recommendation": rec,
    }
