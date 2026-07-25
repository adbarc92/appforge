"""Render documented-run artifacts from a run_pipeline result (no live deps)."""

from __future__ import annotations

import json
from pathlib import Path

_PHASE_ORDER = ["clarify", "design", "code", "test", "deploy", "iterate"]


def _dag_mermaid() -> str:
    edges = "\n".join(
        f"    {a} --> {b}" for a, b in zip(_PHASE_ORDER, _PHASE_ORDER[1:], strict=False)
    )
    return f"```mermaid\nflowchart LR\n{edges}\n```\n"


def write_run_docs(result: dict, out_dir: str) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    snap = result["snapshot"]
    pids = result.get("worker_pids", [])

    def pid_for(owner: str | None) -> str:
        if owner and owner.startswith("w"):
            try:
                return f"pid {pids[int(owner[1:])]}"
            except (ValueError, IndexError):
                return owner
        return owner or "-"

    lines = [
        f"# AppForge run `{result['run_id']}`",
        "",
        f"**Status:** {snap['status']}  •  **Workers (PIDs):** {pids}",
        "",
        "## Phases",
        "",
        "| phase | status | gate |",
        "|---|---|---|",
    ]
    lines += [f"| {p['name']} | {p['status']} | {p['gate']} |" for p in snap["phases"]]
    lines += [
        "",
        "## Tasks (agent → worker PID → model)",
        "",
        "| agent | phase | status | worker | model |",
        "|---|---|---|---|---|",
    ]
    for t in snap["tasks"]:
        lines.append(
            f"| {t['agent_id']} | {t['phase']} | {t['status']} | "
            f"{pid_for(t.get('owner'))} | {t.get('model')} |"
        )
    lines += ["", "## Phase dependency graph", "", _dag_mermaid()]

    summary_p = out / "run-summary.md"
    summary_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    snap_p = out / "snapshot.json"
    snap_p.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    dag_p = out / "dag.md"
    dag_p.write_text(_dag_mermaid(), encoding="utf-8")
    return [str(summary_p), str(snap_p), str(dag_p)]
