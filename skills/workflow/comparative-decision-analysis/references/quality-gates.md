# Quality Gates

Apply these gates on every run.

## Pre-Scoring Gates

- Criteria are confirmed.
- `criteria_confirmation_source` is present and valid when criteria are confirmed.
- Criteria include `metric`, `data_source`, and `scoring_rule`.
- One rubric only per run.
- At least 2 alternatives for scoring.
- Discovery includes at least 1 external option, or a documented blocker.
- Input matches `references/input-schema.json`.
- Independent evaluator evidence is complete:
  - one evaluator record per alternative
  - unique `evaluator_id` per alternative
  - `isolation_confirmed=true` on each evaluator record

## Scoring Gates

- Missing scores are `null`, never silently coerced to zero.
- Coverage is computed per option.
- `select` and `compose` require `coverage >= min_coverage`.
- Infeasible options cannot be recommended unless all options are infeasible.

## Output Gates

- Rank all alternatives that were identified.
- Include explicit per-option justification.
- Include feasibility status for each option.
- Include `decision_status`.
- Include risks, evidence gaps, and follow-up actions.
- Output matches `references/output-schema.json`.

## Regression Gates

Run:

```bash
python3 test/skills/workflow/comparative-decision-analysis/test_score_with_guardrails.py
node skills/workflow/comparative-decision-analysis/scripts/validate_json_contract.mjs \
  --schema skills/workflow/comparative-decision-analysis/references/input-schema.json \
  --data <analysis-input.json>
node skills/workflow/comparative-decision-analysis/scripts/validate_json_contract.mjs \
  --schema skills/workflow/comparative-decision-analysis/references/output-schema.json \
  --data <analysis-result.json>
```

Required test coverage in this suite:

- tie-break ordering
- missing-evidence handling
- single-option behavior
- coverage-gated recommendation behavior
