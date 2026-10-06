import { useState } from "react";
import { Card, Select, Collapse, Space, Typography, Tag, Empty, Alert } from "antd";
import TechnicalAssessment from "./TechnicalAssessment.jsx";
import ExportBar from "./ExportBar.jsx";
import Overview from "./Overview.jsx";
import ConnectionDetails from "./ConnectionDetails.jsx";
import TableInventory from "./TableInventory.jsx";
import ColumnInventory from "./ColumnInventory.jsx";
import Relationships from "./Relationships.jsx";
import Unions from "./Unions.jsx";
import Filters from "./Filters.jsx";
import CustomSql from "./CustomSql.jsx";
import Classification from "./Classification.jsx";
import SchemaAndLineage from "./SchemaAndLineage.jsx";

export default function WorkbookDetail({ metadata, jobId }) {
  const dsList = metadata.dataSources || [];
  const [idx, setIdx] = useState(0);

  if (!dsList.length) {
    return (
      <Card>
        <Empty description="No data sources were found in this workbook." />
        {metadata.warnings?.map((w, i) => (
          <Alert key={i} type="warning" showIcon message={w} style={{ marginTop: 8 }} />
        ))}
      </Card>
    );
  }

  const ds = dsList[Math.min(idx, dsList.length - 1)];
  const c = ds.counts || {};

  const items = [
    { key: "overview", label: "Data Source Overview", children: <Overview ds={ds} /> },
    {
      key: "conn",
      label: `Connection Details (${c.connections ?? 0})`,
      children: <ConnectionDetails connections={ds.connections} />,
    },
    {
      key: "tables",
      label: `Table Inventory (${c.tables ?? 0})`,
      children: <TableInventory tables={ds.tables} />,
    },
    {
      key: "cols",
      label: `Column Inventory (${c.columns ?? 0})`,
      children: <ColumnInventory tables={ds.tables} />,
    },
    {
      key: "rels",
      label: `Relationships & Joins (${c.relationships ?? 0})`,
      children: <Relationships relationships={ds.relationships} />,
    },
  ];

  if ((c.unions ?? 0) > 0) {
    items.push({ key: "unions", label: `Unions (${c.unions})`, children: <Unions unions={ds.unions} /> });
  }
  if ((c.filters ?? 0) > 0) {
    items.push({
      key: "filters",
      label: `Data Source Filters (${c.filters})`,
      children: <Filters filters={ds.filters} />,
    });
  }
  if ((c.customSql ?? 0) > 0) {
    items.push({
      key: "csql",
      label: `Custom SQL (${c.customSql})`,
      children: <CustomSql statements={ds.customSql} jobId={jobId} dsIndex={Math.min(idx, dsList.length - 1)} />,
    });
  }

  items.push({
    key: "classification",
    label: `Model Classification & Metrics — ${ds.classification?.type || "Unknown"}`,
    children: <Classification ds={ds} complexity={metadata.complexity} />,
  });
  items.push({
    key: "diagram",
    label: "Schema Diagram & Data Lineage",
    children: <SchemaAndLineage ds={ds} />,
  });

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card
        title={
          <Space wrap>
            <span>
              Workbook: <b>{metadata.name}</b>
            </span>
            {metadata.version && <Tag>v{metadata.version}</Tag>}
            {metadata.sourcePlatform && <Tag color="default">{metadata.sourcePlatform}</Tag>}
            <Tag color="blue">{metadata.counts?.dataSources ?? dsList.length} data source(s)</Tag>
          </Space>
        }
        extra={
          <Space wrap>
            {dsList.length > 1 && (
              <>
                <Typography.Text type="secondary">Data source</Typography.Text>
                <Select
                  value={idx}
                  style={{ minWidth: 200 }}
                  onChange={setIdx}
                  options={dsList.map((d, i) => ({ value: i, label: d.caption || d.name }))}
                />
              </>
            )}
            <ExportBar jobId={jobId} metadata={metadata} />
          </Space>
        }
      >
        {metadata.warnings?.map((w, i) => (
          <Alert key={i} type="warning" showIcon message={w} style={{ marginBottom: 8 }} />
        ))}
        <Collapse defaultActiveKey={["overview", "tables"]} items={items} />
      </Card>

      {metadata.assessment?.bestPractices && (
        <Card>
          <TechnicalAssessment assessment={metadata.assessment} />
        </Card>
      )}
    </Space>
  );
}
