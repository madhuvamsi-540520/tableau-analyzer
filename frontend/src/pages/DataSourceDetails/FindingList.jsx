import { List, Tag, Typography, Space, Empty } from "antd";
import { SEVERITY_COLOR } from "../../components/severity.js";

const { Text } = Typography;

export default function FindingList({ findings, emptyText = "No issues detected in this category." }) {
  if (!findings?.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />;

  return (
    <List
      size="small"
      dataSource={findings}
      renderItem={(f) => (
        <List.Item>
          <Space direction="vertical" size={2} style={{ width: "100%" }}>
            <Space wrap>
              <Tag color={SEVERITY_COLOR[f.severity] || "default"}>{f.severity}</Tag>
              <Text strong>{f.title}</Text>
            </Space>
            {f.businessImpact && (
              <Text type="secondary">
                <b>Business impact:</b> {f.businessImpact}
              </Text>
            )}
            {f.recommendation && (
              <Text>
                <b>Recommendation:</b> {f.recommendation}
              </Text>
            )}
            {f.evidence?.length > 0 && (
              <Space wrap size={4} style={{ marginTop: 2 }}>
                {f.evidence.map((e, i) => (
                  <Tag key={i} style={{ fontFamily: "Consolas, monospace", fontSize: 11 }}>
                    {e}
                  </Tag>
                ))}
              </Space>
            )}
          </Space>
        </List.Item>
      )}
    />
  );
}
