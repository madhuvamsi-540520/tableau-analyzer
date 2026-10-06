"""Per-dashboard quality assessment from parsed layout composition.

Scores each dashboard 0-100 from signals that are derivable from the primary
layout: worksheet count, filter/legend/parameter/action counts, and the fraction
of the canvas covered by worksheets (visual density / white space). Signals that
need true render information (pixel alignment, cross-device responsiveness) are
reported as heuristic, per the agreed best-effort approach.
"""
from __future__ import annotations

from ..assessment.finding import HIGH, INFO, LOW, MEDIUM

# Composition thresholds.
_MANY_WORKSHEETS = 8
_BUSY_WORKSHEETS = 5
_MANY_FILTERS = 6
_MANY_LEGENDS = 5
_DENSE = 0.90
_SPARSE = 0.20


def _grade(score: int) -> str:
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 \
        else "D" if score >= 60 else "E" if score >= 50 else "F"


def _density_label(ratio) -> str:
    if ratio is None:
        return "Unknown"
    if ratio >= _DENSE:
        return "Overcrowded"
    if ratio >= 0.55:
        return "Balanced"
    if ratio >= _SPARSE:
        return "Comfortable"
    return "Sparse"


def _assess_one(d) -> dict:
    findings: list[dict] = []
    penalty = 0
    ws_n = len(d.worksheets)
    ratio = d.used_area_ratio

    def add(sev, title, detail, rec, pts):
        nonlocal penalty
        penalty += pts
        findings.append({"severity": sev, "title": title, "detail": detail, "recommendation": rec})

    if ws_n >= _MANY_WORKSHEETS:
        add(HIGH, "Too many worksheets on one dashboard",
            f"{ws_n} worksheets compete for attention.",
            "Split into focused dashboards or use navigation/containers.", 18)
    elif ws_n >= _BUSY_WORKSHEETS:
        add(MEDIUM, "Busy dashboard",
            f"{ws_n} worksheets on a single canvas.",
            "Consider grouping related views or reducing the count.", 8)

    if d.filter_count >= _MANY_FILTERS:
        add(MEDIUM, "High filter count",
            f"{d.filter_count} filter controls on the dashboard.",
            "Consolidate filters or move some to a parameter / filter action.", 8)

    if d.legend_count >= _MANY_LEGENDS:
        add(LOW, "Many legends",
            f"{d.legend_count} legends add visual noise.",
            "Combine or hide redundant legends.", 4)

    if ratio is not None:
        if ratio >= _DENSE:
            add(MEDIUM, "Overcrowded layout",
                f"Worksheets cover ~{round(ratio * 100)}% of the canvas.",
                "Add white space; crowded layouts reduce readability. (Heuristic from zone geometry.)", 8)
        elif ratio < _SPARSE and ws_n:
            add(LOW, "Sparse layout",
                f"Worksheets cover only ~{round(ratio * 100)}% of the canvas.",
                "Use the space or reduce the canvas size. (Heuristic from zone geometry.)", 4)

    if not d.width or not d.height:
        add(INFO, "No fixed size set",
            "Dashboard has no explicit size; responsiveness depends on the target device.",
            "Set a size or use automatic/range sizing deliberately. (Heuristic.)", 0)

    score = max(20, 100 - penalty)
    return {
        "name": d.name,
        "score": score,
        "grade": _grade(score),
        "worksheetCount": ws_n,
        "filterCount": d.filter_count,
        "legendCount": d.legend_count,
        "parameterCount": d.parameter_count,
        "actionCount": d.action_count,
        "extensionCount": d.extension_count,
        "usedAreaRatio": ratio,
        "density": _density_label(ratio),
        "hasDeviceLayouts": d.has_device_layouts,
        "findings": findings,
    }


def analyze_dashboards(ctx) -> dict:
    dashboards = [_assess_one(d) for d in ctx.dashboards]
    avg = round(sum(x["score"] for x in dashboards) / len(dashboards)) if dashboards else 100
    return {
        "dashboards": dashboards,
        "averageScore": avg,
        "grade": _grade(avg),
    }
