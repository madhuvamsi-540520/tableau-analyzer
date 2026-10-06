"""Report similarity + clustering.

Worksheet similarity is a weighted Jaccard over the feature vectors (measures,
dimensions, data sources, visual type, filters). Dashboards are compared on their
member-worksheet sets and the union of the measures/dimensions those worksheets
expose. Highly similar reports are grouped into clusters with a union-find
(disjoint-set) so an O(n^2) pairwise pass collapses into O(n α(n)) clustering —
the clusters drive the consolidation recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass

# Similarity thresholds (percent). Below REVIEW nothing is reported.
DUPLICATE = 90
CONSOLIDATE = 75
REVIEW = 60
CLUSTER = 75          # membership threshold for a consolidation cluster

# Weights for the worksheet feature blend (sum = 1.0).
_W_MEASURES = 0.34
_W_DIMENSIONS = 0.28
_W_DATASOURCE = 0.14
_W_VIZTYPE = 0.10
_W_FILTERS = 0.14


def _jaccard(a: frozenset | set, b: frozenset | set) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _recommendation(score: int, kind: str) -> str:
    if score >= DUPLICATE:
        return "Merge into a single report" if kind == "worksheet" else "Merge into a single dashboard"
    if score >= CONSOLIDATE:
        return "Consolidate using parameterized / dynamic filters"
    return "Review for rationalization"


def worksheet_similarity(a, b) -> tuple[int, float]:
    """Return (similarity 0..100, confidence 0..1) for two worksheet features.

    Weights are renormalized over only the components that carry data on at least
    one side, so a channel both sheets leave empty (e.g. no filters) neither
    inflates nor deflates the score."""
    if a.field_count == 0 and b.field_count == 0:
        return 0, 0.3  # no evidence to compare on

    # (weight, value, applicable)
    components = [
        (_W_MEASURES, _jaccard(a.measures, b.measures), bool(a.measures or b.measures)),
        (_W_DIMENSIONS, _jaccard(a.dimensions, b.dimensions), bool(a.dimensions or b.dimensions)),
        (_W_DATASOURCE, _jaccard(a.data_sources, b.data_sources), bool(a.data_sources or b.data_sources)),
        (_W_VIZTYPE, 1.0 if a.viz_type == b.viz_type and a.viz_type != "Unknown" else 0.0, True),
        (_W_FILTERS, _jaccard(a.filters, b.filters), bool(a.filters or b.filters)),
    ]
    applied = sum(w for w, _, ok in components if ok) or 1.0
    score = sum(w * v for w, v, ok in components if ok) / applied

    # Confidence reflects how much evidence backs the score (sparse sheets → lower).
    evidence = min(a.field_count, b.field_count)
    confidence = round(min(1.0, 0.45 + 0.11 * evidence), 2)
    return round(score * 100), confidence


def _dashboard_vectors(dash, ws_by_name):
    sheets = set(dash.worksheets)
    measures: set[str] = set()
    dimensions: set[str] = set()
    for name in dash.worksheets:
        f = ws_by_name.get(name)
        if f:
            measures |= set(f.measures)
            dimensions |= set(f.dimensions)
    return sheets, measures, dimensions


def dashboard_similarity(a, b, ws_by_name) -> tuple[int, float]:
    sa, ma, da = _dashboard_vectors(a, ws_by_name)
    sb, mb, db = _dashboard_vectors(b, ws_by_name)
    score = (
        0.50 * _jaccard(sa, sb)
        + 0.30 * _jaccard(ma, mb)
        + 0.20 * _jaccard(da, db)
    )
    evidence = min(len(sa), len(sb))
    confidence = round(min(1.0, 0.5 + 0.12 * evidence), 2)
    return round(score * 100), confidence


class _UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def groups(self) -> dict:
        out: dict = {}
        for item in self.parent:
            out.setdefault(self.find(item), []).append(item)
        return out


def _shared(a, b) -> dict:
    return {
        "measures": sorted(a.measures & b.measures),
        "dimensions": sorted(a.dimensions & b.dimensions),
    }


def analyze_similarity(ctx) -> dict:
    ws = ctx.worksheets
    ws_pairs = []
    for i in range(len(ws)):
        for j in range(i + 1, len(ws)):
            score, conf = worksheet_similarity(ws[i], ws[j])
            if score >= REVIEW:
                shared = _shared(ws[i], ws[j])
                ws_pairs.append({
                    "type": "worksheet",
                    "a": ws[i].name, "b": ws[j].name,
                    "similarity": score, "confidence": conf,
                    "recommendation": _recommendation(score, "worksheet"),
                    "sharedMeasures": shared["measures"],
                    "sharedDimensions": shared["dimensions"],
                    "vizA": ws[i].viz_type, "vizB": ws[j].viz_type,
                })

    dash = ctx.dashboards
    dash_pairs = []
    for i in range(len(dash)):
        for j in range(i + 1, len(dash)):
            score, conf = dashboard_similarity(dash[i], dash[j], ctx.ws_by_name)
            if score >= REVIEW:
                dash_pairs.append({
                    "type": "dashboard",
                    "a": dash[i].name, "b": dash[j].name,
                    "similarity": score, "confidence": conf,
                    "recommendation": _recommendation(score, "dashboard"),
                    "sharedWorksheets": sorted(set(dash[i].worksheets) & set(dash[j].worksheets)),
                })

    clusters = _build_clusters(dash, dash_pairs) + _build_ws_clusters(ws, ws_pairs)

    pairs = sorted(dash_pairs + ws_pairs, key=lambda p: -p["similarity"])
    # Distinct reports involved in a strong (consolidate-or-higher) overlap — the
    # basis for the estate-relative rationalization score.
    redundant = {p["a"] for p in pairs if p["similarity"] >= CONSOLIDATE}
    redundant |= {p["b"] for p in pairs if p["similarity"] >= CONSOLIDATE}
    return {
        "pairs": pairs,
        "clusters": clusters,
        "duplicateCount": sum(1 for p in pairs if p["similarity"] >= DUPLICATE),
        "similarCount": sum(1 for p in pairs if CONSOLIDATE <= p["similarity"] < DUPLICATE),
        "reviewCount": sum(1 for p in pairs if REVIEW <= p["similarity"] < CONSOLIDATE),
        "redundantReports": len(redundant),
    }


def _build_clusters(items, pairs) -> list[dict]:
    names = [d.name for d in items]
    uf = _UnionFind(names)
    strong = [p for p in pairs if p["similarity"] >= CLUSTER]
    for p in strong:
        uf.union(p["a"], p["b"])
    clusters = []
    for members in uf.groups().values():
        if len(members) < 2:
            continue
        rel = [p for p in strong if p["a"] in members and p["b"] in members]
        avg = round(sum(p["similarity"] for p in rel) / len(rel)) if rel else CLUSTER
        clusters.append({
            "type": "dashboard",
            "members": sorted(members),
            "size": len(members),
            "avgSimilarity": avg,
            "recommendation": f"Consolidate {len(members)} dashboards into 1 parameterized dashboard",
            "rationale": "These dashboards share most worksheets and KPIs; a single parameter- or "
                         "filter-driven dashboard removes the duplicates.",
        })
    return clusters


def _build_ws_clusters(items, pairs) -> list[dict]:
    names = [w.name for w in items]
    uf = _UnionFind(names)
    strong = [p for p in pairs if p["similarity"] >= DUPLICATE]
    for p in strong:
        uf.union(p["a"], p["b"])
    clusters = []
    for members in uf.groups().values():
        if len(members) < 2:
            continue
        clusters.append({
            "type": "worksheet",
            "members": sorted(members),
            "size": len(members),
            "avgSimilarity": DUPLICATE,
            "recommendation": f"Keep one worksheet and reuse it — {len(members) - 1} are near-duplicates",
            "rationale": "Near-identical worksheets should be built once and reused across dashboards.",
        })
    return clusters
