"""Dependency Analyzer — extract field references and build the calc dependency graph.

Everything here is dynamic: references are discovered from the formula text
(``[field]`` tokens), never from a hardcoded list. Two context builders are
provided so the same conversion logic serves both the parse-time engine (which
holds the ``WorkbookMetadata`` dataclass) and the on-demand endpoint (which holds
the already-serialized API dict).
"""
from __future__ import annotations

import re

_FIELD_REF = re.compile(r"\[([^\]]+)\]")


def extract_refs(formula: str) -> list[str]:
    """Distinct ``[field]`` references, in first-seen order."""
    seen: list[str] = []
    for name in _FIELD_REF.findall(formula or ""):
        if name not in seen:
            seen.append(name)
    return seen


# --------------------------------------------------------------------------- #
# Context builders  ->  {field_lookup, measures, tables, param_names}
# --------------------------------------------------------------------------- #
def context_from_wb(wb) -> dict:
    field_lookup: dict[str, tuple[str, str]] = {}
    tables: list[tuple[str, list[str]]] = []
    for ds in wb.data_sources:
        for t in ds.tables:
            cols = [c.name for c in t.columns]
            tables.append((t.name, cols))
            for c in t.columns:
                field_lookup.setdefault(c.name, (t.name, c.original_name or c.name))
    measures = {c.name for ds in wb.data_sources for c in ds.calculations}
    param_names = {p.name for p in wb.parameters}
    return {"field_lookup": field_lookup, "measures": measures,
            "tables": tables, "param_names": param_names}


def context_from_api(metadata: dict) -> dict:
    field_lookup: dict[str, tuple[str, str]] = {}
    tables: list[tuple[str, list[str]]] = []
    measures: set[str] = set()
    for ds in metadata.get("dataSources", []):
        for t in ds.get("tables", []):
            cols = [c.get("name") for c in t.get("columns", []) if c.get("name")]
            tables.append((t.get("name"), cols))
            for c in t.get("columns", []):
                nm = c.get("name")
                if nm and nm not in field_lookup:
                    field_lookup[nm] = (t.get("name"), c.get("originalName") or nm)
        for calc in ds.get("calculations", []):
            measures.add(calc.get("name"))
    param_names = {p.get("name") for p in metadata.get("parameters", [])}
    return {"field_lookup": field_lookup, "measures": measures,
            "tables": tables, "param_names": param_names}


# --------------------------------------------------------------------------- #
# Dependency graph over calculated fields
# --------------------------------------------------------------------------- #
def build_dependency_index(calc_formulas: dict[str, str], param_names: set[str]) -> dict:
    """Given {calc_name: formula}, return per-calc {parents, children, depth}.

    * parents  = other calcs this calc references directly
    * children = other calcs that reference this calc (reverse edges)
    * depth    = longest parent chain (cycle-safe)
    """
    names = set(calc_formulas)
    parents: dict[str, list[str]] = {}
    for name, formula in calc_formulas.items():
        refs = extract_refs(formula)
        parents[name] = [r for r in refs if r in names and r != name]

    children: dict[str, list[str]] = {n: [] for n in names}
    for name, ps in parents.items():
        for p in ps:
            children[p].append(name)

    depth_cache: dict[str, int] = {}

    def depth(name: str, stack: frozenset) -> int:
        if name in depth_cache:
            return depth_cache[name]
        if name in stack:               # cycle guard
            return 0
        ps = parents.get(name, [])
        d = 0 if not ps else 1 + max(depth(p, stack | {name}) for p in ps)
        depth_cache[name] = d
        return d

    return {
        n: {"parents": parents[n], "children": sorted(children[n]), "depth": depth(n, frozenset())}
        for n in names
    }
