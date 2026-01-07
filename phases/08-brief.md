# Phase 8 Brief - Instant Preview Deployment

## Purpose
Automate creation of live preview environments (Vercel/Netlify for frontend, Railway/Fly.io for backend) so humans can validate features via shared URLs directly from chat.

## Prerequisites
- Phase 7 checklist: Quality gates green.
- Required agents: DevOps, Security (for credentials), Orchestrator, BudgetGuard.
- Required documents: Deployment credentials, infrastructure ADR, testing strategy.

## Scope
Build deployment scripts, secrets management, and chat integration that surfaces preview URLs with health checks. Out of scope: production cutover (Phase 12) or iteration workflows (Phase 9).

## Required Changes
1. `deploy/preview_frontend.yaml` and `deploy/preview_backend.yaml` workflows.
2. Secrets loading via `.env.example` + Vault/parameter store instructions.
3. DevOps agent spec/prompt updates covering preview deploy tasks.
4. Automatic Lighthouse + API smoke checks post-deploy.
5. Streamlit UI card showing latest preview URLs, status, and log excerpts.
6. `tests/deploy/test_preview_pipeline.py` mocking providers.
7. Budget tracking for deployment resources (log cost estimates).
8. Documentation for onboarding new environments.
9. Rollback script to tear down previews cleanly.

## Success Criteria
- [ ] Deploy scripts provision preview infrastructure automatically on commit/tag.
- [ ] Frontend and backend preview URLs display in chat with health indicators.
- [ ] Post-deploy checks (Lighthouse >=70, API smoke tests) run automatically and report status.
- [ ] Secrets stored securely; repo only holds `.env.example`.
- [ ] DevOps agent can redeploy or teardown via chat command `/deploy preview`.
- [ ] Deployment logs archived in `logs/deploy/preview-{timestamp}.txt`.
- [ ] BudgetGuard records deployment spend and warns if monthly allocation exceeded.
- [ ] README documents preview deployment workflow, env vars, and rollback commands.
- [ ] Tests simulate deployment success/failure paths.
- [ ] CI gating ensures preview pipeline definitions lint/validate successfully.

## Human Approval Gate
No formal approval, but human must acknowledge first live preview link before Phase 9.

## Dependencies
- Enables Phase 9 change-request loop by giving human a URL to inspect.

## Cost Estimate
- LLM spend: $6-$10 (mainly DevOps agent).
- Infrastructure cost: minimal preview usage (<$20).
- Engineering time: 6-8 hours.

## Rollback Plan
1. Maintain script `deploy/teardown_preview.py` to clean resources.
2. If deployment fails, disable preview stage and revert to Phase 7 baseline.
