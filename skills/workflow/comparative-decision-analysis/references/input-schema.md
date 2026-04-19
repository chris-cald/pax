# Comparative Decision Analysis Input Schema

Use this schema with `scripts/score_with_guardrails.py`.
Use `input-schema.json` in this directory as the machine-readable source of truth.

## Required Fields

| Field                          | Type    | Notes                                                                                            |
| ------------------------------ | ------- | ------------------------------------------------------------------------------------------------ |
| `decision`                     | string  | Decision statement.                                                                              |
| `run_id`                       | string  | Optional stable identifier for reproducible runs.                                                |
| `criteria_confirmed`           | boolean | Must be `true` unless running a one-shot simulation.                                             |
| `criteria_confirmation_source` | enum    | Required when `criteria_confirmed=true`; one of `user-confirmed`, `provided-input`, `yolo-mode`. |
| `current_platform`             | string  | Current platform to optimize.                                                                    |
| `criteria`                     | array   | Must include full criterion contract fields.                                                     |
| `alternatives`                 | array   | Must include at least 2 alternatives for scoring.                                                |
| `discovery`                    | object  | Must record whether external discovery completed or was explicitly blocked.                      |
| `independent_evaluations`      | array   | One isolated evaluator record per alternative.                                                   |

## Optional Fields

| Field                                     | Type     | Default                                   |
| ----------------------------------------- | -------- | ----------------------------------------- |
| `score_scale`                             | string   | `0-100` (`1-5` supported)                 |
| `major_platforms`                         | string[] | `["chatgpt","claude","gemini","copilot"]` |
| `weights.major_platform_average`          | number   | `0.6`                                     |
| `weights.current_platform`                | number   | `0.4`                                     |
| `recommendation_rules.*`                  | number   | Script defaults                           |
| `recommendation_rules.min_coverage`       | number   | `0.8`                                     |
| `independent_evaluations[].evidence_refs` | string[] | `[]`                                      |

## Criterion Contract

Each criterion must include:

- `id`
- `name`
- `weight`
- `metric`
- `data_source`
- `scoring_rule`

## Alternative Contract

Each alternative must include:

- `id`
- `name`
- `type` (`internal|compose|external|build-new`) when known; default is `internal`
- `effort` (`S|M|L`)
- `risk` (`Low|Med|Medium|High`)
- `feasible` (`true|false`)
- `scores` (platform -> criterion -> numeric score or `null`)
- `justification` (explicit option-level rationale)

When `discovery.external_discovery_done=true`, at least one alternative must set `type=external`.

## Discovery Contract

Top-level `discovery` is required:

- `external_discovery_done` (`true|false`)
- `external_discovery_blocked` (`true|false`)
- `block_reason` (required when blocked)
- `checked_at` (optional ISO timestamp)

## Independent Evaluation Contract

Each independent evaluation record must include:

- `alternative_id` (must match exactly one alternative `id`)
- `evaluator_id` (must be unique across all alternatives)
- `isolation_confirmed` (must be `true`)
- `summary` (concise isolated finding summary)
- `evidence_refs` (optional array of evidence pointers)

## Missing Evidence

- Use `null` for missing criterion scores.
- Missing values are excluded from weighted averages.
- Coverage is computed and used for recommendation gating.
