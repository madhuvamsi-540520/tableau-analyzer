import { Row, Col, Card } from "antd";
import SchemaDiagram from "./SchemaDiagram.jsx";
import LineageSummary from "./LineageSummary.jsx";

export default function SchemaAndLineage({ ds }) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={15}>
        <Card size="small" title="Schema Diagram" styles={{ body: { padding: 8 } }}>
          <SchemaDiagram ds={ds} />
        </Card>
      </Col>
      <Col xs={24} lg={9}>
        <LineageSummary ds={ds} />
      </Col>
    </Row>
  );
}
