import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test, beforeEach, vi } from "vitest";

const emit = vi.fn();
const mockSocket = { on: vi.fn(), off: vi.fn(), emit, disconnect: vi.fn(), connected: true };
vi.mock("socket.io-client", () => ({ io: vi.fn(() => mockSocket) }));

import { ChatInterface } from "./ChatInterface";
import { useProjectStore } from "../stores/projectStore";

describe("ChatInterface", () => {
  beforeEach(() => {
    useProjectStore.getState().reset("proj-1");
    emit.mockClear();
  });

  test("renders messages from the store", () => {
    useProjectStore.getState().addMessage({
      id: "m1", role: "user", text: "Hello", timestamp: 0,
    });
    render(<ChatInterface />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  test("submitting input emits user_message", () => {
    render(<ChatInterface />);
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "build a todo app" } });
    fireEvent.submit(input.closest("form")!);
    expect(emit).toHaveBeenCalledWith("user_message", {
      project_id: "proj-1",
      text: "build a todo app",
    });
  });

  test("shows approval card when approvalPending is set", () => {
    useProjectStore.getState().setApprovalPending({
      agent: "product_owner", phase: 3, content: "# PRD",
    });
    render(<ChatInterface />);
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /modify/i })).toBeInTheDocument();
  });

  test("clicking Approve emits approve event", () => {
    useProjectStore.getState().setApprovalPending({
      agent: "product_owner", phase: 3, content: "# PRD",
    });
    render(<ChatInterface />);
    fireEvent.click(screen.getByRole("button", { name: /approve/i }));
    expect(emit).toHaveBeenCalledWith("approve", {
      project_id: "proj-1",
      comment: undefined,
    });
  });

  test("slash command /approve in input emits approve", () => {
    useProjectStore.getState().setApprovalPending({
      agent: "product_owner", phase: 3, content: "# PRD",
    });
    render(<ChatInterface />);
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "/approve" } });
    fireEvent.submit(input.closest("form")!);
    expect(emit).toHaveBeenCalledWith("approve", {
      project_id: "proj-1",
      comment: undefined,
    });
  });
});
