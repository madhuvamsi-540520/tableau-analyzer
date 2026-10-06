"""Visual-type detection against the named worksheets in the sample."""
from __future__ import annotations

from pathlib import Path

from app.parser import parse_workbook
from app.visualization import classify_worksheet

SAMPLE = Path(__file__).resolve().parent / "fixtures" / "twb" / "All Visual Sample.twb"


def _detected():
    wb = parse_workbook(SAMPLE.read_bytes(), "S")
    return {w.name: classify_worksheet(w) for w in wb.worksheets}


def test_clear_visuals_classified():
    d = _detected()
    assert d["Pie Chart"][0].startswith("Pie")
    assert d["Filled Map"][0] == "Filled Map"
    assert d["Symbol Map"][0] == "Symbol Map"
    assert d["Treemap"][0] == "Treemap"
    assert d["Packed Bubble Chart"][0] == "Packed Bubbles"
    assert d["Highlight Table"][0] == "Highlight Table"
    assert d["Single Scatter plot"][0] == "Scatter Plot"
    assert d["Cotinuous Area Chart"][0] == "Area Chart"
    assert d["Horizontal Bar"][0].startswith("Bar")
    assert d["Table"][0].startswith("Text Table")


def test_every_worksheet_gets_type_conf_reasoning():
    d = _detected()
    for name, (vtype, conf, reasoning) in d.items():
        assert vtype, name
        assert 0.0 <= conf <= 1.0, name
        assert reasoning, name  # evidence always provided


def test_geo_is_not_confused_with_scatter():
    d = _detected()
    assert "Map" in d["Filled Map"][0]
    assert "Map" in d["Symbol Map"][0]
