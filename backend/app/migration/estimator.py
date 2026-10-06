"""Deterministic Tableau → Power BI migration estimator.

Produces the manual-effort item list, complexity band, developer-effort estimate
(hours/days/weeks), a 0–100 readiness score, the Power BI components required,
and the risks / challenges / strategy / priority — all from workbook metadata
using the tunable constants in :mod:`constants`.
"""
from __future__ import annotations

from . import constants as K


def _item(feature, reason, complexity, resolution, hours):
    return {
        "feature": feature,
        "reason": reason,
        "complexity": complexity,
        "resolution": resolution,
        "estimatedHours": round(hours, 1),
    }


def _band(hours: float) -> str:
    for limit, name in K.COMPLEXITY_BANDS:
        if hours < limit:
            return name
    return "Very High"


def estimate(wb) -> dict:
    items: list[dict] = []
    penalty = 0.0
    hours = K.PROJECT_OVERHEAD_HOURS

    calcs = [c for ds in wb.data_sources for c in ds.calculations]
    custom_sql = [s for ds in wb.data_sources for s in ds.custom_sql]
    features = wb.features or {}

    # --- Calculations needing manual work -------------------------------- #
    for c in calcs:
        if c.power_bi_support == "Direct":
            continue
        h = K.CALC_HOURS.get(c.migration_complexity, 2.0)
        hours += h
        penalty += K.READINESS_PENALTY["calc_unsupported" if c.power_bi_support == "Unsupported" else "calc_rewrite"]
        items.append(_item(
            f"Calculation: {c.name}", c.note, c.migration_complexity,
            "Rebuild as a DAX measure/column; validate results.", h,
        ))

    # --- Custom SQL ------------------------------------------------------- #
    for s in custom_sql:
        hours += K.CUSTOM_SQL_HOURS
        penalty += K.READINESS_PENALTY["custom_sql"]
        items.append(_item(
            f"Custom SQL: {s.name}",
            "Custom SQL must be reworked as a Power Query (M) query or a database view.",
            "Medium", "Move to a view / Power Query; parameterize where needed.", K.CUSTOM_SQL_HOURS,
        ))

    # --- Stories ---------------------------------------------------------- #
    if wb.stories:
        h = K.STORY_HOURS * len(wb.stories)
        hours += h
        penalty += K.READINESS_PENALTY["story"] * len(wb.stories)
        items.append(_item(
            f"Stories ({len(wb.stories)})",
            "Power BI has no direct Story equivalent.",
            "High", "Recreate as bookmarks + navigation buttons, or a guided report.", h,
        ))

    # --- Dashboard actions ------------------------------------------------ #
    n_actions = features.get("actions", 0)
    if n_actions:
        h = K.ACTION_HOURS * n_actions
        hours += h
        penalty += K.READINESS_PENALTY["action"] * n_actions
        items.append(_item(
            f"Dashboard Actions ({n_actions})",
            "Tableau actions (filter/highlight/URL/parameter) differ from Power BI interactions.",
            "Medium", "Map to visual interactions, drillthrough, bookmarks, or buttons.", h,
        ))

    # --- Device layouts --------------------------------------------------- #
    n_dev = features.get("deviceLayouts", 0)
    if n_dev:
        h = K.DEVICE_LAYOUT_HOURS * n_dev
        hours += h
        penalty += K.READINESS_PENALTY["device_layout"] * n_dev
        items.append(_item(
            f"Device Layouts ({n_dev})",
            "Device-specific layouts must be rebuilt with Power BI mobile layout.",
            "Medium", "Recreate using the Power BI mobile layout view.", h,
        ))

    # --- Extensions ------------------------------------------------------- #
    n_ext = features.get("extensions", 0)
    if n_ext:
        h = K.EXTENSION_HOURS * n_ext
        hours += h
        penalty += K.READINESS_PENALTY["extension"] * n_ext
        items.append(_item(
            f"Extensions ({n_ext})",
            "Dashboard extensions have no standard Power BI equivalent.",
            "Very High", "Replace with a certified custom visual or external tool, or drop.", h,
        ))

    # --- Sets / Groups / Bins -------------------------------------------- #
    n_sets = sum(len(ds.sets) for ds in wb.data_sources)
    n_groups = sum(len(ds.groups) for ds in wb.data_sources)
    n_bins = sum(len(ds.bins) for ds in wb.data_sources)
    if n_sets:
        h = 2.0 * n_sets
        hours += h
        items.append(_item(
            f"Sets ({n_sets})",
            "Power BI has no direct dynamic/IN-OUT set equivalent.",
            "Medium", "Recreate with a calculated table/column or a measure-driven flag.", h,
        ))
    if n_groups:
        h = 1.0 * n_groups
        hours += h
        items.append(_item(
            f"Groups ({n_groups})",
            "Tableau groups map to Power BI grouping or a mapping table.",
            "Low", "Use Power BI groups, or a lookup/mapping table.", h,
        ))
    if n_bins:
        h = 0.5 * n_bins
        hours += h
        items.append(_item(
            f"Bins ({n_bins})",
            "Tableau bins map to Power BI binning / a calculated column.",
            "Low", "Use Power BI binning or a calculated column.", h,
        ))

    # --- Parameters ------------------------------------------------------- #
    if wb.parameters:
        h = K.PARAMETER_HOURS * len(wb.parameters)
        hours += h
        items.append(_item(
            f"Parameters ({len(wb.parameters)})",
            "Tableau parameters map to Power BI field parameters or what-if parameters.",
            "Low", "Recreate as field/what-if parameters; rewire dependent logic.", h,
        ))

    # --- Visuals needing custom visuals / low confidence ------------------ #
    unsupported_vis = [w for w in wb.worksheets if (w.visual_type or "") in K.UNSUPPORTED_VISUALS]
    low_conf = [w for w in wb.worksheets if (w.visual_confidence or 1.0) < K.LOW_CONFIDENCE_THRESHOLD]
    if unsupported_vis:
        h = K.UNSUPPORTED_VISUAL_HOURS * len(unsupported_vis)
        hours += h
        penalty += K.READINESS_PENALTY["unsupported_visual"] * len(unsupported_vis)
        items.append(_item(
            f"Visuals needing custom visuals ({len(unsupported_vis)})",
            "Visual types like " + ", ".join(sorted({w.visual_type for w in unsupported_vis}))
            + " require Power BI marketplace/custom visuals.",
            "Medium", "Install certified custom visuals or redesign with native visuals.", h,
        ))
    if low_conf:
        hours += K.LOW_CONFIDENCE_VISUAL_HOURS * len(low_conf)
        penalty += K.READINESS_PENALTY["low_conf_visual"] * len(low_conf)

    # --- Baseline rebuild effort (worksheets + dashboards) ---------------- #
    hours += K.WORKSHEET_HOURS * len(wb.worksheets)
    hours += K.DASHBOARD_HOURS * len(wb.dashboards)

    # --- Multi data source consolidation ---------------------------------- #
    extra_sources = max(0, len(wb.data_sources) - 1)
    if extra_sources:
        hours += K.DATA_SOURCE_CONSOLIDATION_HOURS * extra_sources
        penalty += K.READINESS_PENALTY["multi_source"] * extra_sources

    # --- Effort / readiness / complexity ---------------------------------- #
    days = hours / K.HOURS_PER_DAY
    weeks = days / K.DAYS_PER_WEEK
    readiness = max(0, min(100, round(100 - penalty)))
    complexity = _band(hours)

    return {
        "manualEffortItems": items,
        "complexity": complexity,
        "effort": {"hours": round(hours, 1), "days": round(days, 1), "weeks": round(weeks, 1)},
        "readiness": readiness,
        "powerBiComponents": _components(wb, calcs, custom_sql, unsupported_vis),
        "risks": _risks(wb, calcs, custom_sql, unsupported_vis),
        "challenges": _challenges(wb, calcs),
        "strategy": _strategy(complexity),
        "priority": [
            "1. Build the semantic model (tables, relationships, data types).",
            "2. Recreate calculations as DAX measures/columns (LOD & table-calcs first).",
            "3. Rebuild worksheets as Power BI visuals (custom visuals where needed).",
            "4. Reassemble dashboards, then wire interactions/bookmarks (actions, stories).",
            "5. Validate numbers against Tableau and apply governance (RLS, certification).",
        ],
    }


