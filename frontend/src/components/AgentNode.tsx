import { memo } from "react";

import type { AgentState, AgentStatus } from "../types";

interface AgentNodeProps {
  data: AgentState;
}

const STATUS_CLASS: Record<AgentStatus, string> = {
  pending: "bg-gray-200 border-gray-400 text-gray-700",
  running: "bg-blue-100 border-blue-500 text-blue-900 animate-pulse",
  complete: "bg-green-100 border-green-500 text-green-900",
  error: "bg-red-100 border-red-500 text-red-900",
  downgraded: "bg-orange-100 border-orange-500 text-orange-900",
};

export const AgentNode = memo(function AgentNode({ data }: AgentNodeProps) {
  return (
    <div
      data-testid="agent-node"
      data-status={data.status}
      className={`rounded-lg border-2 p-3 min-w-[160px] shadow-sm ${STATUS_CLASS[data.status]}`}
    >
      <div className="font-semibold text-sm">{data.name}</div>
      {data.details && (
        <div className="text-xs opacity-75 mt-1 truncate">{data.details}</div>
      )}
    </div>
  );
});
