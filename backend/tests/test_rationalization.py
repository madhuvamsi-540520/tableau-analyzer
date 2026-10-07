"""Dashboard & Worksheet Rationalization engine tests."""
from __future__ import annotations

from pathlib import Path

from app import rationalization
from app.analysis import analyze
from app.core.security import validate_and_prepare
from app.parser import parse_workbook
from app.rationalization import context, similarity, vizrules
from app.rationalization.features import WorksheetFeature

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"


def _full_wb(name="All Visual Sample.twb"):
    raw = (TWB_DIR / name).read_bytes()
    twb_bytes, packaging, _flat_blobs = validate_and_prepare(name, raw)
    return analyze(twb_bytes, name.replace(".twb", ""), raw, packaging)


def _feat(name, viz="Bar Chart (horizontal)", measures=(), dimensions=(), ds=("superstore",),
          filters=(), encodings=("color",), mark="bar", dates=(), dashboards=()):
    return WorksheetFeature(
        name=name, viz_type=viz, mark=mark,
        data_sources=frozenset(ds), measures=frozenset(measures), dimensions=frozenset(dimensions),
        dates=frozenset(dates), filters=frozenset(filters), encodings=frozenset(encodings),
        field_count=len(measures) + len(dimensions), dashboards=tuple(dashboards),
    )


# --- similarity ------------------------------------------------------------ #

def test_identical_worksheets_are_duplicates():
    a = _feat("Sales", measures=("sales", "profit"), dimensions=("region", "segment"))
    b = _feat("Sales v2", measures=("sales", "profit"), dimensions=("region", "segment"))
    score, conf = similarity.worksheet_similarity(a, b)
    assert score >= similarity.DUPLICATE
    assert 0 < conf <= 1.0


def test_unrelated_worksheets_score_low():
    a = _feat("Sales", viz="Bar Chart (horizontal)", measures=("sales",), dimensions=("region",))
    b = _feat("Weather", viz="Line Chart", measures=("temp",), dimensions=("city",), mark="line")
    score, _ = similarity.worksheet_similarity(a, b)
    assert score < similarity.REVIEW


def test_clusters_group_similar_dashboards():
    class D:
        def __init__(self, name, ws):
            self.name = name
            self.worksheets = ws
            self.used_area_ratio = 0.5
            self.filter_count = self.legend_count = self.parameter_count = 0
            self.action_count = self.extension_count = 0
            self.width = self.height = 1000
            self.has_device_layouts = False

    ws_feats = [
        _feat("S1", measures=("sales",), dimensions=("region",)),
        _feat("S2", measures=("profit",), dimensions=("region",)),
    ]
    ctx = context.RationalizationContext(
        worksheets=ws_feats,
        dashboards=[D("Dash A", ["S1", "S2"]), D("Dash B", ["S1", "S2"])],
        stories=[],
        ws_by_name={f.name: f for f in ws_feats},
    )
    result = similarity.analyze_similarity(ctx)
    assert any(c["type"] == "dashboard" and c["size"] == 2 for c in result["clusters"])


# --- visualization rules --------------------------------------------------- #

def test_pie_chart_flagged_with_bar_recommendation():
    issues = vizrules._rule_pie(_feat("Pie", viz="Pie / Donut Chart", mark="pie",
                                      dimensions=("a", "b"), measures=("x",)))
    assert issues and "Bar" in issues[0].recommended_viz


def test_over_encoded_flagged():
    ws = _feat("Busy", encodings=("color", "size", "shape", "label", "detail"))
    assert vizrules._rule_over_encoded(ws)


def test_bars_over_time_recommend_line():
    ws = _feat("Trend", viz="bar over time", mark="bar", dates=("order date",),
               measures=("sales",))
    issues = vizrules._rule_wrong_trend(ws)
    assert issues and issues[0].recommended_viz == "Line Chart"


# --- full pipeline on the fixture ------------------------------------------ #

def test_full_report_shape():
    wb = _full_wb()
    rep = wb.rationalization
    assert rep and "executiveSummary" in rep
    ex = rep["executiveSummary"]
    assert ex["totalWorksheets"] == len(wb.worksheets)
    assert ex["totalDashboards"] == len(wb.dashboards)
    assert 30 <= ex["rationalizationScore"] <= 100
    assert 30 <= ex["vizQualityScore"] <= 100
    for key in ("similarity", "consolidation", "vizQuality", "dashboardQuality",
                "kpiConsolidation", "roadmap", "aiReview"):
        assert key in rep


def test_dashboard_layout_parsed():
    wb = _full_wb()
    # Dashboards should now carry composition detail from the primary <zones>.
    assert wb.dashboards, "fixture has dashboards"
    d = wb.dashboards[0]
    assert d.zone_count > 0
    assert d.used_area_ratio is not None


def test_offline_ai_review_is_deterministic_and_available():
    wb = _full_wb()
    out = rationalization.ai_review(wb.rationalization, use_llm=False)
    assert out["method"] == "offline-summary" and out["available"] is True
    assert out["summary"]


def test_existing_sections_still_present():
    """Additive change must not remove other engines' output."""
    wb = _full_wb()
    api = wb.to_api()
    for key in ("assessment", "migration", "wellArchitected", "rationalization", "dataSources"):
        assert key in api
