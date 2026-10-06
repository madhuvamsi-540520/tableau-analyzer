"""Pillar interface for the plugin-based rule engine.

Each analyzer subclasses :class:`Pillar` and is registered in the engine's
REGISTRY. New pillars are added by writing a new module and appending one entry —
existing pillars are never modified (Open/Closed Principle).
"""
from __future__ import annotations

from .context import WafContext
from .pillar import PillarResult


class Pillar:
    key: str = ""
    name: str = ""
    weight: float = 0.0        # contribution to the overall score (registry weights sum to 1.0)

    def analyze(self, ctx: WafContext) -> PillarResult:  # pragma: no cover - interface
        raise NotImplementedError
