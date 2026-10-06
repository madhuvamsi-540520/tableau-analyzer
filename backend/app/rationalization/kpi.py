"""Business KPI consolidation analysis.

Finds measures that recur across many worksheets/dashboards — the same KPI
rebuilt in several places — and recommends a single reusable measure / KPI
dashboard. Recurring measures are the strongest candidates for a shared semantic
layer in Power BI.
"""
from __future__ import annotations

# A measure used on this many worksheets is treated as a core, reusable KPI.
_CORE_USAGE = 3


def analyze_kpis(ctx) -> dict:
    usage: dict[str, dict] = {}
    for ws in ctx.worksheets:
        for m in ws.measures:
            entry = usage.setdefault(m, {"worksheets": set(), "dashboards": set()})
            entry["worksheets"].add(ws.name)
            entry["dashboards"].update(ws.dashboards)

    kpis = []
    for measure, entry in usage.items():
        ws_names = sorted(entry["worksheets"])
        dash_names = sorted(entry["dashboards"])
        kpis.append({
            "measure": measure,
            "worksheetCount": len(ws_names),
            "dashboardCount": len(dash_names),
            "worksheets": ws_names,
            "dashboards": dash_names,
            "core": len(ws_names) >= _CORE_USAGE,
        })
    kpis.sort(key=lambda k: (-k["worksheetCount"], k["measure"]))

    opportunities = []
    for k in kpis:
        if k["core"]:
            opportunities.append({
                "measure": k["measure"],
                "usedIn": k["worksheetCount"],
                "recommendation": f"Define '{k['measure']}' once as a shared DAX measure and reuse it "
                                  f"(used in {k['worksheetCount']} worksheets across "
                                  f"{k['dashboardCount']} dashboard(s)).",
            })

    return {
        "kpis": kpis[:50],           # cap for the UI; full set is derivable on demand
        "coreKpis": [k["measure"] for k in kpis if k["core"]],
        "opportunities": opportunities,
    }
