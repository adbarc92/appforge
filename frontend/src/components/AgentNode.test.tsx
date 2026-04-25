import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { AgentNode } from "./AgentNode";

function wrap(data: any) {
  return <AgentNode data={data} />;
}

describe("AgentNode", () => {
  test("renders pending by default", () => {
    render(wrap({ id: "clarifying_pm", name: "Clarifying PM", status: "pending" }));
    expect(screen.getByText("Clarifying PM")).toBeInTheDocument();
    expect(screen.getByTestId("agent-node")).toHaveAttribute("data-status", "pending");
  });

  test("renders running with details", () => {
    render(wrap({ id: "clarifying_pm", name: "Clarifying PM", status: "running", details: "thinking" }));
    expect(screen.getByTestId("agent-node")).toHaveAttribute("data-status", "running");
    expect(screen.getByText(/thinking/)).toBeInTheDocument();
  });

  test("renders error status", () => {
    render(wrap({ id: "backend", name: "Backend", status: "error", details: "crashed" }));
    expect(screen.getByTestId("agent-node")).toHaveAttribute("data-status", "error");
  });
});
