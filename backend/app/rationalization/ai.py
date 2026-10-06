"""Pluggable AI Rationalization Review — offline by default, LLM on demand.

Same seam as the DAX module: the deterministic engine always produces the full
report; this adds an optional narrative executive review. The offline backend
composes a deterministic summary from the computed findings (no network). The LLM
backend is opt-in, enabled per-request with a key kept in memory only (never
stored or logged); its output is returned as untrusted text and never executed.
"""
from __future__ import annotations

import os

_METHOD_OFFLINE = "offline-summary"
_METHOD_LLM = "llm"


def _offline_review(report: dict) -> dict:
    ex = report.get("executiveSummary", {})
    sim = report.get("similarity", {})
    cons = report.get("consolidation", {})
    viz = report.get("vizQuality", {})
    lines = [
        f"Rationalization score {ex.get('rationalizationScore')}/100; "
        f"visualization quality {ex.get('vizQualityScore')}/100.",
        f"{sim.get('duplicateCount', 0)} duplicate and {sim.get('similarCount', 0)} similar "
        f"report pairs detected across {ex.get('totalDashboards', 0)} dashboards and "
        f"{ex.get('totalWorksheets', 0)} worksheets.",
        f"Consolidation could remove ~{cons.get('estimatedDashboardReduction', 0)} dashboard(s) "
        f"(~{cons.get('estimatedEffortReductionHours', 0)}h migration effort, "
        f"~{cons.get('estimatedMaintenanceSavingsPct', 0)}% maintenance saving).",
        f"{viz.get('issueCount', 0)} visualization best-practice issues "
        f"({viz.get('highSeverityCount', 0)} high severity).",
    ]
    return {
        "method": _METHOD_OFFLINE,
        "available": True,
        "summary": " ".join(lines),
        "notes": ["Deterministic summary of the offline analysis. Enable AI for a narrative review."],
    }


def _make_client(api_key: str | None):
    key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, "AI review is on but no API key was provided (paste one, or set ANTHROPIC_API_KEY)."
    try:
        import anthropic  # noqa: WPS433 (optional dependency)

        return anthropic.Anthropic(api_key=key), None
    except Exception as exc:  # pragma: no cover - environment dependent
        return None, f"Anthropic SDK not available ({exc})."


_MODEL_ID = "claude-opus-4-8"
_SYSTEM = (
    "You are an expert BI architect advising on rationalizing a Tableau estate before "
    "migration to Power BI. You are given a DETERMINISTIC analysis (similarity clusters, "
    "consolidation opportunities, visualization issues, dashboard quality). Write a concise, "
    "prioritized executive review: what to consolidate first and why, the biggest visualization "
    "risks, and the expected effort/maintenance payoff. Do not invent numbers — use only the "
    "figures provided. Reply in short markdown bullets, no preamble."
)


def _llm_review(report: dict, api_key: str | None, guidance: dict | None) -> dict:
    out = {"method": _METHOD_LLM, "available": False, "summary": "", "notes": []}
    client, err = _make_client(api_key)
    if client is None:
        out["notes"].append(err)
        return out

    ex = report.get("executiveSummary", {})
    payload = {
        "executiveSummary": ex,
        "similarity": {k: report.get("similarity", {}).get(k)
                       for k in ("duplicateCount", "similarCount", "clusters")},
        "consolidation": report.get("consolidation", {}).get("recommendations", [])[:10],
        "vizQuality": {k: report.get("vizQuality", {}).get(k)
                       for k in ("score", "issueCount", "highSeverityCount")},
        "topVizIssues": report.get("vizQuality", {}).get("issues", [])[:8],
    }
    hint = ""
    if guidance:
        hl = [f"- {k}: {str(v).strip()}" for k, v in guidance.items() if str(v).strip()]
        if hl:
            hint = "\nUser focus:\n" + "\n".join(hl)
    try:
        resp = client.messages.create(
            model=_MODEL_ID,
            max_tokens=900,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Analysis JSON:\n{payload}{hint}"}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
    except Exception as exc:  # pragma: no cover - network/SDK dependent
        out["notes"].append(f"AI review failed: {type(exc).__name__}: {exc}")
        return out

    if not text:
        out["notes"].append("Model returned no content.")
        return out
    out["available"] = True
    out["summary"] = text
    out["notes"].append("AI-generated — validate before acting.")
    return out


def review(report: dict, *, use_llm: bool = False, api_key: str | None = None,
           guidance: dict | None = None) -> dict:
    """Facade: deterministic summary by default, LLM narrative when opted in."""
    if use_llm:
        return _llm_review(report, api_key, guidance)
    return _offline_review(report)
