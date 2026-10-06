import { Card, Row, Col, Statistic, Tag, Typography, Space } from "antd";
import { BRAND } from "../../theme/brand.js";

const { Paragraph, Text } = Typography;

// Executive summary: headline statement, strengths/weaknesses, P1/P2/P3 counts.
export default function ExecutiveSummary({ waf }) {
  const es = waf.executiveSummary || {};
  const counts = es.counts || {};

  return (
    <Card size="small" title="Executive Summary">
      <Paragraph>{es.statement}</Paragraph>
      <Row gutter={[12, 12]}>
        <Col xs={8} md={4}><Card size="small"><Statistic title="P1 (critical)" value={counts.P1 ?? 0} valueStyle={{ color: BRAND.error }} /></Card></Col>
        <Col xs={8} md={4}><Card size="small"><Statistic title="P2 (medium)" value={counts.P2 ?? 0} valueStyle={{ color: BRAND.warning }} /></Card></Col>
        <Col xs={8} md={4}><Card size="small"><Statistic title="P3 (low)" value={counts.P3 ?? 0} valueStyle={{ color: BRAND.info }} /></Card></Col>
      </Row>
      <div style={{ marginTop: 12 }}>
        <Space direction="vertical" size={6} style={{ width: "100%" }}>
          <div>
            <Text type="secondary">Strengths: </Text>
            {es.strengths?.length ? <Space wrap size={4}>{es.strengths.map((s) => <Tag color="green" key={s}>{s}</Tag>)}</Space> : <Text type="secondary">—</Text>}
          </div>
          <div>
            <Text type="secondary">Focus areas: </Text>
            {es.weaknesses?.length ? <Space wrap size={4}>{es.weaknesses.map((s) => <Tag color="red" key={s}>{s}</Tag>)}</Space> : <Text type="secondary">None critical</Text>}
          </div>
        </Space>
      </div>
    </Card>
  );
}
