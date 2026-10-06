import { Table, Tag, Space, Empty, Typography } from "antd";

const { Text } = Typography;

function sheetTags(ws) {
  return ws?.length
    ? <Space wrap size={4}>{ws.map((w) => <Tag key={w} color="geekblue">{w}</Tag>)}</Space>
    : <Text type="secondary">none</Text>;
}

export default function DashboardStoryInventory({ metadata }) {
  const dashboards = metadata.dashboards || [];
  const stories = metadata.stories || [];

  return (
    <Space direction="vertical" size={18} style={{ width: "100%" }}>
      <div>
        <Text strong>Dashboards ({dashboards.length})</Text>
        {dashboards.length ? (
          <Table
            style={{ marginTop: 8 }}
            size="small"
            rowKey="name"
            pagination={false}
            columns={[
              { title: "Dashboard", dataIndex: "name" },
              { title: "Worksheets", dataIndex: "worksheets", render: sheetTags },
              { title: "#", dataIndex: "worksheets", align: "right", render: (w) => (w || []).length },
            ]}
            dataSource={dashboards}
          />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No dashboards" />
        )}
      </div>

      <div>
        <Text strong>Stories ({stories.length})</Text>
        {stories.length ? (
          <Table
            style={{ marginTop: 8 }}
            size="small"
            rowKey="name"
            pagination={false}
            columns={[
              { title: "Story", dataIndex: "name" },
              { title: "Story Points", dataIndex: "storyPoints", align: "right" },
              { title: "Worksheets", dataIndex: "worksheets", render: sheetTags },
            ]}
            dataSource={stories}
          />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No stories" />
        )}
      </div>
    </Space>
  );
}
