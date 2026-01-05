### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its Phase 2 patch)

[ ] `config/agents.yaml` enumerates all 15 agents + BudgetGuard with mandatory fields (`module`, `class`, `prompt`, `model`, `enabled`, `authority`, `cost_tier`)  
[ ] `agents/base.py` exposes a single abstract contract and docstring referencing `{{glossary.authority.autonomous}}` vs `{{glossary.authority.approval_required}}`  
[ ] `agents/registry.py` can instantiate any agent defined in YAML and hot-reload changes without restarting Streamlit (verified via test and manual run)  
[ ] Swapping the Frontend Agent for a stub requires editing <=10 LOC (demonstrated via `scripts/swap_agent.py --dry-run frontend agent_stubs.FrontendStub` and documented in README)  
[ ] `prompts/v1/clarifying_pm.jinja` plus 14 placeholder prompts exist to validate file-watcher coverage (content can be TODO-only for non-critical agents)  
[ ] BudgetGuard enforces thresholds at 50/75/85/95/100% exactly as defined in `CoreSystemGlossary.md` (unit test shows actions for each band)  
[ ] Auto-downgrade path logs which agents switched models and persists the decision in a checkpoint/state file  
[ ] Kill-switch path blocks orchestrator invocation until human issues `/approve_budget_override` (documented in README)  
[ ] CI includes new pytest suites and completes <3 minutes locally (`uv run pytest tests/ -k "agent or budget"`)  
[ ] README gains a "Swapping Agents" section describing the workflow (<=5 steps, includes CLI example)  
[ ] Streamlit UI surfaces current budget spend + warnings via BudgetGuard output  
[ ] LangSmith trace shows BudgetGuard invoked before each expensive agent execution
