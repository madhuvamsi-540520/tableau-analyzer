"""DAX Recommendation Engine — pluggable Tableau-formula -> DAX/M conversion.

Two interchangeable backends behind one ``suggest`` call:

* :class:`OfflineDaxBackend` — deterministic, rule-based, runs everywhere with no
  network. The offline rules are PORTED (not imported) from the parked converter's
  ``generator/dax_rules.py`` so the analyzer stays decoupled from that project.
  This is the default and is precomputed at parse time.
* :class:`LlmDaxBackend` — optional, on-demand only. Enabled by the user via the
  UI toggle; the Anthropic key is supplied per-request and is kept in memory only
  (never stored or logged). Degrades to a clear message when no key / no network.

The engine is intentionally conservative: it never fabricates a conversion when
the metadata is insufficient — it returns explicit ``limitations`` instead.
"""
from __future__ import annotations

import os
import re

# --------------------------------------------------------------------------- #
# Ported offline translation rules (from parked generator/dax_rules.py).
# Kept as pure functions — no dependency on any IR/Model type.
# --------------------------------------------------------------------------- #

# Tableau function name -> DAX name (others pass through unchanged).
_RENAME = {
    "AVG": "AVERAGE",
    "COUNTD": "DISTINCTCOUNT",
    "IIF": "IF",
    "ISNULL": "ISBLANK",
    "IFNULL": "COALESCE",
    "CONTAINS": "CONTAINSSTRING",
}

_LEFTOVER = ("THEN", "ELSE", "ELSEIF", "END", "Calculation_")
_FIELD_REF = re.compile(r"\[([^\]]+)\]")
_IF_BLOCK = re.compile(r"\bIF\b(.+?)\bEND\b", re.IGNORECASE | re.DOTALL)
_KW_SPLIT = re.compile(r"\b(THEN|ELSEIF|ELSE)\b", re.IGNORECASE)

# Constructs with no reliable 1:1 offline DAX form -> must be flagged, never
# emitted as confident (LOD braces, table calcs, and functions whose names would
# pass through unchanged and be wrong).
_UNSUPPORTED = re.compile(
    r"\{|\b("
    r"WINDOW_\w+|RUNNING_\w+|INDEX|RANK|RANK_\w+|FIRST|LAST|LOOKUP|TOTAL|SIZE|"
    r"PREVIOUS_VALUE|DATEPART|DATENAME|DATETRUNC|DATEADD|DATEDIFF|MAKEDATE|"
    r"SPLIT|REGEXP_\w+|PERCENTILE|MEDIAN|ATTR|ZN|RAWSQL\w*|SCRIPT_\w+"
    r")\s*\(",
    re.IGNORECASE,
)


def has_unsupported(formula: str) -> bool:
    return bool(_UNSUPPORTED.search(formula or ""))


def _quote_table(name: str) -> str:
    if name and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def _convert_if(formula: str) -> str:
    """`IF c THEN a ELSEIF d THEN e ELSE f END` -> SWITCH(TRUE(), c, a, d, e, f)."""

    def repl(match: re.Match) -> str:
        parts = _KW_SPLIT.split(match.group(1))
        seq = [parts[0].strip()]
        i = 1
        while i < len(parts):
            seq.append((parts[i].upper(), parts[i + 1].strip() if i + 1 < len(parts) else ""))
            i += 2

        args: list[str] = []
        default = "BLANK()"
        cond = seq[0]
        idx = 1
        while idx < len(seq):
            kw, val = seq[idx]
            if kw == "THEN":
                args += [cond, val]
                idx += 1
                if idx < len(seq):
                    kw2, val2 = seq[idx]
                    if kw2 == "ELSEIF":
                        cond = val2
                        idx += 1
                    elif kw2 == "ELSE":
                        default = val2
                        idx += 1
            else:
                idx += 1
        return f"SWITCH(TRUE(), {', '.join(args)}, {default})"

    return _IF_BLOCK.sub(repl, formula)


