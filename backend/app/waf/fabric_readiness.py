"""Microsoft Fabric Readiness pillar (heuristic from connection types + storage)."""
from __future__ import annotations

from .base import Pillar
from .pillar import Check, PillarResult, score_from_checks

# Friendly connection types that map well to a warehouse / Direct Lake path.
_WAREHOUSE = {"SQL Server", "Snowflake", "Azure Synapse", "Google BigQuery", "Amazon Redshift",
              "PostgreSQL", "Databricks", "Azure SQL", "Oracle", "Teradata"}
_FILE = {"Excel", "CSV", "Text File", "JSON"}


class FabricReadinessPillar(Pillar):
    key = "fabricReadiness"
    name = "Fabric Readiness"
    weight = 0.05

    def analyze(self, ctx) -> PillarResult:
        friendly = {c.friendly_type for ds in ctx.wb.data_sources for c in ds.connections}
        has_wh = bool(friendly & _WAREHOUSE)
        has_file = bool(friendly & _FILE)
        has_extract = any(c.is_extract for ds in ctx.wb.data_sources for c in ds.connections)

        checks = [
            Check(
                id="direct-lake",
                title="Direct Lake / Warehouse suitability",
                status="pass" if has_wh else "warn",
                severity="info" if has_wh else "low",
                metric=", ".join(sorted(friendly & _WAREHOUSE)) or "no warehouse source",
                detail=("Warehouse/database sources can land in OneLake for Direct Lake or a Fabric Warehouse."
                        if has_wh else "No warehouse/database source detected."),
                recommendation="Target a Lakehouse/Warehouse and consider Direct Lake for large models." if has_wh
                               else "Consolidate file sources into a Lakehouse for Fabric.",
                benefit="Import-free, near-real-time semantic models at scale.",
            ),
            Check(
                id="dataflows",
                title="Dataflow Gen2 opportunities",
                status="warn" if has_file else "pass",
                severity="low" if has_file else "info",
                metric=", ".join(sorted(friendly & _FILE)) or "no file sources",
                detail=("File-based sources are good candidates for Dataflows Gen2 into OneLake."
                        if has_file else "No file-based sources requiring dataflows."),
                recommendation="Ingest file sources via Dataflow Gen2 / pipelines into a Lakehouse." if has_file else "",
                benefit="Reusable, governed ingestion.",
            ),
            Check(
                id="storage-mode",
                title="Storage mode",
                status="pass",
                severity="info",
                metric="Extract present" if has_extract else "Live/DirectQuery",
                detail=("Extracts map to Import mode; evaluate Direct Lake for freshness at scale."
                        if has_extract else "Live connections map to DirectQuery or Direct Lake."),
                recommendation="Pick Import / DirectQuery / Direct Lake per freshness and volume needs.",
                benefit="Right storage mode balances performance and freshness.",
            ),
        ]

        score = score_from_checks(checks, base=80 if has_wh else 65)
        summary = f"Sources: {', '.join(sorted(friendly)) or '—'}."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


PILLAR = FabricReadinessPillar()
