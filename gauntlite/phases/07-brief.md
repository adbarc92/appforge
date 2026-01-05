# Phase 7 Brief - Cross-Cutting Agents Round 1

## Purpose
Integrate Security, QA, Technical Writer, and Regression agents to enforce quality bars (tests, coverage, docs, security scans) on the Phase 6 application.

## Prerequisites
- Phase 6 checklist: Complete and approved.
- Required agents: Security, QA, Technical Writer, Regression, BudgetGuard, Orchestrator.
- Required documents: `docs/testing-strategy.md`, ADRs, API contract, design ledger entries.

## Scope
Add automated test coverage (>=80%), OWASP scanning, documentation, and regression validation before new phases begin. Out of scope: production deployment or human iteration loop (Phase 9).

## Required Changes
1. Agent specs and prompts for Security, QA, Technical Writer, Regression.
2. `tests/security/` harness running OWASP/ZAP or equivalent with 5-min timeout.
3. Coverage tooling and enforcement script (fail if <80%).
4. Regression Agent script re-running Phase 6 checklist automatically.
5. Documentation generator producing README sections plus API docs.
6. Security findings tracker stored in `docs/security/report-{date}.md`.
7. CI updates to include security + coverage jobs.
8. Streamlit UI card summarizing quality status.
9. Status report template for daily summaries.

## Success Criteria
- [ ] Security agent spec + prompt enforce glossary `quality.secure` requirements.
- [ ] Automated security scan completes <5 minutes and logs results.
- [ ] QA suite reports >=80% coverage with breakdown per module.
- [ ] Regression Agent replays Phase 6 checklist and blocks Phase 7 completion if any item fails.
- [ ] Technical Writer produces updated README + API docs reflecting current endpoints.
- [ ] Security findings categorized (critical/high/medium/low) with remediation plan.
- [ ] CI fails if coverage <80% or security scan reports high/critical issues.
- [ ] Streamlit dashboard shows latest coverage %, scan status, doc status.
- [ ] BudgetGuard logs additional spend and remains within forecast.
- [ ] Design Ledger includes entry summarizing cross-cutting completion.

## Human Approval Gate
Optional. Human reviews consolidated QA/Security report; approval required only if outstanding medium issues deferred.

## Dependencies
- Blocks Phase 8 deployment; release cannot continue without green quality bar.

## Cost Estimate
- LLM spend: $12-$18 (documentation + report generation).
- Engineering time: 8-10 hours.

## Rollback Plan
1. If security scan uncovers critical issues, Regression Agent triggers rollback to Phase 6 to fix root cause.
