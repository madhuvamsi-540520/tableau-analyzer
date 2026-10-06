"""Deterministic visual-type detection from worksheet metadata.

Tableau frequently stores mark class 'Automatic' (the effective type is resolved
by "Show Me" at render time), so classification combines the mark class with the
*kind* of fields on the rows/cols shelves (measure / dimension / date / geo), the
encodings in use, and any analytics objects. Every result carries a confidence
score and the XML-derived evidence. When evidence is weak, confidence is low and
the label is prefixed 'Likely' rather than guessed.
"""
from __future__ import annotations

from ..model.metadata import WorksheetMeta

# Shelf-reference prefixes (e.g. 'sum:Profit:qk', 'tyr:Ship Date:qk', 'none:Segment:nk').
_DATE_PREFIXES = {"tyr", "yr", "qr", "mn", "mdy", "wk", "dy", "hr", "min", "sec",
                  "tmn", "tqr", "twk", "tdy", "thr", "iso-year", "week"}
_MEASURE_PREFIXES = {"sum", "avg", "cnt", "cntd", "agg", "min", "max", "med",
                     "usr", "stdev", "stdevp", "var", "varp", "pct"}


def _shelf_kind(ref: str) -> str:
    low = ref.lower()
    if "latitude" in low or "longitude" in low:
        return "geo"
    prefix = ref.split(":", 1)[0].lower() if ":" in ref else ""
    if prefix in _DATE_PREFIXES:
        return "date"
    if prefix in _MEASURE_PREFIXES:
        return "measure"
    if prefix == "none":
        return "dim"
    if ref.endswith("qk"):
        return "measure"
    if ref.endswith(("nk", "ok")):
        return "dim"
    return "other"


def classify_worksheet(ws: WorksheetMeta) -> tuple[str, float, list[str]]:
    rows = [_shelf_kind(r) for r in ws.rows_shelf]
    cols = [_shelf_kind(c) for c in ws.cols_shelf]
    enc = {e.channel for e in ws.encodings}
    mark = (ws.mark_class or "").lower()
    analytics = set(ws.analytics)
    geo = "geo" in rows or "geo" in cols
    has_measure = "measure" in rows or "measure" in cols
    has_date = "date" in rows or "date" in cols
    has_dim = "dim" in rows or "dim" in cols
    no_axes = not ws.rows_shelf and not ws.cols_shelf

    def R(*items):  # evidence helper
        return list(items)

    # 1. Geographic
    if geo:
        if "color" in enc:
            return "Filled Map", 0.82, R("Latitude/Longitude on shelves", "Color encoding → filled areas")
        return "Symbol Map", 0.78, R("Latitude/Longitude on shelves", "No area fill → symbol map")

    # 2. Pie
    if mark == "pie" or "angle" in enc:
        return "Pie / Donut Chart", 0.85, R(f"Mark class '{ws.mark_class}'")

    # 3. No axes + size → treemap / packed bubbles
    if no_axes and "size" in enc:
        if mark == "circle":
            return "Packed Bubbles", 0.8, R("No axes; circle marks sized by measure")
        return "Treemap", 0.72, R("No axes; marks sized/coloured by measure")

    # 4. Highlight table (square marks)
    if mark == "square":
        return "Highlight Table", 0.8, R("Square marks with text/colour encoding")

    # 5. Text table / crosstab (text only, no measure on an axis)
    if enc and enc.issubset({"text", "tooltip", "detail"}) and not has_measure:
        return "Text Table / Crosstab", 0.8, R("Text encoding only; dimensions on shelves; no measure axis")

    # 6. Area
    if mark == "area":
        return "Area Chart", 0.82, R(f"Mark class '{ws.mark_class}'")

    # 7. Scatter — continuous measure on BOTH axes
    if "measure" in rows and "measure" in cols:
        return "Scatter Plot", 0.76, R("Continuous measure on both axes")

    # 8. Bullet / box plot (analytics-driven)
    if mark == "bar" and ("Reference Line" in analytics or "Reference Band" in analytics):
        return "Bullet Graph", 0.7, R("Bar marks with a reference line/band")
    if mark == "circle" and ("Distribution Band" in analytics or "Reference Band" in analytics):
        return "Box Plot", 0.68, R("Circle marks with a distribution band")

    # 9. Time series (date on one axis + measure)
    if has_date and has_measure:
        label = "Line Chart" if mark in ("line", "automatic") else f"{ws.mark_class} over time"
        return label, 0.75, R("Date field on one axis, measure on the other")

    # 10. Circle / shape marks (before the bar rule so they aren't mislabelled)
    if mark in ("circle", "shape"):
        return "Circle Chart", 0.55, R(f"Mark class '{ws.mark_class}' with size/colour encoding")

    # 11. Bar / column (measure + dimension)
    if has_measure and has_dim:
        if "measure" in cols and "dim" in rows:
            return "Bar Chart (horizontal)", 0.74, R("Dimension on rows, measure on columns")
        return "Column Chart (vertical)", 0.74, R("Measure on rows, dimension on columns")

    # 12. Heat map (dimensions + colour, no measure axis)
    if not has_measure and "color" in enc and has_dim:
        return "Heat Map", 0.6, R("Dimensions with colour encoding, no measure axis")

    # 13. Single-measure bar (stacked)
    if "measure" in rows and "color" in enc and not ws.cols_shelf:
        return "Bar Chart (stacked)", 0.58, R("Single measure with colour breakdown")

    # 14. Mark-based fallback / unknown
    if mark and mark != "automatic":
        return f"Likely {ws.mark_class} Chart", 0.4, R(f"Based on mark class '{ws.mark_class}' only")
    return "Likely Text Table", 0.35, R("Insufficient encoding/shelf metadata to classify confidently")
