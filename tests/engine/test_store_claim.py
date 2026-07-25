import pytest

from backend.engine.phases import PhasesConfig
from backend.engine.store import Store

CFG = PhasesConfig.load("config/phases.yaml")
BASE = dict.fromkeys(CFG.all_agent_ids(), "gpt-4o")


@pytest.fixture
async def store(tmp_path):
    s = Store(str(tmp_path / "run.db"), CFG, BASE, lease_s=100.0)
    await s.connect()
    await s.create_run("r1", "idea", 200.0)
    yield s
    await s.close()


async def test_claim_returns_clarify_task_once(store):
    c1 = await store.claim_next_task("r1", "w1")
    assert c1 is not None and c1.agent_id == "clarifying_pm" and c1.version == 1
    c2 = await store.claim_next_task("r1", "w2")
    assert c2 is None  # only one ready task, already claimed


async def test_claim_assembles_input_from_state(store):
    await store.put_state("r1", "idea", {"text": "todo app"}, expected_version=0)
    c = await store.claim_next_task("r1", "w1")
    assert "idea" in c.input  # clarifying_pm reads [idea]


async def test_heartbeat_owner_guarded(store):
    c = await store.claim_next_task("r1", "w1")
    assert await store.heartbeat(c.task_id, "w1") is True
    assert await store.heartbeat(c.task_id, "someone_else") is False


async def test_reaper_reverts_and_bumps_version(store):
    c = await store.claim_next_task("r1", "w1")
    # force the lease into the past
    await store._db.execute(
        "UPDATE tasks SET lease_expires=? WHERE task_id=?", (0.0, c.task_id)
    )
    await store._db.commit()
    n = await store.reap_expired()
    assert n == 1
    tasks = {t["task_id"]: t for t in await store._all_tasks("r1")}
    t = tasks[c.task_id]
    assert t["status"] == "ready" and t["version"] == 2 and t["attempts"] == 1
    # zombie w1 (holding version 1) can no longer heartbeat
    assert await store.heartbeat(c.task_id, "w1") is False
