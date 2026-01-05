# Phase 11 Brief - Full Open-Source Eco Mode

## Purpose
Enable the entire system to run using open-source LLMs and local infrastructure (Llama, Mistral, SQLite, local embeddings) triggered by `OPEN_SOURCE_ONLY=true`.

## Prerequisites
- Phase 10 checklist: Metrics and monitoring active.
- Required agents: All core agents with eco-mode fallbacks, DevOps, BudgetGuard.
- Required documents: Core design doc, testing strategy, budget rules.

## Scope
Provide configuration, prompts, and tooling necessary to switch from proprietary APIs to local ones without code changes. Out of scope: advanced optimizations or production deployments.

## Required Changes
1. Update `config/llm.yaml` with open-source model routing.
2. Provide local inference stack (vLLM/Ollama) setup scripts.
3. Add prompt variants optimized for smaller context windows where needed.
4. Modify BudgetGuard to account for zero marginal cost runs but higher latency.
5. Extend testing harness to validate both proprietary and eco modes (CI matrix).
6. Documentation for downloading weights, hardware requirements, and troubleshooting.
7. Streamlit toggle to switch modes at runtime (with restart guard).
8. Regression suite ensuring outputs remain within acceptable deltas.
9. Metrics adjustments capturing performance impact.
10. Design Ledger entry documenting eco mode activation.

## Success Criteria
- [ ] Setting `OPEN_SOURCE_ONLY=true` routes all agent calls through local models.
- [ ] Local inference stack spins up via single command documented in README.
- [ ] Prompts adapt context length and temperature for open-source models without manual edits.
- [ ] CI matrix runs proprietary and eco mode smoke tests.
- [ ] BudgetGuard reports $0 incremental spend while tracking energy/time cost.
- [ ] Performance benchmarks captured comparing both modes (tokens/sec, latency).
- [ ] Streamlit UI indicates active mode and warns about capability differences.
- [ ] Documentation lists supported models, hardware specs, and fallbacks.
- [ ] Regression tests confirm parity within defined tolerances.
- [ ] Design Ledger records decision and constraints for eco mode.

## Human Approval Gate
Optional. Human acknowledges benchmark results and signs off on eco readiness.

## Dependencies
- Required before Phase 12 production ship to support cost-sensitive environments.

## Cost Estimate
- LLM spend minimal (local inference). Engineering time: 8-10 hours.

## Rollback Plan
1. Keep proprietary config as default.
2. If eco mode unstable, disable toggle and log issues for later revisit.
