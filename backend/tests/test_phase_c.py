"""Phase C: joins, logical relationships, unions, filters, custom SQL + SQL analysis."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.parser import parse_workbook
from app.sqlanalysis.analyzer import analyze_sql

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"
client = TestClient(app)


# ---- physical joins (real fixtures, de-duplicated) ------------------------ #

def test_simple_test_single_join():
    wb = parse_workbook((TWB_DIR / "Simple Test.twb").read_bytes(), "Simple Test")
    rels = wb.data_sources[0].relationships
    assert len(rels) == 1
    r = rels[0]
    assert r.kind == "join" and r.join_type == "inner"
    assert {r.left_table, r.right_table} == {"Orders", "Sales"}
    assert r.conditions[0].to_api()["left"] == "Orders.P.ID"


def test_final_two_joins():
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    rels = wb.data_sources[0].relationships
    assert len(rels) == 2
    pairs = {frozenset([r.left_table, r.right_table]) for r in rels}
    assert frozenset(["Orders", "Returns"]) in pairs
    assert frozenset(["Orders", "People"]) in pairs


# ---- custom SQL + sqlglot analysis ---------------------------------------- #

CUSTOM_SQL_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource caption='CSQL' name='federated.c1'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='pg.1'><connection class='postgres' server='db' dbname='sales'/></named-connection>
        </named-connections>
        <relation connection='pg.1' name='Top Regions' type='text'>WITH r AS (SELECT region, SUM(sales) s FROM public.orders GROUP BY region) SELECT region, s, RANK() OVER (ORDER BY s DESC) rnk FROM r WHERE s > (SELECT AVG(s) FROM r) UNION ALL SELECT 'ALL', SUM(s), 0 FROM r</relation>
      </connection>
    </datasource>
  </datasources>
</workbook>
"""


def test_custom_sql_extracted_and_analyzed():
    wb = parse_workbook(CUSTOM_SQL_TWB.encode("utf-8"), "CSQL")
    csql = wb.data_sources[0].custom_sql
    assert len(csql) == 1
    a = csql[0].analysis
    assert a["parsed"] is True
    assert "SUM" in a["aggregations"] and "AVG" in a["aggregations"]
    assert a["ctes"] == ["r"]
    assert a["hasUnionAll"] is True
    assert a["subqueryCount"] >= 1
    assert any("orders" in t for t in a["referencedTables"])
    assert "RANK" in a["windowFunctions"]


def test_sql_analysis_regex_fallback_on_garbage():
    a = analyze_sql("SELECT FROM WHERE ) OVER ( UNION ALL", dialect=None)
    # Unparseable, but the fallback still flags UNION ALL / window.
    assert a["parsed"] is False
    assert a["hasUnionAll"] is True


# ---- unions --------------------------------------------------------------- #

UNION_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource caption='U' name='federated.u1'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='x.1'><connection class='excel-direct' filename='C:/d.xlsx'/></named-connection>
        </named-connections>
        <relation name='All Sales' type='union'>
          <relation name='Sales2023' table='[Sales2023$]' type='table'>
            <columns><column datatype='integer' name='amt' ordinal='0'/></columns>
          </relation>
          <relation name='Sales2024' table='[Sales2024$]' type='table'>
            <columns><column datatype='integer' name='amt' ordinal='0'/></columns>
          </relation>
        </relation>
      </connection>
    </datasource>
  </datasources>
</workbook>
"""


def test_union_extracted():
    wb = parse_workbook(UNION_TWB.encode("utf-8"), "U")
    unions = wb.data_sources[0].unions
    assert len(unions) == 1
    assert unions[0].union_type == "manual"
    assert set(unions[0].tables) == {"Sales2023", "Sales2024"}


# ---- data source filters -------------------------------------------------- #

FILTER_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource caption='F' name='federated.f1'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='x.1'><connection class='excel-direct' filename='C:/d.xlsx'/></named-connection>
        </named-connections>
        <relation name='Orders' table='[Orders$]' type='table'>
          <columns><column datatype='string' name='Region' ordinal='0'/><column datatype='real' name='Sales' ordinal='1'/></columns>
        </relation>
      </connection>
      <filter class='categorical' column='[Region]'>
        <groupfilter function='union'>
          <groupfilter function='member' level='[Region]' member='&quot;West&quot;'/>
          <groupfilter function='member' level='[Region]' member='&quot;East&quot;'/>
        </groupfilter>
      </filter>
      <filter class='quantitative' column='[Sales]' included-values='in-range'>
        <min>100</min>
        <max>500</max>
      </filter>
    </datasource>
  </datasources>
</workbook>
"""


def test_filters_extracted():
    wb = parse_workbook(FILTER_TWB.encode("utf-8"), "F")
    filters = wb.data_sources[0].filters
    assert len(filters) == 2
    by_field = {f.field: f for f in filters}
    assert by_field["Region"].filter_type == "include"
    assert set(by_field["Region"].values) == {"West", "East"}
    assert by_field["Sales"].filter_type == "range"
    assert "min=100" in by_field["Sales"].values


# ---- custom SQL download endpoint ----------------------------------------- #

def test_custom_sql_download():
    up = client.post(
        "/api/jobs",
        files=[("files", ("csql.twb", CUSTOM_SQL_TWB.encode("utf-8"), "application/octet-stream"))],
        headers={"X-Session-Id": "csql-dl"},
    )
    job_id = up.json()["jobs"][0]["jobId"]
    r = client.get(f"/api/jobs/{job_id}/customsql/0/0", headers={"X-Session-Id": "csql-dl"})
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert b"UNION ALL" in r.content

    missing = client.get(f"/api/jobs/{job_id}/customsql/0/9", headers={"X-Session-Id": "csql-dl"})
    assert missing.status_code == 404


def test_counts_include_phase_c():
    wb = parse_workbook(CUSTOM_SQL_TWB.encode("utf-8"), "CSQL")
    c = wb.counts()
    assert c["customSql"] == 1
    assert "relationships" in c and "filters" in c and "unions" in c
