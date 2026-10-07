"""Read uploaded data files (Excel / Parquet) and match them to model tables.

Returns per-matched-table row data (aligned to the table's declared columns) so
the generator can embed it as an inline snapshot. Column matching is
case-insensitive; missing columns become null, extra columns are ignored.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from ..model.ir import Model

ROW_WARN_THRESHOLD = 50_000


@dataclass
class LoadedTable:
    columns: list[str]        # model source-column names, in table order
    rows: list[list]          # each row aligned to `columns`


def _match_table(model: Model, name: str):
    """Find the model table whose name matches `name` (case-insensitive).

    Tries the model's display name first, then its physical source name
    (the sheet Tableau actually read): Tableau renames a table when the same
    physical sheet is joined under different aliases, so a bundled file's
    sheet/file name may only match the physical name, not the display one.
    """
    low = (name or "").strip().lower()
    for t in model.tables:
        if t.name.lower() == low:
            return t
    for t in model.tables:
        if t.source_name.lower() == low:
            return t
    return None


def _align(table, source_columns: list[str], source_rows: list[list]) -> LoadedTable:
    """Reorder/parse source data to the model table's declared columns."""
    idx = {c.strip().lower(): i for i, c in enumerate(source_columns)}
    cols = [c.source_column for c in table.columns]
    out_rows: list[list] = []
    for row in source_rows:
        out_rows.append([
            row[idx[c.source_column.strip().lower()]] if c.source_column.strip().lower() in idx
            and idx[c.source_column.strip().lower()] < len(row) else None
            for c in table.columns
        ])
    return LoadedTable(columns=cols, rows=out_rows)


def _read_xlsx(blob: bytes) -> dict[str, tuple[list[str], list[list]]]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    out: dict[str, tuple[list[str], list[list]]] = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        header = [str(h) if h is not None else f"Column{i+1}" for i, h in enumerate(rows[0])]
        data = [list(r) for r in rows[1:]]
        out[ws.title] = (header, data)
    return out


def _read_xls(blob: bytes) -> dict[str, tuple[list[str], list[list]]]:
    """Read a legacy .xls (Excel 97-2003) workbook via xlrd."""
    import xlrd

    book = xlrd.open_workbook(file_contents=blob)
    out: dict[str, tuple[list[str], list[list]]] = {}
    for sheet in book.sheets():
        if sheet.nrows == 0:
            continue
        header = [str(sheet.cell_value(0, c)) or f"Column{c + 1}" for c in range(sheet.ncols)]
        rows: list[list] = []
        for r in range(1, sheet.nrows):
            row = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    row.append(xlrd.xldate_as_datetime(cell.value, book.datemode))
                elif cell.ctype == xlrd.XL_CELL_EMPTY:
                    row.append(None)
                elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                    row.append(bool(cell.value))
                else:
                    row.append(cell.value)
            rows.append(row)
        out[sheet.name] = (header, rows)
    return out


def _read_delimited(blob: bytes) -> tuple[list[str], list[list]]:
    """Read a .csv/.txt bundled data file. Delimiter is sniffed (comma, tab,
    semicolon, ...) rather than assumed, since Tableau text-file connections
    aren't all comma-separated."""
    text = blob.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel  # comma default
    rows = list(csv.reader(io.StringIO(text), dialect))
    if not rows:
        return [], []
    header = [h.strip() or f"Column{i + 1}" for i, h in enumerate(rows[0])]
    return header, rows[1:]


def _read_parquet(blob: bytes) -> tuple[list[str], list[list]]:
    import pyarrow.parquet as pq

    table = pq.read_table(io.BytesIO(blob))
    columns = table.column_names
    py = table.to_pylist()
    rows = [[rec.get(c) for c in columns] for rec in py]
    return columns, rows


def load_data_files(files: list[tuple[str, bytes]], model: Model) -> tuple[dict, list[str]]:
    """Return ({table_name: LoadedTable}, warnings)."""
    loaded: dict[str, LoadedTable] = {}
    warnings: list[str] = []
    unmatched_tables = {t.name for t in model.tables}

    for filename, blob in files or []:
        ext = Path(filename).suffix.lower()
        try:
            if ext in (".xlsx", ".xlsm", ".xls"):
                sheets = _read_xls(blob) if ext == ".xls" else _read_xlsx(blob)
                for sheet, (header, rows) in sheets.items():
                    table = _match_table(model, sheet)
                    if table is None:
                        warnings.append(f"Data sheet '{sheet}' did not match any table - skipped.")
                        continue
                    loaded[table.name] = _align(table, header, rows)
                    unmatched_tables.discard(table.name)
            elif ext in (".parquet", ".pq"):
                header, rows = _read_parquet(blob)
                stem = Path(filename).stem
                table = _match_table(model, stem)
                if table is None and len(unmatched_tables) == 1:
                    table = _match_table(model, next(iter(unmatched_tables)))
                if table is None:
                    warnings.append(f"Parquet '{filename}' did not match any table - skipped.")
                    continue
                loaded[table.name] = _align(table, header, rows)
                unmatched_tables.discard(table.name)
            elif ext in (".csv", ".txt"):
                header, rows = _read_delimited(blob)
                stem = Path(filename).stem
                table = _match_table(model, stem)
                if table is None and len(unmatched_tables) == 1:
                    table = _match_table(model, next(iter(unmatched_tables)))
                if table is None:
                    warnings.append(f"Data file '{filename}' did not match any table - skipped.")
                    continue
                loaded[table.name] = _align(table, header, rows)
                unmatched_tables.discard(table.name)
            else:
                warnings.append(f"Unsupported data file '{filename}' (use .xlsx, .xls, .csv, .txt or .parquet) - skipped.")
        except Exception as exc:  # noqa: BLE001 - surface as warning, never crash
            warnings.append(f"Could not read data file '{filename}': {exc}")

    for name, lt in loaded.items():
        if len(lt.rows) > ROW_WARN_THRESHOLD:
            warnings.append(
                f"'{name}' has {len(lt.rows):,} rows embedded as a snapshot - large inline data "
                "bloats the .pbip; consider a smaller extract or a live connection."
            )
    if loaded and unmatched_tables:
        warnings.append("No data provided for: " + ", ".join(sorted(unmatched_tables))
                        + " (those tables keep their original source and may be empty on open).")
    return loaded, warnings
