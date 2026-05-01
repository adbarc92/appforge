"""End-to-end Socket.IO tests: client sends events, server emits expected responses."""
import asyncio

import pytest
import socketio
import uvicorn


@pytest.fixture
async def server_and_client():
    from backend.main import asgi_app  # reimport inside test to reset state if needed

    config = uvicorn.Config(
        asgi_app, host="127.0.0.1", port=8766, log_level="warning"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)
    client = socketio.AsyncClient()
    await client.connect("http://127.0.0.1:8766", socketio_path="/socket.io")
    try:
        yield server, client
    finally:
        await client.disconnect()
        server.should_exit = True
        await task


@pytest.mark.asyncio
async def test_start_project_emits_project_created(server_and_client):
    server, client = server_and_client
    received: list[dict] = []
    client.on("project_created", lambda data: received.append(data))

    await client.emit("start_project", {"idea": "build a todo app"})
    for _ in range(50):
        await asyncio.sleep(0.05)
        if received:
            break
    assert received, "expected project_created event"
    assert "project_id" in received[0]
    assert len(received[0]["project_id"]) > 0


@pytest.mark.asyncio
async def test_start_project_with_empty_idea_returns_error(server_and_client):
    server, client = server_and_client
    ack = await client.call("start_project", {"idea": ""}, timeout=2)
    assert ack == {"error": "idea required"}
