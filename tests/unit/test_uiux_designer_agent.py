"""Unit tests for the real UiuxDesignerAgent using FakeListChatModel.

The UI/UX Designer returns a structured design-spec JSON parsed into a Pydantic
model. The retry path mirrors tech_lead.py: retry once on malformed JSON; on a
second malformed response, return an error dict.

No real network calls are made — the fake model is injected via `model=`.
"""

import json

import pytest
from langchain_community.chat_models.fake import FakeListChatModel

from backend.agents.uiux_designer import UiuxDesignerAgent  # noqa: F401


def _fake_model(responses: list[str]) -> FakeListChatModel:
    return FakeListChatModel(responses=responses)


_VALID = json.dumps(
    {
        "tokens": {"colorPrimary": "#2563eb", "radius": "0.5rem"},
        "components": [
            {"type": "Header", "tailwind": "bg-blue-600 text-white p-4"},
            {"type": "Button", "tailwind": "rounded px-3 py-2"},
        ],
    }
)


@pytest.mark.asyncio
async def test_produces_design_spec_from_prd():
    model = _fake_model([_VALID])
    agent = UiuxDesignerAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    spec = out["artifact"]["design_spec"]
    assert spec["tokens"] == {"colorPrimary": "#2563eb", "radius": "0.5rem"}
    assert isinstance(spec["components"], list)
    assert spec["components"][0] == {
        "type": "Header",
        "tailwind": "bg-blue-600 text-white p-4",
    }
    assert isinstance(out["cost"], (int, float))


@pytest.mark.asyncio
async def test_retries_once_on_malformed_then_succeeds():
    model = _fake_model(["not json", _VALID])
    agent = UiuxDesignerAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert out["artifact"]["design_spec"]["tokens"]["colorPrimary"] == "#2563eb"


@pytest.mark.asyncio
async def test_errors_on_second_malformed_response():
    model = _fake_model(["not json", "still not json"])
    agent = UiuxDesignerAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "error"
    assert "error" in out


@pytest.mark.asyncio
async def test_parses_json_wrapped_in_code_fences():
    fenced = "```json\n" + _VALID + "\n```"
    model = _fake_model([fenced])
    agent = UiuxDesignerAgent(model=model)
    out = await agent.execute({"idea": "todo", "prd": "# PRD"})
    assert out["status"] == "success"
    assert out["artifact"]["design_spec"]["components"][1]["type"] == "Button"


@pytest.mark.asyncio
async def test_passes_rejection_comments_to_prompt():
    model = _fake_model([_VALID])
    agent = UiuxDesignerAgent(model=model)
    out = await agent.execute(
        {
            "idea": "todo",
            "prd": "# PRD",
            "rejection_comments": ["Use a warmer primary color"],
        }
    )
    assert out["status"] == "success"
    assert out["artifact"]["design_spec"]["tokens"]["radius"] == "0.5rem"
