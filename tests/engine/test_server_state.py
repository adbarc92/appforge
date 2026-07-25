import pytest

from backend.engine.client import EngineClient
from tests.engine.server_harness import running_server


async def test_two_clients_share_state_through_server(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        # Client A creates a run and writes state
        async with EngineClient(url) as a:
            run_id = await a.create_run("Build a todo app", 5.0)
            assert await a.put_state(run_id, "prd", {"text": "v1"}, expected_version=0) is True
        # A SEPARATE client B reads it back through the server
        async with EngineClient(url) as b:
            state = await b.get_state(run_id, ["prd"])
            assert state["prd"]["value"] == {"text": "v1"}
            assert state["prd"]["version"] == 1
            # CAS conflict path is observable across clients
            assert await b.put_state(run_id, "prd", {"text": "stale"}, expected_version=0) is False


async def test_create_run_seeds_clarify(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("idea", 5.0)
            assert isinstance(run_id, str) and run_id
