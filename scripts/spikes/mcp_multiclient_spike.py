"""Throwaway spike: can FastMCP serve many concurrent streamable-HTTP clients?

PASS bar: 8 concurrent client sessions x 100 tool calls each = 800 calls,
zero dropped/failed, correct results. Run with: uv run python scripts/spikes/mcp_multiclient_spike.py

This is a spike, not engine code. No engine module imports this script.

Verified against the installed SDK (mcp==1.28.1): FastMCP(stateless_http=True),
FastMCP.streamable_http_app(), mcp.client.streamable_http.streamablehttp_client,
mcp.ClientSession, and session.call_tool(...).structuredContent all match the
brief's assumed API surface as-is -- no adaptation was required.
"""
import asyncio
import contextlib

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("spike", stateless_http=True)


@mcp.tool()
def echo(n: int) -> int:
    """Return n unchanged (proves per-call dispatch)."""
    return n


async def run_client(base_url: str, worker: int, calls: int) -> int:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    ok = 0
    async with streamablehttp_client(base_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for i in range(calls):
                res = await session.call_tool("echo", {"n": worker * 1000 + i})
                assert res.structuredContent["result"] == worker * 1000 + i
                ok += 1
    return ok


async def main() -> None:
    import uvicorn

    app = mcp.streamable_http_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1.0)  # let it bind

    base = "http://127.0.0.1:8765/mcp"
    try:
        results = await asyncio.gather(*(run_client(base, w, 100) for w in range(8)))
        total = sum(results)
        print(f"SPIKE RESULT: {total}/800 calls ok")
        assert total == 800, "FAIL: dropped/failed calls"
        print("SPIKE PASS")
    finally:
        server.should_exit = True
        with contextlib.suppress(Exception):
            await server_task


if __name__ == "__main__":
    asyncio.run(main())
