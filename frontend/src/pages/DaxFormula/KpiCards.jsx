import { Row, Col, Card, Statistic } from "antd";

// Dynamic calculation-object counts. Discovery is data-driven: every count is
// derived from the parsed metadata, not a hardcoded catalogue.
export function calcObjects(metadata) {
  const dss = metadata.dataSources || [];
  const calcs = dss.flatMap((ds, i) =>
    (ds.calculations || []).map((c) => ({ ...c, _dsIndex: i, _ds: ds.caption || ds.name })));
  return {
    calcs,
    counts: {
      "Calculated Fields": calcs.length,
      "Quick Table Calcs": calcs.filter((c) => c.tableCalc || (c.categories || []).includes("Table Calculation")).length,
      "LOD Expressions": calcs.filter((c) => c.lod || (c.categories || []).some((x) => x.startsWith("LOD"))).length,
      Parameters: (metadata.parameters || []).length,
      Groups: dss.reduce((n, ds) => n + (ds.groups || []).length, 0),
      Sets: dss.reduce((n, ds) => n + (ds.sets || []).length, 0),
      Bins: dss.reduce((n, ds) => n + (ds.bins || []).length, 0),
      "Custom Calculations": calcs.filter(
        (c) => (c.categories || []).length === 1 && c.categories[0] === "Basic / Arithmetic").length,
    },
  };
}

export default function KpiCards({ metadata }) {
  const { counts } = calcObjects(metadata);
  return (
    <Row gutter={[12, 12]}>
      {Object.entries(counts).map(([label, value]) => (
        <Col key={label} xs={12} sm={8} md={6} lg={3}>
          <Card size="small">
            <Statistic title={label} value={value} />
          </Card>
        </Col>
      ))}
    </Row>
  );
}
