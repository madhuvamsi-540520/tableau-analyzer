"""Tableau workbook (.twb) XML parser -> canonical IR (:class:`Model`).

Extracts data sources, physical tables/columns, joins (relationships) and
calculated fields.  Visual/worksheet content is intentionally ignored - the
migration only reproduces the semantic model.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Optional

import defusedxml.ElementTree as DET  # safe parsing (blocks XML-bomb / entity expansion)

from ..model import ir
from ..model.ir import (
    CalculatedField,
    Column,
    Connection,
    Model,
    ProjectionField,
    Relationship,
    Table,
    Worksheet,
)

_CALC_REF = re.compile(r"\[(Calculation_[0-9]+)\]")

_BRACKET = re.compile(r"\[([^\]]+)\]")


def _strip_brackets(value: str) -> str:
    """`[Orders$]` -> `Orders$`, `[dbo].[Orders]` -> `dbo.Orders`."""
    parts = _BRACKET.findall(value or "")
    if parts:
        return ".".join(parts)
    return (value or "").strip("[]")


def _parse_field_ref(ref: str) -> tuple[str, str]:
    """`[Orders].[P.ID]` -> ("Orders", "P.ID")."""
    parts = _BRACKET.findall(ref or "")
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if len(parts) == 1:
        return "", parts[0]
    return "", ref


class TwbParser:
    def __init__(self, xml_text: str, project_name: str):
        self.project_name = project_name
        # Parse safely (defusedxml blocks entity-expansion / XML-bomb attacks in
        # untrusted .twb files). Returns standard ElementTree elements.
        self.root = DET.fromstring(xml_text)

    def parse(self) -> Model:
        model = Model(name=self.project_name)

        datasource = self._first_real_datasource()
        if datasource is None:
            model.warnings.append("No data source found in workbook.")
            return model

        model.source_caption = datasource.get("caption")
        connection = datasource.find("connection")

        # 1. named connections
        if connection is not None:
            self._parse_connections(connection, model)

        # 2. physical tables + joins (from the federated relation tree)
        rel_pairs: list[tuple[str, str, str, str]] = []
        tables: list[Table] = []
        inner_tables: set[str] = set()
        if connection is not None:
            for rel in connection.findall("relation"):
                self._walk_relation(rel, tables, rel_pairs, inner_tables)
        model.tables = tables
        model.inner_join_tables = inner_tables

        # 3. field lookup maps (needed to resolve logical-relationship operands)
        self._build_field_maps(datasource)
        model.field_lookup = {
            key: (self._field_table.get(key, ""), self._field_source_col.get(key, key))
            for key in self._field_table
        }

        # 4. logical relationships (newer Tableau "relationships" model, where the
        # tables are NOT wrapped in a <relation type='join'>) -> add to rel_pairs.
        self._parse_logical_relationships(datasource, rel_pairs)

        # 5. relationships. Power BI needs a direction Tableau doesn't give, so use
        # a many-to-one heuristic: the table with FEWER columns is the "one"
        # (lookup) side -> "to"; the wider table is "many" -> "from". (When data is
        # loaded, converter._refine_relationships re-orients this by row count.)
        col_count = {t.name: len(t.columns) for t in tables}
        rel_cols: set[tuple[str, str]] = set()
        seen_rel: set[tuple] = set()
        for a_t, a_c, b_t, b_c in rel_pairs:
            key = tuple(sorted([(a_t, a_c), (b_t, b_c)]))
            if key in seen_rel:
                continue
            seen_rel.add(key)
            rel_cols.add((a_t, a_c))
            rel_cols.add((b_t, b_c))
            if col_count.get(a_t, 0) >= col_count.get(b_t, 0):
                (ft, fc), (tt, tc) = (a_t, a_c), (b_t, b_c)
            else:
                (ft, fc), (tt, tc) = (b_t, b_c), (a_t, a_c)
            model.relationships.append(
                Relationship(from_table=ft, from_column=fc, to_table=tt, to_column=tc)
            )

        # 6. finalize columns (type mapping, summarizeBy, formatString)
        for table in tables:
            for col in table.columns:
                col.data_type = ir.pbi_type(col.tableau_type)
                col.summarize_by = ir.summarize_by_for(
                    col.name, col.data_type, (table.name, col.name) in rel_cols
                )
                col.format_string = "0" if col.data_type == "int64" else None

        # 7. calculated fields, worksheets
        self._parse_calculated_fields(datasource, model)
        self._parse_worksheets(model)

        return model

    # ------------------------------------------------------------------ #

    def _first_real_datasource(self) -> Optional[ET.Element]:
        """The first federated (non-parameter) datasource with a connection."""
        for ds in self.root.iter("datasource"):
            if ds.get("name") == "Parameters":
                continue
            if ds.find("connection") is not None:
                return ds
        return None

    def _parse_connections(self, federated_conn: ET.Element, model: Model) -> None:
        for nc in federated_conn.iter("named-connection"):
            inner = nc.find("connection")
            if inner is None:
                continue
            conn = Connection(
                name=nc.get("name", ""),
                caption=nc.get("caption"),
                cls=inner.get("class", ""),
                filename=inner.get("filename"),
                server=inner.get("server") or None,
                port=inner.get("port") or None,
                database=inner.get("dbname") or inner.get("database") or None,
                schema=inner.get("schema") or None,
            )
            model.connections[conn.name] = conn

    def _walk_relation(
        self,
        rel: ET.Element,
        tables: list[Table],
        rel_pairs: list[tuple[str, str, str, str]],
        inner_tables: set[str],
    ) -> None:
        rtype = rel.get("type")
        if rtype == "join":
            is_inner = (rel.get("join") or "inner").lower() == "inner"
            # record join predicate(s): [A].[c] = [B].[c]
            for expr in rel.findall("./clause/expression[@op='=']"):
                operands = expr.findall("expression")
                if len(operands) == 2:
                    lt, lc = _parse_field_ref(operands[0].get("op", ""))
                    rt, rc = _parse_field_ref(operands[1].get("op", ""))
                    # Store both endpoints; direction is decided later by the
                    # column-count heuristic in parse().
                    rel_pairs.append((lt, lc, rt, rc))
                    if is_inner:
                        inner_tables.update({lt, rt})
            for child in rel.findall("relation"):
                self._walk_relation(child, tables, rel_pairs, inner_tables)
        elif rtype == "table":
            tables.append(self._build_table(rel))
        elif rtype == "text":
            tables.append(self._build_custom_sql_table(rel))
        else:
            # container relation: recurse
            for child in rel.findall("relation"):
                self._walk_relation(child, tables, rel_pairs, inner_tables)

    def _columns_of(self, rel: ET.Element) -> list[Column]:
        cols: list[Column] = []
        seen: set[str] = set()
        cols_el = rel.find("columns")
        raw = cols_el.findall("column") if cols_el is not None else []
        for c in sorted(raw, key=lambda e: int(e.get("ordinal", "0"))):
            name = c.get("name", "")
            # A column name must appear at most once per table, else TMDL fails to
            # load ("objects cannot be merged ... same property: dataType").
            if name in seen:
                continue
            seen.add(name)
            cols.append(
                Column(
                    name=name,
                    data_type="string",  # replaced during finalize
                    source_column=name,
                    tableau_type=c.get("datatype", "string"),
                )
            )
        return cols

    def _build_table(self, rel: ET.Element) -> Table:
        name = rel.get("name", "Table")
        physical = _strip_brackets(rel.get("table", name))
        connection_ref = rel.get("connection")
        # Excel sheet references look like `Orders$`; the sheet name drops `$`.
        sheet = physical.rstrip("$")
        return Table(
            name=name,
            source_name=sheet if physical.endswith("$") else physical,
            columns=self._columns_of(rel),
            connection_ref=connection_ref,
            kind="excel-sheet" if physical.endswith("$") else "db-table",
        )

    def _build_custom_sql_table(self, rel: ET.Element) -> Table:
        name = rel.get("name", "Custom SQL Query")
        return Table(
            name=name,
            source_name=name,
            columns=self._columns_of(rel),
            connection_ref=rel.get("connection"),
            kind="custom-sql",
            custom_sql=(rel.text or "").strip(),
        )

    def _resolve_operand(self, op_str: str) -> tuple[str, str]:
        """Resolve a relationship operand to (table, column).

        Physical joins use `[Table].[col]`; logical relationships use a bare
        `[field]` that must be resolved through the field map (cols)."""
        parts = _BRACKET.findall(op_str or "")
        if len(parts) >= 2:
            return parts[0], parts[-1]
        if len(parts) == 1:
            key = parts[0]
            if key in getattr(self, "_field_table", {}):
                return self._field_table[key], self._field_source_col.get(key, key)
            return "", key
        return "", op_str

    def _parse_logical_relationships(
        self, datasource: ET.Element, rel_pairs: list[tuple[str, str, str, str]]
    ) -> None:
        """Parse Tableau's newer logical relationships (<relationships>/<relationship>)."""
        for rel in datasource.findall(".//relationships/relationship"):
            expr = rel.find("./expression[@op='=']")
            if expr is None:
                continue
            operands = expr.findall("expression")
            if len(operands) != 2:
                continue
            lt, lc = self._resolve_operand(operands[0].get("op", ""))
            rt, rc = self._resolve_operand(operands[1].get("op", ""))
            if lt and rt:
                rel_pairs.append((lt, lc, rt, rc))

    def _build_field_maps(self, datasource: ET.Element) -> None:
        """Resolve field name -> (physical table, source column) and
        internal Calculation ids -> their user-facing caption."""
        self._field_table: dict[str, str] = {}
        self._field_source_col: dict[str, str] = {}
        self._calc_caption: dict[str, str] = {}

        cols = datasource.find(".//cols")
        if cols is not None:
            for m in cols.findall("map"):
                key = _strip_brackets(m.get("key", ""))
                table, col = _parse_field_ref(m.get("value", ""))
                if key:
                    self._field_table[key] = table
                    self._field_source_col[key] = col

        for col in datasource.findall("column"):
            internal = _strip_brackets(col.get("name", ""))
            caption = col.get("caption")
            if caption and internal.startswith("Calculation_"):
                self._calc_caption[internal] = caption

    def _resolve_refs(self, formula: str) -> str:
        """Rewrite [Calculation_123] references to their readable [Caption]."""
        return _CALC_REF.sub(
            lambda m: f"[{self._calc_caption[m.group(1)]}]"
            if m.group(1) in self._calc_caption
            else m.group(0),
            formula,
        )

    def _parse_calculated_fields(self, datasource: ET.Element, model: Model) -> None:
        fact = model.fact_table()
        fact_name = fact.name if fact else None
        for col in datasource.findall("column"):
            calc = col.find("calculation")
            if calc is None or calc.get("class") != "tableau":
                continue
            formula = calc.get("formula")
            if not formula:
                continue
            internal = _strip_brackets(col.get("name", "Calc"))
            caption = col.get("caption") or internal
            data_type = ir.pbi_type(col.get("datatype", "string"))
            model.calculated_fields.append(
                CalculatedField(
                    name=caption,
                    formula=self._resolve_refs(formula),
                    data_type=data_type,
                    role=col.get("role", "measure"),
                    table=fact_name,
                    format_string="0" if data_type == "int64" else None,
                )
            )

    def _parse_worksheets(self, model: Model) -> None:
        """Each worksheet's placed fields become the columns of a Table visual."""
        fact = model.fact_table()
        fact_name = fact.name if fact else ""
        calc_names = {cf.name for cf in model.calculated_fields}

        for ws in self.root.findall("worksheets/worksheet"):
            deps = ws.find(".//datasource-dependencies")
            if deps is None:
                continue

            # local field defs in this worksheet: colref -> (role, is_calc, caption)
            local: dict[str, tuple[str, bool, str]] = {}
            for col in deps.findall("column"):
                ref = col.get("name", "")
                internal = _strip_brackets(ref)
                is_calc = col.find("calculation") is not None or internal.startswith("Calculation_")
                local[ref] = (col.get("role", "dimension"), is_calc, col.get("caption") or internal)

            fields: list[ProjectionField] = []
            seen: set[tuple[str, str]] = set()
            for ci in deps.findall("column-instance"):
                ref = ci.get("column", "")
                derivation = ci.get("derivation", "None")
                role, is_calc, caption = local.get(ref, ("dimension", False, _strip_brackets(ref)))
                if is_calc or caption in calc_names:
                    key = ("measure", caption)
                    if key in seen:
                        continue
                    seen.add(key)
                    fields.append(ProjectionField(kind="measure", table=fact_name, property=caption))
                else:
                    field_key = _strip_brackets(ref)
                    table = self._field_table.get(field_key, fact_name)
                    prop = self._field_source_col.get(field_key, field_key)
                    # Follow Tableau's aggregation exactly: a derivation other than
                    # "None" (Sum/Avg/Count/...) becomes an aggregated measure.
                    aggregated = derivation and derivation != "None"
                    kind = "aggregation" if aggregated else "column"
                    key = (kind, prop)
                    if key in seen:
                        continue
                    seen.add(key)
                    fields.append(
                        ProjectionField(
                            kind=kind,
                            table=table,
                            property=prop,
                            agg=derivation if aggregated else None,
                        )
                    )

            if fields:
                model.worksheets.append(Worksheet(name=ws.get("name", "Sheet"), fields=fields))


def parse_twb(xml_text: str, project_name: str) -> Model:
    return TwbParser(xml_text, project_name).parse()
