### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its Phase 8 patch)

[ ] Deploy scripts provision preview infrastructure automatically on commit/tag  
[ ] Frontend and backend preview URLs display in chat with health indicators  
[ ] Post-deploy checks (Lighthouse >=70, API smoke tests) run automatically and report status  
[ ] Secrets stored securely; repo only holds `.env.example`  
[ ] DevOps agent can redeploy or teardown via `/deploy preview`  
[ ] Deployment logs archived in `logs/deploy/preview-{timestamp}.txt`  
[ ] BudgetGuard records deployment spend and warns if monthly allocation exceeded  
[ ] README documents preview deployment workflow, env vars, and rollback commands  
[ ] Tests simulate deployment success/failure paths  
[ ] CI gating ensures preview pipeline definitions lint/validate successfully
