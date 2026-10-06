"""Value objects shared by every Well-Architected pillar.

A ``Check`` is one auditable rule result (pass/warn/fail/na) with a quantified
recommendation; a ``PillarResult`` bundles a pillar's checks with a 0-100 score
and letter grade. Reuses the assessment severities so the two engines stay
consistent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Reuse the assessment severity vocabulary.
CRITICAL, HIGH, MEDIUM, LOW, INFO = "critical", "high", "medium", "low", "info"
SEVERITY_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4}

# Points removed from 100 for a failing/warning check, by severity.
_PENALTY = {CRITICAL: 30, HIGH: 20, MEDIUM: 10, LOW: 5, INFO: 0}

# Check statuses.
PASS, WARN, FAIL, NA = "pass", "warn", "fail", "na"


def grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    if score >= 50:
        return "E"
    return "F"


def score_from_checks(checks: list["Check"], base: int = 100, floor: int = 0) -> int:
    """Deterministic score: subtract severity penalties for non-passing checks."""
    total = sum(_PENALTY.get(c.severity, 0) for c in checks if c.status in (WARN, FAIL))
    return max(floor, min(100, base - total))


@dataclass
class Check:
    id: str
    title: str
    status: str = PASS                       # pass | warn | fail | na
    severity: str = INFO                      # critical | high | medium | low | info
    detail: str = ""
    recommendation: str = ""
    benefit: str = ""                         # quantified expected benefit
    metric: str = ""                          # e.g. "42 calculated columns"
    evidence: list[str] = field(default_factory=list)

    def to_api(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "detail": self.detail,
            "recommendation": self.recommendation,
            "benefit": self.benefit,
            "metric": self.metric,
            "evidence": self.evidence,
        }


@dataclass
class PillarResult:
    key: str
    name: str
    score: int
    weight: float
    summary: str = ""
    checks: list[Check] = field(default_factory=list)

    def to_api(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "score": self.score,
            "grade": grade(self.score),
            "weight": self.weight,
            "summary": self.summary,
            "checks": [c.to_api() for c in self.checks],
            "counts": {
                "pass": sum(1 for c in self.checks if c.status == PASS),
                "warn": sum(1 for c in self.checks if c.status == WARN),
                "fail": sum(1 for c in self.checks if c.status == FAIL),
                "na": sum(1 for c in self.checks if c.status == NA),
            },
        }
