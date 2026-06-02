"""Test-environment isolation shared across the suite.

Integration tests that boot the FastAPI app use a module-level ``Orchestrator``
whose SQLite checkpoint path is bound from the environment when ``backend.main``
is first imported. By default that path is the committed ``./data/checkpoints.db``,
so the suite would write checkpoints into the repo and could inherit stale state
across runs — a real source of local flakiness (e.g. a load reading a prior
run's thread).

Point ``SQLITE_PATH`` at a throwaway temp directory *before* any test module
imports ``backend.main`` (conftest is imported by pytest ahead of test
collection), so tests never touch ``./data`` and always start from a clean
database. ``setdefault`` is used so an explicitly-provided ``SQLITE_PATH`` (CI,
a developer's shell, or a per-test ``monkeypatch.setenv``) still wins.
"""

import atexit
import os
import shutil
import tempfile

_TEST_CKPT_DIR = tempfile.mkdtemp(prefix="appforge-test-ckpt-")
os.environ.setdefault("SQLITE_PATH", os.path.join(_TEST_CKPT_DIR, "checkpoints.db"))


@atexit.register
def _cleanup_test_ckpt_dir() -> None:
    shutil.rmtree(_TEST_CKPT_DIR, ignore_errors=True)
