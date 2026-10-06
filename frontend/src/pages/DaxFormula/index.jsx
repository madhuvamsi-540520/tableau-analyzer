import { Card, Table, Tag, Button, Space, Typography, Alert, Popconfirm, Empty, Spin } from "antd";
import { DeleteOutlined, ReloadOutlined, FileZipOutlined, FileTextOutlined } from "@ant-design/icons";
import UploadDropzone from "../../components/UploadDropzone.jsx";
import { formatBytes } from "../../components/format.js";
import { useWorkbookJobs } from "../../hooks/useWorkbookJobs.js";
import KpiCards from "./KpiCards.jsx";
import CalcTable from "./CalcTable.jsx";

// DAX & Formula — the centralized repository for all workbook calculation
// intelligence. Shares session-scoped jobs with the other tabs via useWorkbookJobs.
export default function DaxFormula() {
  const {
    jobs, errors, setErrors, busy, loading,
    selectedId, detail, detailLoading, detailError,
    refresh, select, upload, remove,
  } = useWorkbookJobs();

  const columns = [
    {
      title: "Workbook", dataIndex: "filename",
      sorter: (a, b) => a.filename.localeCompare(b.filename),
      render: (name, row) => (
        <Space>{row.kind === "twbx" ? <FileZipOutlined /> : <FileTextOutlined />}<span>{name}</span></Space>
      ),
    },
    { title: "Type", dataIndex: "kind", render: (k) => <Tag color={k === "twbx" ? "geekblue" : "default"}>{k}</Tag> },
    { title: "Data sources", align: "right", render: (_, r) => r.counts?.dataSources ?? "—" },
    { title: "Size", dataIndex: "size", align: "right", render: (n) => formatBytes(n) },
    {
      title: "", align: "right",
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
        title="DAX & Formula — Calculation Intelligence"
        extra={<Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>Refresh</Button>}
      >
        <Typography.Paragraph type="secondary">
          Deep analysis of every calculation in a Tableau workbook — formulas, dependencies, performance,
          data types, migration effort, and Power BI (DAX / M) conversion guidance. Upload a .twb / .twbx
          or pick one already analyzed.
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

      {selectedId && (
        <Spin spinning={detailLoading}>
          {detailError ? (
            <Alert type="error" showIcon message={detailError} />
          ) : detail ? (
            <Space direction="vertical" size={16} style={{ width: "100%" }}>
              <Card title={`Calculation Summary — ${detail.name}`}>
                <KpiCards metadata={detail} />
              </Card>
              <Card title="Calculations">
                <CalcTable metadata={detail} jobId={selectedId} />
              </Card>
            </Space>
          ) : (
            !detailLoading && <Empty description="Select a workbook to explore its calculations." />
          )}
        </Spin>
      )}
    </Space>
  );
}
