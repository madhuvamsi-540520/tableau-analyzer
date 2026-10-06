import { useState } from "react";
import {
  Card, Switch, Input, Button, Space, Tag, Typography, Alert, List, Divider, App as AntApp,
} from "antd";
import { ThunderboltOutlined, RobotOutlined } from "@ant-design/icons";
import { api } from "../../api/client.js";

const { Text, Paragraph } = Typography;

function confidenceTag(c) {
  if (c == null) return null;
  const pct = Math.round(c * 100);
  const color = c >= 0.8 ? "green" : c >= 0.5 ? "gold" : "red";
  return <Tag color={color}>Confidence {pct}%</Tag>;
}

function DaxBlock({ label, code }) {
  if (!code) return null;
  return (
    <div style={{ marginBottom: 8 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
      <Paragraph
        code
        copyable={{ text: code }}
        style={{ whiteSpace: "pre-wrap", marginBottom: 0, fontSize: 12 }}
      >
        {code}
      </Paragraph>
    </div>
  );
}

// Shows the precomputed OFFLINE DAX suggestion, with a one-click switch to
// AI-assisted conversion. The API key is held in memory only (component state)
// and sent per-request — never written to localStorage/disk.
export default function DaxSuggestion({ calc, jobId }) {
  const { message } = AntApp.useApp();
  const [useLlm, setUseLlm] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(calc.dax || null); // start with offline suggestion

  const generate = async () => {
    setLoading(true);
    try {
      const res = await api.suggestDax(jobId, {
        calcName: calc.name,
        dataSourceIndex: calc._dsIndex,
        useLlm,
        apiKey: useLlm ? apiKey : undefined,
      });
      setResult(res.suggestion);
      if (res.suggestion?.daxMeasure || res.suggestion?.daxColumn) message.success("Conversion generated.");
    } catch (e) {
      message.error(e.message || "Conversion failed.");
    } finally {
      setLoading(false);
    }
  };

  const hasDax = result && (result.daxMeasure || result.daxColumn || result.powerQuery);

  return (
    <Card
      size="small"
      title={<Space><ThunderboltOutlined /> Power BI Conversion</Space>}
      extra={
        <Space size={8}>
          <Text type="secondary" style={{ fontSize: 12 }}>Use AI</Text>
          <Switch
            size="small"
            checked={useLlm}
            onChange={setUseLlm}
            checkedChildren={<RobotOutlined />}
          />
        </Space>
      }
    >
      {useLlm && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="AI-assisted conversion"
          description={
            <Space direction="vertical" style={{ width: "100%" }} size={8}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Your API key is used only for this request and is never stored. Requires network access
                to the model provider.
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

      <Space style={{ marginBottom: 12 }}>
        <Button
          type="primary"
          size="small"
          loading={loading}
          icon={useLlm ? <RobotOutlined /> : <ThunderboltOutlined />}
          onClick={generate}
          disabled={useLlm && !apiKey.trim()}
        >
          {useLlm ? "Generate with AI" : "Regenerate (offline)"}
        </Button>
        {result && confidenceTag(result.confidence)}
        {result?.method && <Tag>{result.method === "llm" ? "AI" : "Offline rules"}</Tag>}
      </Space>

      {hasDax ? (
        <>
          <DaxBlock label="DAX measure" code={result.daxMeasure} />
          <DaxBlock label="Calculated column" code={result.daxColumn} />
          <DaxBlock label="Power Query (M)" code={result.powerQuery} />
        </>
      ) : (
        <Text type="secondary">No automatic conversion available — see limitations below.</Text>
      )}

      {result?.assumptions?.length > 0 && (
        <>
          <Divider style={{ margin: "10px 0" }} />
          <Text type="secondary" style={{ fontSize: 12 }}>Assumptions</Text>
          <List
            size="small"
            dataSource={result.assumptions}
            renderItem={(a) => <List.Item style={{ padding: "2px 0", border: "none" }}>• {a}</List.Item>}
          />
        </>
      )}
      {result?.limitations?.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginTop: 8 }}
          message="Limitations"
          description={<ul style={{ margin: 0, paddingLeft: 18 }}>{result.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>}
        />
      )}
    </Card>
  );
}
