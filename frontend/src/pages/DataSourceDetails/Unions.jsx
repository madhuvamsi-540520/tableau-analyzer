import { Tag, Typography, Empty, Space, Card } from "antd";

export default function Unions({ unions }) {
  if (!unions?.length) return <Empty description="No unions found." />;

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      {unions.map((u, i) => (
        <Card key={i} size="small" title={<Space>{u.name} <Tag color="purple">{u.unionType}</Tag></Space>}>
          <Typography.Text type="secondary">Tables participating: </Typography.Text>
          <Space wrap size={4}>
            {u.tables.map((t) => (
              <Tag key={t} color="geekblue">
                {t}
              </Tag>
            ))}
          </Space>
          {u.conditions?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <Typography.Text type="secondary">Conditions: </Typography.Text>
              {u.conditions.join("; ")}
            </div>
          )}
        </Card>
      ))}
    </Space>
  );
}
