"""Extract UNION relations (manual or wildcard) from a datasource."""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import UnionMeta
from .common import strip_brackets


def extract_unions(datasource: Element) -> list[UnionMeta]:
    unions: list[UnionMeta] = []
    for rel in datasource.iter("relation"):
        if rel.get("type") != "union":
            continue
        # Child table relations are the tables being combined.
        tables = [
            child.get("name") or strip_brackets(child.get("table", ""))
            for child in rel.findall("relation")
            if child.get("type") in ("table", "text")
        ]
        # Wildcard unions carry an expansion hint; otherwise it is a manual union.
        expansion = (rel.get("expansion") or "").lower()
        union_type = "wildcard" if expansion and expansion != "none" else "manual"
        unions.append(
            UnionMeta(
                name=rel.get("name") or "Union",
                union_type=union_type,
                tables=[t for t in tables if t],
                conditions=[],
            )
        )
    return unions
