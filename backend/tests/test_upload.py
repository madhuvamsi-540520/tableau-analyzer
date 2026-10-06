"""Phase A: upload, validation, and session-scoped job lifecycle tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.fixtures import (
    make_twb,
    make_twbx,
    make_twbx_no_twb,
    make_twbx_traversal,
)

client = TestClient(app)


def _upload(files, session=None):
    headers = {"X-Session-Id": session} if session else {}
    return client.post("/api/jobs", files=files, headers=headers)


def _file(name, data, ctype="application/octet-stream"):
    return ("files", (name, data, ctype))


# ---- health --------------------------------------------------------------- #

def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---- happy paths ---------------------------------------------------------- #

def test_upload_twb_ok():
    r = _upload([_file("Sales.twb", make_twb())], session="s-twb")
    assert r.status_code == 200
    job = r.json()["jobs"][0]
    assert job["ok"] is True
    assert job["kind"] == "twb"
    assert job["status"] == "parsed"
    assert job["packaging"]["hasExtract"] is False


def test_upload_twbx_reports_bundled_files_and_extracts():
    r = _upload([_file("Report.twbx", make_twbx())], session="s-twbx")
    job = r.json()["jobs"][0]
    assert job["ok"] is True
    assert job["kind"] == "twbx"
    assert job["packaging"]["innerTwb"] == "MyWorkbook.twb"
    assert [f["name"] for f in job["packaging"]["flatFiles"]] == ["orders.csv"]
    assert job["packaging"]["hasExtract"] is True
    assert job["packaging"]["extracts"][0]["name"] == "data.hyper"


def test_multiple_files_one_batch():
    r = _upload([_file("a.twb", make_twb()), _file("b.twbx", make_twbx())], session="s-multi")
    jobs = r.json()["jobs"]
    assert len(jobs) == 2
    assert all(j["ok"] for j in jobs)


# ---- validation failures (reported inline, batch not aborted) ------------- #

def test_reject_unsupported_extension():
    r = _upload([_file("notebook.pdf", b"%PDF-1.7 junk")], session="s-x")
    job = r.json()["jobs"][0]
    assert job["ok"] is False
    assert "Unsupported file type" in job["error"]


def test_reject_twb_with_non_tableau_content():
    r = _upload([_file("fake.twb", b"this is not xml at all")], session="s-x")
    job = r.json()["jobs"][0]
    assert job["ok"] is False
    assert "workbook" in job["error"].lower()


def test_reject_twbx_without_workbook():
    r = _upload([_file("empty.twbx", make_twbx_no_twb())], session="s-x")
    job = r.json()["jobs"][0]
    assert job["ok"] is False
    assert "No .twb workbook" in job["error"]


def test_reject_twbx_with_path_traversal():
    r = _upload([_file("evil.twbx", make_twbx_traversal())], session="s-x")
    job = r.json()["jobs"][0]
    assert job["ok"] is False
    assert "Unsafe path" in job["error"]


def test_reject_corrupt_twbx():
    r = _upload([_file("broken.twbx", b"PK\x03\x04 not really a zip")], session="s-x")
    job = r.json()["jobs"][0]
    assert job["ok"] is False
    assert "valid .twbx" in job["error"]


def test_partial_batch_success():
    r = _upload([_file("good.twb", make_twb()), _file("bad.pdf", b"nope")], session="s-part")
    jobs = r.json()["jobs"]
    assert jobs[0]["ok"] is True
    assert jobs[1]["ok"] is False


# ---- session scoping / lifecycle ------------------------------------------ #

def test_jobs_are_session_scoped():
    up = _upload([_file("Sales.twb", make_twb())], session="owner")
    job_id = up.json()["jobs"][0]["jobId"]

    mine = client.get(f"/api/jobs/{job_id}", headers={"X-Session-Id": "owner"})
    assert mine.status_code == 200

    theirs = client.get(f"/api/jobs/{job_id}", headers={"X-Session-Id": "intruder"})
    assert theirs.status_code == 404


def test_list_and_delete():
    _upload([_file("Sales.twb", make_twb())], session="lifecycle")
    listing = client.get("/api/jobs", headers={"X-Session-Id": "lifecycle"})
    ids = [j["jobId"] for j in listing.json()["jobs"]]
    assert len(ids) >= 1

    d = client.delete(f"/api/jobs/{ids[0]}", headers={"X-Session-Id": "lifecycle"})
    assert d.status_code == 200
    gone = client.get(f"/api/jobs/{ids[0]}", headers={"X-Session-Id": "lifecycle"})
    assert gone.status_code == 404


def test_session_id_assigned_when_absent():
    r = client.post("/api/jobs", files=[_file("Sales.twb", make_twb())])
    assert r.headers.get("X-Session-Id")
    assert r.json()["sessionId"]
