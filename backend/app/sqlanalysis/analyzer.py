"""Custom-SQL introspection via sqlglot (a real SQL parser, not regex).

Extracts referenced tables/columns, aggregations, window functions, CTEs,
UNION / UNION ALL and subqueries. If sqlglot cannot parse the dialect, a
conservative regex fallback still reports the high-level features so the UI
never shows an empty analysis for valid-looking SQL.
"""
from __future__ import annotations

import re

_EMPTY = {
    "referencedTables": [],
    "referencedColumns": [],
    "aggregations": [],
    "windowFunctions": [],
    "ctes": [],
    "hasUnion": False,
    "hasUnionAll": False,
    "subqueryCount": 0,
    "parsed": False,
    "error": None,
}


def analyze_sql(sql: str, dialect: str | None = None) -> dict:
    sql = (sql or "").strip()
    if not sql:
        return dict(_EMPTY)

    try:
        import sqlglot
        from sqlglot import exp
    except ImportError:
        return {**_EMPTY, **_regex_fallback(sql), "error": "sqlglot not available"}

    try:
        tree = sqlglot.parse_one(sql, read=dialect) if dialect else sqlglot.parse_one(sql)
    except Exception as exc:  # unparseable dialect / syntax — fall back
        return {**_EMPTY, **_regex_fallback(sql), "error": f"{type(exc).__name__}: {exc}"}

    tables: list[str] = []
    for t in tree.find_all(exp.Table):
        name = ".".join(p for p in (t.catalog, t.db, t.name) if p)
        if name and name not in tables:
            tables.append(name)

    columns: list[str] = []
    for c in tree.find_all(exp.Column):
        name = f"{c.table}.{c.name}" if c.table else c.name
        if name and name not in columns:
            columns.append(name)

    aggregations: list[str] = []
    for a in tree.find_all(exp.AggFunc):
        n = type(a).__name__.upper()
        if n not in aggregations:
            aggregations.append(n)

    windows: list[str] = []
    for w in tree.find_all(exp.Window):
        fn = w.this
        if fn is None:
            windows.append("WINDOW")
        elif type(fn).__name__ == "Anonymous":
            windows.append((fn.name or "WINDOW").upper())  # e.g. RANK, LEAD, LAG
        else:
            windows.append(type(fn).__name__.upper())

    ctes = [c.alias_or_name for c in tree.find_all(exp.CTE)]

    unions = list(tree.find_all(exp.Union))
    has_union = bool(unions)
    # In sqlglot, distinct=False on a Union node means UNION ALL.
    has_union_all = any(u.args.get("distinct") is False for u in unions)

    subquery_count = len(list(tree.find_all(exp.Subquery)))

    return {
        "referencedTables": tables,
        "referencedColumns": columns,
        "aggregations": aggregations,
        "windowFunctions": windows,
        "ctes": ctes,
        "hasUnion": has_union,
        "hasUnionAll": has_union_all,
        "subqueryCount": subquery_count,
        "parsed": True,
        "error": None,
    }


def _regex_fallback(sql: str) -> dict:
    up = sql.upper()
    return {
        "referencedTables": _dedupe(
            re.findall(r"\bFROM\s+([A-Za-z_][\w.]*)", sql, re.I)
            + re.findall(r"\bJOIN\s+([A-Za-z_][\w.]*)", sql, re.I)
        ),
        "aggregations": _dedupe(
            m.upper() for m in re.findall(r"\b(SUM|COUNT|AVG|MIN|MAX|MEDIAN|STDDEV|VARIANCE)\s*\(", sql, re.I)
        ),
        "windowFunctions": ["WINDOW"] if re.search(r"\bOVER\s*\(", sql, re.I) else [],
        "ctes": _dedupe(re.findall(r"\bWITH\s+([A-Za-z_]\w*)\s+AS", sql, re.I)),
        "hasUnion": bool(re.search(r"\bUNION\b", up)),
        "hasUnionAll": bool(re.search(r"\bUNION\s+ALL\b", up)),
        "subqueryCount": len(re.findall(r"\(\s*SELECT\b", up)),
    }


def _dedupe(items) -> list[str]:
    out: list[str] = []
    for i in items:
        if i and i not in out:
            out.append(i)
    return out
