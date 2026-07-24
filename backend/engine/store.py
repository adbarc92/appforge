"""Single-writer SQLite store for the engine. All mutations under _db_lock."""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

from backend.engine import scheduler as sch
from backend.engine.models import SCHEMA_SQL
from backend.engine.phases import PhasesConfig


class Store:
    def __init__(self, db_path: str, cfg: PhasesConfig, base_models: dict[str, str], lease_s: float = 120.0):
        self.db_path = db_path
        self.cfg = cfg
        self.base_models = base_models
        self.lease_s = lease_s
        self._db: aiosqlite.Connection | None = None
        self._db_lock = asyncio.Lock()

    def _now(self) -> float:
        return time.time()

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.executescript(SCHEMA_SQL)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    @asynccontextmanager
    async def _txn(self):
        """Commit on success, rollback on any exception. Caller must already hold _db_lock."""
        try:
            yield
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise

    async def create_run(self, run_id: str, idea: str, budget_limit: float) -> None:
        async with self._db_lock:
            async with self._txn():
                now = self._now()
                await self._db.execute(
                    "INSERT INTO runs (run_id, idea, budget_limit, created_at) VALUES (?,?,?,?)",
                    (run_id, idea, budget_limit, now),
                )
                for name in self.cfg.phase_names:
                    order = self.cfg.order_of(name)
                    status = "open" if name == "clarify" else "blocked"
                    await self._db.execute(
                        "INSERT INTO phases (run_id, name, phase_order, status, gate, seeded) VALUES (?,?,?,?,?,0)",
                        (run_id, name, order, status, self.cfg.gate_of(name)),
                    )
                await self._seed_phase_locked(run_id, "clarify", now)
                await self._recompute_ready_locked(run_id)

    async def _seed_phase_locked(self, run_id: str, phase_name: str, now: float) -> None:
        specs = sch.seed_specs_for_phase(self.cfg, run_id, phase_name, self.base_models)
        for s in specs:
            await self._db.execute(
                """INSERT OR IGNORE INTO tasks
                   (task_id, run_id, phase, phase_order, agent_id, input, depends_on,
                    status, version, attempts, created_at, model, sim_cost)
                   VALUES (?,?,?,?,?,?,?,'blocked',0,0,?,?,?)""",
                (s["task_id"], run_id, s["phase"], s["phase_order"], s["agent_id"],
                 json.dumps({"input_keys": s["input_keys"]}), json.dumps(s["depends_on"]),
                 now, s["model"], s["sim_cost"]),
            )
        await self._db.execute(
            "UPDATE phases SET seeded=1 WHERE run_id=? AND name=?", (run_id, phase_name)
        )

    async def _recompute_ready_locked(self, run_id: str) -> None:
        tasks = await self._all_tasks(run_id)
        phases = await self._all_phases(run_id)
        ready_ids = sch.compute_ready(tasks, phases)
        for tid in ready_ids:
            await self._db.execute(
                "UPDATE tasks SET status='ready' WHERE task_id=? AND status='blocked'", (tid,)
            )

    async def _all_tasks(self, run_id: str) -> list[dict[str, Any]]:
        cur = await self._db.execute("SELECT * FROM tasks WHERE run_id=?", (run_id,))
        rows = await cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["depends_on"] = json.loads(d["depends_on"])
            out.append(d)
        return out

    async def _all_phases(self, run_id: str) -> list[dict[str, Any]]:
        cur = await self._db.execute("SELECT * FROM phases WHERE run_id=?", (run_id,))
        return [dict(r) for r in await cur.fetchall()]

    async def get_state(self, run_id: str, keys: list[str] | None = None) -> dict[str, tuple[Any, int]]:
        if keys:
            q = "SELECT key, value, version FROM state WHERE run_id=? AND key IN (%s)" % ",".join("?" * len(keys))
            cur = await self._db.execute(q, (run_id, *keys))
        else:
            cur = await self._db.execute("SELECT key, value, version FROM state WHERE run_id=?", (run_id,))
        return {r["key"]: (json.loads(r["value"]), r["version"]) for r in await cur.fetchall()}

    async def put_state(self, run_id: str, key: str, value: Any, expected_version: int) -> bool:
        async with self._db_lock:
            async with self._txn():
                if expected_version == 0:
                    cur = await self._db.execute(
                        "INSERT OR IGNORE INTO state (run_id, key, value, version) VALUES (?,?,?,1)",
                        (run_id, key, json.dumps(value)),
                    )
                    result = cur.rowcount == 1
                else:
                    cur = await self._db.execute(
                        "UPDATE state SET value=?, version=version+1 WHERE run_id=? AND key=? AND version=?",
                        (json.dumps(value), run_id, key, expected_version),
                    )
                    result = cur.rowcount == 1
            return result
