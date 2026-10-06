"""Well-Architected Power BI Framework engine.

Runs every registered pillar over the canonical context, then assembles the
executive scorecard, quick wins, and a prioritized P1/P2/P3 remediation roadmap.
Pillar analyzers are plugins (see :mod:`base`); adding one means writing a module
and appending it to ``REGISTRY`` — nothing else changes (Open/Closed).
"""
from __future__ import annotations

from . import (
    data_model,
    dax_quality,
    fabric_readiness,
    governance,
    migration_risk,
    performance,
    security,
    semantic_readiness,
    technical_debt,
)
from .context import build_context
from .pillar import grade

# Plugin registry — order is display order. Weights sum to 1.0.
REGISTRY = [
    data_model.PILLAR,
    dax_quality.PILLAR,
    performance.PILLAR,
    security.PILLAR,
    governance.PILLAR,
    semantic_readiness.PILLAR,
    technical_debt.PILLAR,
    fabric_readiness.PILLAR,
    migration_risk.PILLAR,
]

# Pillars that require a GENERATED PBIP project (shown as placeholders until PBIP
# generation is wired in — no fabricated scores).
PBIP_PENDING = [
    {"name": "PBIP / TMDL Validation", "reason": "Validates the generated Power BI project structure, TMDL and references."},
    {"name": "Generated DAX & Code Quality", "reason": "Reviews the DAX/JSON the migration engine emits."},
    {"name": "Report & Visual Fidelity", "reason": "Compares Tableau visuals against the produced Power BI report."},
    {"name": "Auto-Fix Engine", "reason": "Applies safe repairs to the generated project."},
    {"name": "CI/CD Validation", "reason": "Checks Git/deployment-pipeline/workspace binding of the PBIP."},
]

_SEV_TO_PRIORITY = {"critical": "P1", "high": "P1", "medium": "P2", "low": "P3", "info": "P3"}


def _band(score: int) -> str:
    if score >= 85:
        return "Production Ready"
    if score >= 70:
        return "Near Ready — minor remediation"
    if score >= 55:
        return "Needs Work"
    return "Not Production Ready"


def run(wb) -> dict:
    ctx = build_context(wb)

    results = []
    for pillar in REGISTRY:
        try:
            results.append(pillar.analyze(ctx))
        except Exception as exc:  # noqa: BLE001 - one pillar failing must not sink the report
            wb.warnings.append(f"WAF pillar '{pillar.name}' failed: {exc}")

    total_weight = sum(r.weight for r in results) or 1.0
    overall = round(sum(r.score * r.weight for r in results) / total_weight)

    # Roadmap: every non-passing check becomes a prioritized action.
    roadmap = []
    for r in results:
        for c in r.checks:
            if c.status in ("warn", "fail") and c.recommendation:
                roadmap.append({
                    "priority": _SEV_TO_PRIORITY.get(c.severity, "P3"),
                    "pillar": r.name,
                    "title": c.title,
                    "severity": c.severity,
                    "action": c.recommendation,
                    "benefit": c.benefit,
                    "metric": c.metric,
                })
    roadmap.sort(key=lambda x: (x["priority"], x["title"]))

    # Quick wins: low-effort, meaningful checks (medium/low severity, not P1).
    quick_wins = [item for item in roadmap if item["priority"] in ("P2", "P3")][:8]

    strengths = [r.name for r in results if r.score >= 80]
    weaknesses = [r.name for r in results if r.score < 60]
    executive_summary = {
        "overall": overall,
        "grade": grade(overall),
        "band": _band(overall),
        "statement": (f"Overall Power BI architecture score {overall}/100 ({_band(overall)}). "
                      + (f"Strong: {', '.join(strengths)}. " if strengths else "")
                      + (f"Focus areas: {', '.join(weaknesses)}." if weaknesses else "No critical weak pillars.")),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "counts": {
            "P1": sum(1 for i in roadmap if i["priority"] == "P1"),
            "P2": sum(1 for i in roadmap if i["priority"] == "P2"),
            "P3": sum(1 for i in roadmap if i["priority"] == "P3"),
        },
    }

    return {
        "overall": {"score": overall, "grade": grade(overall), "band": _band(overall)},
        "pillars": [r.to_api() for r in results],
        "quickWins": quick_wins,
        "roadmap": roadmap,
        "executiveSummary": executive_summary,
        "pbipPending": PBIP_PENDING,
    }
