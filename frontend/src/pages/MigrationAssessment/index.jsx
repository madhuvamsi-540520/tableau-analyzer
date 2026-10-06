import { Card, Table, Tag, Button, Space, Typography, Alert, Popconfirm, Empty } from "antd";
import { DeleteOutlined, ReloadOutlined, FileZipOutlined, FileTextOutlined, SwapOutlined } from "@ant-design/icons";
import UploadDropzone from "../../components/UploadDropzone.jsx";
import { formatBytes } from "../../components/format.js";
import { useWorkbookJobs } from "../../hooks/useWorkbookJobs.js";
import GeneratePanel from "./GeneratePanel.jsx";

// Migration Assessment — turns an analyzed Tableau workbook into an openable
// Power BI (PBIP) project. Shares session-scoped jobs with the other tabs via
// useWorkbookJobs, so a workbook uploaded anywhere in the app is ready here.
export default function MigrationAssessment() {
  const { jobs, errors, setErrors, busy, loading, selectedId, refresh, select, upload, remove } =
    useWorkbookJobs();

  const selected = jobs.find((j) => j.jobId === selectedId);

  const columns = [
    {
      title: "Workbook",
      dataIndex: "filename",
      sorter: (a, b) => a.filename.localeCompare(b.filename),
      render: (name, row) => (
        <Space>{row.kind === "twbx" ? <FileZipOutlined /> : <FileTextOutlined />}<span>{name}</span></Space>
      ),
    },
    { title: "Type", dataIndex: "kind", render: (k) => <Tag color={k === "twbx" ? "geekblue" : "default"}>{k}</Tag> },
    { title: "Data sources", align: "right", render: (_, r) => r.counts?.dataSources ?? "—" },
    { title: "Size", dataIndex: "size", align: "right", render: (n) => formatBytes(n) },
    {
      title: "",
      align: "right",
      render: (_, row) => (
        <Popconfirm
          title="Remove this workbook?"
          onConfirm={(e) => { e?.stopPropagation?.(); remove(row.jobId); }}
          onCancel={(e) => e?.stopPropagation?.()}
        >
          <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card
        title={<Space><SwapOutlined /> Migration Assessment — Tableau → Power BI (PBIP)</Space>}
        extra={<Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>Refresh</Button>}
      >
        <Typography.Paragraph type="secondary">
          Generate an openable Power BI project (<b>.pbip</b>) directly from a Tableau workbook — semantic
          model (tables, relationships, calculated fields → DAX) and a report page per worksheet, packaged
          as a .zip. Upload a .twb / .twbx or pick one already analyzed in another tab.
        </Typography.Paragraph>
        <UploadDropzone onFiles={upload} disabled={busy} />
      </Card>

      {errors.length > 0 && (
        <Alert
          type="warning" showIcon closable onClose={() => setErrors([])}
          message="Some files could not be processed"
          description={<ul style={{ margin: 0, paddingLeft: 18 }}>{errors.map((e, i) => (<li key={i}><b>{e.filename}</b>: {e.error}</li>))}</ul>}
        />
      )}

      <Card title={`Workbooks (${jobs.length})`}>
        <Table
          rowKey="jobId" size="middle" loading={loading} columns={columns} dataSource={jobs}
          pagination={jobs.length > 10 ? { pageSize: 10 } : false}
          onRow={(row) => ({ onClick: () => select(row.jobId), style: { cursor: "pointer" } })}
          rowClassName={(row) => (row.jobId === selectedId ? "ant-table-row-selected" : "")}
          locale={{ emptyText: <Empty description="No workbooks yet — upload a .twb or .twbx to begin." /> }}
        />
      </Card>

      {selectedId ? (
        <GeneratePanel jobId={selectedId} filename={selected?.filename} />
      ) : (
        jobs.length > 0 && <Empty description="Select a workbook to generate its Power BI project." />
      )}
    </Space>
  );
}
