"""Marquee proof: independent worker PROCESSES claim + execute a pool of ready
tasks with NO collision. A synthetic single phase with M independent agents
(real agent ids, so they resolve to mocks via the registry) is drained by N
real OS worker subprocesses; we then inspect the persisted SQLite DB directly
and assert exactly-once, collision-free effect.
"""

import os
import sqlite3

import pytest

from backend.engine.run import run_pipeline

# 12 real non-clarify phase-worker agents — all resolve to mocks in MOCK mode.
# (clarifying_pm is excluded: the adapter special-cases it into a Q&A loop.)
STRESS_AGENTS = [
    "solution_architect",
    "tech_lead",
    "uiux_designer",
    "frontend",
    "backend",
    "database",
    "ai_ml",
    "qa_test",
    "security",
    "devops",
    "technical_writer",
    "delivery_summarizer",
]
M = len(STRESS_AGENTS)  # 12 independent ready tasks
N = 8  # real worker subprocesses racing to claim them


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    yield


def _write_stress_phases(path, agents):
    lines = [
        "phases:",
        "  - name: stress",
        "    order: 0",
        "    gate: none",
        "    agents:",
    ]
    for a in agents:
        lines.append(
            f"      {a}: {{ reads: [], writes: out_{a}, sim_cost: 0.0, depends_on: [] }}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def test_no_collision_under_real_process_contention(tmp_path, monkeypatch):
    phases = tmp_path / "stress.yaml"
    _write_stress_phases(phases, STRESS_AGENTS)
    monkeypatch.setenv("APPFORGE_PHASES", str(phases))
    db = str(tmp_path / "stress.db")

    result = await run_pipeline(
        "stress", workers=N, budget_limit=1000.0, db_path=db, timeout=120.0
    )
    assert result["snapshot"]["status"] == "done"
    assert len(set(result["worker_pids"])) == N  # N distinct real OS processes

    # Inspect the persisted DB directly: exactly-once, collision-free effect.
    conn = sqlite3.connect(db)
    try:
        done = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='done'"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        distinct = conn.execute("SELECT COUNT(DISTINCT task_id) FROM tasks").fetchone()[
            0
        ]
        spend_rows = conn.execute("SELECT COUNT(*) FROM spend").fetchone()[0]
        state_rows = conn.execute("SELECT COUNT(*) FROM state").fetchone()[0]
    finally:
        conn.close()

    assert done == M and total == M and distinct == M  # every task ran, none duplicated
    assert (
        spend_rows == M
    )  # exactly one completion recorded per task (no double-complete)
    assert state_rows == M  # each agent wrote its one disjoint key exactly once