def translate(formula: str, field_lookup: dict, measures: set) -> str | None:
    """Best-effort offline Tableau->DAX. Returns None (never a guess) when a
    referenced field cannot be resolved, parens are unbalanced, or control-flow
    tokens remain unconverted."""
    s = (formula or "").strip()
    if not s:
        return None

    s = _convert_if(s)
    unknown: list[str] = []

    def resolve(m: re.Match) -> str:
        name = m.group(1)
        if name in measures:
            return f"[{name}]"
        if name in field_lookup:
            table, col = field_lookup[name]
            return f"{_quote_table(table)}[{col}]"
        unknown.append(name)
        return m.group(0)

    s = _FIELD_REF.sub(resolve, s)
    if unknown:
        return None

    for src, dst in _RENAME.items():
        s = re.sub(rf"\b{src}\s*\(", f"{dst}(", s)

    if s.count("(") != s.count(")"):
        return None
    if any(tok in s for tok in _LEFTOVER):
        return None
    return s


# --------------------------------------------------------------------------- #
# Backend interface + implementations
# --------------------------------------------------------------------------- #
_METHOD_OFFLINE = "offline-rules"
_METHOD_LLM = "llm"


def _empty_suggestion(method: str) -> dict:
    return {
        "method": method,
        "daxMeasure": None,
        "daxColumn": None,
        "powerQuery": None,
        "confidence": 0.0,
        "assumptions": [],
        "limitations": [],
    }


def _is_measure_calc(categories: list[str]) -> bool:
    """A calc that aggregates (or references a measure) becomes a DAX MEASURE;
    a purely row-level expression becomes a calculated COLUMN."""
    return any(c.startswith("Aggregation") or c.startswith("Table Calculation")
               or c.startswith("LOD") for c in (categories or []))


class DaxBackend:
    """Common interface — implementations return a suggestion dict."""

    method = "abstract"

    def suggest(self, *, name: str, formula: str, categories: list[str],
                ctx: dict, **kwargs) -> dict:  # pragma: no cover - interface
        raise NotImplementedError


class OfflineDaxBackend(DaxBackend):
    """Deterministic rules — always available, precomputed at parse time."""

    method = _METHOD_OFFLINE

    def suggest(self, *, name: str, formula: str, categories: list[str],
                ctx: dict, **kwargs) -> dict:
        out = _empty_suggestion(self.method)
        field_lookup = ctx.get("field_lookup", {})
        measures = ctx.get("measures", set())

        dax = translate(formula, field_lookup, measures)
        flagged = has_unsupported(formula)
        as_measure = _is_measure_calc(categories)

        if dax is None:
            out["confidence"] = 0.0
            if flagged:
                out["limitations"].append(
                    "Uses a construct with no reliable offline DAX form "
                    "(LOD {FIXED/INCLUDE/EXCLUDE}, table calc such as WINDOW_/RANK/LOOKUP, "
                    "or DATE*/SPLIT/RAWSQL). Rewrite manually or enable AI conversion.")
            else:
                unresolved = [r for r in _FIELD_REF.findall(formula or "")
                              if r not in field_lookup and r not in measures]
                if unresolved:
                    out["limitations"].append(
                        "Could not resolve referenced field(s) to a Table[Column]: "
                        + ", ".join(sorted(set(unresolved)))
                        + ". Confirm the physical source column.")
                else:
                    out["limitations"].append(
                        "Formula shape not confidently convertible by the offline rules.")
            return out

        # A DAX expression was produced.
        if as_measure:
            out["daxMeasure"] = f"{name} = {dax}"
            out["assumptions"].append("Rendered as a DAX MEASURE (calc aggregates or references a measure).")
        else:
            out["daxColumn"] = f"{name} = {dax}"
            out["assumptions"].append("Rendered as a calculated COLUMN (row-level expression, no aggregation).")
        out["assumptions"].append("Field references resolved to Table[Column] by name match.")

        if flagged:
            out["confidence"] = 0.5
            out["limitations"].append(
                "Best-effort only — the formula spans constructs whose relationship/"
                "grain semantics differ in Power BI; validate filter context before use.")
        else:
            out["confidence"] = 0.9
        return out


