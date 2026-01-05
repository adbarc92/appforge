### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its patch)

[ ] GitHub repository exists and is clonable (provide URL)  
[ ] Running `git clone <url> && cd devteam-ai-2025` works  
[ ] `pip install -e .` completes with zero errors  
[ ] `streamlit run app.py` launches a browser page showing "DevTeam.AI" title and an input box (no crash)  
[ ] `ruff check .` returns no errors  
[ ] `black --check .` passes  
[ ] `.github/workflows/ci.yml` exists and GitHub Actions shows green check within 2 minutes of commit  
[ ] `config/agents.yaml` lists all 15 final agents (Orchestrator, BudgetGuard, etc.)  
[ ] `prompts/v1/clarifying_pm.jinja` exists and is ≥300 words with clear system prompt  
[ ] `README.md` contains full vision and local run instructions