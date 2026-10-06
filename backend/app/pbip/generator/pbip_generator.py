"""Assemble a complete, openable PBIP project (bytes) from the IR.

Produces the report artifact (JSON scaffolding, no visuals) and the semantic
model artifact (TMDL, delegated to :mod:`tmdl_generator`), plus the ``.pbip``
entry point and ``.gitignore``.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from ..model.ir import Model
from . import tmdl_generator, visual_generator
from .formatting import CRLF, encode, new_guid, render_json


def _hex20() -> str:
    return uuid.uuid4().hex[:20]

_THEME_PATH = Path(__file__).resolve().parent.parent / "templates" / "CY26SU05.json"
_THEME_NAME = "CY26SU05"

_S = "https://developer.microsoft.com/json-schemas/fabric"


def build_project(model: Model) -> dict[str, bytes]:
    """Return {archive_relative_path: bytes} for the whole PBIP project."""
    name = model.name
    report_dir = f"{name}.Report"
    sm_dir = f"{name}.SemanticModel"

    files: dict[str, bytes] = {}

    # ---- root ----
    files[f"{name}.pbip"] = encode(render_json(_pbip(report_dir)))
    files[".gitignore"] = encode("**/.pbi/localSettings.json" + CRLF + "**/.pbi/cache.abf")

    # ---- report artifact ----
    files[f"{report_dir}/.platform"] = encode(render_json(_platform("Report", name)))
    files[f"{report_dir}/definition.pbir"] = encode(render_json(_pbir(sm_dir)))
    files[f"{report_dir}/definition/report.json"] = encode(render_json(_report_json()))
    files[f"{report_dir}/definition/version.json"] = encode(render_json(_version_json()))
    _emit_pages(files, report_dir, model)
    files[
        f"{report_dir}/StaticResources/SharedResources/BaseThemes/{_THEME_NAME}.json"
    ] = _THEME_PATH.read_bytes()

    # ---- semantic model artifact ----
    files[f"{sm_dir}/.platform"] = encode(render_json(_platform("SemanticModel", name)))
    files[f"{sm_dir}/definition.pbism"] = encode(render_json(_pbism()))
    files[f"{sm_dir}/diagramLayout.json"] = encode(render_json(_diagram_layout(model)))
    files[f"{sm_dir}/.pbi/editorSettings.json"] = encode(render_json(_editor_settings()))

    for rel_path, text in tmdl_generator.generate_tmdl_files(model).items():
        files[f"{sm_dir}/{rel_path}"] = encode(text)

    return files


# --------------------------------------------------------------------------- #
# JSON payloads (key order matches the reference project exactly)
# --------------------------------------------------------------------------- #


def _emit_pages(files: dict[str, bytes], report_dir: str, model: Model) -> None:
    """One page per worksheet (each with a Table visual). Falls back to a single
    empty page when the workbook has no worksheets."""
    base = f"{report_dir}/definition/pages"

    if not model.worksheets:
        page_id = _hex20()
        files[f"{base}/pages.json"] = encode(render_json(_pages_json([page_id], page_id)))
        files[f"{base}/{page_id}/page.json"] = encode(render_json(_empty_page_json(page_id)))
        return

    page_ids: list[str] = []
    for ws in model.worksheets:
        page_id = _hex20()
        page_ids.append(page_id)
        files[f"{base}/{page_id}/page.json"] = encode(
            render_json(visual_generator.build_page(ws, page_id, _hex20()))
        )
        visual_id = _hex20()
        files[f"{base}/{page_id}/visuals/{visual_id}/visual.json"] = encode(
            render_json(visual_generator.build_visual(ws, visual_id))
        )
    files[f"{base}/pages.json"] = encode(render_json(_pages_json(page_ids, page_ids[0])))


def _pbip(report_dir: str) -> dict:
    return {
        "$schema": f"{_S}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": report_dir}}],
        "settings": {"enableAutoRecovery": True},
    }


def _platform(item_type: str, display_name: str) -> dict:
    return {
        "$schema": f"{_S}/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": item_type, "displayName": display_name},
        "config": {"version": "2.0", "logicalId": new_guid()},
    }


def _pbir(sm_dir: str) -> dict:
    return {
        "$schema": f"{_S}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{sm_dir}"}},
    }


def _report_json() -> dict:
    return {
        "$schema": f"{_S}/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": _THEME_NAME,
                "reportVersionAtImport": {"visual": "2.9.0", "report": "3.3.0", "page": "2.3.1"},
                "type": "SharedResources",
            }
        },
        "objects": {
            "section": [
                {"properties": {"verticalAlignment": {"expr": {"Literal": {"Value": "'Top'"}}}}}
            ]
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {"name": _THEME_NAME, "path": f"BaseThemes/{_THEME_NAME}.json", "type": "BaseTheme"}
                ],
            }
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
        },
    }


def _version_json() -> dict:
    return {
        "$schema": f"{_S}/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    }


def _pages_json(page_order: list[str], active: str) -> dict:
    return {
        "$schema": f"{_S}/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": page_order,
        "activePageName": active,
    }


def _empty_page_json(page_id: str) -> dict:
    return {
        "$schema": f"{_S}/item/report/definition/page/2.1.0/schema.json",
        "name": page_id,
        "displayName": "Page 1",
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
    }


def _pbism() -> dict:
    return {
        "$schema": f"{_S}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {},
    }


def _editor_settings() -> dict:
    return {
        "$schema": f"{_S}/item/semanticModel/editorSettings/1.0.0/schema.json",
        "autodetectRelationships": True,
        "parallelQueryLoading": True,
        "typeDetectionEnabled": True,
        "relationshipImportEnabled": True,
        "runBackgroundAnalysis": True,
        "shouldNotifyUserOfNameConflictResolution": True,
    }


def _diagram_layout(model: Model) -> dict:
    nodes = []
    for i, table in enumerate(model.tables):
        nodes.append(
            {
                "location": {"x": i * 300, "y": 0},
                "nodeIndex": table.name,
                "nodeLineageTag": table.lineage_tag,
                "size": {"height": 80 + 24 * len(table.columns), "width": 234},
                "zIndex": i,
            }
        )
    return {
        "version": "1.1.0",
        "diagrams": [
            {
                "ordinal": 0,
                "scrollPosition": {"x": 0, "y": 0},
                "nodes": nodes,
                "name": "All tables",
                "zoomValue": 100,
                "pinKeyFieldsToTop": False,
                "showExtraHeaderInfo": False,
                "hideKeyFieldsWhenCollapsed": False,
                "tablesLocked": False,
            }
        ],
        "selectedDiagram": "All tables",
        "defaultDiagram": "All tables",
    }
