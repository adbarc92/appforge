import { act, renderHook } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

// Mock socket.io-client before importing the hook.
const listeners: Record<string, ((...args: unknown[]) => void)[]> = {};
const mockSocket = {
  on: vi.fn((event: string, cb: (...args: unknown[]) => void) => {
    listeners[event] = listeners[event] ?? [];
    listeners[event].push(cb);
  }),
  off: vi.fn(),
  emit: vi.fn(),
  disconnect: vi.fn(),
  connected: true,
};
vi.mock("socket.io-client", () => ({
  io: vi.fn(() => mockSocket),
}));

import { useSocket } from "./useSocket";
import { useProjectStore } from "../stores/projectStore";

describe("useSocket", () => {
  beforeEach(() => {
    useProjectStore.getState().reset();
    mockSocket.emit.mockClear();
  });

  test("emits start_project with idea", () => {
    const { result } = renderHook(() => useSocket());
    act(() => { result.current.startProject("todo app"); });
    expect(mockSocket.emit).toHaveBeenCalledWith("start_project", { idea: "todo app" });
  });

  test("project_created event resets store with new id", () => {
    renderHook(() => useSocket());
    act(() => {
      for (const cb of listeners.project_created ?? []) {
        cb({ project_id: "proj-xyz" });
      }
    });
    expect(useProjectStore.getState().projectId).toBe("proj-xyz");
  });

  test("agent_status event updates the agent", () => {
    renderHook(() => useSocket());
    act(() => {
      for (const cb of listeners.agent_status ?? []) {
        cb({ agent: "clarifying_pm", status: "running", details: "thinking" });
      }
    });
    expect(useProjectStore.getState().agents.clarifying_pm.status).toBe("running");
  });

  test("approval_required sets approvalPending", () => {
    renderHook(() => useSocket());
    act(() => {
      for (const cb of listeners.approval_required ?? []) {
        cb({ agent: "product_owner", phase: 3, content: "# PRD" });
      }
    });
    expect(useProjectStore.getState().approvalPending?.phase).toBe(3);
    expect(useProjectStore.getState().prd).toBe("# PRD");
  });

  test("phase_complete clears approvalPending and prd", () => {
    renderHook(() => useSocket());
    useProjectStore.getState().setApprovalPending({
      agent: "clarifying_pm", phase: 3, content: "# PRD",
    });
    useProjectStore.getState().setPRD("# PRD");
    act(() => {
      for (const cb of listeners.phase_complete ?? []) {
        cb({ phase: 3, summary: "PRD approved", status: "success" });
      }
    });
    expect(useProjectStore.getState().approvalPending).toBeNull();
    expect(useProjectStore.getState().prd).toBeNull();
  });
});
