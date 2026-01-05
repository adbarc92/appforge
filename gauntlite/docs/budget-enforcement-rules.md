# Budget Enforcement Rules v1.0

```yaml
budget:
  currency: USD
  hard_limit: 200.00
  warning_levels:
    - threshold: 0.50
      action: log_only
      message: "50% budget consumed (${spent}/${limit})."
    - threshold: 0.75
      action: notify_user
      message: "75% budget consumed. Consider switching to cheaper models."
      recommendations:
        - "Move clarifying_pm to gpt-4o-mini."
        - "Run backend/database agents sequentially."
    - threshold: 0.85
      action: auto_downgrade
      message: "85% consumed. Downgrading non-critical agents."
      downgrade_rules:
        - agents: [frontend, backend, database, devops, uiux_designer]
          model: claude-haiku-3.5
        - agents: [qa, technical_writer, delivery_summarizer]
          model: gpt-4o-mini
    - threshold: 0.95
      action: require_ack
      message: "95% consumed. Await `/approve_budget_override` to continue."
      pause_orchestrator: true
    - threshold: 1.00
      action: hard_stop
      message: "Budget exhausted. Workflow paused until new limit set."
      required_decision: ["increase_budget", "abort_phase", "switch_to_eco"]

spend_tracking:
  per_phase:
    store: data/budget/phase_spend.json
    fields: [phase, tokens_in, tokens_out, cost, timestamp]
  forecast:
    rolling_average_phases: 3
    flag_if_projection_exceeds: 1.05

notifications:
  channel: chat
  include:
    - current_spend
    - projected_total
    - agents_downgraded
    - recommended_actions

kill_switch_resume_requirements:
  - "User issues `/approve_budget_override reason`."
  - "Orchestrator logs override in Design Ledger."
  - "BudgetGuard resets projections with new limit."
```

## Operational Notes
- BudgetGuard must execute before any agent invocation with estimated cost > $1.
- All downgrades are reversible once spend drops below prior threshold; however, rolling back requires human confirmation.
- When eco mode (`OPEN_SOURCE_ONLY=true`) is active, `auto_downgrade` converts proprietary models to local equivalents instead of cheaper cloud models.
- Store every threshold crossing event in `logs/budgetguard-YYYYMMDD.jsonl` for auditability.
