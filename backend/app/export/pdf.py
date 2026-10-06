"""Export a formatted executive PDF report (fpdf2, core fonts).

fpdf2 core fonts are Latin-1; text is ASCII-sanitized so Unicode glyphs
(arrows, dashes) never break output — no external font file is shipped.
"""
from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_REPLACEMENTS = {
    "→": "->", "↔": "<->", "×": "x", "–": "-", "—": "-",
    "’": "'", "“": '"', "”": '"', "•": "-", "…": "...",
}


def _ascii(value) -> str:
    if value is None:
        return ""
    s = str(value)
    for k, v in _REPLACEMENTS.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


class _Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(150)
        self.cell(0, 6, "Tableau Analysis Tool - Data Source Assessment",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_text_color(0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


def _line(pdf, text, h=5):
    """Write a full-width paragraph, always starting at the left margin so the
    available width can never collapse to zero."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, h, _ascii(text))


def _h1(pdf, text):
    pdf.set_font("Helvetica", "B", 15)
    _line(pdf, text, 8)
    pdf.ln(1)


def _h2(pdf, text):
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(31, 111, 235)
    _line(pdf, text, 7)
    pdf.set_text_color(0)


def _kv(pdf, key, value):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(55, 6, _ascii(key))
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _ascii(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _finding(pdf, f):
    pdf.set_font("Helvetica", "B", 10)
    _line(pdf, f"[{f.get('severity', '').upper()}] {f.get('title', '')}", 5.5)
    pdf.set_font("Helvetica", "", 9)
    if f.get("businessImpact"):
        _line(pdf, f"Impact: {f['businessImpact']}")
    if f.get("recommendation"):
        _line(pdf, f"Recommendation: {f['recommendation']}")
    if f.get("evidence"):
        _line(pdf, "Evidence: " + "; ".join(f["evidence"][:8]))
    pdf.ln(1)


_SECTIONS = [
    ("technicalDebt", "Technical Debt"),
    ("modelingRisks", "Modeling Risks"),
    ("dataQualityRisks", "Data Quality Risks"),
    ("governance", "Governance Concerns"),
    ("scalability", "Scalability Concerns"),
    ("performance", "Performance Risks"),
    ("optimization", "Optimization Opportunities"),
]


def build_pdf(metadata: dict) -> bytes:
    pdf = _Report()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    _h1(pdf, f"Tableau Analysis - {metadata.get('name', 'Workbook')}")
    counts = metadata.get("counts", {})
    cx = metadata.get("complexity", {})

    _h2(pdf, "Overview")
    _kv(pdf, "Version", metadata.get("version"))
    _kv(pdf, "Source Platform", metadata.get("sourcePlatform"))
    _kv(pdf, "Data Sources", counts.get("dataSources"))

    _h2(pdf, "Complexity Metrics")
    for label, key in [("Tables", "tables"), ("Joins", "joins"), ("Relationships", "relationships"),
                       ("Calculated Fields", "calculatedFields"), ("Filters", "filters"),
                       ("Parameters", "parameters"), ("Custom SQL", "customSql")]:
        _kv(pdf, label, cx.get(key, 0))

    _h2(pdf, "Data Model Classification")
    for ds in metadata.get("dataSources", []):
        c = ds.get("classification", {})
        _kv(pdf, ds.get("caption") or ds.get("name"), c.get("type"))
        pdf.set_font("Helvetica", "I", 9)
        for r in c.get("reasoning", []):
            _line(pdf, f"  - {r}")

    assessment = metadata.get("assessment", {})
    bp = assessment.get("bestPractices", {})
    if bp:
        _h2(pdf, f"Maturity Score: {bp.get('maturityScore')}/100 - {bp.get('maturityBand')}")
        pdf.set_font("Helvetica", "", 9)
        for line in bp.get("explanation", []):
            _line(pdf, f"  - {line}")
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 10)
        _line(pdf, "Best-Practice Framework Scores", 6)
        pdf.set_font("Helvetica", "", 9)
        for fw in bp.get("frameworks", []):
            _line(pdf, f"  {fw.get('name')}: {fw.get('score')}/100 - {fw.get('notes')}")

    _h2(pdf, "Technical Assessment Findings")
    for key, label in _SECTIONS:
        items = assessment.get(key, [])
        if not items:
            continue
        pdf.set_font("Helvetica", "B", 11)
        _line(pdf, f"{label} ({len(items)})", 6)
        pdf.ln(1)
        for f in items:
            _finding(pdf, f)

    return bytes(pdf.output())
