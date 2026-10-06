"""Immutable canonical model every pillar reads.

Assembled once from the parsed workbook plus the already-computed
``wb.assessment`` / ``wb.migration`` / DAX-enriched ``CalcMeta`` / classification.
Keeping this as a single read-only view keeps the pillar analyzers independent
and testable (they never re-scan files or re-parse XML).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..dax import references


@dataclass
class WafContext:
    wb: object
    assessment: dict = field(default_factory=dict)
    migration: dict = field(default_factory=dict)
    calcs: list = field(default_factory=list)          # CalcMeta across all data sources
    tables: list = field(default_factory=list)         # TableMeta across all data sources
    calc_names: set = field(default_factory=set)
    param_names: set = field(default_factory=set)
    set_names: set = field(default_factory=set)
    group_names: set = field(default_factory=set)
    bin_names: set = field(default_factory=set)
    referenced_names: set = field(default_factory=set) # names used by any calc formula or worksheet
    field_lookup: dict = field(default_factory=dict)   # name -> (table, column)

    @property
    def relationships(self) -> list:
        return [r for ds in self.wb.data_sources for r in ds.relationships]

    @property
    def classifications(self) -> list:
        return [ds.classification or {} for ds in self.wb.data_sources]


def build_context(wb) -> WafContext:
    calcs = [c for ds in wb.data_sources for c in ds.calculations]
    tables = [t for ds in wb.data_sources for t in ds.tables]
    ctx_refs = references.context_from_wb(wb)

    referenced: set[str] = set()
    for c in calcs:
        referenced.update(references.extract_refs(c.formula))
    for ws in wb.worksheets:
        referenced.update(f.field for f in ws.fields if f.field)
        referenced.update(ws.rows_shelf or [])
        referenced.update(ws.cols_shelf or [])
        referenced.update(ws.filters or [])

    return WafContext(
        wb=wb,
        assessment=wb.assessment or {},
        migration=wb.migration or {},
        calcs=calcs,
        tables=tables,
        calc_names={c.name for c in calcs},
        param_names={p.name for p in wb.parameters},
        set_names={s.name for ds in wb.data_sources for s in ds.sets},
        group_names={g.name for ds in wb.data_sources for g in ds.groups},
        bin_names={b.name for ds in wb.data_sources for b in ds.bins},
        referenced_names=referenced,
        field_lookup=ctx_refs["field_lookup"],
    )
