"""Headless E2E smoke for Slice 3.

Boots the real ASGI app on a localhost port and drives it with a Socket.IO
client: emits start_project, waits for project_created, and confirms the
mock Clarifying PM emits a clarifying question through the room.
"""
import asyncio

import pytest
import socketio
import uvicorn


@pytest.fixture
async def server_and_client():
    from backend.main import asgi_app

    config = uvicorn.Config(
        asgi_app, host="127.0.0.1", port=8767, log_level="warning"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)
    client = socketio.AsyncClient()
    await client.connect("http://127.0.0.1:8767", socketio_path="/socket.io")
    try:
        yield server, client
    finally:
        await client.disconnect()
        server.should_exit = True
        await task


@pytest.mark.asyncio
async def test_idea_yields_project_and_mock_question(server_and_client):
    _, client = server_and_client
    project_created: list[dict] = []
    statuses: list[dict] = []
    messages: list[dict] = []

    client.on("project_created", lambda data: project_created.append(data))
    client.on("agent_status", lambda data: statuses.append(data))
    client.on("agent_message", lambda data: messages.append(data))

    await client.emit("start_project", {"idea": "build me a todo app"})

    for _ in range(80):
        await asyncio.sleep(0.05)
        if messages:
            break

    assert project_created, "expected project_created"
    assert any(
        s.get("agent") == "clarifying_pm" and s.get("status") == "running"
        for s in statuses
    )
    assert messages, "expected at least one mock clarifying question"
    assert "Clarifying" in (messages[0].get("text") or "")
