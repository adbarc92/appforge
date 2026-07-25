"""Single-writer SQLite store for the engine. All mutations under _db_lock."""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

from backend.engine import scheduler as sch
from backend.engine.models import SCHEMA_SQL, ClaimResult
from backend.engine.phases import PhasesConfig


class Store:
    MAX_ATTEMPTS = 3

    def __init__(
        self,
        db_path: str,
        cfg: PhasesConfig,
        base_models: dict[str, str],
        lease_s: float = 120.0,
        downgrade_paths: dict[str, str] | None = None,
    ):
        self.db_path = db_path
        self.cfg = cfg
        self.base_models = base_models
        self.lease_s = lease_s
        self.downgrade_paths = downgrade_paths or {}
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
        entry = self.cfg.phase_names[0]  # order-0 phase (phase_names is order-sorted)
        async with self._db_lock, self._txn():
            now = self._now()
            await self._db.execute(
                "INSERT INTO runs (run_id, idea, budget_limit, created_at) VALUES (?,?,?,?)",
                (run_id, idea, budget_limit, now),
            )
            for name in self.cfg.phase_names:
                order = self.cfg.order_of(name)
                status = "open" if name == entry else "blocked"
                await self._db.execute(
                    "INSERT INTO phases (run_id, name, phase_order, status, gate, seeded) VALUES (?,?,?,?,?,0)",
                    (run_id, name, order, status, self.cfg.gate_of(name)),
                )
            await self._seed_phase_locked(run_id, entry, now)
            await self._recompute_ready_locked(run_id)

    async def _seed_phase_locked(
        self, run_id: str, phase_name: str, now: float
    ) -> None:
        specs = sch.seed_specs_for_phase(self.cfg, run_id, phase_name, self.base_models)
        for s in specs:
            await self._db.execute(
                """INSERT OR IGNORE INTO tasks
                   (task_id, run_id, phase, phase_order, agent_id, input, depends_on,
                    status, version, attempts, created_at, model, sim_cost)
                   VALUES (?,?,?,?,?,?,?,'blocked',0,0,?,?,?)""",
                (
                    s["task_id"],
                    run_id,
                    s["phase"],
                    s["phase_order"],
                    s["agent_id"],
                    json.dumps({"input_keys": s["input_keys"]}),
                    json.dumps(s["depends_on"]),
                    now,
                    s["model"],
                    s["sim_cost"],
                ),
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
                "UPDATE tasks SET status='ready' WHERE task_id=? AND status='blocked'",
                (tid,),
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

    async def get_state(
        self, run_id: str, keys: list[str] | None = None
    ) -> dict[str, tuple[Any, int]]:
        if keys:
            placeholders = ",".join("?" * len(keys))
            q = f"SELECT key, value, version FROM state WHERE run_id=? AND key IN ({placeholders})"
            cur = await self._db.execute(q, (run_id, *keys))
        else:
            cur = await self._db.execute(
                "SELECT key, value, version FROM state WHERE run_id=?", (run_id,)
            )
        return {
            r["key"]: (json.loads(r["value"]), r["version"])
            for r in await cur.fetchall()
        }

    async def put_state(
        self, run_id: str, key: str, value: Any, expected_version: int
    ) -> bool:
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

    async def _spend_ratio_locked(self, run_id: str) -> float:
        cur = await self._db.execute(
            "SELECT budget_limit FROM runs WHERE run_id=?", (run_id,)
        )
        row = await cur.fetchone()
        limit = row["budget_limit"] if row else 0.0
        cur = await self._db.execute(
            "SELECT COALESCE(SUM(cost),0) AS s FROM spend WHERE run_id=?", (run_id,)
        )
        spent = (await cur.fetchone())["s"]
        return (spent / limit) if limit > 0 else 1.0

    async def _downgrade_config(self) -> tuple[dict[str, str], set[str]]:
        return (self.downgrade_paths, {"clarifying_pm", "solution_architect"})

    async def claim_next_task(self, run_id: str, worker_id: str) -> ClaimResult | None:
        async with self._db_lock:
            async with self._txn():
                now = self._now()
                cur = await self._db.execute(
                    """UPDATE tasks
                       SET status='claimed', owner=?, version=version+1, claimed_at=?, lease_expires=?
                       WHERE task_id = (
                           SELECT task_id FROM tasks
                           WHERE run_id=? AND status='ready'
                           ORDER BY phase_order, created_at LIMIT 1)
                         AND status='ready'
                       RETURNING task_id, run_id, phase, phase_order, agent_id, input, model, version""",
                    (worker_id, now, now + self.lease_s, run_id),
                )
                row = await cur.fetchone()
                if row is None:
                    result = None
                else:
                    ratio = await self._spend_ratio_locked(run_id)
                    paths, skip = await self._downgrade_config()
                    model = sch.resolve_model(
                        row["agent_id"], row["model"], ratio, paths, skip
                    )
                    if model != row["model"]:
                        await self._db.execute(
                            "UPDATE tasks SET model=? WHERE task_id=?",
                            (model, row["task_id"]),
                        )
                    input_keys = json.loads(row["input"]).get("input_keys", [])
                    state = (
                        await self.get_state(run_id, input_keys) if input_keys else {}
                    )
                    resolved_input = {k: v[0] for k, v in state.items()}
                    result = ClaimResult(
                        task_id=row["task_id"],
                        run_id=row["run_id"],
                        phase=row["phase"],
                        phase_order=row["phase_order"],
                        agent_id=row["agent_id"],
                        input=resolved_input,
                        model=model,
                        version=row["version"],
                    )
            return result

    async def heartbeat(self, task_id: str, worker_id: str) -> bool:
        async with self._db_lock:
            async with self._txn():
                cur = await self._db.execute(
                    """UPDATE tasks SET lease_expires=?
                       WHERE task_id=? AND owner=? AND status IN ('claimed','running')""",
                    (self._now() + self.lease_s, task_id, worker_id),
                )
                rowcount = cur.rowcount
            return rowcount == 1

    async def reap_expired(self) -> int:
        async with self._db_lock:
            async with self._txn():
                cur = await self._db.execute(
                    """UPDATE tasks
                       SET status='ready', owner=NULL, version=version+1, attempts=attempts+1, lease_expires=NULL
                       WHERE status IN ('claimed','running') AND lease_expires IS NOT NULL AND lease_expires < ?""",
                    (self._now(),),
                )
                rowcount = cur.rowcount
            return rowcount

    async def spend_total(self, run_id: str) -> float:
        cur = await self._db.execute(
            "SELECT COALESCE(SUM(cost),0) AS s FROM spend WHERE run_id=?", (run_id,)
        )
        return (await cur.fetchone())["s"]

    async def _advance_locked(self, run_id: str) -> None:
        now = self._now()
        plan = sch.advance(
            await self._all_phases(run_id), await self._all_tasks(run_id), self.cfg
        )
        # gate-pending is derived below via cfg.gate_of; plan["open_gates"] is intentionally unused here.
        for name in plan["complete_phases"]:
            await self._db.execute(
                "UPDATE phases SET status='complete' WHERE run_id=? AND name=?",
                (run_id, name),
            )
            if self.cfg.gate_of(name) != "none":
                await self._db.execute(
                    "UPDATE phases SET gate='pending' WHERE run_id=? AND name=?",
                    (run_id, name),
                )
        for name in plan["open_phases"]:
            await self._db.execute(
                "UPDATE phases SET status='open' WHERE run_id=? AND name=?",
                (run_id, name),
            )
            await self._seed_phase_locked(run_id, name, now)
        await self._recompute_ready_locked(run_id)

    async def complete_task(
        self,
        task_id,
        worker_id,
        version,
        result,
        state_writes=None,
        spawn_tasks=None,  # noqa: ARG002
    ) -> bool:
        async with self._db_lock:
            async with self._txn():
                cur = await self._db.execute(
                    "UPDATE tasks SET status='done', result=? WHERE task_id=? AND owner=? AND version=? AND status IN ('claimed','running')",
                    (json.dumps(result), task_id, worker_id, version),
                )
                if cur.rowcount != 1:
                    ok = False
                else:
                    trow = await (
                        await self._db.execute(
                            "SELECT run_id, agent_id, model, sim_cost FROM tasks WHERE task_id=?",
                            (task_id,),
                        )
                    ).fetchone()
                    run_id = trow["run_id"]
                    for k, v in (state_writes or {}).items():
                        await self._db.execute(
                            "INSERT INTO state (run_id, key, value, version) VALUES (?,?,?,1) "
                            "ON CONFLICT(run_id, key) DO UPDATE SET value=excluded.value, version=state.version+1",
                            (run_id, k, json.dumps(v)),
                        )
                    await self._db.execute(
                        "INSERT INTO spend (run_id, task_id, agent_id, cost, model, ts) VALUES (?,?,?,?,?,?)",
                        (
                            run_id,
                            task_id,
                            trow["agent_id"],
                            trow["sim_cost"],
                            trow["model"],
                            self._now(),
                        ),
                    )
                    await self._advance_locked(run_id)
                    ok = True
            return ok

    async def fail_task(
        self, task_id, worker_id, version, error  # noqa: ARG002
    ) -> None:
        async with self._db_lock, self._txn():
            trow = await (
                await self._db.execute(
                    "SELECT run_id, attempts FROM tasks WHERE task_id=? AND owner=? AND version=? AND status IN ('claimed','running')",
                    (task_id, worker_id, version),
                )
            ).fetchone()
            if trow is not None:
                attempts = trow["attempts"] + 1
                if attempts >= self.MAX_ATTEMPTS:
                    await self._db.execute(
                        "UPDATE tasks SET status='failed', attempts=? WHERE task_id=?",
                        (attempts, task_id),
                    )
                    await self._db.execute(
                        "UPDATE runs SET status='failed' WHERE run_id=?",
                        (trow["run_id"],),
                    )
                else:
                    await self._db.execute(
                        "UPDATE tasks SET status='ready', owner=NULL, version=version+1, attempts=? WHERE task_id=?",
                        (attempts, task_id),
                    )

    async def submit_approval(self, run_id: str, phase: str, decision: str) -> None:
        async with self._db_lock, self._txn():
            now = self._now()
            if decision == "approved":
                await self._db.execute(
                    "UPDATE phases SET gate='approved' WHERE run_id=? AND name=?",
                    (run_id, phase),
                )
                order = self.cfg.order_of(phase)
                nxt = next(
                    (
                        n
                        for n in self.cfg.phase_names
                        if self.cfg.order_of(n) == order + 1
                    ),
                    None,
                )
                if nxt is not None:
                    await self._db.execute(
                        "UPDATE phases SET status='open' WHERE run_id=? AND name=?",
                        (run_id, nxt),
                    )
                    await self._seed_phase_locked(run_id, nxt, now)
            elif decision == "rejected":
                await self._db.execute(
                    "UPDATE phases SET gate='rejected', status='open' WHERE run_id=? AND name=?",
                    (run_id, phase),
                )
                await self._db.execute(
                    "UPDATE tasks SET status='blocked', owner=NULL WHERE run_id=? AND phase=?",
                    (run_id, phase),
                )
            await self._recompute_ready_locked(run_id)

    async def snapshot(self, run_id: str) -> dict:
        cur = await self._db.execute(
            "SELECT status FROM runs WHERE run_id=?", (run_id,)
        )
        run_row = await cur.fetchone()
        run_status = run_row["status"] if run_row else "unknown"
        phases = await self._all_phases(run_id)
        tasks = await self._all_tasks(run_id)
        terminal = max(phases, key=lambda p: p["phase_order"]) if phases else None
        if run_status == "failed":
            status = "failed"
        elif terminal is not None and terminal["status"] == "complete":
            status = "done"
        else:
            status = "running"
        cur = await self._db.execute(
            "SELECT COALESCE(SUM(cost),0) AS s FROM spend WHERE run_id=?", (run_id,)
        )
        spent = (await cur.fetchone())["s"]
        cur = await self._db.execute(
            "SELECT budget_limit FROM runs WHERE run_id=?", (run_id,)
        )
        row = await cur.fetchone()
        limit = row["budget_limit"] if row else 0.0
        return {
            "run_id": run_id,
            "status": status,
            "phases": [
                {"name": p["name"], "status": p["status"], "gate": p["gate"]}
                for p in phases
            ],
            "tasks": [
                {
                    "agent_id": t["agent_id"],
                    "phase": t["phase"],
                    "status": t["status"],
                    "owner": t["owner"],
                    "model": t["model"],
                }
                for t in tasks
            ],
            "budget": {"spent": spent, "limit": limit},
        }
