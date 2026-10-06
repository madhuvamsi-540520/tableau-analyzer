"""Tableau Analysis Tool — FastAPI entry point.

Phase A: upload + session-scoped job store for .twb / .twbx files. Parsing,
metadata, classification, assessment, and exports arrive in later phases.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import jobs
from .core import config

app = FastAPI(title="Tableau Analysis Tool API", version="0.1.0")

# Strict CORS allowlist (never "*"); credentials are not used (session id is a
# header, not a cookie), and X-Session-Id is exposed so the browser can read it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

app.include_router(jobs.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "tableau-analyzer", "version": app.version}


# --- Static SPA hosting (production container only) ------------------------ #
# The container copies the built Vite bundle to /app/static. When that exists
# the API also serves the SPA, so the browser sees a single origin. In local
# dev the directory is absent and this block is skipped (Vite serves the UI).
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        """Serve real files when they exist, else index.html for client routes.

        Registered after the API router, so /api/* never reaches here. The
        resolve()/relative_to() check keeps a crafted path from escaping
        STATIC_DIR.
        """
        if full_path:
            candidate = (STATIC_DIR / full_path).resolve()
            try:
                candidate.relative_to(STATIC_DIR)
            except ValueError:
                raise HTTPException(status_code=404)
            if candidate.is_file():
                return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
