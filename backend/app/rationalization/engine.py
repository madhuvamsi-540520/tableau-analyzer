"""Dashboard & Worksheet Rationalization engine.

Assembles the whole module: build the canonical context, run the similarity,
consolidation, visualization-quality, dashboard-quality and KPI analyzers, then
compute the executive summary (KPI cards + rationalization/viz scores) and a
prioritized roadmap. Every analyzer is isolated (fail-soft) so one failing
section degrades gracefully rather than sinking the report.
"""
from __future__ import annotations

from . import ai as ai_module
from .consolidation import analyze_consolidation
from .context import build_context
from .dashboard_quality import analyze_dashboards
from .kpi import analyze_kpis
from .similarity import analyze_similarity
from .vizrules import analyze_viz


def _grade(score: int) -> str:
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 \
        else "D" if score >= 60 else "E" if score >= 50 else "F"


def _band(score: int) -> str:
    if score >= 85:
        return "Lean — well rationalized"
    if score >= 70:
        return "Mostly lean — minor consolidation"
    if score >= 55:
        return "Some redundancy — consolidate"
    return "High redundancy — rationalize before migrating"


def _rationalization_score(similarity: dict, total_reports: int) -> int:
    """Estate-relative leanness. Hard duplicates and mergeable clusters dominate;
    review-level overlap contributes lightly, so the score keeps dynamic range
    instead of collapsing to the floor on overlap-heavy estates."""
    redundant = similarity.get("redundantReports", 0)
    ratio = redundant / total_reports if total_reports else 0.0
    penalty = round(min(70,
                        ratio * 55
                        + similarity["duplicateCount"] * 6
                        + len(similarity.get("clusters", [])) * 4))
    return max(30, 100 - penalty)


def _roadmap(consolidation: dict, viz: dict) -> list[dict]:
    """Prioritized actions: high similarity / high-severity issues first."""
    items: list[dict] = []
    for r in consolidation["recommendations"]:
        items.append({
            "priority": {"high": "P1", "medium": "P2", "low": "P3"}.get(r["severity"], "P3"),
            "category": "Consolidation",
            "title": r["title"],
            "severity": r["severity"],
            "action": r["recommendation"],
            "benefit": r["benefit"],
        })
    for i in viz["issues"]:
        if i["severity"] == "info":
            continue
        items.append({
            "priority": {"high": "P1", "medium": "P2", "low": "P3"}.get(i["severity"], "P3"),
            "category": "Visualization",
            "title": f"{i['worksheet']}: {i['issue']}",
            "severity": i["severity"],
            "action": f"{i['recommendedViz']} — {i['reason']}",
            "benefit": i["businessImpact"],
        })
    items.sort(key=lambda x: (x["priority"], x["title"]))
    return items


def run(wb) -> dict:
    ctx = build_context(wb)

    def safe(fn, fallback):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            wb.warnings.append(f"Rationalization section failed ({fn.__name__}): {exc}")
            return fallback

    similarity = safe(lambda: analyze_similarity(ctx),
                      {"pairs": [], "clusters": [], "duplicateCount": 0,
                       "similarCount": 0, "reviewCount": 0})
    consolidation = safe(lambda: analyze_consolidation(ctx, similarity),
                         {"recommendations": [], "estimatedDashboardReduction": 0,
                          "estimatedWorksheetReduction": 0, "estimatedEffortReductionHours": 0,
                          "estimatedConsolidationPct": 0, "estimatedMaintenanceSavingsPct": 0})
    viz = safe(lambda: analyze_viz(ctx),
               {"score": 100, "issues": [], "issueCount": 0, "highSeverityCount": 0,
                "mediumSeverityCount": 0, "lowSeverityCount": 0})
    dash_quality = safe(lambda: analyze_dashboards(ctx),
                        {"dashboards": [], "averageScore": 100, "grade": "A"})
    kpis = safe(lambda: analyze_kpis(ctx), {"kpis": [], "coreKpis": [], "opportunities": []})

    rat_score = _rationalization_score(similarity, ctx.worksheet_count + ctx.dashboard_count)
    roadmap = _roadmap(consolidation, viz)

    executive = {
        "totalDashboards": ctx.dashboard_count,
        "totalWorksheets": ctx.worksheet_count,
        "totalStories": len(ctx.stories),
        "duplicateReports": similarity["duplicateCount"],
        "similarReports": similarity["similarCount"],
        "rationalizationOpportunities": len(consolidation["recommendations"]),
        "vizIssues": viz["issueCount"],
        "highSeverityVizIssues": viz["highSeverityCount"],
        "consolidationPotential": consolidation["estimatedDashboardReduction"],
        "consolidationPotentialPct": consolidation["estimatedConsolidationPct"],
        "effortReductionHours": consolidation["estimatedEffortReductionHours"],
        "maintenanceSavingsPct": consolidation["estimatedMaintenanceSavingsPct"],
        "rationalizationScore": rat_score,
        "rationalizationGrade": _grade(rat_score),
        "rationalizationBand": _band(rat_score),
        "vizQualityScore": viz["score"],
        "vizQualityGrade": _grade(viz["score"]),
        "dashboardQualityScore": dash_quality["averageScore"],
        "coreKpiCount": len(kpis["coreKpis"]),
        "statement": (
            f"{ctx.dashboard_count} dashboards / {ctx.worksheet_count} worksheets analyzed. "
            f"{similarity['duplicateCount']} duplicate + {similarity['similarCount']} similar report "
            f"pairs; ~{consolidation['estimatedDashboardReduction']} dashboard(s) consolidatable "
            f"(~{consolidation['estimatedEffortReductionHours']}h saved). "
            f"{viz['issueCount']} visualization issues ({viz['highSeverityCount']} high)."
        ),
        "counts": {
            "P1": sum(1 for i in roadmap if i["priority"] == "P1"),
            "P2": sum(1 for i in roadmap if i["priority"] == "P2"),
            "P3": sum(1 for i in roadmap if i["priority"] == "P3"),
        },
    }

    report = {
        "executiveSummary": executive,
        "similarity": similarity,
        "consolidation": consolidation,
        "vizQuality": viz,
        "dashboardQuality": dash_quality,
        "kpiConsolidation": kpis,
        "roadmap": roadmap,
    }
    # Offline AI-review summary rides along; the endpoint can regenerate with the LLM.
    report["aiReview"] = safe(lambda: ai_module.review(report), {"method": "offline-summary",
                                                                 "available": False, "summary": "",
                                                                 "notes": []})
    return report


def ai_review(report: dict, *, use_llm: bool = False, api_key: str | None = None,
              guidance: dict | None = None) -> dict:
    """On-demand review facade used by the endpoint."""
    return ai_module.review(report, use_llm=use_llm, api_key=api_key, guidance=guidance)
