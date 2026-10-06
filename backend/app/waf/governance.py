"""Governance pillar (assessment reuse + naming-convention validator)."""
from __future__ import annotations

import re

from .base import Pillar
from .pillar import Check, PillarResult, score_from_checks
from .util import checks_from_sections

# Auto-generated / placeholder names migration tools and authors leave behind.
_BAD_NAME = re.compile(r"^(calc(ulation)?[_ ]?\d+|measure\s*\d+|new measure|sheet\s*\d*|"
                       r"table\s*\d+|field\s*\d+|column\s*\d+|untitled.*|dashboard\s*\d+)$", re.I)


class GovernancePillar(Pillar):
    key = "governance"
    name = "Governance"
    weight = 0.10

    def analyze(self, ctx) -> PillarResult:
        checks = checks_from_sections(ctx.assessment, "governance")

        # 1. Naming conventions --------------------------------------------- #
        bad = []
        for c in ctx.calcs:
            if _BAD_NAME.match((c.name or "").strip()):
                bad.append(c.name)
        for t in ctx.tables:
            if _BAD_NAME.match((t.name or "").strip()):
                bad.append(t.name)
        for ws in ctx.wb.worksheets:
            if _BAD_NAME.match((ws.name or "").strip()):
                bad.append(ws.name)
        checks.append(Check(
            id="naming-conventions",
            title="Naming conventions",
            status="warn" if bad else "pass",
            severity="medium" if bad else "info",
            metric=f"{len(bad)} poorly-named object(s)",
            detail=("Auto/placeholder names: " + ", ".join(bad[:12])) if bad else
                   "No placeholder/auto-generated names detected.",
            recommendation=("Rename to business-friendly, consistent names (e.g. 'Total Sales', "
                            "'Gross Profit %') and apply an organization naming standard." if bad else ""),
            benefit="Discoverable, maintainable, self-documenting model.",
            evidence=bad[:20],
        ))

        # 2. Documentation / descriptions ----------------------------------- #
        n_ds = len(ctx.wb.data_sources) or 1
        described = sum(1 for ds in ctx.wb.data_sources if (ds.description or "").strip())
        pct = round(100 * described / n_ds)
        checks.append(Check(
            id="documentation",
            title="Metadata & descriptions",
            status="pass" if pct >= 60 else "warn",
            severity="info" if pct >= 60 else "low",
            metric=f"{pct}% documented",
            detail=f"{described}/{n_ds} data source(s) have a description.",
            recommendation="Add descriptions to data sources, tables and key measures." if pct < 60 else "",
            benefit="Faster onboarding; certification readiness.",
        ))

        score = score_from_checks(checks)
        summary = f"{len(bad)} naming issue(s); {pct}% of data sources documented."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


PILLAR = GovernancePillar()