def _components(wb, calcs, custom_sql, unsupported_vis) -> list[dict]:
    measures = sum(1 for c in calcs if c.power_bi_support != "Unsupported")
    rels = sum(len(ds.relationships) for ds in wb.data_sources)
    comps = [
        {"component": "Measures", "count": measures, "rationale": "One per convertible calculated field."},
        {"component": "Calculated Columns", "count": None, "rationale": "For row-level calcs that can't be measures."},
        {"component": "Relationships", "count": rels, "rationale": "Recreate Tableau joins/relationships in the model."},
        {"component": "Power Query (M)", "count": len(custom_sql), "rationale": "For custom SQL / shaping / extracts."},
        {"component": "Bookmarks", "count": len(wb.stories), "rationale": "To reproduce Stories and action navigation."},
        {"component": "Field Parameters", "count": len(wb.parameters), "rationale": "For Tableau parameters."},
        {"component": "Custom Visuals", "count": len(unsupported_vis), "rationale": "For visuals with no native equivalent."},
        {"component": "Calculation Groups", "count": None, "rationale": "Optional — to consolidate repetitive measures."},
        {"component": "Paginated Reports", "count": None, "rationale": "Consider for dense crosstabs / pixel-perfect output."},
    ]
    return comps


def _risks(wb, calcs, custom_sql, unsupported_vis) -> list[str]:
    risks = []
    n_unsup = sum(1 for c in calcs if c.power_bi_support == "Unsupported")
    n_tc = sum(1 for c in calcs if c.table_calc)
    n_lod = sum(1 for c in calcs if c.lod)
    if n_unsup:
        risks.append(f"{n_unsup} calculation(s) have no Power BI equivalent (RAWSQL/script).")
    if n_tc:
        risks.append(f"{n_tc} table calculation(s) require DAX window/rank rewrites and careful validation.")
    if n_lod:
        risks.append(f"{n_lod} LOD expression(s) must be re-expressed with CALCULATE and correct filter context.")
    if custom_sql:
        risks.append(f"{len(custom_sql)} custom SQL object(s) must be reworked in Power Query / views.")
    if wb.stories:
        risks.append("Stories have no native Power BI equivalent (bookmark-based rebuild).")
    if unsupported_vis:
        risks.append(f"{len(unsupported_vis)} visual(s) need custom/marketplace visuals.")
    # Surface a PII governance risk from the assessment if present.
    gov = (wb.assessment or {}).get("governance", [])
    if any("PII" in (f.get("title") or "") for f in gov):
        risks.append("PII/sensitive columns detected — apply RLS/masking during migration.")
    return risks or ["No major migration blockers detected."]


def _challenges(wb, calcs) -> list[str]:
    ch = []
    if any(c.lod for c in calcs) or any(c.table_calc for c in calcs):
        ch.append("Reproducing Tableau's LOD / table-calc semantics exactly in DAX.")
    if len(wb.worksheets) > 20:
        ch.append(f"High visual volume ({len(wb.worksheets)} worksheets) to rebuild and validate.")
    if len(wb.data_sources) > 1:
        ch.append("Consolidating multiple data sources into one governed model.")
    ch.append("Achieving pixel/interaction parity between Tableau and Power BI.")
    return ch


def _strategy(complexity: str) -> str:
    return {
        "Low": "Direct migration: rebuild the model and visuals in a single pass; light validation.",
        "Medium": "Phased migration: model first, then measures, then visuals; validate each phase.",
        "High": "Structured project: dedicate a sprint to the semantic model + DAX, then visuals; automated validation.",
        "Very High": "Program-level effort: staged workstreams for model, DAX, visuals and interactions with formal QA gates; consider re-designing rather than 1:1 porting.",
    }.get(complexity, "Phased migration with validation at each stage.")
