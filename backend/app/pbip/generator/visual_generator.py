"""Generate report pages with a Table (tableEx) visual from worksheets.

Mirrors the reference `visual.json` (schema visualContainer/2.9.0): each placed
field becomes a projection - a `Column` (dimension) or `Measure` (calc) with
`SourceRef.Entity` + `Property`.
"""
from __future__ import annotations

from ..model.ir import ProjectionField, Worksheet

_S = "https://developer.microsoft.com/json-schemas/fabric"

# Tableau derivation -> (Power BI QueryAggregateFunction code, display name).
# Sum=0 is verified against the reference; the others are best-effort.
_AGG = {
    "Sum": (0, "Sum"),
    "Avg": (1, "Average"),
    "Average": (1, "Average"),
    "Min": (3, "Min"),
    "Max": (4, "Max"),
    "Count": (5, "Count"),
    "CountD": (2, "Distinct count"),
}


def _projection(field: ProjectionField) -> dict:
    column_expr = {
        "Expression": {"SourceRef": {"Entity": field.table}},
        "Property": field.property,
    }
    if field.kind == "aggregation":
        func, label = _AGG.get(field.agg or "Sum", (0, "Sum"))
        return {
            "field": {"Aggregation": {"Expression": {"Column": column_expr}, "Function": func}},
            "queryRef": f"{label}({field.table}.{field.property})",
            "nativeQueryRef": f"{label} of {field.property}",
        }
    key = "Measure" if field.kind == "measure" else "Column"
    return {
        "field": {key: column_expr},
        "queryRef": f"{field.table}.{field.property}",
        "nativeQueryRef": field.property,
    }


def build_visual(worksheet: Worksheet, visual_id: str) -> dict:
    return {
        "$schema": f"{_S}/item/report/definition/visualContainer/2.9.0/schema.json",
        "name": visual_id,
        "position": {"x": 16, "y": 16, "z": 0, "height": 688, "width": 1248, "tabOrder": 0},
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {
                    "Values": {"projections": [_projection(f) for f in worksheet.fields]}
                }
            },
            "objects": {
                "total": [
                    {"properties": {"totals": {"expr": {"Literal": {"Value": "false"}}}}}
                ]
            },
            "drillFilterOtherVisuals": True,
        },
    }


def build_page(worksheet: Worksheet, page_id: str, binding_id: str) -> dict:
    return {
        "$schema": f"{_S}/item/report/definition/page/2.1.0/schema.json",
        "name": page_id,
        "displayName": worksheet.name,
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
        "pageBinding": {
            "name": binding_id,
            "type": "Default",
            "parameters": [],
            "acceptsFilterContext": "None",
        },
    }
