import pytest

from backend.engine.phases import PhasesConfig
from backend.engine.store import Store

CFG = PhasesConfig.load("config/phases.yaml")
BASE = {aid: "gpt-4o" for aid in CFG.all_agent_ids()}


@pytest.fixture
async def store(tmp_path):
    s = Store(str(tmp_path / "run.db"), CFG, BASE)
    await s.connect()
    yield s
    await s.close()  # close before tmp_path teardown (win32 WAL files)


async def test_create_run_seeds_clarify_ready(store):
    await store.create_run("r1", "Build a todo app", 5.0)
    tasks = await store._all_tasks("r1")
    assert [t["agent_id"] for t in tasks] == ["clarifying_pm"]
    assert tasks[0]["status"] == "ready"  # clarify is open + no deps


async def test_put_state_cas_success_then_conflict(store):
    await store.create_run("r1", "idea", 5.0)
    assert await store.put_state("r1", "prd", {"text": "v1"}, expected_version=0) is True
    got = await store.get_state("r1", ["prd"])
    assert got["prd"][0] == {"text": "v1"} and got["prd"][1] == 1
    # stale write with old version fails
    assert await store.put_state("r1", "prd", {"text": "stale"}, expected_version=0) is False
    # correct version succeeds
    assert await store.put_state("r1", "prd", {"text": "v2"}, expected_version=1) is True
