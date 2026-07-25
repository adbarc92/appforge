"""Independent worker: claim -> execute (+heartbeat) -> complete/fail loop."""

from __future__ import annotations

import argparse
import asyncio
import contextlib

from backend.agents.registry import get_registry
from backend.engine.agent_adapter import run_agent_task
from backend.engine.client import EngineClient
from backend.engine.phases import PhasesConfig


async def _heartbeat_loop(client, task_id, worker_id, interval):
    while True:
        await asyncio.sleep(interval)
        if not await client.heartbeat(task_id, worker_id):
            return  # lost the lease


async def run_worker(
    url,
    run_id,
    worker_id,
    cfg=None,
    registry=None,
    poll_interval=0.05,
    max_poll=2.0,
    heartbeat_interval=20.0,
) -> int:
    cfg = cfg or PhasesConfig.load()
    registry = registry or get_registry()
    completed = 0
    backoff = poll_interval
    async with EngineClient(url) as client:
        while True:
            claim = await client.claim_next_task(run_id, worker_id)
            if claim is None:
                run = await client.get_run(run_id)
                if run["status"] in ("done", "failed"):
                    return completed
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_poll)
                continue
            backoff = poll_interval
            hb = asyncio.create_task(
                _heartbeat_loop(client, claim["task_id"], worker_id, heartbeat_interval)
            )
            try:
                result, state_writes = await run_agent_task(
                    claim["agent_id"],
                    claim["phase"],
                    claim["input"],
                    claim["model"],
                    registry,
                    cfg,
                )
                await client.complete_task(
                    claim["task_id"], worker_id, claim["version"], result, state_writes
                )
                completed += 1
            except Exception as e:  # noqa: BLE001
                await client.fail_task(
                    claim["task_id"], worker_id, claim["version"], str(e)
                )
            finally:
                hb.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await hb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-url", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--worker-id", required=True)
    a = p.parse_args()
    asyncio.run(run_worker(a.server_url, a.run_id, a.worker_id))


if __name__ == "__main__":
    main()
