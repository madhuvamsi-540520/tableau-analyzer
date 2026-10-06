"""Immutable feature vectors for worksheets and dashboards.

The rationalization engine reasons over *feature vectors* rather than raw XML:
each worksheet is reduced to the sets of measures, dimensions, dates, data
sources, filters and encodings it uses plus its detected visual type. Similarity,
visualization rules and KPI analysis all read these vectors, so the extraction
logic lives in one place (single responsibility) and every downstream analyzer
sees the same canonical view.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _norm(name: str) -> str:
    return (name or "").strip().lower()


_DATE_TYPES = {"date", "datetime"}
_MEASURE_AGG = {"sum", "avg", "count", "countd", "min", "max", "median",
                "stdev", "var", "attr", "agg"}


@dataclass(frozen=True)
class WorksheetFeature:
    name: str
    viz_type: str
    mark: str
    data_sources: frozenset
    measures: frozenset
    dimensions: frozenset
    dates: frozenset
    filters: frozenset
    encodings: frozenset          # channels in use (color/size/shape/label/...)
    field_count: int
    dashboards: tuple             # dashboards that embed this worksheet

    @property
    def fields(self) -> frozenset:
        return self.measures | self.dimensions


def _field_role(f) -> str:
    """dimension | measure, inferred from the explicit role then the aggregation."""
    role = (f.role or "").lower()
    if role in ("measure", "dimension"):
        return role
    if (f.aggregation or "").lower() in _MEASURE_AGG:
        return "measure"
    return "dimension"


def worksheet_feature(ws, dashboards_by_sheet: dict[str, list[str]]) -> WorksheetFeature:
    measures: set[str] = set()
    dimensions: set[str] = set()
    dates: set[str] = set()
    for f in ws.fields:
        n = _norm(f.field)
        if not n:
            continue
        if _field_role(f) == "measure":
            measures.add(n)
        else:
            dimensions.add(n)
        if (f.data_type or "").lower() in _DATE_TYPES:
            dates.add(n)

    return WorksheetFeature(
        name=ws.name,
        viz_type=ws.visual_type or "Unknown",
        mark=(ws.mark_class or "").lower(),
        data_sources=frozenset(_norm(d) for d in ws.data_sources if d),
        measures=frozenset(measures),
        dimensions=frozenset(dimensions),
        dates=frozenset(dates),
        filters=frozenset(_norm(x) for x in ws.filters if x),
        encodings=frozenset(e.channel for e in ws.encodings if e.channel),
        field_count=len(measures) + len(dimensions),
        dashboards=tuple(dashboards_by_sheet.get(ws.name, [])),
    )


def build_worksheet_features(wb) -> list[WorksheetFeature]:
    by_sheet: dict[str, list[str]] = {}
    for d in wb.dashboards:
        for ws_name in d.worksheets:
            by_sheet.setdefault(ws_name, []).append(d.name)
    return [worksheet_feature(ws, by_sheet) for ws in wb.worksheets]
