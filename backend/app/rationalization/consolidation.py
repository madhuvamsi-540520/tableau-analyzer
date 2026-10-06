"""Consolidation recommendations + rationalization savings estimate.

Turns similarity clusters, duplicate reports and repeated worksheets into
concrete actions (merge / retire / parameterize / reuse) and estimates the
resulting reduction in dashboard count, migration effort and maintenance.

Effort constants are deterministic and tunable — no LLM. They mirror the
migration estimator's style (default hours per artifact).
"""
from __future__ import annotations

from ..assessment.finding import HIGH, LOW, MEDIUM

# Default effort saved per rationalized artifact (hours). Tunable defaults.
_HOURS_PER_DASHBOARD = 6.0     # build + validate a dashboard during migration
_HOURS_PER_WORKSHEET = 2.0     # rebuild + validate a worksheet
_MAINT_HOURS_PER_DASHBOARD_YR = 3.0


def _severity_for(similarity: int) -> str:
    return HIGH if similarity >= 90 else MEDIUM if similarity >= 75 else LOW


def analyze_consolidation(ctx, similarity: dict) -> dict:
    recs: list[dict] = []
    dashboards_removed = 0
    worksheets_removed = 0

    # 1. Dashboard clusters -> merge into one parameterized dashboard.
    for cluster in similarity["clusters"]:
        n = cluster["size"]
        if cluster["type"] == "dashboard":
            removed = n - 1
            dashboards_removed += removed
            recs.append({
                "kind": "merge",
                "title": f"Merge {n} similar dashboards",
                "targets": cluster["members"],
                "severity": _severity_for(cluster["avgSimilarity"]),
                "rationale": cluster["rationale"],
                "recommendation": cluster["recommendation"],
                "effortSavedHours": round(removed * _HOURS_PER_DASHBOARD, 1),
                "benefit": f"Removes {removed} dashboard(s) from the migration scope.",
            })
        else:  # worksheet near-duplicate cluster
            removed = n - 1
            worksheets_removed += removed
            recs.append({
                "kind": "reuse",
                "title": f"Reuse one of {n} near-duplicate worksheets",
                "targets": cluster["members"],
                "severity": MEDIUM,
                "rationale": cluster["rationale"],
                "recommendation": cluster["recommendation"],
                "effortSavedHours": round(removed * _HOURS_PER_WORKSHEET, 1),
                "benefit": f"Builds {removed} fewer worksheet(s).",
            })

    # 2. Duplicate report pairs not already captured by a cluster (parameterize).
    clustered = {m for c in similarity["clusters"] for m in c["members"]}
    for p in similarity["pairs"]:
        if p["similarity"] < 75:
            continue
        if p["a"] in clustered and p["b"] in clustered:
            continue
        recs.append({
            "kind": "parameterize" if p["similarity"] < 90 else "merge",
            "title": f"{'Merge' if p['similarity'] >= 90 else 'Consolidate'} "
                     f"'{p['a']}' and '{p['b']}'",
            "targets": [p["a"], p["b"]],
            "severity": _severity_for(p["similarity"]),
            "rationale": f"{p['similarity']}% similar ({p['type']}s).",
            "recommendation": p["recommendation"],
            "effortSavedHours": round(
                _HOURS_PER_DASHBOARD if p["type"] == "dashboard" else _HOURS_PER_WORKSHEET, 1),
            "benefit": "Eliminates a redundant report copy.",
        })
        if p["type"] == "dashboard":
            dashboards_removed += 1 if p["similarity"] >= 90 else 0

    recs.sort(key=lambda r: -r["effortSavedHours"])

    total_dashboards = ctx.dashboard_count or 1
    effort_hours = round(
        dashboards_removed * _HOURS_PER_DASHBOARD + worksheets_removed * _HOURS_PER_WORKSHEET, 1)
    maint_pct = round(min(60, (dashboards_removed / total_dashboards) * 100)) if total_dashboards else 0
    consolidation_pct = round((dashboards_removed / total_dashboards) * 100) if total_dashboards else 0

    return {
        "recommendations": recs,
        "estimatedDashboardReduction": dashboards_removed,
        "estimatedWorksheetReduction": worksheets_removed,
        "estimatedEffortReductionHours": effort_hours,
        "estimatedConsolidationPct": consolidation_pct,
        "estimatedMaintenanceSavingsPct": maint_pct,
    }
