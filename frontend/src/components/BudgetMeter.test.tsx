import { render, screen } from "@testing-library/react";
import { describe, expect, test, beforeEach } from "vitest";

import { BudgetMeter } from "./BudgetMeter";
import { useProjectStore } from "../stores/projectStore";

describe("BudgetMeter", () => {
  beforeEach(() => useProjectStore.getState().reset());

  test("renders current spend and limit", () => {
    useProjectStore.getState().setBudget({ spent: 12.34, limit: 200, threshold: 0 });
    render(<BudgetMeter />);
    expect(screen.getByText(/\$12\.34/)).toBeInTheDocument();
    expect(screen.getByText(/\$200/)).toBeInTheDocument();
  });

  test("shows threshold class for 85", () => {
    useProjectStore.getState().setBudget({ spent: 170, limit: 200, threshold: 85 });
    render(<BudgetMeter />);
    const meter = screen.getByTestId("budget-meter");
    expect(meter).toHaveAttribute("data-threshold", "85");
  });
});
