"""Extract table and column inventory from a datasource.

Physical columns come from ``<metadata-record class='column'>`` (richest:
remote/original name, type, default aggregation, nullability) with a fallback to
the relation's ``<columns>`` block. Each column is then overlaid with the
logical field definition (``<column>`` at datasource level) to pick up the
role (dimension/measure), user rename (caption), type category and hidden flag.
"""
from __future__ import annotations

from dataclasses import dataclass
from xml.etree.ElementTree import Element
from typing import Optional

from ..model.metadata import ColumnMeta, TableMeta
from .common import last_name, parse_ref, strip_brackets


# --------------------------------------------------------------------------- #
# Logical field definitions (datasource-level <column>)
# --------------------------------------------------------------------------- #
@dataclass
class _LogicalField:
    caption: Optional[str]
    role: Optional[str]
    type_category: Optional[str]
    data_type: Optional[str]
    aggregation: Optional[str]
    hidden: bool
    is_calc: bool


def _logical_fields(datasource: Element) -> dict[str, _LogicalField]:
    """Map field name (e.g. ``P.ID (Sales)``) -> its logical definition."""
    fields: dict[str, _LogicalField] = {}
    for col in datasource.findall("column"):
        raw_name = col.get("name", "")
        if not raw_name:
            continue
        # Skip internal object-id placeholder columns (datatype='table').
        if (col.get("datatype") == "table") or "__tableau_internal_object_id__" in raw_name:
            continue
        name = last_name(raw_name)
        fields[name] = _LogicalField(
            caption=col.get("caption"),
            role=col.get("role"),
            type_category=col.get("type"),
            data_type=col.get("datatype"),
            aggregation=col.get("aggregation"),
            hidden=(col.get("hidden") == "true"),
            is_calc=col.find("calculation") is not None,
        )
    return fields


def _reverse_cols(datasource: Element) -> dict[tuple[str, str], str]:
    """Map (table, source column) -> logical field name, from the ``<cols>`` map."""
    rev: dict[tuple[str, str], str] = {}
    cols = datasource.find(".//cols")
    if cols is None:
        return rev
    for m in cols.findall("map"):
        field = last_name(m.get("key", ""))
        table, col = parse_ref(m.get("value", ""))
        if table and col:
            rev[(table, col)] = field
    return rev


# --------------------------------------------------------------------------- #
# Physical columns from metadata-records
# --------------------------------------------------------------------------- #
@dataclass
class _PhysCol:
    original_name: str
    field_name: str
    data_type: str
    aggregation: Optional[str]
    nullable: Optional[bool]
    ordinal: Optional[int]


def _metadata_columns(datasource: Element) -> dict[str, list[_PhysCol]]:
    """Map table name -> physical columns, from ``<metadata-record class='column'>``."""
    by_table: dict[str, list[_PhysCol]] = {}
    for rec in datasource.iter("metadata-record"):
        if rec.get("class") != "column":
            continue
        table = strip_brackets(_text(rec, "parent-name"))
        remote = _text(rec, "remote-name") or last_name(_text(rec, "local-name"))
        if not table or not remote:
            continue
        contains_null = _text(rec, "contains-null")
        ordinal = _text(rec, "ordinal")
        by_table.setdefault(table, []).append(
            _PhysCol(
                original_name=remote,
                field_name=last_name(_text(rec, "local-name")) or remote,
                data_type=_text(rec, "local-type") or "string",
                aggregation=_text(rec, "aggregation") or None,
                nullable=(contains_null == "true") if contains_null else None,
                ordinal=int(ordinal) if (ordinal or "").lstrip("-").isdigit() else None,
            )
        )
    return by_table


