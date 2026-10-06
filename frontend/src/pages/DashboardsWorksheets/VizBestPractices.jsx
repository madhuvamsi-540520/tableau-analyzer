import { Card, Tag, Typography, Space, Empty, Progress } from "antd";
import { ArrowRightOutlined } from "@ant-design/icons";
import SearchableTable from "../../components/SearchableTable.jsx";
import { SEVERITY_COLOR, scoreColor } from "../../components/severity.js";

const { Text } = Typography;

// Visualization best-practice audit: one row per detected issue with the violated
// principle/framework and the recommended replacement visual.
export default function VizBestPractices({ viz }) {
  const issues = (viz?.issues || []).map((x, i) => ({ ...x, _k: i }));

  const columns = [
    { title: "Worksheet", dataIndex: "worksheet", render: (t) => <Text strong>{t}</Text> },
    { title: "Current", dataIndex: "currentViz", render: (t) => <Tag>{t}</Tag> },
    {
      title: "Issue", dataIndex: "issue",
      render: (t, r) => (
        <div>
          <div>{t}</div>
          <Text type="secondary" style={{ fontSize: 11 }}>{r.framework}</Text>
        </div>
      ),
    },
    {
      title: "Severity", dataIndex: "severity",
      render: (s) => <Tag color={SEVERITY_COLOR[s]}>{s}</Tag>,
      filters: ["high", "medium", "low", "info"].map((s) => ({ text: s, value: s })),
      onFilter: (v, r) => r.severity === v,
    },
    {
      title: "Recommended", dataIndex: "recommendedViz",
      render: (t) => <Space size={4}><ArrowRightOutlined style={{ color: "var(--accent)" }} /><Text type="success">{t}</Text></Space>,
    },
  ];

  const expandable = {
    expandedRowRender: (r) => (
      <div style={{ paddingInline: 8 }}>
        <p style={{ margin: "2px 0" }}><Text strong>Why: </Text>{r.reason}</p>
        <p style={{ margin: "2px 0" }}><Text strong>Principle: </Text>{r.principle}</p>
        <p style={{ margin: "2px 0" }}><Text strong>Business impact: </Text>{r.businessImpact}</p>
        {r.metric && <p style={{ margin: "2px 0" }}><Text type="secondary">{r.metric}</Text></p>}
      </div>
    ),
  };

  return (
    <Card
      title="Visualization Best-Practice Assessment"
      size="small"
      extra={
        <Space>
          <Text type="secondary" style={{ fontSize: 12 }}>Quality</Text>
          <Progress type="circle" percent={viz?.score ?? 0} size={38} strokeColor={scoreColor(viz?.score ?? 0)} />
        </Space>
      }
    >
      {issues.length ? (
        <SearchableTable
          rowKey="_k" columns={columns} data={issues} expandable={expandable}
          searchFields={["worksheet", "issue", "currentViz", "recommendedViz", "framework"]}
          placeholder="Search visualization issues…" pageSize={10}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No visualization best-practice issues detected." />
      )}
    </Card>
  );
}
