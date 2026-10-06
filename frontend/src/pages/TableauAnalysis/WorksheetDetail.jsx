import { Drawer, Descriptions, Tag, Table, Space, Typography, Empty, Divider, Alert } from "antd";
import { confidenceColor } from "./WorksheetInventory.jsx";

const { Text, Paragraph } = Typography;
const dash = (v) => (v == null || v === "" ? <Text type="secondary">—</Text> : v);

const COMPLEXITY_COLOR = { Low: "green", Medium: "gold", High: "orange", "Very High": "red" };

function Section({ title, children }) {
  return (
    <>
      <Divider orientation="left" style={{ margin: "12px 0 8px" }}>{title}</Divider>
      {children}
    </>
  );
}

export default function WorksheetDetail({ ws, metadata, open, onClose }) {
  if (!ws) return null;

  const dashboards = (metadata.dashboards || []).filter((d) => (d.worksheets || []).includes(ws.name)).map((d) => d.name);
  const stories = (metadata.stories || []).filter((s) => (s.worksheets || []).includes(ws.name)).map((s) => s.name);

  // Calculations referenced by this worksheet (by field-name match).
  const allCalcs = (metadata.dataSources || []).flatMap((d) => d.calculations || []);
  const fieldNames = new Set((ws.fields || []).map((f) => f.field));
  const calcsUsed = allCalcs.filter((c) => fieldNames.has(c.name));

  return (
    <Drawer title={`Worksheet — ${ws.name}`} width={720} open={open} onClose={onClose}>
      <Section title="General">
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="Visual Type">
            <Space>
              <Tag color={confidenceColor(ws.visualConfidence)}>{ws.visualType || "Unknown"}</Tag>
              {ws.visualConfidence != null && <Text type="secondary">{Math.round(ws.visualConfidence * 100)}% confidence</Text>}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="Mark Type">{dash(ws.markClass)}</Descriptions.Item>
          <Descriptions.Item label="Dashboard(s)">{dashboards.length ? dashboards.join(", ") : <Tag>Standalone</Tag>}</Descriptions.Item>
          <Descriptions.Item label="Story">{stories.length ? stories.join(", ") : dash(null)}</Descriptions.Item>
          <Descriptions.Item label="Data Sources">{(ws.dataSources || []).join(", ") || dash(null)}</Descriptions.Item>
        </Descriptions>
        {ws.visualReasoning?.length > 0 && (
          <Alert
            style={{ marginTop: 8 }}
            type="info"
            showIcon
            message="Why this visual type"
            description={<ul style={{ margin: 0, paddingLeft: 18 }}>{ws.visualReasoning.map((r, i) => <li key={i}>{r}</li>)}</ul>}
          />
        )}
      </Section>

      <Section title={`Fields Used (${(ws.fields || []).length})`}>
        {ws.fields?.length ? (
          <Table
            size="small"
            rowKey={(r, i) => r.field + i}
            pagination={false}
            columns={[
              { title: "Field", dataIndex: "field" },
              { title: "Role", dataIndex: "role", render: (v) => (v ? <Tag color={v === "measure" ? "green" : "blue"}>{v}</Tag> : dash(v)) },
              { title: "Aggregation", dataIndex: "aggregation", render: dash },
              { title: "Data Type", dataIndex: "dataType", render: (v) => (v ? <Tag>{v}</Tag> : dash(v)) },
            ]}
            dataSource={ws.fields}
          />
        ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No fields placed" />}
      </Section>

      <Section title="Shelves & Encodings">
        <Space direction="vertical" size={4} style={{ width: "100%" }}>
          <div><Text strong>Rows: </Text>{(ws.rows || []).join(", ") || dash(null)}</div>
          <div><Text strong>Columns: </Text>{(ws.cols || []).join(", ") || dash(null)}</div>
          <div>
            <Text strong>Encodings: </Text>
            {ws.encodings?.length
              ? <Space wrap size={4}>{ws.encodings.map((e, i) => <Tag key={i}>{e.channel}{e.field ? `: ${e.field}` : ""}</Tag>)}</Space>
              : dash(null)}
          </div>
        </Space>
      </Section>

      <Section title="Filters & Analytics">
        <Space direction="vertical" size={4} style={{ width: "100%" }}>
          <div><Text strong>Filters: </Text>{ws.filters?.length ? <Space wrap size={4}>{ws.filters.map((f) => <Tag key={f}>{f}</Tag>)}</Space> : dash(null)}</div>
          <div><Text strong>Analytics: </Text>{ws.analytics?.length ? <Space wrap size={4}>{ws.analytics.map((a) => <Tag key={a} color="cyan">{a}</Tag>)}</Space> : dash(null)}</div>
        </Space>
      </Section>

      <Section title={`Calculations Used (${calcsUsed.length})`}>
        {calcsUsed.length ? (
          <>
            <Table
              size="small"
              rowKey="name"
              pagination={false}
              columns={[
                { title: "Name", dataIndex: "name" },
                { title: "Type", dataIndex: "categories", render: (c) => <Space wrap size={4}>{(c || []).map((x) => <Tag key={x}>{x}</Tag>)}</Space> },
              ]}
              dataSource={calcsUsed}
            />
            <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}>
              Formulas, dependencies and Power BI conversion are in the <b>DAX &amp; Formula</b> tab.
            </Paragraph>
          </>
        ) : <Paragraph type="secondary">No calculated fields detected on this worksheet.</Paragraph>}
      </Section>
    </Drawer>
  );
}
