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


async def test_complete_guard_rejects_wrong_version(store):
    c = await store.claim_next_task("r1", "w1")
    assert (
        await store.complete_task(c.task_id, "w1", version=999, result={"ok": True})
        is False
    )
    assert (
        await store.complete_task(
            c.task_id, "w1", version=c.version, result={"ok": True}
        )
        is True
    )


async def test_complete_records_spend_and_writes_state(store):
    c = await store.claim_next_task("r1", "w1")
    await store.complete_task(
        c.task_id,
        "w1",
        c.version,
        result={"prd": "PRD text"},
        state_writes={"prd": "PRD text"},
    )
    assert await store.spend_total("r1") == pytest.approx(
        0.30
    )  # clarifying_pm sim_cost
    st = await store.get_state("r1", ["prd"])
    assert st["prd"][0] == "PRD text"


async def test_clarify_completion_sets_prd_gate_pending_not_design(store):
    c = await store.claim_next_task("r1", "w1")
    await store.complete_task(c.task_id, "w1", c.version, result={"prd": "x"})
    phases = {p["name"]: p for p in await store._all_phases("r1")}
    assert phases["clarify"]["status"] == "complete"
    assert phases["clarify"]["gate"] == "pending"
    assert phases["design"]["status"] == "blocked"  # gated: not opened yet
    assert (
        await store.claim_next_task("r1", "w2") is None
    )  # nothing claimable behind the gate


async def test_submit_approval_opens_and_seeds_design(store):
    c = await store.claim_next_task("r1", "w1")
    await store.complete_task(c.task_id, "w1", c.version, result={"prd": "x"})
    await store.submit_approval("r1", "clarify", "approved")
    phases = {p["name"]: p for p in await store._all_phases("r1")}
    assert phases["design"]["status"] == "open" and phases["design"]["seeded"] == 1
    # design fans out to 3 ready tasks
    ready = [t for t in await store._all_tasks("r1") if t["status"] == "ready"]
    assert sorted(t["agent_id"] for t in ready) == [
        "solution_architect",
        "tech_lead",
        "uiux_designer",
    ]


async def test_fail_task_requeues_until_cap(store):
    c = await store.claim_next_task("r1", "w1")
    await store.fail_task(c.task_id, "w1", c.version, "boom")
    t = next(t for t in await store._all_tasks("r1") if t["task_id"] == c.task_id)
    assert t["status"] == "ready" and t["attempts"] == 1
    assert t["owner"] is None


async def test_fail_task_reaches_cap_and_fails_run(store):
    for _ in range(3):
        c = await store.claim_next_task("r1", "w1")
        assert c is not None
        await store.fail_task(c.task_id, "w1", c.version, "boom")
    t = next(
        t for t in await store._all_tasks("r1") if t["agent_id"] == "clarifying_pm"
    )
    assert t["status"] == "failed" and t["attempts"] == 3
    cur = await store._db.execute("SELECT status FROM runs WHERE run_id='r1'")
    assert (await cur.fetchone())["status"] == "failed"
