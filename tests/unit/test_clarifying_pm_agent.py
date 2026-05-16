"""Unit tests for the real ClarifyingPMAgent using FakeListChatModel."""
import json

import pytest
from langchain_community.chat_models.fake import FakeListChatModel

from backend.agents.clarifying_pm import ClarifyingPMAgent, ClarifyingResponse  # noqa: F401


def _fake_model(responses: list[dict]) -> FakeListChatModel:
    return FakeListChatModel(responses=[json.dumps(r) for r in responses])


@pytest.mark.asyncio
async def test_asks_first_question_from_idea():
    model = _fake_model(
        [{"next_question": "Who is the primary user?", "final_prd": None, "done": False}]
    )
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute(
        {"idea": "build a todo app", "questions": [], "answers": []}
    )
    assert out["status"] == "success"
    assert out["artifact"]["question"] == "Who is the primary user?"
    assert out["artifact"].get("prd") is None


@pytest.mark.asyncio
async def test_follow_up_uses_prior_answers():
    model = _fake_model(
        [{"next_question": "What is the success metric?", "final_prd": None, "done": False}]
    )
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute(
        {
            "idea": "build a todo app",
            "questions": [{"text": "Who is the primary user?", "index": 0}],
            "answers": [{"question_index": 0, "text": "remote engineers"}],
        }
    )
    assert out["artifact"]["question"] == "What is the success metric?"


@pytest.mark.asyncio
async def test_emits_prd_when_done():
    prd = "# PRD\n\n## Acceptance Criteria\n- [ ] works"
    model = _fake_model([{"next_question": None, "final_prd": prd, "done": True}])
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute(
        {
            "idea": "todo app",
            "questions": [{"text": "q", "index": 0}] * 2,
            "answers": [{"question_index": 0, "text": "a"}] * 2,
        }
    )
    assert out["artifact"]["prd"] == prd
    assert out["artifact"].get("question") is None


@pytest.mark.asyncio
async def test_synthesizes_prd_at_max_questions():
    """At max_questions, the agent should force a final PRD even if the model asks another question."""
    model = FakeListChatModel(
        responses=[
            json.dumps(
                {"next_question": "Another question?", "final_prd": None, "done": False}
            ),
            # Second call is the forced synthesis with a tightened prompt.
            json.dumps(
                {"next_question": None, "final_prd": "# Synthesized PRD", "done": True}
            ),
        ]
    )
    agent = ClarifyingPMAgent(model=model, max_questions=2)
    out = await agent.execute(
        {
            "idea": "todo app",
            "questions": [{"text": "q1", "index": 0}, {"text": "q2", "index": 1}],
            "answers": [
                {"question_index": 0, "text": "a1"},
                {"question_index": 1, "text": "a2"},
            ],
        }
    )
    assert out["artifact"]["prd"] == "# Synthesized PRD"


@pytest.mark.asyncio
async def test_retries_once_on_malformed_json():
    model = FakeListChatModel(
        responses=[
            "not-json",
            json.dumps(
                {"next_question": "Recovered?", "final_prd": None, "done": False}
            ),
        ]
    )
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute({"idea": "x", "questions": [], "answers": []})
    assert out["status"] == "success"
    assert out["artifact"]["question"] == "Recovered?"


@pytest.mark.asyncio
async def test_errors_on_second_malformed_json():
    model = FakeListChatModel(responses=["not-json", "still-not-json"])
    agent = ClarifyingPMAgent(model=model, max_questions=6)
    out = await agent.execute({"idea": "x", "questions": [], "answers": []})
    assert out["status"] == "error"
    assert "recoverable" in out
    assert out["recoverable"] is True
