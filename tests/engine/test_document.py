import json

from backend.engine.document import write_run_docs

SNAP = {
    "run_id": "r1",
    "status": "done",
    "phases": [
        {"name": "clarify", "status": "complete", "gate": "approved"},
        {"name": "test", "status": "complete", "gate": "none"},
    ],
    "tasks": [
        {
            "agent_id": "clarifying_pm",
            "phase": "clarify",
            "status": "done",
            "owner": "w0",
            "model": "claude-3-5-sonnet-20241022",
        },
        {
            "agent_id": "qa_test",
            "phase": "test",
            "status": "done",
            "owner": "w1",
            "model": "gpt-4o-mini",
        },
    ],
}


def test_write_run_docs_emits_summary_and_snapshot(tmp_path):
    result = {"run_id": "r1", "snapshot": SNAP, "worker_pids": [111, 222]}
    paths = write_run_docs(result, str(tmp_path))
    names = {p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for p in paths}
    assert {"run-summary.md", "snapshot.json", "dag.md"} <= names

    summary = (tmp_path / "run-summary.md").read_text(encoding="utf-8")
    assert "qa_test" in summary and "gpt-4o-mini" in summary  # downgrade shown
    assert "pid 222" in summary  # w1 -> pids[1]
    saved = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert saved["status"] == "done"
