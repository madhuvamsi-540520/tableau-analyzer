import { Tag, Typography } from "antd";
import { Table } from "antd";
import { RoleTag, BoolMark } from "../../components/badges.jsx";

const dash = (v) => (v == null || v === "" ? <Typography.Text type="secondary">—</Typography.Text> : v);

// Column definitions shared by the inline (per-table) and flat column views.
export function columnColumns({ withTable } = {}) {
  const cols = [
    { title: "Column", dataIndex: "name", sorter: (a, b) => a.name.localeCompare(b.name) },
    { title: "Original Name", dataIndex: "originalName", render: dash },
    {
      title: "Data Type",
      dataIndex: "dataType",
      render: (v) => <Tag>{v}</Tag>,
      filters: [
        "integer", "real", "string", "boolean", "date", "datetime",
      ].map((t) => ({ text: t, value: t })),
      onFilter: (v, r) => r.dataType === v,
    },
    {
      title: "Role",
      dataIndex: "role",
      render: (v) => <RoleTag role={v} />,
      filters: [
        { text: "dimension", value: "dimension" },
        { text: "measure", value: "measure" },
      ],
      onFilter: (v, r) => r.role === v,
    },
    { title: "Default Agg.", dataIndex: "defaultAggregation", render: dash },
    { title: "Hidden", dataIndex: "hidden", align: "center", render: (v) => <BoolMark value={v} /> },
    { title: "Nullable", dataIndex: "nullable", align: "center", render: (v) => <BoolMark value={v} /> },
  ];
  if (withTable) {
    cols.unshift({
      title: "Table",
      dataIndex: "_table",
      sorter: (a, b) => a._table.localeCompare(b._table),
    });
  }
  return cols;
}

// Compact inline column table used inside an expanded Table Inventory row.
export default function ColumnList({ columns }) {
  return (
    <Table
      size="small"
      rowKey={(r) => r.name + r.originalName}
      columns={columnColumns()}
      dataSource={columns}
      pagination={columns.length > 8 ? { pageSize: 8 } : false}
      scroll={{ x: "max-content" }}
    />
  );
}
