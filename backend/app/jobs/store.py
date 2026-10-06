"""Session-scoped, TTL-expiring job store with sandboxed on-disk storage.

Uploaded workbook bytes are written to a random per-job directory under the
configured storage root and removed on delete or expiry. Jobs are scoped to a
session id so one session can never read or delete another's jobs (IDOR
defense). In-memory registry is adequate for a single-process deployment; swap
for a shared store if scaled out.
"""
from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from typing import Optional

from ..core import config
from ..core.security import Packaging
from .models import Job


class JobStore:
    def __init__(self, storage_root: Optional[Path] = None):
        self._root = Path(storage_root or config.STORAGE_ROOT)
        self._root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(
        self,
        session_id: str,
        filename: str,
        twb_bytes: bytes,
        original_size: int,
        packaging: Packaging,
    ) -> Job:
        job = Job(session_id=session_id, filename=filename, packaging=packaging, size=original_size)
        job_dir = self._root / job.id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "workbook.twb").write_bytes(twb_bytes)
        job.storage_dir = job_dir
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, session_id: str, job_id: str) -> Optional[Job]:
        self._sweep()
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None or job.session_id != session_id or job.is_expired():
            return None
        return job

    def list(self, session_id: str) -> list[Job]:
        self._sweep()
        with self._lock:
            jobs = [j for j in self._jobs.values() if j.session_id == session_id and not j.is_expired()]
        return sorted(jobs, key=lambda j: j.created_at)

    def delete(self, session_id: str, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.session_id != session_id:
                return False
            self._jobs.pop(job_id, None)
        self._remove_files(job)
        return True

    def workbook_bytes(self, job: Job) -> bytes:
        """The stored .twb XML bytes (used by the parser layer in Phase B)."""
        return (job.storage_dir / "workbook.twb").read_bytes()

    # -- internal ----------------------------------------------------------- #

    def _sweep(self) -> None:
        now = time.time()
        with self._lock:
            expired = [self._jobs.pop(jid) for jid, j in list(self._jobs.items()) if j.is_expired(now)]
        for job in expired:
            self._remove_files(job)

    def _remove_files(self, job: Job) -> None:
        if job.storage_dir and job.storage_dir.exists():
            shutil.rmtree(job.storage_dir, ignore_errors=True)


# Module-level singleton used by the API layer.
store = JobStore()
