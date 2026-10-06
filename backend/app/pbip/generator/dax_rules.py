"""Offline, rule-based Tableau-formula -> DAX translator.

A deterministic fallback used when the LLM is unavailable (e.g. no network /
API blocked). It reliably handles the common shapes - aggregations, arithmetic,
references to other measures, and IF/THEN/ELSEIF/ELSE/END - producing valid DAX
measures. Formulas it cannot confidently convert are left untranslated (BLANK()
with the original formula as a review comment), never guessed.

It is intentionally conservative: better to leave a measure for manual review
than to emit plausible-but-wrong DAX.
"""
from __future__ import annotations

import re

from ..model.ir import Model

# Tableau aggregate/function name -> DAX name (others pass through unchanged).
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


def _quote_table(name: str) -> str:
    if name and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def _convert_if(formula: str) -> str:
    """`IF c THEN a ELSEIF d THEN e ELSE f END` -> SWITCH(TRUE(), c, a, d, e, f)."""

    def repl(match: re.Match) -> str:
        parts = _KW_SPLIT.split(match.group(1))
        # parts = [cond1, THEN, val1, ELSEIF, cond2, THEN, val2, ELSE, default]
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


def translate(formula: str, field_lookup: dict, measures: set[str]) -> str | None:
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
        return None  # a referenced field could not be resolved -> don't guess

    for src, dst in _RENAME.items():
        s = re.sub(rf"\b{src}\s*\(", f"{dst}(", s)

    if s.count("(") != s.count(")"):
        return None
    if any(tok in s for tok in _LEFTOVER):
        return None  # unconverted control-flow / calc ref remains
    return s


def _referenced_column_tables(formula: str, field_lookup: dict, measures: set[str]) -> set[str]:
    """Tables of the physical columns a formula references (measures excluded)."""
    tables: set[str] = set()
    for name in _FIELD_REF.findall(formula or ""):
        if name in measures:
            continue
        if name in field_lookup:
            tables.add(field_lookup[name][0])
    return tables


# Tableau constructs the offline rules cannot translate correctly (they have no
# 1:1 DAX form, or a different signature) -> must be flagged for review, never
# emitted as "confident". LOD expressions use braces; the rest are table calcs /
# functions whose names would pass through unchanged and be wrong.
_UNSUPPORTED = re.compile(
    r"\{|\b("
    r"WINDOW_\w+|RUNNING_\w+|INDEX|RANK|RANK_\w+|FIRST|LAST|LOOKUP|TOTAL|SIZE|"
    r"PREVIOUS_VALUE|DATEPART|DATENAME|DATETRUNC|DATEADD|DATEDIFF|MAKEDATE|"
    r"SPLIT|REGEXP_\w+|PERCENTILE|MEDIAN|ATTR|ZN|RAWSQL\w*"
    r")\s*\(",
    re.IGNORECASE,
)


def _has_unsupported(formula: str) -> bool:
    return bool(_UNSUPPORTED.search(formula or ""))


def _is_join_affected(formula: str, model: Model, measures: set[str]) -> bool:
    """True when a calc spans >1 table or touches an inner-join table - the
    cross-table / join-filtered cases the rules must NOT guess."""
    tables = _referenced_column_tables(formula, model.field_lookup, measures)
    return len(tables) > 1 or bool(tables & model.inner_join_tables)


def translate_model(model: Model) -> None:
    """Translate every calc the rules can express, using a LITERAL translation of
    the Tableau logic. Same-table calcs are confident; cross-table / inner-join
    calcs get the same literal DAX but are flagged needs_review (verify the
    relationship semantics - they may need CALCULATE with a related-table filter)."""
    measures = {cf.name for cf in model.calculated_fields}
    confident = flagged = 0
    for cf in model.calculated_fields:
        if cf.translated:
            continue
        dax = translate(cf.formula, model.field_lookup, measures)
        if not dax:
            continue  # unconvertible -> tmdl_generator emits BLANK() + scaffold
        cf.dax, cf.translated, cf.method = dax, True, "rule"
        if _is_join_affected(cf.formula, model, measures) or _has_unsupported(cf.formula):
            cf.needs_review = True
            flagged += 1
        else:
            confident += 1
    if confident:
        model.warnings.append(f"{confident} calculated field(s) translated to DAX by offline rules.")
    if flagged:
        model.warnings.append(
            f"{flagged} calculated field(s) FLAGGED FOR REVIEW - cross-table / inner-join, or use "
            "constructs the offline rules can't translate reliably (LOD {FIXED..}, table calcs like "
            "WINDOW_SUM/RANK, DATEDIFF/DATEPART, etc.). A best-effort DAX was provided; verify it, "
            "use the AI path (open network), or hand-edit in the Preview."
        )
