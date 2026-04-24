"""Verify a Socket.IO client can connect to the mounted ASGI app."""
import asyncio

import pytest
import socketio
import uvicorn
from contextlib import asynccontextmanager

from backend.main import asgi_app


@pytest.mark.asyncio
async def test_socketio_client_can_connect():
    server_config = uvicorn.Config(asgi_app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(server_config)
    task = asyncio.create_task(server.serve())
    # Wait for the server to be ready
    while not server.started:
        await asyncio.sleep(0.02)

    client = socketio.AsyncClient()
    try:
        await client.connect("http://127.0.0.1:8765", socketio_path="/socket.io")
        assert client.connected is True
    finally:
        await client.disconnect()
        server.should_exit = True
        await task
