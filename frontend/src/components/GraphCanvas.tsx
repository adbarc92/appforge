import { type ComponentType, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { AgentNode } from "./AgentNode";
import { useProjectStore } from "../stores/projectStore";

const LAYOUT: Record<string, { x: number; y: number }> = {
  orchestrator: { x: 400, y: 0 },
  budget_guard: { x: 700, y: 0 },
  clarifying_pm: { x: 100, y: 100 },
  product_owner: { x: 400, y: 100 },
  solution_architect: { x: 100, y: 220 },
  tech_lead: { x: 300, y: 220 },
  uiux_designer: { x: 500, y: 220 },
  frontend: { x: 100, y: 360 },
  backend: { x: 250, y: 360 },
  database: { x: 400, y: 360 },
  ai_ml: { x: 550, y: 360 },
  devops: { x: 100, y: 500 },
  security: { x: 250, y: 500 },
  qa_test: { x: 400, y: 500 },
  technical_writer: { x: 550, y: 500 },
  delivery_summarizer: { x: 400, y: 620 },
};

// AgentNode's prop shape is narrower than the generic NodeProps React Flow
// expects; double-cast through unknown to satisfy the nodeTypes map without
// widening AgentState itself.
const nodeTypes = {
  agent: AgentNode,
} as unknown as Record<string, ComponentType<NodeProps>>;

export function GraphCanvas() {
  const agents = useProjectStore((s) => s.agents);
  const nodes: Node[] = useMemo(
    () =>
      Object.values(agents).map((agent) => ({
        id: agent.id,
        type: "agent",
        position: LAYOUT[agent.id] ?? { x: 0, y: 0 },
        // Cast data so Node<Record<string,unknown>> accepts AgentState
        data: agent as unknown as Record<string, unknown>,
      })),
    [agents],
  );

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={[]}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        fitView
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
