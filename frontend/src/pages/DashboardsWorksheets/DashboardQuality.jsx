import { Card, Tag, Typography, Space, Empty, Progress, Collapse, List } from "antd";
import { scoreColor, gradeColor, SEVERITY_COLOR } from "../../components/severity.js";

const { Text } = Typography;

// Per-dashboard quality score from parsed layout composition.
export default function DashboardQuality({ quality }) {
  const dashboards = quality?.dashboards || [];
  if (!dashboards.length) {
    return (
      <Card title="Dashboard Quality Assessment" size="small">
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No dashboards to assess." />
      </Card>
    );
  }

  const items = dashboards.map((d, i) => ({
    key: String(i),
    label: (
      <Space wrap>
        <Progress type="circle" percent={d.score} size={34} strokeColor={scoreColor(d.score)} />
        <Text strong>{d.name}</Text>
        <Tag color={gradeColor(d.grade)}>{d.grade}</Tag>
        <Tag>{d.density}</Tag>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {d.worksheetCount} sheets · {d.filterCount} filters · {d.legendCount} legends · {d.actionCount} actions
          {d.usedAreaRatio != null && ` · ${Math.round(d.usedAreaRatio * 100)}% density`}
        </Text>
      </Space>
    ),
    children: d.findings?.length ? (
      <List
        size="small"
        dataSource={d.findings}
        renderItem={(f) => (
          <List.Item>
            <List.Item.Meta
              title={<span><Tag color={SEVERITY_COLOR[f.severity]}>{f.severity}</Tag>{f.title}</span>}
              description={<span style={{ fontSize: 12 }}>{f.detail} <Text type="secondary">— {f.recommendation}</Text></span>}
            />
          </List.Item>
        )}
      />
    ) : (
      <Text type="secondary">No quality issues detected for this dashboard.</Text>
    ),
  }));

  return (
    <Card
      title="Dashboard Quality Assessment"
      size="small"
      extra={<Tag color={scoreColor(quality.averageScore)}>Avg {quality.averageScore}/100</Tag>}
    >
      <Collapse accordion items={items} />
    </Card>
  );
}
