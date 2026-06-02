"""Unit tests for the real SolutionArchitectAgent using FakeListChatModel.

The Architect returns a free-markdown ADR (not JSON), so the retry path is:
retry once if the model returns an empty/whitespace response; on a second
empty response, return an error dict.
"""

import pytest
from langchain_community.chat_models.fake import FakeListChatModel

from backend.agents.solution_architect import (  # noqa: F401
    SolutionArchitectAgent,
)


def _fake_model(responses: list[str]) -> FakeListChatModel:
    return FakeListChatModel(responses=responses)


@pytest.mark.asyncio
async def test_produces_adr_from_prd():
    adr = "# ADR\n\n## Context\nWe need a todo app.\n\n## Decision\nUse FastAPI."
    model = _fake_model([adr])
    agent = SolutionArchitectAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert out["artifact"] == {"adr": adr}
    assert isinstance(out["cost"], (int, float))


@pytest.mark.asyncio
async def test_retries_once_on_empty_then_succeeds():
    adr = "# ADR\n\n## Context\nRecovered after a retry."
    model = _fake_model(["", adr])
    agent = SolutionArchitectAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert out["artifact"]["adr"] == adr


@pytest.mark.asyncio
async def test_errors_on_second_empty_response():
    model = _fake_model(["", "   \n  "])
    agent = SolutionArchitectAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "error"
    assert "error" in out


@pytest.mark.asyncio
async def test_passes_rejection_comments_to_prompt():
    adr = "# ADR\n\n## Context\nRevised per feedback."
    model = _fake_model([adr])
    agent = SolutionArchitectAgent(model=model)
    out = await agent.execute(
        {
            "idea": "todo",
            "prd": "# PRD",
            "rejection_comments": ["Add a caching alternative"],
        }
    )
    assert out["status"] == "success"
    assert out["artifact"]["adr"] == adr
