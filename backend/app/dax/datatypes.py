"""Data Type Analyzer (best-effort).

Infers the likely output type of a Tableau calculation and surfaces conversions.
Deliberately conservative: when the type cannot be determined it is reported as
``unknown`` with a note, never guessed. Signals come from the functions used and
the data types of the referenced physical columns.
"""
from __future__ import annotations

import re

# Function-name families -> output type.
_COUNT = re.compile(r"\b(COUNT|COUNTD)\s*\(", re.I)
_NUM_AGG = re.compile(r"\b(SUM|AVG|MIN|MAX|MEDIAN|STDEV|VAR|PERCENTILE)\s*\(", re.I)
_STRING_FN = re.compile(r"\b(LEFT|RIGHT|MID|SPLIT|TRIM|LTRIM|RTRIM|UPPER|LOWER|REPLACE|SUBSTITUTE|STR)\s*\(", re.I)
_DATE_FN = re.compile(r"\b(DATE|DATETIME|DATEADD|DATETRUNC|MAKEDATE|TODAY|NOW|DATEPARSE)\s*\(", re.I)
_BOOL_FN = re.compile(r"\b(ISNULL|CONTAINS|STARTSWITH|ENDSWITH|ISDATE)\s*\(", re.I)
_LOGIC = re.compile(r"\b(IF|IIF|CASE|WHEN)\b", re.I)
_COMPARISON = re.compile(r"(==|!=|<=|>=|<|>| = )")
_BOOL_OP = re.compile(r"\b(AND|OR|NOT)\b", re.I)
# Explicit casts.
_CASTS = {
    "INT": "integer", "FLOAT": "real", "STR": "string",
    "DATE": "date", "DATETIME": "datetime", "BOOL": "boolean",
}
_CAST_RE = re.compile(r"\b(INT|FLOAT|STR|DATE|DATETIME|BOOL)\s*\(", re.I)
_FIELD_REF = re.compile(r"\[([^\]]+)\]")


def infer(*, formula: str, categories: list[str], field_types: dict[str, str]) -> dict:
    """`field_types` maps referenced field name -> its tableau data type."""
    f = formula or ""

    inputs = sorted({t for t in field_types.values() if t})

    # Output type — most specific signal wins.
    if _COUNT.search(f):
        output = "integer"
    elif _NUM_AGG.search(f):
        output = "real"
    elif _DATE_FN.search(f):
        output = "date/datetime"
    elif _STRING_FN.search(f):
        output = "string"
    elif _BOOL_FN.search(f) or (_COMPARISON.search(f) and not _LOGIC.search(f)) or _BOOL_OP.search(f):
        output = "boolean"
    elif _LOGIC.search(f):
        # IF/CASE returns the type of its branches — approximate from inputs.
        output = inputs[0] if len(inputs) == 1 else "varies (branch-dependent)"
    elif re.search(r"[-+*/]", f) and inputs and all(t in ("integer", "real") for t in inputs):
        output = "real"
    else:
        output = inputs[0] if len(inputs) == 1 else "unknown"

    explicit = sorted({_CASTS[m.upper()] for m in _CAST_RE.findall(f)})

    # Implicit conversion risk: mixing string with numeric/date operands.
    issues: list[str] = []
    has_string = "string" in inputs
    has_numeric = any(t in ("integer", "real") for t in inputs)
    has_date = any(t in ("date", "datetime") for t in inputs)
    if has_string and (has_numeric or has_date) and not explicit:
        issues.append("Mixes string with numeric/date operands — verify implicit conversions in DAX (types are stricter).")
    if output in ("unknown", "varies (branch-dependent)"):
        issues.append("Output type could not be determined with confidence — confirm the intended result type.")
    if _DATE_FN.search(f):
        issues.append("Date handling — Tableau and DAX differ on date parsing/locale; validate DATEPARSE/DATE equivalents.")

    return {
        "inputs": inputs,
        "output": output,
        "explicitConversions": explicit,
        "issues": issues,
        "confident": output not in ("unknown", "varies (branch-dependent)"),
    }
