"""Extract Groups, Sets and Bins — 'created fields' that sit alongside calcs.

Bins:   <column><calculation class='bin' formula='[Field]' size='..'/></column>
Groups: <column><calculation class='categorical-bin' column='[Field]'><bin value>..</bin></calculation></column>
Sets:   <group> elements (IN/OUT sets used via column-instance derivation='InOut'),
        and <column><calculation class='set'|'in-out'>.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import BinMeta, GroupMeta, SetMeta
from .common import last_name, strip_brackets


def extract_groups_bins_sets(datasource: Element):
    bins: list[BinMeta] = []
    groups: list[GroupMeta] = []
    sets: list[SetMeta] = []
    seen_bin: set[str] = set()
    seen_group: set[str] = set()
    seen_set: set[str] = set()

    for col in datasource.findall("column"):
        calc = col.find("calculation")
        if calc is None:
            continue
        cls = calc.get("class")
        name = col.get("caption") or last_name(col.get("name", ""))
        if cls == "bin":
            if name not in seen_bin:
                seen_bin.add(name)
                bins.append(BinMeta(name=name, source_field=last_name(calc.get("formula", "")), size=calc.get("size")))
        elif cls == "categorical-bin":
            if name not in seen_group:
                seen_group.add(name)
                members = []
                for b in calc.findall("bin"):
                    members.append({
                        "name": (b.get("value") or "").strip('"'),
                        "values": [(v.text or "").strip().strip('"') for v in b.findall("value")],
                    })
                groups.append(GroupMeta(name=name, source_field=last_name(calc.get("column", "")), groups=members))
        elif cls in ("set", "in-out"):
            if name not in seen_set:
                seen_set.add(name)
                sets.append(SetMeta(name=name, source_field=last_name(calc.get("column", "")), kind="set"))

    # <group> elements (IN/OUT sets built from a field, e.g. via a filter-group).
    for g in datasource.findall(".//group"):
        name = g.get("caption") or last_name(g.get("name", ""))
        if not name or name in seen_set or name in seen_group:
            continue
        seen_set.add(name)
        # Source field: the field referenced by the group's member filters.
        gf = g.find(".//groupfilter")
        source = None
        if gf is not None:
            source = last_name(gf.get("level") or gf.get("member") or "")
        sets.append(SetMeta(name=name, source_field=source or None, kind="in-out"))

    return groups, sets, bins
