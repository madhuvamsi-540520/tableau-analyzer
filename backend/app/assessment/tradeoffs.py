"""Technical trade-offs: neutral analysis of the balances this workbook strikes."""
from __future__ import annotations

from .finding import Tradeoff


def analyze(wb) -> list[Tradeoff]:
    cx = wb.complexity()
    modes = sorted({ds.connection_mode for ds in wb.data_sources}) or ["—"]
    models = sorted({ds.classification.get("type", "") for ds in wb.data_sources if ds.classification})

    return [
        Tradeoff(
            "Live vs Extract",
            ", ".join(modes),
            "Live gives fresh data but depends on source latency; Extract is fast but stale and adds storage/refresh.",
            "Use Extract for large/slow sources and interactive dashboards; use Live when freshness is critical.",
        ),
        Tradeoff(
            "Simplicity vs Flexibility",
            ", ".join(m for m in models) or "—",
            "Flat/denormalized models are simple and fast but rigid; normalized/snowflake models are flexible but complex.",
            "A star schema balances the two — simple to query while preserving analytical flexibility.",
        ),
        Tradeoff(
            "Performance vs Maintainability",
            f"{cx['joins']} joins, {cx['calculatedFields']} calcs, {cx['customSql']} custom SQL",
            "Extra joins, calculations and custom SQL can tune performance but raise maintenance cost and risk.",
            "Push heavy logic into the warehouse; keep the semantic model lean and documented.",
        ),
        Tradeoff(
            "Denormalization",
            f"{cx['tables']} table(s)",
            "Wide denormalized tables reduce joins (faster) but duplicate data and complicate updates.",
            "Denormalize dimensions moderately; keep fact tables at a single, clear grain.",
        ),
    ]
