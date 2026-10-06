"""Pipeline orchestration: .twb bytes -> PBIP project (dict / zip)."""
from __future__ import annotations

import io
import re
import zipfile

from .data import loader as data_loader
from .generator import dax_rules, llm_translator
from .generator.pbip_generator import build_project
from .model.ir import Model
from .parser.twb_parser import parse_twb
from .report import inventory_xlsx


def _project_name(filename: str) -> str:
    stem = re.sub(r"\.(twb|xml)$", "", filename, flags=re.IGNORECASE)
    stem = stem.strip() or "Migrated"
    # Keep it filesystem/PBIP friendly.
    return re.sub(r'[<>:"/\\|?*]', "_", stem)


def _apply_overrides(model: Model, overrides: dict | None) -> None:
    """Apply user-corrected DAX (from the Preview review loop) to measures."""
    if not overrides:
        return
    for cf in model.calculated_fields:
        dax = overrides.get(cf.name)
        if dax and str(dax).strip():
            cf.dax, cf.translated, cf.needs_review, cf.method = str(dax).strip(), True, False, "manual"


def _embed_data(model: Model, data_files: list | None) -> None:
    """Attach uploaded data to matching tables as an inline snapshot."""
    if not data_files:
        return
    loaded, warnings = data_loader.load_data_files(data_files, model)
    model.warnings.extend(warnings)
    for table in model.tables:
        lt = loaded.get(table.name)
        if lt is not None:
            table.inline_columns = lt.columns
            table.inline_rows = lt.rows
            model.warnings.append(f"Embedded {len(lt.rows):,} row(s) into '{table.name}'.")


def _refine_relationships(model: Model) -> None:
    """When data is loaded, use row counts to orient many-to-one: the table with
    MORE rows is the 'from' (many) side. Corrects ties the column-count heuristic
    can't resolve."""
    rows = {t.name: len(t.inline_rows) for t in model.tables if t.inline_rows is not None}
    for rel in model.relationships:
        f, t = rel.from_table, rel.to_table
        if f in rows and t in rows and rows[f] < rows[t]:
            rel.from_table, rel.from_column, rel.to_table, rel.to_column = (
                rel.to_table, rel.to_column, rel.from_table, rel.from_column,
            )


def _build_model(
    xml_bytes: bytes,
    filename: str,
    use_llm: bool,
    api_key: str | None,
    overrides: dict | None,
    data_files: list | None = None,
    embed_data: bool = True,
) -> Model:
    model = parse_twb(xml_bytes.decode("utf-8-sig"), _project_name(filename))
    # Offline rule-based DAX first (always). The LLM (if requested + reachable)
    # then fills what the rules could not translate confidently.
    dax_rules.translate_model(model)
    if use_llm:
        llm_translator.translate_model(model, api_key=api_key)
    # User corrections win over everything.
    _apply_overrides(model, overrides)
    # Embed uploaded data as a snapshot (portable) when requested; otherwise the
    # partitions keep the original source reference (refreshable, path-dependent).
    if embed_data:
        _embed_data(model, data_files)
        _refine_relationships(model)
    return model


def convert(
    xml_bytes: bytes,
    filename: str,
    use_llm: bool = True,
    api_key: str | None = None,
    overrides: dict | None = None,
    data_files: list | None = None,
    embed_data: bool = True,
) -> tuple[Model, dict[str, bytes]]:
    model = _build_model(xml_bytes, filename, use_llm, api_key, overrides, data_files, embed_data)
    files = build_project(model)
    # Bundle the inventory report at the zip root (beside the .pbip; does not
    # affect opening in Power BI).
    files[f"{model.name} Inventory.xlsx"] = inventory_xlsx.build_inventory_xlsx(model)
    return model, files


def build_inventory(
    xml_bytes: bytes,
    filename: str,
    use_llm: bool = True,
    api_key: str | None = None,
    overrides: dict | None = None,
    data_files: list | None = None,
    embed_data: bool = True,
) -> tuple[Model, bytes]:
    """Parse a .twb and return (model, inventory .xlsx bytes) without the PBIP."""
    model = _build_model(xml_bytes, filename, use_llm, api_key, overrides, data_files, embed_data)
    return model, inventory_xlsx.build_inventory_xlsx(model)


