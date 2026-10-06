"""Central configuration for the Tableau Analysis Tool backend.

Values are read from the environment where useful (deployment overrides) and
otherwise fall back to safe defaults. Size and zip guards exist to fail closed
against resource-exhaustion / zip-bomb attacks on untrusted uploads.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ---- Upload size limits (bytes) ------------------------------------------- #
# A .twb is XML only; a .twbx bundles data, so it gets a larger ceiling.
MAX_TWB_BYTES = _int_env("ANALYZER_MAX_TWB_BYTES", 50 * 1024 * 1024)        # 50 MB
MAX_TWBX_BYTES = _int_env("ANALYZER_MAX_TWBX_BYTES", 500 * 1024 * 1024)     # 500 MB

# ---- Safe-unzip guards for .twbx (zip-bomb / zip-slip defense) ------------ #
MAX_ZIP_ENTRIES = _int_env("ANALYZER_MAX_ZIP_ENTRIES", 10_000)
MAX_UNZIP_TOTAL_BYTES = _int_env("ANALYZER_MAX_UNZIP_TOTAL_BYTES", 1024 * 1024 * 1024)  # 1 GB
MAX_ENTRY_BYTES = _int_env("ANALYZER_MAX_ENTRY_BYTES", 500 * 1024 * 1024)               # 500 MB

# ---- Job lifecycle -------------------------------------------------------- #
JOB_TTL_SECONDS = _int_env("ANALYZER_JOB_TTL", 3600)  # uploaded artifacts expire after 1h

# ---- Sandboxed storage root (random per-job subdirectory) ----------------- #
STORAGE_ROOT = Path(
    os.environ.get("ANALYZER_STORAGE", Path(tempfile.gettempdir()) / "tableau-analyzer" / "jobs")
)

# ---- CORS allowlist (never "*"; dev frontends by default) ----------------- #
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ANALYZER_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

# ---- File-type classification -------------------------------------------- #
ALLOWED_EXTENSIONS = {".twb", ".twbx"}
FLAT_FILE_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".csv", ".txt"}
EXTRACT_EXTENSIONS = {".hyper", ".tde"}
