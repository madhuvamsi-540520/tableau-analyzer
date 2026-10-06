import { Card, Table, Tag, Button, Space, Typography, Alert, Popconfirm, Empty, Spin } from "antd";
import { DeleteOutlined, ReloadOutlined, FileZipOutlined, FileTextOutlined } from "@ant-design/icons";
import UploadDropzone from "../../components/UploadDropzone.jsx";
import { formatBytes } from "../../components/format.js";
import { useWorkbookJobs } from "../../hooks/useWorkbookJobs.js";
import ExecutiveSummary from "./ExecutiveSummary.jsx";
import SimilarityAnalysis from "./SimilarityAnalysis.jsx";
import Consolidation from "./Consolidation.jsx";
import VizBestPractices from "./VizBestPractices.jsx";
import DashboardQuality from "./DashboardQuality.jsx";
import KpiConsolidation from "./KpiConsolidation.jsx";
import AiReview from "./AiReview.jsx";

// Dashboard & Worksheet Rationalization — report similarity, consolidation and
// visualization-governance advisor (deterministic, with an opt-in AI review).
export default function DashboardsWorksheets() {
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
    { title: "Dashboards", align: "right", render: (_, r) => r.counts?.dashboards ?? "—" },
    { title: "Worksheets", align: "right", render: (_, r) => r.counts?.worksheets ?? "—" },
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

  const rat = detail?.rationalization;

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card
        title="Dashboards & Worksheets — Rationalization"
        extra={<Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>Refresh</Button>}
      >
        <Typography.Paragraph type="secondary">
          An intelligent Dashboard Rationalization &amp; Visualization Governance engine. It finds
          duplicate and overlapping reports, recommends consolidation (with effort/maintenance savings),
          audits every visualization against recognized best-practice frameworks (Few, Tufte,
          Cleveland &amp; McGill, Gestalt, Tableau/Power BI, WCAG), and scores dashboard quality — all
          offline, with an optional one-click AI review.
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
          ) : rat && rat.executiveSummary ? (
            <Space direction="vertical" size={16} style={{ width: "100%" }}>
              <ExecutiveSummary rat={rat} name={detail.name} />
              <SimilarityAnalysis similarity={rat.similarity} />
              <Consolidation consolidation={rat.consolidation} />
              <VizBestPractices viz={rat.vizQuality} />
              <DashboardQuality quality={rat.dashboardQuality} />
              <KpiConsolidation kpi={rat.kpiConsolidation} />
              <AiReview jobId={selectedId} initial={rat.aiReview} />
            </Space>
          ) : detail ? (
            <Empty description="No rationalization report available for this workbook (it may have no dashboards/worksheets)." />
          ) : (
            !detailLoading && <Empty description="Select a workbook to view its rationalization report." />
          )}
        </Spin>
      )}
    </Space>
  );
}
