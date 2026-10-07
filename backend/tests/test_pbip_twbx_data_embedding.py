"""A .twbx's bundled data should auto-embed into the generated PBIP.

Regression for: Power BI refusing to refresh with "The supplied file path
must be a valid absolute path" - Tableau stores a packaged workbook's Excel
source as a path relative to the .twbx, which ``File.Contents`` cannot open.
Since the data is already bundled inside the .twbx, PBIP generation should
embed it automatically (same mechanism as a manual data upload) instead of
falling back to that unusable relative path.
"""
from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)

_TWB = """<?xml version='1.0' encoding='utf-8' ?>
<workbook version='18.1'>
  <datasources>
    <datasource caption='Orders Source' name='federated.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='Orders' name='excel-direct.1'>
            <connection class='excel-direct' filename='Data/orders.xlsx' />
          </named-connection>
        </named-connections>
        <relation connection='excel-direct.1' name='Orders' table='[Orders$]' type='table'>
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


def _bundled_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(["Id", "Name"])
    ws.append([1, "Widget"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_twbx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Orders.twb", _TWB)
        z.writestr("Data/orders.xlsx", _bundled_xlsx())
    return buf.getvalue()


def _upload_twbx(session: str) -> str:
    up = client.post(
        "/api/jobs",
        files=[("files", ("Orders.twbx", _make_twbx(), "application/octet-stream"))],
        headers={"X-Session-Id": session},
    )
    jobs = up.json()["jobs"]
    assert jobs[0]["ok"], jobs
    return jobs[0]["jobId"]


def test_bundled_twbx_data_is_embedded_not_a_relative_path_error():
    job_id = _upload_twbx("embed1")
    preview = client.post(
        f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": "embed1"}
    ).json()["summary"]

    orders = next(t for t in preview["tables"] if t["name"] == "Orders")
    assert orders["dataLoaded"] is True
    assert orders["rowCount"] == 1
    assert not any("valid absolute path" in w for w in preview["warnings"])

    r = client.post(f"/api/jobs/{job_id}/pbip", json={}, headers={"X-Session-Id": "embed1"})
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    model_tmdl = next(n for n in zf.namelist() if n.endswith("Orders.tmdl"))
    text = zf.read(model_tmdl).decode("utf-8")
    assert "Table.FromRows" in text
    assert "File.Contents" not in text


def _generated_table_tmdl(session: str, job_id: str, table: str) -> str:
    r = client.post(f"/api/jobs/{job_id}/pbip", json={}, headers={"X-Session-Id": session})
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    name = next(n for n in zf.namelist() if n.endswith(f"/tables/{table}.tmdl"))
    return zf.read(name).decode("utf-8")


def test_plain_twb_without_data_embeds_sample_rows_not_a_dead_path():
    up = client.post(
        "/api/jobs",
        files=[("files", ("Orders.twb", _TWB.encode("utf-8"), "application/octet-stream"))],
        headers={"X-Session-Id": "embed2"},
    )
    job_id = up.json()["jobs"][0]["jobId"]

    preview = client.post(
        f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": "embed2"}
    ).json()["summary"]

    orders = next(t for t in preview["tables"] if t["name"] == "Orders")
    assert orders["dataOrigin"] == "sample"
    assert orders["rowCount"] > 0
    assert preview["dataMode"] == "Embedded sample data (inline)"
    assert any("SAMPLE" in w for w in preview["warnings"])
    tmdl = _generated_table_tmdl("embed2", job_id, "Orders")
    assert "Table.FromRows" in tmdl and "File.Contents" not in tmdl


# Mirrors a real failing workbook: the Excel connection has NO filename because
# the data only exists in a bundled .hyper extract -> File.Contents("") gave
# "The path is not of a legal form" in Power BI.
_TWB_HYPER = """<?xml version='1.0' encoding='utf-8' ?>
<workbook version='18.1'>
  <datasources>
    <datasource caption='Sample' name='federated.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='Sample' name='excel-direct.1'>
            <connection class='excel-direct' cleaning='no' />
          </named-connection>
        </named-connections>
        <relation type='collection'>
          <relation connection='excel-direct.1' name='Orders' table='[Orders$]' type='table'>
            <columns header='yes'>
              <column datatype='string' name='Order ID' ordinal='0' />
              <column datatype='real' name='Sales' ordinal='1' />
            </columns>
          </relation>
          <relation connection='excel-direct.1' name='Returns' table='[Returns$]' type='table'>
            <columns header='yes'>
              <column datatype='string' name='Order ID' ordinal='0' />
              <column datatype='string' name='Returned' ordinal='1' />
            </columns>
          </relation>
        </relation>
      </connection>
      <extract enabled='true'>
        <connection class='hyper' dbname='Data/TableauTemp/x.hyper' />
      </extract>
    </datasource>
  </datasources>
  <worksheets />
</workbook>
"""


def test_hyper_only_twbx_with_empty_excel_path_still_opens():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Hyper.twb", _TWB_HYPER)
        z.writestr("Data/TableauTemp/x.hyper", b"\x00not-readable-offline")
    up = client.post(
        "/api/jobs",
        files=[("files", ("Hyper.twbx", buf.getvalue(), "application/octet-stream"))],
        headers={"X-Session-Id": "hyper1"},
    )
    job_id = up.json()["jobs"][0]["jobId"]
    preview = client.post(
        f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": "hyper1"}
    ).json()["summary"]

    assert {t["dataOrigin"] for t in preview["tables"]} == {"sample"}
    assert any(".hyper extract" in w for w in preview["warnings"])
    for table in ("Orders", "Returns"):
        tmdl = _generated_table_tmdl("hyper1", job_id, table)
        assert "File.Contents" not in tmdl
        assert "Table.FromRows" in tmdl
