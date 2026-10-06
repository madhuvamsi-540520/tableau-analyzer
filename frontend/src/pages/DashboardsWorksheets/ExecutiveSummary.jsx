import { Card, Row, Col, Statistic, Progress, Tag, Typography, Space } from "antd";
import {
  DashboardOutlined, AppstoreOutlined, CopyOutlined, MergeCellsOutlined,
  WarningOutlined, ExclamationCircleOutlined, ScissorOutlined, ClockCircleOutlined,
} from "@ant-design/icons";
import { scoreColor, gradeColor } from "../../components/severity.js";
import { BRAND } from "../../theme/brand.js";

const { Text, Title } = Typography;

function Gauge({ score, grade, band, label }) {
  return (
    <div style={{ textAlign: "center" }}>
      <Progress
        type="dashboard" percent={score} strokeColor={scoreColor(score)} size={128}
        format={(p) => (
          <span>
            <div style={{ fontSize: 26, fontWeight: 700 }}>{p}</div>
            <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>/ 100</div>
          </span>
        )}
      />
      <div style={{ marginTop: 6 }}>
        <Tag color={gradeColor(grade)} style={{ fontWeight: 700 }}>{grade}</Tag>
        {band && <Tag color={scoreColor(score)}>{band}</Tag>}
      </div>
      <Title level={5} style={{ marginTop: 6, marginBottom: 0 }}>{label}</Title>
    </div>
  );
}

const KPIS = [
  ["totalDashboards", "Dashboards", <DashboardOutlined />, undefined],
  ["totalWorksheets", "Worksheets", <AppstoreOutlined />, undefined],
  ["duplicateReports", "Duplicate reports", <CopyOutlined />, BRAND.error],
  ["similarReports", "Similar reports", <CopyOutlined />, BRAND.warning],
  ["rationalizationOpportunities", "Consolidation opportunities", <MergeCellsOutlined />, BRAND.info],
  ["vizIssues", "Visualization issues", <WarningOutlined />, BRAND.warning],
  ["highSeverityVizIssues", "High-severity viz issues", <ExclamationCircleOutlined />, BRAND.error],
  ["consolidationPotential", "Dashboards consolidatable", <ScissorOutlined />, BRAND.accent],
];

// Executive KPI cards + the two headline scores.
export default function ExecutiveSummary({ rat, name }) {
  const ex = rat.executiveSummary;
  return (
    <Card title={`Executive Rationalization Report — ${name}`}>
      <Row gutter={[24, 24]} align="middle">
        <Col xs={24} md={8}>
          <Row gutter={16}>
            <Col span={12}>
              <Gauge score={ex.rationalizationScore} grade={ex.rationalizationGrade}
                     band={null} label="Rationalization" />
            </Col>
            <Col span={12}>
              <Gauge score={ex.vizQualityScore} grade={ex.vizQualityGrade}
                     band={null} label="Viz Quality" />
            </Col>
          </Row>
          <div style={{ textAlign: "center", marginTop: 10 }}>
            <Tag color={scoreColor(ex.rationalizationScore)}>{ex.rationalizationBand}</Tag>
          </div>
        </Col>

        <Col xs={24} md={16}>
          <Row gutter={[16, 16]}>
            {KPIS.map(([key, label, icon, color]) => (
              <Col xs={12} sm={8} md={6} key={key}>
                <Statistic
                  title={<Space size={4}>{icon}<span style={{ fontSize: 12 }}>{label}</span></Space>}
                  value={ex[key] ?? 0}
                  valueStyle={{ color, fontSize: 22 }}
                />
              </Col>
            ))}
            <Col xs={12} sm={8} md={6}>
              <Statistic
                title={<Space size={4}><ClockCircleOutlined /><span style={{ fontSize: 12 }}>Effort saved</span></Space>}
                value={ex.effortReductionHours ?? 0} suffix="h" valueStyle={{ color: "var(--accent)", fontSize: 22 }}
              />
            </Col>
            <Col xs={12} sm={8} md={6}>
              <Statistic
                title={<span style={{ fontSize: 12 }}>Maintenance saving</span>}
                value={ex.maintenanceSavingsPct ?? 0} suffix="%" valueStyle={{ color: "var(--accent)", fontSize: 22 }}
              />
            </Col>
          </Row>
        </Col>
      </Row>
      <Text type="secondary" style={{ display: "block", marginTop: 12 }}>{ex.statement}</Text>
    </Card>
  );
}
