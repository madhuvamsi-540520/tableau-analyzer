"""PBIP generation (Migration Assessment tab): the /pbip preview + download.

The generation core is the parked converter, ported verbatim into ``app.pbip``.
These tests exercise the wiring: the offline (no key / no network) path turns a
stored workbook into a valid, openable PBIP project and a preview summary, and
the endpoints stay session-scoped.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"
client = TestClient(app)


def _upload(session: str, name: str = "Simple Test.twb") -> str:
    data = (TWB_DIR / name).read_bytes()
    up = client.post(
        "/api/jobs",
        files=[("files", (name, data, "application/octet-stream"))],
        headers={"X-Session-Id": session},
    )
    return up.json()["jobs"][0]["jobId"]


def test_generate_pbip_offline_is_valid_zip():
    job_id = _upload("pbip1")
    r = client.post(f"/api/jobs/{job_id}/pbip", json={}, headers={"X-Session-Id": "pbip1"})
    assert r.status_code == 200
    assert "application/zip" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    assert ".pbip.zip" in r.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert any(n.endswith(".pbip") for n in names)
    assert any(".SemanticModel/" in n for n in names)
    assert any(".Report/" in n for n in names)
    # Every generated definition file is non-empty (guards the "empty artifact" bug).
    for n in names:
        if n.endswith(("definition.pbir", "definition.pbism", "model.tmdl")):
            assert zf.read(n), f"empty artifact: {n}"


def test_pbip_preview_offline_summary():
    job_id = _upload("pbip2")
    r = client.post(f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": "pbip2"})
    assert r.status_code == 200
    summary = r.json()["summary"]
    assert summary["projectName"]
    assert "counts" in summary and summary["counts"]["tables"] >= 1
    # Calc->DAX entries carry a review flag so the UI can surface it.
    for cf in summary.get("calculatedFields", []):
        assert "needsReview" in cf and "dax" in cf


def test_pbip_is_session_scoped():
    job_id = _upload("owner")
    intruder = client.post(f"/api/jobs/{job_id}/pbip", json={}, headers={"X-Session-Id": "stranger"})
    assert intruder.status_code == 404
    preview = client.post(
        f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": "stranger"}
    )
    assert preview.status_code == 404


def test_pbip_missing_job_is_404():
    r = client.post("/api/jobs/does-not-exist/pbip", json={}, headers={"X-Session-Id": "pbip1"})
    assert r.status_code == 404
