import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { PlanViewer } from "./PlanViewer";

describe("PlanViewer", () => {
  test("renders ADR, task, and design json", () => {
    render(
      <PlanViewer
        adr={"# ADR\n\nContext here"}
        tasks={[{ id: "T1", title: "Build API", description: "impl", owner_agent: "backend", depends_on: [] }]}
        designSpec={{ tokens: { colorPrimary: "#2563eb" }, components: [] }}
      />,
    );
    const root = screen.getByTestId("plan-viewer");
    expect(root).toBeInTheDocument();
    expect(screen.getByText(/Build API/)).toBeInTheDocument();
    expect(screen.getByText(/backend/)).toBeInTheDocument();
    expect(root.textContent).toContain("colorPrimary");
  });

  test("renders nothing meaningful when all empty", () => {
    const { container } = render(<PlanViewer adr={null} tasks={[]} designSpec={null} />);
    // Should not throw; may render an empty container.
    expect(container).toBeTruthy();
  });
});
