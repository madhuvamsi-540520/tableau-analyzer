import { useCallback, useEffect, useState } from "react";
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Alert,
  Popconfirm,
  Empty,
  Spin,
  App as AntApp,
  Tooltip,
} from "antd";
import {
  DeleteOutlined,
  ReloadOutlined,
  FileZipOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import UploadDropzone from "../../components/UploadDropzone.jsx";
import { formatBytes } from "../../components/format.js";
import { api } from "../../api/client.js";
import WorkbookDetail from "./WorkbookDetail.jsx";

export default function DataSourceDetails() {
  const { message } = AntApp.useApp();
  const [jobs, setJobs] = useState([]);
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listJobs();
      setJobs(data.jobs || []);
      return data.jobs || [];
    } catch (e) {
      message.error(e.message || "Could not load workbooks.");
      return [];
    } finally {
      setLoading(false);
    }
  }, [message]);

  const select = useCallback(
    async (jobId) => {
      setSelectedId(jobId);
      setDetail(null);
      setDetailError(null);
      setDetailLoading(true);
      try {
        const data = await api.getJob(jobId);
        setDetail(data.metadata || null);
      } catch (e) {
        setDetailError(e.message || "Could not load workbook metadata.");
      } finally {
        setDetailLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleFiles = async (files) => {
    setBusy(true);
    setErrors([]);
    try {
      const res = await api.upload(files);
      const ok = (res.jobs || []).filter((j) => j.ok);
      const bad = (res.jobs || []).filter((j) => !j.ok);
      setErrors(bad);
      if (ok.length) message.success(`Analyzed ${ok.length} workbook(s).`);
      if (bad.length) message.warning(`${bad.length} file(s) could not be processed.`);
      await refresh();
      if (ok.length) select(ok[0].jobId);
    } catch (e) {
      message.error(e.message || "Upload failed.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (jobId) => {
    try {
      await api.deleteJob(jobId);
      if (jobId === selectedId) {
        setSelectedId(null);
        setDetail(null);
      }
      message.success("Removed.");
      await refresh();
    } catch (e) {
      message.error(e.message || "Delete failed.");
    }
  };

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
    {
      title: "Type",
      dataIndex: "kind",
      filters: [
        { text: ".twb", value: "twb" },
        { text: ".twbx", value: "twbx" },
      ],
      onFilter: (v, row) => row.kind === v,
      render: (kind) => <Tag color={kind === "twbx" ? "geekblue" : "default"}>{kind}</Tag>,
    },
    {
      title: "Data sources",
      key: "ds",
      align: "right",
      render: (_, row) => row.counts?.dataSources ?? "—",
    },
    {
      title: "Tables",
      key: "tbl",
      align: "right",
      render: (_, row) => row.counts?.tables ?? "—",
    },
    {
      title: "Columns",
      key: "col",
      align: "right",
      render: (_, row) => row.counts?.columns ?? "—",
    },
    { title: "Size", dataIndex: "size", align: "right", render: (n) => formatBytes(n) },
    {
      title: "Bundled",
      key: "bundled",
      render: (_, row) => {
        const p = row.packaging || {};
        if (row.kind !== "twbx") return <Typography.Text type="secondary">—</Typography.Text>;
        const flat = p.flatFiles?.length || 0;
        const ext = p.extracts?.length || 0;
        return (
          <Space size={4} wrap>
            {flat > 0 && (
              <Tooltip title={p.flatFiles.map((f) => f.name).join(", ")}>
                <Tag>{flat} file(s)</Tag>
              </Tooltip>
            )}
            {ext > 0 && (
              <Tooltip title={p.extracts.map((f) => `${f.name} (${formatBytes(f.size)})`).join(", ")}>
                <Tag color="orange">{ext} extract(s)</Tag>
              </Tooltip>
            )}
            {flat === 0 && ext === 0 && <Typography.Text type="secondary">none</Typography.Text>}
          </Space>
        );
      },
    },
    {
      title: "",
      key: "actions",
      align: "right",
      render: (_, row) => (
        <Popconfirm
          title="Remove this workbook?"
          onConfirm={(e) => {
            e?.stopPropagation?.();
            remove(row.jobId);
          }}
          onCancel={(e) => e?.stopPropagation?.()}
        >
          <Button
            size="small"
            danger
            type="text"
            icon={<DeleteOutlined />}
            onClick={(e) => e.stopPropagation()}
          />
        </Popconfirm>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card
        title="Data Source Details — Inventory"
        extra={
          <Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
            Refresh
          </Button>
        }
      >
        <Typography.Paragraph type="secondary">
          Upload one or more Tableau workbooks (.twb / .twbx) to build an enterprise metadata
          inventory. Select a workbook below to view its data sources, connections, tables and
          columns.
        </Typography.Paragraph>
        <UploadDropzone onFiles={handleFiles} disabled={busy} />
      </Card>

      {errors.length > 0 && (
        <Alert
          type="warning"
          showIcon
          message="Some files could not be processed"
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {errors.map((e, i) => (
                <li key={i}>
                  <b>{e.filename}</b>: {e.error}
                </li>
              ))}
            </ul>
          }
          closable
          onClose={() => setErrors([])}
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
          onRow={(row) => ({
            onClick: () => select(row.jobId),
            style: { cursor: "pointer" },
          })}
          rowClassName={(row) => (row.jobId === selectedId ? "ant-table-row-selected" : "")}
          locale={{
            emptyText: (
              <Empty description="No workbooks yet — upload a .twb or .twbx to begin." />
            ),
          }}
        />
      </Card>

      {selectedId && (
        <Spin spinning={detailLoading}>
          {detailError ? (
            <Alert type="error" showIcon message={detailError} />
          ) : detail ? (
            <WorkbookDetail metadata={detail} jobId={selectedId} />
          ) : (
            !detailLoading && <Empty description="Select a workbook to view its metadata." />
          )}
        </Spin>
      )}
    </Space>
  );
}