class LlmDaxBackend(DaxBackend):
    """On-demand Claude translation. Key is supplied per-call and kept in memory
    only (never persisted or logged). Output is treated as untrusted text."""

    method = _METHOD_LLM
    MODEL_ID = "claude-opus-4-8"
    _SYSTEM = (
        "You are a Tableau-to-Power BI migration expert translating a Tableau "
        "calculated field into a DAX measure.\n"
        "CRITICAL modeling difference: Tableau physically JOINS tables into one, so a "
        "Tableau calc can reference any joined column directly. Power BI keeps tables "
        "SEPARATE and linked by RELATIONSHIPS, so a calc that touches another table "
        "must use CALCULATE / RELATED / relationship context.\n"
        "Use the provided model context (tables, columns, and the field map). "
        "Reference other measures by [Name] and columns by Table[Column].\n"
        "Reply with ONLY the DAX expression (the right-hand side of the measure) — no "
        "name, no 'MEASURE =', no code fences, no commentary. If it genuinely cannot "
        "be expressed in DAX, reply with the single token UNTRANSLATABLE."
    )

    def _context_block(self, ctx: dict) -> str:
        lines = ["TABLES:"]
        for tname, cols in ctx.get("tables", []):
            lines.append(f"  {tname}[{', '.join(cols)}]")
        field_lookup = ctx.get("field_lookup", {})
        if field_lookup:
            lines.append("FIELD MAP (Tableau field -> DAX Table[Column]):")
            for fname, (table, col) in sorted(field_lookup.items()):
                lines.append(f"  [{fname}] -> {table}[{col}]")
        measures = ctx.get("measures", set())
        if measures:
            lines.append("OTHER MEASURES (reference by [name]):")
            lines.append("  " + ", ".join(f"[{m}]" for m in sorted(measures)))
        return "\n".join(lines)

    def suggest(self, *, name: str, formula: str, categories: list[str],
                ctx: dict, api_key: str | None = None, guidance: dict | None = None,
                **kwargs) -> dict:
        out = _empty_suggestion(self.method)
        client, err = _make_client(api_key)
        if client is None:
            out["limitations"].append(err)
            return out

        hints = ""
        if guidance:
            hint_lines = [f"- {k}: {str(v).strip()}" for k, v in guidance.items() if str(v).strip()]
            if hint_lines:
                hints = "\nUser guidance for the correct result:\n" + "\n".join(hint_lines)

        try:
            resp = client.messages.create(
                model=self.MODEL_ID,
                max_tokens=512,
                system=self._SYSTEM,
                messages=[{
                    "role": "user",
                    "content": (
                        f"{self._context_block(ctx)}\n\n"
                        f"Translate this Tableau calculated field to a DAX measure.\n"
                        f"Name: {name}\n"
                        f"Tableau formula: {formula}{hints}"
                    ),
                }],
            )
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
        except Exception as exc:  # pragma: no cover - network/SDK dependent
            out["limitations"].append(f"AI conversion failed: {type(exc).__name__}: {exc}")
            return out

        if not text or "UNTRANSLATABLE" in text or text.count("(") != text.count(")"):
            out["limitations"].append("Model returned no usable DAX (empty / invalid / untranslatable).")
            return out

        out["daxMeasure"] = f"{name} = {text}"
        out["confidence"] = 0.85
        out["assumptions"].append("AI-generated — validate against the semantic model before publishing.")
        return out


def _make_client(api_key: str | None):
    """Return (client, error). Uses the per-request key, else ANTHROPIC_API_KEY.
    The key is never stored or logged."""
    key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, "AI conversion is on but no API key was provided (paste one in the key box, or set ANTHROPIC_API_KEY)."
    try:
        import anthropic  # noqa: WPS433 (optional dependency)

        return anthropic.Anthropic(api_key=key), None
    except Exception as exc:  # pragma: no cover - environment dependent
        return None, f"Anthropic SDK not available ({exc})."


_OFFLINE = OfflineDaxBackend()
_LLM = LlmDaxBackend()


def suggest(*, name: str, formula: str, categories: list[str], ctx: dict,
            use_llm: bool = False, api_key: str | None = None,
            guidance: dict | None = None) -> dict:
    """Facade used by the engine (offline) and the endpoint (on-demand LLM)."""
    backend = _LLM if use_llm else _OFFLINE
    return backend.suggest(name=name, formula=formula, categories=categories,
                           ctx=ctx, api_key=api_key, guidance=guidance)
