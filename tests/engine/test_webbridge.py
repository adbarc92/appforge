from backend.engine import webbridge as wb

BASE = {"qa_test": "gpt-4o", "clarifying_pm": "claude-3-5-sonnet-20241022"}


def _snap(status, phases, tasks, spent=0.0, limit=200.0):
    return {
        "run_id": "r1",
        "status": status,
        "phases": phases,
        "tasks": tasks,
        "budget": {"spent": spent, "limit": limit},
    }


def test_phase_number_and_kind():
    assert wb.phase_number("clarify") == 3 and wb.phase_number("code") == 6
    assert wb.PHASE_GATE_KIND["design"] == "plan"


def test_agent_status_transitions_emit_events():
    prev = _snap(
        "running",
        [{"name": "clarify", "status": "open", "gate": "none"}],
        [
            {
                "agent_id": "clarifying_pm",
                "phase": "clarify",
                "status": "ready",
                "owner": None,
                "model": "claude-3-5-sonnet-20241022",
            }
        ],
    )
    new = _snap(
        "running",
        [{"name": "clarify", "status": "open", "gate": "none"}],
        [
            {
                "agent_id": "clarifying_pm",
                "phase": "clarify",
                "status": "running",
                "owner": "w0",
                "model": "claude-3-5-sonnet-20241022",
            }
        ],
    )
    events = wb.diff_to_events(prev, new, {}, BASE)
    assert ("agent_status", {"agent": "clarifying_pm", "status": "running"}) in [
        (e, {k: v for k, v in p.items() if k in ("agent", "status")}) for e, p in events
    ]


def test_pending_gate_emits_approval_required_with_prd():
    prev = _snap(
        "running", [{"name": "clarify", "status": "complete", "gate": "none"}], []
    )
    new = _snap(
        "running", [{"name": "clarify", "status": "complete", "gate": "pending"}], []
    )
    events = wb.diff_to_events(prev, new, {"prd": "# PRD"}, BASE)
    appr = [p for e, p in events if e == "approval_required"]
    assert (
        appr
        and appr[0]["kind"] == "prd"
        and appr[0]["phase"] == 3
        and appr[0]["content"] == "# PRD"
    )


def test_downgraded_status_on_completion():
    prev = _snap(
        "running",
        [{"name": "test", "status": "open", "gate": "none"}],
        [
            {
                "agent_id": "qa_test",
                "phase": "test",
                "status": "running",
                "owner": "w0",
                "model": "gpt-4o-mini",
            }
        ],
    )
    new = _snap(
        "running",
        [{"name": "test", "status": "open", "gate": "none"}],
        [
            {
                "agent_id": "qa_test",
                "phase": "test",
                "status": "done",
                "owner": "w0",
                "model": "gpt-4o-mini",
            }
        ],
    )  # base gpt-4o, ran on mini
    events = wb.diff_to_events(prev, new, {}, BASE)
    st = [
        p["status"]
        for e, p in events
        if e == "agent_status" and p["agent"] == "qa_test"
    ]
    assert st == ["downgraded"]


def test_to_project_state_shape():
    snap = _snap(
        "running",
        [{"name": "clarify", "status": "complete", "gate": "pending"}],
        [
            {
                "agent_id": "clarifying_pm",
                "phase": "clarify",
                "status": "done",
                "owner": "w0",
                "model": "claude-3-5-sonnet-20241022",
            }
        ],
        spent=1.0,
    )
    ps = wb.to_project_state(snap, "todo", {"prd": "# PRD"})
    assert ps["idea"] == "todo" and ps["prd"] == "# PRD"
    assert ps["agents"]["clarifying_pm"]["status"] == "complete"
    assert ps["approval_pending"]["kind"] == "prd"
    assert ps["budget"]["spent"] == 1.0


def test_budget_update_uses_discrete_threshold_bucket():
    prev = _snap("running", [], [], spent=0.0, limit=200.0)
    new = _snap("running", [], [], spent=190.0, limit=200.0)  # 0.95
    events = wb.diff_to_events(prev, new, {}, {})
    bu = [p for e, p in events if e == "budget_update"]
    assert bu and bu[0]["threshold"] == 95 and bu[0]["spent"] == 190.0


def test_to_project_state_includes_threshold_bucket():
    snap = _snap("running", [], [], spent=170.0, limit=200.0)  # 0.85
    ps = wb.to_project_state(snap, "todo", {})
    assert ps["budget"]["threshold"] == 85
