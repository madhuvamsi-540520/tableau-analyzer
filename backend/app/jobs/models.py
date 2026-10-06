"""The Job record: one uploaded workbook, its packaging, and its lifecycle."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core import config
from ..core.security import Packaging


@dataclass
class Job:
    session_id: str
    filename: str
    packaging: Packaging
    id: str = field(default_factory=lambda: uuid.uuid4().hex)  # non-guessable job id
    status: str = "uploaded"            # uploaded | parsed | error
    error: Optional[str] = None
    size: int = 0                       # bytes of the original upload
    created_at: float = field(default_factory=time.time)
    storage_dir: Optional[Path] = None
    metadata: Optional[dict] = None     # parsed WorkbookMetadata.to_api()

    @property
    def expires_at(self) -> float:
        return self.created_at + config.JOB_TTL_SECONDS

    def is_expired(self, now: Optional[float] = None) -> bool:
        return (now if now is not None else time.time()) >= self.expires_at

    def summary(self) -> dict:
        """Client-facing view (no filesystem paths, no session id)."""
        p = self.packaging
        return {
            "jobId": self.id,
            "filename": self.filename,
            "kind": p.kind,
            "status": self.status,
            "error": self.error,
            "size": self.size,
            "createdAt": self.created_at,
            "expiresAt": self.expires_at,
            "counts": (self.metadata or {}).get("counts"),
            "packaging": {
                "kind": p.kind,
                "innerTwb": p.inner_twb_name,
                "flatFiles": p.flat_files,
                "extracts": p.extracts,
                "hasExtract": p.has_extract,
            },
        }
