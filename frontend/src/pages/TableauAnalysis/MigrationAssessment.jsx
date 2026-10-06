import { Card, Row, Col, Progress, Statistic, Tag, Table, List, Space, Typography, Empty } from "antd";
import { scoreColor } from "../../components/severity.js";

const { Text, Paragraph } = Typography;

const COMPLEXITY_COLOR = { Low: "green", Medium: "gold", High: "orange", "Very High": "red" };

export default function MigrationAssessment({ migration }) {
  if (!migration || !migration.effort) return <Empty description="No migration estimate available." />;

  const eff = migration.effort;
  const readiness = migration.readiness ?? 0;

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {/* Estimator dashboard */}
      <Row gutter={[12, 12]}>
        <Col xs={24} sm={8} md={6} style={{ textAlign: "center" }}>
          <Card size="small">
            <Progress
              type="dashboard"
              percent={readiness}
              strokeColor={scoreColor(readiness)}
              format={(p) => <span><div style={{ fontSize: 22, fontWeight: 700 }}>{p}</div><div style={{ fontSize: 11, color: "var(--text-secondary)" }}>readiness</div></span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={16} md={18}>
          <Row gutter={[12, 12]}>
            <Col xs={12} md={6}>
              <Card size="small">
                <div style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 6 }}>Complexity</div>
                <Tag color={COMPLEXITY_COLOR[migration.complexity]} style={{ fontSize: 15, padding: "2px 10px" }}>
                  {migration.complexity}
                </Tag>
              </Card>
            </Col>
            <Col xs={12} md={6}><Card size="small"><Statistic title="Effort (hours)" value={eff.hours} /></Card></Col>
            <Col xs={12} md={6}><Card size="small"><Statistic title="Effort (days)" value={eff.days} /></Card></Col>
            <Col xs={12} md={6}><Card size="small"><Statistic title="Effort (weeks)" value={eff.weeks} /></Card></Col>
          </Row>
          <Card size="small" style={{ marginTop: 12 }} title="Recommended Strategy">
            <Paragraph style={{ marginBottom: 0 }}>{migration.strategy}</Paragraph>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card size="small" title="Power BI Components Required">
            <List
              size="small"
              dataSource={migration.powerBiComponents || []}
              renderItem={(c) => (
                <List.Item>
                  <Space direction="vertical" size={0} style={{ width: "100%" }}>
                    <Space>
                      <Text strong>{c.component}</Text>
                      {c.count != null && <Tag color="blue">{c.count}</Tag>}
                    </Space>
                    <Text type="secondary" style={{ fontSize: 12 }}>{c.rationale}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title="Biggest Risks & Challenges" style={{ height: "100%" }}>
            <Text strong>Risks</Text>
            <ul style={{ marginTop: 4 }}>{(migration.risks || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
            <Text strong>Challenges</Text>
            <ul style={{ marginTop: 4 }}>{(migration.challenges || []).map((c, i) => <li key={i}>{c}</li>)}</ul>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="Recommended Priority Order">
        <List size="small" dataSource={migration.priority || []} renderItem={(p) => <List.Item>{p}</List.Item>} />
      </Card>

      {/* Manual migration effort table */}
      <Card size="small" title={`Manual Migration Effort (${(migration.manualEffortItems || []).length} item(s))`}>
        <Table
          size="small"
          rowKey={(r, i) => r.feature + i}
          pagination={(migration.manualEffortItems || []).length > 10 ? { pageSize: 10 } : false}
          scroll={{ x: "max-content" }}
          columns={[
            { title: "Feature", dataIndex: "feature" },
            { title: "Reason", dataIndex: "reason" },
            { title: "Complexity", dataIndex: "complexity", render: (v) => <Tag color={COMPLEXITY_COLOR[v] || "default"}>{v}</Tag> },
            { title: "Suggested Resolution", dataIndex: "resolution" },
            { title: "Est. Hours", dataIndex: "estimatedHours", align: "right" },
          ]}
          dataSource={migration.manualEffortItems || []}
        />
      </Card>
    </Space>
  );
}
