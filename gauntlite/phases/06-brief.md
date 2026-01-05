# Phase 6 Brief - Specialist Agents Round 1 (Todo MVC)

## Purpose
Demonstrate end-to-end delivery by having Frontend, Backend, Database, and DevOps agents build a fully functional Todo application that adheres to PRD-derived requirements, using outputs from Phase 4 planning.

## Prerequisites
- Phase 5 checklist: Complete with persistence enabled.
- Required agents: Frontend, Backend, Database, DevOps, QA (smoke), Context Curator, BudgetGuard.
- Required documents: ADR-001, design JSON, task backlog, persistence docs.

## Scope
Implement the foundational application (API, database schema, UI) defined by the parallel planning sprint. Include migrations, API docs, and minimal tests. Out of scope: advanced security hardening (Phase 7) or preview deployments (Phase 8).

## Required Changes
1. `services/scaffolder.py`: Generate project structure per ADR.
2. Backend implementation (Fastify/Express or as decided), including routes for CRUD tasks.
3. Database migrations (Prisma/SQL) plus seed data.
4. Frontend React components built from design JSON (Tailwind/Ant).
5. Shared API contract in `docs/api/todo.yml`.
6. DevOps scripts for local run (docker-compose or uvicorn stack).
7. QA smoke tests covering basic CRUD and validation.
8. CI pipeline executing backend/frontend tests.
9. README updates with local development instructions and API reference.
10. Streamlit preview embed or screenshot for demo.

## Success Criteria
- [ ] Backend exposes CRUD endpoints matching API contract with JSON schema validation.
- [ ] Database migrations apply cleanly and seed data loads without manual edits.
- [ ] Frontend renders design-accurate UI with task list, filters, and create/edit forms.
- [ ] Shared TypeScript types or OpenAPI definitions ensure contract sync.
- [ ] DevOps script (`make dev` or equivalent) spins up full stack locally.
- [ ] QA smoke test suite passes and covers create/read/update/delete flows.
- [ ] Context Curator logs implementation decisions back to Design Ledger.
- [ ] BudgetGuard records per-agent spend and stays within projected range.
- [ ] Streamlit UI can launch Todo app inside iframe or provide clickable preview.
- [ ] README contains step-by-step instructions for running frontend, backend, and tests.
- [ ] CI remains green within 8 minutes, including lint/tests.

## Human Approval Gate
Yes. Human reviews working Todo app demo, code links, and QA report before Phase 7.

## Dependencies
- Enables Phase 7 cross-cutting enhancements and baseline for preview deployment.
- Blocks downstream phases until approved.

## Cost Estimate
- LLM spend: $30-$40 (multiple specialist agents).
- Engineering time: 12-16 hours.

## Rollback Plan
1. Tag repo prior to scaffolding.
2. Use checkpoint restore if build fails; Regression Agent re-validates Phase 5 artifacts before retry.
