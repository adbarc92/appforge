"""Bridge a claimed task to an agent via the registry (mock/real).

No single execute() signature exists across agents: base MockAgent takes an
AgentTask and returns AgentResult; specialized/real agents take a dict and
return a dict. We always PASS a dict and read results defensively.
"""

from __future__ import annotations

from typing import Any


def _field(res: Any, name: str):
    """Read `name` from a dict-or-attribute result, else None."""
    if isinstance(res, dict):
        return res.get(name)
    return getattr(res, name, None)


def _artifact(res: Any):
    art = _field(res, "artifact")
    return art if art is not None else res


def _writes_value(res: Any, writes_key: str):
    art = _artifact(res)
    if isinstance(art, dict):
        return art.get(writes_key, art)
    return art


async def _run_clarify_loop(task_input, registry, max_questions):
    clarifier = registry.get("clarifying_pm")
    po = registry.get("product_owner")
    idea = task_input.get("idea", "")
    questions: list[str] = []
    answers: list[str] = []
    for _ in range(max_questions + 1):
        res = await clarifier.execute(
            {
                "idea": idea,
                "questions": list(questions),
                "answers": list(answers),
                "mode": "autonomous",
            }
        )
        art = _artifact(res)
        prd = None
        if isinstance(art, dict):
            prd = art.get("prd") or art.get("final_prd")
            question = art.get("question")
        else:
            question, prd = None, None
        if prd:
            return {"agent_id": "clarifying_pm", "output": prd}, {"prd": prd}
        if not question:
            break
        questions.append(question)
        ans = await po.execute({"question": question})
        ans_art = _artifact(ans)
        answers.append(ans_art if isinstance(ans_art, str) else str(ans_art))
    # Fallback: synthesize a minimal PRD so the pipeline always advances in mock mode.
    prd = f"PRD for: {idea}"
    return {"agent_id": "clarifying_pm", "output": prd}, {"prd": prd}


async def run_agent_task(
    agent_id, phase, task_input, model, registry, cfg, max_questions=6
):
    if agent_id == "clarifying_pm":
        return await _run_clarify_loop(task_input, registry, max_questions)
    writes_key = cfg.agents_of(phase)[agent_id].writes
    agent = registry.get(agent_id)
    res = await agent.execute(
        dict(task_input, agent_id=agent_id, model=model, mode="autonomous")
    )
    value = _writes_value(res, writes_key)
    return {"agent_id": agent_id, "output": value}, {writes_key: value}
