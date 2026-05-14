# Comparative Analysis Framework

Use this framework to compare build, buy, and hybrid options.

## 1. Decision Framing

- Decision statement:
- Time horizon:
- Hard constraints:
- Non-goals:

## 2. Alternatives

List at least 3:

1. Build in-house
2. Buy existing platform
3. Hybrid (control plane + existing tools)

## 3. Scoring Rubric

Use a 1-5 scale per criterion with weighted scoring.

| Criterion                  | Weight (%) | Notes                             |
| -------------------------- | ---------: | --------------------------------- |
| Determinism of outcomes    |         20 | stable decisions and reruns       |
| Human-gate handling        |         15 | explicit approvals and audit      |
| Target coverage            |         15 | GitHub, npm, VS Marketplace, etc  |
| Time to value              |         15 | onboarding speed                  |
| Total cost of ownership    |         15 | build + operate + maintain        |
| Extensibility              |         10 | adapter model and contracts       |
| Compliance/audit readiness |         10 | evidence quality and traceability |

## 4. Evaluation Table

| Alternative | Determinism | Human-Gate | Coverage | TTV | TCO | Extensibility | Compliance | Weighted Total |
| ----------- | ----------: | ---------: | -------: | --: | --: | ------------: | ---------: | -------------: |
| Build       |             |            |          |     |     |               |            |                |
| Buy         |             |            |          |     |     |               |            |                |
| Hybrid      |             |            |          |     |     |               |            |                |

## 5. Evidence Log

For each score, cite objective evidence:

- benchmark result:
- integration test outcome:
- pilot feedback:
- policy/compliance finding:

## 6. Sensitivity Check

- Which criterion changes could flip the result?
- Recompute with +/- 20% weight shift on top 2 criteria.

## 7. Recommendation

- Selected option:
- Why it wins:
- Key risks:
- 90-day execution plan:

## 8. Decision Record Stub

```yaml
decision:
alternatives_considered: []
selected_option:
criteria_confirmation_source:
key_evidence: []
open_risks: []
review_date:
```
