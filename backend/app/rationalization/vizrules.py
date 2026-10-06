"""Visualization best-practice rule engine (deterministic, plugin-based).

Each rule is a pure function ``(WorksheetFeature) -> list[VizIssue]``. Adding a new
rule means writing a function and appending it to ``RULES`` — no existing rule
changes (Open/Closed). Every issue names the framework/principle it enforces
(Few, Tufte, Cleveland & McGill, Gestalt, Tableau/Power BI guidance, WCAG) so the
recommendation is explainable, and carries a recommended replacement visual.

The rules are grounded in metadata that is actually derivable from the workbook
(mark type, encodings in use, field counts, presence of a date field). Signals
that need pixel/render information (exact category counts, palette contrast) are
flagged as heuristic in the reason text rather than asserted as exact.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..assessment.finding import HIGH, INFO, LOW, MEDIUM


@dataclass
class VizIssue:
    worksheet: str
    current_viz: str
    issue: str
    severity: str
    principle: str
    framework: str
    business_impact: str
    recommended_viz: str
    reason: str
    metric: str = ""

    def to_api(self) -> dict:
        return {
            "worksheet": self.worksheet,
            "currentViz": self.current_viz,
            "issue": self.issue,
            "severity": self.severity,
            "principle": self.principle,
            "framework": self.framework,
            "businessImpact": self.business_impact,
            "recommendedViz": self.recommended_viz,
            "reason": self.reason,
            "metric": self.metric,
        }


# --------------------------------------------------------------------------- #
# Individual rules
# --------------------------------------------------------------------------- #
def _rule_pie(ws) -> list[VizIssue]:
    if "pie" not in ws.viz_type.lower() and ws.mark != "pie":
        return []
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Pie / donut chart used for category comparison",
        severity=MEDIUM,
        principle="Angles/areas are judged far less accurately than aligned length",
        framework="Cleveland & McGill · Stephen Few",
        business_impact="Viewers cannot rank or compare slices precisely, so relative values are misread.",
        recommended_viz="Horizontal Bar Chart (or Treemap if part-to-whole with many parts)",
        reason="Pie charts lose readability beyond ~5-6 categories; a bar chart gives an aligned "
               "baseline for accurate comparison. (Category count is not exact from metadata — heuristic.)",
        metric=f"{len(ws.dimensions)} dimension(s) encoded",
    )]


def _rule_over_encoded(ws) -> list[VizIssue]:
    channels = ws.encodings & {"color", "size", "shape", "label", "detail"}
    if len(channels) < 4:
        return []
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Too many simultaneous encodings on one visual",
        severity=MEDIUM,
        principle="Every added channel raises cognitive load and lowers the data-ink ratio",
        framework="Edward Tufte · Stephen Few",
        business_impact="Over-encoded marks are hard to decode; the key message is buried.",
        recommended_viz="Split into focused views or drop redundant channels",
        reason="4+ visual channels (color/size/shape/label/detail) are active at once. Reduce to the "
               "one or two that carry the insight.",
        metric=f"{len(channels)} encoding channels: {', '.join(sorted(channels))}",
    )]


def _rule_dense_table(ws) -> list[VizIssue]:
    is_table = "table" in ws.viz_type.lower() or "crosstab" in ws.viz_type.lower()
    if not is_table or ws.field_count < 8:
        return []
    sev = MEDIUM if ws.field_count >= 12 else LOW
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Wide text table with many fields",
        severity=sev,
        principle="Tables force serial reading; graphics enable pattern detection",
        framework="Stephen Few — Information Dashboard Design",
        business_impact="Large tables slow comprehension and hide trends/outliers.",
        recommended_viz="Focused bar/line view, or a matrix limited to the key measures",
        reason="Dense tables are hard to scan. Show only the fields the decision needs, and move "
               "detail behind drill-through.",
        metric=f"{ws.field_count} fields on the sheet",
    )]


def _rule_overcrowded(ws) -> list[VizIssue]:
    if ws.field_count < 12 or "table" in ws.viz_type.lower():
        return []
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Overcrowded visual (too many fields)",
        severity=LOW,
        principle="Working memory holds only a few elements at once",
        framework="Nielsen Norman Group (NN/g) · Gestalt",
        business_impact="Cluttered visuals increase time-to-insight and error rate.",
        recommended_viz="Break into small multiples or several focused visuals",
        reason="A single visual carries a large number of distinct fields; consider decomposition.",
        metric=f"{ws.field_count} fields on the sheet",
    )]


def _rule_wrong_trend(ws) -> list[VizIssue]:
    # A bar/column over a date axis usually reads better as a line for trend.
    if ws.mark not in ("bar",) or not ws.dates:
        return []
    if "line" in ws.viz_type.lower():
        return []
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Bars used for a time series",
        severity=MEDIUM,
        principle="Connected lines encode trend and continuity better than separated bars",
        framework="Tableau Visual Best Practices",
        business_impact="Trend direction and rate of change are harder to see across many periods.",
        recommended_viz="Line Chart",
        reason="A date field is on an axis with bar marks. Lines show change over time more clearly.",
        metric=f"date field(s): {', '.join(sorted(ws.dates))}",
    )]


def _rule_area_stacked(ws) -> list[VizIssue]:
    if ws.mark != "area" or "color" not in ws.encodings:
        return []
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Stacked area chart with a color breakdown",
        severity=LOW,
        principle="Stacked bands share a shifting baseline, so inner series are hard to read",
        framework="Stephen Few",
        business_impact="Comparing individual categories over time is unreliable.",
        recommended_viz="Line Chart (one line per category) or 100% stacked only for part-to-whole",
        reason="Only the bottom band sits on a fixed baseline; the rest drift, defeating comparison.",
        metric="color-segmented area",
    )]


def _rule_heatmap_weak(ws) -> list[VizIssue]:
    if "heat map" not in ws.viz_type.lower():
        return []
    if "color" in ws.encodings and ws.measures:
        return []
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Heat map without a clear measure on color",
        severity=LOW,
        principle="Color intensity must map to a quantitative value to be interpretable",
        framework="Stephen Few · Gestalt",
        business_impact="Without a measure driving color, the heat map carries little information.",
        recommended_viz="Highlight table with a measure on color, or a bar chart",
        reason="No measure is bound to the color channel, so the color carries no magnitude.",
        metric=f"{len(ws.measures)} measure(s)",
    )]


def _rule_accessibility(ws) -> list[VizIssue]:
    # Heuristic accessibility nudge for color-carrying visuals.
    if "color" not in ws.encodings:
        return []
    return [VizIssue(
        worksheet=ws.name, current_viz=ws.viz_type,
        issue="Verify color is color-blind safe",
        severity=INFO,
        principle="Color must not be the only channel conveying meaning",
        framework="WCAG 2.1 (contrast & use of color)",
        business_impact="~8% of male viewers have color-vision deficiency and may miss the encoding.",
        recommended_viz="Use a color-blind-safe palette and add labels/shape as a redundant cue",
        reason="Color encoding is in use. Contrast/palette can't be verified from metadata — confirm "
               "against a color-blind-safe palette. (Heuristic.)",
        metric="color channel active",
    )]


# Plugin registry — append new rules here (Open/Closed).
RULES = [
    _rule_pie,
    _rule_over_encoded,
    _rule_dense_table,
    _rule_overcrowded,
    _rule_wrong_trend,
    _rule_area_stacked,
    _rule_heatmap_weak,
    _rule_accessibility,
]

# Penalty toward the viz-quality score by severity (bounded in the engine).
_PENALTY = {HIGH: 12, MEDIUM: 6, LOW: 3, INFO: 0}
_SEV_ORDER = {"critical": 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4}


def analyze_viz(ctx) -> dict:
    issues: list[VizIssue] = []
    for ws in ctx.worksheets:
        for rule in RULES:
            try:
                issues.extend(rule(ws))
            except Exception:  # noqa: BLE001 - a broken rule must not sink the report
                continue

    issues.sort(key=lambda i: (_SEV_ORDER.get(i.severity, 9), i.worksheet))
    penalty = min(70, sum(_PENALTY.get(i.severity, 0) for i in issues))
    score = max(30, 100 - penalty)

    actionable = [i for i in issues if i.severity != INFO]
    return {
        "score": score,
        "issues": [i.to_api() for i in issues],
        "issueCount": len(actionable),
        "highSeverityCount": sum(1 for i in issues if i.severity == HIGH),
        "mediumSeverityCount": sum(1 for i in issues if i.severity == MEDIUM),
        "lowSeverityCount": sum(1 for i in issues if i.severity == LOW),
    }
