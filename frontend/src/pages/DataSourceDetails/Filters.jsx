import { Tag, Typography, Empty, Space } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";

const TYPE_COLOR = {
  include: "green",
  exclude: "red",
  range: "blue",
  wildcard: "purple",
  formula: "volcano",
  "relative-date": "gold",
};

export default function Filters({ filters }) {
  if (!filters?.length) return <Empty description="No data source filters found." />;

  const columns = [
    { title: "Field", dataIndex: "field", sorter: (a, b) => a.field.localeCompare(b.field) },
    {
      title: "Type",
      dataIndex: "filterType",
      render: (v) => <Tag color={TYPE_COLOR[v] || "default"}>{v}</Tag>,
    },
    { title: "Class", dataIndex: "filterClass", render: (v) => <Tag>{v}</Tag> },
    {
      title: "Applied Values",
      dataIndex: "values",
      render: (vals) =>
        vals?.length ? (
          <Space wrap size={4}>
            {vals.map((v, i) => (
              <Tag key={i}>{v}</Tag>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">—</Typography.Text>
        ),
    },
    { title: "Expression", dataIndex: "expression", render: (v) => <Typography.Text code>{v}</Typography.Text> },
  ];

  const data = filters.map((f, i) => ({ ...f, _key: i }));
  return (
    <SearchableTable
      rowKey="_key"
      columns={columns}
      data={data}
      searchFields={["field", "filterType", "filterClass", "expression"]}
      placeholder="Search filters…"
    />
  );
}
