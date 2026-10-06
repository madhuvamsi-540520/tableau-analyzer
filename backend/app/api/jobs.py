"""Job API — upload, list, inspect, delete. Every route is session-scoped.

A session id is supplied by the client via the ``X-Session-Id`` header; if
absent, one is generated and echoed back in the response header so the client
can adopt it. Jobs are only ever visible to the session that created them.

Phase A exposes upload + lifecycle only. ``GET /jobs/{id}`` returns the job
summary; the full parsed metadata is added in Phase B.
"""
from __future__ import annotations

import io
import re
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Body, File, Header, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse

from .. import analysis
from ..core.security import UploadError, validate_and_prepare
from ..dax import context_from_api, suggest as suggest_dax
from ..rationalization import ai_review as rationalization_ai_review
from ..export import csv_export, excel, json_export, pdf
from ..jobs.store import store
from ..parser import ParseError
from ..pbip import converter as pbip_converter

router = APIRouter(prefix="/api", tags=["jobs"])

_SESSION_HEADER = "X-Session-Id"


def _resolve_session(response: Response, x_session_id: str | None) -> str:
    sid = (x_session_id or "").strip() or uuid.uuid4().hex
    response.headers[_SESSION_HEADER] = sid
    return sid


@router.post("/jobs")
async def upload_jobs(
    response: Response,
    files: list[UploadFile] = File(...),
    x_session_id: str | None = Header(default=None),
) -> dict:
    """Upload one or more .twb / .twbx files. Per-file validation errors are
    reported inline (ok=false) rather than failing the whole batch."""
    sid = _resolve_session(response, x_session_id)
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    results: list[dict] = []
    for f in files:
        filename = f.filename or "workbook.twb"
        try:
            raw = await f.read()
            twb_bytes, packaging = validate_and_prepare(filename, raw)
            workbook_name = PurePosixPath(filename).stem or filename
            metadata = analysis.analyze(twb_bytes, workbook_name, raw, packaging)
            job = store.create(sid, filename, twb_bytes, len(raw), packaging)
            job.metadata = metadata.to_api()
            job.status = "parsed"
            results.append({**job.summary(), "ok": True})
        except (UploadError, ParseError) as exc:
            results.append({"filename": filename, "ok": False, "error": str(exc)})

    return {"sessionId": sid, "jobs": results}


@router.get("/jobs")
def list_jobs(response: Response, x_session_id: str | None = Header(default=None)) -> dict:
    sid = _resolve_session(response, x_session_id)
    return {"sessionId": sid, "jobs": [j.summary() for j in store.list(sid)]}


