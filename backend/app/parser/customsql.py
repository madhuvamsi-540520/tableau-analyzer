"""Extract Custom SQL relations and analyze their SQL with sqlglot."""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import CustomSqlMeta
from ..sqlanalysis.analyzer import analyze_sql

# Map a Tableau connection class to a sqlglot dialect for more accurate parsing.
_DIALECTS = {
    "sqlserver": "tsql",
    "sqlserver-odbc": "tsql",
    "postgres": "postgres",
    "redshift": "redshift",
    "snowflake": "snowflake",
    "mysql": "mysql",
    "oracle": "oracle",
    "bigquery": "bigquery",
    "databricks": "databricks",
    "spark": "spark",
    "presto": "presto",
    "athena": "presto",
    "teradata": "teradata",
}


def extract_custom_sql(datasource: Element, conn_class_by_ref: dict[str, str]) -> list[CustomSqlMeta]:
    out: list[CustomSqlMeta] = []
    seen: set[str] = set()
    for rel in datasource.iter("relation"):
        if rel.get("type") != "text":
            continue
        name = rel.get("name") or "Custom SQL Query"
        sql = (rel.text or "").strip()
        key = f"{name}::{sql[:64]}"
        if not sql or key in seen:
            continue
        seen.add(key)
        dialect = _DIALECTS.get((conn_class_by_ref.get(rel.get("connection")) or "").lower())
        out.append(CustomSqlMeta(name=name, sql=sql, analysis=analyze_sql(sql, dialect)))
    return out
