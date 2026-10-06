import { Card, List, Tag, Typography, Empty } from "antd";
import { ThunderboltTwoTone } from "@ant-design/icons";
import { BRAND } from "../../theme/brand.js";

const { Text } = Typography;

const PRIORITY_COLOR = { P1: "red", P2: "orange", P3: "gold" };

// Low-effort, high-value fixes surfaced from the roadmap.
export default function QuickWins({ quickWins }) {
  if (!quickWins?.length) {
    return (
      <Card size="small" title="Quick Wins">
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No quick wins identified." />
      </Card>
    );
  }
  return (
    <Card size="small" title="Quick Wins">
      <List
        size="small"
        dataSource={quickWins}
        renderItem={(w) => (
          <List.Item>
            <List.Item.Meta
              avatar={<ThunderboltTwoTone twoToneColor={BRAND.accent} />}
              title={<span><Text strong>{w.title}</Text> <Tag color={PRIORITY_COLOR[w.priority]}>{w.priority}</Tag> <Text type="secondary" style={{ fontSize: 12 }}>· {w.pillar}</Text></span>}
              description={
                <span style={{ fontSize: 12 }}>
                  {w.action}{w.benefit && <Text type="success" style={{ fontSize: 11 }}> — ▲ {w.benefit}</Text>}
                </span>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
}
