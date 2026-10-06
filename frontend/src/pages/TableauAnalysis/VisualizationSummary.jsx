import { useMemo } from "react";
import { Row, Col, Card, Statistic, Empty } from "antd";

// High-level visualization KPIs for the workbook overview. Counts by category are
// derived dynamically from the detected visual types — no hardcoded chart list.
export default function VisualizationSummary({ metadata }) {
  const { total, byType } = useMemo(() => {
    const worksheets = metadata.worksheets || [];
    const counts = {};
    for (const w of worksheets) {
      const t = w.visualType || "Unknown";
      counts[t] = (counts[t] || 0) + 1;
    }
    const byType = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    return { total: worksheets.length, byType };
  }, [metadata]);

  const ws = metadata.workbookSummary || {};
  const counts = metadata.counts || {};

  // The five top-level KPI cards required for the overview.
  const kpis = [
    { label: "Total Stories", value: ws.stories },
    { label: "Total Dashboards", value: ws.dashboards },
    { label: "Total Worksheets", value: ws.worksheets },
    { label: "Total Data Sources", value: counts.dataSources },
    { label: "Total Visualizations", value: total },
  ];

  return (
    <>
      <Row gutter={[12, 12]}>
        {kpis.map((k) => (
          <Col key={k.label} xs={12} sm={8} md={8} lg={4}>
            <Card size="small">
              <Statistic title={k.label} value={k.value == null ? "—" : k.value} />
            </Card>
          </Col>
        ))}
      </Row>

      <Card size="small" title="Visualization Summary (by type)" style={{ marginTop: 16 }}>
        {byType.length ? (
          <Row gutter={[12, 12]}>
            {byType.map(([type, count]) => (
              <Col key={type} xs={12} sm={8} md={6} lg={4}>
                <Card size="small">
                  <Statistic title={type} value={count} />
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No worksheets detected." />
        )}
      </Card>
    </>
  );
}
