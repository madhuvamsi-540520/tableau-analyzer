"""Dashboard & Worksheet Rationalization module.

Deterministic (offline) engine that identifies redundant/overlapping reports,
recommends consolidation, and audits visualization best practices — with a
pluggable, opt-in AI review seam. See :mod:`engine` for the entry points.
"""
from __future__ import annotations

from .engine import ai_review, run

__all__ = ["run", "ai_review"]
