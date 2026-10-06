"""Top-level workbook parser: .twb XML bytes -> WorkbookMetadata.

Phase B scope: all data sources, their connections, tables and columns. Later
phases enrich the same DataSourceMeta with relationships, filters, custom SQL,
parameters, calculated fields, classification and the assessment.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element
from typing import Optional

from ..classification.model_shape import classify
from ..model.metadata import DataSourceMeta, WorkbookMetadata
from .calculations import calculated_field_names, extract_calculations
from .groups_bins import extract_groups_bins_sets
from .common import ParseError, last_name, load_xml, parse_ref
from .connections import PUBLISHED_CLASSES, extract_connections
from .customsql import extract_custom_sql
from .filters import extract_filters
from .parameters import extract_parameters
from .relationships import extract_joins, extract_logical_relationships
from .tables import extract_tables
from .unions import extract_unions
from .worksheets import extract_dashboards_and_stories, extract_worksheets

__all__ = ["parse_workbook", "ParseError"]


def _has_content(ds: Element) -> bool:
    return ds.find("connection") is not None or ds.find("column") is not None


def _field_lookup(ds_el: Element) -> dict[str, str]:
    """Field name -> physical table, from the ``<cols>`` map (for logical rels)."""
    lookup: dict[str, str] = {}
    cols = ds_el.find(".//cols")
    if cols is not None:
        for m in cols.findall("map"):
            field = last_name(m.get("key", ""))
            table, _ = parse_ref(m.get("value", ""))
            if field and table:
                lookup[field] = table
    return lookup


def _build_datasource(ds_el: Element, row_counts: Optional[dict[str, int]]) -> DataSourceMeta:
    connections = extract_connections(ds_el)
    conn_lookup = {c.name: c for c in connections}
    tables = extract_tables(ds_el, conn_lookup, row_counts)

    field_lookup = _field_lookup(ds_el)
    relationships = extract_joins(ds_el, field_lookup) + extract_logical_relationships(ds_el, field_lookup)
    unions = extract_unions(ds_el)
    filters = extract_filters(ds_el)
    custom_sql = extract_custom_sql(ds_el, {c.name: c.cls for c in connections})
    calc_names = calculated_field_names(ds_el)
    calcs = extract_calculations(ds_el)
    groups, sets_, bins = extract_groups_bins_sets(ds_el)

    # Extract vs Live: any extract-class connection, or an <extract> element.
    is_extract = any(c.is_extract for c in connections) or ds_el.find(".//extract") is not None
    is_published = any((c.cls or "").lower() in PUBLISHED_CLASSES for c in connections)

    return DataSourceMeta(
        name=ds_el.get("name", ""),
        caption=ds_el.get("caption"),
        description=ds_el.get("description") or _description_child(ds_el),
        version=ds_el.get("version"),
        connection_mode="Extract" if is_extract else "Live",
        is_extract=is_extract,
        is_published=is_published,
        connections=connections,
        tables=tables,
        relationships=relationships,
        unions=unions,
        filters=filters,
        custom_sql=custom_sql,
        calculated_field_names=calc_names,
        calculations=calcs,
        groups=groups,
        sets=sets_,
        bins=bins,
        classification=classify(tables, relationships),
    )


def _description_child(ds_el: Element) -> Optional[str]:
    # Tableau stores an optional rich-text description under <datasource>.
    node = ds_el.find(".//formatted-text/run")
    if node is not None and node.text:
        return node.text.strip()
    return None


def parse_workbook(
    twb_bytes: bytes,
    name: str,
    row_counts: Optional[dict[str, int]] = None,
) -> WorkbookMetadata:
    """Parse workbook XML into structured metadata.

    ``row_counts`` (table name lowercased -> rows) is supplied by the caller
    from bundled flat files (.twbx) when available; otherwise row counts are
    left unknown.
    """
    root = load_xml(twb_bytes)
    if root.tag != "workbook":
        raise ParseError(f"Root element is <{root.tag}>, expected <workbook>.")

    wb = WorkbookMetadata(
        name=name,
        version=root.get("version"),
        source_platform=root.get("source-platform"),
        source_build=root.get("source-build"),
        author=root.get("author") or _author(root),
        last_modified=root.get("modified") or root.get("last-modified"),
    )

    for ds_el in root.iter("datasource"):
        if ds_el.get("name") == "Parameters":
            continue  # the Parameters datasource is handled separately (below)
        if not _has_content(ds_el):
            continue
        wb.data_sources.append(_build_datasource(ds_el, row_counts))

    wb.parameters = extract_parameters(root)

    # Worksheets / dashboards / stories (fail-soft: never abort the whole parse).
    try:
        wb.worksheets = extract_worksheets(root)
        worksheet_names = {w.name for w in wb.worksheets}
        wb.dashboards, wb.stories = extract_dashboards_and_stories(root, worksheet_names)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully with a warning
        wb.warnings.append(f"Could not fully parse worksheets/dashboards: {exc}")

    wb.features = {
        "actions": len(root.findall(".//actions/action")) or len(root.findall(".//action")),
        "deviceLayouts": len(root.findall(".//device-layouts/device-layout")),
        "extensions": (
            len(root.findall(".//zone[@type-v2='extension']")) + len(root.findall(".//extension"))
        ),
    }

    if not wb.data_sources:
        wb.warnings.append("No data sources were found in this workbook.")
    return wb


def _author(root: Element) -> Optional[str]:
    # Tableau may store author under a repository-location or a user element.
    node = root.find(".//repository-location")
    if node is not None and node.get("id"):
        return node.get("id")
    return None
