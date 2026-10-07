import { Card, Table, Tag, Space, Typography, Alert, Row, Col, Statistic, Empty } from "antd";

const { Text, Paragraph } = Typography;

function Metric({ title, value }) {
  return (
    <Col xs={12} sm={8} md={6} lg={4}>
      <Card size="small">
        <Statistic title={title} value={value ?? 0} />
      </Card>
    </Col>
  );
}

// Renders converter.summary(model): the model Power BI will be built from.
export default function PbipPreview({ summary }) {
  if (!summary) return <Empty description="No preview yet." />;
  const c = summary.counts || {};

  const tableCols = [
    {
      title: "Table",
      dataIndex: "name",
      render: (n, r) => (
        <Space>
          {n}
          {r.dataOrigin === "bundled" ? <Tag color="green">real data</Tag> : null}
          {r.dataOrigin === "sample" ? <Tag color="gold">sample data</Tag> : null}
        </Space>
      ),
    },
    { title: "Kind", dataIndex: "kind", render: (k) => <Tag>{k || "table"}</Tag> },
    { title: "Columns", align: "right", render: (_, r) => r.columns?.length ?? 0 },
    { title: "Rows", align: "right", dataIndex: "rowCount", render: (v) => (v == null ? "—" : v.toLocaleString()) },
  ];

  const relCols = [
    { title: "From", dataIndex: "from" },
    { title: "To", dataIndex: "to" },
    { title: "Cardinality", dataIndex: "type", render: (t) => <Tag color="blue">{t}</Tag> },
    { title: "Cross-filter", dataIndex: "crossFilter", render: (t) => <Tag>{t}</Tag> },
  ];

  const calcCols = [
    { title: "Calculated field", dataIndex: "name" },
    {
      title: "DAX",
      dataIndex: "dax",
      render: (dax) =>
        dax ? (
          <Paragraph code copyable={{ text: dax }} style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 12 }}>
            {dax}
          </Paragraph>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: "Status",
      align: "right",
      render: (_, r) => (
        <Space size={4}>
          <Tag>{r.method || "rule"}</Tag>
          {r.needsReview ? <Tag color="gold">review</Tag> : r.translated ? <Tag color="green">ok</Tag> : <Tag color="red">manual</Tag>}
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Row gutter={[12, 12]}>
        <Metric title="Tables" value={c.tables} />
        <Metric title="Columns" value={c.columns} />
        <Metric title="Relationships" value={c.relationships} />
        <Metric title="Calc fields" value={c.calculatedFields} />
        <Metric title="DAX translated" value={c.translated} />
        <Metric title="Worksheets" value={c.worksheets} />
        <Metric title="Dashboard pages" value={c.dashboardPages} />
      </Row>

      {summary.warnings?.length > 0 && (
        <Alert
          type="warning"
          showIcon
          message={`${summary.warnings.length} conversion note(s)`}
          description={<ul style={{ margin: 0, paddingLeft: 18 }}>{summary.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
        />
      )}

      <Card
        size="small"
        title={`Semantic model — Tables (${summary.tables?.length || 0})`}
        extra={summary.dataMode ? <Tag color="blue">{summary.dataMode}</Tag> : null}
      >
        <Table rowKey="name" size="small" columns={tableCols} dataSource={summary.tables || []} pagination={false} />
      </Card>

      <Card size="small" title={`Relationships (${summary.relationships?.length || 0})`}>
        {summary.relationships?.length ? (
          <Table rowKey={(r) => `${r.from}->${r.to}`} size="small" columns={relCols} dataSource={summary.relationships} pagination={false} />
        ) : (
          <Empty description="No relationships detected." />
        )}
      </Card>

      <Card size="small" title={`Dashboard pages (${summary.dashboards?.length || 0})`}>
        {summary.dashboards?.length ? (
          <Space direction="vertical" size={8} style={{ width: "100%" }}>
            {summary.dashboards.map((d) => (
              <div key={d.name}>
                <Text strong>{d.name}</Text>{" "}
                <Text type="secondary">— composes {d.worksheets.length} worksheet(s): {d.worksheets.join(", ")}</Text>
              </div>
            ))}
          </Space>
        ) : (
          <Empty description="No dashboards detected (or none reference a worksheet with placed fields)." />
        )}
      </Card>

      <Card size="small" title={`Calculated fields → DAX (${summary.calculatedFields?.length || 0})`}>
        {summary.calculatedFields?.length ? (
          <Table
            rowKey="name"
            size="small"
            columns={calcCols}
            dataSource={summary.calculatedFields}
            pagination={summary.calculatedFields.length > 10 ? { pageSize: 10 } : false}
          />
        ) : (
          <Empty description="No calculated fields." />
        )}
      </Card>
    </Space>
  );
}