def _text(el: Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
def _table_relations(datasource: Element) -> list[Element]:
    """All physical table / custom-SQL relations, de-duplicated by (name, table)."""
    seen: set[tuple[str, str]] = set()
    out: list[Element] = []
    for rel in datasource.iter("relation"):
        if rel.get("type") not in ("table", "text"):
            continue
        key = (rel.get("name", ""), rel.get("table", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(rel)
    return out


def _build_column(
    original_name: str,
    field_name: str,
    data_type: str,
    aggregation: Optional[str],
    nullable: Optional[bool],
    ordinal: Optional[int],
    table_name: str,
    logical: dict[str, _LogicalField],
    reverse: dict[tuple[str, str], str],
) -> ColumnMeta:
    # Resolve the logical field: prefer the cols-map (table, source col) link,
    # else fall back to matching the field name directly.
    fname = reverse.get((table_name, original_name)) or field_name
    lf = logical.get(fname) or logical.get(field_name)

    caption = lf.caption if lf else None
    resolved_type = lf.data_type if lf and lf.data_type else data_type
    # Use the explicit Tableau role when set; otherwise infer as Tableau does by
    # default (numeric fields with no explicit role are measures, else dimension).
    if lf and lf.role:
        role = lf.role
    elif resolved_type in ("integer", "real"):
        role = "measure"
    else:
        role = "dimension"
    return ColumnMeta(
        name=caption or fname or original_name,
        original_name=original_name,
        data_type=resolved_type,
        role=role,
        alias=caption,
        default_aggregation=(lf.aggregation if lf and lf.aggregation else aggregation),
        type_category=(lf.type_category if lf else None),
        hidden=(lf.hidden if lf else False),
        nullable=nullable,
        calculated=False,
        ordinal=ordinal,
    )


def _columns_from_relation(
    rel: Element,
    table_name: str,
    logical: dict[str, _LogicalField],
    reverse: dict[tuple[str, str], str],
) -> list[ColumnMeta]:
    """Fallback column source when no metadata-records exist for the table."""
    out: list[ColumnMeta] = []
    seen: set[str] = set()
    cols_el = rel.find("columns")
    raw = cols_el.findall("column") if cols_el is not None else []
    for c in sorted(raw, key=lambda e: int(e.get("ordinal", "0")) if e.get("ordinal", "0").lstrip("-").isdigit() else 0):
        name = c.get("name", "")
        if not name or name in seen:
            continue
        seen.add(name)
        ordinal = c.get("ordinal")
        out.append(
            _build_column(
                original_name=name,
                field_name=name,
                data_type=c.get("datatype", "string"),
                aggregation=None,
                nullable=None,
                ordinal=int(ordinal) if (ordinal or "").isdigit() else None,
                table_name=table_name,
                logical=logical,
                reverse=reverse,
            )
        )
    return out


def _schema_database(rel: Element, conn_lookup: dict) -> tuple[Optional[str], Optional[str]]:
    physical = strip_brackets(rel.get("table", ""))
    schema = None
    if "." in physical and not physical.endswith("$"):
        schema = physical.split(".", 1)[0]
    conn = conn_lookup.get(rel.get("connection"))
    if conn is None and len(conn_lookup) == 1:
        # A relation may omit its connection ref; if the datasource has a single
        # connection, it is unambiguously the source.
        conn = next(iter(conn_lookup.values()))
    if schema is None and conn is not None:
        schema = conn.schema
    database = conn.database if conn is not None else None
    return schema, database


def extract_tables(
    datasource: Element,
    conn_lookup: dict,
    row_counts: Optional[dict[str, int]] = None,
) -> list[TableMeta]:
    logical = _logical_fields(datasource)
    reverse = _reverse_cols(datasource)
    meta_cols = _metadata_columns(datasource)
    row_counts = row_counts or {}

    tables: list[TableMeta] = []
    for rel in _table_relations(datasource):
        name = rel.get("name", "Table")
        physical = strip_brackets(rel.get("table", name))
        is_sheet = physical.endswith("$")
        is_customsql = rel.get("type") == "text"

        if name in meta_cols and meta_cols[name]:
            columns = [
                _build_column(
                    pc.original_name, pc.field_name, pc.data_type, pc.aggregation,
                    pc.nullable, pc.ordinal, name, logical, reverse,
                )
                for pc in sorted(meta_cols[name], key=lambda p: (p.ordinal is None, p.ordinal or 0))
            ]
        else:
            columns = _columns_from_relation(rel, name, logical, reverse)

        schema, database = _schema_database(rel, conn_lookup)
        source_base = physical.rstrip("$").split(".")[-1] if physical else name
        tables.append(
            TableMeta(
                name=name,
                kind="custom-sql" if is_customsql else ("table" if not is_sheet else "table"),
                caption=name,
                schema=None if is_sheet else schema,
                database=None if is_sheet else database,
                alias=name if name != source_base else None,
                connection_name=rel.get("connection"),
                row_count=row_counts.get(name.lower()) or row_counts.get(source_base.lower()),
                is_extract=_is_extract_table(name, physical, rel, conn_lookup),
                columns=columns,
            )
        )
    return tables


def _is_extract_table(name: str, physical: str, rel: Element, conn_lookup: dict) -> bool:
    """Extract storage artifacts are not real tables (excluded from diagrams/lineage).

    Detected by the pseudo-table name 'Extract', a .hyper/.tde source, or an
    extract-class connection backing the relation.
    """
    if (name or "").strip().lower() == "extract":
        return True
    if (physical or "").lower().endswith((".hyper", ".tde")):
        return True
    conn = conn_lookup.get(rel.get("connection"))
    if conn is None and len(conn_lookup) == 1:
        conn = next(iter(conn_lookup.values()))
    return bool(conn is not None and conn.is_extract)
