"""DAX & Formula module — calculation intelligence engine tests."""
from __future__ import annotations

from pathlib import Path

from app.dax import convert, datatypes, engine, performance, references
from app.parser import parse_workbook

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"


# --- references / dependency graph ----------------------------------------- #

def test_extract_refs_distinct_in_order():
    assert references.extract_refs("[A] + [B] - [A]") == ["A", "B"]
    assert references.extract_refs("") == []


def test_dependency_index_parents_children_depth():
    formulas = {
        "Base": "SUM([Sales])",
        "Ratio": "[Base] / 100",
        "Scaled": "[Ratio] * [Base]",
    }
    idx = references.build_dependency_index(formulas, param_names=set())
    assert idx["Base"]["parents"] == []
    assert set(idx["Ratio"]["parents"]) == {"Base"}
    assert idx["Base"]["children"] == ["Ratio", "Scaled"]
    assert idx["Scaled"]["depth"] == 2   # Scaled -> Ratio -> Base


def test_dependency_index_is_cycle_safe():
    idx = references.build_dependency_index({"A": "[B]", "B": "[A]"}, param_names=set())
    assert idx["A"]["depth"] >= 0  # does not recurse infinitely


# --- offline conversion ---------------------------------------------------- #

def test_offline_translate_simple_measure():
    fl = {"Profit": ("Orders", "Profit"), "Sales": ("Orders", "Sales")}
    out = convert.suggest(name="Profit Ratio", formula="SUM([Profit])/SUM([Sales])",
                          categories=["Aggregation"], ctx={"field_lookup": fl, "measures": set()})
    assert out["method"] == "offline-rules"
    assert out["daxMeasure"] == "Profit Ratio = SUM(Orders[Profit])/SUM(Orders[Sales])"
    assert out["confidence"] >= 0.9


def test_offline_if_becomes_switch():
    fl = {"Sales": ("Orders", "Sales")}
    out = convert.suggest(name="Band", formula="IF [Sales] > 100 THEN 'Hi' ELSE 'Lo' END",
                          categories=["Logic (IF/CASE)"], ctx={"field_lookup": fl, "measures": set()})
    assert out["daxColumn"] and "SWITCH(TRUE()" in out["daxColumn"]


def test_offline_flags_lod_as_unconvertible():
    out = convert.suggest(name="CustLtv", formula="{FIXED [Customer] : SUM([Sales])}",
                          categories=["LOD (FIXED)"], ctx={"field_lookup": {}, "measures": set()})
    assert out["daxMeasure"] is None and out["daxColumn"] is None
    assert out["confidence"] == 0.0
    assert out["limitations"]


def test_offline_unresolved_field_is_not_guessed():
    out = convert.suggest(name="X", formula="SUM([Mystery])", categories=["Aggregation"],
                          ctx={"field_lookup": {}, "measures": set()})
    assert out["daxMeasure"] is None
    assert any("resolve" in l.lower() for l in out["limitations"])


# --- performance ----------------------------------------------------------- #

def test_performance_table_calc_is_high_risk():
    p = performance.assess(formula="WINDOW_SUM(SUM([Sales]))", categories=["Table Calculation"],
                           lod=None, table_calc=True, dep_depth=0, child_count=0)
    assert p["riskLevel"] in ("Medium", "High")
    assert any("window" in s.lower() or "table calc" in s.lower() for s in p["signals"])


def test_performance_simple_is_low_risk():
    p = performance.assess(formula="[A] + [B]", categories=["Basic / Arithmetic"],
                           lod=None, table_calc=False, dep_depth=0, child_count=0)
    assert p["riskLevel"] == "Low"


# --- data types ------------------------------------------------------------ #

def test_datatype_count_is_integer():
    dt = datatypes.infer(formula="COUNTD([Order ID])", categories=["Aggregation"],
                         field_types={"Order ID": "string"})
    assert dt["output"] == "integer"


def test_datatype_flags_string_numeric_mix():
    dt = datatypes.infer(formula="[Name] + [Qty]", categories=["Basic / Arithmetic"],
                         field_types={"Name": "string", "Qty": "integer"})
    assert any("implicit" in i.lower() or "string" in i.lower() for i in dt["issues"])


# --- full pipeline on a real fixture --------------------------------------- #

def test_enrich_final_fixture_populates_intelligence():
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    engine.enrich_calculations(wb)
    calcs = [c for ds in wb.data_sources for c in ds.calculations]
    # Fixture has calculated fields; enrichment must attach the new fields.
    if calcs:
        c = calcs[0]
        assert c.performance and "riskLevel" in c.performance
        assert isinstance(c.dax, dict) and "method" in c.dax
        assert c.automation_feasibility
        assert isinstance(c.dependencies, dict) and "depth" in c.dependencies
        api = c.to_api()
        assert "dependencies" in api and "performance" in api and "dax" in api


def test_context_from_api_roundtrip():
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    engine.enrich_calculations(wb)
    ctx = references.context_from_api(wb.to_api())
    assert isinstance(ctx["field_lookup"], dict)
    assert isinstance(ctx["measures"], set)
