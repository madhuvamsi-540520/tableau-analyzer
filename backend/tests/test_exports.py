"""Phase F: export builders + the /export endpoint."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis import analyze
from app.core.security import Packaging
from app.export import csv_export, excel, json_export, pdf
from app.main import app

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"
client = TestClient(app)


def _meta():
    data = (TWB_DIR / "Final.twb").read_bytes()
    return analyze(data, "Final", data, Packaging(kind="twb")).to_api()


def test_json_export():
    out = json_export.build_json(_meta())
    assert out.startswith(b"{") and b'"dataSources"' in out


def test_csv_export_has_header_and_rows():
    out = csv_export.build_columns_csv(_meta()).decode("utf-8-sig")
    lines = out.strip().splitlines()
    assert lines[0].startswith("Data Source,Table,Column")
    assert len(lines) > 1


def test_xlsx_export_is_zip():
    out = excel.build_xlsx(_meta())
    assert out[:2] == b"PK"  # xlsx is a zip container


def test_pdf_export_is_pdf():
    out = pdf.build_pdf(_meta())
    assert out[:4] == b"%PDF"


def test_export_endpoint_all_formats():
    data = (TWB_DIR / "Final.twb").read_bytes()
    up = client.post(
        "/api/jobs",
        files=[("files", ("Final.twb", data, "application/octet-stream"))],
        headers={"X-Session-Id": "exp"},
    )
    job_id = up.json()["jobs"][0]["jobId"]

    expected = {
        "json": "application/json",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }
    for fmt, media in expected.items():
        r = client.get(f"/api/jobs/{job_id}/export?format={fmt}", headers={"X-Session-Id": "exp"})
        assert r.status_code == 200, fmt
        assert media in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]
        assert f"inventory.{fmt}" in r.headers["content-disposition"]
        assert r.content


def test_export_bad_format_and_scope():
    data = (TWB_DIR / "Final.twb").read_bytes()
    up = client.post(
        "/api/jobs",
        files=[("files", ("Final.twb", data, "application/octet-stream"))],
        headers={"X-Session-Id": "exp2"},
    )
    job_id = up.json()["jobs"][0]["jobId"]

    bad = client.get(f"/api/jobs/{job_id}/export?format=xml", headers={"X-Session-Id": "exp2"})
    assert bad.status_code == 400

    other = client.get(f"/api/jobs/{job_id}/export?format=json", headers={"X-Session-Id": "intruder"})
    assert other.status_code == 404
