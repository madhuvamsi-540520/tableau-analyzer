"""Export the full workbook metadata as pretty JSON."""
from __future__ import annotations

import json


def build_json(metadata: dict) -> bytes:
    return json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8")
