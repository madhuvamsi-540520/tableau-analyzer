"""Enterprise best-practice review and overall maturity score (0-100).

The score is a transparent weighted average of six dimensions. Dimension
sub-scores are derived deterministically from the model shape, documentation
coverage, naming consistency, and the severity of findings in each area — so the
same workbook always yields the same score, and the number is auditable.
"""
from __future__ import annotations

_MODEL_SCORE = {
    "Star Schema": 90,
    "Galaxy Schema (Fact Constellation)": 82,
    "Snowflake Schema": 80,
    "Flat Model": 60,
    "Hybrid Model": 55,
}

_SEV_PENALTY = {"critical": 30, "high": 20, "medium": 10, "low": 5, "info": 0}

_WEIGHTS = {
    "Dimensional modeling": 0.25,
    "Metadata completeness": 0.15,
    "Naming consistency": 0.10,
    "Governance & PII": 0.15,
    "Performance & complexity": 0.15,
    "Data quality & modeling": 0.20,
}


def _penalty_score(findings, floor: int = 25) -> int:
    total = sum(_SEV_PENALTY.get(f.severity, 0) for f in findings)
    return max(floor, 100 - total)


def _model_score(wb) -> int:
    if not wb.data_sources:
        return 50
    scores = [_MODEL_SCORE.get(ds.classification.get("type", ""), 55) for ds in wb.data_sources]
    return round(sum(scores) / len(scores))


def _meta_score(wb) -> int:
    n = len(wb.data_sources) or 1
    described = sum(1 for ds in wb.data_sources if ds.description and ds.description.strip())
    return round(100 * described / n)


def _band(score: int) -> str:
    if score >= 85:
        return "Excellent (certification-ready)"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Moderate"
    if score >= 40:
        return "Developing"
    return "Low"


def evaluate(wb, sections: dict) -> dict:
    gov_findings = sections.get("governance", [])
    naming_flagged = any(f.title.startswith("Inconsistent naming") for f in gov_findings)

    dm = _model_score(wb)
    meta = _meta_score(wb)
    naming = 70 if naming_flagged else 100
    gov = _penalty_score([f for f in gov_findings if not f.title.startswith("Inconsistent naming")])
    perf = _penalty_score(sections.get("performance", []) + sections.get("scalability", []))
    dq = _penalty_score(sections.get("dataQualityRisks", []) + sections.get("modelingRisks", []))

    dims = {
        "Dimensional modeling": dm,
        "Metadata completeness": meta,
        "Naming consistency": naming,
        "Governance & PII": gov,
        "Performance & complexity": perf,
        "Data quality & modeling": dq,
    }
    score = round(sum(dims[k] * _WEIGHTS[k] for k in dims))

    frameworks = [
        {"name": "Kimball Dimensional Modeling", "score": dm,
         "notes": "Rewards a clear star schema with conformed dimensions and a single fact grain."},
        {"name": "Inmon Enterprise DW", "score": round((meta + dm) / 2),
         "notes": "Emphasizes integrated, well-documented, normalized foundations feeding marts."},
        {"name": "Tableau Best Practices", "score": perf,
         "notes": "Favors extracts for large sources, minimal joins, and pushing logic to the source."},
        {"name": "Power BI Modeling", "score": round((dm + perf) / 2),
         "notes": "Prefers a star schema with single-direction relationships and lean measures."},
        {"name": "Dimensional Modeling Principles", "score": dm,
         "notes": "Clear grain, surrogate keys, and conformed dimensions."},
        {"name": "Data Governance", "score": gov,
         "notes": "Documentation, ownership, PII classification and certification readiness."},
        {"name": "Performance Optimization", "score": perf,
         "notes": "Join reduction, aggregation, push-down and extract strategy."},
        {"name": "Enterprise Reporting Standards", "score": round((meta + naming) / 2),
         "notes": "Consistent naming and complete, discoverable metadata."},
    ]

    explanation = [
        f"{k}: {dims[k]}/100 (weight {int(_WEIGHTS[k] * 100)}%)" for k in dims
    ]

    return {
        "maturityScore": score,
        "maturityBand": _band(score),
        "dimensions": dims,
        "weights": {k: _WEIGHTS[k] for k in _WEIGHTS},
        "frameworks": frameworks,
        "explanation": explanation,
    }
