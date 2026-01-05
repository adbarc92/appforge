### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its Phase 13 patch)

[ ] Optimization agent spec + prompt define experiment workflow and guardrails  
[ ] Experiment runner replays at least three historical tasks per variant  
[ ] Metrics comparison shows quantified improvements (e.g., -20% tokens or -30% duration)  
[ ] Promotion of new prompt/model requires human acknowledgment and Design Ledger entry  
[ ] Regression Agent confirms no Phase 0-12 checklist item regressed after adopting improvement  
[ ] Streamlit UI displays experiment status, deltas, and decisions  
[ ] README documents self-improvement loop and how to add experiments  
[ ] Tests ensure experiment runner deterministic given seed inputs  
[ ] BudgetGuard tracks experiment cost separately from production work
