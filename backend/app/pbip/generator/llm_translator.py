"""Translate Tableau calculated-field formulas into DAX measures via Claude.

This is the ONLY non-deterministic step in the pipeline and it runs only when
the workbook actually contains calculated fields.  If the Anthropic SDK or an
API key is unavailable, or a translation looks malformed, the field degrades to
a ``BLANK()`` measure carrying the original formula as a description - the
project still opens rather than failing.
"""
from __future__ import annotations

import os

from ..model.ir import CalculatedField, Model

MODEL_ID = "claude-opus-4-8"

_SYSTEM = (
    "You are a Tableau-to-Power BI migration expert translating a Tableau "
    "calculated field into a DAX measure.\n"
    "CRITICAL modeling difference: Tableau physically JOINS tables into one, so a "
    "Tableau calc can reference any joined column directly. Power BI keeps tables "
    "SEPARATE and linked by RELATIONSHIPS, so a calc that touches another table "
    "must use CALCULATE / RELATED / relationship context. Example: Tableau "
    "COUNT([Order ID (Returns)]) becomes CALCULATE(COUNT(Orders[Order ID]), "
    'Returns[Returned] = "Yes") when Returns is a separate related table.\n'
    "Use the provided model context (tables, columns, relationships, and which "
    "physical table each field came from). Reference other measures by [Name] and "
    "columns by Table[Column].\n"
    "Reply with ONLY the DAX expression (the right-hand side of the measure) - no "
    "name, no 'MEASURE =', no code fences, no commentary. If it genuinely cannot "
    "be expressed in DAX, reply with the single token UNTRANSLATABLE."
)


def _valid_dax(text: str) -> bool:
    if not text or "UNTRANSLATABLE" in text:
        return False
    return text.count("(") == text.count(")")


def _model_context(model: Model) -> str:
    lines = ["TABLES:"]
    for t in model.tables:
        cols = ", ".join(c.source_column for c in t.columns)
        lines.append(f"  {t.name}[{cols}]")
    if model.relationships:
        lines.append("RELATIONSHIPS (from = many side):")
        for r in model.relationships:
            lines.append(f"  {r.from_table}[{r.from_column}] * : 1 {r.to_table}[{r.to_column}]")
    if model.inner_join_tables:
        lines.append(
            "INNER JOIN (IMPORTANT): in Tableau these tables were combined with an INNER join, "
            "which FILTERS the whole dataset to matched rows: "
            + ", ".join(sorted(model.inner_join_tables))
            + ". Therefore any aggregation over these tables' columns must be wrapped in "
            "CALCULATE with a filter that keeps only matched rows on the related lookup table "
            '(e.g. Returns[Returned] = "Yes"), so the measure still responds to visual filter context.'
        )
    if model.field_lookup:
        lines.append("FIELD MAP (Tableau field name -> DAX Table[Column]):")
        for name, (table, col) in sorted(model.field_lookup.items()):
            lines.append(f"  [{name}] -> {table}[{col}]")
    if model.calculated_fields:
        lines.append("OTHER MEASURES (reference by [name]):")
        lines.append("  " + ", ".join(f"[{cf.name}]" for cf in model.calculated_fields))
    return "\n".join(lines)


def translate_model(model: Model, api_key: str | None = None) -> None:
    """Populate ``dax``/``translated`` on each calculated field in place."""
    if not model.calculated_fields:
        return

    client, client_error = _make_client(api_key)
    if client is None:
        model.warnings.append(f"LLM disabled: {client_error}. Calculated fields left as BLANK().")
        return

    context = _model_context(model)
    for cf in model.calculated_fields:
        if cf.translated and not cf.needs_review:
            continue  # confident offline result - keep it
        # Untranslated OR flagged-for-review: let the model produce relationship-aware DAX.
        dax, error = _translate_one(client, cf, context)
        if dax and _valid_dax(dax):
            cf.dax, cf.translated, cf.method, cf.needs_review = dax.strip(), True, "llm", False
        elif error:
            model.warnings.append(f"'{cf.name}' not translated - API error: {error}")
        else:
            model.warnings.append(f"'{cf.name}' not translated (empty/invalid DAX); left as BLANK().")


def _make_client(api_key: str | None = None):
    """Return (client, error_message). client is None when unavailable.

    Uses the given api_key (from the UI) if provided, otherwise the
    ANTHROPIC_API_KEY environment variable.
    """
    key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, "No API key provided (paste one in the app, or set ANTHROPIC_API_KEY)"
    try:
        import anthropic  # noqa: WPS433 (optional dependency)

        return anthropic.Anthropic(api_key=key), None
    except Exception as exc:  # pragma: no cover - environment dependent
        return None, f"anthropic SDK not available ({exc})"


_GUIDANCE_LABELS = {
    "intent": "Business intent / meaning",
    "columns": "Columns to use",
    "join_type": "Join type",
    "aggregation": "Aggregation",
    "filters": "Filters to apply",
    "context": "Filter / row context",
    "time_intelligence": "Time intelligence",
    "error_notes": "Error / correction notes",
}


def retranslate_one(
    model: Model, calc_name: str, guidance: dict, api_key: str | None
) -> tuple[str | None, str | None]:
    """Re-translate a single measure using the user's guidance. Returns (dax, error)."""
    cf = next((c for c in model.calculated_fields if c.name == calc_name), None)
    if cf is None:
        return None, f"Calculated field '{calc_name}' not found."

    client, client_error = _make_client(api_key)
    if client is None:
        return None, client_error

    hints = [f"- {_GUIDANCE_LABELS[k]}: {v.strip()}" for k, v in (guidance or {}).items()
             if k in _GUIDANCE_LABELS and str(v).strip()]
    guidance_block = ("\nThe user provided this guidance for the CORRECT result:\n"
                      + "\n".join(hints)) if hints else ""

    context = _model_context(model)
    try:
        resp = client.messages.create(
            model=MODEL_ID,
            max_tokens=512,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"{context}\n\n"
                        f"Translate this Tableau calculated field to a DAX measure.\n"
                        f"Name: {cf.name}\n"
                        f"Tableau formula: {cf.formula}\n"
                        f"Current DAX (may be wrong): {cf.dax or '(none)'}"
                        f"{guidance_block}"
                    ),
                }
            ],
        )
        dax = "".join(b.text for b in resp.content if b.type == "text").strip()
        return (dax, None) if _valid_dax(dax) else (None, "Model returned empty/invalid DAX.")
    except Exception as exc:  # pragma: no cover - network/SDK dependent
        return None, f"{type(exc).__name__}: {exc}"


def _translate_one(client, cf: CalculatedField, context: str) -> tuple[str | None, str | None]:
    """Return (dax_text, error_message)."""
    try:
        resp = client.messages.create(
            model=MODEL_ID,
            max_tokens=512,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"{context}\n\n"
                        f"Translate this Tableau calculated field to a DAX measure.\n"
                        f"Name: {cf.name}\n"
                        f"Tableau formula: {cf.formula}"
                    ),
                }
            ],
        )
        return "".join(block.text for block in resp.content if block.type == "text"), None
    except Exception as exc:  # pragma: no cover - network/SDK dependent
        return None, f"{type(exc).__name__}: {exc}"
