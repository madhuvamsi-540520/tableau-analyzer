"""Extract data-source-level filters.

Tableau stores filter shapes differently by class (categorical / quantitative /
relative-date / condition). This is a pragmatic, best-effort classifier that
covers the common cases (include/exclude member lists, numeric ranges, wildcard
pattern-match, and formula/condition) and always records a readable expression.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import FilterMeta
from .common import last_name


def _ns_attr(el: Element, localname: str) -> str | None:
    """Read an attribute by local name, ignoring XML namespace prefixes."""
    for k, v in el.attrib.items():
        if k.split("}")[-1] == localname:
            return v
    return None


def _members(filter_el: Element) -> list[str]:
    values: list[str] = []
    for gf in filter_el.iter("groupfilter"):
        if gf.get("function") == "member":
            m = gf.get("member")
            if m:
                values.append(m.strip().strip('"'))
    return values


def _text(el: Element, tag: str) -> str | None:
    child = el.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _classify(f: Element, fclass: str) -> tuple[str, list[str]]:
    # Formula / condition filters.
    if f.find(".//formula") is not None or fclass == "condition":
        formula = _text(f, ".//formula") or ""
        return "formula", [formula] if formula else []

    if fclass == "quantitative":
        lo, hi = _text(f, "min"), _text(f, "max")
        if lo is not None or hi is not None:
            return "range", [f"min={lo or '*'}", f"max={hi or '*'}"]
        return (f.get("included-values") or "range"), []

    if fclass == "relative-date":
        return "relative-date", []

    if fclass == "categorical":
        # Wildcard / pattern-match?
        for gf in f.iter("groupfilter"):
            if gf.get("function") == "filter" and (_ns_attr(gf, "ui-marker") == "pattern-match"):
                return "wildcard", [gf.get("member", "").strip().strip('"')]
        values = _members(f)
        # Inclusive vs exclusive from the enumeration marker / outer function.
        enum = None
        outer = f.find("groupfilter")
        if outer is not None:
            enum = _ns_attr(outer, "ui-enumeration") or outer.get("function")
        if enum in ("exclusive", "except"):
            return "exclude", values
        return "include", values

    return fclass or "unknown", _members(f)


def _expression(field: str, ftype: str, values: list[str]) -> str:
    if ftype == "range":
        return f"[{field}] in range ({', '.join(values)})"
    if ftype == "include":
        return f"[{field}] IN ({', '.join(values)})" if values else f"[{field}] (include)"
    if ftype == "exclude":
        return f"[{field}] NOT IN ({', '.join(values)})" if values else f"[{field}] (exclude)"
    if ftype == "wildcard":
        return f"[{field}] matches '{values[0] if values else ''}'"
    if ftype == "formula":
        return values[0] if values else f"[{field}] (formula)"
    if ftype == "relative-date":
        return f"[{field}] (relative date)"
    return f"[{field}] ({ftype})"


def extract_filters(datasource: Element) -> list[FilterMeta]:
    filters: list[FilterMeta] = []
    for f in datasource.findall("filter"):
        field = last_name(f.get("column", "")) or "(unknown)"
        fclass = f.get("class", "") or "unknown"
        ftype, values = _classify(f, fclass)
        filters.append(
            FilterMeta(
                field=field,
                filter_type=ftype,
                filter_class=fclass,
                values=values,
                expression=_expression(field, ftype, values),
            )
        )
    return filters
