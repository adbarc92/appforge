import { create } from "zustand";

import type {
  AgentState,
  AgentStatus,
  ApprovalRequest,
  BudgetState,
  Message,
  ProjectStateSnapshot,
  Task,
} from "../types";

const AGENT_NAMES: Record<string, string> = {
  orchestrator: "Orchestrator",
  clarifying_pm: "Clarifying PM",
  product_owner: "Product Owner",
  solution_architect: "Solution Architect",
  tech_lead: "Tech Lead",
  uiux_designer: "UI/UX Designer",
  frontend: "Frontend",
  backend: "Backend",
  database: "Database",
  ai_ml: "AI/ML",
  devops: "DevOps",
  security: "Security",
  qa: "QA",
  technical_writer: "Technical Writer",
  delivery_summarizer: "Delivery Summarizer",
};

function initialAgents(): Record<string, AgentState> {
  const out: Record<string, AgentState> = {};
  for (const [id, name] of Object.entries(AGENT_NAMES)) {
    out[id] = { id, name, status: "pending" };
  }
  return out;
}

interface ProjectStore {
  projectId: string | null;
  idea: string;
  messages: Message[];
  agents: Record<string, AgentState>;
  approvalPending: ApprovalRequest | null;
  budget: BudgetState;
  phase: number;
  prd: string | null;
  status: "idle" | "running" | "paused" | "complete" | "failed";
  adr: string | null;
  tasks: Task[];
  designSpec: Record<string, unknown> | null;

  reset: (projectId?: string, idea?: string) => void;
  addMessage: (message: Message) => void;
  updateAgentStatus: (agent: string, status: AgentStatus, details?: string) => void;
  setApprovalPending: (req: ApprovalRequest | null) => void;
  setBudget: (budget: BudgetState) => void;
  setPRD: (prd: string | null) => void;
  setPlanningArtifact: (kind: "adr" | "tasks" | "design", value: unknown) => void;
  hydrateFromState: (snap: ProjectStateSnapshot) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projectId: null,
  idea: "",
  messages: [],
  agents: initialAgents(),
  approvalPending: null,
  budget: { spent: 0, limit: 200, threshold: 0 },
  phase: 0,
  prd: null,
  status: "idle",
  adr: null,
  tasks: [],
  designSpec: null,

  reset: (projectId, idea) =>
    set({
      projectId: projectId ?? null,
      idea: idea ?? "",
      messages: [],
      agents: initialAgents(),
      approvalPending: null,
      budget: { spent: 0, limit: 200, threshold: 0 },
      phase: 0,
      prd: null,
      status: projectId ? "running" : "idle",
      adr: null,
      tasks: [],
      designSpec: null,
    }),

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateAgentStatus: (agent, status, details) =>
    set((s) => ({
      agents: {
        ...s.agents,
        [agent]: { ...s.agents[agent], status, details },
      },
    })),

  setApprovalPending: (req) => set({ approvalPending: req }),

  setBudget: (budget) => set({ budget }),

  setPRD: (prd) => set({ prd }),

  setPlanningArtifact: (kind, value) => {
    if (kind === "adr") {
      set({ adr: value as string });
    } else if (kind === "tasks") {
      set({ tasks: value as Task[] });
    } else {
      set({ designSpec: value as Record<string, unknown> });
    }
  },

  hydrateFromState: (snap) =>
    set({
      projectId: snap.project_id,
      idea: snap.idea,
      messages: snap.messages,
      agents: { ...initialAgents(), ...snap.agents },
      approvalPending: snap.approval_pending,
      budget: snap.budget,
      phase: snap.phase,
      prd: snap.prd,
      status: snap.status,
      adr: snap.adr ?? null,
      tasks: snap.tasks ?? [],
      designSpec: snap.design_spec ?? null,
    }),
}));
