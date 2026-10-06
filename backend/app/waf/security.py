"""Security & RLS pillar (PII reuse + heuristic RLS suggestions)."""
from __future__ import annotations

import re

from .base import Pillar
from .pillar import Check, PillarResult, score_from_checks
from .util import check_from_finding

# Dimension columns that typically drive row-level security.
_RLS_HINT = re.compile(r"\b(region|territory|country|state|department|dept|division|branch|store|"
                       r"manager|owner|team|business\s*unit|org|company|customer\s*group)\b", re.I)
_PII = re.compile(r"\b(email|e-mail|phone|ssn|passport|dob|birth|address|credit\s*card|iban|"
                  r"salary|national\s*id|tax\s*id)\b", re.I)


class SecurityPillar(Pillar):
    key = "security"
    name = "Security & RLS"
    weight = 0.10

    def analyze(self, ctx) -> PillarResult:
        checks: list[Check] = []

        # 1. PII — reuse governance PII findings, plus a name scan. ---------- #
        gov = ctx.assessment.get("governance", []) or []
        pii_findings = [f for f in gov if "PII" in (f.get("title") or "")]
        pii_cols = [f"{t.name}.{c.name}" for t in ctx.tables for c in t.columns if _PII.search(c.name or "")]
        if pii_findings:
            checks.append(check_from_finding(pii_findings[0]))
        checks.append(Check(
            id="pii-columns",
            title="Sensitive / PII columns",
            status="warn" if pii_cols else "pass",
            severity="high" if pii_cols else "info",
            metric=f"{len(pii_cols)} candidate PII column(s)",
            detail=("Potential PII (by name): " + ", ".join(pii_cols[:12])) if pii_cols else
                   "No obvious PII columns detected by name.",
            recommendation=("Classify with sensitivity labels, restrict via OLS, and mask where required."
                            if pii_cols else ""),
            benefit="Regulatory compliance (GDPR/PII handling).",
            evidence=pii_cols[:20],
        ))

        # 2. RLS candidates -------------------------------------------------- #
        rls_cols = sorted({c.name for t in ctx.tables for c in t.columns
                           if c.role == "dimension" and _RLS_HINT.search(c.name or "")})
        checks.append(Check(
            id="rls-candidates",
            title="Row-Level Security scope",
            status="warn" if rls_cols else "na",
            severity="medium" if rls_cols else "info",
            metric=f"{len(rls_cols)} candidate dimension(s)",
            detail=("Dimensions that commonly need RLS: " + ", ".join(rls_cols)) if rls_cols else
                   "No obvious RLS-driving dimensions found (limited by available metadata).",
            recommendation=("Define RLS roles on these dimensions (e.g. per region/department/manager) "
                            "and validate with 'View as role'." if rls_cols else
                            "Confirm security requirements with stakeholders."),
            benefit="Enforces least-privilege data access per user.",
            evidence=rls_cols[:20],
        ))

        # 3. Metadata limitation note --------------------------------------- #
        checks.append(Check(
            id="security-scope-note",
            title="Workspace/gateway/credential review",
            status="na", severity="info",
            detail="Workspace permissions, gateways, service principals and credential storage are "
                   "deployment-time concerns not present in the Tableau workbook.",
            recommendation="Review during Power BI deployment (covered further after PBIP generation).",
        ))

        score = score_from_checks(checks)
        summary = f"{len(pii_cols)} candidate PII column(s); {len(rls_cols)} RLS-driving dimension(s)."
        return PillarResult(self.key, self.name, score, self.weight, summary, checks)


PILLAR = SecurityPillar()
