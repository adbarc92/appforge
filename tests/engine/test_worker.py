import asyncio
import os

import pytest

from backend.agents.registry import reset_registry
from backend.engine.client import EngineClient
from backend.engine.worker import run_worker
from tests.engine.server_harness import running_server


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    reset_registry()
    yield
    reset_registry()


async def _auto_approver(url, run_id, stop):
    async with EngineClient(url) as c:
        while not stop.is_set():
            run = await c.get_run(run_id)
            for p in run["phases"]:
                if p["gate"] == "pending":
                    await c.submit_approval(run_id, p["name"], "approved")
            if run["status"] in ("done", "failed"):
                return
            await asyncio.sleep(0.05)


async def test_single_worker_completes_all_phases(tmp_path):
    async with running_server(str(tmp_path / "run.db")) as url:
        async with EngineClient(url) as c:
            run_id = await c.create_run("todo app", 200.0)
        stop = asyncio.Event()
        approver = asyncio.create_task(_auto_approver(url, run_id, stop))
        completed = await run_worker(url, run_id, "w1")
        stop.set()
        await approver
        async with EngineClient(url) as c:
            run = await c.get_run(run_id)
        assert run["status"] == "done"
        phases_done = {p["name"] for p in run["phases"] if p["status"] == "complete"}
        assert phases_done == {"clarify", "design", "code", "test", "deploy", "iterate"}
        assert completed >= 13  # all phase-worker tasks ran
