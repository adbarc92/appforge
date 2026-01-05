### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its Phase 3 patch)

[ ] `agent_specs/agent-01-clarifying-pm.md` exists and matches DocumentDesignGuide template  
[ ] Clarifying PM asks exactly one focus area per turn (roles, features, NFRs, tech, scope, gaps)  
[ ] Agent enforces max six question turns before generating PRD  
[ ] Generated PRD conforms to schema and includes success metrics, MVP scope, and appendix  
[ ] Rubric self-score includes pass/fail per criterion plus rationale for any misses  
[ ] Red flags trigger automatic follow-up prompts  
[ ] Conversation log saved to `logs/clarification/{timestamp}.jsonl`  
[ ] BudgetGuard invoked before each Clarifying PM call and logs estimated spend  
[ ] Streamlit UI displays PRD preview and download link  
[ ] README documents Clarification Loop workflow and sample transcript  
[ ] CI adds `pytest tests/test_clarifying_pm.py` and passes locally in under 90 seconds
