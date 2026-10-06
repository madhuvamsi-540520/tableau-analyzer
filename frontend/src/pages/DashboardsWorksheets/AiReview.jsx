import { useState } from "react";
import { Card, Switch, Input, Button, Space, Tag, Typography, Alert, App as AntApp } from "antd";
import { RobotOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { api } from "../../api/client.js";

const { Text, Paragraph } = Typography;

// AI Rationalization Review. Offline deterministic summary by default; a one-click
// toggle switches to an LLM narrative. The API key is held in memory only
// (component state) and sent per-request — never written to localStorage/disk.
export default function AiReview({ jobId, initial }) {
  const { message } = AntApp.useApp();
  const [useLlm, setUseLlm] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(initial || null);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await api.rationalizationReview(jobId, { useLlm, apiKey: useLlm ? apiKey : undefined });
      setResult(res.review);
      if (res.review?.available) message.success("Review generated.");
      else if (res.review?.notes?.length) message.warning(res.review.notes[0]);
    } catch (e) {
      message.error(e.message || "Review failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      size="small"
      title={<Space><RobotOutlined /> AI Rationalization Review</Space>}
      extra={
        <Space size={8}>
          <Text type="secondary" style={{ fontSize: 12 }}>Use AI</Text>
          <Switch size="small" checked={useLlm} onChange={setUseLlm} checkedChildren={<RobotOutlined />} />
        </Space>
      }
    >
      {useLlm && (
        <Alert
          type="info" showIcon style={{ marginBottom: 12 }}
          message="AI-assisted review"
          description={
            <Space direction="vertical" style={{ width: "100%" }} size={8}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Your API key is used only for this request and is never stored. Requires network access
                to the model provider. The full analysis stays deterministic and offline; this only adds
                a narrative summary.
              </Text>
              <Input.Password
                placeholder="Anthropic API key (session only)"
                value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                autoComplete="off" style={{ maxWidth: 360 }}
              />
            </Space>
          }
        />
      )}

      <Space style={{ marginBottom: 12 }}>
        <Button
          type="primary" size="small" loading={loading}
          icon={useLlm ? <RobotOutlined /> : <ThunderboltOutlined />}
          onClick={generate} disabled={useLlm && !apiKey.trim()}
        >
          {useLlm ? "Generate with AI" : "Regenerate (offline)"}
        </Button>
        {result?.method && <Tag>{result.method === "llm" ? "AI" : "Offline summary"}</Tag>}
      </Space>

      {result?.summary ? (
        <Paragraph style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>{result.summary}</Paragraph>
      ) : (
        <Text type="secondary">No review yet.</Text>
      )}

      {result?.notes?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {result.notes.map((n, i) => <Text key={i} type="secondary" style={{ display: "block", fontSize: 12 }}>• {n}</Text>)}
        </div>
      )}
    </Card>
  );
}
