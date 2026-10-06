import { useMemo } from "react";
import { Tag, Typography, Space } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";

const dash = (v) => (v == null || v === "" ? <Typography.Text type="secondary">—</Typography.Text> : v);

export function confidenceColor(c) {
  if (c == null) return "default";
  if (c >= 0.7) return "green";
  if (c >= 0.5) return "gold";
  return "orange";
}

// Build worksheet -> [dashboards], [stories] membership from the workbook metadata.
export function membership(metadata) {
  const toDash = {};
  const toStory = {};
  for (const d of metadata.dashboards || []) for (const w of d.worksheets || []) (toDash[w] ||= []).push(d.name);
  for (const s of metadata.stories || []) for (const w of s.worksheets || []) (toStory[w] ||= []).push(s.name);
  return { toDash, toStory };
}

export default function WorksheetInventory({ metadata, onSelect }) {
  const { toDash, toStory } = useMemo(() => membership(metadata), [metadata]);
  const rows = useMemo(
    () =>
      (metadata.worksheets || []).map((w) => ({
        ...w,
        _dashboards: toDash[w.name] || [],
        _stories: toStory[w.name] || [],
      })),
    [metadata, toDash, toStory]
  );

  const columns = [
    { title: "Worksheet", dataIndex: "name", sorter: (a, b) => a.name.localeCompare(b.name) },
    {
      title: "Visual Type",
      key: "visual",
      render: (_, r) => (
        <Space size={4}>
          <Tag color={confidenceColor(r.visualConfidence)}>{r.visualType || "Unknown"}</Tag>
          {r.visualConfidence != null && (
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
              {Math.round(r.visualConfidence * 100)}%
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: "Dashboard(s)",
      key: "dash",
      render: (_, r) =>
        r._dashboards.length
          ? <Space wrap size={4}>{r._dashboards.map((d) => <Tag key={d} color="geekblue">{d}</Tag>)}</Space>
          : (r._stories.length ? dash(null) : <Tag>Standalone Worksheet</Tag>),
    },
    {
      title: "Story",
      key: "story",
      render: (_, r) =>
        r._stories.length ? <Space wrap size={4}>{r._stories.map((s) => <Tag key={s} color="purple">{s}</Tag>)}</Space> : dash(null),
    },
    { title: "Data Sources", key: "ds", render: (_, r) => (r.dataSources || []).join(", ") || dash(null) },
    { title: "Fields", dataIndex: "fields", align: "right", render: (f) => (f ? f.length : 0) },
  ];

  return (
    <SearchableTable
      rowKey="name"
      columns={columns}
      data={rows}
      searchFields={["name", "visualType"]}
      placeholder="Search worksheets…"
      pageSize={12}
      onRowClick={onSelect}
    />
  );
}
