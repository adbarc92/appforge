# Phase 13 Brief - Self-Improvement Loop

## Purpose
Continuously optimize speed and quality by capturing telemetry, training DSPy or similar optimizers, and applying prompt/agent improvements that measurably reduce cost or time.

## Prerequisites
- Phase 12 checklist: Production ship signed off.
- Required agents: Delivery Summarizer, BudgetGuard, Optimization agent (new), Orchestrator, Core specialists.
- Required documents: Metrics dashboard, approval protocol, testing strategy.

## Scope
Instrument experiments comparing current prompts/workflows with optimized variants, collect metrics, and adopt improvements only when statistically significant. Out of scope: new feature development (Phase 9 handles change requests).

## Required Changes
1. `agent_specs/agent-18-regression.md` (if not already) and Optimization agent spec.
2. Experiment runner that replays historical tasks with new prompts/models.
3. Metrics logging for experiment outcomes (speed, tokens, success rate).
4. Process for promoting winning variants and updating prompts repository.
5. Documentation describing experiment design and approval steps.
6. Tests verifying experiment runner reproducibility.
7. Streamlit UI module showing experiment queue and results.

## Success Criteria
- [ ] Optimization agent spec + prompt define experiment workflow and guardrails.
- [ ] Experiment runner replays at least three historical tasks per variant.
- [ ] Metrics comparison shows quantified improvements (e.g., -20% tokens or -30% duration).
- [ ] Promotion of new prompt/model requires human acknowledgment and Design Ledger entry.
- [ ] Regression Agent confirms no Phase 0-12 checklist item regressed after adopting improvement.
- [ ] Streamlit UI displays experiment status, deltas, and decisions.
- [ ] README documents self-improvement loop and how to add experiments.
- [ ] Tests ensure experiment runner deterministic given seed inputs.
- [ ] BudgetGuard tracks experiment cost separately from production work.

## Human Approval Gate
Yes. Human approves each promoted improvement with `/approve Experiment {id}`.

## Dependencies
- Prepares system for template release by ensuring mature processes.

## Cost Estimate
- LLM spend: $10-$15 depending on experiment volume.
- Engineering time: 6-8 hours.

## Rollback Plan
1. If experiment introduces regression, use Regression Agent to revert prompts/configs to previous version and document incident.