@router.get("/jobs/{job_id}")
def get_job(
    response: Response, job_id: str, x_session_id: str | None = Header(default=None)
) -> dict:
    sid = _resolve_session(response, x_session_id)
    job = store.get(sid, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    return {**job.summary(), "metadata": job.metadata}


@router.post("/jobs/{job_id}/dax")
def suggest_dax_conversion(
    response: Response,
    job_id: str,
    payload: dict = Body(default={}),
    x_session_id: str | None = Header(default=None),
) -> dict:
    """On-demand DAX/M conversion for one calculation (session-scoped).

    Body: ``{calcName, dataSourceIndex?, useLlm?, apiKey?, guidance?}``.

    Offline suggestions already ride in ``GET /jobs/{id}``; this route exists for
    the opt-in AI path. The ``apiKey`` is used only for this request and is never
    stored or logged; model output is returned as untrusted text (never executed).
    """
    sid = _resolve_session(response, x_session_id)
    job = store.get(sid, job_id)
    if job is None or not job.metadata:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    calc_name = (payload.get("calcName") or "").strip()
    if not calc_name:
        raise HTTPException(status_code=400, detail="calcName is required.")

    data_sources = job.metadata.get("dataSources", [])
    ds_index = payload.get("dataSourceIndex")
    calc = None
    search = [data_sources[ds_index]] if isinstance(ds_index, int) and 0 <= ds_index < len(data_sources) else data_sources
    for ds in search:
        calc = next((c for c in ds.get("calculations", []) if c.get("name") == calc_name), None)
        if calc:
            break
    if calc is None:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    ctx = context_from_api(job.metadata)
    suggestion = suggest_dax(
        name=calc["name"],
        formula=calc.get("formula", ""),
        categories=calc.get("categories", []),
        ctx=ctx,
        use_llm=bool(payload.get("useLlm")),
        api_key=payload.get("apiKey"),
        guidance=payload.get("guidance"),
    )
    return {"calcName": calc_name, "suggestion": suggestion}


@router.post("/jobs/{job_id}/rationalization/ai-review")
def rationalization_review(
    response: Response,
    job_id: str,
    payload: dict = Body(default={}),
    x_session_id: str | None = Header(default=None),
) -> dict:
    """On-demand AI Rationalization Review (session-scoped).

    Body: ``{useLlm?, apiKey?, guidance?}``. The deterministic report already rides
    in ``GET /jobs/{id}``; this route adds the optional narrative review. The
    ``apiKey`` is used only for this request and is never stored or logged; model
    output is returned as untrusted text (never executed).
    """
    sid = _resolve_session(response, x_session_id)
    job = store.get(sid, job_id)
    if job is None or not job.metadata:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    report = job.metadata.get("rationalization")
    if not report:
        raise HTTPException(status_code=404, detail="No rationalization report for this workbook.")

    result = rationalization_ai_review(
        report,
        use_llm=bool(payload.get("useLlm")),
        api_key=payload.get("apiKey"),
        guidance=payload.get("guidance"),
    )
    return {"review": result}


def _build_pbip_model(job, payload: dict):
    """Convert the job's stored .twb into a PBIP model + files.

    Offline rule-based DAX runs always; the LLM path is used only when the user
    enables AI and supplies a key. The key is read for this request only and is
    never stored or logged; model output is treated as untrusted (the generator
    validates structure and flags calcs that need review).
    """
    xml_bytes = store.workbook_bytes(job)
    try:
        return pbip_converter.convert(
            xml_bytes,
            job.filename or "Migrated.twb",
            use_llm=bool(payload.get("useLlm")),
            api_key=payload.get("apiKey"),
        )
    except Exception as exc:  # parser/generator failure -> unprocessable, not 500
        raise HTTPException(status_code=422, detail=f"Could not generate PBIP: {exc}")


@router.post("/jobs/{job_id}/pbip/preview")
def pbip_preview(
    response: Response,
    job_id: str,
    payload: dict = Body(default={}),
    x_session_id: str | None = Header(default=None),
) -> dict:
    """Preview what the PBIP generation will produce (session-scoped).

    Body: ``{useLlm?, apiKey?}``. Returns the migration summary (tables,
    relationships, calc->DAX with review flags, warnings) so the UI can show the
    result before downloading. Offline by default; ``apiKey`` is memory-only.
    """
    sid = _resolve_session(response, x_session_id)
    job = store.get(sid, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    model, _ = _build_pbip_model(job, payload)
    return {"summary": pbip_converter.summary(model)}


@router.post("/jobs/{job_id}/pbip")
def generate_pbip(
    response: Response,
    job_id: str,
    payload: dict = Body(default={}),
    x_session_id: str | None = Header(default=None),
) -> StreamingResponse:
    """Generate an openable Power BI (PBIP) project as a .zip (session-scoped).

    Body: ``{useLlm?, apiKey?}``. Offline rule-based DAX by default; the AI path
    is opt-in and the key is used for this request only (never stored/logged).
    """
    sid = _resolve_session(response, x_session_id)
    job = store.get(sid, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    model, files = _build_pbip_model(job, payload)
    zip_bytes = pbip_converter.to_zip(files)
    filename = _safe_filename(model.name) + ".pbip.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(zip_bytes), media_type="application/zip", headers=headers)


def _safe_filename(name: str) -> str:
    """Sanitize a name for use in a Content-Disposition filename."""
    return re.sub(r'[<>:"/\\|?*\r\n]', "_", name).strip() or "custom_sql"


@router.get("/jobs/{job_id}/customsql/{ds_index}/{sql_index}")
def download_custom_sql(
    response: Response,
    job_id: str,
    ds_index: int,
    sql_index: int,
    x_session_id: str | None = Header(default=None),
) -> StreamingResponse:
    """Download one Custom SQL statement as a .sql attachment (session-scoped)."""
    sid = _resolve_session(response, x_session_id)
    job = store.get(sid, job_id)
    if job is None or not job.metadata:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    data_sources = job.metadata.get("dataSources", [])
    if not (0 <= ds_index < len(data_sources)):
        raise HTTPException(status_code=404, detail="Data source not found.")
    statements = data_sources[ds_index].get("customSql", [])
    if not (0 <= sql_index < len(statements)):
        raise HTTPException(status_code=404, detail="Custom SQL not found.")

    stmt = statements[sql_index]
    sql_text = (stmt.get("sql") or "").encode("utf-8")
    filename = _safe_filename(stmt.get("name") or "custom_sql") + ".sql"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(sql_text), media_type="application/sql", headers=headers)


_EXPORTS = {
    "json": (json_export.build_json, "application/json", "json"),
    "csv": (csv_export.build_columns_csv, "text/csv", "csv"),
    "xlsx": (excel.build_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "pdf": (pdf.build_pdf, "application/pdf", "pdf"),
}


@router.get("/jobs/{job_id}/export")
def export_job(
    response: Response,
    job_id: str,
    format: str = Query("json"),
    x_session_id: str | None = Header(default=None),
) -> StreamingResponse:
    """Export the analyzed metadata as JSON / CSV / Excel / PDF (session-scoped)."""
    sid = _resolve_session(response, x_session_id)
    job = store.get(sid, job_id)
    if job is None or not job.metadata:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    builder = _EXPORTS.get(format.lower())
    if builder is None:
        raise HTTPException(status_code=400, detail="Unsupported format (use json, csv, xlsx or pdf).")

    build, media_type, ext = builder
    data = build(job.metadata)
    filename = f"{_safe_filename(job.metadata.get('name') or 'workbook')}-inventory.{ext}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(data), media_type=media_type, headers=headers)


@router.delete("/jobs/{job_id}")
def delete_job(
    response: Response, job_id: str, x_session_id: str | None = Header(default=None)
) -> dict:
    sid = _resolve_session(response, x_session_id)
    if not store.delete(sid, job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"ok": True}
