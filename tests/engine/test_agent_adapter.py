import os

import pytest

from backend.agents.registry import get_registry, reset_registry
from backend.engine.agent_adapter import run_agent_task
from backend.engine.phases import PhasesConfig

CFG = PhasesConfig.load("config/phases.yaml")


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["MOCK_AGENTS"] = "true"
    reset_registry()
    yield
    reset_registry()


async def test_clarify_loop_yields_prd(tmp_path):
    reg = get_registry()
    result, writes = await run_agent_task("clarifying_pm", "clarify",
                                          {"idea": "todo app"}, "m", reg, CFG, max_questions=6)
    assert "prd" in writes and writes["prd"]  # PRD produced without a human
    assert result["agent_id"] == "clarifying_pm"


async def test_generic_agent_writes_its_key(tmp_path):
    reg = get_registry()
    # solution_architect writes 'adr'
    result, writes = await run_agent_task("solution_architect", "design",
                                          {"prd": "PRD"}, "m", reg, CFG)
    assert "adr" in writes and writes["adr"]
