"""Technical Debt pillar (assessment reuse + unused objects + broken references)."""
from __future__ import annotations

from ..dax import references
from .base import Pillar
from .pillar import Check, PillarResult, score_from_checks
from .util import checks_from_sections


class TechnicalDebtPillar(Pillar):
    key = "technicalDebt"
    name = "Technical Debt"
    weight = 0.10

    def analyze(self, ctx) -> PillarResult:
        checks = checks_from_sections(ctx.assessment, "technicalDebt")

        # 1. Unused parameters / sets / groups ------------------------------ #
        used = ctx.referenced_names
        unused_params = sorted(ctx.param_names - used)
        unused_sets = sorted(ctx.set_names - used)
        unused_groups = sorted(ctx.group_names - used)
        unused_total = len(unused_params) + len(unused_sets) + len(unused_groups)
        checks.append(Check(
            id="unused-objects",
            title="Unused parameters / sets / groups",
            status="warn" if unused_total else "pass",
            severity="low" if unused_total else "info",
            metric=f"{unused_total} unused object(s)",
            detail=f"Unused — parameters: {len(unused_params)}, sets: {len(unused_sets)}, groups: {len(unused_groups)}.",
            recommendation="Drop unused objects instead of carrying them into Power BI." if unused_total else "",
            benefit="Less clutter and lower migration effort.",
            evidence=(unused_params + unused_sets + unused_groups)[:20],
        ))

        # 2. Broken references (calc referencing a name that resolves to nothing) #
        known = ctx.calc_names | set(ctx.field_lookup) | ctx.param_names | ctx.set_names | ctx.group_names | ctx.bin_names
        broken = []
        for c in ctx.calcs:
            for ref in references.extract_refs(c.formula):
                if ref not in known:
                    broken.append(f"{c.name} → [{ref}]")
        checks.append(Check(
            id="broken-refs",
            title="Broken calculation references",
            status="fail" if broken else "pass",
            severity="high" if broken else "info",
            metric=f"{len(broken)} unresolved reference(s)",
            detail=("Unresolved: " + "; ".join(broken[:10])) if broken else "All calc references resolve.",
            recommendation="Fix or remove calculations that reference missing fields." if broken else "",
            benefit="Avoids broken measures after migration.",
            evidence=broken[:20],
        ))

        score = score_from_checks(checks)
        summary = f"{unused_total} unused object(s); {len(broken)} broken reference(s)."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


PILLAR = TechnicalDebtPillar()
