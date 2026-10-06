"""Calculation Intelligence Engine — orchestrator.

Enriches every ``CalcMeta`` in a parsed workbook with the analysis the DAX &
Formula module surfaces: dependency graph, performance rating, data-type
analysis, source worksheet/dashboard usage, a precomputed OFFLINE DAX suggestion,
and per-calc migration figures. Runs at parse time (fail-soft, see analysis.py);
the on-demand LLM path is handled separately by the endpoint.
"""
from __future__ import annotations

from ..migration import constants as K
from . import convert, datatypes, performance, references

# Automation feasibility keyed by the Power BI support disposition.
_FEASIBILITY = {
    "Direct": "High — automatable",
    "Rewrite": "Medium — assisted rewrite",
    "Manual": "Low — manual",
    "Unsupported": "None — manual rebuild",
}


def _worksheet_field_set(ws) -> set[str]:
    """All field names a worksheet references (shelves, encodings, filters)."""
    names: set[str] = set()
    names.update(f.field for f in ws.fields if f.field)
    names.update(ws.rows_shelf or [])
    names.update(ws.cols_shelf or [])
    names.update(ws.filters or [])
    names.update(e.field for e in ws.encodings if e.field)
    return names


def enrich_calculations(wb) -> None:
    """Mutate each ``CalcMeta`` in place with intelligence fields."""
    ctx = references.context_from_wb(wb)
    field_lookup = ctx["field_lookup"]
    param_names = ctx["param_names"]

    all_calcs = [(ds, c) for ds in wb.data_sources for c in ds.calculations]
    if not all_calcs:
        return
    calc_names = {c.name for _, c in all_calcs}

    dep_index = references.build_dependency_index(
        {c.name: c.formula for _, c in all_calcs}, param_names)

    # Which worksheets / dashboards use each calc (dynamic field-name match).
    ws_uses: dict[str, list[str]] = {n: [] for n in calc_names}
    for ws in wb.worksheets:
        used = _worksheet_field_set(ws) & calc_names
        for n in used:
            ws_uses[n].append(ws.name)
    db_uses: dict[str, list[str]] = {n: [] for n in calc_names}
    for db in wb.dashboards:
        db_sheets = set(db.worksheets or [])
        for n in calc_names:
            if db_sheets & set(ws_uses[n]):
                db_uses[n].append(db.name)

    for ds, c in all_calcs:
        refs = references.extract_refs(c.formula)
        ref_fields = [r for r in refs if r in field_lookup and r not in calc_names]
        ref_tables = sorted({field_lookup[r][0] for r in ref_fields})
        params_used = [r for r in refs if r in param_names]
        dep = dep_index.get(c.name, {"parents": [], "children": [], "depth": 0})

        c.data_source = ds.caption or ds.name
        c.worksheets = sorted(ws_uses.get(c.name, []))
        c.dashboards = sorted(db_uses.get(c.name, []))
        c.referenced_fields = ref_fields
        c.referenced_tables = ref_tables
        c.dependencies = {
            "parents": dep["parents"],
            "children": dep["children"],
            "parameters": params_used,
            "depth": dep["depth"],
        }
        c.performance = performance.assess(
            formula=c.formula, categories=c.categories, lod=c.lod,
            table_calc=c.table_calc, dep_depth=dep["depth"],
            child_count=len(dep["children"]))
        field_types = {r: field_lookup[r] and _field_type(wb, field_lookup[r]) for r in ref_fields}
        c.data_types = datatypes.infer(
            formula=c.formula, categories=c.categories,
            field_types={k: v for k, v in field_types.items() if v})
        c.dax = convert.suggest(
            name=c.name, formula=c.formula, categories=c.categories, ctx=ctx)
        c.estimated_effort_hours = K.CALC_HOURS.get(c.migration_complexity, 2.0)
        c.automation_feasibility = _FEASIBILITY.get(c.power_bi_support, "Medium — assisted rewrite")
        c.conversion_confidence = c.dax.get("confidence")


def _field_type(wb, table_col: tuple[str, str]) -> str | None:
    """Look up a physical column's tableau data type by (table, source-column)."""
    table, col = table_col
    for ds in wb.data_sources:
        for t in ds.tables:
            if t.name != table:
                continue
            for c in t.columns:
                if (c.original_name or c.name) == col or c.name == col:
                    return c.data_type
    return None
