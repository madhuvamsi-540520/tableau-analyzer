import { Card, List, Tag, Typography } from "antd";
import { ClockCircleOutlined } from "@ant-design/icons";

const { Text } = Typography;

// Pillars that inspect a GENERATED Power BI project — shown as clearly-labelled
// placeholders until PBIP generation is wired in (no fabricated data).
export default function PbipPending({ pending }) {
  if (!pending?.length) return null;
  return (
    <Card
      size="small"
      title={<span><ClockCircleOutlined /> Available after PBIP generation</span>}
      style={{ opacity: 0.85 }}
    >
      <Text type="secondary" style={{ display: "block", marginBottom: 8, fontSize: 12 }}>
        These pillars analyze a generated Power BI (PBIP) project. This app currently analyzes the
        Tableau workbook; they activate once PBIP generation is enabled.
      </Text>
      <List
        size="small"
        dataSource={pending}
        renderItem={(p) => (
          <List.Item>
            <List.Item.Meta
              title={<span><Text strong>{p.name}</Text> <Tag>Planned</Tag></span>}
              description={<Text type="secondary" style={{ fontSize: 12 }}>{p.reason}</Text>}
            />
          </List.Item>
        )}
      />
    </Card>
  );
}
