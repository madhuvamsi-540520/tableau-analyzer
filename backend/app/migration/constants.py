"""Tunable effort constants for the migration estimator (documented defaults).

All values are in developer-hours and are intentionally centralized so they can
be calibrated to an organization's own benchmarks without touching logic.
"""

HOURS_PER_DAY = 8
DAYS_PER_WEEK = 5

# Per-calculation effort by Power BI migration disposition.
CALC_HOURS = {"Low": 0.5, "Medium": 2.0, "High": 4.0, "Very High": 8.0}

# Per-object effort.
CUSTOM_SQL_HOURS = 3.0
STORY_HOURS = 4.0
ACTION_HOURS = 1.5
DEVICE_LAYOUT_HOURS = 2.0
EXTENSION_HOURS = 6.0            # typically a custom visual / external tool
PARAMETER_HOURS = 1.0
DASHBOARD_HOURS = 3.0
WORKSHEET_HOURS = 0.5           # baseline rebuild per worksheet
UNSUPPORTED_VISUAL_HOURS = 2.0  # extra when a visual needs a custom visual
LOW_CONFIDENCE_VISUAL_HOURS = 1.0
DATA_SOURCE_CONSOLIDATION_HOURS = 2.0  # per extra data source
PROJECT_OVERHEAD_HOURS = 8.0    # setup, theming, validation

# Visual types with no native Power BI equivalent (need a custom/marketplace visual).
UNSUPPORTED_VISUALS = {
    "Packed Bubbles", "Box Plot", "Gantt Chart", "Bullet Graph", "Treemap",
}
LOW_CONFIDENCE_THRESHOLD = 0.5

# Readiness penalties (points off 100).
READINESS_PENALTY = {
    "calc_rewrite": 3,        # per Rewrite calc
    "calc_unsupported": 8,    # per Unsupported calc
    "custom_sql": 4,
    "story": 6,
    "action": 2,
    "extension": 10,
    "device_layout": 2,
    "low_conf_visual": 2,
    "unsupported_visual": 3,
    "multi_source": 3,        # per extra data source
}

# Complexity bands by total effort (hours).
COMPLEXITY_BANDS = [(16, "Low"), (40, "Medium"), (120, "High")]  # else "Very High"
