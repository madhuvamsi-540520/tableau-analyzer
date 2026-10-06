"""Generate the ``.SemanticModel/definition`` TMDL files from the IR."""
from __future__ import annotations

import json

from ..model.ir import CalculatedField, Model, Table
from . import m_query
from .formatting import TAB, new_guid, quote_tmdl_name, render_tmdl

CULTURE = "en-US"
# Machine-locale value; en-US is portable. The golden test normalizes this line.
SOURCE_QUERY_CULTURE = "en-US"


def generate_tmdl_files(model: Model) -> dict[str, str]:
    """Return {relative_path: file_text} for every TMDL file."""
    files: dict[str, str] = {
        "definition/model.tmdl": _model_tmdl(model),
        "definition/database.tmdl": _database_tmdl(),
        "definition/cultures/en-US.tmdl": render_tmdl(["cultureInfo " + CULTURE]),
    }
    for table in model.tables:
        files[f"definition/tables/{table.name}.tmdl"] = _table_tmdl(table, model)
    if model.relationships:
        files["definition/relationships.tmdl"] = _relationships_tmdl(model)
    return files


def _model_tmdl(model: Model) -> str:
    query_order = json.dumps([t.name for t in model.tables], separators=(",", ":"))
    lines = [
        "model Model",
        f"{TAB}culture: {CULTURE}",
        f"{TAB}defaultPowerBIDataSourceVersion: powerBI_V3",
        f"{TAB}sourceQueryCulture: {SOURCE_QUERY_CULTURE}",
        f"{TAB}dataAccessOptions",
        f"{TAB}{TAB}legacyRedirects",
        f"{TAB}{TAB}returnErrorValuesAsNull",
        "",
        # Auto date/time disabled: keeps the model clean and avoids generating
        # hidden LocalDateTables for every date column.
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        f"annotation PBI_QueryOrder = {query_order}",
        "",
        'annotation PBI_ProTooling = ["DevMode"]',
        "",
    ]
    lines += [f"ref table {quote_tmdl_name(t.name)}" for t in model.tables]
    lines += ["", f"ref cultureInfo {CULTURE}"]
    return render_tmdl(lines)


def _database_tmdl() -> str:
    return render_tmdl(["database", f"{TAB}compatibilityLevel: 1600"])


def _measure_tmdl(cf: CalculatedField) -> list[str]:
    """Render one measure block. Multi-line DAX uses a triple-backtick fence
    (body at 3 tabs); single-line DAX is inline."""
    name = quote_tmdl_name(cf.name)
    lines: list[str] = []
    if cf.translated and cf.dax:
        expr = cf.dax.strip()
        if cf.needs_review:
            # Literal translation of the Tableau logic, but the join makes it
            # need verification - highlight, don't silently trust.
            lines.append(f"{TAB}/// REVIEW - literal DAX translation of the Tableau formula below.")
            lines.append(f"{TAB}/// Verify relationship semantics: cross-table / inner-join calcs")
            lines.append(f"{TAB}/// usually need CALCULATE with a related-table filter (e.g. Returns[Returned] = \"Yes\").")
            lines.append(f"{TAB}/// Original Tableau formula: {cf.formula}")
    else:
        # Could not auto-translate at all - leave a scaffold to complete by hand.
        expr = "BLANK()"
        lines.append(f"{TAB}/// REVIEW REQUIRED - could not auto-translate; complete by hand.")
        lines.append(f"{TAB}/// Original Tableau formula: {cf.formula}")

    if "\n" in expr:
        lines.append(f"{TAB}measure {name} = ```")
        for raw in expr.split("\n"):
            lines.append(f"{TAB}{TAB}{TAB}{raw}")
        lines.append(f"{TAB}{TAB}{TAB}```")
    else:
        lines.append(f"{TAB}measure {name} = {expr}")

    if cf.format_string is not None:
        lines.append(f"{TAB}{TAB}formatString: {cf.format_string}")
    lines.append(f"{TAB}{TAB}lineageTag: {new_guid()}")
    lines.append("")
    return lines


def _table_tmdl(table: Table, model: Model) -> str:
    lines: list[str] = [
        f"table {quote_tmdl_name(table.name)}",
        f"{TAB}lineageTag: {table.lineage_tag}",
        "",
    ]

    # Calculated fields become measures on their assigned (fact) table, first.
    fact = model.fact_table()
    fact_name = fact.name if fact else None
    for cf in model.calculated_fields:
        if (cf.table or fact_name) == table.name:
            lines += _measure_tmdl(cf)

    for col in table.columns:
        lines.append(f"{TAB}column {quote_tmdl_name(col.name)}")
        lines.append(f"{TAB}{TAB}dataType: {col.data_type}")
        if col.format_string is not None:
            lines.append(f"{TAB}{TAB}formatString: {col.format_string}")
        lines.append(f"{TAB}{TAB}lineageTag: {col.lineage_tag}")
        lines.append(f"{TAB}{TAB}summarizeBy: {col.summarize_by}")
        lines.append(f"{TAB}{TAB}sourceColumn: {col.source_column}")
        lines.append("")
        lines.append(f"{TAB}{TAB}annotation SummarizationSetBy = Automatic")
        lines.append("")

    conn = model.connections.get(table.connection_ref) if table.connection_ref else None
    if conn is None and model.connections:
        conn = next(iter(model.connections.values()))

    lines.append(f"{TAB}partition {quote_tmdl_name(table.name)} = m")
    lines.append(f"{TAB}{TAB}mode: import")
    lines.append(f"{TAB}{TAB}source =")
    lines += m_query.build_partition_m(table, conn)
    lines.append("")
    lines.append(f"{TAB}annotation PBI_ResultType = Table")

    return render_tmdl(lines)


def _relationships_tmdl(model: Model) -> str:
    blocks: list[str] = []
    lines: list[str] = []
    for i, rel in enumerate(model.relationships):
        if i:
            lines.append("")
        from_ref = f"{quote_tmdl_name(rel.from_table)}.{quote_tmdl_name(rel.from_column)}"
        to_ref = f"{quote_tmdl_name(rel.to_table)}.{quote_tmdl_name(rel.to_column)}"
        lines.append(f"relationship {rel.name}")
        lines.append(f"{TAB}fromColumn: {from_ref}")
        lines.append(f"{TAB}toColumn: {to_ref}")
    return render_tmdl(lines)
