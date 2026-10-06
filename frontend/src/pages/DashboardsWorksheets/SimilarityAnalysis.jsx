import { Card, Tag, Typography, Space, Empty, Progress } from "antd";
import { ClusterOutlined } from "@ant-design/icons";
import SearchableTable from "../../components/SearchableTable.jsx";
import { BRAND } from "../../theme/brand.js";

const { Text } = Typography;

// Escalating overlap severity — not a "good score", so the semantic
// error/warning tokens (not the teal->green ramp) apply here.
function simColor(s) {
  return s >= 90 ? BRAND.error : BRAND.warning;
}

// Dashboard & worksheet similarity: pairwise overlap + consolidation clusters.
export default function SimilarityAnalysis({ similarity }) {
  const pairs = (similarity?.pairs || []).map((p, i) => ({ ...p, _k: i }));
  const clusters = similarity?.clusters || [];

  const columns = [
    {
      title: "Report", dataIndex: "a",
      render: (a, r) => <Space><Tag color={r.type === "dashboard" ? "geekblue" : "default"}>{r.type}</Tag>{a}</Space>,
    },
    { title: "Similar to", dataIndex: "b" },
    {
      title: "Similarity", dataIndex: "similarity", align: "right",
      defaultSortOrder: "descend",
      sorter: (a, b) => a.similarity - b.similarity,
      render: (s) => (
        <Space size={6}>
          <Progress percent={s} showInfo={false} size={[70, 6]} strokeColor={simColor(s)} />
          <Text strong style={{ color: simColor(s) }}>{s}%</Text>
        </Space>
      ),
    },
    {
      title: "Confidence", dataIndex: "confidence", align: "right",
      render: (c) => (c != null ? `${Math.round(c * 100)}%` : "—"),
    },
    { title: "Recommendation", dataIndex: "recommendation", render: (t) => <Text type="secondary">{t}</Text> },
  ];

  return (
    <Card title="Report Similarity Analysis" size="small">
      {clusters.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text strong><ClusterOutlined /> Consolidation clusters</Text>
          <div style={{ marginTop: 8 }}>
            {clusters.map((c, i) => (
              <div key={i} style={{ marginBottom: 8, padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}>
                <Space wrap>
                  <Tag color={c.type === "dashboard" ? "geekblue" : "default"}>{c.type}</Tag>
                  <Tag color="orange">{c.size} reports · avg {c.avgSimilarity}%</Tag>
                  <Text strong>{c.recommendation}</Text>
                </Space>
                <div style={{ marginTop: 4 }}>
                  {c.members.map((m) => <Tag key={m} style={{ marginBottom: 4 }}>{m}</Tag>)}
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>{c.rationale}</Text>
              </div>
            ))}
          </div>
        </div>
      )}

      {pairs.length ? (
        <SearchableTable
          rowKey="_k" columns={columns} data={pairs}
          searchFields={["a", "b", "recommendation", "type"]}
          placeholder="Search reports…" pageSize={10}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No overlapping reports detected." />
      )}
    </Card>
  );
}
