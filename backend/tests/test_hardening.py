"""Fail-soft / resilience: malformed, partial, and unusual workbooks."""
from __future__ import annotations

import pytest

from app.analysis import analyze
from app.core.security import Packaging
from app.parser import ParseError, parse_workbook


def _analyze(xml: str):
    data = xml.encode("utf-8")
    return analyze(data, "t", data, Packaging(kind="twb"))


def test_malformed_xml_raises_parse_error():
    with pytest.raises(ParseError):
        parse_workbook(b"<workbook><datasource></workbook>", "bad")


def test_non_workbook_root_raises():
    with pytest.raises(ParseError):
        parse_workbook(b"<?xml version='1.0'?><nope/>", "bad")


def test_partial_workbook_no_datasources_is_soft():
    # Valid workbook, but empty — should return with a warning, not crash.
    wb = _analyze("<?xml version='1.0'?><workbook version='2021.4'><worksheets/></workbook>")
    assert wb.data_sources == []
    assert wb.warnings
    assert wb.assessment and wb.migration  # engines still produced output


def test_workbook_with_worksheets_no_datasource():
    xml = """<?xml version='1.0'?>
    <workbook version='2021.4'>
      <worksheets><worksheet name='S1'><table><panes><pane><mark class='Bar'/></pane></panes>
      <rows/><cols/></table></worksheet></worksheets>
    </workbook>"""
    wb = _analyze(xml)
    assert len(wb.worksheets) == 1
    assert wb.worksheets[0].visual_type  # visual detection still runs
    assert wb.migration["complexity"] in {"Low", "Medium", "High", "Very High"}


def test_full_pipeline_on_rich_sample_has_all_sections():
    import pathlib
    p = pathlib.Path(__file__).resolve().parent / "fixtures" / "twb" / "All Visual Sample.twb"
    data = p.read_bytes()
    wb = analyze(data, "S", data, Packaging(kind="twb"))
    api = wb.to_api()
    for key in ("workbookSummary", "worksheets", "dashboards", "stories",
                "assessment", "migration", "dataSources", "features"):
        assert key in api and api[key] is not None
    assert api["workbookSummary"]["worksheets"] == 30
