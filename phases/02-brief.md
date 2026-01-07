# Phase 2 Brief - Agent Framework + BudgetGuard

## Purpose
Establish a universal agent interface with hot-swappable configuration and activate BudgetGuard so every subsequent phase can invoke specialized agents safely. By the end of this phase, the system must be able to (a) replace any agent implementation via a single config edit (<10 LOC) and (b) enforce budget thresholds automatically before expensive work runs.

## Prerequisites
- Phase 0 checklist: **Complete** (repo, CI, prompts, README in place).
- Phase 1 checklist: **Complete** (LangGraph skeleton, Mem0/SQLite persistence, basic Streamlit trigger).
- Documents available: `CoreDesignDocument.md`, `Roadmap.md`, `CoreSystemGlossary.md`, `Phase-3-PRD-Rubric-v1.md`, `PlanOfAction.md`.
- Inputs handed off: Phase 1 run logs (for regression) and updated `config/llm.yaml`.

## Scope
In scope:
- Define a typed agent contract (Pydantic model + base class) and central registry that resolves configured agents at runtime.
- Implement `config/agents.yaml` with all 15 production agents plus BudgetGuard metadata (model tier, autonomy flags, prompt path).
- Add prompt hot-reload plumbing (watcher or timestamp check) so swapping prompts does not require code deploys.
- Implement BudgetGuard agent (code + config) that monitors spend, enforces warning/kill thresholds, and can downgrade models via configuration.
- Provide CLI or script ergonomics for swapping an agent in <10 lines.
- Extend tests/CI to cover registry loading, hot reload, and BudgetGuard decision logic.

Explicitly out of scope:
- Building the real specialist prompts (covered in later phases).
- Implementing Clarifying PM logic (Phase 3).
- Adding new external storage (stay on SQLite/Mem0).

## Required Changes
1. `agents/base.py`: Define `AgentConfig` (Pydantic) + `BaseAgent` ABC with `plan()`, `execute()`, `validate()` hooks and shared telemetry hooks.
2. `agents/registry.py`: Load `config/agents.yaml`, instantiate agents, expose `swap_agent(name, import_path)` API.
3. `config/agents.yaml`: List all 15 agents + BudgetGuard with fields (`module`, `class`, `prompt`, `model`, `enabled`, `authority`, `cost_tier`).
4. `scripts/swap_agent.py`: CLI accepting `--name` and `--path` that edits YAML + triggers reload; include dry-run flag.
5. `prompts/v1/*.jinja`: Add stubs for each agent (placeholder content referencing Glossary) to validate hot reload.
6. `agents/budget_guard.py`: BudgetGuard implementation that reads spend from telemetry (mocked) and issues actions per thresholds (log, notify, downgrade, halt).
7. `config/budget.yaml`: Store budget limit, warning thresholds, downgrade rules (mirrors `budget-enforcement-rules.md` once published).
8. `tests/test_agent_registry.py`: Ensure swapping agents requires <=10 LOC change (use fixtures), registry reloads without restart, invalid config raises helpful errors.
9. `tests/test_budget_guard.py`: Cover warning, auto-downgrade, and kill-switch flows using fake spend data.
10. CI (`.github/workflows/ci.yml`): Add pytest matrix for registry + budget tests; ensure lint/format tasks still run.

## Success Criteria
- [ ] `config/agents.yaml` enumerates all 15 agents + BudgetGuard with mandatory fields (`module`, `class`, `prompt`, `model`, `enabled`, `authority`, `cost_tier`) and stays in lockstep with `docs/Roadmap.md` agent inventory.
- [ ] `agents/base.py` exposes a single abstract contract and docstring referencing `{{glossary.authority.autonomous}}` vs `{{glossary.authority.approval_required}}`.
- [ ] `agents/registry.py` can instantiate any agent defined in YAML and hot-reload changes without restarting Streamlit (verified via test and manual run).
- [ ] Swapping the Frontend Agent for a stub requires editing <=10 LOC (demonstrated via `scripts/swap_agent.py --dry-run frontend agent_stubs.FrontendStub` and documented in README).
- [ ] `prompts/v1/clarifying_pm.jinja` plus 14 placeholder prompts exist to validate file-watcher coverage (content can be TODO-only for non-critical agents).
- [ ] BudgetGuard enforces thresholds at 50/75/85/95/100% exactly as defined in `CoreSystemGlossary.md` and `docs/budget-enforcement-rules.md` (log-only, notify, auto-downgrade, require_ack, hard_stop; unit test shows actions for each band).
- [ ] Auto-downgrade path logs which agents switched models and persists the decision in a checkpoint/state file.
- [ ] Kill-switch path blocks orchestrator invocation until human issues `/approve_budget_override` (documented in README).
- [ ] CI includes new pytest suites and completes <3 minutes locally (`uv run pytest tests/ -k "agent or budget"`) and is enforced via workflow job `ci.yml::phase-02-registry-budget`.
- [ ] README gains a "Swapping Agents" section describing the workflow (<=5 steps, includes CLI example).
- [ ] Streamlit UI surfaces current budget spend + warnings via BudgetGuard output.
- [ ] LangSmith trace shows BudgetGuard invoked before each expensive agent execution.
- [ ] Human sign-off mirrors `checklists/02-checklist.md` verbatim to keep criteria synchronized.

## Human Approval Gate
No gating approval required to exit Phase 2. However, if BudgetGuard kill-switch triggers during verification, log output and request human sign-off before overriding.

## Dependencies
- Blocks: Phase 3 Clarifying PM (needs hot-swappable prompts + BudgetGuard guardrails).
- Consumes: Roadmap phases, Glossary definitions, pending `budget-enforcement-rules.md` (should be drafted in parallel but not blocking initial implementation).
- Enables: Agent spec documents (they can plug into registry once specs exist).

## Cost Estimate
- Expected LLM cost: **$8–$12** (mainly for generating placeholder prompts/tests).
- Engineering time: **6–8 hours** (agent base + registry + BudgetGuard + tests).

## Rollback Plan
1. Tag repo at `phase-1-complete` before starting.
2. If registry or BudgetGuard causes instability, revert to tag, disable BudgetGuard hook, and re-run Phase 1 validation suite.
3. Reapply changes incrementally: base class → registry → YAML → BudgetGuard.
4. Document lessons learned in `Status-YYYY_MM_DD.md` before retrying.

Locked 2025-12-17 (Codex pass)
