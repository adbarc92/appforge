# Testing Strategy v1.0

## Purpose
Define a consistent validation approach for every AppForge phase, spanning unit, integration, regression, and manual thought-experiment tests. Testing artifacts live alongside code so checklist verification stays under 3 minutes.

## Test Categories
1. **Unit Tests**  
   - Validate individual agents, helpers, and CLI utilities.  
   - Use pytest with fixtures that stub LLM calls via recorded responses.  
   - Minimum: new modules ship with at least one happy-path and one failure-path test.

2. **Integration Tests**  
   - Exercise LangGraph flows, BudgetGuard hooks, and external tool adapters.  
   - Use Mem0/SQLite checkpoints to simulate multi-turn runs.  
   - Required once a phase introduces more than one cooperating agent.

3. **Regression Tests**  
   - Re-run prior phase checklists automatically before advancing.  
   - Implemented via Regression Agent (Phase 7) plus `tests/regression/phase_{n}.py`.

4. **End-to-End / Scenario Tests**  
   - Trigger full Streamlit session, feed scripted commands, ensure Orchestrator finishes without manual intervention.  
   - Required from Phase 6 onward when building real apps.

5. **Thought-Experiment Tests**  
   - Manual dry runs that walk a backlog idea through current capabilities.  
   - Document insights in `Status-YYYY_MM_DD.md` and convert gaps into backlog items.

## Phase-to-Test Matrix
| Phase | Primary Focus | Mandatory Tests |
|-------|---------------|-----------------|
| 0 | Repo + CI | `pytest --maxfail=1`, lint pipeline smoke |
| 1 | LangGraph skeleton | Graph invocation unit test, Streamlit smoke |
| 2 | Agent registry + BudgetGuard | Registry swap test, budget thresholds test |
| 3 | Clarifying loop | Prompt rendering snapshot, PRD schema validation |
| 4 | Parallel planning | Multi-agent integration test, ADR schema validation |
| 5 | Memory & persistence | Checkpoint restore test, design ledger serialization |
| 6 | Specialist build | Backend/frontend unit suites, API contract tests |
| 7 | Cross-cutting agents | Security scan harness, coverage gate (>=80%) |
| 8 | Preview deploy | Deployment script dry run (mock), URL health check |
| 9 | Iteration loop | Change-request rehearsal test, rollback simulation |
| 10 | Metrics dashboard | Metrics API test, dashboard rendering snapshot |
| 11 | Open-source mode | Local LLM smoke test, dependency substitution test |
| 12 | Production ship | Release script test, credential packaging validation |
| 13 | Self-improvement | DSPy optimization test, before/after benchmark |
| 14 | Template release | Repo template export test, onboarding script test |

## Tooling Standards
- **pytest** with `-q --maxfail=1`.
- **coverage.py** HTML + terminal reports, target >=80% from Phase 7 onward.
- **ruff** and **black** enforced in CI for every commit.
- Snapshot tests store artifacts under `tests/__snapshots__` and must be reviewed on failure.

## Automation Hooks
- GitHub Actions pipeline stages: `lint`, `test-unit`, `test-integration`, `report`.
- Phase-specific jobs toggled via matrix keyed by `APPFORGE_PHASE`.
- BudgetGuard cancels long-running suites if spend threshold already exceeded (Phase 2).

## Failure Handling
- Unit failure: triage immediately, block merge.
- Integration failure: log in Status doc, assess if rollback required.
- Regression failure: Regression Agent auto-triggers `/rollback` recommendation.
- Manual rehearsal failure: document assumption gaps, schedule follow-up design session.
