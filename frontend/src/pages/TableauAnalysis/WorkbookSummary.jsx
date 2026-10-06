import { Card, Row, Col, Statistic, Descriptions, Tag, Space } from "antd";

const dash = (v) => (v == null || v === "" ? "—" : v);

// Live vs Extract connection counts, computed from the data-source connections.
function connectionModes(metadata) {
  let live = 0;
  let extract = 0;
  for (const ds of metadata.dataSources || []) {
    for (const c of ds.connections || []) {
      if (c.isExtract) extract += 1;
      else live += 1;
    }
  }
  return { live, extract };
}

export default function WorkbookSummary({ metadata }) {
  const counts = metadata.counts || {};
  const cx = metadata.complexity || {};
  const ws = metadata.workbookSummary || {}; // populated once worksheet/dashboard parsing lands
  const { live, extract } = connectionModes(metadata);

  const tiles = [
    { label: "Dashboards", value: ws.dashboards },
    { label: "Worksheets", value: ws.worksheets },
    { label: "Stories", value: ws.stories },
    { label: "Data Sources", value: counts.dataSources },
    { label: "Parameters", value: cx.parameters },
    { label: "Filters", value: cx.filters },
    { label: "Calculated Fields", value: cx.calculatedFields },
    { label: "Custom SQL", value: cx.customSql },
    { label: "Live Connections", value: live },
    { label: "Extract Connections", value: extract },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Descriptions bordered size="small" column={{ xs: 1, sm: 2, md: 3 }} title="Workbook">
        <Descriptions.Item label="Name">{dash(metadata.name)}</Descriptions.Item>
        <Descriptions.Item label="Version">{dash(metadata.version)}</Descriptions.Item>
        <Descriptions.Item label="Source Platform">{dash(metadata.sourcePlatform)}</Descriptions.Item>
        <Descriptions.Item label="Author">{dash(ws.author)}</Descriptions.Item>
        <Descriptions.Item label="Last Modified">{dash(ws.lastModified)}</Descriptions.Item>
        <Descriptions.Item label="Source Build">{dash(metadata.sourceBuild)}</Descriptions.Item>
      </Descriptions>

      <Row gutter={[12, 12]}>
        {tiles.map((t) => (
          <Col key={t.label} xs={12} sm={8} md={6} lg={4}>
            <Card size="small">
              <Statistic
                title={t.label}
                value={t.value == null ? "—" : t.value}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </Space>
  );
}
