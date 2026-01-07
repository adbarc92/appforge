# Phase 10 Brief - Stand-up & Metrics Dashboard

## Purpose
Provide automated daily status summaries and live dashboards showing token usage, budget, velocity, and blocker metrics so humans can monitor progress asynchronously.

## Prerequisites
- Phase 9 checklist: Iteration loop stable.
- Required agents: Delivery Summarizer, BudgetGuard, Orchestrator, Context Curator, optional Metrics agent.
- Required documents: testing strategy, approval protocol, budget rules.

## Scope
Implement metrics aggregation, dashboard UI, and scheduled stand-up summaries. Out of scope: production releases or eco mode support.

## Required Changes
1. `agent_specs/agent-17-delivery-summarizer.md` plus prompt.
2. Metrics collector service aggregating phase duration, token usage, cost, approval wait time, revision count.
3. Streamlit dashboard page with charts/tables.
4. Scheduled job (GitHub Actions or cron) posting daily stand-up summary.
5. Data storage for metrics (`data/metrics/*.json`).
6. Alerting when KPIs exceed thresholds (e.g., approval wait >4h).
7. Tests verifying metrics calculations.
8. Documentation describing dashboard and stand-up process.

## Success Criteria
- [ ] Delivery Summarizer outputs 3-bullet stand-up (yesterday, today, blockers) daily.
- [ ] Metrics dashboard displays live budget spend, velocity, approval wait, revision count.
- [ ] Metrics data persists between restarts and is queryable via API.
- [ ] Alert triggers if approval wait exceeds 4 hours or budget passes warning thresholds.
- [ ] Stand-up job posts to chat or log channel at scheduled time.
- [ ] README includes instructions for accessing dashboard and adjusting schedules.
- [ ] CI covers metrics calculations and API serialization.
- [ ] Design Ledger records adoption of dashboard tooling.
- [ ] BudgetGuard integrates metrics data into projections.

## Human Approval Gate
No formal approval; human simply acknowledges first stand-up summary.

## Dependencies
- Enables better decision-making for Phases 11-14.

## Cost Estimate
- LLM spend: <$5 (mostly summarization).
- Engineering time: 6-8 hours.

## Rollback Plan
1. Keep previous logging scripts intact.
2. If dashboard causes performance issues, disable scheduled job and fall back to manual status updates.
