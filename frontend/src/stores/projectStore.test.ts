import { describe, expect, test, beforeEach } from "vitest";

import { useProjectStore } from "./projectStore";
import type { ProjectStateSnapshot } from "../types";

describe("projectStore", () => {
  beforeEach(() => {
    useProjectStore.getState().reset();
  });

  test("reset creates 15 pending agents", () => {
    const { agents } = useProjectStore.getState();
    expect(Object.keys(agents)).toHaveLength(15);
    for (const agent of Object.values(agents)) {
      expect(agent.status).toBe("pending");
    }
  });

  test("addMessage appends to messages", () => {
    useProjectStore.getState().addMessage({
      id: "m1", role: "user", text: "hi", timestamp: 0,
    });
    expect(useProjectStore.getState().messages).toHaveLength(1);
    expect(useProjectStore.getState().messages[0].text).toBe("hi");
  });

  test("updateAgentStatus updates the named agent only", () => {
    useProjectStore.getState().updateAgentStatus("clarifying_pm", "running", "thinking");
    const agents = useProjectStore.getState().agents;
    expect(agents.clarifying_pm.status).toBe("running");
    expect(agents.clarifying_pm.details).toBe("thinking");
    expect(agents.orchestrator.status).toBe("pending");
  });

  test("setApprovalPending / clearApprovalPending", () => {
    useProjectStore.getState().setApprovalPending({
      agent: "product_owner", phase: 3, content: "# PRD",
    });
    expect(useProjectStore.getState().approvalPending?.phase).toBe(3);
    useProjectStore.getState().setApprovalPending(null);
    expect(useProjectStore.getState().approvalPending).toBeNull();
  });

  test("setBudget updates budget", () => {
    useProjectStore.getState().setBudget({ spent: 12.5, limit: 200, threshold: 50 });
    expect(useProjectStore.getState().budget.spent).toBe(12.5);
  });

  test("setPRD stores the markdown", () => {
    useProjectStore.getState().setPRD("# Final PRD\n- Requirement 1");
    expect(useProjectStore.getState().prd).toContain("Final PRD");
  });

  test("hydrateFromState replaces the whole store", () => {
    const snap: ProjectStateSnapshot = {
      project_id: "abc",
      idea: "build a thing",
      messages: [{ id: "m1", role: "user", text: "hi", timestamp: 1 }],
      agents: {
        clarifying_pm: { id: "clarifying_pm", name: "Clarifying PM", status: "complete" },
      },
      approval_pending: null,
      budget: { spent: 1.23, limit: 200, threshold: 50 },
      phase: 3,
      prd: "# PRD",
      status: "running",
    };
    useProjectStore.getState().hydrateFromState(snap);
    expect(useProjectStore.getState().projectId).toBe("abc");
    expect(useProjectStore.getState().messages).toHaveLength(1);
    expect(useProjectStore.getState().agents.clarifying_pm.status).toBe("complete");
  });

  test("setPlanningArtifact stores adr/tasks/design", () => {
    useProjectStore.getState().setPlanningArtifact("adr", "# ADR");
    useProjectStore.getState().setPlanningArtifact("tasks", [{ id: "T1", title: "x", description: "y", owner_agent: "backend", depends_on: [] }]);
    useProjectStore.getState().setPlanningArtifact("design", { tokens: {}, components: [] });
    expect(useProjectStore.getState().adr).toContain("ADR");
    expect(useProjectStore.getState().tasks).toHaveLength(1);
    expect(useProjectStore.getState().designSpec).not.toBeNull();
  });
});
