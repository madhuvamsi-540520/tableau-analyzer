import { Upload, Typography } from "antd";
import { InboxOutlined } from "@ant-design/icons";

const { Dragger } = Upload;

// Presentational dropzone. Upload is handled by the parent (customRequest is a
// no-op so Ant Design does not auto-POST); the parent batches selected files.
export default function UploadDropzone({ onFiles, disabled }) {
  return (
    <Dragger
      multiple
      accept=".twb,.twbx"
      disabled={disabled}
      showUploadList={false}
      beforeUpload={() => false}
      onChange={(info) => {
        const files = info.fileList
          .map((f) => f.originFileObj)
          .filter(Boolean);
        if (files.length) onFiles(files);
      }}
      customRequest={({ onSuccess }) => onSuccess && onSuccess("ok")}
    >
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">Click or drag Tableau workbooks here to analyze</p>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        Supports <b>.twb</b> and <b>.twbx</b> — one or more files.
      </Typography.Paragraph>
    </Dragger>
  );
}
