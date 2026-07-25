from backend.engine.client import EngineClient
from tests.engine.server_harness import running_server


async def _drive_clarify(c, run_id):
    claim = await c.claim_next_task(run_id, "w1")
    await c.complete_task(
        claim["task_id"], "w1", claim["version"], {"prd": "PRD"}, {"prd": "PRD"}
    )


async def test_approval_opens_design(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url, EngineClient(url) as c:
        run_id = await c.create_run("idea", 200.0)
        await _drive_clarify(c, run_id)
        run = await c.get_run(run_id)
        assert run["status"] == "running"
        clarify = next(p for p in run["phases"] if p["name"] == "clarify")
        assert clarify["gate"] == "pending"
        await c.submit_approval(run_id, "clarify", "approved")
        # design now has 3 claimable tasks
        got = set()
        for w in ("w1", "w2", "w3"):
            claim = await c.claim_next_task(run_id, w)
            assert claim is not None
            got.add(claim["agent_id"])
        assert got == {"solution_architect", "tech_lead", "uiux_designer"}
