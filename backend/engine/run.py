"""Run controller / CLI: boot server, spawn worker subprocesses, drive gates."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys

from backend.engine.client import EngineClient
from backend.engine.state_server import free_port, serve


async def _drive_gates(url, run_id, auto_approve, timeout, poll):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    async with EngineClient(url) as c:
        while True:
            run = await c.get_run(run_id)
            if run["status"] in ("done", "failed"):
                return run
            if auto_approve:
                for p in run["phases"]:
                    if p["gate"] == "pending":
                        await c.submit_approval(run_id, p["name"], "approved")
            if loop.time() > deadline:
                return run
            await asyncio.sleep(poll)


async def run_pipeline(
    idea,
    workers=4,
    budget_limit=200.0,
    auto_approve=True,
    db_path=None,
    host="127.0.0.1",
    port=None,
    poll=0.1,
    timeout=60.0,
) -> dict:
    db_path = db_path or "data/engine.db"
    port = port or free_port()
    url = f"http://{host}:{port}/mcp"

    server_task = asyncio.create_task(serve(db_path, host, port))
    procs = []
    worker_pids = []
    run_id = None
    final = None
    try:
        # wait for the server to accept connections, then create the run
        for _ in range(200):
            try:
                async with EngineClient(url) as c:
                    run_id = await c.create_run(idea, budget_limit)
                break
            except Exception:  # noqa: BLE001 - server may not be up yet
                await asyncio.sleep(0.05)
        if run_id is None:
            raise RuntimeError("state server failed to start")

        # spawn worker subprocesses (inside the try so a mid-spawn failure still tears down)
        for i in range(workers):
            procs.append(
                await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "backend.engine.worker",
                    "--server-url",
                    url,
                    "--run-id",
                    run_id,
                    "--worker-id",
                    f"w{i}",
                )
            )
        worker_pids = [p.pid for p in procs]

        final = await _drive_gates(url, run_id, auto_approve, timeout, poll)
    finally:
        for p in procs:
            if p.returncode is None:
                p.terminate()
        for p in procs:
            try:
                await asyncio.wait_for(p.wait(), timeout=5.0)
            except TimeoutError:
                p.kill()
        server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await server_task

    return {"run_id": run_id, "snapshot": final, "worker_pids": worker_pids}


def main() -> None:
    p = argparse.ArgumentParser(prog="appforge")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("idea")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--budget-limit", type=float, default=200.0)
    r.add_argument("--no-auto-approve", action="store_true")
    a = p.parse_args()
    result = asyncio.run(
        run_pipeline(
            a.idea,
            workers=a.workers,
            budget_limit=a.budget_limit,
            auto_approve=not a.no_auto_approve,
        )
    )
    print(f"run {result['run_id']}: {result['snapshot']['status']}")
    for ph in result["snapshot"]["phases"]:
        print(f"  {ph['name']:9} {ph['status']:9} gate={ph['gate']}")


if __name__ == "__main__":
    main()
