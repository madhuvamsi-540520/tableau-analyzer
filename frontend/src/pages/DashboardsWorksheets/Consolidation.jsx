import { Card, Row, Col, Statistic, Tag, Typography, Empty } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";
import { SEVERITY_COLOR } from "../../components/severity.js";

const { Text } = Typography;

const KIND_COLOR = { merge: "red", retire: "volcano", parameterize: "orange", reuse: "blue" };

// Consolidation recommendations + estimated reductions.
export default function Consolidation({ consolidation }) {
  const recs = (consolidation?.recommendations || []).map((r, i) => ({ ...r, _k: i }));

  const columns = [
    {
      title: "Action", dataIndex: "title",
      render: (t, r) => <Text strong>{t}</Text>,
    },
    { title: "Type", dataIndex: "kind", render: (k) => <Tag color={KIND_COLOR[k] || "default"}>{k}</Tag> },
    {
      title: "Severity", dataIndex: "severity",
      render: (s) => <Tag color={SEVERITY_COLOR[s]}>{s}</Tag>,
      filters: ["high", "medium", "low"].map((s) => ({ text: s, value: s })),
      onFilter: (v, r) => r.severity === v,
    },
    {
      title: "Effort saved", dataIndex: "effortSavedHours", align: "right",
      sorter: (a, b) => a.effortSavedHours - b.effortSavedHours,
      defaultSortOrder: "descend",
      render: (h) => <Text type="success">{h}h</Text>,
    },
    {
      title: "Recommendation", dataIndex: "recommendation",
      render: (t, r) => (
        <div>
          <div>{t}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {(r.targets || []).map((x) => <Tag key={x} style={{ marginBottom: 2 }}>{x}</Tag>)}
          </Text>
        </div>
      ),
    },
  ];

  return (
    <Card title="Consolidation Recommendations" size="small">
      <Row gutter={16} style={{ marginBottom: 12 }}>
        <Col xs={12} md={6}>
          <Statistic title="Dashboard reduction" value={consolidation?.estimatedDashboardReduction ?? 0}
                     valueStyle={{ color: "var(--accent)" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="Worksheet reduction" value={consolidation?.estimatedWorksheetReduction ?? 0}
                     valueStyle={{ color: "var(--accent)" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="Migration effort saved" value={consolidation?.estimatedEffortReductionHours ?? 0}
                     suffix="h" valueStyle={{ color: "var(--accent)" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="Maintenance saving" value={consolidation?.estimatedMaintenanceSavingsPct ?? 0}
                     suffix="%" valueStyle={{ color: "var(--accent)" }} />
        </Col>
      </Row>
      {recs.length ? (
        <SearchableTable
          rowKey="_k" columns={columns} data={recs}
          searchFields={["title", "recommendation", "kind"]}
          placeholder="Search recommendations…" pageSize={10}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No consolidation opportunities found." />
      )}
    </Card>
  );
}
