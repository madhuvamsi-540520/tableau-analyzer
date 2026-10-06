"""Well-Architected Power BI Framework — deterministic architecture advisor.

A plugin-based rule engine that scores a would-be Power BI solution across
pillars (data model, DAX, performance, security, governance, semantic-model
readiness, technical debt, Fabric readiness, migration risk) and produces an
executive scorecard, quick wins and a prioritized remediation roadmap. Reuses
the existing assessment/migration/DAX outputs — single source of truth.
"""
from __future__ import annotations

from .engine import run

__all__ = ["run"]
