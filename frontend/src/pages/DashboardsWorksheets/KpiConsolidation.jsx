import { Card, Tag, Typography, Empty, List } from "antd";
import { StarFilled } from "@ant-design/icons";
import SearchableTable from "../../components/SearchableTable.jsx";

const { Text } = Typography;

// Business KPI consolidation: measures reused across many worksheets/dashboards.
export default function KpiConsolidation({ kpi }) {
  const kpis = (kpi?.kpis || []).map((k, i) => ({ ...k, _k: i }));
  const opportunities = kpi?.opportunities || [];

  const columns = [
    {
      title: "Measure / KPI", dataIndex: "measure",
      render: (m, r) => <span>{r.core && <StarFilled style={{ color: "var(--accent)", marginRight: 6 }} />}<Text strong>{m}</Text></span>,
    },
    {
      title: "Worksheets", dataIndex: "worksheetCount", align: "right",
      sorter: (a, b) => a.worksheetCount - b.worksheetCount, defaultSortOrder: "descend",
    },
    { title: "Dashboards", dataIndex: "dashboardCount", align: "right" },
    {
      title: "Reuse", dataIndex: "core",
      render: (c) => (c ? <Tag color="gold">Core KPI</Tag> : <Tag>local</Tag>),
      filters: [{ text: "Core", value: true }, { text: "Local", value: false }],
      onFilter: (v, r) => r.core === v,
    },
  ];

  return (
    <Card title="Business KPI Consolidation" size="small">
      {opportunities.length > 0 && (
        <List
          size="small"
          style={{ marginBottom: 12 }}
          header={<Text strong>Reusable-measure opportunities</Text>}
          dataSource={opportunities}
          renderItem={(o) => (
            <List.Item>
              <List.Item.Meta
                avatar={<StarFilled style={{ color: "var(--accent)" }} />}
                title={<Text strong>{o.measure}</Text>}
                description={<span style={{ fontSize: 12 }}>{o.recommendation}</span>}
              />
            </List.Item>
          )}
        />
      )}
      {kpis.length ? (
        <SearchableTable
          rowKey="_k" columns={columns} data={kpis}
          searchFields={["measure"]} placeholder="Search measures…" pageSize={10}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No measures detected across worksheets." />
      )}
    </Card>
  );
}
