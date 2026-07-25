"""Test helper: run the state server in a dedicated background thread.

Running uvicorn as an asyncio task inside the test's own event loop
contaminates resources across tests in the same process (the FastMCP
streamable-HTTP session manager / loop is not fully torn down between tests,
producing "ASGI callable returned without completing response" and hangs on
the second server). Running the server in its OWN thread + event loop fully
isolates it: the test's client talks to it over HTTP, and stopping joins the
thread (which closes the Store connection before tmp_path teardown — required
on win32 for the WAL files).
"""
from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager

from backend.engine.state_server import build_server, free_port


class _ServerThread:
    def __init__(self, db_path: str, **kw):
        self.db_path = db_path
        self.kw = kw
        self.port = free_port()
        self._server = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        import uvicorn

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _serve() -> None:
            mcp, store = build_server(self.db_path, **self.kw)
            await store.connect()
            app = mcp.streamable_http_app()
            config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="error")
            self._server = uvicorn.Server(config)
            self._server.install_signal_handlers = lambda: None

            async def _watch_ready() -> None:
                while not self._server.started:
                    await asyncio.sleep(0.01)
                self._ready.set()

            watcher = asyncio.create_task(_watch_ready())
            try:
                await self._server.serve()
            finally:
                watcher.cancel()
                await store.close()

        loop.run_until_complete(_serve())
        # Drain leftover tasks (e.g. sse_starlette's shutdown watcher) so
        # loop.close() doesn't emit "Task was destroyed but it is pending!".
        pending = asyncio.all_tasks(loop)
        for t in pending:
            t.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    def start(self) -> None:
        self._thread.start()
        if not self._ready.wait(timeout=30):
            raise RuntimeError("state server thread failed to start")

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        self._thread.join(timeout=30)


@asynccontextmanager
async def running_server(db_path: str, **kw):
    server = _ServerThread(db_path, **kw)
    try:
        server.start()
        yield f"http://127.0.0.1:{server.port}/mcp"
    finally:
        server.stop()
