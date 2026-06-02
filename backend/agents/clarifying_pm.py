"""Real Clarifying PM agent backed by an LLM chat model with structured output.

The agent wraps an arbitrary `BaseChatModel` (Anthropic by default) and asks
clarifying questions about an idea until either the model says it is done or
the agent has hit `max_questions`. At that cap the agent forces synthesis of a
final PRD on a second LLM call.

The output shape matches what the orchestrator's `clarifying_node` expects:

    {"status": "success", "artifact": {"question": "..."}, "cost": 0.0}
    {"status": "success", "artifact": {"prd": "..."}, "cost": 0.0}
    {"status": "error", "error": "...", "recoverable": True}
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from backend.agents.base_agent import (
    AgentTask,
    InstrumentedAgent,
)
from backend.config import Config
from backend.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


EmitCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class ClarifyingResponse(BaseModel):
    """Structured output expected from the LLM on each turn."""

    next_question: str | None = Field(default=None)
    final_prd: str | None = Field(default=None)
    done: bool = Field(default=False)


class ClarifyingPMAgent(InstrumentedAgent):
    """Real clarifying PM agent that drives a question/answer loop into a PRD."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        max_questions: int = 6,
        name: str = "clarifying_pm",
        emit_callback: EmitCallback | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialise the agent.

        The signature accepts both the test-friendly form
        (`ClarifyingPMAgent(model=..., max_questions=...)`) and the registry
        form (`ClarifyingPMAgent(name=..., emit_callback=..., config=...)`).
        """
        super().__init__(name=name, emit_callback=emit_callback, config=config)
        self.model = model or self._default_model()
        self.max_questions = max_questions

    def _default_model(self) -> BaseChatModel:
        """Build the default Anthropic chat model from `Config`."""
        # Imported lazily so tests that pass a fake model never touch
        # langchain_anthropic (and never require an API key).
        from langchain_anthropic import ChatAnthropic

        cfg = Config.load()
        return ChatAnthropic(
            model=cfg.anthropic_model,
            anthropic_api_key=cfg.anthropic_api_key or "missing",
            max_tokens=2048,
            timeout=60.0,
        )

    # The orchestrator invokes this agent with a plain dict task (see
    # backend/orchestrator.py's clarifying_node). The base class's `run()`
    # wrapper uses AgentTask, but `clarifying_node` calls `execute()` directly
    # with a dict, so the signature here intentionally accepts either shape.
    async def execute(  # type: ignore[override]
        self, task: dict[str, Any] | AgentTask
    ) -> dict[str, Any]:
        task_dict = self._coerce_task(task)
        idea: str = task_dict.get("idea", "")
        questions: list[Any] = task_dict.get("questions", []) or []
        answers: list[Any] = task_dict.get("answers", []) or []

        force_synthesis = len(questions) >= self.max_questions
        rendered = load_prompt(
            "clarifying_pm",
            idea=idea,
            questions_so_far=questions,
            answers_so_far=answers,
            max_questions=self.max_questions,
        )

        _, parsed = await self._call_with_retry(rendered, force_synthesis)
        if parsed is None:
            return {
                "status": "error",
                "error": "invalid LLM response",
                "recoverable": True,
            }

        # If we're at/over the cap but the model still tried to ask another
        # question, push back once with a hardened prompt forcing synthesis.
        if force_synthesis and parsed.final_prd is None:
            synthesis_prompt = rendered + (
                "\n\nYou have asked the maximum number of questions. "
                "You MUST respond with final_prd set to the complete PRD "
                "and done=true. Do not ask another question."
            )
            _, parsed = await self._call_with_retry(
                synthesis_prompt, force_synthesis=True
            )
            if parsed is None or parsed.final_prd is None:
                return {
                    "status": "error",
                    "error": "synthesis failed",
                    "recoverable": True,
                }

        artifact: dict[str, Any] = {}
        if parsed.final_prd is not None:
            artifact["prd"] = parsed.final_prd
        elif parsed.next_question is not None:
            artifact["question"] = parsed.next_question
        else:
            return {
                "status": "error",
                "error": "empty LLM response",
                "recoverable": True,
            }

        return {"status": "success", "artifact": artifact, "cost": 0.0}

    async def _call_with_retry(
        self,
        prompt: str,
        force_synthesis: bool,  # noqa: ARG002 (reserved for forced-synthesis retry)
    ) -> tuple[str, ClarifyingResponse | None]:
        """Call the model up to twice, retrying once on malformed JSON."""
        text: str = ""
        for attempt in (1, 2):
            messages = [
                SystemMessage(
                    content=(
                        "You are a senior product manager. " "Respond ONLY with JSON."
                    )
                ),
                HumanMessage(
                    content=(
                        prompt
                        if attempt == 1
                        else prompt + "\n\nYour last response was not valid JSON. "
                        "Respond with JSON only."
                    )
                ),
            ]
            raw = await self.model.ainvoke(messages)
            text = raw.content if hasattr(raw, "content") else str(raw)
            parsed = self._parse(text)
            if parsed is not None:
                return text, parsed
        return text, None

    @staticmethod
    def _parse(text: str) -> ClarifyingResponse | None:
        """Parse a JSON LLM response into a `ClarifyingResponse`, or None."""
        try:
            data = json.loads(text)
            return ClarifyingResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            return None

    @staticmethod
    def _coerce_task(task: dict[str, Any] | AgentTask) -> dict[str, Any]:
        """Accept either a dict or an `AgentTask`."""
        if isinstance(task, dict):
            return task
        # AgentTask: prefer content if it's a dict, else fall back to context.
        if isinstance(task.content, dict):
            return task.content
        return task.context or {}
