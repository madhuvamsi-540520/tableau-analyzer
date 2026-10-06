"""Extract connection metadata from a datasource, with friendly type mapping.

Handles both the federated model (``<connection class='federated'>`` wrapping
``<named-connection>`` entries) and direct single connections. Secrets
(passwords) are never surfaced.
"""
from __future__ import annotations

from xml.etree.ElementTree import Element

from ..model.metadata import ConnectionMeta

# Raw Tableau connection class -> human-facing data source type.
CLASS_TO_TYPE = {
    "sqlserver": "SQL Server",
    "sqlserver-odbc": "SQL Server",
    "oracle": "Oracle",
    "snowflake": "Snowflake",
    "postgres": "PostgreSQL",
    "redshift": "Amazon Redshift",
    "mysql": "MySQL",
    "bigquery": "Google BigQuery",
    "athena": "Amazon Athena",
    "presto": "Presto",
    "awshadoophive": "Amazon EMR Hive",
    "hadoophive": "Hive",
    "spark": "Spark SQL",
    "databricks": "Databricks",
    "vertica": "Vertica",
    "teradata": "Teradata",
    "db2": "IBM Db2",
    "saphana": "SAP HANA",
    "sapbw": "SAP BW",
    "excel-direct": "Excel",
    "excel": "Excel",
    "textscan": "Text / CSV File",
    "csv": "CSV File",
    "hyper": "Tableau Extract (Hyper)",
    "dataengine": "Tableau Extract",
    "tdescan": "Tableau Extract (TDE)",
    "google-sheets": "Google Sheets",
    "googlesheets": "Google Sheets",
    "salesforce": "Salesforce",
    "odbc": "ODBC",
    "genericodbc": "ODBC",
    "msolap": "SSAS (Analysis Services)",
    "azure-sql-dw": "Azure Synapse",
    "azuresqldw": "Azure Synapse",
    "azure_data_lake_storage_gen2": "Azure Data Lake Gen2",
    "sqlproxy": "Published Data Source",
    "federated": "Federated",
}

# Classes whose data is a materialized Tableau extract (not a live source).
EXTRACT_CLASSES = {"hyper", "dataengine", "tdescan", "tde"}
PUBLISHED_CLASSES = {"sqlproxy"}

# Connection attributes we never echo back.
_SECRET_ATTRS = {"password", "token", "access-token", "refresh-token", "secret"}
# Attributes surfaced as first-class fields (so they are not duplicated in `extra`).
_KNOWN_ATTRS = {
    "class", "server", "port", "dbname", "database", "schema", "warehouse",
    "catalog", "authentication", "username", "filename", "directory",
    "one-time-sql", "sslmode",
} | _SECRET_ATTRS


def friendly_type(cls: str | None) -> str:
    if not cls:
        return "Unknown"
    return CLASS_TO_TYPE.get(cls.lower(), cls.replace("-", " ").replace("_", " ").title())


def _from_inner(name: str, caption: str | None, inner: Element) -> ConnectionMeta:
    cls = inner.get("class", "")
    extra = {
        k: v
        for k, v in inner.attrib.items()
        if k not in _KNOWN_ATTRS and (v or "").strip()
    }
    return ConnectionMeta(
        name=name,
        caption=caption,
        cls=cls,
        friendly_type=friendly_type(cls),
        server=inner.get("server") or None,
        port=inner.get("port") or None,
        database=inner.get("dbname") or inner.get("database") or None,
        schema=inner.get("schema") or None,
        warehouse=inner.get("warehouse") or None,
        catalog=inner.get("catalog") or None,
        authentication=inner.get("authentication") or None,
        username=inner.get("username") or None,
        filename=inner.get("filename") or None,
        directory=inner.get("directory") or None,
        is_extract=cls.lower() in EXTRACT_CLASSES,
        extra=extra,
    )


def extract_connections(datasource: Element) -> list[ConnectionMeta]:
    """Return every connection under a ``<datasource>`` element."""
    conns: list[ConnectionMeta] = []
    top = datasource.find("connection")
    if top is None:
        return conns

    if (top.get("class") or "").lower() == "federated":
        named = top.find("named-connections")
        if named is not None:
            for nc in named.findall("named-connection"):
                inner = nc.find("connection")
                if inner is not None:
                    conns.append(_from_inner(nc.get("name", ""), nc.get("caption"), inner))
    else:
        # Direct (non-federated) connection: the datasource connection is the source.
        conns.append(_from_inner(datasource.get("name", ""), datasource.get("caption"), top))

    return conns
