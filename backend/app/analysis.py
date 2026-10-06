"""Analysis orchestration: raw upload -> WorkbookMetadata.

Ties the parser to the packaging: for a .twbx, best-effort row counts are
computed from bundled flat files and matched to tables by name.
"""
from __future__ import annotations

from . import rationalization, waf
from .assessment import assess
from .core.security import Packaging
from .data import flatfiles
from .dax import enrich_calculations
from .migration import estimate
from .model.metadata import WorkbookMetadata
from .parser import parse_workbook
from .visualization import classify_worksheet


def analyze(
    twb_bytes: bytes,
    name: str,
    original_bytes: bytes,
    packaging: Packaging,
) -> WorkbookMetadata:
    row_counts: dict[str, int] = {}
    if packaging.kind == "twbx":
        row_counts = flatfiles.row_counts_from_twbx(original_bytes)
    wb = parse_workbook(twb_bytes, name, row_counts)

    # Each downstream engine is isolated: a failure degrades that section (with a
    # structured warning) rather than failing the whole analysis (fail-soft).
    for ws in wb.worksheets:
        try:
            ws.visual_type, ws.visual_confidence, ws.visual_reasoning = classify_worksheet(ws)
        except Exception as exc:  # noqa: BLE001
            wb.warnings.append(f"Visual detection failed for '{ws.name}': {exc}")

    try:
        enrich_calculations(wb)
    except Exception as exc:  # noqa: BLE001
        wb.warnings.append(f"Calculation intelligence (DAX & Formula) failed: {exc}")

    try:
        wb.assessment = assess(wb)
    except Exception as exc:  # noqa: BLE001
        wb.warnings.append(f"Technical assessment failed: {exc}")

    try:
        wb.migration = estimate(wb)
    except Exception as exc:  # noqa: BLE001
        wb.warnings.append(f"Migration estimate failed: {exc}")

    # Dashboard & Worksheet rationalization (report similarity, consolidation,
    # visualization best-practice audit) — consumes worksheet/dashboard metadata.
    try:
        wb.rationalization = rationalization.run(wb)
    except Exception as exc:  # noqa: BLE001
        wb.warnings.append(f"Dashboard & Worksheet rationalization failed: {exc}")

    # Well-Architected framework consumes assessment + migration + DAX enrichment,
    # so it runs last (fail-soft — a failure degrades only this section).
    try:
        wb.well_architected = waf.run(wb)
    except Exception as exc:  # noqa: BLE001
        wb.warnings.append(f"Well-Architected Framework failed: {exc}")

    return wb
