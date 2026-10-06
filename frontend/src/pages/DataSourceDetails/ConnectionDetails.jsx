import { Tag, Typography, Empty } from "antd";
import SearchableTable from "../../components/SearchableTable.jsx";
import { ModeTag } from "../../components/badges.jsx";

const dash = (v) => (v == null || v === "" ? <Typography.Text type="secondary">—</Typography.Text> : v);

export default function ConnectionDetails({ connections }) {
  if (!connections?.length) return <Empty description="No connections found." />;

  const columns = [
    { title: "Type", dataIndex: "friendlyType", render: (v) => <Tag color="geekblue">{v}</Tag> },
    { title: "Class", dataIndex: "class", render: dash },
    { title: "Server", dataIndex: "server", render: dash },
    { title: "Database", dataIndex: "database", render: dash },
    { title: "Schema", dataIndex: "schema", render: dash },
    { title: "Warehouse", dataIndex: "warehouse", render: dash },
    { title: "Catalog", dataIndex: "catalog", render: dash },
    { title: "Port", dataIndex: "port", render: dash },
    { title: "Auth", dataIndex: "authentication", render: dash },
    { title: "Username", dataIndex: "username", render: dash },
    { title: "Owner", dataIndex: "owner", render: dash },
    {
      title: "File Location",
      dataIndex: "fileLocation",
      render: (v) => (v ? <Typography.Text copyable={{ text: v }}>{v}</Typography.Text> : dash(v)),
    },
    { title: "Extract", dataIndex: "isExtract", render: (v) => (v ? <ModeTag mode="Extract" /> : dash(null)) },
  ];

  return (
    <SearchableTable
      rowKey="name"
      columns={columns}
      data={connections}
      searchFields={["friendlyType", "class", "server", "database", "schema", "fileLocation"]}
      placeholder="Search connections…"
    />
  );
}
