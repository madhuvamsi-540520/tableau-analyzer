import {
  Card, Table, Tag, Button, Space, Typography, Alert, Popconfirm, Empty, Spin,
} from "antd";
import {
  DeleteOutlined, ReloadOutlined, FileZipOutlined, FileTextOutlined,
} from "@ant-design/icons";
import UploadDropzone from "../../components/UploadDropzone.jsx";
import { formatBytes } from "../../components/format.js";
import { useState } from "react";
import { useWorkbookJobs } from "../../hooks/useWorkbookJobs.js";
import WorkbookSummary from "./WorkbookSummary.jsx";
import DashboardStoryInventory from "./DashboardStoryInventory.jsx";
import VisualizationSummary from "./VisualizationSummary.jsx";
import WorksheetInventory from "./WorksheetInventory.jsx";
import WorksheetDetail from "./WorksheetDetail.jsx";
import MigrationAssessment from "./MigrationAssessment.jsx";

export default function TableauAnalysis() {
  const {
    jobs, errors, setErrors, busy, loading,
    selectedId, detail, detailLoading, detailError,
    refresh, select, upload, remove,
  } = useWorkbookJobs();

  const [selectedWs, setSelectedWs] = useState(null);

  const columns = [
    {
      title: "Workbook",
      dataIndex: "filename",
      sorter: (a, b) => a.filename.localeCompare(b.filename),
      render: (name, row) => (
        <Space>
          {row.kind === "twbx" ? <FileZipOutlined /> : <FileTextOutlined />}
          <span>{name}</span>
        </Space>
      ),
    },
    { title: "Type", dataIndex: "kind", render: (k) => <Tag color={k === "twbx" ? "geekblue" : "default"}>{k}</Tag> },
    { title: "Data sources", align: "right", render: (_, r) => r.counts?.dataSources ?? "—" },
    { title: "Tables", align: "right", render: (_, r) => r.counts?.tables ?? "—" },
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
        title="Tableau Analysis — Workbook Overview"
        extra={<Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>Refresh</Button>}
      >
        <Typography.Paragraph type="secondary">
          Upload one or more Tableau workbooks (.twb / .twbx). This is the primary workbook overview:
          summary metrics, worksheet inventory, and the Power BI migration assessment.
        </Typography.Paragraph>
        <UploadDropzone onFiles={upload} disabled={busy} />
      </Card>

      {errors.length > 0 && (
        <Alert
          type="warning"
          showIcon
          closable
          onClose={() => setErrors([])}
          message="Some files could not be processed"
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {errors.map((e, i) => (<li key={i}><b>{e.filename}</b>: {e.error}</li>))}
            </ul>
          }
        />
      )}

      <Card title={`Workbooks (${jobs.length})`}>
        <Table
          rowKey="jobId"
          size="middle"
          loading={loading}
          columns={columns}
          dataSource={jobs}
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
              <Card title={`Summary — ${detail.name}`}>
                <WorkbookSummary metadata={detail} />
              </Card>
              <Card title="Dashboards & Stories">
                <DashboardStoryInventory metadata={detail} />
              </Card>
              <Card title="Visualizations">
                <VisualizationSummary metadata={detail} />
              </Card>
              <Card title={`Worksheet Inventory (${(detail.worksheets || []).length})`}>
                <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
                  Select a worksheet to drill into its fields, marks, encodings and detected visual type.
                </Typography.Paragraph>
                <WorksheetInventory metadata={detail} onSelect={setSelectedWs} />
              </Card>
              <Card title="Power BI Migration Assessment">
                <MigrationAssessment migration={detail.migration} />
              </Card>
            </Space>
          ) : (
            !detailLoading && <Empty description="Select a workbook to view its overview." />
          )}
        </Spin>
      )}

      <WorksheetDetail
        ws={selectedWs}
        metadata={detail}
        open={!!selectedWs}
        onClose={() => setSelectedWs(null)}
      />
    </Space>
  );
}
