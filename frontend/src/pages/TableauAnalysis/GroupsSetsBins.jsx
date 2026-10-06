import { Table, Tag, Space, Empty, Typography } from "antd";

const { Text } = Typography;

export default function GroupsSetsBins({ metadata }) {
  const dss = metadata.dataSources || [];
  const groups = dss.flatMap((ds) => (ds.groups || []).map((g) => ({ ...g, _ds: ds.caption || ds.name })));
  const sets = dss.flatMap((ds) => (ds.sets || []).map((s) => ({ ...s, _ds: ds.caption || ds.name })));
  const bins = dss.flatMap((ds) => (ds.bins || []).map((b) => ({ ...b, _ds: ds.caption || ds.name })));

  if (!groups.length && !sets.length && !bins.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No groups, sets or bins found." />;
  }

  const block = (title, rows, columns) =>
    rows.length ? (
      <div>
        <Text strong>{title} ({rows.length})</Text>
        <Table style={{ marginTop: 8 }} size="small" rowKey={(r, i) => r.name + i} pagination={false} columns={columns} dataSource={rows} />
      </div>
    ) : null;

  return (
    <Space direction="vertical" size={18} style={{ width: "100%" }}>
      {block("Groups", groups, [
        { title: "Group", dataIndex: "name" },
        { title: "From Field", dataIndex: "sourceField" },
        { title: "Sub-groups", dataIndex: "groupCount", align: "right" },
        {
          title: "Members",
          dataIndex: "groups",
          render: (g) => <Space wrap size={4}>{(g || []).map((m, i) => <Tag key={i}>{m.name}: {(m.values || []).join(", ")}</Tag>)}</Space>,
        },
      ])}
      {block("Sets", sets, [
        { title: "Set", dataIndex: "name" },
        { title: "From Field", dataIndex: "sourceField", render: (v) => v || <Text type="secondary">—</Text> },
        { title: "Kind", dataIndex: "kind", render: (v) => <Tag color="purple">{v}</Tag> },
      ])}
      {block("Bins", bins, [
        { title: "Bin", dataIndex: "name" },
        { title: "From Field", dataIndex: "sourceField" },
        { title: "Bin Size", dataIndex: "size", render: (v) => v || <Text type="secondary">—</Text> },
      ])}
    </Space>
  );
}
