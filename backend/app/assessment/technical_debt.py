"""Technical-debt analyzer: duplicate tables/calcs, circular/excessive joins, hardcoded filters, redundant extracts."""
from __future__ import annotations

from collections import defaultdict

from .constants import EXCESSIVE_JOINS
from .finding import Finding, HIGH, LOW, MEDIUM
from .util import find_cycles


def analyze(wb) -> list[Finding]:
    findings: list[Finding] = []

    # Duplicate tables (identical column-name signature).
    sigs: dict[tuple, list[str]] = defaultdict(list)
    for ds in wb.data_sources:
        for t in ds.tables:
            sig = tuple(sorted(c.original_name.lower() for c in t.columns))
            if len(sig) >= 2:
                sigs[sig].append(f"{ds.caption or ds.name}.{t.name}")
    for locs in sigs.values():
        if len(locs) > 1:
            findings.append(Finding(
                "technical-debt", "Duplicate tables (identical column structure)", MEDIUM,
                "Redundant tables inflate the model and risk inconsistent logic.",
                "Consolidate duplicates into a single conformed table.", locs,
            ))

    for ds in wb.data_sources:
        label = ds.caption or ds.name
        # Circular joins.
        cycles = find_cycles(ds.tables, ds.relationships)
        if cycles:
            findings.append(Finding(
                "technical-debt", "Circular join path", HIGH,
                "Circular joins create ambiguous query paths and can multiply row counts.",
                "Break the cycle; keep a single unambiguous join path (star).",
                [f"{a} ↔ {b}" for a, b in cycles],
            ))
        # Excessive joins.
        joins = [r for r in ds.relationships if r.kind == "join"]
        if len(joins) > EXCESSIVE_JOINS:
            findings.append(Finding(
                "technical-debt", "Excessive joins", MEDIUM,
                "Many physical joins slow queries and complicate maintenance.",
                "Reduce joins via a star model, pre-aggregation, or an extract.",
                [f"{label}: {len(joins)} joins"],
            ))
        # Hardcoded data source filters.
        if ds.filters:
            findings.append(Finding(
                "technical-debt", "Hardcoded data source filters", LOW,
                "Baked-in filter values can silently exclude data and confuse consumers.",
                "Prefer parameters or documented, governed filters; review the values.",
                [f"{f.field}: {f.expression}" for f in ds.filters],
            ))

    # Redundant extracts.
    extracts = [ds.caption or ds.name for ds in wb.data_sources if ds.is_extract]
    if len(extracts) > 1:
        findings.append(Finding(
            "technical-debt", "Multiple extracts", LOW,
            "Several extracts duplicate storage and refresh effort.",
            "Consolidate extracts or use a shared/published extract.", extracts,
        ))

    # Duplicate calculated field names.
    calc_locs: dict[str, list[str]] = defaultdict(list)
    for ds in wb.data_sources:
        for name in ds.calculated_field_names:
            calc_locs[name.lower()].append(f"{ds.caption or ds.name}.{name}")
    for locs in calc_locs.values():
        if len(locs) > 1:
            findings.append(Finding(
                "technical-debt", "Duplicate calculated field names", LOW,
                "Duplicate calc names across data sources cause confusion and drift.",
                "Standardize into a single certified calculation.", locs,
            ))

    return findings
