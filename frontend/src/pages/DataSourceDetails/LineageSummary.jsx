import { Card, Timeline, Tag, Space, Typography, Divider } from "antd";
import {
  CloudServerOutlined,
  DatabaseOutlined,
  TableOutlined,
  ShareAltOutlined,
  FilterOutlined,
  CodeOutlined,
  ImportOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

function uniq(arr) {
  return [...new Set(arr.filter(Boolean))];
}

function Group({ label, items, color }) {
  if (!items?.length) return null;
  return (
    <div style={{ marginBottom: 6 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>
        {label}:{" "}
      </Text>
      <Space wrap size={4}>
        {items.map((x, i) => (
          <Tag key={i} color={color}>
            {x}
          </Tag>
        ))}
      </Space>
    </div>
  );
}

export default function LineageSummary({ ds }) {
  const sources = uniq(
    (ds.connections || []).map((c) =>
      c.server ? `${c.friendlyType} (${c.server})` : c.fileLocation ? `${c.friendlyType} (file)` : c.friendlyType
    )
  );
  const databases = uniq((ds.connections || []).map((c) => c.database));
  const physicalTables = (ds.tables || []).filter((t) => !t.isExtract);
  const schemas = uniq(physicalTables.map((t) => t.schema));
  const tables = physicalTables.map((t) => t.name);
  const rels = (ds.relationships || []).map((r) => `${r.parentTable} → ${r.childTable}`);
  const customSql = (ds.customSql || []).map((s) => s.name);
  const filters = (ds.filters || []).map((f) => f.field);

  const flow = [
    {
      color: "blue",
      dot: <CloudServerOutlined />,
      title: "Source Systems",
      body: <Group label="Systems" items={sources} color="geekblue" />,
    },
    {
      color: "blue",
      dot: <DatabaseOutlined />,
      title: "Databases & Schemas",
      body: (
        <>
          <Group label="Databases" items={databases} color="blue" />
          <Group label="Schemas" items={schemas} color="cyan" />
        </>
      ),
    },
    customSql.length && {
      color: "red",
      dot: <CodeOutlined />,
      title: "Custom SQL Transformations",
      body: <Group label="Queries" items={customSql} color="volcano" />,
    },
    {
      color: "green",
      dot: <TableOutlined />,
      title: `Tables (${tables.length})`,
      body: <Group label="Tables" items={tables} color="green" />,
    },
    rels.length && {
      color: "purple",
      dot: <ShareAltOutlined />,
      title: `Relationships (${rels.length})`,
      body: <Group label="Joins" items={rels} color="purple" />,
    },
    filters.length && {
      color: "orange",
      dot: <FilterOutlined />,
      title: `Filters (${filters.length})`,
      body: <Group label="Fields" items={filters} color="orange" />,
    },
    {
      color: ds.isExtract ? "orange" : "cyan",
      dot: <ImportOutlined />,
      title: "Data Source",
      body: (
        <Space wrap>
          <Tag color={ds.isExtract ? "orange" : "cyan"}>{ds.connectionMode}</Tag>
          {ds.isPublished && <Tag color="purple">Published</Tag>}
        </Space>
      ),
    },
  ].filter(Boolean);

  return (
    <Card size="small" title="Data Lineage Summary" style={{ height: "100%" }}>
      <Timeline
        items={flow.map((f) => ({
          color: f.color,
          dot: f.dot,
          children: (
            <>
              <Text strong>{f.title}</Text>
              <div style={{ marginTop: 4 }}>{f.body}</div>
            </>
          ),
        }))}
      />
      <Divider style={{ margin: "8px 0" }} />
      <Text type="secondary" style={{ fontSize: 12 }}>
        Flow: source systems → {customSql.length ? "custom SQL → " : ""}tables →{" "}
        {rels.length ? "relationships → " : ""}
        {filters.length ? "filters → " : ""}
        {ds.connectionMode.toLowerCase()} data source.
      </Text>
    </Card>
  );
}
