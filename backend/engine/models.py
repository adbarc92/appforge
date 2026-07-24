"""SQL schema + typed result models for the engine store."""
from __future__ import annotations

from pydantic import BaseModel

PHASE_STATUS = {"blocked", "open", "complete"}
TASK_STATUS = {"blocked", "ready", "claimed", "running", "done", "failed"}
GATE = {"none", "pending", "approved", "rejected"}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  idea TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  current_phase INTEGER NOT NULL DEFAULT 0,
  budget_limit REAL NOT NULL DEFAULT 200.0,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS phases (
  run_id TEXT NOT NULL,
  name TEXT NOT NULL,
  phase_order INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'blocked',
  gate TEXT NOT NULL DEFAULT 'none',
  seeded INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (run_id, name)
);
CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  phase TEXT NOT NULL,
  phase_order INTEGER NOT NULL,
  agent_id TEXT NOT NULL,
  input TEXT NOT NULL DEFAULT '{}',
  depends_on TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'blocked',
  owner TEXT,
  version INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0,
  lease_expires REAL,
  created_at REAL NOT NULL,
  claimed_at REAL,
  model TEXT,
  sim_cost REAL NOT NULL DEFAULT 0.0,
  result TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_ready ON tasks (run_id, status, phase_order, created_at);
CREATE TABLE IF NOT EXISTS state (
  run_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (run_id, key)
);
CREATE TABLE IF NOT EXISTS spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  task_id TEXT,
  agent_id TEXT,
  cost REAL NOT NULL,
  model TEXT,
  ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  type TEXT NOT NULL,
  payload TEXT NOT NULL,
  worker_pid INTEGER,
  ts REAL NOT NULL
);
"""


class ClaimResult(BaseModel):
    task_id: str
    run_id: str
    phase: str
    phase_order: int
    agent_id: str
    input: dict
    model: str | None
    version: int