def retranslate(
    xml_bytes: bytes, filename: str, calc_name: str, guidance: dict, api_key: str | None
) -> dict:
    """AI-assisted re-translation of a single measure using the user's guidance."""
    model = parse_twb(xml_bytes.decode("utf-8-sig"), _project_name(filename))
    dax_rules.translate_model(model)  # gives the LLM full context + field maps
    dax, error = llm_translator.retranslate_one(model, calc_name, guidance, api_key)
    return {"name": calc_name, "dax": dax, "ok": bool(dax), "error": error}


_HOW_TO_OPEN = (
    "HOW TO OPEN THIS POWER BI PROJECT\r\n"
    "=================================\r\n\r\n"
    "A .pbip is a POINTER, not a single file. It needs its sibling\r\n"
    "  <name>.Report\\  and  <name>.SemanticModel\\  folders next to it.\r\n\r\n"
    "1. EXTRACT this whole .zip first (right-click > Extract All).\r\n"
    "   Do NOT open the .pbip from inside the zip preview, and do NOT\r\n"
    "   copy out only the .pbip file - the report/model folders must\r\n"
    "   stay beside it.\r\n"
    "2. Open the EXTRACTED <name>.pbip in Power BI Desktop.\r\n\r\n"
    "If you see 'Required artifact is missing ... definition.pbir', it\r\n"
    "means the folders were not extracted next to the .pbip - re-extract\r\n"
    "the full zip and try again.\r\n"
)


def to_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    # Deterministic order; store paths with forward slashes (zip standard).
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("HOW_TO_OPEN.txt", _HOW_TO_OPEN)
        for path in sorted(files):
            zf.writestr(path, files[path])
    return buf.getvalue()


def _cardinality_label(from_cardinality: str) -> str:
    return "One-to-one" if from_cardinality == "one" else "Many-to-one"


def _crossfilter_label(cross_filter: str) -> str:
    return "Both" if cross_filter == "bothDirections" else "Single"


def summary(model: Model) -> dict:
    # Columns that participate in a relationship (either side) are "keys".
    key_cols = set()
    for r in model.relationships:
        key_cols.add((r.from_table, r.from_column))
        key_cols.add((r.to_table, r.to_column))

    translated = sum(1 for cf in model.calculated_fields if cf.translated)
    return {
        "projectName": model.name,
        "sourceCaption": model.source_caption,
        "counts": {
            "tables": len(model.tables),
            "columns": sum(len(t.columns) for t in model.tables),
            "relationships": len(model.relationships),
            "calculatedFields": len(model.calculated_fields),
            "translated": translated,
            "worksheets": len(model.worksheets),
        },
        "tables": [
            {
                "name": t.name,
                "kind": t.kind,
                "dataLoaded": t.inline_rows is not None,
                "rowCount": len(t.inline_rows) if t.inline_rows is not None else None,
                "columns": [
                    {
                        "name": c.name,
                        "dataType": c.data_type,
                        "summarizeBy": c.summarize_by,
                        "isKey": (t.name, c.name) in key_cols,
                    }
                    for c in t.columns
                ],
            }
            for t in model.tables
        ],
        "relationships": [
            {
                "from": f"{r.from_table}.{r.from_column}",
                "to": f"{r.to_table}.{r.to_column}",
                "fromTable": r.from_table,
                "fromKey": r.from_column,
                "toTable": r.to_table,
                "toKey": r.to_column,
                "type": _cardinality_label(r.from_cardinality),
                "crossFilter": _crossfilter_label(r.cross_filter),
            }
            for r in model.relationships
        ],
        "calculatedFields": [
            {
                "name": cf.name,
                "translated": cf.translated,
                "needsReview": cf.needs_review,
                "formula": cf.formula,
                "dax": cf.dax,
                "method": cf.method,
            }
            for cf in model.calculated_fields
        ],
        "worksheets": [
            {
                "name": ws.name,
                "visual": "tableEx",
                "fields": [f"{f.property} ({f.kind})" for f in ws.fields],
            }
            for ws in model.worksheets
        ],
        "connections": [
            {"class": c.cls, "server": c.server, "database": c.database, "filename": c.filename}
            for c in model.connections.values()
        ],
        "warnings": model.warnings,
    }
