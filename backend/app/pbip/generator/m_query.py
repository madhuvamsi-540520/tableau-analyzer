"""Build the Power Query M expression for a table partition.

Emits fully-indented TMDL body lines (``let`` / ``in`` at 4 tabs, steps at
4 tabs + 4 spaces) so the caller can splice them straight under ``source =``.
Every query terminates with ``Table.TransformColumnTypes`` casting each column
to its declared dataType - the step whose omission caused the earlier
"DataModelLoadFailed" refresh errors.
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import Optional

from ..model.ir import Connection, Table, m_type
from .formatting import M_LET_INDENT, M_STEP_INDENT


def _m_literal(value, pbi_type: str) -> str:
    """Render a Python value as an M literal for an inline #table snapshot."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (_dt.datetime,)):
        return f"#datetime({value.year},{value.month},{value.day},{value.hour},{value.minute},{value.second})"
    if isinstance(value, _dt.date):
        return f"#datetime({value.year},{value.month},{value.day},0,0,0)"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "null"
        return repr(value)
    text = str(value)
    return '"' + text.replace('"', '""') + '"'


def build_inline_partition(table: Table) -> list[str]:
    """Embed the table's snapshot rows directly in the model (like 'Enter data')."""
    col_types = {c.source_column: c.data_type for c in table.columns}
    names = table.inline_columns or [c.source_column for c in table.columns]
    col_list = "{" + ", ".join(f'"{_m_escape(n)}"' for n in names) + "}"

    row_literals = []
    for row in table.inline_rows or []:
        cells = ", ".join(_m_literal(v, col_types.get(names[i], "string")) for i, v in enumerate(row))
        row_literals.append("{" + cells + "}")
    rows_m = "{" + ", ".join(row_literals) + "}"

    steps = [M_STEP_INDENT + f"Source = Table.FromRows({rows_m}, {col_list}),"]
    cast = _cast_step("Source", table)
    steps += cast
    return _wrap(steps, '#"Changed Type"' if cast else "Source")


def _win_path(path: str) -> str:
    """Tableau stores Excel paths with forward slashes; Power BI uses backslashes."""
    return (path or "").replace("/", "\\")


def _m_escape(text: str) -> str:
    return (text or "").replace('"', '""')


def _server_arg(conn: Connection, sep: str) -> str:
    """`server` or `server<sep>port` (SQL Server uses ',' , others ':')."""
    server = conn.server or ""
    if conn.port:
        return f"{server}{sep}{conn.port}"
    return server


def _transform_types(table: Table) -> str:
    if not table.columns:
        return ""
    parts = [f'{{"{_m_escape(c.source_column)}", {m_type(c.data_type)}}}' for c in table.columns]
    return "{" + ", ".join(parts) + "}"


def _cast_step(prev_step: str, table: Table) -> list[str]:
    types = _transform_types(table)
    if not types:
        return []
    return [
        M_STEP_INDENT
        + f'#"Changed Type" = Table.TransformColumnTypes({prev_step},{types})'
    ]


def _wrap(step_lines: list[str], return_step: str) -> list[str]:
    """Wrap step assignment lines in ``let ... in <return_step>``.

    ``step_lines`` must already carry a trailing comma on every line except the
    last; this joins/validates commas so the final step has none.
    """
    body: list[str] = [M_LET_INDENT + "let"]
    for i, line in enumerate(step_lines):
        is_last = i == len(step_lines) - 1
        stripped = line.rstrip(",")
        body.append(stripped + ("" if is_last else ","))
    body.append(M_LET_INDENT + "in")
    body.append(M_STEP_INDENT + return_step)
    return body


def build_partition_m(table: Table, conn: Optional[Connection]) -> list[str]:
    # Embedded snapshot wins over any external source.
    if table.inline_columns is not None:
        return build_inline_partition(table)

    cls = (conn.cls if conn else "") or ""

    if cls == "excel-direct" or (conn and conn.filename):
        return _build_excel(table, conn)
    if cls in ("sqlserver", "sqlserver-odbc"):
        return _build_sql_server(table, conn)
    if cls in ("postgres",):
        return _build_generic_db(table, conn, "PostgreSQL.Database", ":")
    if cls in ("mysql",):
        return _build_generic_db(table, conn, "MySQL.Database", ":")
    return _build_odbc(table, conn)


def _build_excel(table: Table, conn: Connection) -> list[str]:
    path = _win_path(conn.filename or "")
    sheet_var = f"{table.name}_Sheet"
    steps = [
        M_STEP_INDENT
        + f'Source = Excel.Workbook(File.Contents("{path}"), null, true),',
        M_STEP_INDENT
        + f'{sheet_var} = Source{{[Item="{_m_escape(table.source_name)}",Kind="Sheet"]}}[Data],',
        M_STEP_INDENT
        + f'#"Promoted Headers" = Table.PromoteHeaders({sheet_var}, [PromoteAllScalars=true]),',
    ]
    cast = _cast_step('#"Promoted Headers"', table)
    if cast:
        steps += cast
        return _wrap(steps, '#"Changed Type"')
    return _wrap(steps, '#"Promoted Headers"')


def _split_schema_item(table: Table, conn: Optional[Connection]) -> tuple[str, str]:
    if "." in table.source_name:
        schema, item = table.source_name.split(".", 1)
        return schema, item
    return (conn.schema if conn and conn.schema else "dbo"), table.source_name


def _build_sql_server(table: Table, conn: Connection) -> list[str]:
    server, database = _server_arg(conn, ","), conn.database or ""
    if table.kind == "custom-sql" and table.custom_sql:
        query = _m_escape(" ".join(table.custom_sql.split()))
        steps = [
            M_STEP_INDENT
            + f'Source = Sql.Database("{server}", "{database}", [Query="{query}"]),'
        ]
        cast = _cast_step("Source", table)
        steps += cast
        return _wrap(steps, '#"Changed Type"' if cast else "Source")

    schema, item = _split_schema_item(table, conn)
    nav_var = f"{schema}_{item}"
    steps = [
        M_STEP_INDENT + f'Source = Sql.Database("{server}", "{database}"),',
        M_STEP_INDENT
        + f'{nav_var} = Source{{[Schema="{schema}",Item="{item}"]}}[Data],',
    ]
    cast = _cast_step(nav_var, table)
    steps += cast
    return _wrap(steps, '#"Changed Type"' if cast else nav_var)


def _build_generic_db(
    table: Table, conn: Connection, connector: str, port_sep: str
) -> list[str]:
    server, database = _server_arg(conn, port_sep), conn.database or ""
    schema, item = _split_schema_item(table, conn)
    nav_var = f"{schema}_{item}"
    steps = [
        M_STEP_INDENT + f'Source = {connector}("{server}", "{database}"),',
        M_STEP_INDENT
        + f'{nav_var} = Source{{[Schema="{schema}",Item="{item}"]}}[Data],',
    ]
    cast = _cast_step(nav_var, table)
    steps += cast
    return _wrap(steps, '#"Changed Type"' if cast else nav_var)


def _build_odbc(table: Table, conn: Optional[Connection]) -> list[str]:
    dsn = (conn.server if conn else "") or ""
    query = f"SELECT * FROM {table.source_name}"
    steps = [
        M_STEP_INDENT
        + f'Source = Odbc.Query("dsn={dsn}", "{_m_escape(query)}"),'
    ]
    cast = _cast_step("Source", table)
    steps += cast
    return _wrap(steps, '#"Changed Type"' if cast else "Source")
