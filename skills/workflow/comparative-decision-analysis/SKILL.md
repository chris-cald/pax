---
name: comparative-decision-analysis
description: "Comparative decision analysis workflow with mandatory discovery (including external options), criteria derivation and confirmation, explicit evidence discipline, hard-constraint gating, and deterministic scoring. Use for vendor analysis, head-to-head comparisons, competitor analysis, tool/architecture/workflow selection, and build-vs-buy decisions when you need reliable, auditable recommendations."
---

# Comparative Decision Analysis

Produce a defensible decision by combining:

- Mandatory criteria confirmation and evidence discipline.
- Deterministic scoring and ranking.
- Explicit score scale, effort and risk tie-breaks, and coverage visibility.

## Inputs

- Decision statement.
- Current platform.
- Primary user and workflow context.
- Hard constraints and non-goals.
- Time horizon.
- Initial alternatives or discovery scope.
- Optional evaluation criteria, weights, and scoring scale.

**Accepting JSON from discovering-alternatives**: When using `discovering-alternatives` for discovery (Step 2), request JSON output and transform using `../discovering-alternatives/references/integration-guide.md`. The JSON format pre-populates `decision`, `alternatives`, and baseline context, streamlining the workflow.

## Workflow

1. Frame decision and constraints.
2. **Run discovery using `discovering-alternatives` skill** (see `../discovering-alternatives/SKILL.md`).
   - Delegate to `discovering-alternatives` for exhaustive discovery (build, buy, hybrid options).
   - Request JSON output format for automated transformation: `output as JSON`
   - Transform JSON using `../discovering-alternatives/references/integration-guide.md`
   - Accept the ranked option list from `discovering-alternatives` as input to comparative analysis.
   - If `discovering-alternatives` is unavailable, fall back to `references/discovery-protocol.md` (legacy).
3. Normalize alternatives for comparative scoring (skip if using JSON from discovering-alternatives).
   - Require at least two alternatives before scoring (enforced by `discovering-alternatives`).
   - Mark each alternative `feasible` or `infeasible` (already done by `discovering-alternatives`).
4. Derive criteria from intended use.
   - Use `references/rubric-packs.md` as a starting point, then adapt.
5. Present the evaluation criteria, weights, score scale, and platform set, then wait for confirmation.
   - Do not continue scoring in the same turn until the user confirms or refines criteria.
   - If criteria are already explicitly provided, record `criteria_confirmation_source=provided-input`.
   - If running in yolo mode, record `criteria_confirmation_source=yolo-mode`.
   - Otherwise record `criteria_confirmation_source=user-confirmed`.
6. Evaluate each alternative in an isolated evaluator subagent.
   - Use one evaluator per alternative with unique `evaluator_id`.
   - Run evaluator subagents in parallel when possible.
   - Keep evaluator contexts isolated; do not let evaluators see each other outputs.
7. Prepare input using `references/input-schema.md` and `references/input-schema.json`.
   - Include discovery state under `discovery`.
   - Include one `independent_evaluations` record per alternative.
8. Execute deterministic harness:

   ```bash
   python3 skills/workflow/comparative-decision-analysis/scripts/run_comparative_decision_harness.py \
     --input <analysis-input.json> \
     --output-dir <run-output-dir>
   ```

9. Run reliability checks.
   - Use `references/scenario-bakeoff-protocol.md` for bakeoff evaluation.
   - Run sensitivity checks for close results.
   - Validate the generated result against `references/output-schema.json`.
10. Produce record using `assets/comparative-decision-record-template.md`.

## Guardrails

- Apply `references/quality-gates.md` as the single source of truth for pass/fail checks.
- Do not bypass confirmation or independent evaluator records except with explicit simulation flags.
- Keep all scores traceable to evidence and isolated evaluator summaries.
- Apply an agentic-eval loop (Generate → Evaluate → Critique → Refine), max 3 iterations.
- Use structured JSON for critique output and stop if no improvement between iterations.

## Testing

Run guardrail tests before relying on scoring or harness changes:

```bash
python3 test/skills/workflow/comparative-decision-analysis/test_score_with_guardrails.py
node skills/workflow/comparative-decision-analysis/scripts/validate_json_contract.mjs \
   --schema skills/workflow/comparative-decision-analysis/references/input-schema.json \
   --data <analysis-input.json>
node skills/workflow/comparative-decision-analysis/scripts/validate_json_contract.mjs \
   --schema skills/workflow/comparative-decision-analysis/references/output-schema.json \
   --data <analysis-result.json>
```

## References

- **Discovery**: `../discovering-alternatives/SKILL.md` (primary), `references/discovery-protocol.md` (legacy fallback)
- Input contract: `references/input-schema.md`
- Machine-readable schema: `references/input-schema.json`
- Output contract: `references/output-schema.md`
- Machine-readable output schema: `references/output-schema.json`
- Rubric packs: `references/rubric-packs.md`
- Quality gates: `references/quality-gates.md`
- Bakeoff protocol: `references/scenario-bakeoff-protocol.md`
- Reusable bakeoff fixture: `assets/bakeoff-fixture.v1.json`
- Reusable bakeoff results template: `assets/bakeoff-results-template.v1.json`
- Decision record template: `assets/comparative-decision-record-template.md`

## Related Skills

**Upstream (Discovery Phase)**:

- [[discovering-alternatives]]: Exhaustive option discovery with evidence-backed ranking (use in Step 2)

**Downstream (Selection Phase)**:

- [[evaluating-alternative]]: Deep-dive evaluation of a single option (useful for top-ranked alternatives)

**Workflow Sequence**:

```text
1. discovering-alternatives → 2. comparative-decision-analysis → 3. evaluating-alternative
   (exhaustive discovery)       (criteria-based scoring)            (deep dive on the preferred option)
```
