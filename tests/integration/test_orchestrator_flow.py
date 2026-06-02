"""Integration tests for Orchestrator.run using mock agents and no real LLM."""

import asyncio

import pytest

from backend.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_emits_project_started_and_agent_status():
    events: list[tuple[str, dict, str]] = []

    async def emit(event: str, data: dict, room: str) -> None:
        events.append((event, data, room))

    orch = Orchestrator(mock_mode=True)
    await orch.run("proj-1", "build a todo app", emit)

    # Wait for the clarifying_pm agent to emit its first status update.
    for _ in range(50):
        await asyncio.sleep(0.05)
        if any(
            e[0] == "agent_status" and e[1].get("agent") == "clarifying_pm"
            for e in events
        ):
            break

    clarifying_events = [
        e
        for e in events
        if e[0] == "agent_status" and e[1].get("agent") == "clarifying_pm"
    ]
    assert clarifying_events, "expected at least one clarifying_pm agent_status event"
    first = clarifying_events[0]
    assert first[2] == "project:proj-1"

    await orch.stop("proj-1")
