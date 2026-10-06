import { Card, Row, Col, Progress, Tag, Typography, Space } from "antd";
import { scoreColor, gradeColor } from "../../components/severity.js";

const { Text, Title } = Typography;

// Executive scorecard: overall architecture score + grade + per-pillar bars.
export default function Scorecard({ waf }) {
  const overall = waf.overall || {};
  const score = overall.score ?? 0;
  const pillars = waf.pillars || [];

  return (
    <Card size="small">
      <Row gutter={[24, 16]} align="middle">
        <Col xs={24} md={7} style={{ textAlign: "center" }}>
          <Progress
            type="dashboard"
            percent={score}
            format={(p) => (
              <span>
                <div style={{ fontSize: 30, fontWeight: 700 }}>{p}</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>/ 100</div>
              </span>
            )}
            strokeColor={scoreColor(score)}
          />
          <div style={{ marginTop: 8 }}>
            <Space>
              <Tag color={gradeColor(overall.grade)} style={{ fontSize: 16, padding: "2px 12px", fontWeight: 700 }}>
                {overall.grade}
              </Tag>
              <Tag color={scoreColor(score)}>{overall.band}</Tag>
            </Space>
          </div>
          <Title level={5} style={{ marginTop: 10, marginBottom: 0 }}>Architecture Score</Title>
        </Col>

        <Col xs={24} md={17}>
          <Text strong>Pillar scores</Text>
          <div style={{ marginTop: 8 }}>
            {pillars.map((p) => (
              <div key={p.key} style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                  <span>
                    {p.name}{" "}
                    <Text type="secondary">({Math.round((p.weight || 0) * 100)}%)</Text>
                  </span>
                  <span>
                    <Tag color={gradeColor(p.grade)} style={{ marginInlineEnd: 6 }}>{p.grade}</Tag>
                    {p.score}/100
                  </span>
                </div>
                <Progress percent={p.score} showInfo={false} strokeColor={scoreColor(p.score)} size="small" />
              </div>
            ))}
          </div>
        </Col>
      </Row>
    </Card>
  );
}
