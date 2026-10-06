import { Card, Collapse, Tag, Typography, Space, Table } from "antd";
import {
  CheckCircleTwoTone, WarningTwoTone, CloseCircleTwoTone, MinusCircleTwoTone,
} from "@ant-design/icons";
import { SEVERITY_COLOR, scoreColor, gradeColor } from "../../components/severity.js";
import { BRAND } from "../../theme/brand.js";

const { Text } = Typography;

export function StatusIcon({ status }) {
  if (status === "pass") return <CheckCircleTwoTone twoToneColor={BRAND.accent} />;
  if (status === "warn") return <WarningTwoTone twoToneColor={BRAND.warning} />;
  if (status === "fail") return <CloseCircleTwoTone twoToneColor={BRAND.error} />;
  return <MinusCircleTwoTone twoToneColor={BRAND.textSecondary} />;
}

function ChecksTable({ checks }) {
  const columns = [
    { title: "", dataIndex: "status", width: 36, render: (s) => <StatusIcon status={s} /> },
    { title: "Check", dataIndex: "title", render: (t, r) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: 13 }}>{t}</Text>
          {r.detail && <Text type="secondary" style={{ fontSize: 12 }}>{r.detail}</Text>}
        </Space>
      ) },
    { title: "Severity", dataIndex: "severity", width: 90,
      render: (s, r) => (r.status === "pass" || r.status === "na"
        ? <Tag>{r.status}</Tag>
        : <Tag color={SEVERITY_COLOR[s] || "default"}>{s}</Tag>) },
    { title: "Metric", dataIndex: "metric", width: 150, render: (m) => m ? <Text code style={{ fontSize: 11 }}>{m}</Text> : <Text type="secondary">—</Text> },
    { title: "Recommendation", dataIndex: "recommendation", render: (rec, r) => (
        <Space direction="vertical" size={2}>
          <span style={{ fontSize: 12 }}>{rec || <Text type="secondary">—</Text>}</span>
          {r.benefit && <Text type="success" style={{ fontSize: 11 }}>▲ {r.benefit}</Text>}
        </Space>
      ) },
  ];
  return (
    <Table
      size="small"
      rowKey="id"
      columns={columns}
      dataSource={checks}
      pagination={false}
      scroll={{ x: "max-content" }}
    />
  );
}

// One AntD Collapse panel per pillar (score + summary + checks table).
export default function PillarSection({ pillars }) {
  const items = (pillars || []).map((p) => ({
    key: p.key,
    label: (
      <Space wrap>
        <Text strong>{p.name}</Text>
        <Tag color={gradeColor(p.grade)}>{p.grade}</Tag>
        <Tag color={scoreColor(p.score)}>{p.score}/100</Tag>
        {p.counts?.fail > 0 && <Tag color="red">{p.counts.fail} fail</Tag>}
        {p.counts?.warn > 0 && <Tag color="orange">{p.counts.warn} warn</Tag>}
      </Space>
    ),
    children: (
      <>
        {p.summary && <Text type="secondary" style={{ display: "block", marginBottom: 8 }}>{p.summary}</Text>}
        <ChecksTable checks={p.checks || []} />
      </>
    ),
  }));

  // Open the pillars that need attention by default.
  const defaultOpen = (pillars || []).filter((p) => (p.counts?.fail || 0) > 0).map((p) => p.key);

  return (
    <Card size="small" title="Architecture Pillars">
      <Collapse items={items} defaultActiveKey={defaultOpen} />
    </Card>
  );
}
