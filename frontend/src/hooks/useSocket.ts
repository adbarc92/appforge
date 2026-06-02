import { useEffect } from "react";
import { io, type Socket } from "socket.io-client";

import { useProjectStore } from "../stores/projectStore";
import type {
  AgentMessagePayload,
  AgentStatusPayload,
  ApprovalRequest,
  BudgetUpdatePayload,
  PhaseCompletePayload,
  ProjectCreatedPayload,
  ProjectStateSnapshot,
} from "../types";

let socketSingleton: Socket | null = null;
let listenersAttached = false;

// Attach the store-dispatched event handlers exactly once. useSocket() is
// called from several components that all share this one socket singleton; if
// each registered its own listeners, every event would be handled N times
// (triplicate chat messages, duplicate React keys). Guard so it happens once.
function attachListeners(socket: Socket): void {
  if (listenersAttached) return;
  listenersAttached = true;

  socket.on("project_created", (p: ProjectCreatedPayload) => {
    useProjectStore.getState().reset(p.project_id, useProjectStore.getState().idea);
  });
  socket.on("agent_status", (p: AgentStatusPayload) => {
    useProjectStore.getState().updateAgentStatus(p.agent, p.status, p.details);
  });
  socket.on("agent_message", (p: AgentMessagePayload) => {
    useProjectStore.getState().addMessage({
      id: `${Date.now()}-${Math.random()}`,
      role: "agent",
      agent: p.agent,
      text: p.text,
      timestamp: Date.now(),
    });
  });
  socket.on("approval_required", (p: ApprovalRequest) => {
    useProjectStore.getState().setApprovalPending(p);
    // Only set the PRD for the PRD approval gate (phase 3). When kind is
    // "plan" (phase 4 planning gate) we must NOT overwrite the already-approved
    // PRD that lives in the store.
    if (p.kind !== "plan") {
      useProjectStore.getState().setPRD(p.content);
    }
  });
  socket.on("budget_update", (p: BudgetUpdatePayload) => {
    useProjectStore.getState().setBudget(p);
  });
  socket.on("planning_artifact", (p: { kind: "adr" | "tasks" | "design"; content: unknown }) => {
    useProjectStore.getState().setPlanningArtifact(p.kind, p.content);
  });
  socket.on("phase_complete", (p: PhaseCompletePayload) => {
    useProjectStore.getState().addMessage({
      id: `${Date.now()}-${Math.random()}-phase`,
      role: "system",
      text: `Phase ${p.phase} ${p.status ?? "complete"}: ${p.summary}`,
      timestamp: Date.now(),
    });
    // Resolve the approval card UI. We intentionally do NOT clear the prd here:
    // a phase_complete for the planning gate fires while the approved PRD is
    // still needed for downstream agents (solution_architect reads it).
    useProjectStore.getState().setApprovalPending(null);
  });
  socket.on("project_state", (p: ProjectStateSnapshot) => {
    useProjectStore.getState().hydrateFromState(p);
  });
}

function getSocket(): Socket {
  if (!socketSingleton) {
    socketSingleton = io("/", { path: "/socket.io", autoConnect: true });
    attachListeners(socketSingleton);
  }
  return socketSingleton;
}

export interface UseSocketApi {
  startProject: (idea: string) => void;
  sendMessage: (text: string) => void;
  approve: (comment?: string) => void;
  reject: (comment?: string) => void;
  modify: (comment: string) => void;
  retry: () => void;
  loadProject: (projectId: string) => void;
}

export function useSocket(): UseSocketApi {
  // Early-init on mount so the socket handshake begins (and listeners are
  // attached to receive server events) before the first user action — e.g. the
  // top-level App mount that doesn't itself emit. getSocket() is idempotent.
  useEffect(() => {
    getSocket();
  }, []);

  return {
    startProject: (idea) => {
      getSocket().emit("start_project", { idea });
    },
    sendMessage: (text) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      getSocket().emit("user_message", { project_id: projectId, text });
    },
    approve: (comment) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      getSocket().emit("approve", { project_id: projectId, comment });
    },
    reject: (comment) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      getSocket().emit("reject", { project_id: projectId, comment });
    },
    modify: (comment) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      getSocket().emit("modify", { project_id: projectId, comment });
    },
    retry: () => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      getSocket().emit("retry", { project_id: projectId });
    },
    loadProject: (projectId) => {
      getSocket().emit("load_project", { project_id: projectId });
    },
  };
}
