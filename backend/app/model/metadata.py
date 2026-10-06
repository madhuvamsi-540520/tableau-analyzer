"""Canonical metadata model for an analyzed Tableau workbook.

The parser produces this structured model from the workbook XML; the API and
exports consume it. Phase B populates data sources, connections, tables and
columns. Later phases add relationships, joins, unions, filters, custom SQL,
parameters, calculated fields, classification and the technical assessment;
those fields are declared with empty defaults so the model shape stays stable.

``to_api()`` emits a camelCase dict for the frontend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# Columns
# --------------------------------------------------------------------------- #
@dataclass
class ColumnMeta:
    name: str                               # field/display name (caption if renamed, else source)
    original_name: str                      # remote/source column name
    data_type: str                          # tableau datatype: integer/real/string/boolean/date/datetime
    role: str = "dimension"                 # dimension | measure
    alias: Optional[str] = None             # user rename (caption), if any
    default_aggregation: Optional[str] = None
    type_category: Optional[str] = None     # quantitative | ordinal | nominal
    hidden: bool = False
    nullable: Optional[bool] = None         # from <contains-null> when available
    calculated: bool = False
    ordinal: Optional[int] = None

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "originalName": self.original_name,
            "alias": self.alias,
            "dataType": self.data_type,
            "role": self.role,
            "defaultAggregation": self.default_aggregation,
            "typeCategory": self.type_category,
            "hidden": self.hidden,
            "nullable": self.nullable,
            "calculated": self.calculated,
        }


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
@dataclass
class TableMeta:
    name: str                               # table/relation name (e.g. "Orders")
    kind: str = "table"                     # table | custom-sql | text | federated
    caption: Optional[str] = None
    schema: Optional[str] = None
    database: Optional[str] = None
    alias: Optional[str] = None
    connection_name: Optional[str] = None
    row_count: Optional[int] = None         # if available (bundled flat file / extract), else None
    is_extract: bool = False                # extract storage artifact (not a real table)
    columns: list[ColumnMeta] = field(default_factory=list)

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "caption": self.caption,
            "schema": self.schema,
            "database": self.database,
            "alias": self.alias,
            "connectionName": self.connection_name,
            "rowCount": self.row_count,
            "isExtract": self.is_extract,
            "columnCount": len(self.columns),
            "columns": [c.to_api() for c in self.columns],
        }


# --------------------------------------------------------------------------- #
# Connections
# --------------------------------------------------------------------------- #
@dataclass
class ConnectionMeta:
    name: str                               # named-connection id
    cls: str                                # raw Tableau connection class
    friendly_type: str                      # "SQL Server", "Snowflake", "Excel", ...
    caption: Optional[str] = None
    server: Optional[str] = None
    port: Optional[str] = None
    database: Optional[str] = None
    schema: Optional[str] = None
    warehouse: Optional[str] = None
    catalog: Optional[str] = None
    authentication: Optional[str] = None
    username: Optional[str] = None
    owner: Optional[str] = None
    filename: Optional[str] = None
    directory: Optional[str] = None
    is_extract: bool = False
    extra: dict = field(default_factory=dict)

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "class": self.cls,
            "friendlyType": self.friendly_type,
            "caption": self.caption,
            "server": self.server,
            "port": self.port,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
            "catalog": self.catalog,
            "authentication": self.authentication,
            "username": self.username,
            "owner": self.owner,
            "fileLocation": self.filename,
            "directory": self.directory,
            "isExtract": self.is_extract,
            "extra": self.extra,
        }


# --------------------------------------------------------------------------- #
# Relationships & joins
# --------------------------------------------------------------------------- #
@dataclass
class JoinCondition:
    left: str                               # "Orders.Order ID"
    op: str                                 # "=", "<", ...
    right: str                              # "Returns.Order ID"

    def to_api(self) -> dict:
        return {"left": self.left, "op": self.op, "right": self.right}


@dataclass
class RelationshipMeta:
    kind: str                               # "join" (physical) | "relationship" (logical)
    left_table: str
    right_table: str
    join_type: Optional[str] = None         # inner | left | right | full (physical joins)
    cardinality: Optional[str] = None       # e.g. "many-to-one" (logical relationships)
    conditions: list[JoinCondition] = field(default_factory=list)

    def to_api(self) -> dict:
        return {
            "kind": self.kind,
            "parentTable": self.left_table,
            "childTable": self.right_table,
            "joinType": self.join_type,
            "cardinality": self.cardinality,
            "conditions": [c.to_api() for c in self.conditions],
            "joinKeys": [f"{c.left} {c.op} {c.right}" for c in self.conditions],
        }


# --------------------------------------------------------------------------- #
# Unions
# --------------------------------------------------------------------------- #
@dataclass
class UnionMeta:
    name: str
    union_type: str = "manual"              # manual | wildcard
    tables: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "unionType": self.union_type,
            "tables": self.tables,
            "conditions": self.conditions,
        }


# --------------------------------------------------------------------------- #
# Data source filters
# --------------------------------------------------------------------------- #
@dataclass
class FilterMeta:
    field: str
    filter_type: str                        # include | exclude | range | wildcard | relative-date | condition | formula
    filter_class: str                       # categorical | quantitative | relative-date | ...
    values: list[str] = field(default_factory=list)
    expression: str = ""

    def to_api(self) -> dict:
        return {
            "field": self.field,
            "filterType": self.filter_type,
            "filterClass": self.filter_class,
            "values": self.values,
            "expression": self.expression,
        }


# --------------------------------------------------------------------------- #
# Custom SQL
# --------------------------------------------------------------------------- #
@dataclass
class CustomSqlMeta:
    name: str
    sql: str
    analysis: dict = field(default_factory=dict)

    def to_api(self) -> dict:
        return {"name": self.name, "sql": self.sql, "analysis": self.analysis}


# --------------------------------------------------------------------------- #
# Calculated fields
# --------------------------------------------------------------------------- #
@dataclass
class CalcMeta:
    name: str
    formula: str = ""
    categories: list[str] = field(default_factory=list)
    lod: Optional[str] = None
    table_calc: bool = False
    migration_complexity: str = "Low"          # Low | Medium | High | Very High
    power_bi_support: str = "Direct"           # Direct | Rewrite | Manual | Unsupported
    note: str = ""
    # --- Calculation-intelligence enrichment (DAX & Formula module, all optional /
    #     additive; populated by app.dax.engine, empty when the engine is skipped). ---
    data_source: Optional[str] = None                       # owning datasource caption
    worksheets: list[str] = field(default_factory=list)     # sheets that use this calc
    dashboards: list[str] = field(default_factory=list)     # dashboards that surface it
    referenced_fields: list[str] = field(default_factory=list)
    referenced_tables: list[str] = field(default_factory=list)
    dependencies: dict = field(default_factory=dict)        # {parents, children, parameters, depth}
    performance: dict = field(default_factory=dict)         # {rating, riskLevel, recommendation, signals}
    data_types: dict = field(default_factory=dict)          # {inputs, output, conversions, issues}
    dax: dict = field(default_factory=dict)                 # offline conversion suggestion
    estimated_effort_hours: Optional[float] = None
    automation_feasibility: Optional[str] = None
    conversion_confidence: Optional[float] = None

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "formula": self.formula,
            "categories": self.categories,
            "lod": self.lod,
            "tableCalc": self.table_calc,
            "migrationComplexity": self.migration_complexity,
            "powerBiSupport": self.power_bi_support,
            "note": self.note,
            # Additive enrichment (see above) — existing keys unchanged.
            "dataSource": self.data_source,
            "worksheets": self.worksheets,
            "dashboards": self.dashboards,
            "referencedFields": self.referenced_fields,
            "referencedTables": self.referenced_tables,
            "dependencies": self.dependencies,
            "performance": self.performance,
            "dataTypes": self.data_types,
            "dax": self.dax,
            "estimatedEffortHours": self.estimated_effort_hours,
            "automationFeasibility": self.automation_feasibility,
            "conversionConfidence": self.conversion_confidence,
        }


# --------------------------------------------------------------------------- #
# Groups / sets / bins (created fields alongside calculations)
# --------------------------------------------------------------------------- #
@dataclass
class BinMeta:
    name: str
    source_field: Optional[str] = None
    size: Optional[str] = None

    def to_api(self) -> dict:
        return {"name": self.name, "sourceField": self.source_field, "size": self.size}


@dataclass
class GroupMeta:
    name: str
    source_field: Optional[str] = None
    groups: list[dict] = field(default_factory=list)   # [{name, values:[...]}]

    def to_api(self) -> dict:
        return {"name": self.name, "sourceField": self.source_field,
                "groupCount": len(self.groups), "groups": self.groups}


@dataclass
class SetMeta:
    name: str
    source_field: Optional[str] = None
    kind: str = "set"                                  # set | dynamic-set | in-out

    def to_api(self) -> dict:
        return {"name": self.name, "sourceField": self.source_field, "kind": self.kind}


# --------------------------------------------------------------------------- #
# Parameters
# --------------------------------------------------------------------------- #
@dataclass
class ParameterMeta:
    name: str
    data_type: Optional[str] = None
    current_value: Optional[str] = None
    domain_type: Optional[str] = None       # all | list | range

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "dataType": self.data_type,
            "currentValue": self.current_value,
            "domainType": self.domain_type,
        }


# --------------------------------------------------------------------------- #
# Data source
# --------------------------------------------------------------------------- #
@dataclass
class DataSourceMeta:
    name: str                               # internal name (federated.xxx)
    caption: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    connection_mode: str = "Live"           # "Live" | "Extract"
    is_extract: bool = False
    is_published: bool = False
    connections: list[ConnectionMeta] = field(default_factory=list)
    tables: list[TableMeta] = field(default_factory=list)
    relationships: list[RelationshipMeta] = field(default_factory=list)
    unions: list[UnionMeta] = field(default_factory=list)
    filters: list[FilterMeta] = field(default_factory=list)
    custom_sql: list[CustomSqlMeta] = field(default_factory=list)
    calculated_field_names: list[str] = field(default_factory=list)
    calculations: list[CalcMeta] = field(default_factory=list)
    groups: list[GroupMeta] = field(default_factory=list)
    sets: list[SetMeta] = field(default_factory=list)
    bins: list[BinMeta] = field(default_factory=list)
    classification: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def friendly_types(self) -> list[str]:
        seen: list[str] = []
        for c in self.connections:
            if c.friendly_type not in seen:
                seen.append(c.friendly_type)
        return seen

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "caption": self.caption or self.name,
            "description": self.description,
            "version": self.version,
            "connectionMode": self.connection_mode,
            "isExtract": self.is_extract,
            "isPublished": self.is_published,
            "dataSourceTypes": self.friendly_types,
            "counts": {
                "connections": len(self.connections),
                "tables": len(self.tables),
                "columns": sum(len(t.columns) for t in self.tables),
                "relationships": len(self.relationships),
                "joins": sum(1 for r in self.relationships if r.kind == "join"),
                "unions": len(self.unions),
                "filters": len(self.filters),
                "customSql": len(self.custom_sql),
                "calculatedFields": len(self.calculated_field_names),
                "groups": len(self.groups),
                "sets": len(self.sets),
                "bins": len(self.bins),
            },
            "classification": self.classification,
            "calculations": [c.to_api() for c in self.calculations],
            "groups": [g.to_api() for g in self.groups],
            "sets": [s.to_api() for s in self.sets],
            "bins": [b.to_api() for b in self.bins],
            "connections": [c.to_api() for c in self.connections],
            "tables": [t.to_api() for t in self.tables],
            "relationships": [r.to_api() for r in self.relationships],
            "unions": [u.to_api() for u in self.unions],
            "filters": [f.to_api() for f in self.filters],
            "customSql": [s.to_api() for s in self.custom_sql],
            "calculatedFields": self.calculated_field_names,
            "warnings": self.warnings,
        }


# --------------------------------------------------------------------------- #
# Worksheets / dashboards / stories
# --------------------------------------------------------------------------- #
@dataclass
class FieldUse:
    field: str
    role: Optional[str] = None              # dimension | measure
    aggregation: Optional[str] = None       # Sum / None / Count ... (Tableau derivation)
    data_type: Optional[str] = None

    def to_api(self) -> dict:
        return {"field": self.field, "role": self.role,
                "aggregation": self.aggregation, "dataType": self.data_type}


@dataclass
class EncodingUse:
    channel: str                            # color | size | shape | label | detail | text | tooltip | path | angle | rows | cols
    field: Optional[str] = None

    def to_api(self) -> dict:
        return {"channel": self.channel, "field": self.field}


@dataclass
class WorksheetMeta:
    name: str
    data_sources: list[str] = field(default_factory=list)   # captions
    mark_class: Optional[str] = None
    fields: list[FieldUse] = field(default_factory=list)
    encodings: list[EncodingUse] = field(default_factory=list)
    rows_shelf: list[str] = field(default_factory=list)
    cols_shelf: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)        # field names filtered on this sheet
    analytics: list[str] = field(default_factory=list)      # reference-line / trend / forecast / band
    # Set by the visual-detection engine (later phase).
    visual_type: Optional[str] = None
    visual_confidence: Optional[float] = None
    visual_reasoning: list[str] = field(default_factory=list)

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "dataSources": self.data_sources,
            "markClass": self.mark_class,
            "fields": [f.to_api() for f in self.fields],
            "encodings": [e.to_api() for e in self.encodings],
            "rows": self.rows_shelf,
            "cols": self.cols_shelf,
            "filters": self.filters,
            "analytics": self.analytics,
            "visualType": self.visual_type,
            "visualConfidence": self.visual_confidence,
            "visualReasoning": self.visual_reasoning,
        }


@dataclass
class DashboardMeta:
    name: str
    worksheets: list[str] = field(default_factory=list)
    # --- Layout / composition detail (Dashboards & Worksheets module; all additive
    #     and best-effort — populated by the parser from the primary <zones> layout). ---
    zone_count: int = 0
    filter_count: int = 0
    legend_count: int = 0
    parameter_count: int = 0
    text_count: int = 0
    image_count: int = 0
    web_count: int = 0
    extension_count: int = 0
    action_count: int = 0
    used_area_ratio: Optional[float] = None      # sum(worksheet zone area) / canvas, 0..1
    has_device_layouts: bool = False
    width: Optional[int] = None
    height: Optional[int] = None

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "worksheets": self.worksheets,
            "worksheetCount": len(self.worksheets),
            "zoneCount": self.zone_count,
            "filterCount": self.filter_count,
            "legendCount": self.legend_count,
            "parameterCount": self.parameter_count,
            "textCount": self.text_count,
            "imageCount": self.image_count,
            "webCount": self.web_count,
            "extensionCount": self.extension_count,
            "actionCount": self.action_count,
            "usedAreaRatio": self.used_area_ratio,
            "hasDeviceLayouts": self.has_device_layouts,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class StoryMeta:
    name: str
    story_points: int = 0
    worksheets: list[str] = field(default_factory=list)

    def to_api(self) -> dict:
        return {"name": self.name, "storyPoints": self.story_points, "worksheets": self.worksheets}


# --------------------------------------------------------------------------- #
# Workbook
# --------------------------------------------------------------------------- #
@dataclass
class WorkbookMetadata:
    name: str
    version: Optional[str] = None
    source_platform: Optional[str] = None
    source_build: Optional[str] = None
    author: Optional[str] = None
    last_modified: Optional[str] = None
    data_sources: list[DataSourceMeta] = field(default_factory=list)
    parameters: list[ParameterMeta] = field(default_factory=list)
    worksheets: list[WorksheetMeta] = field(default_factory=list)
    dashboards: list[DashboardMeta] = field(default_factory=list)
    stories: list[StoryMeta] = field(default_factory=list)
    features: dict = field(default_factory=dict)   # actions / deviceLayouts / extensions counts
    assessment: dict = field(default_factory=dict)
    migration: dict = field(default_factory=dict)
    well_architected: dict = field(default_factory=dict)  # Well-Architected PBI Framework report
    rationalization: dict = field(default_factory=dict)   # Dashboard & Worksheet rationalization report
    warnings: list[str] = field(default_factory=list)

    def counts(self) -> dict:
        return {
            "dataSources": len(self.data_sources),
            "connections": sum(len(d.connections) for d in self.data_sources),
            "tables": sum(len(d.tables) for d in self.data_sources),
            "columns": sum(len(t.columns) for d in self.data_sources for t in d.tables),
            "relationships": sum(len(d.relationships) for d in self.data_sources),
            "unions": sum(len(d.unions) for d in self.data_sources),
            "filters": sum(len(d.filters) for d in self.data_sources),
            "customSql": sum(len(d.custom_sql) for d in self.data_sources),
            "worksheets": len(self.worksheets),
            "dashboards": len(self.dashboards),
            "stories": len(self.stories),
        }

    def workbook_summary(self) -> dict:
        """Header summary with de-duplicated object counts and Live/Extract split."""
        live = extract = 0
        for d in self.data_sources:
            for c in d.connections:
                if c.is_extract:
                    extract += 1
                else:
                    live += 1
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "lastModified": self.last_modified,
            "dashboards": len(self.dashboards),
            "worksheets": len(self.worksheets),      # unique worksheets (deduped)
            "stories": len(self.stories),
            "dataSources": len(self.data_sources),
            "parameters": len(self.parameters),
            "filters": sum(len(d.filters) for d in self.data_sources),
            "calculatedFields": sum(len(d.calculated_field_names) for d in self.data_sources),
            "customSql": sum(len(d.custom_sql) for d in self.data_sources),
            "liveConnections": live,
            "extractConnections": extract,
        }

    def complexity(self) -> dict:
        """Connection complexity metrics across the whole workbook."""
        return {
            "tables": sum(len(d.tables) for d in self.data_sources),
            "joins": sum(1 for d in self.data_sources for r in d.relationships if r.kind == "join"),
            "relationships": sum(
                1 for d in self.data_sources for r in d.relationships if r.kind == "relationship"
            ),
            "dataSources": len(self.data_sources),
            "calculatedFields": sum(len(d.calculated_field_names) for d in self.data_sources),
            "filters": sum(len(d.filters) for d in self.data_sources),
            "parameters": len(self.parameters),
            "customSql": sum(len(d.custom_sql) for d in self.data_sources),
        }

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "sourcePlatform": self.source_platform,
            "sourceBuild": self.source_build,
            "author": self.author,
            "lastModified": self.last_modified,
            "counts": self.counts(),
            "complexity": self.complexity(),
            "workbookSummary": self.workbook_summary(),
            "parameters": [p.to_api() for p in self.parameters],
            "worksheets": [w.to_api() for w in self.worksheets],
            "dashboards": [d.to_api() for d in self.dashboards],
            "stories": [s.to_api() for s in self.stories],
            "features": self.features,
            "dataSources": [d.to_api() for d in self.data_sources],
            "assessment": self.assessment,
            "migration": self.migration,
            "wellArchitected": self.well_architected,
            "rationalization": self.rationalization,
            "warnings": self.warnings,
        }
