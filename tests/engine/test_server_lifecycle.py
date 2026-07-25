from backend.engine.client import EngineClient
from tests.engine.server_harness import running_server


async def test_claim_complete_advances_to_prd_gate(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url, EngineClient(url) as c:
        run_id = await c.create_run("idea", 200.0)
        claim = await c.claim_next_task(run_id, "w1")
        assert claim is not None and claim["agent_id"] == "clarifying_pm"
        ok = await c.complete_task(
            claim["task_id"],
            "w1",
            claim["version"],
            result={"prd": "PRD"},
            state_writes={"prd": "PRD"},
        )
        assert ok is True
        # behind the pending PRD gate nothing is claimable
        assert await c.claim_next_task(run_id, "w2") is None
        st = await c.get_state(run_id, ["prd"])
        assert st["prd"]["value"] == "PRD"


async def test_complete_wrong_version_rejected(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url, EngineClient(url) as c:
        run_id = await c.create_run("idea", 200.0)
        claim = await c.claim_next_task(run_id, "w1")
        assert (
            await c.complete_task(
                claim["task_id"], "w1", 999, result={}, state_writes=None
            )
            is False
        )


async def test_heartbeat_owner_guarded(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url, EngineClient(url) as c:
        run_id = await c.create_run("idea", 200.0)
        claim = await c.claim_next_task(run_id, "w1")
        assert await c.heartbeat(claim["task_id"], "w1") is True
        assert await c.heartbeat(claim["task_id"], "w2") is False
