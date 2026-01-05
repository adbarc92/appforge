# Phase 9 Brief - Full Human Iteration Loop

## Purpose
Support rapid change requests by enabling `/modify` commands, auto-regression, redeployments, and `/escalate` handling within 15-minute turnaround windows.

## Prerequisites
- Phase 8 checklist: Preview deployment operational.
- Required agents: Frontend, Backend, QA, DevOps, Regression, Delivery Summarizer, Orchestrator, BudgetGuard.
- Required documents: Approval protocol, testing strategy, deployment scripts.

## Scope
Implement workflow for capturing feedback, creating tasks, applying changes, validating, and redeploying automatically. Out of scope: production release (Phase 12) or self-improvement loops (Phase 13).

## Required Changes
1. `/modify` command parser that converts user feedback into structured tasks.
2. Orchestrator routine that spins up relevant agents per request.
3. Regression suite automation triggered after each change.
4. Deployment pipeline configured for quick redeploys (<=15 min).
5. Delivery Summarizer agent spec/prompt and status output.
6. Logging improvements for `/escalate` events and resolution steps.
7. Streamlit UI timeline showing request -> work -> deployment states.
8. Tests covering modify/escalate flows and regression gating.
9. Documentation for human iteration workflow.

## Success Criteria
- [ ] `/modify` command captures description, priority, and acceptance criteria.
- [ ] Orchestrator assigns tasks to appropriate agents automatically based on change scope.
- [ ] Each iteration triggers regression tests and preview redeploy without manual steps.
- [ ] Average turnaround from `/modify` to redeploy <=15 minutes in dry run.
- [ ] `/escalate` pauses current work, switches to strongest model, and records ledger entry.
- [ ] Delivery Summarizer posts iteration summary (what changed, tests, cost).
- [ ] Streamlit timeline reflects real-time status for each change request.
- [ ] Regression Agent blocks deployment if any prior phase checklist item regresses.
- [ ] README documents change-request workflow with example commands.
- [ ] CI suite includes tests for modify/escalate parsing and regression triggers.

## Human Approval Gate
Human must approve at least two completed change requests before proceeding.

## Dependencies
- Enables Phase 10 reporting and later production handoff.

## Cost Estimate
- LLM spend: $15-$20 depending on iteration count.
- Engineering time: 8-12 hours.

## Rollback Plan
1. Maintain `rollback/phase9.sh` to revert to last stable preview.
2. On repeated failures, regress to Phase 8 baseline and disable `/modify` temporarily.
