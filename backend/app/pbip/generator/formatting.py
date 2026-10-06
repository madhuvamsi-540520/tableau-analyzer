"""Low-level formatting helpers that make generated PBIP files byte-identical to
what Power BI Desktop writes.

Ground truth captured from the hand-authored reference project:
  * Every text file uses CRLF line endings.
  * JSON  : 2-space indent, ``$schema`` first key, NO trailing newline.
  * TMDL  : TAB indent (one tab per nesting level), ONE trailing blank line.
  * M body: ``let``/``in`` at 4 tabs; inner ``let`` steps at 4 tabs + 4 spaces.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

CRLF = "\r\n"
TAB = "\t"

# Indentation used inside a partition's M expression (verified via od -c).
M_LET_INDENT = TAB * 4          # `let`, `in`, and the return line sit at 4 tabs
M_STEP_INDENT = TAB * 4 + " " * 4   # each `let` step assignment: 4 tabs + 4 spaces


def new_guid() -> str:
    """A fresh lowercase GUID (matches Desktop's lineageTag / logicalId format)."""
    return str(uuid.uuid4())


def render_json(obj: Any) -> str:
    """Serialize ``obj`` exactly like the reference JSON files: 2-space indent,
    CRLF line endings, and no trailing newline."""
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    return text.replace("\n", CRLF)


def render_tmdl(lines: list[str]) -> str:
    """Join TMDL content lines with CRLF and append the single trailing blank
    line that Desktop emits (file ends with ``...\\r\\n\\r\\n``)."""
    return "".join(line + CRLF for line in lines) + CRLF


def encode(text: str) -> bytes:
    """UTF-8 bytes (no BOM) for writing to disk / zipping."""
    return text.encode("utf-8")


def quote_tmdl_name(name: str) -> str:
    """Quote a TMDL object name when it is not a bare identifier.

    Desktop leaves simple identifiers bare (``Id``, ``Cost``) but single-quotes
    names containing a dot, space, or other special characters (``'P.ID'``).
    """
    if name and all(c.isalnum() or c == "_" for c in name) and not name[0].isdigit():
        return name
    return "'" + name.replace("'", "''") + "'"
