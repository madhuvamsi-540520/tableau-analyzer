import { Row, Col, Card, Descriptions, Tag, Space, Typography, List, Empty, Progress } from "antd";
import DaxSuggestion from "./DaxSuggestion.jsx";

const { Text, Paragraph } = Typography;

const SUPPORT_COLOR = { Direct: "green", Rewrite: "orange", Manual: "gold", Unsupported: "red" };
const COMPLEXITY_COLOR = { Low: "green", Medium: "gold", High: "orange", "Very High": "red" };
const RISK_COLOR = { Low: "green", Medium: "gold", High: "red" };

const dash = (v) => (v == null || v === "" ? <Text type="secondary">—</Text> : v);
const tags = (arr, color) =>
  arr && arr.length ? <Space wrap size={4}>{arr.map((x) => <Tag key={x} color={color}>{x}</Tag>)}</Space> : dash(null);

function Panel({ title, children }) {
  return <Card size="small" title={title} style={{ height: "100%" }}>{children}</Card>;
}

export default function CalcDetailPanel({ calc, jobId }) {
  const dep = calc.dependencies || {};
  const perf = calc.performance || {};
  const dt = calc.dataTypes || {};

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      {/* Basic metadata */}
      <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
        <Descriptions.Item label="Name">{calc.name}</Descriptions.Item>
        <Descriptions.Item label="Data Source">{dash(calc.dataSource || calc._ds)}</Descriptions.Item>
        <Descriptions.Item label="Category">{tags(calc.categories)}</Descriptions.Item>
        <Descriptions.Item label="Power BI">
          <Tag color={SUPPORT_COLOR[calc.powerBiSupport] || "default"}>{calc.powerBiSupport}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Source Worksheet(s)">{tags(calc.worksheets, "blue")}</Descriptions.Item>
        <Descriptions.Item label="Source Dashboard(s)">{tags(calc.dashboards, "geekblue")}</Descriptions.Item>
        <Descriptions.Item label="Referenced Tables">{tags(calc.referencedTables, "purple")}</Descriptions.Item>
        <Descriptions.Item label="Referenced Fields">{tags(calc.referencedFields)}</Descriptions.Item>
      </Descriptions>

      {/* Formula */}
      <Card size="small" title="Formula (Tableau)">
        <Paragraph
          code
          copyable={{ text: calc.formula }}
          ellipsis={{ rows: 4, expandable: true, symbol: "show more" }}
          style={{ whiteSpace: "pre-wrap", marginBottom: 0, fontSize: 12 }}
        >
          {calc.formula || "—"}
        </Paragraph>
      </Card>

      <Row gutter={[12, 12]}>
        {/* Expression analysis */}
        <Col xs={24} md={12}>
          <Panel title="Expression Analysis">
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <div><Text type="secondary">Categories: </Text>{tags(calc.categories)}</div>
              <div><Text type="secondary">LOD: </Text>{dash(calc.lod)}</div>
              <div><Text type="secondary">Table calculation: </Text>{calc.tableCalc ? <Tag color="orange">Yes</Tag> : <Tag>No</Tag>}</div>
              <div><Text type="secondary">Dependency depth: </Text>{dep.depth ?? 0}</div>
              {calc.note && <Text type="secondary" style={{ fontSize: 12 }}>{calc.note}</Text>}
            </Space>
          </Panel>
        </Col>

        {/* Data type analysis */}
        <Col xs={24} md={12}>
          <Panel title="Data Type Analysis">
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <div><Text type="secondary">Input types: </Text>{tags(dt.inputs)}</div>
              <div><Text type="secondary">Output type: </Text><Tag color={dt.confident ? "blue" : "default"}>{dt.output || "unknown"}</Tag></div>
              <div><Text type="secondary">Explicit conversions: </Text>{tags(dt.explicitConversions, "cyan")}</div>
              {dt.issues?.length > 0 && (
                <List size="small" dataSource={dt.issues}
                  renderItem={(i) => <List.Item style={{ padding: "2px 0", border: "none" }}><Text type="warning" style={{ fontSize: 12 }}>⚠ {i}</Text></List.Item>} />
              )}
            </Space>
          </Panel>
        </Col>

        {/* Dependency graph (lists — interactive graph is Phase 2) */}
        <Col xs={24} md={12}>
          <Panel title="Dependencies">
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <div><Text type="secondary">Parent calcs (referenced): </Text>{tags(dep.parents, "gold")}</div>
              <div><Text type="secondary">Child calcs (use this): </Text>{tags(dep.children, "green")}</div>
              <div><Text type="secondary">Parameters: </Text>{tags(dep.parameters, "magenta")}</div>
            </Space>
          </Panel>
        </Col>

        {/* Performance */}
        <Col xs={24} md={12}>
          <Panel title="Performance Assessment">
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <Space>
                <Tag color={RISK_COLOR[perf.riskLevel] || "default"}>Risk: {perf.riskLevel || "—"}</Tag>
                <Tag>{perf.rating || "—"}</Tag>
              </Space>
              {perf.recommendation && <Text style={{ fontSize: 12 }}>{perf.recommendation}</Text>}
              {perf.signals?.length > 0 && (
                <List size="small" dataSource={perf.signals}
                  renderItem={(s) => <List.Item style={{ padding: "2px 0", border: "none" }}><Text type="secondary" style={{ fontSize: 12 }}>• {s}</Text></List.Item>} />
              )}
            </Space>
          </Panel>
        </Col>

        {/* Migration assessment */}
        <Col xs={24} md={12}>
          <Panel title="Migration Assessment">
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <div><Text type="secondary">Complexity: </Text><Tag color={COMPLEXITY_COLOR[calc.migrationComplexity] || "default"}>{calc.migrationComplexity}</Tag></div>
              <div><Text type="secondary">Estimated effort: </Text>{calc.estimatedEffortHours != null ? `${calc.estimatedEffortHours} h` : dash(null)}</div>
              <div><Text type="secondary">Automation: </Text>{dash(calc.automationFeasibility)}</div>
              <div>
                <Text type="secondary">Conversion confidence: </Text>
                {calc.conversionConfidence != null
                  ? <Progress percent={Math.round(calc.conversionConfidence * 100)} size="small" style={{ maxWidth: 160 }} />
                  : dash(null)}
              </div>
            </Space>
          </Panel>
        </Col>

        {/* Conversion suggestion (offline default + AI toggle) */}
        <Col xs={24} md={12}>
          <DaxSuggestion calc={calc} jobId={jobId} />
        </Col>
      </Row>
    </Space>
  );
}
