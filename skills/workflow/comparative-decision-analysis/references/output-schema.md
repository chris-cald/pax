# Comparative Decision Analysis Output Schema

Use this schema with `scripts/score_with_guardrails.py` and `scripts/run_comparative_decision_harness.py`.
Use `output-schema.json` in this directory as the machine-readable source of truth.

## Required Audit Fields

- `run_id`
- `scorer_version`
- `rules_version`
- `evaluated_at`
- `decision_status` (`proceed|defer|no-go`)

## Required Decision Fields

- `criteria_confirmation_source`
- `discovery`
- `independent_evaluations`
- `ranked_alternatives`
- `recommendation`

## Recommendation Action Set

- `select`
- `compose`
- `improve`
- `extend`
- `build-new`

## Decision Status Semantics

- `proceed`: The workflow produced an actionable forward path (`select`, `compose`, `extend`, or `build-new`).
- `defer`: The workflow found a viable direction but recommends more evidence or iteration before acting (`improve`).
- `no-go`: Reserved for future hard-stop outcomes where the workflow cannot recommend action.
