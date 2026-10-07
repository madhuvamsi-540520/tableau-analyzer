"""Report visuals must only project fields that exist in the semantic model.

Regressions found by validating real workbooks: a Tableau bin/group was
projected as if it were a model field (Power BI: "Something's wrong with one or
more fields"), and a Year date-part derivation became "Sum of Ship Date".
"""
from __future__ import annotations

from pathlib import Path

from app.pbip.parser.twb_parser import parse_twb

TWB = Path(__file__).resolve().parent / "fixtures" / "twb" / "All Visual Sample.twb"


def _model():
    return parse_twb(TWB.read_text(encoding="utf-8-sig"), "All Visual Sample")


def test_every_projected_field_exists_in_the_model():
    model = _model()
    columns = {(t.name, c.name) for t in model.tables for c in t.columns}
    measures = {cf.name for cf in model.calculated_fields}
    for ws in model.worksheets:
        for f in ws.fields:
            if f.kind == "measure":
                assert f.property in measures, (ws.name, f.property)
            else:
                assert (f.table, f.property) in columns, (ws.name, f.table, f.property)


def test_bins_and_groups_are_omitted_with_a_warning():
    model = _model()
    histogram = next(ws for ws in model.worksheets if ws.name == "Histogram")
    assert "Sales (bin)" not in {f.property for f in histogram.fields}
    assert any("Histogram" in w and "Sales (bin)" in w for w in model.warnings)


def test_date_part_derivation_is_not_summed():
    model = _model()
    col_types = {(t.name, c.name): c.data_type for t in model.tables for c in t.columns}
    for ws in model.worksheets:
        for f in ws.fields:
            if f.kind == "aggregation" and f.agg in ("Sum", "Avg", "Average"):
                assert col_types[(f.table, f.property)] in ("int64", "double"), (ws.name, f.property)
