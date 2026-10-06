"""Calc classification + migration estimator (deterministic)."""
from __future__ import annotations

from pathlib import Path

from app.migration import estimate
from app.parser import parse_workbook
from app.parser.calc_classify import classify_formula

SAMPLE = Path(__file__).resolve().parent / "fixtures" / "twb" / "All Visual Sample.twb"


# ---- calc classification -------------------------------------------------- #

def test_classify_lod():
    r = classify_formula("{ FIXED [Country/Region] : SUM([Profit]) }")
    assert r["lod"] == "FIXED"
    assert r["powerBiSupport"] == "Rewrite"
    assert r["migrationComplexity"] == "Medium"


def test_classify_table_calc():
    r = classify_formula("WINDOW_SUM(SUM([Sales]))")
    assert r["tableCalc"] is True
    assert r["migrationComplexity"] == "High"


def test_classify_unsupported():
    r = classify_formula("RAWSQL_REAL('x', [Sales])")
    assert r["powerBiSupport"] == "Unsupported"
    assert r["migrationComplexity"] == "Very High"


def test_classify_basic_direct():
    r = classify_formula("SUM([Sales]) - SUM([Cost])")
    assert r["powerBiSupport"] == "Direct"
    assert r["migrationComplexity"] == "Low"


# ---- estimator ------------------------------------------------------------ #

def _wb():
    return parse_workbook(SAMPLE.read_bytes(), "S")


def test_estimator_shape_and_ranges():
    m = estimate(_wb())
    assert m["complexity"] in {"Low", "Medium", "High", "Very High"}
    assert 0 <= m["readiness"] <= 100
    assert m["effort"]["hours"] > 0
    assert m["effort"]["days"] == round(m["effort"]["hours"] / 8, 1)
    assert m["powerBiComponents"] and m["risks"] and m["priority"]


def test_estimator_flags_lod_calcs():
    m = estimate(_wb())
    titles = " ".join(i["feature"] for i in m["manualEffortItems"])
    assert "Calculation" in titles           # the 3 LOD calcs surface as manual items
    assert any("LOD" in r for r in m["risks"])


def test_estimator_deterministic():
    assert estimate(_wb()) == estimate(_wb())


def test_estimator_lists_stories_when_present():
    m = estimate(_wb())
    assert any("Stories" in i["feature"] for i in m["manualEffortItems"])
