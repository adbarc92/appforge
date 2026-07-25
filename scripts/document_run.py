"""Run one documented pipeline and write docs/runs/<date>/ artifacts.

Usage: uv run python scripts/document_run.py YYYY-MM-DD
(pass the date explicitly so the output dir is deterministic/committable.)
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.engine.document import write_run_docs  # noqa: E402
from backend.engine.run import run_pipeline  # noqa: E402


async def main(date: str) -> None:
    os.environ["MOCK_AGENTS"] = "true"
    db = os.path.join(tempfile.mkdtemp(), "documented.db")
    result = await run_pipeline(
        "Build a todo app", workers=4, budget_limit=5.0, db_path=db, timeout=180.0
    )
    paths = write_run_docs(result, f"docs/runs/{date}")
    print(f"status={result['snapshot']['status']} pids={result['worker_pids']}")
    for p in paths:
        print("wrote", p)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "run"))
