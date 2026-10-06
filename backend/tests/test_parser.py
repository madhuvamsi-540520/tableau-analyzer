"""Phase B: workbook metadata parser tests (real fixtures + synthetic)."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from app.analysis import analyze
from app.core.security import Packaging, validate_and_prepare
from app.parser import ParseError, parse_workbook

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"


def _load(name: str) -> bytes:
    return (TWB_DIR / name).read_bytes()


# ---- real fixtures -------------------------------------------------------- #

def test_simple_test_tables_and_columns():
    wb = parse_workbook(_load("Simple Test.twb"), "Simple Test")
    assert wb.version == "18.1"
    assert len(wb.data_sources) == 1
    ds = wb.data_sources[0]
    assert ds.friendly_types == ["Excel"]
    assert ds.connection_mode == "Live"
    tables = {t.name: t for t in ds.tables}
    assert set(tables) == {"Orders", "Sales"}
    assert tables["Sales"].columns  # has columns
    # The Sales-side P.ID is disambiguated by the cols map.
    sales_cols = {c.name for c in tables["Sales"].columns}
    assert "P.ID (Sales)" in sales_cols
    # Renamed captions are applied.
    orders_cols = {c.name for c in tables["Orders"].columns}
    assert {"P.Id", "P.Name"} <= orders_cols


def test_superstore_measure_role_inference():
    wb = parse_workbook(_load("Book1T1.twb"), "Book1T1")
    cols = {c.name: c for t in wb.data_sources[0].tables for c in t.columns}
    # Numerics with no explicit role default to measure...
    assert cols["Sales"].role == "measure"
    assert cols["Profit"].role == "measure"
    # ...but explicit dimensions stay dimensions.
    assert cols["Row ID"].role == "dimension"
    assert cols["Postal Code"].role == "dimension"
    # Nullability captured from <contains-null>.
    assert cols["Sales"].nullable is True


def test_original_name_vs_caption():
    wb = parse_workbook(_load("Simple Test.twb"), "Simple Test")
    cols = {c.name: c for t in wb.data_sources[0].tables for c in t.columns}
    assert cols["P.Id"].original_name == "P.ID"   # display renamed, source preserved
    assert cols["P.Id"].alias == "P.Id"


def test_final_three_tables():
    wb = parse_workbook(_load("Final.twb"), "Final")
    names = {t.name for t in wb.data_sources[0].tables}
    assert names == {"Orders", "People", "Returns"}


def test_counts_shape():
    wb = parse_workbook(_load("Book1T1.twb"), "Book1T1")
    c = wb.counts()
    assert c["dataSources"] == 1 and c["tables"] == 1 and c["columns"] == 21


# ---- synthetic: connection-type mapping + multi datasource ---------------- #

SNOWFLAKE_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4' source-platform='win'>
  <datasources>
    <datasource caption='Sales DW' name='federated.sf1' version='2021.4'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='SF' name='snowflake.1'>
            <connection class='snowflake' server='acme.snowflakecomputing.com'
              dbname='ANALYTICS' schema='PUBLIC' warehouse='WH_XS'
              authentication='Username' username='svc_bi' password='shh' />
          </named-connection>
        </named-connections>
        <relation name='FACT_SALES' table='[PUBLIC].[FACT_SALES]' type='table'>
          <columns>
            <column datatype='integer' name='ORDER_ID' ordinal='0'/>
            <column datatype='real' name='AMOUNT' ordinal='1'/>
          </columns>
        </relation>
      </connection>
    </datasource>
    <datasource caption='Ref' name='federated.x2' version='2021.4'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='sqlserver.1'>
            <connection class='sqlserver' server='db01' dbname='REF' authentication='sspi'/>
          </named-connection>
        </named-connections>
        <relation name='DimDate' table='[dbo].[DimDate]' type='table'>
          <columns><column datatype='date' name='DateKey' ordinal='0'/></columns>
        </relation>
      </connection>
    </datasource>
  </datasources>
</workbook>
"""


def test_multi_datasource_and_type_mapping():
    wb = parse_workbook(SNOWFLAKE_TWB.encode("utf-8"), "Synthetic")
    assert len(wb.data_sources) == 2
    sf, ref = wb.data_sources
    assert sf.friendly_types == ["Snowflake"]
    conn = sf.connections[0]
    assert conn.warehouse == "WH_XS"
    assert conn.database == "ANALYTICS"
    assert conn.authentication == "Username"
    # Secrets are never surfaced.
    assert "password" not in conn.extra and conn.to_api().get("password") is None
    assert ref.friendly_types == ["SQL Server"]
    assert ref.tables[0].schema == "dbo"
    assert ref.tables[0].database == "REF"


def test_amount_is_measure_by_type():
    wb = parse_workbook(SNOWFLAKE_TWB.encode("utf-8"), "Synthetic")
    cols = {c.name: c for c in wb.data_sources[0].tables[0].columns}
    assert cols["AMOUNT"].role == "measure"
    assert cols["ORDER_ID"].role == "measure"  # numeric, no explicit role


# ---- error handling ------------------------------------------------------- #

def test_malformed_xml_raises_parse_error():
    with pytest.raises(ParseError):
        parse_workbook(b"<workbook><datasource></workbook>", "bad")


def test_wrong_root_raises_parse_error():
    with pytest.raises(ParseError):
        parse_workbook(b"<?xml version='1.0'?><notaworkbook/>", "bad")


# ---- .twbx row counts from bundled flat files ----------------------------- #

def _make_twbx_with_csv() -> bytes:
    twb = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource caption='D' name='federated.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='csv.1'><connection class='textscan' directory='.'/></named-connection>
        </named-connections>
        <relation name='orders' table='[orders]' type='table'>
          <columns><column datatype='integer' name='id' ordinal='0'/></columns>
        </relation>
      </connection>
    </datasource>
  </datasources>
</workbook>
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("wb.twb", twb)
        z.writestr("Data/orders.csv", "id\n1\n2\n3\n")
    return buf.getvalue()


def test_twbx_row_counts_applied():
    data = _make_twbx_with_csv()
    twb_bytes, packaging = validate_and_prepare("bundle.twbx", data)
    assert packaging.kind == "twbx"
    wb = analyze(twb_bytes, "bundle", data, packaging)
    orders = wb.data_sources[0].tables[0]
    assert orders.row_count == 3
