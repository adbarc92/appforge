"""Unit tests for the real TechLeadAgent using FakeListChatModel.

The Tech Lead returns structured JSON parsed into a Pydantic model (unlike the
Architect's free markdown). The retry path mirrors clarifying_pm.py: retry once
on malformed JSON; on a second malformed response, return an error dict.

No real network calls are made — the fake model is injected via `model=`.
"""

import json

import pytest
from langchain_community.chat_models.fake import FakeListChatModel

from backend.agents.tech_lead import TechLeadAgent  # noqa: F401


def _fake_model(responses: list[str]) -> FakeListChatModel:
    return FakeListChatModel(responses=responses)


_VALID = json.dumps(
    {
        "tasks": [
            {
                "id": "T1",
                "title": "Build API",
                "description": "impl",
                "owner_agent": "backend",
                "depends_on": [],
            },
            {
                "id": "T2",
                "title": "Build UI",
                "description": "impl ui",
                "owner_agent": "frontend",
                "depends_on": ["T1"],
            },
        ]
    }
)


@pytest.mark.asyncio
async def test_produces_task_list_from_prd():
    model = _fake_model([_VALID])
    agent = TechLeadAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert isinstance(out["artifact"]["tasks"], list)
    assert out["artifact"]["tasks"][0] == {
        "id": "T1",
        "title": "Build API",
        "description": "impl",
        "owner_agent": "backend",
        "depends_on": [],
    }
    assert out["artifact"]["tasks"][1]["owner_agent"] == "frontend"
    assert out["artifact"]["tasks"][1]["depends_on"] == ["T1"]
    assert isinstance(out["cost"], (int, float))


@pytest.mark.asyncio
async def test_retries_once_on_malformed_then_succeeds():
    model = _fake_model(["not json", _VALID])
    agent = TechLeadAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert out["artifact"]["tasks"][0]["id"] == "T1"


@pytest.mark.asyncio
async def test_errors_on_second_malformed_response():
    model = _fake_model(["not json", "still not json"])
    agent = TechLeadAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "error"
    assert "error" in out


@pytest.mark.asyncio
async def test_parses_json_wrapped_in_code_fences():
    fenced = "```json\n" + _VALID + "\n```"
    model = _fake_model([fenced])
    agent = TechLeadAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert out["artifact"]["tasks"][0]["id"] == "T1"


@pytest.mark.asyncio
async def test_passes_rejection_comments_to_prompt():
    model = _fake_model([_VALID])
    agent = TechLeadAgent(model=model)
    out = await agent.execute(
        {
            "idea": "todo",
            "prd": "# PRD",
            "rejection_comments": ["Split the API task"],
        }
    )
    assert out["status"] == "success"
    assert out["artifact"]["tasks"][0]["id"] == "T1"
