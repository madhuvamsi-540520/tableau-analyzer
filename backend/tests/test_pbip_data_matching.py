"""Generalized bundled-data matching for PBIP generation.

Not every .twbx bundles an .xlsx whose sheet name matches the model's display
table name 1:1 - Tableau sometimes aliases a table (same physical sheet, used
twice) and some workbooks bundle .csv/.txt instead of Excel. These tests cover
both so the "embed bundled data instead of a dead-end path" fix generalizes
beyond the one sample it was first verified against.
"""
from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)

_TWB_TEMPLATE = """<?xml version='1.0' encoding='utf-8' ?>
<workbook version='18.1'>
  <datasources>
    <datasource caption='Orders Source' name='federated.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='Orders' name='excel-direct.1'>
            <connection class='excel-direct' filename='Data/orders.xlsx' />
          </named-connection>
        </named-connections>
        <relation connection='excel-direct.1' name='{table_name}' table='[Orders$]' type='table'>
          <columns gridOrigin='A1:B4:no:A1:B4:0' header='yes' outcome='6'>
            <column datatype='integer' name='Id' ordinal='0' />
            <column datatype='string' name='Name' ordinal='1' />
          </columns>
        </relation>
      </connection>
    </datasource>
  </datasources>
  <worksheets />
</workbook>
"""


def _upload_twbx(session: str, twb_xml: str, data_name: str, data_bytes: bytes) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Workbook.twb", twb_xml)
        z.writestr(f"Data/{data_name}", data_bytes)
    up = client.post(
        "/api/jobs",
        files=[("files", ("Workbook.twbx", buf.getvalue(), "application/octet-stream"))],
        headers={"X-Session-Id": session},
    )
    jobs = up.json()["jobs"]
    assert jobs[0]["ok"], jobs
    return jobs[0]["jobId"]


def _preview(session: str, job_id: str) -> dict:
    return client.post(
        f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": session}
    ).json()["summary"]


def test_bundled_csv_data_is_embedded():
    twb_xml = _TWB_TEMPLATE.format(table_name="Orders")
    csv_bytes = b"Id,Name\n1,Widget\n2,Gadget\n"
    job_id = _upload_twbx("csv1", twb_xml, "orders.csv", csv_bytes)

    summary = _preview("csv1", job_id)
    orders = next(t for t in summary["tables"] if t["name"] == "Orders")
    assert orders["dataLoaded"] is True
    assert orders["rowCount"] == 2
    assert not any("legal form" in w or "absolute path" in w for w in summary["warnings"])


def test_aliased_table_name_still_matches_physical_sheet_name():
    """Tableau's display name for the table ('Orders (1)') can differ from the
    physical sheet it reads ('Orders'); the bundled workbook only has the
    physical name, so matching must fall back to it."""
    twb_xml = _TWB_TEMPLATE.format(table_name="Orders (1)")

    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"  # matches the physical sheet, NOT the display name
    ws.append(["Id", "Name"])
    ws.append([1, "Widget"])
    buf = io.BytesIO()
    wb.save(buf)

    job_id = _upload_twbx("alias1", twb_xml, "orders.xlsx", buf.getvalue())
    summary = _preview("alias1", job_id)
    table = next(t for t in summary["tables"] if t["name"] == "Orders (1)")
    assert table["dataLoaded"] is True
    assert table["rowCount"] == 1
