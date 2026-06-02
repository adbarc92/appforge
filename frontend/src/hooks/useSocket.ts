import { useEffect, useRef } from "react";
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

function getSocket(): Socket {
  if (!socketSingleton) {
    socketSingleton = io("/", { path: "/socket.io", autoConnect: true });
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
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socket = getSocket();
    socketRef.current = socket;
    const store = useProjectStore.getState;

    const onProjectCreated = (p: ProjectCreatedPayload) => {
      useProjectStore.getState().reset(p.project_id, store().idea);
    };
    const onAgentStatus = (p: AgentStatusPayload) => {
      useProjectStore.getState().updateAgentStatus(p.agent, p.status, p.details);
    };
    const onAgentMessage = (p: AgentMessagePayload) => {
      useProjectStore.getState().addMessage({
        id: `${Date.now()}-${Math.random()}`,
        role: "agent",
        agent: p.agent,
        text: p.text,
        timestamp: Date.now(),
      });
    };
    const onApprovalRequired = (p: ApprovalRequest) => {
      useProjectStore.getState().setApprovalPending(p);
      useProjectStore.getState().setPRD(p.content);
    };
    const onBudgetUpdate = (p: BudgetUpdatePayload) => {
      useProjectStore.getState().setBudget(p);
    };
    const onPhaseComplete = (p: PhaseCompletePayload) => {
      useProjectStore.getState().addMessage({
        id: `${Date.now()}-phase`,
        role: "system",
        text: `Phase ${p.phase} ${p.status ?? "complete"}: ${p.summary}`,
        timestamp: Date.now(),
      });
      // The approval gate is resolved once the phase completes; clear the
      // card and the draft PRD so the UI reflects the finished state.
      useProjectStore.getState().setApprovalPending(null);
      useProjectStore.getState().setPRD(null);
    };
    const onProjectState = (p: ProjectStateSnapshot) => {
      useProjectStore.getState().hydrateFromState(p);
    };

    socket.on("project_created", onProjectCreated);
    socket.on("agent_status", onAgentStatus);
    socket.on("agent_message", onAgentMessage);
    socket.on("approval_required", onApprovalRequired);
    socket.on("budget_update", onBudgetUpdate);
    socket.on("phase_complete", onPhaseComplete);
    socket.on("project_state", onProjectState);

    return () => {
      socket.off("project_created", onProjectCreated);
      socket.off("agent_status", onAgentStatus);
      socket.off("agent_message", onAgentMessage);
      socket.off("approval_required", onApprovalRequired);
      socket.off("budget_update", onBudgetUpdate);
      socket.off("phase_complete", onPhaseComplete);
      socket.off("project_state", onProjectState);
    };
  }, []);

  // Return stable wrapper functions that delegate through socketRef so they
  // work correctly from the very first render (before useEffect fires) as well
  // as after socket is attached.
  return {
    startProject: (idea) => {
      const socket = socketRef.current ?? getSocket();
      socket.emit("start_project", { idea });
    },
    sendMessage: (text) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      const socket = socketRef.current ?? getSocket();
      socket.emit("user_message", { project_id: projectId, text });
    },
    approve: (comment) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      const socket = socketRef.current ?? getSocket();
      socket.emit("approve", { project_id: projectId, comment });
    },
    reject: (comment) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      const socket = socketRef.current ?? getSocket();
      socket.emit("reject", { project_id: projectId, comment });
    },
    modify: (comment) => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      const socket = socketRef.current ?? getSocket();
      socket.emit("modify", { project_id: projectId, comment });
    },
    retry: () => {
      const projectId = useProjectStore.getState().projectId;
      if (!projectId) return;
      const socket = socketRef.current ?? getSocket();
      socket.emit("retry", { project_id: projectId });
    },
    loadProject: (projectId) => {
      const socket = socketRef.current ?? getSocket();
      socket.emit("load_project", { project_id: projectId });
    },
  };
}
