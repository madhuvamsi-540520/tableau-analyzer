import { useMemo } from "react";
import { ReactFlow, Background, Controls, MarkerType } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import { Empty } from "antd";
import { BRAND } from "../../theme/brand.js";

const NODE_W = 190;
const NODE_H = 64;

const ROLE_STYLE = {
  fact: { border: "#fa8c16", accent: "#fa8c16" },
  dim: { border: "#1f6feb", accent: "#1f6feb" },
  table: { border: "#8c8c8c", accent: "#8c8c8c" },
};

function nodeLabel(t, role) {
  const s = ROLE_STYLE[role];
  return (
    <div style={{ textAlign: "left", lineHeight: 1.3 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: s.accent, flexShrink: 0 }} />
        <b style={{ color: "var(--text-primary)" }}>{t.name}</b>
      </div>
      <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
        {role !== "table" ? `${role} · ` : ""}
        {t.columnCount} cols{t.rowCount != null ? ` · ${t.rowCount.toLocaleString()} rows` : ""}
      </div>
    </div>
  );
}

function layout(nodes, edges) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 45, ranksep: 90 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const p = g.node(n.id);
    return { ...n, position: { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 } };
  });
}

function build(ds) {
  const facts = new Set(ds.classification?.factTables || []);
  const dims = new Set(ds.classification?.dimensionTables || []);
  // Extract objects are a storage mechanism, not tables — exclude from the diagram.
  const physicalTables = (ds.tables || []).filter((t) => !t.isExtract);
  const nodes = physicalTables.map((t) => {
    const role = facts.has(t.name) ? "fact" : dims.has(t.name) ? "dim" : "table";
    const s = ROLE_STYLE[role];
    return {
      id: t.name,
      data: { label: nodeLabel(t, role) },
      position: { x: 0, y: 0 },
      style: {
        width: NODE_W,
        borderRadius: 8,
        border: `2px solid ${s.border}`,
        background: "var(--bg)",
        padding: "8px 10px",
        boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
      },
    };
  });
  const ids = new Set(nodes.map((n) => n.id));
  const edges = (ds.relationships || [])
    .filter((r) => ids.has(r.parentTable) && ids.has(r.childTable))
    .map((r, i) => ({
      id: `e${i}`,
      source: r.parentTable,
      target: r.childTable,
      label: r.joinType || r.kind,
      labelStyle: { fontSize: 11, fill: "var(--text-secondary)" },
      labelBgStyle: { fill: "var(--surface-alt)" },
      labelBgPadding: [4, 2],
      markerEnd: { type: MarkerType.ArrowClosed, color: BRAND.accent },
      style: { stroke: BRAND.accent, strokeWidth: 1.5 },
    }));
  return { nodes: layout(nodes, edges), edges };
}

export default function SchemaDiagram({ ds }) {
  const { nodes, edges } = useMemo(() => build(ds), [ds]);

  if (!nodes.length) return <Empty description="No tables to diagram." />;

  return (
    <div
      style={{
        height: 460,
        border: "1px solid var(--border)",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        minZoom={0.2}
        nodesConnectable={false}
        edgesFocusable={false}
        nodesDraggable
      >
        <Background gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
