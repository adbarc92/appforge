"""Regression: the store must create the directory holding its database file.

The engine's default paths live under data/ (data/engine.db, data/web.db),
which is gitignored and so does not exist on a fresh clone or a CI runner.
sqlite does not create missing intermediate directories, so connect() used to
die with "unable to open database file" for anyone who had not happened to
create data/ locally.

Every other store test builds its path under pytest's tmp_path, which already
exists -- which is exactly why the suite stayed green while CI failed.
"""

from pathlib import Path

from backend.engine.phases import PhasesConfig
from backend.engine.store import Store

CFG = PhasesConfig.load("config/phases.yaml")
BASE = dict.fromkeys(CFG.all_agent_ids(), "gpt-4o")


async def test_connect_creates_missing_parent_directory(tmp_path):
    db_path = tmp_path / "data" / "engine.db"
    assert not db_path.parent.exists()  # the fresh-clone condition

    s = Store(str(db_path), CFG, BASE)
    await s.connect()
    try:
        await s.create_run("r1", "Build a todo app", 5.0)
        assert [t["agent_id"] for t in await s._all_tasks("r1")] == ["clarifying_pm"]
    finally:
        await s.close()  # close before tmp_path teardown (win32 WAL files)

    assert db_path.exists()


async def test_connect_creates_nested_parent_directories(tmp_path):
    db_path = tmp_path / "a" / "b" / "c" / "run.db"

    s = Store(str(db_path), CFG, BASE)
    await s.connect()
    await s.close()

    assert db_path.exists()


async def test_connect_accepts_bare_filename(tmp_path, monkeypatch):
    """A path with no directory component must not trip the mkdir."""
    monkeypatch.chdir(tmp_path)

    s = Store("run.db", CFG, BASE)
    await s.connect()
    await s.close()

    assert Path(tmp_path / "run.db").exists()
