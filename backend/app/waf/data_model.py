"""Data Model & Architecture pillar."""
from __future__ import annotations

import re

from .base import Pillar
from .pillar import Check, PillarResult, score_from_checks

_MODEL_SCORE = {
    "Star Schema": 90,
    "Galaxy Schema (Fact Constellation)": 82,
    "Snowflake Schema": 78,
    "Flat Model": 50,
    "Hybrid Model": 55,
}
# Column names that are almost always high-cardinality in a fact table.
_HIGH_CARD = re.compile(r"(?:^|[\s_])(id|guid|uuid|email|e-mail|invoice|transaction|order\s*id|"
                        r"account|phone|ssn|number|code|key|timestamp)s?(?:$|[\s_])", re.I)
_DATE_TABLE = re.compile(r"\b(date|calendar|dim.?date|time)\b", re.I)


class DataModelPillar(Pillar):
    key = "dataModel"
    name = "Data Model & Architecture"
    weight = 0.20

    def analyze(self, ctx) -> PillarResult:
        wb = ctx.wb
        checks: list[Check] = []

        # 1. Star schema ----------------------------------------------------- #
        types = [(ds.classification or {}).get("type", "Unknown") for ds in wb.data_sources]
        model_scores = [_MODEL_SCORE.get(t, 55) for t in types] or [55]
        model_base = round(sum(model_scores) / len(model_scores))
        star_like = all(t in ("Star Schema", "Galaxy Schema (Fact Constellation)") for t in types) and types
        facts = sorted({f for ds in wb.data_sources for f in (ds.classification or {}).get("factTables", [])})
        dims = sorted({d for ds in wb.data_sources for d in (ds.classification or {}).get("dimensionTables", [])})
        checks.append(Check(
            id="star-schema",
            title="Star schema implemented",
            status="pass" if star_like else ("warn" if any("Snowflake" in t for t in types) else "fail"),
            severity="info" if star_like else "high",
            metric=", ".join(types),
            detail=f"Model shape(s): {', '.join(types)}. Facts: {', '.join(facts) or '—'}; dimensions: {', '.join(dims) or '—'}.",
            recommendation=("Model is dimensional — keep the single fact grain and conformed dimensions."
                            if star_like else
                            "Refactor toward a star schema: separate dimensions (DimCustomer/DimProduct/"
                            "DimRegion/DimDate) from the fact table; avoid one giant flat table."),
            benefit="Faster DAX, lower memory, simpler relationships.",
            evidence=[f"{ds.caption or ds.name}: {(ds.classification or {}).get('type', '—')}" for ds in wb.data_sources],
        ))

        # 2. Date dimension -------------------------------------------------- #
        has_date_table = any(_DATE_TABLE.search(t.name or "") for t in ctx.tables)
        has_date_cols = any(c.data_type in ("date", "datetime") for t in ctx.tables for c in t.columns)
        checks.append(Check(
            id="date-dimension",
            title="Dedicated Date dimension",
            status="pass" if has_date_table else ("fail" if has_date_cols else "na"),
            severity="info" if has_date_table else ("high" if has_date_cols else "info"),
            metric="Found" if has_date_table else "Not found",
            detail=("A date/calendar table is present." if has_date_table else
                    "Date fields are used but no dedicated Date table was found." if has_date_cols else
                    "No date fields detected."),
            recommendation=("" if has_date_table else
                            "Create a DimDate table and mark it as the Date table so time-intelligence "
                            "(YTD/MTD/QTD) works and date logic stays simple."),
            benefit="Enables time-intelligence functions; simpler YTD/MTD/QTD.",
        ))

        # 3. Relationship count / anti-patterns ------------------------------ #
        rels = ctx.relationships
        n_tables = len(ctx.tables) or 1
        many_to_many = [r for r in rels if (r.cardinality or "").lower() in ("many-to-many", "*:*")]
        excessive = len(rels) > 2 * n_tables
        checks.append(Check(
            id="relationships",
            title="Relationship hygiene",
            status="fail" if many_to_many else ("warn" if excessive else "pass"),
            severity="high" if many_to_many else ("medium" if excessive else "info"),
            metric=f"{len(rels)} relationship(s)",
            detail=f"{len(rels)} relationships across {n_tables} tables; "
                   f"{len(many_to_many)} many-to-many.",
            recommendation=("Replace many-to-many with a bridge table or one-to-many star relationships; "
                            "avoid bidirectional filters." if many_to_many or excessive else
                            "Relationship count is proportionate to the model."),
            benefit="Removes ambiguous filter paths; predictable, faster calculations.",
        ))

        # 4. Calculated column vs measure overuse ---------------------------- #
        col_calcs = [c for c in ctx.calcs if (c.dax or {}).get("daxColumn")]
        aggregatable = [c for c in col_calcs if any(str(x).startswith("Aggregation") for x in (c.categories or []))]
        checks.append(Check(
            id="columns-vs-measures",
            title="Measures preferred over calculated columns",
            status="warn" if aggregatable else "pass",
            severity="medium" if aggregatable else "info",
            metric=f"{len(col_calcs)} column-style calc(s)",
            detail=f"{len(col_calcs)} calculations render as calculated columns; "
                   f"{len(aggregatable)} of those aggregate and could be measures.",
            recommendation=("Convert aggregating calculated columns to measures to shrink the model and "
                            "speed up rendering." if aggregatable else
                            "No obvious calculated-column overuse detected."),
            benefit="Smaller model, faster refresh, better query performance.",
        ))

        # 5. High-cardinality columns (heuristic) ---------------------------- #
        high_card = [f"{t.name}.{c.name}" for t in ctx.tables for c in t.columns
                     if _HIGH_CARD.search(c.name or "") and not c.hidden]
        checks.append(Check(
            id="high-cardinality",
            title="High-cardinality columns",
            status="warn" if high_card else "pass",
            severity="medium" if high_card else "info",
            metric=f"{len(high_card)} likely high-cardinality column(s)",
            detail=("Likely high-cardinality columns (by name/type): " + ", ".join(high_card[:12])
                    + ("…" if len(high_card) > 12 else "")) if high_card else
                   "No obvious high-cardinality columns detected.",
            recommendation=("Remove from visuals, hide from the report layer, or split/aggregate to reduce "
                            "cardinality." if high_card else ""),
            benefit="Lower memory footprint and better compression.",
            evidence=high_card[:20],
        ))

        score = score_from_checks(checks, base=model_base)
        summary = f"Model shape: {', '.join(sorted(set(types)))}. {len(facts)} fact / {len(dims)} dimension table(s)."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


PILLAR = DataModelPillar()
