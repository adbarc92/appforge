import sqlite3

from backend.engine.models import SCHEMA_SQL, ClaimResult


def test_schema_creates_all_tables(tmp_path):
    db = sqlite3.connect(tmp_path / "t.db")
    db.executescript(SCHEMA_SQL)
    names = {
        r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"runs", "phases", "tasks", "state", "spend", "events"} <= names
    db.close()


def test_tasks_has_ordering_and_lease_columns(tmp_path):
    db = sqlite3.connect(tmp_path / "t.db")
    db.executescript(SCHEMA_SQL)
    cols = {r[1] for r in db.execute("PRAGMA table_info(tasks)")}
    required_cols = {
        "task_id",
        "run_id",
        "phase",
        "phase_order",
        "agent_id",
        "input",
        "depends_on",
        "status",
        "owner",
        "version",
        "attempts",
        "lease_expires",
        "created_at",
        "claimed_at",
        "model",
        "sim_cost",
        "result",
    }
    assert required_cols <= cols
    db.close()


def test_claim_result_roundtrips():
    cr = ClaimResult(
        task_id="t1",
        run_id="r1",
        phase="code",
        phase_order=2,
        agent_id="backend",
        input={"prd": "x"},
        model="gpt-4o",
        version=1,
    )
    assert cr.agent_id == "backend"
    assert cr.input["prd"] == "x"
