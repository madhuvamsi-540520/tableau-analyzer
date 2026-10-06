import { Tag, Typography, Empty, Space } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";

const dash = (v) => (v == null || v === "" ? <Typography.Text type="secondary">—</Typography.Text> : v);

const JOIN_COLOR = { inner: "blue", left: "green", right: "gold", full: "purple" };

export default function Relationships({ relationships }) {
  if (!relationships?.length) return <Empty description="No joins or relationships found." />;

  const columns = [
    {
      title: "Kind",
      dataIndex: "kind",
      render: (v) => <Tag color={v === "join" ? "geekblue" : "cyan"}>{v}</Tag>,
      filters: [
        { text: "join", value: "join" },
        { text: "relationship", value: "relationship" },
      ],
      onFilter: (v, r) => r.kind === v,
    },
    { title: "Parent Table", dataIndex: "parentTable", sorter: (a, b) => a.parentTable.localeCompare(b.parentTable) },
    { title: "Child Table", dataIndex: "childTable" },
    {
      title: "Join Type",
      dataIndex: "joinType",
      render: (v) => (v ? <Tag color={JOIN_COLOR[v] || "default"}>{v}</Tag> : dash(v)),
    },
    { title: "Cardinality", dataIndex: "cardinality", render: dash },
    {
      title: "Join Keys",
      dataIndex: "joinKeys",
      render: (keys) => (
        <Space direction="vertical" size={0}>
          {(keys || []).map((k, i) => (
            <Typography.Text key={i} code>
              {k}
            </Typography.Text>
          ))}
        </Space>
      ),
    },
  ];

  const data = relationships.map((r, i) => ({ ...r, _key: i }));
  return (
    <SearchableTable
      rowKey="_key"
      columns={columns}
      data={data}
      searchFields={["parentTable", "childTable", "kind", "joinType"]}
      placeholder="Search relationships…"
    />
  );
}
