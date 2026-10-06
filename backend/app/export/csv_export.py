"""Export the flat column inventory as CSV (the most granular inventory grain)."""
from __future__ import annotations

import csv
import io


def build_columns_csv(metadata: dict) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["Data Source", "Table", "Column", "Original Name", "Data Type", "Role",
         "Default Aggregation", "Hidden", "Nullable"]
    )
    for ds in metadata.get("dataSources", []):
        ds_name = ds.get("caption") or ds.get("name")
        for t in ds.get("tables", []):
            for c in t.get("columns", []):
                writer.writerow([
                    ds_name, t.get("name"), c.get("name"), c.get("originalName"),
                    c.get("dataType"), c.get("role"), c.get("defaultAggregation") or "",
                    c.get("hidden"), c.get("nullable"),
                ])
    # UTF-8 BOM so Excel opens it with correct encoding.
    return buf.getvalue().encode("utf-8-sig")
