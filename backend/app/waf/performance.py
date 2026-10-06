"""Performance Optimization pillar (reuses assessment perf/scalability findings)."""
from __future__ import annotations

from .base import Pillar
from .pillar import Check, PillarResult, score_from_checks
from .util import checks_from_sections


class PerformancePillar(Pillar):
    key = "performance"
    name = "Performance Optimization"
    weight = 0.15

    def analyze(self, ctx) -> PillarResult:
        checks = checks_from_sections(ctx.assessment, "performance", "scalability")

        # Advisor recommendations derived from workbook shape.
        col_calcs = [c for c in ctx.calcs if (c.dax or {}).get("daxColumn")]
        if col_calcs:
            checks.append(Check(
                id="perf-measures",
                title="Convert calculated columns to measures",
                status="warn", severity="medium",
                metric=f"{len(col_calcs)} column-style calc(s)",
                detail="Calculated columns are materialized and inflate the model.",
                recommendation="Move aggregating logic into measures.",
                benefit="Reduced model size and faster refresh.",
            ))
        big_tables = [t for t in ctx.tables if (t.row_count or 0) >= 1_000_000]
        if big_tables:
            checks.append(Check(
                id="perf-incremental",
                title="Incremental refresh for large tables",
                status="warn", severity="medium",
                metric=f"{len(big_tables)} table(s) ≥ 1M rows",
                detail="Large fact tables refresh slowly when fully reloaded.",
                recommendation="Enable incremental refresh with a date range policy; consider aggregations.",
                benefit="Shorter refresh windows; lower resource use.",
            ))
        checks.append(Check(
            id="perf-unused",
            title="Remove unused columns",
            status="pass", severity="info",
            detail="Trim columns not used by any visual or measure to improve compression.",
            recommendation="Hide/remove unused columns; keep only what the report needs.",
            benefit="Better dictionary compression, smaller model.",
        ))

        # Base score from the reused perf/scalability finding severities.
        score = score_from_checks(checks)
        summary = f"{len([c for c in checks if c.status in ('warn', 'fail')])} performance item(s) to address."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


PILLAR = PerformancePillar()
