import { Card, Button, Space, Tag, Typography, Empty, Descriptions, App as AntApp } from "antd";
import { DownloadOutlined, CopyOutlined } from "@ant-design/icons";
import { api } from "../../api/client.js";

function Chips({ label, items, color }) {
  if (!items?.length) return null;
  return (
    <Descriptions.Item label={label}>
      <Space wrap size={4}>
        {items.map((x, i) => (
          <Tag key={i} color={color}>
            {x}
          </Tag>
        ))}
      </Space>
    </Descriptions.Item>
  );
}

function Analysis({ a }) {
  if (!a) return null;
  return (
    <Descriptions size="small" column={1} bordered style={{ marginTop: 12 }}>
      <Chips label="Referenced Tables" items={a.referencedTables} color="geekblue" />
      <Chips label="Referenced Columns" items={a.referencedColumns} />
      <Chips label="Aggregations" items={a.aggregations} color="green" />
      <Chips label="Window Functions" items={a.windowFunctions} color="purple" />
      <Chips label="CTEs" items={a.ctes} color="cyan" />
      <Descriptions.Item label="Set Operations">
        {a.hasUnionAll ? <Tag color="volcano">UNION ALL</Tag> : null}
        {a.hasUnion && !a.hasUnionAll ? <Tag color="orange">UNION</Tag> : null}
        {!a.hasUnion ? <Typography.Text type="secondary">none</Typography.Text> : null}
      </Descriptions.Item>
      <Descriptions.Item label="Subqueries">{a.subqueryCount ?? 0}</Descriptions.Item>
      {a.parsed === false && (
        <Descriptions.Item label="Parser">
          <Typography.Text type="warning">
            Approximate (dialect not fully parsed{a.error ? `: ${a.error}` : ""})
          </Typography.Text>
        </Descriptions.Item>
      )}
    </Descriptions>
  );
}

export default function CustomSql({ statements, jobId, dsIndex }) {
  const { message } = AntApp.useApp();
  if (!statements?.length) return <Empty description="No custom SQL in this data source." />;

  const copy = async (sql) => {
    try {
      await navigator.clipboard.writeText(sql);
      message.success("SQL copied to clipboard.");
    } catch {
      message.error("Copy failed.");
    }
  };

  const download = async (name, i) => {
    try {
      await api.downloadCustomSql(jobId, dsIndex, i, `${name || "custom_sql"}.sql`);
    } catch (e) {
      message.error(e.message || "Download failed.");
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {statements.map((s, i) => (
        <Card
          key={i}
          size="small"
          title={s.name}
          extra={
            <Space>
              <Button size="small" icon={<CopyOutlined />} onClick={() => copy(s.sql)}>
                Copy
              </Button>
              <Button
                size="small"
                type="primary"
                icon={<DownloadOutlined />}
                onClick={() => download(s.name, i)}
              >
                Download .sql
              </Button>
            </Space>
          }
        >
          <pre
            style={{
              margin: 0,
              padding: 12,
              borderRadius: 8,
              overflowX: "auto",
              background: "rgba(128,128,128,0.12)",
              fontFamily: "Consolas, 'Courier New', monospace",
              fontSize: 12.5,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {s.sql}
          </pre>
          <Analysis a={s.analysis} />
        </Card>
      ))}
    </Space>
  );
}
