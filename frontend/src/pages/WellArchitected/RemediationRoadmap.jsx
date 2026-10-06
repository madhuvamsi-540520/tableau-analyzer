import { Card, Tag, Typography } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";
import { SEVERITY_COLOR } from "../../components/severity.js";

const { Text } = Typography;

const PRIORITY_COLOR = { P1: "red", P2: "orange", P3: "gold" };

// Prioritized P1/P2/P3 remediation roadmap (searchable/sortable).
export default function RemediationRoadmap({ roadmap }) {
  const rows = (roadmap || []).map((r, i) => ({ ...r, _key: i }));
  if (!rows.length) {
    return (
      <Card size="small" title="Prioritized Remediation Roadmap">
        <Text type="secondary">No remediation items — the workbook maps cleanly to a well-architected model.</Text>
      </Card>
    );
  }

  const columns = [
    { title: "Priority", dataIndex: "priority", width: 90,
      filters: ["P1", "P2", "P3"].map((v) => ({ text: v, value: v })),
      onFilter: (v, r) => r.priority === v,
      sorter: (a, b) => a.priority.localeCompare(b.priority),
      defaultSortOrder: "ascend",
      render: (p) => <Tag color={PRIORITY_COLOR[p]}>{p}</Tag> },
    { title: "Pillar", dataIndex: "pillar", width: 200,
      filters: [...new Set(rows.map((r) => r.pillar))].map((v) => ({ text: v, value: v })),
      onFilter: (v, r) => r.pillar === v },
    { title: "Finding", dataIndex: "title", render: (t, r) => (
        <div>
          <Text strong style={{ fontSize: 13 }}>{t}</Text>{" "}
          <Tag color={SEVERITY_COLOR[r.severity] || "default"}>{r.severity}</Tag>
          {r.metric && <div><Text code style={{ fontSize: 11 }}>{r.metric}</Text></div>}
        </div>
      ) },
    { title: "Recommended action", dataIndex: "action", render: (a, r) => (
        <div>
          <span style={{ fontSize: 12 }}>{a}</span>
          {r.benefit && <div><Text type="success" style={{ fontSize: 11 }}>▲ {r.benefit}</Text></div>}
        </div>
      ) },
  ];

  return (
    <Card size="small" title={`Prioritized Remediation Roadmap (${rows.length})`}>
      <SearchableTable
        rowKey="_key"
        columns={columns}
        data={rows}
        pageSize={12}
        searchFields={["title", "pillar", "action", "metric"]}
        placeholder="Search remediation items…"
      />
    </Card>
  );
}
