"""Semantic Model Readiness pillar (naming + metadata completeness)."""
from __future__ import annotations

from .base import Pillar
from .governance import _BAD_NAME
from .pillar import Check, PillarResult, score_from_checks


class SemanticReadinessPillar(Pillar):
    key = "semanticReadiness"
    name = "Semantic Model Readiness"
    weight = 0.10

    def analyze(self, ctx) -> PillarResult:
        checks: list[Check] = []

        # Naming quality (share of well-named calcs/tables).
        objs = [c.name for c in ctx.calcs] + [t.name for t in ctx.tables]
        bad = [o for o in objs if _BAD_NAME.match((o or "").strip())]
        naming_ok = 100 if not objs else round(100 * (len(objs) - len(bad)) / len(objs))
        checks.append(Check(
            id="naming-standard",
            title="Naming standards",
            status="pass" if naming_ok >= 90 else "warn",
            severity="info" if naming_ok >= 90 else "low",
            metric=f"{naming_ok}% well-named",
            detail=f"{len(objs) - len(bad)}/{len(objs) or 0} objects follow a clean naming standard.",
            recommendation="Standardize object names before publishing the semantic model." if naming_ok < 90 else "",
            benefit="Consistent, professional semantic model.",
        ))

        # Column metadata completeness (data types + captions present).
        cols = [c for t in ctx.tables for c in t.columns]
        typed = sum(1 for c in cols if c.data_type)
        typed_pct = 100 if not cols else round(100 * typed / len(cols))
        checks.append(Check(
            id="metadata-complete",
            title="Metadata completeness",
            status="pass" if typed_pct >= 90 else "warn",
            severity="info" if typed_pct >= 90 else "low",
            metric=f"{typed_pct}% columns typed",
            detail=f"{typed}/{len(cols) or 0} columns carry a data type.",
            recommendation="Ensure every column has a correct data type and a friendly caption." if typed_pct < 90 else "",
            benefit="Reliable formatting, sorting and relationships.",
        ))

        # Measure organization (display folders) — not expressible pre-PBIP.
        checks.append(Check(
            id="measure-folders",
            title="Measure organization (display folders)",
            status="na", severity="info",
            detail="Display folders and a dedicated measures table are set up in Power BI.",
            recommendation="Group measures into display folders and a Measures table during build.",
            benefit="Navigable, maintainable model for report authors.",
        ))

        score = score_from_checks(checks, base=round((naming_ok + typed_pct) / 2))
        summary = f"Naming {naming_ok}% · metadata {typed_pct}% complete."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


PILLAR = SemanticReadinessPillar()
