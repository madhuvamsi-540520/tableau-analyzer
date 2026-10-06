import { Descriptions, Tag, Row, Col, Card, Statistic, Space } from "antd";
import { ModeTag } from "../../components/badges.jsx";

export default function Overview({ ds }) {
  const c = ds.counts || {};
  const tiles = [
    { label: "Connections", value: c.connections },
    { label: "Tables", value: c.tables },
    { label: "Columns", value: c.columns },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Row gutter={[12, 12]}>
        {tiles.map((t) => (
          <Col key={t.label} xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic title={t.label} value={t.value ?? 0} />
            </Card>
          </Col>
        ))}
      </Row>

      <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
        <Descriptions.Item label="Data Source Name">{ds.name}</Descriptions.Item>
        <Descriptions.Item label="Caption">{ds.caption || "—"}</Descriptions.Item>
        <Descriptions.Item label="Description">{ds.description || "—"}</Descriptions.Item>
        <Descriptions.Item label="Version">{ds.version || "—"}</Descriptions.Item>
        <Descriptions.Item label="Data Source Type">
          <Space wrap>
            {(ds.dataSourceTypes || []).map((t) => (
              <Tag key={t} color="geekblue">
                {t}
              </Tag>
            ))}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="Connection">
          <Space>
            <ModeTag mode={ds.connectionMode} />
            {ds.isPublished && <Tag color="purple">Published</Tag>}
          </Space>
        </Descriptions.Item>
      </Descriptions>
    </Space>
  );
}
