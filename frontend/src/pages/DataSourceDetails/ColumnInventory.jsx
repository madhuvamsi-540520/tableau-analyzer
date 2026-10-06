import { useMemo } from "react";
import { Empty } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";
import { columnColumns } from "./ColumnList.jsx";

// Flat inventory of every column across all tables in the data source.
export default function ColumnInventory({ tables }) {
  const rows = useMemo(
    () =>
      (tables || []).flatMap((t) =>
        (t.columns || []).map((c, i) => ({ ...c, _table: t.name, _key: `${t.name}.${c.name}.${i}` }))
      ),
    [tables]
  );

  if (!rows.length) return <Empty description="No columns found." />;

  const cols = columnColumns({ withTable: true }).map((c) =>
    c.dataIndex === "_table"
      ? {
          ...c,
          filters: [...new Set(rows.map((r) => r._table))].map((t) => ({ text: t, value: t })),
          onFilter: (v, r) => r._table === v,
        }
      : c
  );

  return (
    <SearchableTable
      rowKey="_key"
      columns={cols}
      data={rows}
      searchFields={["name", "originalName", "_table", "dataType"]}
      placeholder="Search columns…"
      pageSize={15}
    />
  );
}
