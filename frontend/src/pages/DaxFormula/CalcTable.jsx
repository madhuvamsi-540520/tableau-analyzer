import { useMemo } from "react";
import { Empty, Tag, Typography, Space, Progress } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";
import CalcDetailPanel from "./CalcDetailPanel.jsx";
import { calcObjects } from "./KpiCards.jsx";

const { Text } = Typography;

const SUPPORT_COLOR = { Direct: "green", Rewrite: "orange", Manual: "gold", Unsupported: "red" };
const COMPLEXITY_COLOR = { Low: "green", Medium: "gold", High: "orange", "Very High": "red" };
const RISK_COLOR = { Low: "green", Medium: "gold", High: "red" };
const COMPLEXITY_ORDER = { Low: 0, Medium: 1, High: 2, "Very High": 3 };
const RISK_ORDER = { Low: 0, Medium: 1, High: 2 };

const uniq = (arr) => [...new Set(arr.filter(Boolean))].sort();
const opts = (arr) => uniq(arr).map((v) => ({ text: v, value: v }));

// The central calculation intelligence table: search, filter, sort, drill-down.
export default function CalcTable({ metadata, jobId }) {
  const rows = useMemo(() => {
    const { calcs } = calcObjects(metadata);
    return calcs.map((c, i) => {
      const dep = c.dependencies || {};
      const depCount = (dep.parents?.length || 0) + (dep.children?.length || 0);
      return {
        ...c,
        _key: `${c._dsIndex}:${c.name}:${i}`,
        _risk: c.performance?.riskLevel || null,
        _depCount: depCount,
        _effort: c.estimatedEffortHours ?? null,
        _conf: c.conversionConfidence ?? null,
        _worksheets: (c.worksheets || []).join(", "),
        _dashboards: (c.dashboards || []).join(", "),
      };
    });
  }, [metadata]);

  if (!rows.length) return <Empty description="No calculated fields found in this workbook." />;

  const allCategories = uniq(rows.flatMap((r) => r.categories || []));

  const columns = [
    { title: "Name", dataIndex: "name", fixed: "left", sorter: (a, b) => a.name.localeCompare(b.name) },
    {
      title: "Data Source", dataIndex: "_ds",
      filters: opts(rows.map((r) => r._ds)), onFilter: (v, r) => r._ds === v,
    },
    {
      title: "Type", dataIndex: "categories",
      filters: allCategories.map((v) => ({ text: v, value: v })),
      onFilter: (v, r) => (r.categories || []).includes(v),
      render: (c) => <Space wrap size={4}>{(c || []).map((x) => <Tag key={x}>{x}</Tag>)}</Space>,
    },
    {
      title: "Complexity", dataIndex: "migrationComplexity",
      filters: opts(rows.map((r) => r.migrationComplexity)), onFilter: (v, r) => r.migrationComplexity === v,
      sorter: (a, b) => (COMPLEXITY_ORDER[a.migrationComplexity] ?? 0) - (COMPLEXITY_ORDER[b.migrationComplexity] ?? 0),
      render: (v) => <Tag color={COMPLEXITY_COLOR[v] || "default"}>{v}</Tag>,
    },
    {
      title: "Power BI", dataIndex: "powerBiSupport",
      filters: opts(rows.map((r) => r.powerBiSupport)), onFilter: (v, r) => r.powerBiSupport === v,
      render: (v) => <Tag color={SUPPORT_COLOR[v] || "default"}>{v}</Tag>,
    },
    {
      title: "Perf Risk", dataIndex: "_risk",
      filters: opts(rows.map((r) => r._risk)), onFilter: (v, r) => r._risk === v,
      sorter: (a, b) => (RISK_ORDER[a._risk] ?? -1) - (RISK_ORDER[b._risk] ?? -1),
      render: (v) => (v ? <Tag color={RISK_COLOR[v] || "default"}>{v}</Tag> : <Text type="secondary">—</Text>),
    },
    {
      title: "Effort (h)", dataIndex: "_effort", align: "right",
      sorter: (a, b) => (a._effort ?? 0) - (b._effort ?? 0),
      render: (v) => (v == null ? "—" : v),
    },
    {
      title: "Deps", dataIndex: "_depCount", align: "right",
      sorter: (a, b) => a._depCount - b._depCount,
    },
    {
      title: "Confidence", dataIndex: "_conf", align: "right", width: 130,
      sorter: (a, b) => (a._conf ?? -1) - (b._conf ?? -1),
      render: (v) => (v == null ? "—" : <Progress percent={Math.round(v * 100)} size="small" />),
    },
    {
      title: "Worksheets", dataIndex: "_worksheets",
      filters: opts(rows.flatMap((r) => r.worksheets || [])),
      onFilter: (v, r) => (r.worksheets || []).includes(v),
      render: (_, r) => (r.worksheets?.length ? <Tag color="blue">{r.worksheets.length}</Tag> : <Text type="secondary">—</Text>),
    },
    {
      title: "Dashboards", dataIndex: "_dashboards",
      filters: opts(rows.flatMap((r) => r.dashboards || [])),
      onFilter: (v, r) => (r.dashboards || []).includes(v),
      render: (_, r) => (r.dashboards?.length ? <Tag color="geekblue">{r.dashboards.length}</Tag> : <Text type="secondary">—</Text>),
    },
  ];

  return (
    <SearchableTable
      rowKey="_key"
      columns={columns}
      data={rows}
      pageSize={12}
      searchFields={["name", "formula", "_ds", "_worksheets", "_dashboards"]}
      placeholder="Search name, formula, worksheet, dashboard, data source…"
      expandable={{
        expandedRowRender: (row) => <CalcDetailPanel calc={row} jobId={jobId} />,
        rowExpandable: () => true,
      }}
    />
  );
}
