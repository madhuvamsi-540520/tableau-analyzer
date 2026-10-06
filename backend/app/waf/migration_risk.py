"""Migration Risk & Complexity pillar (reuses the migration estimator output)."""
from __future__ import annotations

from .base import Pillar
from .pillar import Check, PillarResult

_COMPLEXITY_SEV = {"Low": "info", "Medium": "medium", "High": "high", "Very High": "critical"}


class MigrationRiskPillar(Pillar):
    key = "migrationRisk"
    name = "Migration Risk & Complexity"
    weight = 0.05

    def analyze(self, ctx) -> PillarResult:
        mig = ctx.migration or {}
        readiness = mig.get("readiness", 100)
        complexity = mig.get("complexity", "Low")
        effort = mig.get("effort", {}) or {}
        risks = mig.get("risks", []) or []

        checks: list[Check] = [
            Check(
                id="readiness",
                title="Migration readiness",
                status="pass" if readiness >= 70 else ("warn" if readiness >= 50 else "fail"),
                severity="info" if readiness >= 70 else ("medium" if readiness >= 50 else "high"),
                metric=f"{readiness}/100",
                detail=f"Deterministic readiness score is {readiness}/100.",
                recommendation="Address the manual-effort items and high-severity findings to raise readiness.",
                benefit="Higher confidence for stakeholder sign-off.",
            ),
            Check(
                id="complexity",
                title="Overall migration complexity",
                status="pass" if complexity in ("Low", "Medium") else "warn",
                severity=_COMPLEXITY_SEV.get(complexity, "medium"),
                metric=complexity,
                detail=f"Estimated effort: {effort.get('hours', '—')} h "
                       f"(~{effort.get('weeks', '—')} weeks).",
                recommendation=mig.get("strategy", "Plan a phased migration with validation gates."),
                benefit="Realistic planning and resourcing.",
            ),
        ]
        for i, r in enumerate(risks[:6]):
            checks.append(Check(
                id=f"risk-{i}", title="Migration risk", status="warn", severity="medium",
                detail=r, recommendation="Mitigate during the migration project.",
            ))

        summary = f"Readiness {readiness}/100 · complexity {complexity} · ~{effort.get('weeks', '—')} weeks."
        return PillarResult(self.key, self.name, int(readiness), self.weight, summary, checks)


PILLAR = MigrationRiskPillar()
