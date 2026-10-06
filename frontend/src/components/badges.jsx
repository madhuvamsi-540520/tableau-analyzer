import { Tag } from "antd";
import { CheckOutlined, MinusOutlined } from "@ant-design/icons";

export function RoleTag({ role }) {
  return role === "measure" ? (
    <Tag color="green">measure</Tag>
  ) : (
    <Tag color="blue">dimension</Tag>
  );
}

export function ModeTag({ mode }) {
  return mode === "Extract" ? (
    <Tag color="orange">Extract</Tag>
  ) : (
    <Tag color="cyan">Live</Tag>
  );
}

export function BoolMark({ value }) {
  if (value === true) return <CheckOutlined style={{ color: "var(--accent)" }} />;
  if (value === false) return <MinusOutlined style={{ color: "var(--text-secondary)" }} />;
  return <span style={{ color: "var(--text-secondary)" }}>—</span>;
}
