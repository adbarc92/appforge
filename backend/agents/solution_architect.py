"""Real Solution Architect agent backed by an LLM chat model.

The agent wraps an arbitrary `BaseChatModel` (Anthropic by default) and produces
an Architecture Decision Record (ADR) as free-form markdown from a PRD. Because
the output is free markdown (not JSON), the "malformed" retry path is simply:
retry once if the model returns an empty/whitespace response; on a second empty
response, return an error dict.

The output shape mirrors the other Phase 3/4 agents:

    {"status": "success", "artifact": {"adr": "..."}, "cost": 0.0}
    {"status": "error", "error": "...", "recoverable": True}
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.base_agent import (
    AgentTask,
    InstrumentedAgent,
)
from backend.config import Config
from backend.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


EmitCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class SolutionArchitectAgent(InstrumentedAgent):
    """Real solution architect agent that produces an ADR in markdown."""

    def __init__(
        self,
        model: BaseChatModel | None = None,
        name: str = "solution_architect",
        emit_callback: EmitCallback | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialise the agent.

        The signature accepts both the test-friendly form
        (`SolutionArchitectAgent(model=...)`) and the registry form
        (`SolutionArchitectAgent(name=..., emit_callback=..., config=...)`).
        """
        super().__init__(name=name, emit_callback=emit_callback, config=config)
        self.model = model or self._default_model()

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

    # The orchestrator invokes this agent with a plain dict task. The base
    # class's `run()` wrapper uses AgentTask, so the signature here
    # intentionally accepts either shape.
    async def execute(  # type: ignore[override]
        self, task: dict[str, Any] | AgentTask
    ) -> dict[str, Any]:
        task_dict = self._coerce_task(task)
        prd: str = task_dict.get("prd", "")
        rejection_comments: list[Any] = task_dict.get("rejection_comments", []) or []

        rendered = load_prompt(
            "solution_architect",
            prd=prd,
            rejection_comments=rejection_comments,
        )

        text = await self._call_with_retry(rendered)
        if text is None:
            return {
                "status": "error",
                "error": "empty ADR response",
                "recoverable": True,
            }

        return {"status": "success", "artifact": {"adr": text}, "cost": 0.0}

    async def _call_with_retry(self, prompt: str) -> str | None:
        """Call the model up to twice, retrying once on an empty response.

        Returns the stripped-but-original markdown text on success, or None if
        the model returns empty/whitespace on both attempts.
        """
        for attempt in (1, 2):
            messages = [
                SystemMessage(
                    content=(
                        "You are a staff software engineer writing an "
                        "Architecture Decision Record (ADR) in markdown."
                    )
                ),
                HumanMessage(
                    content=(
                        prompt
                        if attempt == 1
                        else prompt + "\n\nYour last response was empty. "
                        "Respond with the full ADR in markdown."
                    )
                ),
            ]
            raw = await self.model.ainvoke(messages)
            text = raw.content if hasattr(raw, "content") else str(raw)
            if isinstance(text, str) and text.strip():
                return text
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
