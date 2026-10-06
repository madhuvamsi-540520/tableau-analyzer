import { useState } from "react";
import { Card, Switch, Input, Button, Space, Tag, Typography, Alert, Spin, App as AntApp } from "antd";
import { DownloadOutlined, RobotOutlined, EyeOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { api } from "../../api/client.js";
import PbipPreview from "./PbipPreview.jsx";

const { Text } = Typography;

// Generates an openable Power BI (PBIP) project from the selected workbook.
// Offline rule-based DAX by default; a one-click AI toggle reveals a session-only
// API-key box (held in component state, sent per-request, never persisted).
export default function GeneratePanel({ jobId, filename }) {
  const { message } = AntApp.useApp();
  const [useLlm, setUseLlm] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [summary, setSummary] = useState(null);

  const body = () => ({ useLlm, apiKey: useLlm ? apiKey : undefined });
  const aiBlocked = useLlm && !apiKey.trim();

  const preview = async () => {
    setPreviewing(true);
    try {
      const res = await api.pbipPreview(jobId, body());
      setSummary(res.summary);
    } catch (e) {
      message.error(e.message || "Preview failed.");
    } finally {
      setPreviewing(false);
    }
  };

  const download = async () => {
    setDownloading(true);
    try {
      await api.generatePbip(jobId, body());
      message.success("PBIP generated — extract the whole .zip before opening the .pbip.");
    } catch (e) {
      message.error(e.message || "Generation failed.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Card
      title={<Space><ThunderboltOutlined /> Generate Power BI Project (PBIP){filename ? <Text type="secondary">— {filename}</Text> : null}</Space>}
      extra={
        <Space size={8}>
          <Text type="secondary" style={{ fontSize: 12 }}>Use AI</Text>
          <Switch size="small" checked={useLlm} onChange={setUseLlm} checkedChildren={<RobotOutlined />} />
        </Space>
      }
    >
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Text type="secondary">
          Converts this workbook into an openable Power BI <b>.pbip</b> project (semantic model + report),
          bundled as a .zip. Tableau calculations are translated to DAX by deterministic offline rules; ones
          needing manual verification are flagged <Tag color="gold" style={{ marginInline: 2 }}>review</Tag>.
        </Text>

        {useLlm && (
          <Alert
            type="info"
            showIcon
            message="AI-assisted DAX translation"
            description={
              <Space direction="vertical" style={{ width: "100%" }} size={8}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Your API key is used only for this request and is never stored. Requires network access to the
                  model provider; if it's unreachable, generation falls back to the offline rules.
                </Text>
                <Input.Password
                  placeholder="Anthropic API key (session only)"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  autoComplete="off"
                  style={{ maxWidth: 360 }}
                />
              </Space>
            }
          />
        )}

        <Space wrap>
          <Button icon={<EyeOutlined />} onClick={preview} loading={previewing} disabled={aiBlocked}>
            Preview generation
          </Button>
          <Button type="primary" icon={<DownloadOutlined />} onClick={download} loading={downloading} disabled={aiBlocked}>
            Generate &amp; Download PBIP
          </Button>
          {useLlm ? <Tag color="purple">AI mode</Tag> : <Tag>Offline rules</Tag>}
        </Space>

        {(previewing || summary) && (
          <Spin spinning={previewing}>
            {summary && <PbipPreview summary={summary} />}
          </Spin>
        )}
      </Space>
    </Card>
  );
}
