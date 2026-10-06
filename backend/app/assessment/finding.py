"""Finding and Trade-off value objects shared by all assessment analyzers."""
from __future__ import annotations

from dataclasses import dataclass, field

# Severity ordering (used for sorting / summary counts).
CRITICAL, HIGH, MEDIUM, LOW, INFO = "critical", "high", "medium", "low", "info"
SEVERITY_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4}


@dataclass
class Finding:
    category: str
    title: str
    severity: str
    business_impact: str
    recommendation: str
    evidence: list[str] = field(default_factory=list)

    def to_api(self) -> dict:
        return {
            "category": self.category,
            "title": self.title,
            "severity": self.severity,
            "businessImpact": self.business_impact,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
        }


@dataclass
class Tradeoff:
    aspect: str            # e.g. "Live vs Extract"
    current: str           # what the workbook currently does
    tradeoff: str          # the tension being balanced
    guidance: str          # neutral guidance

    def to_api(self) -> dict:
        return {
            "aspect": self.aspect,
            "current": self.current,
            "tradeoff": self.tradeoff,
            "guidance": self.guidance,
        }


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
