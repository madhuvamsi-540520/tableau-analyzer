import { Result, Card } from "antd";
import { ToolOutlined } from "@ant-design/icons";

export default function ComingSoon({ title }) {
  return (
    <Card>
      <Result
        icon={<ToolOutlined />}
        title={`${title} — Coming soon`}
        subTitle="This module is planned for a future phase. The Data Source Details module is available now."
      />
    </Card>
  );
}
