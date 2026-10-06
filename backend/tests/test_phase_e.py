"""Phase E: deterministic technical assessment + maturity score."""
from __future__ import annotations

from pathlib import Path

from app.assessment import assess
from app.assessment.util import naming_style, pii_category
from app.parser import parse_workbook

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"


def _titles(findings):
    return [f["title"] for f in findings]


# ---- helpers -------------------------------------------------------------- #

def test_pii_category():
    assert pii_category("Customer Email") == "Email"
    assert pii_category("SSN") == "SSN"
    assert pii_category("annual_salary") == "Compensation"
    assert pii_category("Region") is None


def test_naming_style():
    assert naming_style("Order Date") == "spaced"
    assert naming_style("order_date") == "snake"
    assert naming_style("orderDate") == "camel"
    assert naming_style("ORDER") == "upper"


# ---- real fixture assessment ---------------------------------------------- #

def test_final_assessment_shape_and_score():
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    a = assess(wb)
    for key in (
        "technicalDebt", "modelingRisks", "dataQualityRisks", "governance",
        "scalability", "performance", "optimization", "tradeoffs", "bestPractices", "summary",
    ):
        assert key in a
    assert 0 <= a["bestPractices"]["maturityScore"] <= 100
    assert a["summary"]["maturityBand"]
    # Final joins People on Region (non-key) -> grain/many-to-many risk flagged.
    assert any("non-key" in t for t in _titles(a["modelingRisks"]))


def test_assessment_is_deterministic():
    wb = parse_workbook((TWB_DIR / "Final.twb").read_bytes(), "Final")
    assert assess(wb)["bestPractices"] == assess(wb)["bestPractices"]


# ---- targeted synthetic checks -------------------------------------------- #

PII_MISMATCH_TWB = """<?xml version='1.0' encoding='utf-8'?>
<workbook version='2021.4'>
  <datasources>
    <datasource caption='People' name='federated.p1'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='pg.1'><connection class='postgres' server='db' dbname='hr'/></named-connection>
        </named-connections>
        <relation join='inner' type='join'>
          <clause type='join'>
            <expression op='='>
              <expression op='[Employee].[dept_id]'/>
              <expression op='[Dept].[dept_code]'/>
            </expression>
          </clause>
          <relation connection='pg.1' name='Employee' table='[public].[Employee]' type='table'>
            <columns>
              <column datatype='integer' name='dept_id' ordinal='0'/>
              <column datatype='string' name='Email' ordinal='1'/>
              <column datatype='string' name='SSN' ordinal='2'/>
            </columns>
          </relation>
          <relation connection='pg.1' name='Dept' table='[public].[Dept]' type='table'>
            <columns>
              <column datatype='string' name='dept_code' ordinal='0'/>
            </columns>
          </relation>
        </relation>
      </connection>
    </datasource>
  </datasources>
</workbook>
"""


def test_pii_and_type_mismatch_detected():
    wb = parse_workbook(PII_MISMATCH_TWB.encode("utf-8"), "PII")
    a = assess(wb)
    assert any("PII" in t for t in _titles(a["governance"]))
    assert any("data-type mismatch" in t.lower() for t in _titles(a["dataQualityRisks"]))
    # No description -> governance finding; PII high severity lowers governance dimension.
    assert a["bestPractices"]["dimensions"]["Governance & PII"] < 100


def test_missing_description_flagged():
    wb = parse_workbook(PII_MISMATCH_TWB.encode("utf-8"), "PII")
    a = assess(wb)
    assert any("without descriptions" in t for t in _titles(a["governance"]))


def test_maturity_band_thresholds():
    from app.assessment.best_practices import _band
    assert _band(90) == "Excellent (certification-ready)"
    assert _band(72) == "Good"
    assert _band(60) == "Moderate"
    assert _band(45) == "Developing"
    assert _band(20) == "Low"


def test_via_full_analyze_includes_assessment():
    from app.analysis import analyze
    from app.core.security import Packaging
    data = (TWB_DIR / "Final.twb").read_bytes()
    wb = analyze(data, "Final", data, Packaging(kind="twb"))
    assert wb.assessment["summary"]["totalFindings"] >= 0
    assert "maturityScore" in wb.assessment["summary"]
