"""Canonical intermediate representation (IR) for a migrated workbook.

The parser produces this structured model from the Tableau XML; the generators
consume it to emit the PBIP.  Keeping a clean IR in the middle is what lets the
pipeline stay ``TWB -> parser -> IR -> generators -> PBIP``.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Optional

from ..generator.formatting import new_guid

# ---------------------------------------------------------------------------
# Type mapping tables
# ---------------------------------------------------------------------------

# Tableau logical datatype -> Power BI (TMDL) dataType
TABLEAU_TO_PBI_TYPE = {
    "integer": "int64",
    "real": "double",
    "string": "string",
    "boolean": "boolean",
    "date": "dateTime",
    "datetime": "dateTime",
}

# Power BI dataType -> Power Query M type expression used in Table.TransformColumnTypes
PBI_TO_M_TYPE = {
    "int64": "Int64.Type",
    "double": "type number",
    "string": "type text",
    "boolean": "type logical",
    "dateTime": "type datetime",
}


def pbi_type(tableau_type: str) -> str:
    return TABLEAU_TO_PBI_TYPE.get((tableau_type or "").lower(), "string")


def m_type(pbi_data_type: str) -> str:
    return PBI_TO_M_TYPE.get(pbi_data_type, "type any")


def _looks_like_identifier(name: str) -> bool:
    low = name.lower().replace(" ", "")
    return low == "id" or low.endswith("id") or low.endswith("key") or low.endswith("code")


def summarize_by_for(name: str, pbi_data_type: str, in_relationship: bool) -> str:
    """Reproduce Power BI Desktop's default summarizeBy choice.

    Verified against the reference: relationship key columns and any
    non-numeric column -> ``none``; identifier-like numerics (``Id``) ->
    ``count``; other numerics (``Cost``) -> ``sum``.
    """
    if in_relationship:
        return "none"
    if pbi_data_type not in ("int64", "double"):
        return "none"
    if _looks_like_identifier(name):
        return "count"
    return "sum"


# ---------------------------------------------------------------------------
# IR dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Column:
    name: str                       # column name in the model (== source column here)
    data_type: str                  # PBI dataType (int64/string/double/boolean/dateTime)
    source_column: str              # raw source column name (unquoted in TMDL)
    tableau_type: str = "string"    # original Tableau datatype (for reference/debug)
    summarize_by: str = "none"
    format_string: Optional[str] = None
    lineage_tag: str = field(default_factory=new_guid)


@dataclass
class Table:
    name: str                       # model table name (e.g. "Orders")
    source_name: str                # physical sheet/table (e.g. "Orders" sheet, "dbo.Orders")
    columns: list[Column] = field(default_factory=list)
    connection_ref: Optional[str] = None   # named-connection id this table reads from
    kind: str = "db-table"          # "excel-sheet" | "db-table" | "custom-sql"
    custom_sql: Optional[str] = None
    lineage_tag: str = field(default_factory=new_guid)
    # When set, the partition embeds this data inline (snapshot) instead of
    # sourcing from the original file/DB. Rows align to inline_columns order.
    inline_columns: Optional[list[str]] = None
    inline_rows: Optional[list[list]] = None
    # Where the inline rows came from: "bundled" (real data) | "sample" | None
    data_origin: Optional[str] = None


@dataclass
class Connection:
    name: str                       # named-connection id
    cls: str = ""                   # excel-direct / sqlserver / postgres / mysql / odbc ...
    filename: Optional[str] = None
    server: Optional[str] = None
    port: Optional[str] = None
    database: Optional[str] = None
    schema: Optional[str] = None
    caption: Optional[str] = None


@dataclass
class Relationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    from_cardinality: str = "many"          # many-to-one by default
    cross_filter: str = "singleDirection"
    name: str = field(default_factory=lambda: "Relationship_" + new_guid())


@dataclass
class CalculatedField:
    name: str                       # user-facing caption (e.g. "Number of Returns")
    formula: str                    # Tableau formula, with [Calculation_x] refs resolved to captions
    data_type: str = "string"
    role: str = "measure"
    table: Optional[str] = None     # model table the measure is attached to (the fact table)
    format_string: Optional[str] = None
    # Filled in by the translators (or left as a placeholder comment).
    dax: Optional[str] = None
    translated: bool = False
    method: Optional[str] = None      # how dax was produced: "rule" | "llm" | "manual"
    needs_review: bool = False        # DAX present but cross-table/join-affected -> verify


@dataclass
class ProjectionField:
    """One field placed on a worksheet, to become a column in a Table visual."""
    kind: str            # "column" | "measure" | "aggregation"
    table: str           # source entity (table) name
    property: str        # field / measure name shown in the visual
    agg: Optional[str] = None   # Tableau derivation for kind=="aggregation" (Sum/Avg/...)


@dataclass
class Worksheet:
    name: str
    fields: list[ProjectionField] = field(default_factory=list)


@dataclass
class ReportPage:
    """A composed Power BI page for one Tableau Dashboard: its member
    worksheets, each rendered as its own visual stacked on the same page."""
    name: str
    worksheets: list[Worksheet] = field(default_factory=list)


@dataclass
class Model:
    name: str                                # PBIP project name (from .twb filename)
    tables: list[Table] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    connections: dict[str, Connection] = field(default_factory=dict)
    calculated_fields: list[CalculatedField] = field(default_factory=list)
    worksheets: list[Worksheet] = field(default_factory=list)
    dashboards: list[ReportPage] = field(default_factory=list)
    source_caption: Optional[str] = None     # Tableau datasource caption (informational)
    has_hyper_extract: bool = False          # data lives in a .hyper/.tde extract (not readable offline)
    warnings: list[str] = field(default_factory=list)
    # field name -> (table, source column); used to resolve refs in calc formulas
    field_lookup: dict[str, tuple[str, str]] = field(default_factory=dict)
    # tables joined via an INNER join in Tableau (the join filters the dataset,
    # so aggregations over their columns are join-affected and need review)
    inner_join_tables: set[str] = field(default_factory=set)

    def fact_table(self) -> Optional["Table"]:
        """The table measures attach to: the one with the most columns."""
        return max(self.tables, key=lambda t: len(t.columns), default=None)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the IR to a plain dict (downloadable debug artifact)."""
        return dataclasses.asdict(self)
