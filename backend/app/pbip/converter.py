"""Pipeline orchestration: .twb bytes -> PBIP project (dict / zip)."""
from __future__ import annotations

import io
import json
import re
import zipfile

from .data import loader as data_loader
from .generator import dax_rules, excel_scaffold, llm_translator
from .generator.pbip_generator import build_project
from .model.ir import Model
from .parser.twb_parser import parse_twb
from .report import inventory_xlsx


def _project_name(filename: str) -> str:
    stem = re.sub(r"\.(twbx|twb|xml)$", "", filename, flags=re.IGNORECASE)
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


DATA_BUNDLED = "bundled"
DATA_SAMPLE = "sample"


def _embed_data(model: Model, data_files: list | None) -> None:
    """Attach real data (bundled in the .twbx, or uploaded) to matching tables
    as an inline snapshot."""
    if not data_files:
        return
    loaded, warnings = data_loader.load_data_files(data_files, model)
    model.warnings.extend(warnings)
    for table in model.tables:
        lt = loaded.get(table.name)
        if lt is not None:
            table.inline_columns = lt.columns
            table.inline_rows = lt.rows
            table.data_origin = DATA_BUNDLED
            model.warnings.append(f"Embedded {len(lt.rows):,} real row(s) into '{table.name}'.")


def _embed_sample_data(model: Model) -> None:
    """Every table without real data gets join-consistent sample rows inline.

    Same rule as obiee-analyzer: the model must never depend on an external
    file. A Tableau source path is not usable on another machine - it is
    relative to the .twbx, empty when the data lives only in a .hyper extract,
    or in another OS's syntax - and Power BI then fails to load with "The
    supplied file path must be a valid absolute path" / "The path is not of a
    legal form". Sample rows keep the project openable; the warning says so.
    """
    missing = [t for t in model.tables if t.inline_rows is None and t.columns]
    if not missing:
        return
    data = excel_scaffold.sample_rows(model)
    for table in missing:
        cols, rows = data[table.name]
        table.inline_columns = cols
        table.inline_rows = rows
        table.data_origin = DATA_SAMPLE
    model.warnings.append(
        "No readable source data for " + ", ".join(f"'{t.name}'" for t in missing)
        + " - embedded SAMPLE rows (join-consistent) so the project opens without an external "
        "file. Paste real data into the companion 'Data (template).xlsx' to replace them."
        + _hyper_note(model)
    )


def _hyper_note(model: Model) -> str:
    if model.has_hyper_extract:
        return " (This workbook's data is stored in a Tableau .hyper extract, which is not readable offline.)"
    return ""


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
    # Embed real data first and orient relationships by its row counts, then
    # fill every remaining table with sample rows so no partition ever points
    # at an external path. embed_data=False keeps the original source refs.
    if embed_data:
        _embed_data(model, data_files)
        _refine_relationships(model)
        _embed_sample_data(model)
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
    # Companion artifacts at the zip root (beside the .pbip; the model does not
    # depend on any of them to open).
    files[f"{model.name} Inventory.xlsx"] = inventory_xlsx.build_inventory_xlsx(model)
    template_name = f"{model.name} Data (template).xlsx"
    files[template_name] = excel_scaffold.build_workbook(model)
    files[f"{model.name} Migration Report.json"] = json.dumps(
        _report_dict(model, template_name), indent=2
    ).encode("utf-8")
    return model, files


def _data_mode(model: Model) -> str:
    origins = {t.data_origin for t in model.tables}
    if origins == {DATA_BUNDLED}:
        return "Embedded real data (inline)"
    if DATA_BUNDLED in origins and DATA_SAMPLE in origins:
        return "Embedded real + sample data (inline)"
    if origins == {DATA_SAMPLE}:
        return "Embedded sample data (inline)"
    return "Original source references"


def _report_dict(model: Model, template_name: str) -> dict:
    return {
        "project": model.name,
        "sourceCaption": model.source_caption,
        "dataSource": {
            "mode": _data_mode(model),
            "template": template_name,
            "tables": {t.name: t.data_origin or "source-reference" for t in model.tables},
        },
        "counts": {
            "tables": len(model.tables),
            "columns": sum(len(t.columns) for t in model.tables),
            "relationships": len(model.relationships),
            "calculatedFields": len(model.calculated_fields),
            "worksheetPages": len(model.worksheets),
            "dashboardPages": len(model.dashboards),
        },
        "calculatedFields": [
            {"name": cf.name, "formula": cf.formula, "dax": cf.dax,
             "method": cf.method, "needsReview": cf.needs_review}
            for cf in model.calculated_fields
        ],
        "warnings": model.warnings,
    }


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
    "The data is EMBEDDED inside the model, so the project opens fully\r\n"
    "populated - there is NO external file to locate and NO path to set.\r\n"
    "Tables whose real data was bundled in the .twbx carry that real data;\r\n"
    "any table whose data could not be read (e.g. it lives only in a .hyper\r\n"
    "extract) carries join-consistent SAMPLE rows instead. See\r\n"
    "'<name> Migration Report.json' for which is which, and paste real data\r\n"
    "into '<name> Data (template).xlsx' (exact sheet/column names) to replace\r\n"
    "sample rows.\r\n\r\n"
    "If you see 'Required artifact is missing ... definition.pbir', it\r\n"
    "means the folders were not extracted next to the .pbip - re-extract\r\n"
    "the full zip and try again.\r\n"
)


_EXTRACT_FIRST = (
    "!!! EXTRACT THIS ZIP FIRST !!!\r\n\r\n"
    "Right-click the .zip > Extract All, then open the .pbip from the EXTRACTED\r\n"
    "folder. Do NOT double-click the .pbip while it is still inside the zip - a\r\n"
    ".pbip needs its sibling .Report and .SemanticModel folders next to it, and\r\n"
    "Windows only unpacks the single file when you open it from inside the zip.\r\n"
)


def to_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    # Deterministic order; store paths with forward slashes (zip standard).
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Names starting with "!" sort to the top in Explorer so it's seen first.
        zf.writestr("! EXTRACT ALL FIRST - README !.txt", _EXTRACT_FIRST)
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
        "dataMode": _data_mode(model),
        "counts": {
            "tables": len(model.tables),
            "columns": sum(len(t.columns) for t in model.tables),
            "relationships": len(model.relationships),
            "calculatedFields": len(model.calculated_fields),
            "translated": translated,
            "worksheets": len(model.worksheets),
            "dashboardPages": len(model.dashboards),
        },
        "tables": [
            {
                "name": t.name,
                "kind": t.kind,
                "dataLoaded": t.inline_rows is not None,
                "dataOrigin": t.data_origin,
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
        "dashboards": [
            {
                "name": dash.name,
                "worksheets": [ws.name for ws in dash.worksheets],
            }
            for dash in model.dashboards
        ],
        "connections": [
            {"class": c.cls, "server": c.server, "database": c.database, "filename": c.filename}
            for c in model.connections.values()
        ],
        "warnings": model.warnings,
    }
