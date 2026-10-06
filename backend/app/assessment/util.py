"""Shared, deterministic helpers for the assessment analyzers.

No live data is available, so every check derives from workbook *metadata*:
column names/types/roles/nullability, the join graph, and structural counts.
"""
from __future__ import annotations

import re
from collections import defaultdict

# ---- key / naming heuristics ---------------------------------------------- #

def is_key_name(name: str) -> bool:
    low = (name or "").lower().replace(" ", "").replace("_", "")
    return low == "id" or low.endswith("id") or low.endswith("key") or low.endswith("code")


def naming_style(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return "empty"
    if " " in n:
        return "spaced"
    if "_" in n:
        return "snake"
    if re.fullmatch(r"[A-Z0-9]+", n):
        return "upper"
    if re.fullmatch(r"[A-Z][a-zA-Z0-9]*", n) and any(c.isupper() for c in n[1:]):
        return "pascal"
    if re.fullmatch(r"[a-z][a-zA-Z0-9]*", n) and any(c.isupper() for c in n):
        return "camel"
    return "lower"


# ---- join graph ----------------------------------------------------------- #

def graph(tables, relationships):
    names = {t.name for t in tables}
    edges = [
        (r.left_table, r.right_table)
        for r in relationships
        if r.left_table in names and r.right_table in names and r.left_table != r.right_table
    ]
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    degree = {t.name: len(adj[t.name]) for t in tables}
    return names, edges, adj, degree


def find_cycles(tables, relationships) -> list[tuple[str, str]]:
    """Return the join edges that close a cycle (union-find)."""
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    _, edges, _, _ = graph(tables, relationships)
    closing: list[tuple[str, str]] = []
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            closing.append((a, b))
        else:
            parent[ra] = rb
    return closing


def isolated_tables(tables, relationships) -> list[str]:
    names, _, adj, _ = graph(tables, relationships)
    if len(names) <= 1:
        return []
    return [t.name for t in tables if not adj[t.name]]


# ---- PII detection (name-based, since no data values exist) --------------- #

_PII_PATTERNS: list[tuple[str, str]] = [
    (r"\bssn\b|social.?security", "SSN"),
    (r"e.?mail", "Email"),
    (r"phone|mobile|contact.?number", "Phone"),
    (r"birth|dob\b|date.?of.?birth", "Date of birth"),
    (r"\bage\b", "Age"),
    (r"gender|\bsex\b", "Gender"),
    (r"race|ethnic", "Race/Ethnicity"),
    (r"salary|income|compensation|wage", "Compensation"),
    (r"credit.?card|card.?number|\bcvv\b|\bpan\b", "Payment card"),
    (r"passport|driver.?licen|national.?id|\btax.?id\b|\bein\b", "Government ID"),
    (r"address|street|\bcity\b|\bzip\b|postal", "Address"),
    (r"latitude|longitude|geo.?location", "Geolocation"),
    (r"ip.?address", "IP address"),
    (r"account.?number|\biban\b|routing.?number", "Financial account"),
    (r"password|secret|api.?key|token", "Credential"),
    (r"patient|diagnos|medical|health|icd", "Health/PHI"),
    (r"first.?name|last.?name|full.?name|customer.?name|employee.?name", "Personal name"),
]
_PII_COMPILED = [(re.compile(p, re.I), label) for p, label in _PII_PATTERNS]


def pii_category(column_name: str) -> str | None:
    name = column_name or ""
    for rx, label in _PII_COMPILED:
        if rx.search(name):
            return label
    return None


def all_columns(workbook):
    for ds in workbook.data_sources:
        for t in ds.tables:
            for c in t.columns:
                yield ds, t, c


def split_ref(ref: str) -> tuple[str, str]:
    """'Orders.Order ID' -> ('Orders', 'Order ID')."""
    if "." in (ref or ""):
        a, b = ref.split(".", 1)
        return a, b
    return "", ref or ""


def find_column(ds, table_name: str, col_name: str):
    """Locate a column in a data source by table + (source or display) name."""
    low = (col_name or "").lower()
    for t in ds.tables:
        if t.name != table_name:
            continue
        for c in t.columns:
            if low in (c.original_name.lower(), c.name.lower()):
                return c
    return None
