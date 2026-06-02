"""Reject the PRD repeatedly; verify feedback threads back and the third
rejection surfaces an escalation flag on the approval gate."""

import asyncio

import pytest

from backend.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_three_rejections_escalate(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_AGENTS", "true")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "chk.db"))
    received: list = []

    async def emit(event, data, room):
        received.append((event, data))

    orch = Orchestrator()
    await orch.run("proj-reject", "idea", emit)

    async def wait_for(event_name, predicate=lambda d: True, timeout: float = 4.0):
        for _ in range(int(timeout / 0.05)):
            await asyncio.sleep(0.05)
            if any(e[0] == event_name and predicate(e[1]) for e in received):
                return True
        return False

    # Drive through clarifying -> approval (mock asks 3 questions then PRD).
    for n in (1, 2, 3):
        assert await wait_for(
            "agent_message", lambda d, n=n: f"#{n}?" in (d.get("text") or "")
        )
        await orch.user_message("proj-reject", f"answer {n}")
    assert await wait_for("approval_required")

    # First and second rejections route back, re-emit a revised PRD, and do
    # NOT yet escalate.
    for comment in ("not enough detail", "still not enough"):
        received.clear()
        await orch.reject("proj-reject", comment)
        assert await wait_for("approval_required")
        assert not any(
            e[0] == "approval_required" and e[1].get("escalation") for e in received
        ), f"should not escalate before the third rejection ({comment})"

    # Third rejection -> escalation flag.
    received.clear()
    await orch.reject("proj-reject", "nope")
    assert await wait_for(
        "approval_required", lambda d: bool(d.get("escalation"))
    ), f"third rejection should emit escalation=true; received={received}"

    await orch.stop("proj-reject")
