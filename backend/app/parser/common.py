"""Shared parsing helpers: safe XML load and Tableau bracket-name utilities.

XML is parsed with :mod:`defusedxml` so malformed / hostile workbooks (XXE,
billion-laughs) fail closed rather than executing entity expansion.
"""
from __future__ import annotations

import re
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as DET

_BRACKET = re.compile(r"\[([^\]]+)\]")


class ParseError(Exception):
    """Raised when a workbook cannot be parsed (malformed / unsupported XML)."""


def load_xml(xml_bytes: bytes) -> Element:
    try:
        text = xml_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = xml_bytes.decode("latin-1", errors="replace")
    try:
        return DET.fromstring(text)
    except Exception as exc:  # defusedxml raises various parse/entity errors
        raise ParseError(f"Malformed or unsupported Tableau XML: {exc}") from exc


def strip_brackets(value: str | None) -> str:
    """``[Orders$]`` -> ``Orders$`` ; ``[dbo].[Orders]`` -> ``dbo.Orders``."""
    parts = _BRACKET.findall(value or "")
    if parts:
        return ".".join(parts)
    return (value or "").strip("[]")


def last_name(value: str | None) -> str:
    """``[P.ID]`` -> ``P.ID`` ; ``[Orders].[P.ID]`` -> ``P.ID``."""
    parts = _BRACKET.findall(value or "")
    if parts:
        return parts[-1]
    return (value or "").strip("[]")


def parse_ref(value: str | None) -> tuple[str, str]:
    """``[Orders].[P.ID]`` -> ``("Orders", "P.ID")``."""
    parts = _BRACKET.findall(value or "")
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if len(parts) == 1:
        return "", parts[0]
    return "", value or ""
