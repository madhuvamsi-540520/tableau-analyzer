"""Worksheet / dashboard / story parsing + unique counting (rich sample)."""
from __future__ import annotations

from pathlib import Path

from app.parser import parse_workbook

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"
SAMPLE = TWB_DIR / "All Visual Sample.twb"


def _wb():
    return parse_workbook(SAMPLE.read_bytes(), "All Visual Sample")


def test_worksheet_dashboard_story_counts():
    wb = _wb()
    s = wb.workbook_summary()
    assert s["worksheets"] == 30
    assert s["dashboards"] == 2      # stories excluded from dashboard count
    assert s["stories"] == 1


def test_dashboard_membership_dedup():
    wb = _wb()
    d1 = next(d for d in wb.dashboards if d.name == "Dashboard 1")
    assert set(d1.worksheets) == {"Table", "Heat Map"}
    # A worksheet appears once per dashboard even if placed in multiple zones.
    assert len(d1.worksheets) == len(set(d1.worksheets))


def test_story_detected_with_points():
    wb = _wb()
    story = wb.stories[0]
    assert story.name == "Story 1"
    assert story.story_points >= 1


def test_worksheet_fields_marks_encodings():
    wb = _wb()
    by_name = {w.name: w for w in wb.worksheets}
    circle = by_name["Circle chart"]
    assert circle.mark_class == "Shape"
    assert any(f.aggregation == "Sum" for f in circle.fields)
    assert {"color", "size"} <= {e.channel for e in circle.encodings}


def test_marks_cover_multiple_types():
    wb = _wb()
    marks = {w.mark_class for w in wb.worksheets}
    assert {"Bar", "Circle", "Area", "Shape"} <= marks


def test_groups_sets_bins_captured():
    wb = _wb()
    ds = wb.data_sources[0]
    assert [b.name for b in ds.bins] == ["Sales (bin)"]
    assert ds.bins[0].size == "446"
    assert [g.name for g in ds.groups] == ["Sub Category Group"]
    assert ds.groups[0].source_field == "Sub-Category"
    assert len(ds.groups[0].groups) == 3           # A / B / C
    assert any(s.name == "IMP Region" for s in ds.sets)


def test_minimal_workbook_has_no_worksheet_crash():
    # The tiny fixtures have a single empty worksheet and no dashboards.
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    assert wb.workbook_summary()["dashboards"] == 0
    assert wb.workbook_summary()["worksheets"] >= 1
