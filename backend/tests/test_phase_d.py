"""Phase D: model classification, complexity metrics, calc/parameter counts."""
from __future__ import annotations

from pathlib import Path

from app.classification.model_shape import classify
from app.model.metadata import ColumnMeta, JoinCondition, RelationshipMeta, TableMeta
from app.parser import parse_workbook

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"


def _tbl(name, measures=0, dims=0):
    cols = [ColumnMeta(name=f"m{i}", original_name=f"m{i}", data_type="real", role="measure") for i in range(measures)]
    cols += [ColumnMeta(name=f"d{i}", original_name=f"d{i}", data_type="string", role="dimension") for i in range(dims)]
    return TableMeta(name=name, columns=cols)


def _rel(a, b):
    return RelationshipMeta(kind="join", left_table=a, right_table=b, join_type="inner",
                            conditions=[JoinCondition(left=f"{a}.k", op="=", right=f"{b}.k")])


# ---- classification ------------------------------------------------------- #

def test_flat_single_table():
    r = classify([_tbl("T", measures=3, dims=5)], [])
    assert r["type"] == "Flat Model"


def test_flat_disconnected_tables():
    r = classify([_tbl("A", dims=3), _tbl("B", dims=3)], [])
    assert r["type"] == "Flat Model"


def test_star_schema():
    tables = [_tbl("Fact", measures=4, dims=2), _tbl("DimA", dims=3), _tbl("DimB", dims=3)]
    rels = [_rel("Fact", "DimA"), _rel("Fact", "DimB")]
    r = classify(tables, rels)
    assert r["type"] == "Star Schema"
    assert r["factTables"] == ["Fact"]
    assert set(r["dimensionTables"]) == {"DimA", "DimB"}


def test_snowflake_schema():
    tables = [_tbl("Fact", measures=4), _tbl("DimA", dims=3), _tbl("DimSub", dims=3)]
    rels = [_rel("Fact", "DimA"), _rel("DimA", "DimSub")]  # dim->dim normalization
    r = classify(tables, rels)
    assert r["type"] == "Snowflake Schema"


def test_galaxy_schema():
    tables = [_tbl("Sales", measures=3, dims=2), _tbl("Returns", measures=2, dims=2), _tbl("DateDim", dims=3)]
    rels = [_rel("Sales", "DateDim"), _rel("Returns", "DateDim")]  # shared dim
    r = classify(tables, rels)
    assert r["type"].startswith("Galaxy")
    assert set(r["factTables"]) == {"Sales", "Returns"}


def test_final_fixture_is_star():
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    cls = wb.data_sources[0].classification
    assert cls["type"] == "Star Schema"
    assert cls["factTables"] == ["Orders"]
    assert set(cls["dimensionTables"]) == {"People", "Returns"}


# ---- calc fields, parameters, complexity ---------------------------------- #

CALC_PARAM_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource name='Parameters'>
      <column caption='Target' name='[Parameter 1]' datatype='integer' param-domain-type='range' value='100'>
        <calculation class='tableau' formula='100'/>
      </column>
      <column caption='Region P' name='[Parameter 2]' datatype='string' param-domain-type='list' value='West'>
        <calculation class='tableau' formula='&quot;West&quot;'/>
      </column>
    </datasource>
    <datasource caption='DS' name='federated.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='x.1'><connection class='excel-direct' filename='C:/d.xlsx'/></named-connection>
        </named-connections>
        <relation name='Orders' table='[Orders$]' type='table'>
          <columns><column datatype='real' name='Sales' ordinal='0'/></columns>
        </relation>
      </connection>
      <column caption='Profit Ratio' name='[Calculation_1]' datatype='real' role='measure'>
        <calculation class='tableau' formula='SUM([Profit])/SUM([Sales])'/>
      </column>
    </datasource>
  </datasources>
</workbook>
"""


def test_calc_and_parameter_counts():
    wb = parse_workbook(CALC_PARAM_TWB.encode("utf-8"), "CP")
    assert wb.data_sources[0].calculated_field_names == ["Profit Ratio"]
    assert [p.name for p in wb.parameters] == ["Target", "Region P"]
    assert wb.parameters[0].domain_type == "range"


def test_complexity_metrics():
    wb = parse_workbook(CALC_PARAM_TWB.encode("utf-8"), "CP")
    cx = wb.complexity()
    assert cx["calculatedFields"] == 1
    assert cx["parameters"] == 2
    assert cx["dataSources"] == 1
    assert cx["tables"] == 1


def test_final_complexity_has_two_joins():
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    assert wb.complexity()["joins"] == 2
