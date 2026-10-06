import { Card, Row, Col, Progress, Space, Typography, Tag, Collapse, List, Divider } from "antd";
import FindingList from "./FindingList.jsx";
import { SEVERITY_COLOR, scoreColor } from "../../components/severity.js";

const { Text, Title } = Typography;

const SECTIONS = [
  ["technicalDebt", "Technical Debt"],
  ["modelingRisks", "Modeling Risks"],
  ["dataQualityRisks", "Data Quality Risks"],
  ["governance", "Governance Concerns"],
  ["scalability", "Scalability Concerns"],
  ["performance", "Performance Risks"],
  ["optimization", "Optimization Opportunities"],
];

function Maturity({ best }) {
  const score = best.maturityScore ?? 0;
  return (
    <Card size="small">
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} sm={8} md={6} style={{ textAlign: "center" }}>
          <Progress
            type="dashboard"
            percent={score}
            format={(p) => (
              <span>
                <div style={{ fontSize: 26, fontWeight: 700 }}>{p}</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>/ 100</div>
              </span>
            )}
            strokeColor={scoreColor(score)}
          />
          <div>
            <Tag color={scoreColor(score)} style={{ marginTop: 8 }}>
              {best.maturityBand}
            </Tag>
          </div>
        </Col>
        <Col xs={24} sm={16} md={18}>
          <Text strong>Maturity by dimension</Text>
          <div style={{ marginTop: 8 }}>
            {Object.entries(best.dimensions || {}).map(([dim, val]) => (
              <div key={dim} style={{ marginBottom: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                  <span>
                    {dim}{" "}
                    <Text type="secondary">({Math.round((best.weights?.[dim] || 0) * 100)}%)</Text>
                  </span>
                  <span>{val}/100</span>
                </div>
                <Progress percent={val} showInfo={false} strokeColor={scoreColor(val)} size="small" />
              </div>
            ))}
          </div>
        </Col>
      </Row>
    </Card>
  );
}

function Frameworks({ frameworks }) {
  return (
    <Card size="small" title="Enterprise Best-Practice Review">
      <List
        size="small"
        dataSource={frameworks || []}
        renderItem={(f) => (
          <List.Item>
            <Space direction="vertical" size={2} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <Text strong>{f.name}</Text>
                <Text>{f.score}/100</Text>
              </div>
              <Progress percent={f.score} showInfo={false} strokeColor={scoreColor(f.score)} size="small" />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {f.notes}
              </Text>
            </Space>
          </List.Item>
        )}
      />
    </Card>
  );
}

function Tradeoffs({ tradeoffs }) {
  if (!tradeoffs?.length) return null;
  return (
    <Card size="small" title="Technical Trade-offs">
      <Row gutter={[12, 12]}>
        {tradeoffs.map((t, i) => (
          <Col xs={24} md={12} key={i}>
            <Card size="small" type="inner" title={<Space>{t.aspect} <Tag>{t.current}</Tag></Space>}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t.tradeoff}
              </Text>
              <Divider style={{ margin: "8px 0" }} />
              <Text style={{ fontSize: 12 }}>
                <b>Guidance:</b> {t.guidance}
              </Text>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
}

function severitySummaryTags(bySeverity = {}) {
  return ["critical", "high", "medium", "low", "info"]
    .filter((s) => bySeverity[s])
    .map((s) => (
      <Tag key={s} color={SEVERITY_COLOR[s]}>
        {bySeverity[s]} {s}
      </Tag>
    ));
}

export default function TechnicalAssessment({ assessment }) {
  if (!assessment || !assessment.bestPractices) return null;
  const summary = assessment.summary || {};

  const sectionItems = SECTIONS.map(([key, label]) => {
    const findings = assessment[key] || [];
    const worst = findings[0]?.severity;
    return {
      key,
      label: (
        <Space>
          <span>{label}</span>
          <Tag>{findings.length}</Tag>
          {worst && <Tag color={SEVERITY_COLOR[worst]}>{worst}</Tag>}
        </Space>
      ),
      children: <FindingList findings={findings} />,
    };
  });

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div>
        <Title level={5} style={{ margin: 0 }}>
          Technical Assessment
        </Title>
        <Space wrap style={{ marginTop: 6 }}>
          <Text type="secondary">{summary.totalFindings} finding(s):</Text>
          {severitySummaryTags(summary.bySeverity)}
        </Space>
      </div>

      <Maturity best={assessment.bestPractices} />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card size="small" title="Findings by category" styles={{ body: { paddingTop: 4 } }}>
            <Collapse
              ghost
              items={sectionItems}
              defaultActiveKey={["modelingRisks", "dataQualityRisks", "governance"]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Frameworks frameworks={assessment.bestPractices.frameworks} />
        </Col>
      </Row>

      <Tradeoffs tradeoffs={assessment.tradeoffs} />
    </Space>
  );
}
