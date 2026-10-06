"""Canonical, immutable context assembled once and shared by every analyzer.

Mirrors the WAF context pattern: build it from the parsed workbook, then hand the
same object to the similarity engine, the visualization rule engine, the
dashboard-quality analyzer and the KPI analyzer. Nothing downstream re-reads XML.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .features import WorksheetFeature, build_worksheet_features


@dataclass
class RationalizationContext:
    worksheets: list[WorksheetFeature]
    dashboards: list                      # DashboardMeta (has layout detail)
    stories: list
    ws_by_name: dict[str, WorksheetFeature] = field(default_factory=dict)
    all_measures: set = field(default_factory=set)
    all_dimensions: set = field(default_factory=set)

    @property
    def dashboard_count(self) -> int:
        return len(self.dashboards)

    @property
    def worksheet_count(self) -> int:
        return len(self.worksheets)


def build_context(wb) -> RationalizationContext:
    features = build_worksheet_features(wb)
    ctx = RationalizationContext(
        worksheets=features,
        dashboards=list(wb.dashboards),
        stories=list(wb.stories),
        ws_by_name={f.name: f for f in features},
    )
    for f in features:
        ctx.all_measures |= set(f.measures)
        ctx.all_dimensions |= set(f.dimensions)
    return ctx
