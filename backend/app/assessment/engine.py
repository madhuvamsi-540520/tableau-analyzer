"""Assessment engine: runs every analyzer and assembles the report + maturity."""
from __future__ import annotations

from collections import Counter

from . import (
    best_practices,
    data_quality,
    governance,
    modeling_risks,
    optimization,
    performance,
    scalability,
    technical_debt,
    tradeoffs,
)
from .finding import sort_findings


def assess(wb) -> dict:
    sections = {
        "technicalDebt": technical_debt.analyze(wb),
        "modelingRisks": modeling_risks.analyze(wb),
        "dataQualityRisks": data_quality.analyze(wb),
        "governance": governance.analyze(wb),
        "scalability": scalability.analyze(wb),
        "performance": performance.analyze(wb),
        "optimization": optimization.analyze(wb),
    }

    best = best_practices.evaluate(wb, sections)
    trade = tradeoffs.analyze(wb)

    all_findings = [f for findings in sections.values() for f in findings]
    by_severity = Counter(f.severity for f in all_findings)

    result = {key: [f.to_api() for f in sort_findings(v)] for key, v in sections.items()}
    result["tradeoffs"] = [t.to_api() for t in trade]
    result["bestPractices"] = best
    result["summary"] = {
        "totalFindings": len(all_findings),
        "bySeverity": dict(by_severity),
        "maturityScore": best["maturityScore"],
        "maturityBand": best["maturityBand"],
    }
    return result
