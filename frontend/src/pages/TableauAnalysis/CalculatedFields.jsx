import { Empty, Tag, Typography, Space } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";

const SUPPORT_COLOR = { Direct: "green", Rewrite: "orange", Manual: "gold", Unsupported: "red" };
const COMPLEXITY_COLOR = { Low: "green", Medium: "gold", High: "orange", "Very High": "red" };

export default function CalculatedFields({ metadata }) {
  const rows = (metadata.dataSources || []).flatMap((ds) =>
    (ds.calculations || []).map((c, i) => ({
      ...c,
      _ds: ds.caption || ds.name,
      _key: `${ds.name || ""}:${c.name}:${i}`,
    }))
  );

  if (!rows.length) return <Empty description="No calculated fields found in this workbook." />;

  const columns = [
    { title: "Name", dataIndex: "name", sorter: (a, b) => a.name.localeCompare(b.name) },
    { title: "Data Source", dataIndex: "_ds" },
    {
      title: "Type",
      dataIndex: "categories",
      render: (c) => <Space wrap size={4}>{(c || []).map((x) => <Tag key={x}>{x}</Tag>)}</Space>,
    },
    {
      title: "Power BI",
      dataIndex: "powerBiSupport",
      render: (v) => <Tag color={SUPPORT_COLOR[v] || "default"}>{v}</Tag>,
      filters: ["Direct", "Rewrite", "Manual", "Unsupported"].map((v) => ({ text: v, value: v })),
      onFilter: (v, r) => r.powerBiSupport === v,
    },
    {
      title: "Complexity",
      dataIndex: "migrationComplexity",
      render: (v) => <Tag color={COMPLEXITY_COLOR[v] || "default"}>{v}</Tag>,
    },
    {
      title: "Formula",
      dataIndex: "formula",
      render: (v) => <Typography.Text code style={{ fontSize: 11 }}>{v}</Typography.Text>,
    },
  ];

  return (
    <SearchableTable
      rowKey="_key"
      columns={columns}
      data={rows}
      searchFields={["name", "formula", "_ds"]}
      placeholder="Search calculated fields…"
    />
  );
}
