import { useMemo, useState } from "react";
import { Table, Input, Space } from "antd";

// AntD table with a client-side search box. Columns already carry their own
// sorters/filters; this adds free-text search across the given fields.
export default function SearchableTable({
  columns,
  data,
  rowKey,
  searchFields,
  size = "small",
  pageSize = 10,
  expandable,
  placeholder = "Search…",
  onRowClick,
}) {
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return data;
    const fields = searchFields || (data[0] ? Object.keys(data[0]) : []);
    return data.filter((row) =>
      fields.some((f) => String(row[f] ?? "").toLowerCase().includes(term))
    );
  }, [q, data, searchFields]);

  return (
    <Space direction="vertical" style={{ width: "100%" }} size={8}>
      <Input.Search
        allowClear
        placeholder={placeholder}
        onChange={(e) => setQ(e.target.value)}
        style={{ maxWidth: 340 }}
      />
      <Table
        size={size}
        rowKey={rowKey}
        columns={columns}
        dataSource={filtered}
        expandable={expandable}
        onRow={onRowClick ? (row) => ({ onClick: () => onRowClick(row), style: { cursor: "pointer" } }) : undefined}
        pagination={filtered.length > pageSize ? { pageSize, showSizeChanger: true } : false}
        scroll={{ x: "max-content" }}
      />
    </Space>
  );
}
