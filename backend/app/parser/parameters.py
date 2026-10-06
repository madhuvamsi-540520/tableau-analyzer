"""Extract Tableau parameters (stored in the special 'Parameters' datasource)."""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import ParameterMeta
from .common import last_name


def extract_parameters(root: Element) -> list[ParameterMeta]:
    params: list[ParameterMeta] = []
    for ds in root.iter("datasource"):
        if ds.get("name") != "Parameters":
            continue
        for col in ds.findall("column"):
            # Parameter columns carry a param-domain-type; skip anything else.
            domain = col.get("param-domain-type")
            name = col.get("caption") or last_name(col.get("name", ""))
            if not name:
                continue
            params.append(
                ParameterMeta(
                    name=name,
                    data_type=col.get("datatype"),
                    current_value=col.get("value"),
                    domain_type=domain,
                )
            )
    return params
