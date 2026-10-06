"""Classify a Tableau calculation formula (deterministic, regex-based).

Produces the category tags, LOD/table-calc flags, and a Power BI migration
disposition (Direct / Rewrite / Manual / Unsupported) with a complexity band.
Used by the calc inventory, worksheet drill-down, and migration estimator.
"""
from __future__ import annotations

import re

_LOD = re.compile(r"\{\s*(FIXED|INCLUDE|EXCLUDE)\b", re.I)
_TABLE_CALC = re.compile(
    r"\b(WINDOW_\w+|RUNNING_\w+|INDEX|RANK(_\w+)?|LOOKUP|TOTAL|FIRST|LAST|SIZE|PREVIOUS_VALUE)\s*\(",
    re.I,
)
_RAW = re.compile(r"\b(RAWSQL\w*|SCRIPT_(STR|REAL|BOOL|INT))\s*\(", re.I)
_AGG = re.compile(r"\b(SUM|AVG|COUNT|COUNTD|MIN|MAX|MEDIAN|ATTR|STDEV|VAR|PERCENTILE)\s*\(", re.I)
_LOGIC = re.compile(r"\b(IF|IIF|CASE|WHEN|ELSEIF|THEN)\b", re.I)
_DATE = re.compile(r"\b(DATEPART|DATEADD|DATEDIFF|DATETRUNC|DATENAME|MAKEDATE|TODAY|NOW|YEAR|MONTH|DAY|DATEPARSE)\s*\(", re.I)
_STRING = re.compile(r"\b(LEFT|RIGHT|MID|CONTAINS|STARTSWITH|ENDSWITH|SPLIT|REGEXP_\w+|TRIM|LTRIM|RTRIM|UPPER|LOWER|REPLACE|FIND|LEN|SUBSTITUTE)\s*\(", re.I)


def classify_formula(formula: str) -> dict:
    f = formula or ""
    categories: list[str] = []

    lod_match = _LOD.search(f)
    lod = lod_match.group(1).upper() if lod_match else None
    table_calc = bool(_TABLE_CALC.search(f))
    raw = bool(_RAW.search(f))
    nested = f.count("{") > 1 or (lod and f.count("{") > 1)

    if lod:
        categories.append(f"LOD ({lod})")
    if table_calc:
        categories.append("Table Calculation")
    if raw:
        categories.append("RAWSQL / Script")
    if _AGG.search(f):
        categories.append("Aggregation")
    if _LOGIC.search(f):
        categories.append("Logic (IF/CASE)")
    if _DATE.search(f):
        categories.append("Date")
    if _STRING.search(f):
        categories.append("String")
    if not categories:
        categories.append("Basic / Arithmetic")

    # Power BI migration disposition (deterministic, most-severe wins).
    if raw:
        support, complexity = "Unsupported", "Very High"
        note = "RAWSQL / SCRIPT_* has no Power BI equivalent — rebuild logic natively or push to the source."
    elif table_calc:
        support, complexity = "Rewrite", "High"
        note = "Table calculations map to DAX window/RANKX/running-total patterns — manual rewrite and validation."
    elif lod:
        support, complexity = "Rewrite", "Medium"
        note = f"LOD {lod} maps to CALCULATE with the right filter context — review grain and relationships."
    elif nested:
        support, complexity = "Rewrite", "Medium"
        note = "Nested calculation — flatten and translate to DAX; verify evaluation order."
    else:
        support, complexity = "Direct", "Low"
        note = "Standard aggregation/logic/date/string — translates directly to a DAX measure/column."

    return {
        "categories": categories,
        "lod": lod,
        "tableCalc": table_calc,
        "nested": nested,
        "migrationComplexity": complexity,
        "powerBiSupport": support,
        "note": note,
    }
