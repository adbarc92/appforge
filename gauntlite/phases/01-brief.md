### PHASE 1 – Minimal Viable Graph (Core Orchestration Skeleton)

Build the thinnest runnable LangGraph + CrewAI hybrid that executes a blank cycle: user idea → clarification node → end. No real agents yet—use dummies. Ensure parallelism stub (e.g., one branch) and state persistence (SQLite via Mem0). Test with Claude Code CLI integration (add a dummy `claude` call in graph).

### REQUIRED CHANGES
1. Add `/graph.py`: LangGraph StateGraph with TypedDict state (e.g., `AppState = TypedDict("AppState", {"messages": list, "prd": str})`). Nodes: "clarify" (dummy print), "end". Edges: clarify → END. Compile as `app = graph.compile(checkpointer=MemorySaver())`.
2. Add `/orchestrator.py`: Pure supervisor (no LLM)—routes to nodes via LangGraph. Split from future Summarizer.
3. Update `/app.py`: Streamlit button triggers `app.invoke({"messages": ["Dummy idea"]})`; display output.
4. Add `/config/llm.yaml`: Skeleton for Claude 3.5 Sonnet (Anthropic API key placeholder).
5. Add test: `/tests/test_graph.py` with pytest: Run cycle → assert "clarify" executed, no errors.
6. Update `pyproject.toml`: Add `[tool.uv]` for deps; run `uv add langgraph crewai` equivalent.
7. README: Add "Run with Claude Code: claude -p 'Test graph' --json".

### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its patch)

[ ] `uv sync` installs all deps with zero errors  
[ ] `streamlit run app.py` shows UI; button click runs blank cycle (visible in trace/logs)  
[ ] LangSmith trace (via env var) logs the full cycle without crashes  
[ ] Dummy "clarify" node executes (check output: e.g., "Clarifying: Dummy idea")  
[ ] State persists (run twice → second recalls first's "messages")  
[ ] `pytest tests/` passes (100% coverage on graph invoke)  
[ ] Claude Code dummy call succeeds (e.g., `claude -p "Dummy"` outputs JSON)  
[ ] No lint errors: `uv run ruff check .` and `uv run black --check .` pass  
[ ] GitHub Actions CI runs green on commit (now with pytest)  

Only when ALL boxes can be truthfully ticked is Phase 1 considered complete.