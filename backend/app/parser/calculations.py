"""Lightweight calculated-field detection (names/count only).

Full formula analysis belongs to the future Calculations module; here we only
need the inventory count for complexity metrics.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import CalcMeta
from .calc_classify import classify_formula
from .common import last_name


def _calc_columns(datasource: Element):
    seen: set[str] = set()
    for col in datasource.findall("column"):
        calc = col.find("calculation")
        if calc is None or calc.get("class") != "tableau" or not calc.get("formula"):
            continue
        name = col.get("caption") or last_name(col.get("name", ""))
        if name and name not in seen:
            seen.add(name)
            yield name, calc.get("formula", "")


def calculated_field_names(datasource: Element) -> list[str]:
    return [name for name, _formula in _calc_columns(datasource)]


def extract_calculations(datasource: Element) -> list[CalcMeta]:
    calcs: list[CalcMeta] = []
    for name, formula in _calc_columns(datasource):
        c = classify_formula(formula)
        calcs.append(CalcMeta(
            name=name,
            formula=formula,
            categories=c["categories"],
            lod=c["lod"],
            table_calc=c["tableCalc"],
            migration_complexity=c["migrationComplexity"],
            power_bi_support=c["powerBiSupport"],
            note=c["note"],
        ))
    return calcs
