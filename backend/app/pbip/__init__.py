"""PBIP generation core, ported verbatim from the parked ``tableau-to-pbip-app``.

This is a self-contained sub-package: its modules import each other with
relative imports (``from ..model.ir import Model``), so it never collides with
the analyzer's own ``app.parser`` / ``app.model`` / ``app.report`` packages.

It turns a Tableau ``.twb`` (XML bytes) into an openable Power BI ``.pbip``
project via ``converter.convert`` + ``converter.to_zip``. Offline rule-based
DAX runs always; the LLM path is optional and used only when a per-request API
key is supplied (it degrades gracefully when unavailable).
"""
from . import converter

__all__ = ["converter"]
