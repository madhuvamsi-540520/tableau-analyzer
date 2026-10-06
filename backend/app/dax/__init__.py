"""Calculation Intelligence (DAX & Formula) engine.

Modular, reusable analysis of Tableau calculations for Power BI migration:

* :mod:`references`  — dependency graph + context builders
* :mod:`performance` — deterministic cost/risk rating
* :mod:`datatypes`   — best-effort data-type inference
* :mod:`convert`     — pluggable DAX/M recommendation (offline default, optional LLM)
* :mod:`engine`      — orchestrator that enriches ``CalcMeta`` in place

Each component exposes a small, pure interface so future AI-assisted features
(bulk DAX generation, formula validation, migration automation) can build on it.
"""
from __future__ import annotations

from .convert import suggest
from .engine import enrich_calculations
from .references import context_from_api, context_from_wb

__all__ = ["enrich_calculations", "suggest", "context_from_api", "context_from_wb"]
