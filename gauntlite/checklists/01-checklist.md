### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its Phase 1 patch)

[ ] `uv sync` installs all deps with zero errors  
[ ] `streamlit run app.py` shows UI; button click runs blank cycle (visible in trace/logs)  
[ ] LangSmith trace (via env var) logs the full cycle without crashes  
[ ] Dummy "clarify" node executes (check output: e.g., "Clarifying: Dummy idea")  
[ ] State persists (run twice + second recalls first's "messages")  
[ ] `pytest tests/` passes (100% coverage on graph invoke)  
[ ] Claude Code dummy call succeeds (e.g., `claude -p "Dummy"` outputs JSON)  
[ ] No lint errors: `uv run ruff check .` and `uv run black --check .` pass  
[ ] GitHub Actions CI runs green on commit (now with pytest)
