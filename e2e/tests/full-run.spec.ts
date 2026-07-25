import { test, expect } from "@playwright/test";

// Drives the whole six-phase DAG (config/phases.yaml) through the browser:
// clarify -> [gate] -> design -> [gate] -> code -> test -> deploy -> iterate.
// Both gates are approved from the UI; the run then finishes on its own and the
// poller emits a terminal phase_complete with the summary "run done".
test("approve both gates -> all six phases run to completion", async ({ page }) => {
  test.setTimeout(120_000); // full pipeline: 13 mock tasks across 4 worker processes

  await page.goto("/");
  await page.fill('input[name="idea"]', "Build me a todo app");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(page).toHaveURL(/\/project\/[0-9a-f]{32}$/);

  // --- clarify gate ---
  await expect(page.getByText("Approval needed")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByRole("heading", { name: /^Mock PRD$/ })).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).click();

  // Approving opens the design phase, whose three agents (solution_architect,
  // tech_lead, uiux_designer) have no intra-phase dependencies and so are
  // claimed in parallel by separate worker processes.
  await expect(page.getByText(/Phase 4 success: design complete/)).toBeVisible({
    timeout: 45_000,
  });

  // --- design (plan) gate ---
  await page.getByRole("button", { name: "Approve" }).click();

  // The remaining phases carry gate: none, so they run unattended to the end.
  await expect(page.getByText(/Phase 10 success: run done/)).toBeVisible({
    timeout: 60_000,
  });
});
