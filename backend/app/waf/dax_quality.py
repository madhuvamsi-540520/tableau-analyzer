"""DAX & Formula quality pillar (reads the DAX-enriched CalcMeta)."""
from __future__ import annotations

from collections import Counter

from .base import Pillar
from .pillar import Check, PillarResult, score_from_checks

_NEST_WARN = 3   # dependency depth at which nested-calc risk becomes notable


class DaxQualityPillar(Pillar):
    key = "daxQuality"
    name = "DAX & Formula Quality"
    weight = 0.15

    def analyze(self, ctx) -> PillarResult:
        calcs = ctx.calcs
        checks: list[Check] = []

        if not calcs:
            return PillarResult(self.key, self.name, 100, self.weight,
                                "No calculated fields in this workbook.", [])

        # 1. LOD migration risk --------------------------------------------- #
        lods = [c for c in calcs if c.lod]
        lod_manual = [c for c in lods if c.power_bi_support in ("Unsupported", "Manual") or c.migration_complexity in ("High", "Very High")]
        checks.append(Check(
            id="lod-risk",
            title="LOD expression migration risk",
            status="fail" if lod_manual else ("warn" if lods else "pass"),
            severity="high" if lod_manual else ("medium" if lods else "info"),
            metric=f"{len(lods)} LOD expression(s)",
            detail=f"{len(lods)} LOD expressions; {len(lod_manual)} need manual DAX rewrites "
                   f"(FIXED/INCLUDE/EXCLUDE → CALCULATE with modified filter context).",
            recommendation=("Rewrite complex LODs with CALCULATE and correct filter/grain context; validate "
                            "against Tableau numbers." if lods else "No LOD expressions."),
            benefit="Avoids silently-wrong cross-grain aggregations after migration.",
        ))

        # 2. Nested calculation depth --------------------------------------- #
        max_depth = max((c.dependencies.get("depth", 0) for c in calcs), default=0)
        deep = [c.name for c in calcs if c.dependencies.get("depth", 0) >= _NEST_WARN]
        checks.append(Check(
            id="nested-depth",
            title="Nested calculation depth",
            status="fail" if max_depth >= _NEST_WARN + 2 else ("warn" if deep else "pass"),
            severity="high" if max_depth >= _NEST_WARN + 2 else ("medium" if deep else "info"),
            metric=f"max depth {max_depth}",
            detail=f"Deepest calc-on-calc chain is {max_depth}. Deep calcs: {', '.join(deep[:8]) or '—'}.",
            recommendation=("Flatten deep dependency chains before migration; consolidate with variables "
                            "(VAR/RETURN)." if deep else "Dependency chains are shallow."),
            benefit="Lower migration complexity and easier debugging.",
        ))

        # 3. Quick table calculations --------------------------------------- #
        tcs = [c for c in calcs if c.table_calc]
        tc_manual = [c for c in tcs if c.power_bi_support in ("Unsupported", "Manual")]
        tc_auto = len(tcs) - len(tc_manual)
        checks.append(Check(
            id="table-calcs",
            title="Quick table calculation conversion",
            status="warn" if tcs else "pass",
            severity="medium" if tcs else "info",
            metric=f"{len(tcs)} table calc(s)",
            detail=f"{len(tcs)} table calculations — {tc_auto} auto-convertible, {len(tc_manual)} need manual review "
                   "(WINDOW_/RANK/RUNNING_/LOOKUP → DAX window functions).",
            recommendation=("Convert running-total/percent-of-total/moving-average patterns to the matching DAX "
                            "window functions; review the manual ones." if tcs else "No table calculations."),
            benefit="Correct time-series and ranking results in Power BI.",
        ))

        # 4. Circular dependencies ------------------------------------------ #
        cycles = _find_cycles({c.name: c.dependencies.get("parents", []) for c in calcs})
        checks.append(Check(
            id="circular-deps",
            title="Circular calculation dependencies",
            status="fail" if cycles else "pass",
            severity="critical" if cycles else "info",
            metric=f"{len(cycles)} cycle(s)",
            detail=("Circular references: " + "; ".join(" → ".join(c) for c in cycles[:5])) if cycles else
                   "No circular dependencies detected.",
            recommendation=("Break the cycle — Power BI rejects circular calculation dependencies." if cycles else ""),
            benefit="Prevents a model that will not load in Power BI.",
        ))

        # 5. Duplicate calculations ----------------------------------------- #
        formula_counts = Counter((c.formula or "").strip() for c in calcs if (c.formula or "").strip())
        dups = [f for f, n in formula_counts.items() if n > 1]
        checks.append(Check(
            id="duplicate-calcs",
            title="Duplicate calculations",
            status="warn" if dups else "pass",
            severity="low" if dups else "info",
            metric=f"{len(dups)} duplicated formula(s)",
            detail=f"{len(dups)} formulas are defined more than once." if dups else "No duplicate formulas.",
            recommendation="Consolidate duplicates into a single reusable measure." if dups else "",
            benefit="Less maintenance and a leaner model.",
        ))

        score = score_from_checks(checks)
        summary = f"{len(calcs)} calculations — {len(lods)} LOD, {len(tcs)} table-calc, max depth {max_depth}."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


def _find_cycles(parents: dict[str, list[str]]) -> list[list[str]]:
    """Return simple cycles in the calc dependency graph (best-effort, capped)."""
    cycles: list[list[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in parents}

    def dfs(node, stack):
        color[node] = GRAY
        stack.append(node)
        for nxt in parents.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                i = stack.index(nxt)
                cycles.append(stack[i:] + [nxt])
            elif color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for n in parents:
        if color[n] == WHITE:
            dfs(n, [])
    return cycles[:10]


PILLAR = DaxQualityPillar()
