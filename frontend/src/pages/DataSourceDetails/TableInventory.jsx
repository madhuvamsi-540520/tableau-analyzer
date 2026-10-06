import { Tag, Typography, Empty } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";
import ColumnList from "./ColumnList.jsx";

const dash = (v) => (v == null || v === "" ? <Typography.Text type="secondary">—</Typography.Text> : v);

export default function TableInventory({ tables }) {
  if (!tables?.length) return <Empty description="No tables found." />;

  const columns = [
    { title: "Table", dataIndex: "name", sorter: (a, b) => a.name.localeCompare(b.name) },
    {
      title: "Kind",
      dataIndex: "kind",
      render: (v) => <Tag color={v === "custom-sql" ? "volcano" : "default"}>{v}</Tag>,
      filters: [
        { text: "table", value: "table" },
        { text: "custom-sql", value: "custom-sql" },
      ],
      onFilter: (v, r) => r.kind === v,
    },
    { title: "Schema", dataIndex: "schema", render: dash },
    { title: "Database", dataIndex: "database", render: dash },
    { title: "Alias", dataIndex: "alias", render: dash },
    {
      title: "Columns",
      dataIndex: "columnCount",
      align: "right",
      sorter: (a, b) => a.columnCount - b.columnCount,
    },
    {
      title: "Rows",
      dataIndex: "rowCount",
      align: "right",
      sorter: (a, b) => (a.rowCount ?? -1) - (b.rowCount ?? -1),
      render: (v) => (v == null ? <Typography.Text type="secondary">n/a</Typography.Text> : v.toLocaleString()),
    },
  ];

  return (
    <SearchableTable
      rowKey="name"
      columns={columns}
      data={tables}
      searchFields={["name", "schema", "database", "alias", "kind"]}
      placeholder="Search tables…"
      expandable={{
        expandedRowRender: (row) => <ColumnList columns={row.columns} />,
        rowExpandable: (row) => (row.columns || []).length > 0,
      }}
    />
  );
}
