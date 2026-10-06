import { Button, Space, Dropdown, App as AntApp } from "antd";
import {
  FileExcelOutlined,
  FileTextOutlined,
  FilePdfOutlined,
  CodeOutlined,
  DownloadOutlined,
  CopyOutlined,
} from "@ant-design/icons";
import { api } from "../../api/client.js";

export default function ExportBar({ jobId, metadata }) {
  const { message } = AntApp.useApp();

  const doExport = async (format) => {
    try {
      await api.exportJob(jobId, format);
    } catch (e) {
      message.error(e.message || "Export failed.");
    }
  };

  const copyJson = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(metadata, null, 2));
      message.success("Metadata (JSON) copied to clipboard.");
    } catch {
      message.error("Copy failed.");
    }
  };

  const items = [
    { key: "xlsx", label: "Excel (.xlsx)", icon: <FileExcelOutlined /> },
    { key: "csv", label: "CSV (.csv)", icon: <FileTextOutlined /> },
    { key: "json", label: "JSON (.json)", icon: <CodeOutlined /> },
    { key: "pdf", label: "PDF (.pdf)", icon: <FilePdfOutlined /> },
  ];

  return (
    <Space wrap>
      <Dropdown menu={{ items, onClick: ({ key }) => doExport(key) }}>
        <Button type="primary" icon={<DownloadOutlined />}>
          Export
        </Button>
      </Dropdown>
      <Button icon={<CopyOutlined />} onClick={copyJson}>
        Copy JSON
      </Button>
    </Space>
  );
}
