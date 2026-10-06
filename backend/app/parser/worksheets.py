"""Extract worksheets, dashboards and stories (attribute-order-independent).

All access is via ElementTree attribute lookups and tag discovery — no fixed
paths or attribute positions — so it tolerates Tableau version differences and
missing nodes (fail-soft).
"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import DashboardMeta, EncodingUse, FieldUse, StoryMeta, WorksheetMeta
from .common import last_name

# Encoding channels are represented as child element names under <encodings>.
_ENCODING_CHANNELS = {
    "color", "size", "shape", "label", "detail", "text", "tooltip", "path",
    "angle", "lod", "level-of-detail",
}
_ANALYTICS_TAGS = {
    "reference-line": "Reference Line",
    "reference-band": "Reference Band",
    "reference-distribution": "Distribution Band",
    "trend-line": "Trend Line",
    "forecast": "Forecast",
    "cluster": "Clustering",
}


def _field_defs(deps: list[Element]) -> dict[str, tuple[str | None, str | None]]:
    """field name -> (role, datatype) from <column> defs inside dependencies."""
    out: dict[str, tuple[str | None, str | None]] = {}
    for dep in deps:
        for col in dep.findall("column"):
            out[last_name(col.get("name", ""))] = (col.get("role"), col.get("datatype"))
    return out


def _fields_used(deps: list[Element], defs: dict) -> list[FieldUse]:
    fields: list[FieldUse] = []
    seen: set[tuple[str, str]] = set()
    for dep in deps:
        for ci in dep.findall("column-instance"):
            col = last_name(ci.get("column", ""))
            deriv = ci.get("derivation")
            key = (col, deriv or "")
            if not col or key in seen:
                continue
            seen.add(key)
            role, dtype = defs.get(col, (None, None))
            fields.append(FieldUse(
                field=col,
                role=role,
                aggregation=None if (deriv in (None, "None")) else deriv,
                data_type=dtype,
            ))
    return fields


def _encodings(ws: Element) -> list[EncodingUse]:
    enc: list[EncodingUse] = []
    for pane in ws.iter("pane"):
        block = pane.find("encodings")
        if block is None:
            continue
        for child in list(block):
            channel = child.tag.lower()
            if channel in _ENCODING_CHANNELS:
                enc.append(EncodingUse(channel=channel, field=last_name(child.get("column", ""))))
    # Mark-level style encodings (e.g. size-bar) carry an attr + field.
    for rule in ws.findall(".//style/style-rule"):
        if rule.get("element") != "mark":
            continue
        for e in rule.findall("encoding"):
            attr = (e.get("attr") or "").split("-")[0]
            if attr in _ENCODING_CHANNELS:
                enc.append(EncodingUse(channel=attr, field=last_name(e.get("field", ""))))
    return enc


def _shelf(ws: Element, tag: str) -> list[str]:
    node = ws.find(tag)
    if node is None or not (node.text or "").strip():
        return []
    # A shelf holds one or more bracketed field references.
    return [last_name(part) for part in (node.text or "").split("][") if part.strip()]


def extract_worksheets(root: Element) -> list[WorksheetMeta]:
    sheets: list[WorksheetMeta] = []
    container = root.find("worksheets")
    if container is None:
        return sheets

    for ws in container.findall("worksheet"):
        name = ws.get("name", "Sheet")
        data_sources = [
            ds.get("caption") or ds.get("name")
            for ds in ws.findall(".//view/datasources/datasource")
            if (ds.get("caption") or ds.get("name"))
        ]
        deps = ws.findall(".//datasource-dependencies")
        defs = _field_defs(deps)
        fields = _fields_used(deps, defs)

        mark = ws.find(".//panes/pane/mark")
        mark_class = mark.get("class") if mark is not None else None

        filters = [
            last_name(f.get("column", ""))
            for f in ws.findall(".//filter")
            if f.get("column")
        ]
        analytics = sorted({
            label for tag, label in _ANALYTICS_TAGS.items() if ws.find(f".//{tag}") is not None
        })

        sheets.append(WorksheetMeta(
            name=name,
            data_sources=_dedupe(data_sources),
            mark_class=mark_class,
            fields=fields,
            encodings=_encodings(ws),
            rows_shelf=_shelf(ws, ".//rows") or _shelf(ws, "table/rows"),
            cols_shelf=_shelf(ws, ".//cols") or _shelf(ws, "table/cols"),
            filters=_dedupe(filters),
            analytics=analytics,
        ))
    return sheets


# Zone `type-v2` buckets (attribute-driven; unknown types fall through to "other").
_LAYOUT_ZONES = {"layout-basic", "layout-flow"}
_LEGEND_ZONES = {"size", "color", "shape", "measure-color", "ranged-color",
                 "legend", "filter-legend", "encoding"}
_FILTER_ZONES = {"filter", "flow-filter", "qualitative-filter", "quantitative-filter"}
_PARAM_ZONES = {"paramctrl", "parameter", "parameter-control"}
_TEXT_ZONES = {"text", "title", "caption"}
_IMAGE_ZONES = {"bitmap", "image"}
_WEB_ZONES = {"web", "webpage", "url", "page"}


def _classify_zone(z: Element, worksheet_names: set[str]) -> str:
    """Best-effort bucket for a single dashboard zone from its metadata."""
    tv = (z.get("type-v2") or "").lower()
    if tv in _LAYOUT_ZONES:
        return "container"
    if tv in _LEGEND_ZONES:
        return "legend"
    if tv in _FILTER_ZONES:
        return "filter"
    if tv in _PARAM_ZONES:
        return "parameter"
    if tv in _TEXT_ZONES:
        return "text"
    if tv in _IMAGE_ZONES:
        return "image"
    if tv in _WEB_ZONES:
        return "web"
    if tv == "dashboard-object":
        if z.find("add-in") is not None or "extension" in (z.get("param") or "").lower():
            return "extension"
        if z.find(".//bitmap") is not None:
            return "image"
        if z.find(".//formatted-text") is not None:
            return "text"
        return "object"
    # No/other type-v2: a worksheet zone carries the sheet's name and child zones.
    if (z.get("name") in worksheet_names) and not list(z.findall("zone")):
        return "worksheet"
    return "other"


def _int(z: Element, attr: str) -> int:
    try:
        return int(z.get(attr) or 0)
    except (TypeError, ValueError):
        return 0


def _dashboard_layout(dash: Element, worksheet_names: set[str]) -> dict:
    """Parse composition metrics from the dashboard's PRIMARY <zones> layout only
    (device layouts are skipped so their duplicated zones don't double-count)."""
    detail = {
        "zone_count": 0, "filter_count": 0, "legend_count": 0, "parameter_count": 0,
        "text_count": 0, "image_count": 0, "web_count": 0, "extension_count": 0,
        "used_area_ratio": None, "width": None, "height": None,
        "has_device_layouts": dash.find("devicelayouts") is not None,
    }
    size = dash.find("size")
    if size is not None:
        detail["width"] = _int(size, "maxwidth") or _int(size, "minwidth") or None
        detail["height"] = _int(size, "maxheight") or _int(size, "minheight") or None

    zones_el = dash.find("zones")
    if zones_el is None:
        return detail

    used_area = 0
    canvas = 100000 * 100000  # Tableau zone geometry is expressed in a 0..100000 grid
    for z in zones_el.iter("zone"):
        kind = _classify_zone(z, worksheet_names)
        if kind == "container":
            continue
        detail["zone_count"] += 1
        if kind == "worksheet":
            used_area += _int(z, "w") * _int(z, "h")
        elif kind == "legend":
            detail["legend_count"] += 1
        elif kind == "filter":
            detail["filter_count"] += 1
        elif kind == "parameter":
            detail["parameter_count"] += 1
        elif kind == "text":
            detail["text_count"] += 1
        elif kind == "image":
            detail["image_count"] += 1
        elif kind == "web":
            detail["web_count"] += 1
        elif kind == "extension":
            detail["extension_count"] += 1
    detail["used_area_ratio"] = round(min(1.0, used_area / canvas), 3) if used_area else 0.0
    return detail


def _action_counts(root: Element) -> dict[str, int]:
    """Count workbook actions referencing each sheet/dashboard name (best-effort).

    Actions reference their source/target views by name in child <param> values or
    in <source>/<target> attributes, in a version-independent way."""
    counts: dict[str, int] = {}
    for action in root.findall(".//actions/action") or root.findall(".//action"):
        names: set[str] = set()
        for p in action.iter("param"):
            val = p.get("value")
            if val:
                names.add(val)
        for tag in ("source", "target"):
            for node in action.iter(tag):
                for attr in ("name", "sheet", "dashboard"):
                    if node.get(attr):
                        names.add(node.get(attr))
        for n in names:
            counts[n] = counts.get(n, 0) + 1
    return counts


def extract_dashboards_and_stories(
    root: Element, worksheet_names: set[str]
) -> tuple[list[DashboardMeta], list[StoryMeta]]:
    dashboards: list[DashboardMeta] = []
    stories: list[StoryMeta] = []

    container = root.find("dashboards")
    if container is None:
        return dashboards, stories

    action_counts = _action_counts(root)

    for dash in container.findall("dashboard"):
        name = dash.get("name") or "Untitled"
        members = _dedupe([
            z.get("name") for z in dash.iter("zone")
            if z.get("name") in worksheet_names
        ])
        story_points = dash.findall(".//story-point")
        if story_points:
            stories.append(StoryMeta(name=name, story_points=len(story_points), worksheets=members))
        else:
            layout = _dashboard_layout(dash, worksheet_names)
            dashboards.append(DashboardMeta(
                name=name,
                worksheets=members,
                action_count=action_counts.get(name, 0),
                **layout,
            ))

    return dashboards, stories


def _dedupe(items) -> list[str]:
    out: list[str] = []
    for i in items:
        if i and i not in out:
            out.append(i)
    return out
