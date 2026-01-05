### PHASE 0 – Repository Bootstrap & Minimal Viable Skeleton

Implement the absolute minimum foundation required for all future phases.  
Everything must be 100% local-first (no Redis, no external services yet).

### REQUIRED FILES & EXACT CONTENTS

1. GitHub repository (public or private) named `devteam-ai-2025` (or your preferred name)
2. Folder structure exactly as:
├── agents/                  # empty for now
├── config/
│   └── agents.yaml          # list all 15 final agents with placeholder LLM config
├── prompts/
│   └── v1/
│       └── clarifying_pm.jinja   # strong initial clarification prompt (≥300 words)
├── phases/                  # this brief will live here
├── app.py                   # minimal Streamlit UI with title "DevTeam.AI" and a text input box
├── requirements.txt         # pinned versions (see list below)
├── pyproject.toml           # black + ruff configuration
├── .gitignore
└── .github/workflows/ci.yml # runs ruff + black --check + pytest (even if no tests yet)
text3. `requirements.txt` must contain at minimum (exact versions as of Dec 2025):
langgraph==1.0.15
crewai==0.5.10
langchain==0.3.4
langchain-openai
langchain-anthropic
streamlit==1.38.0
pydantic==2.9.2
mem0ai==0.1.18
python-dotenv
jinja2
pyyaml
gitpython
rich
text4. `README.md` must contain:
- Project title "DevTeam.AI – Autonomous Development Team"
- One-paragraph vision
- Local run instructions (pip install -e . → streamlit run app.py)
- Link to Core Design Document v1.1 (paste full text or link)

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

Only when ALL boxes can be truthfully ticked is Phase 0 considered complete.