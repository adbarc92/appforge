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


@pytest.mark.asyncio
async def test_load_project_unknown_returns_error(server_and_client):
    server, client = server_and_client
    ack = await client.call(
        "load_project", {"project_id": "does-not-exist"}, timeout=2
    )
    assert ack == {"error": "project not found"}


@pytest.mark.asyncio
async def test_load_project_hydrates_persisted_state(server_and_client):
    server, client = server_and_client
    created: list[dict] = []
    state: list[dict] = []
    messages: list[dict] = []
    client.on("project_created", lambda data: created.append(data))
    client.on("project_state", lambda data: state.append(data))
    client.on("agent_message", lambda data: messages.append(data))

    await client.emit("start_project", {"idea": "build a todo app"})
    # Wait until the first clarifying question lands so a checkpoint exists.
    for _ in range(80):
        await asyncio.sleep(0.05)
        if messages:
            break
    assert created, "expected project_created"
    project_id = created[0]["project_id"]

    await client.emit("load_project", {"project_id": project_id})
    for _ in range(40):
        await asyncio.sleep(0.05)
        if state:
            break
    assert state, "expected project_state hydration emit"
    assert state[0]["idea"] == "build a todo app"
