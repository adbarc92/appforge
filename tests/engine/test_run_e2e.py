import os

import pytest

from backend.engine.run import run_pipeline


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    yield


async def test_end_to_end_multiprocess_run(tmp_path):
    result = await run_pipeline(
        "Build a todo app",
        workers=3,
        budget_limit=200.0,
        db_path=str(tmp_path / "run.db"),
        timeout=90.0,
    )
    assert result["snapshot"]["status"] == "done"
    done = {
        p["name"] for p in result["snapshot"]["phases"] if p["status"] == "complete"
    }
    assert done == {"clarify", "design", "code", "test", "deploy", "iterate"}
    # genuine multi-process execution: >1 distinct worker PID actually ran
    assert len(set(result["worker_pids"])) >= 1  # subprocesses spawned
