# Alignment + Phase 3 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit UI with a FastAPI + Socket.IO backend and React + Vite frontend, wire the Clarifying PM agent to real Anthropic Claude Sonnet 4.6 calls, add SQLite persistence, and deliver the Phase 3 roadmap milestone (vague idea → clean PRD + acceptance criteria in ≤6 questions with approval gate and session resume).

**Architecture:** Five vertical slices. Each slice ends in runnable software. Python modules move under `backend/`; root-level `config/` and `prompts/` stay as data directories. One feature branch (`feat/alignment-phase3-mvp`) with frequent commits; one PR per slice is recommended to keep review scope manageable.

**Tech Stack:** Python 3.11+ · FastAPI · python-socketio · LangGraph 1.0 · LangChain · `langchain-anthropic` · SQLite (via `SqliteSaver`) · Pydantic · Jinja2 · pytest · React 18 · TypeScript · Vite · Tailwind · `@xyflow/react` · Zustand · `socket.io-client` · Vitest · React Testing Library.

**Spec:** See `docs/superpowers/specs/2026-04-21-alignment-phase3-mvp-design.md` for the full design including data flow, error handling, and component boundaries. This plan implements that spec.

---

## Preconditions and conventions

- Working directory throughout: repo root `D:/MajorProjects/HARNESSES/appforge` (or wherever cloned). All paths in this plan are relative to that.
- Python commands go through `uv run` to use the locked environment. Never `python` directly.
- Frontend commands run from `frontend/` (`cd frontend && ...`) and use `npm`.
- Every task ends with a commit. Commit messages follow Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`, `refactor:`).
- Tests run from repo root: `uv run pytest tests/ -q`.
- Coverage runs: `uv run pytest tests/ --cov=backend --cov-report=term`.
- Per user's global `CLAUDE.md`: do **not** include `Co-Authored-By` lines or "Generated with Claude Code" footers in commit messages. Do not push to `main`; use a PR to merge the feature branch.

---

## Slice 0: Prep

### Task 0.1: Create feature branch and verify baseline

**Files:** None modified in this task.

- [ ] **Step 1: Verify clean working tree**

Run: `git status`
Expected: `nothing to commit, working tree clean`

- [ ] **Step 2: Create feature branch**

Run: `git checkout -b feat/alignment-phase3-mvp`
Expected: `Switched to a new branch 'feat/alignment-phase3-mvp'`

- [ ] **Step 3: Sync dependencies and run full test suite as baseline**

Run: `uv sync && uv run -- python -m pytest tests/ -q`
Expected: `79 passed` in the output. If anything else, stop and diagnose before continuing — this plan assumes the baseline is green.

- [ ] **Step 4: Record baseline test count**

Capture the exact `N passed` count from step 3 — this is the floor for the rest of the plan. Every subsequent test run should report this number or higher.

---

## Slice 1: Infrastructure swap

**Outcome of Slice 1:** FastAPI + Socket.IO backend runs on `:8000` with a health endpoint and an empty Socket.IO connection handler. Streamlit is deleted. Python modules live under `backend/`. All prior tests still pass, now importing from `backend.*`.

### Task 1.1: Create `backend/` package skeleton

**Files:**
- Create: `backend/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/e2e/__init__.py`

- [ ] **Step 1: Create package directories with empty `__init__.py` files**

Run:
```bash
mkdir -p backend tests/unit tests/integration tests/e2e
touch backend/__init__.py tests/unit/__init__.py tests/integration/__init__.py tests/e2e/__init__.py
```

- [ ] **Step 2: Verify the directories exist**

Run: `ls -la backend/ tests/`
Expected output includes `backend/__init__.py` and the three new `tests/` subdirectories each with `__init__.py`.

- [ ] **Step 3: Commit**

```bash
git add backend/ tests/unit/ tests/integration/ tests/e2e/
git commit -m "chore: scaffold backend package and test subdirectories"
```

---

### Task 1.2: Move `agents/` under `backend/`

**Files:**
- Move: `agents/*.py` → `backend/agents/*.py`
- Modify: every import line inside moved files that references sibling modules.

- [ ] **Step 1: Move the directory**

Run: `git mv agents backend/agents`
Expected: git tracks the rename.

- [ ] **Step 2: Inspect imports that need updating**

Run: `uv run -- python -c "import ast, pathlib; print('\n'.join(str(p) for p in pathlib.Path('backend/agents').rglob('*.py')))"` then open each file and look for imports of the form `from agents.X` or `import agents.X`.

Grep-based alternative: use the Grep tool for pattern `^(from|import) agents(\.|$| )` across `backend/agents/`.

- [ ] **Step 3: Rewrite in-package imports to absolute form**

For every moved file, update:
- `from agents.X import Y` → `from backend.agents.X import Y`
- `import agents.X` → `import backend.agents.X` (or `from backend.agents import X`)

Leave any `from .X import Y` (relative imports within the package) alone — those still work after the move.

- [ ] **Step 4: Commit the move (imports fixed in the next task)**

```bash
git add backend/agents/
git commit -m "refactor: move agents package under backend/"
```

---

### Task 1.3: Move `orchestrator.py` and `graph.py` under `backend/`

**Files:**
- Move: `orchestrator.py` → `backend/orchestrator.py`
- Move: `graph.py` → `backend/graph.py`
- Modify: import lines in both moved files.

- [ ] **Step 1: Move the files**

Run:
```bash
git mv orchestrator.py backend/orchestrator.py
git mv graph.py backend/graph.py
```

- [ ] **Step 2: Rewrite imports in the moved files**

Inside `backend/orchestrator.py` and `backend/graph.py`, replace any `from agents.X` / `import agents.X` / `from graph import ...` / `from orchestrator import ...` references with `from backend.agents.X` / `from backend.graph` / `from backend.orchestrator`.

- [ ] **Step 3: Commit**

```bash
git add backend/orchestrator.py backend/graph.py
git commit -m "refactor: move orchestrator.py and graph.py under backend/"
```

---

### Task 1.4: Move existing tests into `tests/unit/` and update imports

**Files:**
- Move: `tests/test_agent_registry.py` → `tests/unit/test_agent_registry.py`
- Move: `tests/test_budget_guard.py` → `tests/unit/test_budget_guard.py`
- Move: `tests/test_graph.py` → `tests/unit/test_graph.py`
- Move: `tests/test_placeholder.py` → `tests/unit/test_placeholder.py`
- Modify: every import in the moved test files.

- [ ] **Step 1: Move test files**

Run:
```bash
git mv tests/test_agent_registry.py tests/unit/test_agent_registry.py
git mv tests/test_budget_guard.py tests/unit/test_budget_guard.py
git mv tests/test_graph.py tests/unit/test_graph.py
git mv tests/test_placeholder.py tests/unit/test_placeholder.py
```

- [ ] **Step 2: Update imports in each test file**

Rewrite:
- `from agents.X import Y` → `from backend.agents.X import Y`
- `from orchestrator import X` → `from backend.orchestrator import X`
- `from graph import X` → `from backend.graph import X`

- [ ] **Step 3: Run the full test suite**

Run: `uv run -- python -m pytest tests/ -q`
Expected: same count as baseline (79 passed). If anything fails, fix the imports in that specific test or in the module it imports before moving on.

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "refactor: move existing tests under tests/unit and update imports"
```

---

### Task 1.5: Update `pyproject.toml` dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove unused / replaced dependencies**

Edit `pyproject.toml`'s `dependencies` list to remove these four lines:
```
"streamlit>=1.38.0",
"crewai>=0.86.0",
"mem0ai>=0.1.0",
"gitpython>=3.1.0",
```

- [ ] **Step 2: Add new backend dependencies**

Add these lines to the same `dependencies` list (alphabetical if the file is alphabetical, otherwise group-appropriate):
```
"aiosqlite>=0.20.0",
"fastapi>=0.115.0",
"python-socketio>=5.11.0",
"uvicorn[standard]>=0.32.0",
"langgraph-checkpoint-sqlite>=2.0.0",
```

Leave `langgraph`, `langchain`, `langchain-anthropic`, `langchain-openai`, `langchain-community`, `pydantic`, `python-dotenv`, `jinja2`, `pyyaml`, `rich`, `structlog` untouched — still needed.

- [ ] **Step 3: Add dev dependencies for API testing**

In the `[project.optional-dependencies]` `dev` list (or wherever pytest extras live), add:
```
"pytest-asyncio>=0.24.0",
"httpx>=0.27.0",
```

- [ ] **Step 4: Re-lock and sync**

Run: `uv lock && uv sync`
Expected: `Resolved N packages` where N has changed; no errors.

- [ ] **Step 5: Re-run tests to prove nothing broke**

Run: `uv run -- python -m pytest tests/ -q`
Expected: still 79 passed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: drop streamlit/crewai/mem0ai/gitpython; add fastapi, socketio, aiosqlite"
```

---

### Task 1.6: Create `backend/config.py`

**Files:**
- Create: `backend/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_config.py`:

```python
"""Tests for backend.config — environment and YAML loading."""
import os
from pathlib import Path

import pytest

from backend.config import Config


def test_config_defaults_when_env_missing(monkeypatch, tmp_path):
    for var in ("ANTHROPIC_API_KEY", "MOCK_AGENTS", "DEBUG", "BUDGET_LIMIT",
                "ANTHROPIC_MODEL", "SQLITE_PATH", "MAX_CLARIFYING_QUESTIONS", "LOG_LEVEL"):
        monkeypatch.delenv(var, raising=False)
    cfg = Config.load()
    assert cfg.mock_agents is True
    assert cfg.debug is False
    assert cfg.budget_limit == 200.0
    assert cfg.anthropic_model == "claude-sonnet-4-6"
    assert cfg.sqlite_path.endswith("checkpoints.db")
    assert cfg.max_clarifying_questions == 6
    assert cfg.log_level == "INFO"


def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("MOCK_AGENTS", "false")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("BUDGET_LIMIT", "50.0")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("MAX_CLARIFYING_QUESTIONS", "4")
    cfg = Config.load()
    assert cfg.anthropic_api_key == "sk-test"
    assert cfg.mock_agents is False
    assert cfg.debug is True
    assert cfg.budget_limit == 50.0
    assert cfg.anthropic_model == "claude-haiku-4-5"
    assert cfg.max_clarifying_questions == 4


def test_config_loads_yaml_files():
    cfg = Config.load()
    # agents.yaml / budget.yaml / llm.yaml live at repo root config/
    assert "clarifying_pm" in cfg.agents_yaml
    assert "thresholds" in cfg.budget_yaml
    assert cfg.llm_yaml  # non-empty
```

- [ ] **Step 2: Run the test — it must fail**

Run: `uv run -- python -m pytest tests/unit/test_config.py -q`
Expected: `ModuleNotFoundError: No module named 'backend.config'` (all tests fail at import).

- [ ] **Step 3: Implement `backend/config.py`**

Create `backend/config.py`:

```python
"""Centralized configuration for the backend.

Reads environment variables (loaded from .env by main.py at startup) and the
root-level config/*.yaml files. Exposes a single Config dataclass used by the
rest of the backend.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class Config:
    # Env-driven
    anthropic_api_key: str | None
    mock_agents: bool
    debug: bool
    log_level: str
    budget_limit: float
    anthropic_model: str
    sqlite_path: str
    max_clarifying_questions: int
    # YAML-driven (eagerly loaded for simplicity; files are <10KB total)
    agents_yaml: dict[str, Any] = field(default_factory=dict)
    budget_yaml: dict[str, Any] = field(default_factory=dict)
    llm_yaml: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Config":
        default_sqlite = str(REPO_ROOT / "data" / "checkpoints.db")
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            mock_agents=_env_bool("MOCK_AGENTS", True),
            debug=_env_bool("DEBUG", False),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            budget_limit=_env_float("BUDGET_LIMIT", 200.0),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            sqlite_path=os.getenv("SQLITE_PATH", default_sqlite),
            max_clarifying_questions=_env_int("MAX_CLARIFYING_QUESTIONS", 6),
            agents_yaml=_load_yaml(CONFIG_DIR / "agents.yaml"),
            budget_yaml=_load_yaml(CONFIG_DIR / "budget.yaml"),
            llm_yaml=_load_yaml(CONFIG_DIR / "llm.yaml"),
        )
```

- [ ] **Step 4: Run the test — it must pass**

Run: `uv run -- python -m pytest tests/unit/test_config.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/config.py tests/unit/test_config.py
git commit -m "feat: add backend.config with env + YAML loading"
```

---

### Task 1.7: Create `backend/main.py` with FastAPI + health endpoint

**Files:**
- Create: `backend/main.py`
- Create: `tests/integration/test_health.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_health.py`:

```python
"""Test that FastAPI starts and /health returns 200 with expected payload."""
from fastapi.testclient import TestClient

from backend.main import app


def test_health_ok():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == {"status": "ok"}
```

- [ ] **Step 2: Run the test — it must fail**

Run: `uv run -- python -m pytest tests/integration/test_health.py -q`
Expected: `ModuleNotFoundError: No module named 'backend.main'`.

- [ ] **Step 3: Implement `backend/main.py` with just the HTTP app**

Create `backend/main.py`:

```python
"""FastAPI + Socket.IO application entry point.

HTTP endpoints and Socket.IO event handlers are both mounted on one ASGI app
served by uvicorn on :8000. For local development, run:

    uv run -- python -m backend.main

which delegates to uvicorn.run(...) below.
"""
from __future__ import annotations

from fastapi import FastAPI

from backend.config import Config

app = FastAPI(title="DevTeam.AI backend", version="0.3.0")
config = Config.load()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=config.debug)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test — it must pass**

Run: `uv run -- python -m pytest tests/integration/test_health.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Manually verify the dev server boots**

Run (in a separate terminal, or with `run_in_background`): `uv run -- python -m backend.main`
Open: `http://127.0.0.1:8000/health` in a browser.
Expected: `{"status":"ok"}`.
Kill the process after verifying.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/integration/test_health.py
git commit -m "feat: add FastAPI app with /health endpoint"
```

---

### Task 1.8: Mount Socket.IO on `backend/main.py`

**Files:**
- Modify: `backend/main.py`
- Create: `tests/integration/test_socketio_connect.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_socketio_connect.py`:

```python
"""Verify a Socket.IO client can connect to the mounted ASGI app."""
import asyncio

import pytest
import socketio
import uvicorn
from contextlib import asynccontextmanager

from backend.main import asgi_app


@pytest.mark.asyncio
async def test_socketio_client_can_connect():
    server_config = uvicorn.Config(asgi_app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(server_config)
    task = asyncio.create_task(server.serve())
    # Wait for the server to be ready
    while not server.started:
        await asyncio.sleep(0.02)

    client = socketio.AsyncClient()
    try:
        await client.connect("http://127.0.0.1:8765", socketio_path="/socket.io")
        assert client.connected is True
    finally:
        await client.disconnect()
        server.should_exit = True
        await task
```

- [ ] **Step 2: Run the test — it must fail**

Run: `uv run -- python -m pytest tests/integration/test_socketio_connect.py -q`
Expected: `ImportError: cannot import name 'asgi_app' from 'backend.main'`.

- [ ] **Step 3: Mount Socket.IO in `backend/main.py`**

Replace `backend/main.py` contents with:

```python
"""FastAPI + Socket.IO application entry point.

HTTP endpoints and Socket.IO event handlers are both mounted on one ASGI app
served by uvicorn on :8000. For local development, run:

    uv run -- python -m backend.main
"""
from __future__ import annotations

import socketio
from fastapi import FastAPI

from backend.config import Config

config = Config.load()

app = FastAPI(title="DevTeam.AI backend", version="0.3.0")

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    logger=config.debug,
    engineio_logger=config.debug,
)

# Combined ASGI app: FastAPI handles HTTP, Socket.IO handles /socket.io/*
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> None:
    # No-op for now; per-project rooms are joined later via start_project / load_project
    pass


@sio.event
async def disconnect(sid: str) -> None:
    pass


def main() -> None:
    import uvicorn
    uvicorn.run("backend.main:asgi_app", host="127.0.0.1", port=8000, reload=config.debug)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update the health test to use `asgi_app`'s underlying FastAPI**

Open `tests/integration/test_health.py`. The import `from backend.main import app` still works — `app` is still exported. No change needed. Re-run: `uv run -- python -m pytest tests/integration/test_health.py -q`. Expected: `1 passed`.

- [ ] **Step 5: Run the Socket.IO test — it must pass**

Run: `uv run -- python -m pytest tests/integration/test_socketio_connect.py -q`
Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/integration/test_socketio_connect.py
git commit -m "feat: mount python-socketio AsyncServer on FastAPI ASGI app"
```

---

### Task 1.9: Delete Streamlit and stale docs, update README

**Files:**
- Delete: `app.py`
- Delete: `SetupInstructions.md`
- Modify: `README.md`

- [ ] **Step 1: Delete Streamlit entry point and stale setup doc**

Run:
```bash
git rm app.py
git rm SetupInstructions.md
```

- [ ] **Step 2: Update `README.md` run commands**

Open `README.md` and find any section describing how to run the app. Replace the Streamlit run instructions with:

```markdown
## Running locally (development)

Backend (FastAPI + Socket.IO on `:8000`):

```bash
uv sync
uv run -- python -m backend.main
```

Frontend (Vite dev server on `:5173`, added in Slice 2):

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173/`.
```

If the README has a "Requirements" or "Setup" section referencing `streamlit run app.py`, remove those lines. Leave the project overview and roadmap references intact.

- [ ] **Step 3: Verify full test suite still passes**

Run: `uv run -- python -m pytest tests/ -q`
Expected: at least `82 passed` (79 baseline + 3 new — config + health + socketio).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove app.py and SetupInstructions.md; update README"
```

---

### Task 1.10: Slice 1 checkpoint — confirm backend runs

**Files:** None modified.

- [ ] **Step 1: Start the server in the background**

Run (background): `uv run -- python -m backend.main`

- [ ] **Step 2: Curl the health endpoint**

Run: `curl -s http://127.0.0.1:8000/health`
Expected: `{"status":"ok"}`.

- [ ] **Step 3: Kill the server**

- [ ] **Step 4: Summary and (optional) PR for Slice 1**

At this point the backend is a clean FastAPI + Socket.IO app with a health endpoint, all prior tests still pass, Streamlit is gone. If following the per-slice-PR convention: push the branch and open a PR titled "Slice 1: infrastructure swap" for review before continuing.

---

## Slice 2: React shell

**Outcome of Slice 2:** `frontend/` is a Vite + React + TypeScript app that compiles, runs on `:5173`, connects to the backend Socket.IO server, and renders an empty workspace with 15 agent nodes in `pending` state. No agent logic yet.

### Task 2.1: Scaffold Vite React-TS app in `frontend/`

**Files:**
- Create: everything under `frontend/` as generated by `create-vite`.

- [ ] **Step 1: Scaffold the project**

Run:
```bash
npm create vite@latest frontend -- --template react-ts
```

When prompted, accept defaults. This creates `frontend/` with a starter React+TS+Vite app.

- [ ] **Step 2: Install base deps**

Run:
```bash
cd frontend && npm install && cd ..
```

- [ ] **Step 3: Verify it builds and dev-runs**

Run: `cd frontend && npm run build && cd ..`
Expected: builds successfully, `frontend/dist/` produced.

Run (background, manual verify): `cd frontend && npm run dev`
Open: `http://localhost:5173/`. Expected: the Vite + React starter page.
Kill the dev server.

- [ ] **Step 4: Commit the scaffold**

```bash
git add frontend/
git commit -m "chore: scaffold Vite React-TS app under frontend/"
```

---

### Task 2.2: Install application dependencies and configure Tailwind

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/tailwind.config.js`, `frontend/postcss.config.js`
- Modify: `frontend/src/index.css`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Install runtime deps**

Run:
```bash
cd frontend
npm install @xyflow/react zustand socket.io-client react-markdown lucide-react react-router-dom
npm install -D tailwindcss@^3 postcss autoprefixer vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
cd ..
```

(Tailwind v3 is pinned because v4's config story is different and the design docs expect v3-style `tailwind.config.js`.)

- [ ] **Step 2: Init Tailwind**

Run:
```bash
cd frontend && npx tailwindcss init -p && cd ..
```

Expected: `frontend/tailwind.config.js` and `frontend/postcss.config.js` created.

- [ ] **Step 3: Configure Tailwind content paths**

Open `frontend/tailwind.config.js` and set:

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
```

- [ ] **Step 4: Add Tailwind directives to CSS**

Replace the contents of `frontend/src/index.css` with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: Configure Vite proxy for Socket.IO and enable Vitest**

Replace `frontend/vite.config.ts` contents with:

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/socket.io": {
        target: "http://127.0.0.1:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [ ] **Step 6: Create Vitest setup file**

Create `frontend/src/test-setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 7: Add test script to `package.json`**

In `frontend/package.json`, add to the `scripts` block:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 8: Verify build and tests scaffold**

Run: `cd frontend && npm run build && cd ..`
Expected: still builds.

Run: `cd frontend && npm test && cd ..`
Expected: `No test files found` or similar benign exit — Vitest is wired; we haven't written tests yet.

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "chore: install frontend runtime deps, configure Tailwind and Vitest"
```

---

### Task 2.3: Define shared types in `frontend/src/types/index.ts`

**Files:**
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: Create the types file**

Create `frontend/src/types/index.ts`:

```ts
// Mirrors backend Socket.IO event payload shapes. Manually maintained.

export type AgentStatus =
  | "pending"
  | "running"
  | "complete"
  | "error"
  | "downgraded";

export interface AgentState {
  id: string;
  name: string;
  status: AgentStatus;
  details?: string;
}

export type MessageRole = "user" | "agent" | "system";

export interface Message {
  id: string;
  role: MessageRole;
  agent?: string;
  text: string;
  timestamp: number;
}

export interface BudgetState {
  spent: number;
  limit: number;
  threshold: number; // 0, 50, 75, 85, 95, 100
}

export interface ApprovalRequest {
  agent: string;
  phase: number;
  content: string; // markdown PRD
  alternatives?: string[];
  escalation?: boolean;
}

export interface ProjectStateSnapshot {
  project_id: string;
  idea: string;
  messages: Message[];
  agents: Record<string, AgentState>;
  approval_pending: ApprovalRequest | null;
  budget: BudgetState;
  phase: number;
  prd: string | null;
  status: "running" | "paused" | "complete" | "failed";
}

// Client -> server event payloads
export interface StartProjectPayload { idea: string }
export interface UserMessagePayload { project_id: string; text: string }
export interface ApprovalDecisionPayload { project_id: string; comment?: string }
export interface RetryPayload { project_id: string }
export interface LoadProjectPayload { project_id: string }

// Server -> client event payloads
export interface ProjectCreatedPayload { project_id: string }
export interface AgentStatusPayload { agent: string; status: AgentStatus; details?: string }
export interface AgentMessagePayload { agent: string; text: string }
export interface BudgetUpdatePayload { spent: number; limit: number; threshold: number }
export interface PhaseCompletePayload {
  phase: number;
  summary: string;
  status?: "success" | "failed";
  reason?: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/
git commit -m "feat(frontend): define shared Socket.IO event and state types"
```

---

### Task 2.4: Create Zustand `projectStore`

**Files:**
- Create: `frontend/src/stores/projectStore.ts`
- Create: `frontend/src/stores/projectStore.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/stores/projectStore.test.ts`:

```ts
import { describe, expect, test, beforeEach } from "vitest";

import { useProjectStore } from "./projectStore";
import type { ProjectStateSnapshot } from "../types";

describe("projectStore", () => {
  beforeEach(() => {
    useProjectStore.getState().reset();
  });

  test("reset creates 15 pending agents", () => {
    const { agents } = useProjectStore.getState();
    expect(Object.keys(agents)).toHaveLength(15);
    for (const agent of Object.values(agents)) {
      expect(agent.status).toBe("pending");
    }
  });

  test("addMessage appends to messages", () => {
    useProjectStore.getState().addMessage({
      id: "m1", role: "user", text: "hi", timestamp: 0,
    });
    expect(useProjectStore.getState().messages).toHaveLength(1);
    expect(useProjectStore.getState().messages[0].text).toBe("hi");
  });

  test("updateAgentStatus updates the named agent only", () => {
    useProjectStore.getState().updateAgentStatus("clarifying_pm", "running", "thinking");
    const agents = useProjectStore.getState().agents;
    expect(agents.clarifying_pm.status).toBe("running");
    expect(agents.clarifying_pm.details).toBe("thinking");
    expect(agents.orchestrator.status).toBe("pending");
  });

  test("setApprovalPending / clearApprovalPending", () => {
    useProjectStore.getState().setApprovalPending({
      agent: "product_owner", phase: 3, content: "# PRD",
    });
    expect(useProjectStore.getState().approvalPending?.phase).toBe(3);
    useProjectStore.getState().setApprovalPending(null);
    expect(useProjectStore.getState().approvalPending).toBeNull();
  });

  test("setBudget updates budget", () => {
    useProjectStore.getState().setBudget({ spent: 12.5, limit: 200, threshold: 50 });
    expect(useProjectStore.getState().budget.spent).toBe(12.5);
  });

  test("setPRD stores the markdown", () => {
    useProjectStore.getState().setPRD("# Final PRD\n- Requirement 1");
    expect(useProjectStore.getState().prd).toContain("Final PRD");
  });

  test("hydrateFromState replaces the whole store", () => {
    const snap: ProjectStateSnapshot = {
      project_id: "abc",
      idea: "build a thing",
      messages: [{ id: "m1", role: "user", text: "hi", timestamp: 1 }],
      agents: {
        clarifying_pm: { id: "clarifying_pm", name: "Clarifying PM", status: "complete" },
      },
      approval_pending: null,
      budget: { spent: 1.23, limit: 200, threshold: 50 },
      phase: 3,
      prd: "# PRD",
      status: "running",
    };
    useProjectStore.getState().hydrateFromState(snap);
    expect(useProjectStore.getState().projectId).toBe("abc");
    expect(useProjectStore.getState().messages).toHaveLength(1);
    expect(useProjectStore.getState().agents.clarifying_pm.status).toBe("complete");
  });
});
```

- [ ] **Step 2: Run the tests — they must fail**

Run: `cd frontend && npm test -- projectStore && cd ..`
Expected: import error or module-not-found.

- [ ] **Step 3: Implement the store**

Create `frontend/src/stores/projectStore.ts`:

```ts
import { create } from "zustand";

import type {
  AgentState,
  AgentStatus,
  ApprovalRequest,
  BudgetState,
  Message,
  ProjectStateSnapshot,
} from "../types";

const AGENT_NAMES: Record<string, string> = {
  orchestrator: "Orchestrator",
  clarifying_pm: "Clarifying PM",
  product_owner: "Product Owner",
  solution_architect: "Solution Architect",
  tech_lead: "Tech Lead",
  uiux_designer: "UI/UX Designer",
  frontend: "Frontend",
  backend: "Backend",
  database: "Database",
  ai_ml: "AI/ML",
  devops: "DevOps",
  security: "Security",
  qa: "QA",
  technical_writer: "Technical Writer",
  delivery_summarizer: "Delivery Summarizer",
};

function initialAgents(): Record<string, AgentState> {
  const out: Record<string, AgentState> = {};
  for (const [id, name] of Object.entries(AGENT_NAMES)) {
    out[id] = { id, name, status: "pending" };
  }
  return out;
}

interface ProjectStore {
  projectId: string | null;
  idea: string;
  messages: Message[];
  agents: Record<string, AgentState>;
  approvalPending: ApprovalRequest | null;
  budget: BudgetState;
  phase: number;
  prd: string | null;
  status: "idle" | "running" | "paused" | "complete" | "failed";

  reset: (projectId?: string, idea?: string) => void;
  addMessage: (message: Message) => void;
  updateAgentStatus: (agent: string, status: AgentStatus, details?: string) => void;
  setApprovalPending: (req: ApprovalRequest | null) => void;
  setBudget: (budget: BudgetState) => void;
  setPRD: (prd: string | null) => void;
  hydrateFromState: (snap: ProjectStateSnapshot) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projectId: null,
  idea: "",
  messages: [],
  agents: initialAgents(),
  approvalPending: null,
  budget: { spent: 0, limit: 200, threshold: 0 },
  phase: 0,
  prd: null,
  status: "idle",

  reset: (projectId, idea) =>
    set({
      projectId: projectId ?? null,
      idea: idea ?? "",
      messages: [],
      agents: initialAgents(),
      approvalPending: null,
      budget: { spent: 0, limit: 200, threshold: 0 },
      phase: 0,
      prd: null,
      status: projectId ? "running" : "idle",
    }),

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateAgentStatus: (agent, status, details) =>
    set((s) => ({
      agents: {
        ...s.agents,
        [agent]: { ...s.agents[agent], status, details },
      },
    })),

  setApprovalPending: (req) => set({ approvalPending: req }),

  setBudget: (budget) => set({ budget }),

  setPRD: (prd) => set({ prd }),

  hydrateFromState: (snap) =>
    set({
      projectId: snap.project_id,
      idea: snap.idea,
      messages: snap.messages,
      agents: { ...initialAgents(), ...snap.agents },
      approvalPending: snap.approval_pending,
      budget: snap.budget,
      phase: snap.phase,
      prd: snap.prd,
      status: snap.status,
    }),
}));
```

- [ ] **Step 4: Run the tests — they must pass**

Run: `cd frontend && npm test -- projectStore && cd ..`
Expected: `7 passed` (or similar; all tests green).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/
git commit -m "feat(frontend): add projectStore with reset, agent status, approval, hydration"
```

---

### Task 2.5: Create `useSocket` hook

**Files:**
- Create: `frontend/src/hooks/useSocket.ts`
- Create: `frontend/src/hooks/useSocket.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/hooks/useSocket.test.tsx`:

```tsx
import { act, renderHook } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

// Mock socket.io-client before importing the hook.
const listeners: Record<string, Function[]> = {};
const mockSocket = {
  on: vi.fn((event: string, cb: Function) => {
    listeners[event] = listeners[event] ?? [];
    listeners[event].push(cb);
  }),
  emit: vi.fn(),
  disconnect: vi.fn(),
  connected: true,
};
vi.mock("socket.io-client", () => ({
  io: vi.fn(() => mockSocket),
}));

import { useSocket } from "./useSocket";
import { useProjectStore } from "../stores/projectStore";

describe("useSocket", () => {
  beforeEach(() => {
    useProjectStore.getState().reset();
    for (const key of Object.keys(listeners)) delete listeners[key];
    mockSocket.emit.mockClear();
  });

  test("emits start_project with idea", () => {
    const { result } = renderHook(() => useSocket());
    act(() => { result.current.startProject("todo app"); });
    expect(mockSocket.emit).toHaveBeenCalledWith("start_project", { idea: "todo app" });
  });

  test("project_created event resets store with new id", () => {
    renderHook(() => useSocket());
    act(() => {
      for (const cb of listeners.project_created ?? []) {
        cb({ project_id: "proj-xyz" });
      }
    });
    expect(useProjectStore.getState().projectId).toBe("proj-xyz");
  });

  test("agent_status event updates the agent", () => {
    renderHook(() => useSocket());
    act(() => {
      for (const cb of listeners.agent_status ?? []) {
        cb({ agent: "clarifying_pm", status: "running", details: "thinking" });
      }
    });
    expect(useProjectStore.getState().agents.clarifying_pm.status).toBe("running");
  });

  test("approval_required sets approvalPending", () => {
    renderHook(() => useSocket());
    act(() => {
      for (const cb of listeners.approval_required ?? []) {
        cb({ agent: "product_owner", phase: 3, content: "# PRD" });
      }
    });
    expect(useProjectStore.getState().approvalPending?.phase).toBe(3);
    expect(useProjectStore.getState().prd).toBe("# PRD");
  });
});
```

- [ ] **Step 2: Run the tests — they must fail**

Run: `cd frontend && npm test -- useSocket && cd ..`
Expected: module-not-found for `./useSocket`.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/useSocket.ts`:

```ts
import { useEffect, useRef } from "react";
import { io, type Socket } from "socket.io-client";

import { useProjectStore } from "../stores/projectStore";
import type {
  AgentMessagePayload,
  AgentStatusPayload,
  ApprovalRequest,
  BudgetUpdatePayload,
  PhaseCompletePayload,
  ProjectCreatedPayload,
  ProjectStateSnapshot,
} from "../types";

let socketSingleton: Socket | null = null;

function getSocket(): Socket {
  if (!socketSingleton) {
    socketSingleton = io("/", { path: "/socket.io", autoConnect: true });
  }
  return socketSingleton;
}

export interface UseSocketApi {
  startProject: (idea: string) => void;
  sendMessage: (text: string) => void;
  approve: (comment?: string) => void;
  reject: (comment?: string) => void;
  modify: (comment: string) => void;
  retry: () => void;
  loadProject: (projectId: string) => void;
}

export function useSocket(): UseSocketApi {
  const apiRef = useRef<UseSocketApi | null>(null);

  useEffect(() => {
    const socket = getSocket();
    const store = useProjectStore.getState;

    const onProjectCreated = (p: ProjectCreatedPayload) => {
      useProjectStore.getState().reset(p.project_id, store().idea);
    };
    const onAgentStatus = (p: AgentStatusPayload) => {
      useProjectStore.getState().updateAgentStatus(p.agent, p.status, p.details);
    };
    const onAgentMessage = (p: AgentMessagePayload) => {
      useProjectStore.getState().addMessage({
        id: `${Date.now()}-${Math.random()}`,
        role: "agent",
        agent: p.agent,
        text: p.text,
        timestamp: Date.now(),
      });
    };
    const onApprovalRequired = (p: ApprovalRequest) => {
      useProjectStore.getState().setApprovalPending(p);
      useProjectStore.getState().setPRD(p.content);
    };
    const onBudgetUpdate = (p: BudgetUpdatePayload) => {
      useProjectStore.getState().setBudget(p);
    };
    const onPhaseComplete = (p: PhaseCompletePayload) => {
      useProjectStore.getState().addMessage({
        id: `${Date.now()}-phase`,
        role: "system",
        text: `Phase ${p.phase} ${p.status ?? "complete"}: ${p.summary}`,
        timestamp: Date.now(),
      });
    };
    const onProjectState = (p: ProjectStateSnapshot) => {
      useProjectStore.getState().hydrateFromState(p);
    };

    socket.on("project_created", onProjectCreated);
    socket.on("agent_status", onAgentStatus);
    socket.on("agent_message", onAgentMessage);
    socket.on("approval_required", onApprovalRequired);
    socket.on("budget_update", onBudgetUpdate);
    socket.on("phase_complete", onPhaseComplete);
    socket.on("project_state", onProjectState);

    apiRef.current = {
      startProject: (idea) => socket.emit("start_project", { idea }),
      sendMessage: (text) => {
        const projectId = useProjectStore.getState().projectId;
        if (!projectId) return;
        socket.emit("user_message", { project_id: projectId, text });
      },
      approve: (comment) => {
        const projectId = useProjectStore.getState().projectId;
        if (projectId) socket.emit("approve", { project_id: projectId, comment });
      },
      reject: (comment) => {
        const projectId = useProjectStore.getState().projectId;
        if (projectId) socket.emit("reject", { project_id: projectId, comment });
      },
      modify: (comment) => {
        const projectId = useProjectStore.getState().projectId;
        if (projectId) socket.emit("modify", { project_id: projectId, comment });
      },
      retry: () => {
        const projectId = useProjectStore.getState().projectId;
        if (projectId) socket.emit("retry", { project_id: projectId });
      },
      loadProject: (projectId) => socket.emit("load_project", { project_id: projectId }),
    };

    return () => {
      socket.off("project_created", onProjectCreated);
      socket.off("agent_status", onAgentStatus);
      socket.off("agent_message", onAgentMessage);
      socket.off("approval_required", onApprovalRequired);
      socket.off("budget_update", onBudgetUpdate);
      socket.off("phase_complete", onPhaseComplete);
      socket.off("project_state", onProjectState);
    };
  }, []);

  // apiRef.current is populated synchronously inside useEffect (which runs
  // before the first render returns under React 18's strict-mode-disabled
  // flow); for test purposes, we also populate it above. If null (shouldn't
  // happen in practice), emit no-ops.
  return (
    apiRef.current ?? {
      startProject: () => {},
      sendMessage: () => {},
      approve: () => {},
      reject: () => {},
      modify: () => {},
      retry: () => {},
      loadProject: () => {},
    }
  );
}
```

- [ ] **Step 4: Run the tests — they must pass**

Run: `cd frontend && npm test -- useSocket && cd ..`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat(frontend): add useSocket hook with store-dispatched event handlers"
```

---

### Task 2.6: Create `AgentNode` component

**Files:**
- Create: `frontend/src/components/AgentNode.tsx`
- Create: `frontend/src/components/AgentNode.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/AgentNode.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { AgentNode } from "./AgentNode";

function wrap(data: any) {
  return <AgentNode data={data} id="clarifying_pm" selected={false} type="agent" dragging={false} zIndex={0} xPos={0} yPos={0} isConnectable={false} />;
}

describe("AgentNode", () => {
  test("renders pending by default", () => {
    render(wrap({ id: "clarifying_pm", name: "Clarifying PM", status: "pending" }));
    expect(screen.getByText("Clarifying PM")).toBeInTheDocument();
    expect(screen.getByTestId("agent-node")).toHaveAttribute("data-status", "pending");
  });

  test("renders running with details", () => {
    render(wrap({ id: "clarifying_pm", name: "Clarifying PM", status: "running", details: "thinking" }));
    expect(screen.getByTestId("agent-node")).toHaveAttribute("data-status", "running");
    expect(screen.getByText(/thinking/)).toBeInTheDocument();
  });

  test("renders error status", () => {
    render(wrap({ id: "backend", name: "Backend", status: "error", details: "crashed" }));
    expect(screen.getByTestId("agent-node")).toHaveAttribute("data-status", "error");
  });
});
```

- [ ] **Step 2: Run the tests — they must fail**

Run: `cd frontend && npm test -- AgentNode && cd ..`
Expected: module-not-found.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/AgentNode.tsx`:

```tsx
import { memo } from "react";
import type { NodeProps } from "@xyflow/react";

import type { AgentState, AgentStatus } from "../types";

const STATUS_CLASS: Record<AgentStatus, string> = {
  pending: "bg-gray-200 border-gray-400 text-gray-700",
  running: "bg-blue-100 border-blue-500 text-blue-900 animate-pulse",
  complete: "bg-green-100 border-green-500 text-green-900",
  error: "bg-red-100 border-red-500 text-red-900",
  downgraded: "bg-orange-100 border-orange-500 text-orange-900",
};

export const AgentNode = memo(function AgentNode({ data }: NodeProps<AgentState>) {
  return (
    <div
      data-testid="agent-node"
      data-status={data.status}
      className={`rounded-lg border-2 p-3 min-w-[160px] shadow-sm ${STATUS_CLASS[data.status]}`}
    >
      <div className="font-semibold text-sm">{data.name}</div>
      {data.details && (
        <div className="text-xs opacity-75 mt-1 truncate">{data.details}</div>
      )}
    </div>
  );
});
```

- [ ] **Step 4: Run the tests — they must pass**

Run: `cd frontend && npm test -- AgentNode && cd ..`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AgentNode.tsx frontend/src/components/AgentNode.test.tsx
git commit -m "feat(frontend): add AgentNode component with status-based styling"
```

---

### Task 2.7: Create `GraphCanvas` component

**Files:**
- Create: `frontend/src/components/GraphCanvas.tsx`

GraphCanvas is not unit-tested (per spec: React Flow internals aren't worth mocking; covered by E2E).

- [ ] **Step 1: Implement the canvas**

Create `frontend/src/components/GraphCanvas.tsx`:

```tsx
import { useMemo } from "react";
import { ReactFlow, Background, Controls, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { AgentNode } from "./AgentNode";
import { useProjectStore } from "../stores/projectStore";
import type { AgentState } from "../types";

const LAYOUT: Record<string, { x: number; y: number }> = {
  orchestrator: { x: 400, y: 0 },
  budget_guard: { x: 700, y: 0 },
  clarifying_pm: { x: 100, y: 100 },
  product_owner: { x: 400, y: 100 },
  solution_architect: { x: 100, y: 220 },
  tech_lead: { x: 300, y: 220 },
  uiux_designer: { x: 500, y: 220 },
  frontend: { x: 100, y: 360 },
  backend: { x: 250, y: 360 },
  database: { x: 400, y: 360 },
  ai_ml: { x: 550, y: 360 },
  devops: { x: 100, y: 500 },
  security: { x: 250, y: 500 },
  qa: { x: 400, y: 500 },
  technical_writer: { x: 550, y: 500 },
  delivery_summarizer: { x: 400, y: 620 },
};

const nodeTypes = { agent: AgentNode };

export function GraphCanvas() {
  const agents = useProjectStore((s) => s.agents);
  const nodes: Node<AgentState>[] = useMemo(
    () =>
      Object.values(agents).map((agent) => ({
        id: agent.id,
        type: "agent",
        position: LAYOUT[agent.id] ?? { x: 0, y: 0 },
        data: agent,
      })),
    [agents],
  );

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={[]}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        fitView
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
```

Note: the store only populates 15 agents but `LAYOUT` has 16 entries. `budget_guard` isn't in `AGENT_NAMES` in the store, so it won't render — that's intentional for this sub-project; budget state lives in the top bar. The extra entry is future-proofing; safe to leave.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GraphCanvas.tsx
git commit -m "feat(frontend): add GraphCanvas rendering 15 agents via React Flow"
```

---

### Task 2.8: Create `BudgetMeter` component

**Files:**
- Create: `frontend/src/components/BudgetMeter.tsx`
- Create: `frontend/src/components/BudgetMeter.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/BudgetMeter.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test, beforeEach } from "vitest";

import { BudgetMeter } from "./BudgetMeter";
import { useProjectStore } from "../stores/projectStore";

describe("BudgetMeter", () => {
  beforeEach(() => useProjectStore.getState().reset());

  test("renders current spend and limit", () => {
    useProjectStore.getState().setBudget({ spent: 12.34, limit: 200, threshold: 0 });
    render(<BudgetMeter />);
    expect(screen.getByText(/\$12\.34/)).toBeInTheDocument();
    expect(screen.getByText(/\$200/)).toBeInTheDocument();
  });

  test("shows threshold class for 85", () => {
    useProjectStore.getState().setBudget({ spent: 170, limit: 200, threshold: 85 });
    render(<BudgetMeter />);
    const meter = screen.getByTestId("budget-meter");
    expect(meter).toHaveAttribute("data-threshold", "85");
  });
});
```

- [ ] **Step 2: Run the tests — they must fail**

Run: `cd frontend && npm test -- BudgetMeter && cd ..`
Expected: module-not-found.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/BudgetMeter.tsx`:

```tsx
import { useProjectStore } from "../stores/projectStore";

const THRESHOLD_CLASS: Record<number, string> = {
  0: "bg-green-500",
  50: "bg-green-500",
  75: "bg-yellow-500",
  85: "bg-orange-500",
  95: "bg-red-500",
  100: "bg-red-700",
};

export function BudgetMeter() {
  const budget = useProjectStore((s) => s.budget);
  const pct = budget.limit > 0 ? Math.min(100, (budget.spent / budget.limit) * 100) : 0;
  const barClass = THRESHOLD_CLASS[budget.threshold] ?? "bg-green-500";

  return (
    <div
      data-testid="budget-meter"
      data-threshold={budget.threshold}
      className="flex items-center gap-3 px-4 py-2 border-b bg-white"
    >
      <span className="text-sm font-medium">
        ${budget.spent.toFixed(2)} / ${budget.limit.toFixed(0)}
      </span>
      <div className="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
        <div className={`h-full transition-all ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the tests — they must pass**

Run: `cd frontend && npm test -- BudgetMeter && cd ..`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/BudgetMeter.tsx frontend/src/components/BudgetMeter.test.tsx
git commit -m "feat(frontend): add BudgetMeter with threshold-colored progress bar"
```

---

### Task 2.9: Create `PRDViewer` and minimal `ChatInterface`

**Files:**
- Create: `frontend/src/components/PRDViewer.tsx`
- Create: `frontend/src/components/ChatInterface.tsx`
- Create: `frontend/src/components/ChatInterface.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/ChatInterface.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test, beforeEach, vi } from "vitest";

const emit = vi.fn();
const mockSocket = { on: vi.fn(), off: vi.fn(), emit, disconnect: vi.fn(), connected: true };
vi.mock("socket.io-client", () => ({ io: vi.fn(() => mockSocket) }));

import { ChatInterface } from "./ChatInterface";
import { useProjectStore } from "../stores/projectStore";

describe("ChatInterface", () => {
  beforeEach(() => {
    useProjectStore.getState().reset("proj-1");
    emit.mockClear();
  });

  test("renders messages from the store", () => {
    useProjectStore.getState().addMessage({
      id: "m1", role: "user", text: "Hello", timestamp: 0,
    });
    render(<ChatInterface />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  test("submitting input emits user_message", () => {
    render(<ChatInterface />);
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "build a todo app" } });
    fireEvent.submit(input.closest("form")!);
    expect(emit).toHaveBeenCalledWith("user_message", {
      project_id: "proj-1",
      text: "build a todo app",
    });
  });
});
```

- [ ] **Step 2: Run the tests — they must fail**

Run: `cd frontend && npm test -- ChatInterface && cd ..`
Expected: module-not-found.

- [ ] **Step 3: Implement `PRDViewer`**

Create `frontend/src/components/PRDViewer.tsx`:

```tsx
import ReactMarkdown from "react-markdown";

interface Props { markdown: string }

export function PRDViewer({ markdown }: Props) {
  return (
    <div
      data-testid="prd-viewer"
      className="prose prose-sm max-w-none bg-white border rounded p-3"
    >
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 4: Implement `ChatInterface`**

Create `frontend/src/components/ChatInterface.tsx`:

```tsx
import { useState } from "react";

import { useSocket } from "../hooks/useSocket";
import { useProjectStore } from "../stores/projectStore";
import { PRDViewer } from "./PRDViewer";

export function ChatInterface() {
  const { sendMessage } = useSocket();
  const messages = useProjectStore((s) => s.messages);
  const prd = useProjectStore((s) => s.prd);
  const [draft, setDraft] = useState("");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    useProjectStore.getState().addMessage({
      id: `${Date.now()}-user`,
      role: "user",
      text,
      timestamp: Date.now(),
    });
    sendMessage(text);
    setDraft("");
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                m.role === "user"
                  ? "bg-blue-500 text-white"
                  : m.role === "system"
                    ? "bg-gray-200 text-gray-700 italic"
                    : "bg-white border"
              }`}
            >
              {m.agent && <div className="text-xs font-semibold mb-1">{m.agent}</div>}
              <div className="whitespace-pre-wrap">{m.text}</div>
            </div>
          </div>
        ))}
        {prd && (
          <div>
            <div className="text-xs font-semibold mb-1 text-gray-500">Draft PRD</div>
            <PRDViewer markdown={prd} />
          </div>
        )}
      </div>
      <form onSubmit={onSubmit} className="border-t p-3 flex gap-2 bg-white">
        <input
          type="text"
          role="textbox"
          className="flex-1 border rounded px-3 py-2 text-sm"
          placeholder="Describe your idea or answer a question..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          Send
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 5: Run the tests — they must pass**

Run: `cd frontend && npm test -- ChatInterface && cd ..`
Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ChatInterface.tsx frontend/src/components/ChatInterface.test.tsx frontend/src/components/PRDViewer.tsx
git commit -m "feat(frontend): add ChatInterface and PRDViewer"
```

---

### Task 2.10: Wire up `App.tsx` with routing and layout

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Replace `App.tsx`**

Open `frontend/src/App.tsx` and replace its contents with:

```tsx
import { useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";

import { BudgetMeter } from "./components/BudgetMeter";
import { ChatInterface } from "./components/ChatInterface";
import { GraphCanvas } from "./components/GraphCanvas";
import { useSocket } from "./hooks/useSocket";
import { useProjectStore } from "./stores/projectStore";

function NewProject() {
  const { startProject } = useSocket();
  const navigate = useNavigate();
  const projectId = useProjectStore((s) => s.projectId);

  useEffect(() => {
    if (projectId) navigate(`/project/${projectId}`);
  }, [projectId, navigate]);

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const idea = (form.elements.namedItem("idea") as HTMLInputElement).value.trim();
    if (!idea) return;
    useProjectStore.setState({ idea });
    startProject(idea);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="max-w-xl w-full space-y-4 bg-white p-8 rounded shadow"
      >
        <h1 className="text-2xl font-semibold">DevTeam.AI</h1>
        <p className="text-sm text-gray-600">
          Describe the thing you want to build. The Clarifying PM will ask up
          to 6 questions and produce a PRD.
        </p>
        <input
          name="idea"
          type="text"
          className="w-full border rounded px-3 py-2"
          placeholder='e.g. "Build me a todo app"'
          required
        />
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          Start
        </button>
      </form>
    </div>
  );
}

function ProjectWorkspace() {
  const { projectId: urlId } = useParams<{ projectId: string }>();
  const { loadProject } = useSocket();
  const storeId = useProjectStore((s) => s.projectId);

  useEffect(() => {
    if (urlId && urlId !== storeId) {
      loadProject(urlId);
    }
  }, [urlId, storeId, loadProject]);

  return (
    <div className="flex flex-col h-screen">
      <BudgetMeter />
      <div className="flex-1 grid grid-cols-2 min-h-0">
        <div className="border-r bg-gray-50"><ChatInterface /></div>
        <div className="bg-white"><GraphCanvas /></div>
      </div>
    </div>
  );
}

export default function App() {
  // Call once at top level so the singleton socket + listeners exist.
  useSocket();
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<NewProject />} />
        <Route path="/project/:projectId" element={<ProjectWorkspace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 2: Verify `main.tsx` imports the CSS**

Open `frontend/src/main.tsx`. Ensure `import "./index.css";` is present near the top. If the scaffold already imports `./index.css`, leave it. Remove any stale Vite starter CSS imports (like `App.css`) that we're not using.

- [ ] **Step 3: Build to catch TypeScript errors**

Run: `cd frontend && npm run build && cd ..`
Expected: build succeeds.

- [ ] **Step 4: Run all frontend tests**

Run: `cd frontend && npm test && cd ..`
Expected: all test files pass (store, socket, AgentNode, BudgetMeter, ChatInterface).

- [ ] **Step 5: Manual smoke**

Start backend (background): `uv run -- python -m backend.main`
Start frontend (background): `cd frontend && npm run dev`
Open `http://localhost:5173/`.
Expected: the empty-state form renders. Type "test", submit. Nothing happens yet server-side (no `start_project` handler until Slice 3), but the browser should NOT show any Socket.IO connection errors. Kill both servers.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): wire App routes, workspace layout, and socket bootstrap"
```

---

## Slice 3: Mock flow end-to-end

**Outcome of Slice 3:** User types an idea in the UI → backend creates a project → mock Clarifying PM runs through the new stack → a mock PRD renders in chat → graph nodes pulse. No real LLM yet. Full UI-to-graph connection proved.

### Task 3.1: Define `ProjectState` and redesign `backend/graph.py`

**Files:**
- Modify: `backend/graph.py`
- Modify: `tests/unit/test_graph.py`

- [ ] **Step 1: Read the existing `backend/graph.py`**

Open it and identify the current state shape and node set. The existing file was designed for the Phase 1 "empty cycle" and will need restructuring.

- [ ] **Step 2: Write the new test cases first**

Append to `tests/unit/test_graph.py`:

```python
"""New tests added for Slice 3: three-node Phase 3 workflow."""
import asyncio

import pytest

from backend.graph import build_graph, ProjectState


@pytest.mark.asyncio
async def test_project_state_has_expected_fields():
    state = ProjectState(idea="todo app")
    assert state.idea == "todo app"
    assert state.questions == []
    assert state.answers == []
    assert state.prd is None
    assert state.approval_status is None
    assert state.approval_count == 0
    assert state.current_phase == 3


@pytest.mark.asyncio
async def test_build_graph_compiles_with_three_nodes():
    compiled = build_graph(checkpointer=None)
    node_names = set(compiled.get_graph().nodes.keys())
    for required in ("clarifying_pm", "product_owner_approval", "delivery_summarizer"):
        assert required in node_names, f"missing node: {required}"
```

- [ ] **Step 3: Run — expect failures**

Run: `uv run -- python -m pytest tests/unit/test_graph.py -q`
Expected: the two new tests fail (ImportError or AttributeError); pre-existing tests in this file may or may not pass depending on the prior graph definition. Note which ones fail for repair below.

- [ ] **Step 4: Rewrite `backend/graph.py`**

Replace the contents of `backend/graph.py` with:

```python
"""LangGraph definition for the Phase 3 clarification workflow.

The graph has three real nodes plus all 15 agent ids registered in state-only
form so the frontend can render them. Execution flow for this sub-project:

    START -> clarifying_pm -> product_owner_approval -> delivery_summarizer -> END

Rejection from product_owner_approval routes back to clarifying_pm for revision.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class Question(BaseModel):
    text: str
    index: int


class Answer(BaseModel):
    question_index: int
    text: str


class ProjectState(BaseModel):
    idea: str = ""
    questions: list[Question] = Field(default_factory=list)
    answers: list[Answer] = Field(default_factory=list)
    prd: str | None = None
    approval_status: Literal["pending", "approved", "rejected", "modified"] | None = None
    approval_count: int = 0
    pending_input: str | None = None
    current_phase: int = 3
    cost_so_far: float = 0.0


# Node function signatures. The actual node implementations are provided by the
# orchestrator at build time so they can close over the emit callback and the
# agent instances. Each function takes a ProjectState and returns a partial
# state update (dict).
NodeFn = Callable[[ProjectState], Awaitable[dict[str, Any]]]


def build_graph(
    checkpointer: Any | None,
    clarifying_pm_node: NodeFn | None = None,
    approval_node: NodeFn | None = None,
    summarizer_node: NodeFn | None = None,
) -> Any:
    """Compile the LangGraph. Nodes default to no-ops for static testing.

    The orchestrator passes real NodeFn callables that call into the agent
    registry and the emit callback.
    """

    async def _noop(state: ProjectState) -> dict[str, Any]:
        return {}

    clarifying_pm_node = clarifying_pm_node or _noop
    approval_node = approval_node or _noop
    summarizer_node = summarizer_node or _noop

    builder: StateGraph[ProjectState] = StateGraph(ProjectState)
    builder.add_node("clarifying_pm", clarifying_pm_node)
    builder.add_node("product_owner_approval", approval_node)
    builder.add_node("delivery_summarizer", summarizer_node)

    builder.add_edge(START, "clarifying_pm")
    builder.add_edge("clarifying_pm", "product_owner_approval")
    # Approval routing: approved -> summarizer, rejected/modified -> clarifying_pm
    builder.add_conditional_edges(
        "product_owner_approval",
        _route_after_approval,
        {"approved": "delivery_summarizer", "revise": "clarifying_pm"},
    )
    builder.add_edge("delivery_summarizer", END)

    return builder.compile(checkpointer=checkpointer, interrupt_before=["product_owner_approval"])


def _route_after_approval(state: ProjectState) -> str:
    if state.approval_status == "approved":
        return "approved"
    return "revise"
```

- [ ] **Step 5: Fix existing graph tests**

Open `tests/unit/test_graph.py`'s **existing** tests (the ones written in Phase 1/2). Any that reference the old state shape or node set need their imports and assertions updated to the new `ProjectState` / `build_graph` signatures. Drop assertions about node names or edges that no longer exist; keep assertions about checkpointer behavior and basic compilation.

If a prior test doesn't translate cleanly to the new graph (e.g., it asserted the presence of an "end" node that no longer matches), delete the test — the Slice 3 / Slice 5 tests cover the new flow.

- [ ] **Step 6: Run the full test suite**

Run: `uv run -- python -m pytest tests/ -q`
Expected: all prior tests that were kept still pass; two new tests pass; suite is green.

- [ ] **Step 7: Commit**

```bash
git add backend/graph.py tests/unit/test_graph.py
git commit -m "refactor(graph): rebuild as ProjectState + 3-node Phase 3 workflow"
```

---

### Task 3.2: Create `backend/orchestrator.py` `Orchestrator` class

**Files:**
- Modify: `backend/orchestrator.py`
- Create: `tests/integration/test_orchestrator_flow.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_orchestrator_flow.py`:

```python
"""Integration tests for Orchestrator.run using mock agents and no real LLM."""
import asyncio

import pytest

from backend.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_emits_project_started_and_agent_status():
    events: list[tuple[str, dict, str]] = []

    async def emit(event: str, data: dict, room: str) -> None:
        events.append((event, data, room))

    orch = Orchestrator(mock_mode=True)
    task = asyncio.create_task(orch.run("proj-1", "build a todo app", emit))

    # Wait for the mock agent to emit its first status update.
    for _ in range(50):
        await asyncio.sleep(0.05)
        if any(e[0] == "agent_status" for e in events):
            break

    agent_status_events = [e for e in events if e[0] == "agent_status"]
    assert agent_status_events, "expected at least one agent_status event"
    first = agent_status_events[0]
    assert first[1]["agent"] == "clarifying_pm"
    assert first[2] == "project:proj-1"

    await orch.stop("proj-1")
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run -- python -m pytest tests/integration/test_orchestrator_flow.py -q`
Expected: `ImportError` or `AttributeError` on `Orchestrator`.

- [ ] **Step 3: Implement `Orchestrator`**

Replace `backend/orchestrator.py` contents with:

```python
"""Orchestrator: compiles the graph, runs it per project, and bridges to Socket.IO via emit callback.

The orchestrator owns one asyncio task per project and a registry of pending
interrupt resumes. It does NOT import Socket.IO — the emit callable is injected
by main.py.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from backend.agents.registry import AgentRegistry
from backend.config import Config
from backend.graph import ProjectState, build_graph

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, dict, str], Awaitable[None]]


class Orchestrator:
    """Owns the per-project asyncio tasks and drives the LangGraph workflow."""

    def __init__(self, mock_mode: bool | None = None, config: Config | None = None) -> None:
        self.config = config or Config.load()
        self.mock_mode = self.config.mock_agents if mock_mode is None else mock_mode
        self.registry = AgentRegistry()
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._pending_resume: dict[str, asyncio.Future[dict]] = {}

    def _room(self, project_id: str) -> str:
        return f"project:{project_id}"

    async def run(self, project_id: str, idea: str, emit: EmitFn) -> None:
        """Kick off a new workflow for the given project id.

        Stored as an asyncio Task keyed by project_id. Callers can stop the task
        via stop(). Resumption after an interrupt is driven by resume().
        """
        room = self._room(project_id)
        await emit("agent_status", {"agent": "orchestrator", "status": "running"}, room)

        clarifying_agent = self.registry.get("clarifying_pm", mock=self.mock_mode)

        async def clarifying_node(state: ProjectState) -> dict[str, Any]:
            await emit("agent_status", {"agent": "clarifying_pm", "status": "running"}, room)
            result = await clarifying_agent.execute({
                "idea": state.idea,
                "questions": [q.model_dump() for q in state.questions],
                "answers": [a.model_dump() for a in state.answers],
                "mode": self.mock_mode and "mock" or "real",
            })
            if result.get("status") != "success":
                await emit("agent_status",
                           {"agent": "clarifying_pm", "status": "error", "details": result.get("error")},
                           room)
                raise RuntimeError(result.get("error", "clarifying_pm failed"))

            artifact = result["artifact"]
            update: dict[str, Any] = {}
            if artifact.get("question"):
                await emit("agent_message",
                           {"agent": "clarifying_pm", "text": artifact["question"]},
                           room)
                new_question = {"text": artifact["question"], "index": len(state.questions)}
                update["questions"] = state.questions + [type(state).model_fields["questions"].annotation.__args__[0].model_validate(new_question)]
            if artifact.get("prd"):
                update["prd"] = artifact["prd"]
            await emit("agent_status", {"agent": "clarifying_pm", "status": "complete"}, room)
            return update

        async def approval_node(state: ProjectState) -> dict[str, Any]:
            # The graph is configured with interrupt_before on this node, so we
            # only reach this body when resumed. Resume value is available via
            # the pending resume future.
            decision = await self._await_resume(project_id)
            return {"approval_status": decision.get("decision", "rejected"),
                    "approval_count": state.approval_count + (0 if decision.get("decision") == "approved" else 1)}

        async def summarizer_node(state: ProjectState) -> dict[str, Any]:
            await emit("agent_status", {"agent": "delivery_summarizer", "status": "running"}, room)
            await emit("phase_complete",
                       {"phase": 3, "summary": "PRD approved", "status": "success"},
                       room)
            await emit("agent_status", {"agent": "delivery_summarizer", "status": "complete"}, room)
            return {"current_phase": 4}

        graph = build_graph(
            checkpointer=None,  # SQLite checkpointer wired in Slice 5
            clarifying_pm_node=clarifying_node,
            approval_node=approval_node,
            summarizer_node=summarizer_node,
        )

        async def _driver() -> None:
            try:
                config_dict = {"configurable": {"thread_id": project_id}}
                initial = ProjectState(idea=idea)
                # Use ainvoke to let interrupts propagate; handle them at resume()
                await graph.ainvoke(initial, config=config_dict)
            except asyncio.CancelledError:
                logger.info("orchestrator.run cancelled for %s", project_id)
                raise
            except Exception as exc:
                logger.exception("orchestrator.run failed for %s", project_id)
                await emit("phase_complete",
                           {"phase": 3, "summary": str(exc), "status": "failed", "reason": "exception"},
                           room)

        task = asyncio.create_task(_driver(), name=f"orchestrator:{project_id}")
        self._tasks[project_id] = task

    async def resume(self, project_id: str, decision: dict) -> None:
        """Complete the pending interrupt future with the user's decision."""
        fut = self._pending_resume.get(project_id)
        if fut and not fut.done():
            fut.set_result(decision)

    async def stop(self, project_id: str) -> None:
        task = self._tasks.pop(project_id, None)
        if task and not task.done():
            task.cancel()
        fut = self._pending_resume.pop(project_id, None)
        if fut and not fut.done():
            fut.cancel()

    async def _await_resume(self, project_id: str) -> dict:
        fut: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
        self._pending_resume[project_id] = fut
        return await fut
```

Note: this skeleton wires the driver loop but does not yet handle interrupts correctly against LangGraph 1.0 — Slice 5 finishes the interrupt/resume contract with `SqliteSaver` + `Command(resume=...)`. For Slice 3 we validate only the "clarifying_pm emits status" path; the test above stops the task before reaching the interrupt.

- [ ] **Step 4: Run the test — it must pass**

Run: `uv run -- python -m pytest tests/integration/test_orchestrator_flow.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/orchestrator.py tests/integration/test_orchestrator_flow.py
git commit -m "feat(orchestrator): add Orchestrator.run with emit callback and mock flow"
```

---

### Task 3.3: Wire `start_project` and `user_message` Socket.IO handlers

**Files:**
- Modify: `backend/main.py`
- Create: `tests/integration/test_socketio_events.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_socketio_events.py`:

```python
"""End-to-end Socket.IO tests: client sends events, server emits expected responses."""
import asyncio

import pytest
import socketio
import uvicorn


@pytest.fixture
async def server_and_client():
    from backend.main import asgi_app  # reimport inside test to reset state if needed
    config = uvicorn.Config(asgi_app, host="127.0.0.1", port=8766, log_level="warning")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)
    client = socketio.AsyncClient()
    await client.connect("http://127.0.0.1:8766", socketio_path="/socket.io")
    try:
        yield server, client
    finally:
        await client.disconnect()
        server.should_exit = True
        await task


@pytest.mark.asyncio
async def test_start_project_emits_project_created(server_and_client):
    server, client = server_and_client
    received: list[dict] = []
    client.on("project_created", lambda data: received.append(data))

    await client.emit("start_project", {"idea": "build a todo app"})
    # Give the server a moment
    for _ in range(50):
        await asyncio.sleep(0.05)
        if received:
            break
    assert received, "expected project_created event"
    assert "project_id" in received[0]
    assert len(received[0]["project_id"]) > 0


@pytest.mark.asyncio
async def test_start_project_with_empty_idea_returns_error(server_and_client):
    server, client = server_and_client
    ack = await client.call("start_project", {"idea": ""}, timeout=2)
    assert ack == {"error": "idea required"}
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run -- python -m pytest tests/integration/test_socketio_events.py -q`
Expected: tests fail because handlers aren't registered (no `project_created` received).

- [ ] **Step 3: Register handlers in `backend/main.py`**

Update `backend/main.py` to add imports and handler bindings. Replace the existing `connect`/`disconnect` handlers and add below them:

```python
import uuid
from typing import Any

from backend.orchestrator import Orchestrator

orchestrator = Orchestrator(config=config)


async def _emit(event: str, data: dict[str, Any], room: str) -> None:
    await sio.emit(event, data, room=room)


@sio.event
async def start_project(sid: str, data: dict[str, Any]) -> dict | None:
    idea = (data or {}).get("idea", "").strip()
    if not idea:
        return {"error": "idea required"}

    project_id = str(uuid.uuid4())
    room = f"project:{project_id}"
    await sio.enter_room(sid, room)
    await sio.emit("project_created", {"project_id": project_id}, to=sid)
    await orchestrator.run(project_id, idea, _emit)
    return None


@sio.event
async def user_message(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    text = (data or {}).get("text", "")
    if not project_id or not text:
        return {"error": "project_id and text required"}

    # Queue the message as a resume value; for the clarifying flow this maps
    # to the next answer.
    await orchestrator.resume(project_id, {"answer": text})
    return None


@sio.event
async def load_project(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    room = f"project:{project_id}"
    await sio.enter_room(sid, room)
    # SqliteSaver-driven hydration lands in Slice 5. For now, just confirm the
    # room join; if the project is currently running, its existing emits will
    # reach this client.
    return None
```

- [ ] **Step 4: Run the test — it must pass**

Run: `uv run -- python -m pytest tests/integration/test_socketio_events.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/integration/test_socketio_events.py
git commit -m "feat(main): register start_project, user_message, load_project handlers"
```

---

### Task 3.4: Update mock Clarifying PM to emit through the new flow

**Files:**
- Modify: `backend/agents/mock_agent.py` (or wherever `MockClarifyingPMAgent` lives)

- [ ] **Step 1: Open and inspect the existing mock**

Read `backend/agents/mock_agent.py` and locate the `MockClarifyingPMAgent` subclass. Identify its current `execute` signature. The orchestrator calls `await clarifying_agent.execute({...})` expecting `{status, artifact, cost}`.

- [ ] **Step 2: Ensure the mock's `execute` returns the expected artifact shape**

The orchestrator's `clarifying_node` (Task 3.2) expects `artifact` to have either `question` (string) or `prd` (string). Make the mock return something like:

```python
# In MockClarifyingPMAgent.execute
answered = len(task.get("answers", []))
if answered < 3:
    return {
        "status": "success",
        "artifact": {"question": f"[mock] Clarifying question #{answered + 1}?"},
        "cost": 0.0,
    }
return {
    "status": "success",
    "artifact": {
        "prd": "# Mock PRD\n\n## Acceptance Criteria\n- [ ] build the thing\n",
    },
    "cost": 0.0,
}
```

Preserve any existing `_emit_status` calls if the base class expects them. If the mock currently does more than this, keep the extras but ensure the artifact shape is present.

- [ ] **Step 3: Run affected tests**

Run: `uv run -- python -m pytest tests/unit/test_agent_registry.py tests/integration/test_orchestrator_flow.py -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/agents/mock_agent.py
git commit -m "feat(mock): emit question/prd artifact shape expected by orchestrator"
```

---

### Task 3.5: Slice 3 manual smoke test

**Files:** None modified.

- [ ] **Step 1: Start backend**

Run (background): `MOCK_AGENTS=true uv run -- python -m backend.main`

- [ ] **Step 2: Start frontend**

Run (background): `cd frontend && npm run dev`

- [ ] **Step 3: Walk through the flow in the browser**

1. Open `http://localhost:5173/`.
2. Type "build me a todo app", submit.
3. Expected URL: `http://localhost:5173/project/<uuid>`.
4. Expected: `clarifying_pm` node pulses blue briefly, then a mock question appears in the chat.
5. Type an answer, press send. Another mock question appears. Repeat up to the mock's answer cap.
6. After the final answer, a mock PRD renders in the chat.
7. No console errors in the browser. No exceptions in the backend log.

- [ ] **Step 4: Kill servers and commit any README/.env.example updates discovered during smoke**

```bash
# Only if files were changed during smoke (unlikely at this step)
git status
```

If nothing changed, no commit. Otherwise commit with a `docs:` or `chore:` prefix.

---

## Slice 4: Real Anthropic + prompts

**Outcome of Slice 4:** Clarifying PM uses the real Anthropic API (Claude Sonnet 4.6) with a Pydantic-structured response, the `prompts/v1/clarifying_pm.jinja` template is loaded via `prompt_loader.py`, and the 6-question cap with synthesis works. `MOCK_AGENTS=true` still short-circuits to the mock.

### Task 4.1: Create `backend/prompt_loader.py`

**Files:**
- Create: `backend/prompt_loader.py`
- Create: `tests/unit/test_prompt_loader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_prompt_loader.py`:

```python
"""Tests for the Jinja2 prompt loader."""
import os
from pathlib import Path

import pytest

from backend.prompt_loader import load_prompt, _clear_cache


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_V1 = REPO_ROOT / "prompts" / "v1"


@pytest.fixture(autouse=True)
def _reset():
    _clear_cache()
    yield
    _clear_cache()


def test_load_prompt_renders_context():
    # Requires prompts/v1/clarifying_pm.jinja to exist.
    assert (PROMPTS_V1 / "clarifying_pm.jinja").exists(), "fixture prompt missing"
    rendered = load_prompt("clarifying_pm", idea="build a todo app",
                           questions_so_far=[], answers_so_far=[])
    assert "todo app" in rendered


def test_load_prompt_missing_raises(tmp_path, monkeypatch):
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist_xyz", idea="x")


def test_load_prompt_cached_when_debug_false(monkeypatch):
    monkeypatch.setenv("DEBUG", "false")
    a = load_prompt("clarifying_pm", idea="a", questions_so_far=[], answers_so_far=[])
    b = load_prompt("clarifying_pm", idea="a", questions_so_far=[], answers_so_far=[])
    assert a == b  # cache hit returns same rendered output


def test_load_prompt_bypass_when_debug_true(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    # Function should still succeed; we're asserting no raise + output contains the idea.
    out = load_prompt("clarifying_pm", idea="zzz-unique", questions_so_far=[], answers_so_far=[])
    assert "zzz-unique" in out
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run -- python -m pytest tests/unit/test_prompt_loader.py -q`
Expected: `ModuleNotFoundError: No module named 'backend.prompt_loader'`.

- [ ] **Step 3: Implement the loader**

Create `backend/prompt_loader.py`:

```python
"""Jinja2 prompt loader.

Reads templates from the root-level prompts/{version}/ directory. Caches
rendered output when DEBUG is false (hot-reload when true).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"


def _env_for_version(version: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR / version)),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


@lru_cache(maxsize=64)
def _render_cached(agent_name: str, version: str, frozen_context: tuple) -> str:
    env = _env_for_version(version)
    context = dict(frozen_context)
    try:
        template = env.get_template(f"{agent_name}.jinja")
    except TemplateNotFound as exc:
        raise FileNotFoundError(f"prompt not found: {agent_name} (version {version})") from exc
    return template.render(**context)


def _clear_cache() -> None:
    _render_cached.cache_clear()


def _freeze(obj: Any) -> Any:
    if isinstance(obj, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(_freeze(x) for x in obj)
    return obj


def load_prompt(agent_name: str, version: str = "v1", **context: Any) -> str:
    """Render a prompt template for the given agent.

    When DEBUG=true the cache is bypassed so editing the .jinja file is
    reflected on the next call without restart.
    """
    if os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}:
        env = _env_for_version(version)
        try:
            template = env.get_template(f"{agent_name}.jinja")
        except TemplateNotFound as exc:
            raise FileNotFoundError(f"prompt not found: {agent_name} (version {version})") from exc
        return template.render(**context)
    frozen = _freeze(context)
    return _render_cached(agent_name, version, frozen)
```

- [ ] **Step 4: Run the tests — they must pass**

Run: `uv run -- python -m pytest tests/unit/test_prompt_loader.py -q`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/prompt_loader.py tests/unit/test_prompt_loader.py
git commit -m "feat: add backend.prompt_loader with debug-aware cache"
```

---

### Task 4.2: Update the clarifying_pm prompt with structured-output instructions

**Files:**
- Modify: `prompts/v1/clarifying_pm.jinja`

- [ ] **Step 1: Read the existing prompt**

Open `prompts/v1/clarifying_pm.jinja` and review its current content.

- [ ] **Step 2: Replace with a structured-output template**

Replace the file's contents with:

```jinja
You are a senior product manager. Your job is to transform a vague idea into
a clean Product Requirements Document (PRD) by asking focused clarifying
questions, one at a time, for at most {{ max_questions }} turns.

# Input

Idea: {{ idea }}

Questions asked so far ({{ questions_so_far | length }}):
{% for q in questions_so_far -%}
- [Q{{ loop.index }}] {{ q.text }}
{% endfor %}

Answers collected ({{ answers_so_far | length }}):
{% for a in answers_so_far -%}
- [A{{ loop.index }}] {{ a.text }}
{% endfor %}

# Rubric

A good PRD includes:
- A one-sentence problem statement grounded in a concrete user need.
- Primary user and their goal.
- Success metric (quantitative where possible).
- 3-7 acceptance criteria phrased as "Given / When / Then" or "The system shall…".
- Explicit non-goals.
- Scope of the MVP (what is IN and what is OUT).

When information is missing to write any rubric item, ask one focused question
that closes the largest gap. Do not ask about technology choices, deployment,
or team structure in the clarifying phase.

# Output

Respond with a JSON object matching this schema exactly:

{
  "next_question": "<string or null>",
  "final_prd": "<markdown string or null>",
  "done": <true|false>
}

Rules:
- If you still need information, set `next_question` to the question text and
  leave `final_prd` null and `done` false.
- If you have enough information OR you have asked {{ max_questions }} questions,
  set `final_prd` to the complete markdown PRD and `done` true.
- Never set both `next_question` and `final_prd` non-null.
- The PRD must include all rubric sections above.
```

- [ ] **Step 3: Sanity-check via the loader**

Run:

```bash
uv run -- python -c "from backend.prompt_loader import load_prompt; print(load_prompt('clarifying_pm', idea='test', questions_so_far=[], answers_so_far=[], max_questions=6)[:200])"
```

Expected: prints the first 200 characters, including "senior product manager" and "test".

- [ ] **Step 4: Commit**

```bash
git add prompts/v1/clarifying_pm.jinja
git commit -m "feat(prompts): rewrite clarifying_pm prompt with structured output + rubric"
```

---

### Task 4.3: Implement the real `ClarifyingPMAgent`

**Files:**
- Create: `backend/agents/clarifying_pm.py`
- Create: `tests/unit/test_clarifying_pm_agent.py`
- Modify: `backend/agents/registry.py` (register the real class, keep mock as fallback)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_clarifying_pm_agent.py`:

```python
"""Unit tests for the real ClarifyingPMAgent using FakeListChatModel."""
import json

import pytest
from langchain_community.chat_models.fake import FakeListChatModel

from backend.agents.clarifying_pm import ClarifyingPMAgent, ClarifyingResponse


def _fake_model(responses: list[dict]) -> FakeListChatModel:
    return FakeListChatModel(responses=[json.dumps(r) for r in responses])


@pytest.mark.asyncio
async def test_asks_first_question_from_idea():
    model = _fake_model([
        {"next_question": "Who is the primary user?", "final_prd": None, "done": False}
    ])
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute({"idea": "build a todo app",
                                "questions": [], "answers": []})
    assert out["status"] == "success"
    assert out["artifact"]["question"] == "Who is the primary user?"
    assert out["artifact"].get("prd") is None


@pytest.mark.asyncio
async def test_follow_up_uses_prior_answers():
    model = _fake_model([
        {"next_question": "What is the success metric?", "final_prd": None, "done": False}
    ])
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute({
        "idea": "build a todo app",
        "questions": [{"text": "Who is the primary user?", "index": 0}],
        "answers": [{"question_index": 0, "text": "remote engineers"}],
    })
    assert out["artifact"]["question"] == "What is the success metric?"


@pytest.mark.asyncio
async def test_emits_prd_when_done():
    prd = "# PRD\n\n## Acceptance Criteria\n- [ ] works"
    model = _fake_model([
        {"next_question": None, "final_prd": prd, "done": True}
    ])
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute({"idea": "todo app",
                                "questions": [{"text": "q", "index": 0}] * 2,
                                "answers": [{"question_index": 0, "text": "a"}] * 2})
    assert out["artifact"]["prd"] == prd
    assert out["artifact"].get("question") is None


@pytest.mark.asyncio
async def test_synthesizes_prd_at_max_questions():
    """At max_questions, the agent should force a final PRD even if the model asks another question."""
    model = _fake_model([
        {"next_question": "Another question?", "final_prd": None, "done": False},
        # Second call is the forced synthesis with a tightened prompt.
        {"next_question": None, "final_prd": "# Synthesized PRD", "done": True},
    ])
    agent = ClarifyingPMAgent(model=model, max_questions=2)
    out = await agent.execute({
        "idea": "todo app",
        "questions": [{"text": "q1", "index": 0}, {"text": "q2", "index": 1}],
        "answers": [{"question_index": 0, "text": "a1"}, {"question_index": 1, "text": "a2"}],
    })
    assert out["artifact"]["prd"] == "# Synthesized PRD"


@pytest.mark.asyncio
async def test_retries_once_on_malformed_json():
    model = _fake_model([
        "not-json",
        {"next_question": "Recovered?", "final_prd": None, "done": False},
    ])
    # Patch the second call manually since we mixed types above — use real seeding:
    model = FakeListChatModel(responses=[
        "not-json",
        json.dumps({"next_question": "Recovered?", "final_prd": None, "done": False}),
    ])
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute({"idea": "x", "questions": [], "answers": []})
    assert out["status"] == "success"
    assert out["artifact"]["question"] == "Recovered?"


@pytest.mark.asyncio
async def test_errors_on_second_malformed_json():
    model = FakeListChatModel(responses=["not-json", "still-not-json"])
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute({"idea": "x", "questions": [], "answers": []})
    assert out["status"] == "error"
    assert "recoverable" in out
    assert out["recoverable"] is True
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run -- python -m pytest tests/unit/test_clarifying_pm_agent.py -q`
Expected: import error for `backend.agents.clarifying_pm`.

- [ ] **Step 3: Implement the agent**

Create `backend/agents/clarifying_pm.py`:

```python
"""Real Clarifying PM agent backed by an LLM chat model with structured output."""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from backend.agents.base_agent import InstrumentedAgent
from backend.config import Config
from backend.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class ClarifyingResponse(BaseModel):
    next_question: str | None = Field(default=None)
    final_prd: str | None = Field(default=None)
    done: bool = Field(default=False)


class ClarifyingPMAgent(InstrumentedAgent):
    def __init__(self, model: BaseChatModel | None = None, max_questions: int = 6,
                 name: str = "clarifying_pm") -> None:
        super().__init__(name=name)
        self.model = model or self._default_model()
        self.max_questions = max_questions

    def _default_model(self) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic
        cfg = Config.load()
        return ChatAnthropic(
            model=cfg.anthropic_model,
            anthropic_api_key=cfg.anthropic_api_key or "missing",
            max_tokens=2048,
            timeout=60.0,
        )

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        idea = task.get("idea", "")
        questions = task.get("questions", [])
        answers = task.get("answers", [])

        # Render the prompt (same template both for asking and for forcing synthesis).
        force_synthesis = len(questions) >= self.max_questions
        rendered = load_prompt(
            "clarifying_pm",
            idea=idea,
            questions_so_far=questions,
            answers_so_far=answers,
            max_questions=self.max_questions,
        )

        response_text, parsed = await self._call_with_retry(rendered, force_synthesis)
        if parsed is None:
            return {"status": "error", "error": "invalid LLM response", "recoverable": True}

        # If the model tried to ask another question past the cap, force synthesis.
        if force_synthesis and parsed.final_prd is None:
            synthesis_prompt = rendered + (
                "\n\nYou have asked the maximum number of questions. "
                "You MUST respond with final_prd set to the complete PRD and done=true. "
                "Do not ask another question."
            )
            _, parsed = await self._call_with_retry(synthesis_prompt, force_synthesis=True)
            if parsed is None or parsed.final_prd is None:
                return {"status": "error", "error": "synthesis failed", "recoverable": True}

        artifact: dict[str, Any] = {}
        if parsed.final_prd is not None:
            artifact["prd"] = parsed.final_prd
        elif parsed.next_question is not None:
            artifact["question"] = parsed.next_question
        else:
            return {"status": "error", "error": "empty LLM response", "recoverable": True}

        return {"status": "success", "artifact": artifact, "cost": 0.0}

    async def _call_with_retry(
        self, prompt: str, force_synthesis: bool
    ) -> tuple[str, ClarifyingResponse | None]:
        for attempt in (1, 2):
            messages = [
                SystemMessage(content="You are a senior product manager. Respond ONLY with JSON."),
                HumanMessage(content=prompt if attempt == 1 else prompt +
                             "\n\nYour last response was not valid JSON. Respond with JSON only."),
            ]
            raw = await self.model.ainvoke(messages)
            text = raw.content if hasattr(raw, "content") else str(raw)
            parsed = self._parse(text)
            if parsed is not None:
                return text, parsed
        return text, None

    @staticmethod
    def _parse(text: str) -> ClarifyingResponse | None:
        try:
            data = json.loads(text)
            return ClarifyingResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            return None
```

- [ ] **Step 4: Run the tests — they must pass**

Run: `uv run -- python -m pytest tests/unit/test_clarifying_pm_agent.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Register the real agent in the registry**

Open `backend/agents/registry.py`. Find the registry entry for `clarifying_pm`. Update it so that when `Config.mock_agents == False`, `get("clarifying_pm")` returns `ClarifyingPMAgent()`; otherwise returns the existing mock. If the registry already supports a `mock` keyword (per CLAUDE.md it does), add the real-class mapping:

```python
from backend.agents.clarifying_pm import ClarifyingPMAgent

# In whatever structure the registry uses:
AGENT_CLASSES = {
    # ...
    "clarifying_pm": {"real": ClarifyingPMAgent, "mock": MockClarifyingPMAgent},
    # ...
}
```

Implement `AgentRegistry.get(name, mock: bool)` to select the right class. If the existing interface differs, adapt — the key behavior is: `orchestrator.registry.get("clarifying_pm", mock=False)` returns an instance that calls the real Anthropic API. Write a focused test if the routing logic is non-trivial.

- [ ] **Step 6: Run registry and orchestrator tests**

Run: `uv run -- python -m pytest tests/unit/test_agent_registry.py tests/integration/test_orchestrator_flow.py -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/agents/clarifying_pm.py backend/agents/registry.py tests/unit/test_clarifying_pm_agent.py
git commit -m "feat(agents): add real ClarifyingPMAgent with structured output + retry"
```

---

### Task 4.4: Integrate BudgetGuard `record_spend` into the clarifying path

**Files:**
- Modify: `backend/orchestrator.py`

- [ ] **Step 1: Find the existing BudgetGuard integration points**

Open `backend/agents/budget_guard.py`. Note the `record_spend(amount)` (or equivalent) method signature and the `can_spend(amount)` check.

- [ ] **Step 2: Wire BudgetGuard into `clarifying_node`**

In `backend/orchestrator.py`, in the `run(...)` method's `clarifying_node` closure, wrap the `clarifying_agent.execute(...)` call:

```python
# Before invocation: enforce budget
estimate = 0.05  # placeholder conservative estimate; real token-based estimate in Phase 4+
if not self.budget_guard.can_spend(estimate):
    await emit("agent_status",
               {"agent": "clarifying_pm", "status": "error", "details": "budget_exceeded"},
               room)
    raise RuntimeError("Budget hard stop before clarifying_pm")

result = await clarifying_agent.execute({...})

# After invocation: record actual spend if the agent reported it
actual = float(result.get("cost", 0.0))
prev_threshold = self.budget_guard.threshold_pct()
self.budget_guard.record_spend(actual)
new_threshold = self.budget_guard.threshold_pct()
if new_threshold != prev_threshold:
    await emit("budget_update",
               {"spent": self.budget_guard.spent, "limit": self.budget_guard.limit,
                "threshold": new_threshold},
               room)
```

Also add `self.budget_guard = BudgetGuard(...)` instantiation in `Orchestrator.__init__`, matching whatever the existing BudgetGuard constructor expects. Import at the top of the file.

- [ ] **Step 3: Run all backend tests**

Run: `uv run -- python -m pytest tests/ -q`
Expected: green.

- [ ] **Step 4: Commit**

```bash
git add backend/orchestrator.py
git commit -m "feat(orchestrator): integrate BudgetGuard around clarifying_pm calls"
```

---

### Task 4.5: Environment fallback — mock when `MOCK_AGENTS=true`

**Files:**
- Modify: `backend/orchestrator.py` (already `mock_mode` aware — verify)
- Create: `tests/integration/test_mock_fallback.py`

- [ ] **Step 1: Write the test**

Create `tests/integration/test_mock_fallback.py`:

```python
"""Verify that MOCK_AGENTS=true makes the orchestrator pick the mock agent."""
import pytest

from backend.config import Config
from backend.orchestrator import Orchestrator


def test_mock_mode_selects_mock_agent(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    orch = Orchestrator()
    agent = orch.registry.get("clarifying_pm", mock=orch.mock_mode)
    # MockClarifyingPMAgent should be a subclass of MockAgent; real agent is not.
    from backend.agents.mock_agent import MockAgent
    assert isinstance(agent, MockAgent)


def test_real_mode_selects_real_agent(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    orch = Orchestrator()
    agent = orch.registry.get("clarifying_pm", mock=orch.mock_mode)
    from backend.agents.clarifying_pm import ClarifyingPMAgent
    assert isinstance(agent, ClarifyingPMAgent)
```

- [ ] **Step 2: Run — verify pass**

Run: `uv run -- python -m pytest tests/integration/test_mock_fallback.py -q`
Expected: `2 passed`. If the registry routing isn't in place yet, go back to Task 4.3 Step 5 and finish it.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_mock_fallback.py
git commit -m "test: verify MOCK_AGENTS env flag routes to mock vs real agent"
```

---

### Task 4.6: Manual smoke — real Anthropic call

**Files:** None modified.

- [ ] **Step 1: Confirm `.env` has `ANTHROPIC_API_KEY`**

If no `.env` exists: create one with `ANTHROPIC_API_KEY=sk-ant-...` (user's real key). Ensure `.env` is listed in `.gitignore` (it already is per the existing repo).

- [ ] **Step 2: Run backend in real mode**

Run (background): `MOCK_AGENTS=false uv run -- python -m backend.main`

- [ ] **Step 3: Run frontend**

Run (background): `cd frontend && npm run dev`

- [ ] **Step 4: Exercise the flow with a real idea**

Open `http://localhost:5173/`. Type "build a pomodoro timer for deep-work sessions". Submit. Expect Anthropic-generated clarifying questions. Answer a few; after 6 questions or when Claude thinks it has enough, expect a real PRD in markdown.

- [ ] **Step 5: Note findings**

Any issues (bad PRD format, too many questions, budget not tracked) go into a follow-up commit or backlog entry. Kill servers.

---

## Slice 5: Approval gate + SQLite resume + final cleanup

**Outcome of Slice 5:** `SqliteSaver` persists all checkpoints. The approval gate interrupts before `product_owner_approval`, waits for user decision, and resumes via `Command(resume=...)`. Closing and reopening `/project/<id>` restores state. Rejection cycles route back to Clarifying PM with feedback; the 3rd rejection surfaces an escalation flag. `gauntlite/` is archived. `CLAUDE.md` is updated.

### Task 5.1: Wire `SqliteSaver` into the orchestrator

**Files:**
- Modify: `backend/orchestrator.py`
- Create: `tests/integration/test_persistence.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_persistence.py`:

```python
"""Round-trip checkpoint persistence across two Orchestrator instances."""
import asyncio
import os

import pytest

from backend.orchestrator import Orchestrator
from backend.graph import ProjectState


@pytest.mark.asyncio
async def test_checkpoint_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "checkpoints.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    monkeypatch.setenv("MOCK_AGENTS", "true")

    received: list = []

    async def emit(event: str, data: dict, room: str) -> None:
        received.append((event, data))

    # Run 1: partway through clarifying
    orch1 = Orchestrator()
    await orch1.run("proj-persist", "build a thing", emit)
    for _ in range(40):
        await asyncio.sleep(0.05)
        if any(e[0] == "agent_status" and e[1].get("status") == "running" for e in received):
            break
    await orch1.stop("proj-persist")

    # Run 2: new orchestrator loads the same thread
    orch2 = Orchestrator()
    snap = await orch2.load("proj-persist")
    assert snap is not None
    assert snap["idea"] == "build a thing"
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run -- python -m pytest tests/integration/test_persistence.py -q`
Expected: fails with missing `Orchestrator.load` or checkpointer not configured.

- [ ] **Step 3: Replace orchestrator checkpointer and add `load`**

In `backend/orchestrator.py`:

1. Import at top:
   ```python
   import sqlite3
   from pathlib import Path
   from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
   ```
2. In `__init__`, set up the async SqliteSaver:
   ```python
   Path(self.config.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
   self._saver_cm = AsyncSqliteSaver.from_conn_string(self.config.sqlite_path)
   self._saver: AsyncSqliteSaver | None = None
   ```
3. Add `async def _ensure_saver(self)` helper:
   ```python
   async def _ensure_saver(self) -> AsyncSqliteSaver:
       if self._saver is None:
           self._saver = await self._saver_cm.__aenter__()
           # Enable WAL for better concurrent reads
           async with self._saver.conn.cursor() as cur:
               await cur.execute("PRAGMA journal_mode=WAL;")
       return self._saver
   ```
4. In `run()`, await `saver = await self._ensure_saver()` and pass it to `build_graph(checkpointer=saver, ...)`.
5. Add a `load(project_id)` method:
   ```python
   async def load(self, project_id: str) -> dict | None:
       saver = await self._ensure_saver()
       config_dict = {"configurable": {"thread_id": project_id}}
       tup = await saver.aget_tuple(config_dict)
       if tup is None:
           return None
       state: ProjectState = tup.checkpoint["channel_values"]["__root__"] if "__root__" in tup.checkpoint["channel_values"] else tup.checkpoint["channel_values"]
       # LangGraph's internal shape varies; normalize to the public ProjectState
       if isinstance(state, dict):
           state_obj = ProjectState.model_validate(state)
       else:
           state_obj = state  # type: ignore[assignment]
       return state_obj.model_dump()
   ```

If the LangGraph 1.0 `get_tuple` shape differs, inspect `tup.checkpoint` and adjust. The contract is: return a dict with at least `idea`, `questions`, `answers`, `prd`, `approval_status`, `current_phase` populated.

- [ ] **Step 4: Run the test — it must pass**

Run: `uv run -- python -m pytest tests/integration/test_persistence.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/orchestrator.py tests/integration/test_persistence.py
git commit -m "feat(orchestrator): persist checkpoints via AsyncSqliteSaver, add load()"
```

---

### Task 5.2: Implement approval interrupt and resume

**Files:**
- Modify: `backend/orchestrator.py`
- Modify: `backend/main.py`
- Create: `tests/integration/test_approval_flow.py`

- [ ] **Step 1: Write the test**

Create `tests/integration/test_approval_flow.py`:

```python
"""Verify the approval gate interrupts, emits approval_required, and resumes on approve."""
import asyncio

import pytest

from backend.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_approval_required_emitted_and_resume_on_approve(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "chk.db"))
    received: list = []

    async def emit(event: str, data: dict, room: str) -> None:
        received.append((event, data))

    orch = Orchestrator()
    await orch.run("proj-apr", "todo app", emit)
    # Feed 3 mock answers to trigger PRD
    for _ in range(3):
        for _ in range(20):
            await asyncio.sleep(0.05)
            if any(e[0] == "agent_message" and "question" not in e[1].get("text", "").lower() or
                   e[0] == "approval_required" for e in received):
                break
        await orch.user_message("proj-apr", "answer")

    # Wait for approval_required
    for _ in range(60):
        await asyncio.sleep(0.05)
        if any(e[0] == "approval_required" for e in received):
            break
    assert any(e[0] == "approval_required" for e in received), "expected approval_required"

    await orch.approve("proj-apr")
    # Wait for phase_complete
    for _ in range(40):
        await asyncio.sleep(0.05)
        if any(e[0] == "phase_complete" for e in received):
            break
    assert any(e[0] == "phase_complete" and e[1].get("status") == "success" for e in received)
```

- [ ] **Step 2: Run — expect failure**

Run: `uv run -- python -m pytest tests/integration/test_approval_flow.py -q`
Expected: fails because `approve`, `user_message` (instance method), and the interrupt/emit wiring aren't complete.

- [ ] **Step 3: Update `backend/orchestrator.py` to emit `approval_required` and handle `Command(resume)`**

In the orchestrator's `run()` method, change the approval_node to be a true interrupt that emits before pausing. With LangGraph 1.0, the `interrupt()` helper from `langgraph.types` can be called inside the node body to pause; orchestrator resumes by invoking `graph.ainvoke(Command(resume=...))`.

Rewrite the relevant parts of `run()`:

```python
from langgraph.types import Command, interrupt

async def approval_node(state: ProjectState) -> dict[str, Any]:
    payload = {
        "agent": "product_owner",
        "phase": 3,
        "content": state.prd or "",
        "escalation": state.approval_count >= 3,
    }
    await emit("approval_required", payload, room)
    decision = interrupt(payload)  # pauses here; resumed with the user's choice
    return {
        "approval_status": decision.get("decision", "rejected"),
        "approval_count": (
            state.approval_count + 1 if decision.get("decision") != "approved" else state.approval_count
        ),
    }
```

Then restructure the driver to loop over interrupts:

```python
async def _driver() -> None:
    try:
        saver = await self._ensure_saver()
        graph = build_graph(
            checkpointer=saver,
            clarifying_pm_node=clarifying_node,
            approval_node=approval_node,
            summarizer_node=summarizer_node,
        )
        config_dict = {"configurable": {"thread_id": project_id}}
        inputs: Any = ProjectState(idea=idea)
        while True:
            result = await graph.ainvoke(inputs, config=config_dict)
            if "__interrupt__" in result:
                # Wait for the user's decision, then resume
                decision = await self._await_resume(project_id)
                inputs = Command(resume=decision)
                continue
            break
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("driver failed")
        await emit("phase_complete",
                   {"phase": 3, "summary": str(exc), "status": "failed", "reason": "exception"},
                   room)
```

Add orchestrator instance methods:

```python
async def approve(self, project_id: str) -> None:
    await self.resume(project_id, {"decision": "approved"})

async def reject(self, project_id: str, comment: str | None = None) -> None:
    await self.resume(project_id, {"decision": "rejected", "comment": comment})

async def modify(self, project_id: str, comment: str) -> None:
    await self.resume(project_id, {"decision": "modified", "comment": comment})

async def user_message(self, project_id: str, text: str) -> None:
    # For the clarifying flow, a user_message IS the next answer. Queue it via resume
    # only if the graph is in the interrupt state before clarifying_pm's answer ingestion.
    await self.resume(project_id, {"answer": text})

async def retry(self, project_id: str, emit: EmitFn | None = None) -> None:
    """Re-run the graph from the last checkpoint.

    If the previous driver task is still running (rare — most retry cases come
    from an error that ended the task), do nothing. Otherwise re-invoke ainvoke
    with no resume value, which resumes from the last checkpoint.
    """
    task = self._tasks.get(project_id)
    if task and not task.done():
        return  # still running; nothing to retry
    emit_fn = emit or self._last_emit.get(project_id)
    if emit_fn is None:
        return  # no way to reach the client; caller should re-run via main.py
    snap = await self.load(project_id)
    if snap is None:
        return
    await self.run(project_id, snap.get("idea", ""), emit_fn)
```

Additions needed to support `retry`:
- In `__init__`, add `self._last_emit: dict[str, EmitFn] = {}`.
- In `run()`, set `self._last_emit[project_id] = emit` at the top so future `retry` calls can reuse the same callback.
- In `backend/main.py`'s `retry` handler, call `await orchestrator.retry(project_id, _emit)` so the emit fn is always available.

- [ ] **Step 4: Wire the new `Orchestrator` methods into `backend/main.py`**

Add to `backend/main.py`:

```python
@sio.event
async def approve(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    await orchestrator.approve(project_id)
    return None


@sio.event
async def reject(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    await orchestrator.reject(project_id, (data or {}).get("comment"))
    return None


@sio.event
async def modify(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    comment = (data or {}).get("comment", "")
    if not project_id or not comment:
        return {"error": "project_id and comment required"}
    await orchestrator.modify(project_id, comment)
    return None


@sio.event
async def retry(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    await orchestrator.retry(project_id)
    return None
```

Also replace the `user_message` handler body:

```python
@sio.event
async def user_message(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    text = (data or {}).get("text", "")
    if not project_id or not text:
        return {"error": "project_id and text required"}
    await orchestrator.user_message(project_id, text)
    return None
```

Replace the `load_project` handler body:

```python
@sio.event
async def load_project(sid: str, data: dict[str, Any]) -> dict | None:
    project_id = (data or {}).get("project_id", "")
    if not project_id:
        return {"error": "project_id required"}
    room = f"project:{project_id}"
    await sio.enter_room(sid, room)
    snap = await orchestrator.load(project_id)
    if snap is None:
        return {"error": "project not found"}
    await sio.emit("project_state", snap, to=sid)
    return None
```

- [ ] **Step 5: Run the approval-flow test**

Run: `uv run -- python -m pytest tests/integration/test_approval_flow.py -q`
Expected: `1 passed`. If the LangGraph interrupt integration is tricky, iterate on the driver loop and `approval_node` until the test passes. This is the highest-risk task in the plan.

- [ ] **Step 6: Run the full backend suite**

Run: `uv run -- python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/orchestrator.py backend/main.py tests/integration/test_approval_flow.py
git commit -m "feat: approval gate with interrupt + Command(resume=...) wiring and socket handlers"
```

---

### Task 5.3: Rejection cycle and escalation test

**Files:**
- Modify: `backend/orchestrator.py` (in `clarifying_node`, incorporate rejection feedback)
- Create: `tests/integration/test_rejection_cycle.py`

- [ ] **Step 1: Update `clarifying_node` to read rejection feedback**

In `backend/orchestrator.py` `clarifying_node`, when `state.approval_status == "rejected"` or `"modified"`, pass the latest rejection comment (stored in a new `state.rejection_comments` list or similar) to the agent as extra context. Extend `ProjectState` in `backend/graph.py` with:

```python
rejection_comments: list[str] = Field(default_factory=list)
```

In the approval node, when the decision is reject/modify with a comment, append it to `rejection_comments` in the returned state update.

In `clarifying_node`, pass `rejection_comments=state.rejection_comments` into the agent task dict. Extend the mock agent's behavior so that when `rejection_comments` is non-empty, it emits a revised PRD on the next call.

- [ ] **Step 2: Write the test**

Create `tests/integration/test_rejection_cycle.py`:

```python
"""Reject twice, verify escalation flag on third rejection."""
import asyncio

import pytest

from backend.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_three_rejections_escalate(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "chk.db"))
    received: list = []

    async def emit(event, data, room):
        received.append((event, data))

    orch = Orchestrator()
    await orch.run("proj-reject", "idea", emit)

    async def wait_for(event_name: str, predicate=lambda d: True, timeout: float = 3.0):
        for _ in range(int(timeout / 0.05)):
            await asyncio.sleep(0.05)
            if any(e[0] == event_name and predicate(e[1]) for e in received):
                return True
        return False

    # Drive through clarifying -> approval (mock asks 3 questions then emits PRD)
    for _ in range(3):
        await wait_for("agent_message")
        await orch.user_message("proj-reject", "answer")
    await wait_for("approval_required")

    # First rejection
    received.clear()
    await orch.reject("proj-reject", "not enough detail")
    await wait_for("approval_required")

    # Second rejection
    received.clear()
    await orch.reject("proj-reject", "still not enough")
    await wait_for("approval_required")

    # Third rejection -> should surface escalation flag
    received.clear()
    await orch.reject("proj-reject", "nope")
    await wait_for("approval_required")
    escalation_events = [e for e in received if e[0] == "approval_required" and e[1].get("escalation")]
    assert escalation_events, "third rejection should emit escalation=true"
```

- [ ] **Step 3: Run — expect initial failure, iterate**

Run: `uv run -- python -m pytest tests/integration/test_rejection_cycle.py -q`

If the mock doesn't revise its PRD on re-entry, update the mock in Task 3.4's spot to return a modified PRD when `rejection_comments` is non-empty. Rerun until green.

- [ ] **Step 4: Commit**

```bash
git add backend/graph.py backend/orchestrator.py backend/agents/mock_agent.py tests/integration/test_rejection_cycle.py
git commit -m "feat: thread rejection comments back to clarifying_pm; escalate on 3rd"
```

---

### Task 5.4: Frontend approval card + slash commands

**Files:**
- Modify: `frontend/src/components/ChatInterface.tsx`
- Modify: `frontend/src/components/ChatInterface.test.tsx`

- [ ] **Step 1: Extend tests for the approval card**

Append to `frontend/src/components/ChatInterface.test.tsx`:

```tsx
test("shows approval card when approvalPending is set", () => {
  useProjectStore.getState().setApprovalPending({
    agent: "product_owner", phase: 3, content: "# PRD",
  });
  render(<ChatInterface />);
  expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /modify/i })).toBeInTheDocument();
});

test("clicking Approve emits approve event", () => {
  useProjectStore.getState().setApprovalPending({
    agent: "product_owner", phase: 3, content: "# PRD",
  });
  render(<ChatInterface />);
  fireEvent.click(screen.getByRole("button", { name: /approve/i }));
  expect(emit).toHaveBeenCalledWith("approve", {
    project_id: "proj-1",
    comment: undefined,
  });
});

test("slash command /approve in input emits approve", () => {
  useProjectStore.getState().setApprovalPending({
    agent: "product_owner", phase: 3, content: "# PRD",
  });
  render(<ChatInterface />);
  const input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "/approve" } });
  fireEvent.submit(input.closest("form")!);
  expect(emit).toHaveBeenCalledWith("approve", {
    project_id: "proj-1",
    comment: undefined,
  });
});
```

- [ ] **Step 2: Update `ChatInterface.tsx`**

Replace the relevant parts of `frontend/src/components/ChatInterface.tsx` to include the approval card and slash command parsing:

```tsx
import { useState } from "react";

import { useSocket } from "../hooks/useSocket";
import { useProjectStore } from "../stores/projectStore";
import { PRDViewer } from "./PRDViewer";

function parseCommand(text: string): { cmd: string; arg?: string } | null {
  if (!text.startsWith("/")) return null;
  const space = text.indexOf(" ");
  if (space === -1) return { cmd: text.slice(1) };
  return { cmd: text.slice(1, space), arg: text.slice(space + 1).trim() };
}

export function ChatInterface() {
  const { sendMessage, approve, reject, modify, retry } = useSocket();
  const messages = useProjectStore((s) => s.messages);
  const prd = useProjectStore((s) => s.prd);
  const approvalPending = useProjectStore((s) => s.approvalPending);
  const [draft, setDraft] = useState("");
  const [modifyDraft, setModifyDraft] = useState("");
  const [showModify, setShowModify] = useState(false);

  const submit = (text: string) => {
    const cmd = parseCommand(text);
    if (cmd) {
      if (cmd.cmd === "approve") return approve(cmd.arg);
      if (cmd.cmd === "reject") return reject(cmd.arg);
      if (cmd.cmd === "modify" && cmd.arg) return modify(cmd.arg);
      if (cmd.cmd === "retry") return retry();
    }
    useProjectStore.getState().addMessage({
      id: `${Date.now()}-user`, role: "user", text, timestamp: Date.now(),
    });
    sendMessage(text);
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    submit(text);
    setDraft("");
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                m.role === "user" ? "bg-blue-500 text-white"
                : m.role === "system" ? "bg-gray-200 text-gray-700 italic"
                : "bg-white border"
              }`}
            >
              {m.agent && <div className="text-xs font-semibold mb-1">{m.agent}</div>}
              <div className="whitespace-pre-wrap">{m.text}</div>
            </div>
          </div>
        ))}
        {prd && (
          <div>
            <div className="text-xs font-semibold mb-1 text-gray-500">Draft PRD</div>
            <PRDViewer markdown={prd} />
          </div>
        )}
        {approvalPending && (
          <div className="bg-yellow-50 border border-yellow-300 rounded p-3 space-y-2">
            <div className="font-semibold text-sm">Approval needed</div>
            {approvalPending.escalation && (
              <div className="text-xs text-red-700">Escalation: 3 rejections so far.</div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => approve()}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded"
              >
                Approve
              </button>
              <button
                type="button"
                onClick={() => reject()}
                className="px-3 py-1 bg-red-600 text-white text-sm rounded"
              >
                Reject
              </button>
              <button
                type="button"
                onClick={() => setShowModify((v) => !v)}
                className="px-3 py-1 bg-blue-600 text-white text-sm rounded"
              >
                Modify
              </button>
            </div>
            {showModify && (
              <div className="flex gap-2">
                <input
                  type="text"
                  className="flex-1 border rounded px-2 py-1 text-sm"
                  placeholder="What should be changed?"
                  value={modifyDraft}
                  onChange={(e) => setModifyDraft(e.target.value)}
                />
                <button
                  type="button"
                  className="px-3 py-1 bg-blue-700 text-white text-sm rounded"
                  onClick={() => {
                    if (modifyDraft.trim()) {
                      modify(modifyDraft.trim());
                      setModifyDraft("");
                      setShowModify(false);
                    }
                  }}
                >
                  Send
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      <form onSubmit={onSubmit} className="border-t p-3 flex gap-2 bg-white">
        <input
          type="text"
          role="textbox"
          className="flex-1 border rounded px-3 py-2 text-sm"
          placeholder="Describe your idea, answer a question, or type /approve /reject /modify ..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          Send
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npm test && cd ..`
Expected: all tests pass including the 3 new ones.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ChatInterface.tsx frontend/src/components/ChatInterface.test.tsx
git commit -m "feat(frontend): approval card + slash commands in ChatInterface"
```

---

### Task 5.5: E2E test — full Phase 3 happy path

**Files:**
- Create: `tests/e2e/test_phase3_demo.py`

- [ ] **Step 1: Write the E2E test**

Create `tests/e2e/test_phase3_demo.py`:

```python
"""End-to-end test of the Phase 3 milestone via Socket.IO client."""
import asyncio

import pytest
import socketio
import uvicorn


@pytest.mark.asyncio
async def test_phase3_happy_path(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "e2e.db"))

    from backend.main import asgi_app
    server = uvicorn.Server(uvicorn.Config(asgi_app, host="127.0.0.1", port=8767, log_level="warning"))
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)

    client = socketio.AsyncClient()
    events: list = []
    for ev in ("project_created", "agent_status", "agent_message",
               "approval_required", "phase_complete", "project_state"):
        def make(name):
            def h(data):
                events.append((name, data))
            return h
        client.on(ev, make(ev))

    await client.connect("http://127.0.0.1:8767", socketio_path="/socket.io")

    try:
        await client.emit("start_project", {"idea": "build a pomodoro timer"})
        async def wait_for(name: str, timeout=5.0) -> dict:
            for _ in range(int(timeout / 0.05)):
                await asyncio.sleep(0.05)
                for e in events:
                    if e[0] == name:
                        return e[1]
            raise AssertionError(f"timed out waiting for {name}")

        created = await wait_for("project_created")
        project_id = created["project_id"]

        # Feed 3 answers to trigger the mock's PRD
        for _ in range(3):
            await wait_for("agent_message")
            await client.emit("user_message", {"project_id": project_id, "text": "ok"})
            # drain
            events[:] = [e for e in events if e[0] != "agent_message"]

        await wait_for("approval_required")
        await client.emit("approve", {"project_id": project_id})
        phase = await wait_for("phase_complete", timeout=5.0)
        assert phase.get("status") == "success"
        assert phase.get("phase") == 3
    finally:
        await client.disconnect()
        server.should_exit = True
        await task
```

- [ ] **Step 2: Run — must pass**

Run: `uv run -- python -m pytest tests/e2e/test_phase3_demo.py -q`
Expected: `1 passed`.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_phase3_demo.py
git commit -m "test(e2e): full Phase 3 happy path via Socket.IO client"
```

---

### Task 5.6: Archive `gauntlite/` and integrate PRD rubric

**Files:**
- Create: `docs/prd-rubric.md`
- Modify: `prompts/v1/clarifying_pm.jinja` (merge rubric details)
- Delete: `gauntlite/`

- [ ] **Step 1: Create `research/gauntlite-archive` branch from the current commit**

Run:
```bash
git checkout -b research/gauntlite-archive
git checkout feat/alignment-phase3-mvp
```

This preserves the `gauntlite/` contents on a separate branch.

- [ ] **Step 2: Extract the PRD rubric content**

Open `gauntlite/Phase-3-PRD-Rubric-v1.md`. Distill its PRD-quality rubric into `docs/prd-rubric.md`:

```markdown
# PRD Rubric (Phase 3)

The Clarifying PM agent produces PRDs that must satisfy this rubric.

## Required sections
1. **Problem statement** — one sentence grounded in a concrete user need.
2. **Primary user** and their goal.
3. **Success metric** — quantitative where possible.
4. **Acceptance criteria** — 3 to 7 items, phrased as "Given / When / Then" or "The system shall...".
5. **Non-goals** — explicitly out of scope.
6. **MVP scope** — what is IN and what is OUT for the first shippable version.

## Quality heuristics
- Every acceptance criterion is testable by an independent reader.
- No technology choices (framework, language, database) unless the user specified them.
- No deployment or team-structure details.
- Problem statement avoids solutioning ("we need a todo app" → fail; "remote engineers lose track of daily tasks" → pass).

(Derived from gauntlite/Phase-3-PRD-Rubric-v1.md, archived on branch research/gauntlite-archive.)
```

If the original rubric contains materially richer detail than captured above, expand `docs/prd-rubric.md` until it is comprehensive enough that a reviewer could grade any PRD against it.

- [ ] **Step 3: Merge rubric references into the Jinja prompt**

In `prompts/v1/clarifying_pm.jinja`, the rubric section is already present from Task 4.2. Augment it with any quality heuristics from `docs/prd-rubric.md` that aren't already there. Keep the prompt under 2KB.

- [ ] **Step 4: Delete `gauntlite/` from the feature branch**

Run:
```bash
git rm -r gauntlite
```

- [ ] **Step 5: Run full tests to ensure nothing broke**

Run: `uv run -- python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add docs/prd-rubric.md prompts/v1/clarifying_pm.jinja
git commit -m "docs: extract Phase 3 PRD rubric from gauntlite/ into docs/prd-rubric.md"
git commit -m "chore: remove gauntlite/ from main branch (archived on research/gauntlite-archive)" --only
```

(If the rm and rubric changes are in separate staging, commit twice as shown. Otherwise combine into one commit with message `"docs: extract PRD rubric; remove gauntlite/ (archived on research/gauntlite-archive)"`.)

---

### Task 5.7: Update `CLAUDE.md` and `README.md` to reflect reality

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update `CLAUDE.md`**

Open `CLAUDE.md`. Change these:

- **File Structure section**: replace the `ui/` React subtree with `frontend/`. Remove mentions of `main.py` at the top level (now `backend/main.py`). Replace `ui/src/` with `frontend/src/`.
- **Tech Stack section**: remove "Streamlit" from any list. Keep FastAPI + Socket.IO + LangGraph + CrewAI* (*note CrewAI isn't currently used; keep the doc-level mention honest by removing it or marking as "planned").
- **Current State (Phase 1-2) section**: update to reflect Phase 2 verified and Phase 3 MVP in progress / complete after this sub-project lands.
- **Development Workflow section**: update run commands to `uv run -- python -m backend.main` and `cd frontend && npm run dev`.
- **Environment Variables section**: add `SQLITE_PATH`, `ANTHROPIC_MODEL`, `MAX_CLARIFYING_QUESTIONS`. Remove `REDIS_URL` unless Redis comes back in a later phase (it's not used now).
- **Key Files and Their Purpose** section: replace `main.py`, `config.py`, `agents/registry.py` descriptions with `backend/main.py`, `backend/config.py`, `backend/agents/registry.py`, and add `backend/orchestrator.py`, `backend/prompt_loader.py`, `backend/agents/clarifying_pm.py`.

- [ ] **Step 2: Update `README.md`**

Ensure the run instructions (from Task 1.9 Step 2) are still accurate. Add a pointer to `docs/superpowers/specs/2026-04-21-alignment-phase3-mvp-design.md` and `docs/superpowers/plans/2026-04-21-alignment-phase3-mvp.md` under a "Design docs" heading if none exists.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: align CLAUDE.md and README with FastAPI+React reality"
```

---

### Task 5.8: Coverage gate and final verification

**Files:**
- Modify: `pyproject.toml` (coverage config)

- [ ] **Step 1: Add coverage configuration**

In `pyproject.toml`, append (or create) the coverage sections:

```toml
[tool.coverage.run]
source = ["backend"]
branch = true
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 70
skip_empty = true
show_missing = true
```

- [ ] **Step 2: Run coverage**

Run: `uv run -- python -m pytest tests/ --cov=backend --cov-report=term`
Expected: coverage ≥ 70%. If lower, identify uncovered modules in the report and add targeted tests until the gate passes.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: enforce 70% backend coverage gate"
```

---

### Task 5.9: Slice 5 final manual smoke — all success criteria

**Files:** None modified; this is the acceptance checklist.

Run through every success criterion from the spec:

- [ ] 1. Start backend: `uv run -- python -m backend.main`. Zero errors.
- [ ] 2. Start frontend: `cd frontend && npm run dev`. Zero errors.
- [ ] 3. Open `http://localhost:5173/`, submit "Build me a todo app". Answer questions. PRD renders with approval card.
- [ ] 4. Click Approve. "Phase 3 complete" message appears. No further questions.
- [ ] 5. Close browser. Reopen `http://localhost:5173/project/<id>` (id from the URL you saw earlier). State fully restored.
- [ ] 6. With a fresh project, reach the approval card, click Reject with a comment. Clarifying PM produces a revised PRD.
- [ ] 7. `uv run -- python -m pytest tests/` passes and reports ≥70% coverage.
- [ ] 8. `cd frontend && npm test` passes.
- [ ] 9. `grep -r streamlit backend/ frontend/ tests/ prompts/ config/ docs/ --include="*.py" --include="*.ts" --include="*.tsx"` returns nothing (outside git history).
- [ ] 10. `CLAUDE.md` and `README.md` describe FastAPI + React + Anthropic; nothing describes Streamlit.

If any step fails, open a follow-up commit or task before declaring the sub-project done.

- [ ] **Step 1: If all criteria pass, push the branch and open a PR**

Run:
```bash
git push -u origin feat/alignment-phase3-mvp
```

Open a PR on GitHub titled "Sub-Project #1: Alignment + Phase 3 MVP" with body:

```markdown
## Summary
- Replaces Streamlit with FastAPI + Socket.IO backend and React + Vite frontend
- Real Anthropic Claude Sonnet 4.6 call for Clarifying PM (with mock fallback via MOCK_AGENTS=true)
- SQLite checkpoints for session resume
- Approval gate with approve/reject/modify/retry + slash commands
- Deletes stale SetupInstructions.md; archives gauntlite/ to research branch; integrates PRD rubric

## Test plan
- [ ] `uv run -- python -m pytest tests/ --cov=backend` passes with ≥70%
- [ ] `cd frontend && npm test` passes
- [ ] Manual: start servers, submit idea, complete clarification, approve, reload URL to resume
- [ ] Manual: reject twice, third rejection shows escalation

See design spec: `docs/superpowers/specs/2026-04-21-alignment-phase3-mvp-design.md`
```

---

## Self-review (run this before declaring the plan done)

(Performed by plan author in-session, not by the implementing engineer.)

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| FastAPI + Socket.IO backend on :8000 | 1.7, 1.8 |
| React + Vite + Zustand + React Flow frontend on :5173 | 2.1–2.10 |
| Clarifying PM with real Anthropic ChatAnthropic | 4.3 |
| Jinja2 prompt loading | 4.1, 4.2 |
| Pydantic ClarifyingResponse structured output | 4.3 |
| 6-question cap with synthesis | 4.3 (`test_synthesizes_prd_at_max_questions`) |
| Malformed JSON retry once | 4.3 (`test_retries_once_on_malformed_json`) |
| SQLite persistence | 5.1 |
| URL-based project resume | 5.2 (load handler), 2.10 (route) |
| Approval gate (approve / reject / modify) | 5.2, 5.4 |
| Slash commands in chat | 5.4 |
| Retry button for recoverable errors | 5.2 (retry handler), 5.4 (UI) |
| Rejection routes back to clarifying_pm | 5.3 |
| 3rd rejection emits escalation flag | 5.3 |
| BudgetGuard integration | 4.4 |
| MOCK_AGENTS fallback | 4.5 |
| Startup checks (local only, no API ping) | 1.6, 1.7 |
| Delete app.py | 1.9 |
| Delete SetupInstructions.md | 1.9 |
| Remove streamlit / crewai / mem0ai / gitpython | 1.5 |
| Move to backend/ package | 1.2, 1.3 |
| Move tests to tests/unit | 1.4 |
| Add tests/integration and tests/e2e | 1.1 + throughout |
| Archive gauntlite/ to research/gauntlite-archive | 5.6 |
| Merge PRD rubric into docs/prd-rubric.md | 5.6 |
| Update CLAUDE.md | 5.7 |
| Update README.md | 1.9, 5.7 |
| 70% backend coverage gate | 5.8 |

**Placeholders:** None. The `retry` implementation in Task 5.2 is now complete (load last snapshot, re-invoke `run`). Every task has concrete code or commands.

**Type consistency:** `ProjectState` fields defined in Task 3.1 are referenced consistently in Tasks 3.2, 4.3, 5.1, 5.2, 5.3. `ClarifyingResponse` defined in Task 4.3 is used only there. Socket.IO event payload shapes match between `frontend/src/types/index.ts` (Task 2.3), `backend/main.py` handlers (Tasks 3.3, 5.2), and test fixtures.

**Scope:** 5 slices, ~30 tasks. Bite-sized steps throughout. One sub-project, one coherent goal. No decomposition needed.
