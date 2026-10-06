"""Extract physical joins and logical relationships from a datasource.

Physical joins live in the relation tree: each ``<relation type='join'>`` carries
its own ``<clause>/<expression op='='>`` naming the two joined tables and keys.
Logical relationships (newer model) live in ``<relationships>/<relationship>``
and may declare cardinality.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element
from typing import Optional

from ..model.metadata import JoinCondition, RelationshipMeta
from .common import parse_ref


def _operand_ref(op_str: str, field_lookup: dict[str, str]) -> tuple[str, str]:
    """Resolve a join operand to (table, column).

    Physical joins use ``[Table].[Col]``; logical relationships may use a bare
    ``[field]`` that resolves via the field->table lookup.
    """
    table, col = parse_ref(op_str)
    if not table and col in field_lookup:
        return field_lookup[col], col
    return table, col


def _conditions_from_clause(clause: Element, field_lookup: dict[str, str]) -> tuple[list[JoinCondition], str, str]:
    conditions: list[JoinCondition] = []
    left_table = right_table = ""
    for expr in clause.findall("expression"):
        op = expr.get("op", "=")
        operands = expr.findall("expression")
        if len(operands) != 2:
            continue
        lt, lc = _operand_ref(operands[0].get("op", ""), field_lookup)
        rt, rc = _operand_ref(operands[1].get("op", ""), field_lookup)
        left_table = left_table or lt
        right_table = right_table or rt
        conditions.append(
            JoinCondition(left=f"{lt}.{lc}" if lt else lc, op=op, right=f"{rt}.{rc}" if rt else rc)
        )
    return conditions, left_table, right_table


def _signature(rel: RelationshipMeta) -> tuple:
    return (
        rel.kind,
        rel.join_type,
        rel.left_table,
        rel.right_table,
        tuple((c.left, c.op, c.right) for c in rel.conditions),
    )


def extract_joins(datasource: Element, field_lookup: Optional[dict[str, str]] = None) -> list[RelationshipMeta]:
    field_lookup = field_lookup or {}
    joins: list[RelationshipMeta] = []
    seen: set[tuple] = set()
    # Tableau stores the relation tree more than once (physical model + a legacy
    # object-model copy), so the same join appears repeatedly; dedupe by signature.
    for rel in datasource.iter("relation"):
        if rel.get("type") != "join":
            continue
        join_type = (rel.get("join") or "inner").lower()
        for clause in rel.findall("clause"):
            conditions, left, right = _conditions_from_clause(clause, field_lookup)
            if not conditions:
                continue
            meta = RelationshipMeta(
                kind="join",
                left_table=left,
                right_table=right,
                join_type=join_type,
                cardinality=None,
                conditions=conditions,
            )
            sig = _signature(meta)
            if sig in seen:
                continue
            seen.add(sig)
            joins.append(meta)
    return joins


def extract_logical_relationships(
    datasource: Element, field_lookup: Optional[dict[str, str]] = None
) -> list[RelationshipMeta]:
    field_lookup = field_lookup or {}
    rels: list[RelationshipMeta] = []
    seen: set[tuple] = set()
    for rel in datasource.findall(".//relationships/relationship"):
        cardinality = _cardinality(rel)
        conditions: list[JoinCondition] = []
        left_table = right_table = ""
        for expr in rel.findall("./expression[@op='=']"):
            operands = expr.findall("expression")
            if len(operands) != 2:
                continue
            lt, lc = _operand_ref(operands[0].get("op", ""), field_lookup)
            rt, rc = _operand_ref(operands[1].get("op", ""), field_lookup)
            left_table = left_table or lt
            right_table = right_table or rt
            conditions.append(
                JoinCondition(left=f"{lt}.{lc}" if lt else lc, op="=", right=f"{rt}.{rc}" if rt else rc)
            )
        if conditions:
            meta = RelationshipMeta(
                kind="relationship",
                left_table=left_table,
                right_table=right_table,
                join_type=None,
                cardinality=cardinality,
                conditions=conditions,
            )
            sig = _signature(meta)
            if sig in seen:
                continue
            seen.add(sig)
            rels.append(meta)
    return rels


def _cardinality(rel: Element) -> Optional[str]:
    """Read declared cardinality if present (Tableau stores it on the relationship)."""
    first = rel.get("first-end-point-cardinality") or rel.get("expected-first-cardinality")
    second = rel.get("second-end-point-cardinality") or rel.get("expected-second-cardinality")
    if first and second:
        return f"{first}-to-{second}"
    return None
