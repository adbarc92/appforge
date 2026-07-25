import pytest

from backend.engine.client import EngineClient
from backend.engine.run import start_run, stop_run


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")


async def test_start_run_boots_and_seeds_then_stop_cleans_up(tmp_path):
    db = str(tmp_path / "run.db")
    handle = await start_run("todo app", workers=2, budget_limit=200.0, db_path=db)
    try:
        assert handle.run_id and handle.url.endswith("/mcp")
        assert len(handle.procs) == 2
        async with EngineClient(handle.url) as c:
            snap = await c.get_run(handle.run_id)
        assert snap["status"] == "running"  # not auto-driven; gate not yet approved
    finally:
        await stop_run(handle)
    # workers terminated
    for p in handle.procs:
        assert p.returncode is not None
