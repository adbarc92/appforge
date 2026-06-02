import { test, expect, type Page } from "@playwright/test";

// Submit an idea and answer the three mock clarifying questions, leaving the
// page parked on the PRD approval gate. Copied from phase3.spec.ts (a small
// helper is cheaper to duplicate than to share across spec files).
async function driveToApprovalGate(page: Page) {
  await page.goto("/");
  await page.fill('input[name="idea"]', "Build me a todo app");
  await page.getByRole("button", { name: "Start" }).click();

  for (const n of [1, 2, 3]) {
    await expect(
      page.getByText(new RegExp(`Clarifying question #${n}`)),
    ).toBeVisible();
    await page.getByPlaceholder(/Describe your idea/).fill(`answer ${n}`);
    await page.locator('button[type="submit"]', { hasText: "Send" }).click();
  }

  await expect(page.getByText("Approval needed")).toBeVisible();
  await expect(page.getByRole("heading", { name: /^Mock PRD$/ })).toBeVisible();
}

// With ENABLE_PHASE4=true the suite runs the full pipeline: PRD approval →
// planning fan-out (ADR / tasks / design) → plan approval gate → phase 4 done.
test("phase 4 happy path: approve PRD -> plan renders -> approve plan -> done", async ({
  page,
}) => {
  await driveToApprovalGate(page);

  // Approve the PRD. Backend emits "Phase 3 success: PRD approved" then begins
  // the planning sprint.
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText(/Phase 3 success/)).toBeVisible();

  // Planning artifacts render via PlanViewer. The ADR "# ADR" markdown renders
  // as a heading; "Build the backend" is one of the mock task titles. Wait for
  // these BEFORE the plan card, since the approval card briefly clears on the
  // phase-3 phase_complete before re-opening for the plan gate.
  await expect(page.getByTestId("plan-viewer")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: /^ADR$/ })).toBeVisible();
  await expect(page.getByText(/Build the backend/)).toBeVisible();

  // The new planning approval gate (kind == "plan") opens.
  await expect(page.getByText("Approval needed")).toBeVisible({ timeout: 15_000 });

  // Approve the plan gate. Summarizer emits "Phase 4 success: Planning approved".
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText(/Phase 4 success/)).toBeVisible();
  await expect(page.getByText(/Planning approved/)).toBeVisible();

  // After the final phase_complete the approval card is gone.
  await expect(page.getByText("Approval needed")).toBeHidden();
});
