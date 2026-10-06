import { Alert, Card, Col, Row, Space, Statistic, Tag, Typography } from "antd";
import { ApartmentOutlined } from "@ant-design/icons";

const MODEL_COLOR = {
  "Star Schema": "gold",
  "Snowflake Schema": "cyan",
  "Flat Model": "default",
  "Hybrid Model": "orange",
};

function modelColor(type) {
  if (!type) return "default";
  if (type.startsWith("Galaxy")) return "purple";
  return MODEL_COLOR[type] || "blue";
}

export default function Classification({ ds, complexity }) {
  const cls = ds.classification || {};
  const metrics = [
    { label: "Tables", value: ds.counts?.tables },
    { label: "Joins", value: ds.counts?.joins },
    { label: "Relationships", value: ds.counts?.relationships },
    { label: "Calc Fields", value: ds.counts?.calculatedFields },
    { label: "Filters", value: ds.counts?.filters },
    { label: "Custom SQL", value: ds.counts?.customSql },
    { label: "Parameters", value: complexity?.parameters },
    { label: "Unions", value: ds.counts?.unions },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card size="small">
        <Space align="start">
          <ApartmentOutlined style={{ fontSize: 22, color: "var(--accent)", marginTop: 4 }} />
          <div>
            <Space wrap>
              <Typography.Text strong>Data Model:</Typography.Text>
              <Tag color={modelColor(cls.type)} style={{ fontSize: 14, padding: "2px 10px" }}>
                {cls.type || "Unknown"}
              </Tag>
            </Space>
            <div style={{ marginTop: 6 }}>
              {(cls.reasoning || []).map((r, i) => (
                <Typography.Paragraph key={i} style={{ marginBottom: 4 }} type="secondary">
                  {r}
                </Typography.Paragraph>
              ))}
            </div>
            <Space wrap size={4} style={{ marginTop: 4 }}>
              {(cls.factTables || []).map((t) => (
                <Tag key={t} color="volcano">
                  fact: {t}
                </Tag>
              ))}
              {(cls.dimensionTables || []).map((t) => (
                <Tag key={t} color="blue">
                  dim: {t}
                </Tag>
              ))}
            </Space>
          </div>
        </Space>
      </Card>

      <Row gutter={[12, 12]}>
        {metrics.map((m) => (
          <Col key={m.label} xs={12} sm={8} md={6} lg={6}>
            <Card size="small">
              <Statistic title={m.label} value={m.value ?? 0} />
            </Card>
          </Col>
        ))}
      </Row>

      <Alert
        type="info"
        showIcon
        message="Classification is structural"
        description="The model shape is inferred from the join/relationship graph and where measures live (no live data is read). Facts are measure-bearing hubs; dimensions are the tables joined to them."
      />
    </Space>
  );
}
