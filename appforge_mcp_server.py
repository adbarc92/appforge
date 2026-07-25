"""Entry alias: `python appforge_mcp_server.py [--db ...] [--port ...]` runs the state server."""
from backend.engine.state_server import serve

if __name__ == "__main__":
    import argparse
    import asyncio

    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/engine.db")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8800)
    a = p.parse_args()
    asyncio.run(serve(a.db, a.host, a.port))
