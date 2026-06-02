// Mirrors backend Socket.IO event payload shapes. Manually maintained.

export type AgentStatus =
  | "pending"
  | "running"
  | "complete"
  | "error"
  | "downgraded";

export interface AgentState {
  id: string;
  name: string;
  status: AgentStatus;
  details?: string;
}

export type MessageRole = "user" | "agent" | "system";

export interface Message {
  id: string;
  role: MessageRole;
  agent?: string;
  text: string;
  timestamp: number;
}

export interface BudgetState {
  spent: number;
  limit: number;
  threshold: number; // 0, 50, 75, 85, 95, 100
}

export interface ApprovalRequest {
  agent: string;
  phase: number;
  content: string; // markdown PRD
  alternatives?: string[];
  escalation?: boolean;
}

export interface ProjectStateSnapshot {
  project_id: string;
  idea: string;
  messages: Message[];
  agents: Record<string, AgentState>;
  approval_pending: ApprovalRequest | null;
  budget: BudgetState;
  phase: number;
  prd: string | null;
  status: "running" | "paused" | "complete" | "failed";
}

// Client -> server event payloads
export interface StartProjectPayload { idea: string }
export interface UserMessagePayload { project_id: string; text: string }
export interface ApprovalDecisionPayload { project_id: string; comment?: string }
export interface RetryPayload { project_id: string }
export interface LoadProjectPayload { project_id: string }

// Server -> client event payloads
export interface ProjectCreatedPayload { project_id: string }
export interface AgentStatusPayload { agent: string; status: AgentStatus; details?: string }
export interface AgentMessagePayload { agent: string; text: string }
export interface BudgetUpdatePayload { spent: number; limit: number; threshold: number }
export interface PhaseCompletePayload {
  phase: number;
  summary: string;
  status?: "success" | "failed";
  reason?: string;
}
