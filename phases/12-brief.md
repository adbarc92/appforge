# Phase 12 Brief - Production Ship + Handover

## Purpose
Promote the application from preview to production, deliver credentials and documentation, and capture final approval for release.

## Prerequisites
- Phase 11 checklist: Eco mode validated.
- Required agents: DevOps, Security, QA, Technical Writer, Delivery Summarizer, BudgetGuard.
- Required documents: Approved PRD, ADRs, deployment scripts, approval protocol.

## Scope
Execute production deployment, run final smoke/regression tests, package admin credentials, and produce cost/report summaries. Out of scope: post-release iteration loops (handled later).

## Required Changes
1. Production deployment workflows and infrastructure definitions.
2. Secrets rotation procedure and credential delivery pack.
3. Final QA regression covering all acceptance criteria.
4. Documentation updates (Runbook, README, API docs).
5. Handover packet summarizing architecture, endpoints, costs, and support plan.
6. BudgetGuard final report vs. initial estimate.
7. Streamlit UI celebratory banner + release metadata.
8. Design Ledger closure entry referencing approval.
9. Tests verifying production config and smoke tests.

## Success Criteria
- [ ] Production environment created and reachable with HTTPS and monitoring.
- [ ] Final regression suite passes with documented evidence.
- [ ] Security agent signs off on zero high/critical findings after final scan.
- [ ] Deployment runbook stored in `docs/runbooks/production.md`.
- [ ] Credential package (admin login, API keys) encrypted and shared securely.
- [ ] Cost report compares actual vs. planned spend with explanation of variances.
- [ ] Delivery Summarizer posts release announcement with links.
- [ ] README updated with production URL and support instructions.
- [ ] BudgetGuard resets counters and archives spend log.
- [ ] Human `/approve` recorded, transitioning to `state.complete`.

## Human Approval Gate
Mandatory. Human reviews release packet, production URL, and QA evidence before `/approve`.

## Dependencies
- Blocks Phase 13 self-improvement; cannot iterate until production stable.

## Cost Estimate
- LLM spend: $6-$10.
- Infrastructure: dependent on target environment (document actuals).

## Rollback Plan
1. Keep preview environment active as rollback target.
2. If production issues arise, execute `/rollback` to preview snapshot and reopen Phase 9 for fixes.
