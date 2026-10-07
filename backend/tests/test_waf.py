"""Well-Architected Power BI Framework engine tests."""
from __future__ import annotations

from pathlib import Path

from app import waf
from app.analysis import analyze
from app.core.security import validate_and_prepare
from app.dax import enrich_calculations
from app.parser import parse_workbook
from app.waf import context, engine
from app.waf.dax_quality import _find_cycles
from app.waf.pillar import Check, grade, score_from_checks

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"


def _full_wb(name="All Visual Sample.twb"):
    """Parse + run the full pipeline so wb has assessment/migration/dax enrichment."""
    raw = (TWB_DIR / name).read_bytes()
    twb_bytes, packaging, _flat_blobs = validate_and_prepare(name, raw)
    return analyze(twb_bytes, name.replace(".twb", ""), raw, packaging)


# --- value objects --------------------------------------------------------- #

def test_grade_bands():
    assert grade(95) == "A" and grade(82) == "B" and grade(72) == "C"
    assert grade(61) == "D" and grade(51) == "E" and grade(10) == "F"


def test_score_from_checks_penalizes_only_nonpassing():
    checks = [
        Check(id="a", title="a", status="pass", severity="high"),
        Check(id="b", title="b", status="fail", severity="high"),   # -20
        Check(id="c", title="c", status="warn", severity="medium"), # -10
    ]
    assert score_from_checks(checks) == 70


def test_find_cycles_detects_circular():
    cycles = _find_cycles({"A": ["B"], "B": ["A"]})
    assert cycles
    assert _find_cycles({"A": ["B"], "B": []}) == []


# --- registry / weights ---------------------------------------------------- #

def test_registry_weights_sum_to_one():
    assert round(sum(p.weight for p in engine.REGISTRY), 3) == 1.0


def test_registry_keys_unique():
    keys = [p.key for p in engine.REGISTRY]
    assert len(keys) == len(set(keys))


# --- engine output shape --------------------------------------------------- #

def test_run_produces_scorecard_and_roadmap():
    wb = _full_wb()
    report = waf.run(wb)

    assert 0 <= report["overall"]["score"] <= 100
    assert report["overall"]["grade"] in list("ABCDEF")
    assert report["overall"]["band"]

    # every registered pillar present with a 0-100 score
    assert len(report["pillars"]) == len(engine.REGISTRY)
    for p in report["pillars"]:
        assert 0 <= p["score"] <= 100
        assert p["grade"] in list("ABCDEF")
        assert "checks" in p and "counts" in p

    # roadmap items are prioritized and carry an action
    for item in report["roadmap"]:
        assert item["priority"] in ("P1", "P2", "P3")
        assert item["action"]
    # roadmap is sorted by priority
    priorities = [i["priority"] for i in report["roadmap"]]
    assert priorities == sorted(priorities)

    # quick wins are only P2/P3
    assert all(i["priority"] in ("P2", "P3") for i in report["quickWins"])

    # PBIP-dependent pillars surfaced as placeholders
    assert len(report["pbipPending"]) >= 3


def test_overall_is_weighted_average_of_pillars():
    wb = _full_wb()
    report = waf.run(wb)
    pillars = {p["key"]: p for p in report["pillars"]}
    total_w = sum(p.weight for p in engine.REGISTRY)
    expected = round(sum(pillars[p.key]["score"] * p.weight for p in engine.REGISTRY) / total_w)
    assert report["overall"]["score"] == expected


def test_context_builds_reference_sets():
    wb = _full_wb()
    ctx = context.build_context(wb)
    assert isinstance(ctx.calc_names, set)
    assert isinstance(ctx.referenced_names, set)
    assert isinstance(ctx.field_lookup, dict)


def test_fail_soft_on_empty_workbook():
    # A workbook with no data sources must still yield a well-formed report.
    from app.model.metadata import WorkbookMetadata
    wb = WorkbookMetadata(name="empty")
    report = waf.run(wb)
    assert report["overall"]["score"] >= 0
    assert len(report["pillars"]) == len(engine.REGISTRY)


def test_wellarchitected_in_api_payload():
    wb = _full_wb("Final.twb")
    api = wb.to_api()
    assert "wellArchitected" in api
    assert "overall" in api["wellArchitected"]
