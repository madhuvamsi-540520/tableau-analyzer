"""Dashboard-composed PBIP report pages + the .twbx project-name fix.

Tableau's "report" concept is the Dashboard (a page combining several
worksheets); the PBIP generator already emitted one page per Worksheet, but
had no notion of Dashboards at all. These tests cover the new
``model.dashboards`` composition and the regression fix in ``_project_name``
(a .twbx-sourced project used to keep the literal ".twbx" in its name).
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.pbip.converter import _project_name
from app.pbip.parser.twb_parser import parse_twb

TWB_DIR = Path(__file__).resolve().parent / "fixtures" / "twb"
client = TestClient(app)


def _load(name: str) -> str:
    return (TWB_DIR / name).read_text(encoding="utf-8-sig")


# --------------------------------------------------------------------------- #
# .twbx project-naming regression
# --------------------------------------------------------------------------- #


def test_project_name_strips_twbx_extension():
    assert _project_name("All Visuval Sample.twbx") == "All Visuval Sample"


def test_project_name_strips_twb_extension_unaffected():
    assert _project_name("Simple Test.twb") == "Simple Test"


# --------------------------------------------------------------------------- #
# Dashboard -> composed report page (parser level)
# --------------------------------------------------------------------------- #


def test_dashboards_compose_member_worksheets_in_zone_order():
    model = parse_twb(_load("All Visual Sample.twb"), "All Visual Sample")
    by_name = {d.name: [ws.name for ws in d.worksheets] for d in model.dashboards}

    assert by_name["Dashboard 1"] == ["Table", "Heat Map"]
    assert by_name["Dashboard 2"] == ["Pie Chart", "Side by side circle chart"]


def test_story_dashboard_is_excluded():
    model = parse_twb(_load("All Visual Sample.twb"), "All Visual Sample")
    names = {d.name for d in model.dashboards}
    assert "Story 1" not in names
    assert len(model.dashboards) == 2


# --------------------------------------------------------------------------- #
# End-to-end: the generated PBIP carries the composed pages
# --------------------------------------------------------------------------- #


def _upload(session: str, name: str = "All Visual Sample.twb") -> str:
    data = (TWB_DIR / name).read_bytes()
    up = client.post(
        "/api/jobs",
        files=[("files", (name, data, "application/octet-stream"))],
        headers={"X-Session-Id": session},
    )
    return up.json()["jobs"][0]["jobId"]


def test_pbip_preview_summary_lists_dashboards():
    job_id = _upload("dash1")
    r = client.post(f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": "dash1"})
    summary = r.json()["summary"]

    assert summary["counts"]["dashboardPages"] == 2
    names = {d["name"] for d in summary["dashboards"]}
    assert names == {"Dashboard 1", "Dashboard 2"}


def test_pbip_zip_has_one_page_per_worksheet_plus_dashboard():
    job_id = _upload("dash2")
    preview = client.post(
        f"/api/jobs/{job_id}/pbip/preview", json={}, headers={"X-Session-Id": "dash2"}
    ).json()["summary"]
    n_worksheets = preview["counts"]["worksheets"]
    n_dashboards = preview["counts"]["dashboardPages"]

    r = client.post(f"/api/jobs/{job_id}/pbip", json={}, headers={"X-Session-Id": "dash2"})
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    page_jsons = [n for n in zf.namelist() if n.endswith("/page.json")]
    assert len(page_jsons) == n_worksheets + n_dashboards

    # A dashboard page's visuals are stacked (distinct y-offsets), one per
    # member worksheet, not overlapping at the single-worksheet full-page spot.
    display_names = {}
    for n in page_jsons:
        page = json.loads(zf.read(n))
        display_names[page["name"]] = page["displayName"]
    dash1_page = next(k for k, v in display_names.items() if v == "Dashboard 1")
    visual_jsons = [
        n for n in zf.namelist() if f"/pages/{dash1_page}/visuals/" in n and n.endswith("visual.json")
    ]
    assert len(visual_jsons) == 2  # Table + Heat Map

    ys = sorted(json.loads(zf.read(n))["position"]["y"] for n in visual_jsons)
    assert ys[0] != ys[1]
