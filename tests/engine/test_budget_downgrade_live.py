import os

import pytest

from backend.engine.run import run_pipeline


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    yield


async def test_test_phase_downgraded_when_budget_crossed(tmp_path):
    result = await run_pipeline(
        "Build a todo app",
        workers=4,
        budget_limit=5.0,
        db_path=str(tmp_path / "run.db"),
        timeout=120.0,
    )
    assert result["snapshot"]["status"] == "done"
    tasks = {t["agent_id"]: t for t in result["snapshot"]["tasks"]}
    # Test phase opens after all Code spend (4.30) committed -> 0.86 ratio -> downgrade
    assert tasks["qa_test"]["model"] == "gpt-4o-mini"
    assert tasks["security"]["model"] == "claude-3-5-haiku-20241022"
    # critical agent (clarify) claimed early + skip-listed -> keeps its model
    assert tasks["clarifying_pm"]["model"] == "claude-3-5-sonnet-20241022"
