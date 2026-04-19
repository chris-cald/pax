---
name: handle-pr-feedback
description: "Coordinate PR review loops by triaging feedback severity, resolving low-risk issues, reverting work items when major rework is required, and keeping parent context slim through focused subagent delegation. Use when a PR has unresolved review comments, failing checks, or requested changes. Supports: (1) comment triage by severity, (2) low-risk auto-resolution, (3) blocker-driven work item reversion, (4) feedback summarization, (5) context minimization via subagents"
metadata:
  category: workflow
  aspects:
    - interaction-modes
  decisions:
    - id: feedback_severity
      trigger: after-triage
      yolo: [use_triage]
      collaborative:
        prompt: "Classify feedback severity"
        options:
          - id: trivial
            label: "Trivial (auto-fix)"
            action: auto-fix
          - id: minor
            label: "Minor (fix and re-request review)"
            action: resolve-minor
          - id: moderate
            label: "Moderate (manual fix)"
            action: resolve-moderate
          - id: major
            label: "Major (revert to in_progress)"
            action: revert-status
          - id: blocker
            label: "Blocker (revert and escalate)"
            action: revert-and-escalate
          - id: custom
            label: "Other action..."
            allow_freeform: true
        resume: "Proceed with selected action"
license: MIT
---

# Handle PR Feedback

## Overview

Monitor and respond to pull request review feedback. Triage comments by severity, automatically address low-risk issues when appropriate, and revert work items when requested changes imply broader rework. Keep the feedback loop coordinated between PR state, validation status, and work item status.

## Context Management

Because PR feedback loops can become verbose, keep the parent context slim.

### Rule

Prefer delegating narrow, self-contained work to subagents whenever possible.

Use subagents for:

- fetching and summarizing review comments
- isolating a single reviewer thread or concern
- reproducing a failing CI check
- implementing a narrowly scoped fix
- generating a before/after summary for one feedback cluster

Keep in the parent context only:

- current PR status
- severity classification summary
- chosen resolution strategy
- files changed
- validation outcome
- remaining blockers

### Parent / Subagent Split

#### Parent agent owns

- overall severity decision
- coordination with work item status
- decision to keep fixing vs. revert to `in_progress`
- reviewer coordination and re-requesting review
- final summary

#### Subagents own

- one feedback thread at a time
- one CI failure at a time
- one narrow code/doc/test fix at a time
- compact summaries of findings and changes

### Output Contract for Subagents

Each subagent should return a minimal report containing only:

- issue addressed
- severity
- root cause
- files changed
- validation performed
- unresolved risks

Do not paste full logs, large diffs, or full comment threads back into the parent context unless they are required for a decision.

## Orchestrator Compatibility

This skill should remain closed for modification and open for extension.

- Do not encode assumptions about a specific upstream orchestrator.
- Do not reference specific caller workflows by name.
- Expose a stable coordination pattern that any upstream skill can reuse.
- Let upstream skills decide when and why this feedback loop is invoked.

When composed by an upstream skill, this skill should behave as:

- a feedback triage and resolution coordinator
- a compact-state reducer for verbose review loops
- a reusable severity-to-action decision engine

## When to Use

Use this skill when:

- a PR has unresolved review comments or requested changes
- CI failures must be interpreted alongside reviewer feedback
- the next step is unclear: inline fix, broader rework, or revert to `in_progress`
- PR status and work item status must remain synchronized
- subsequent review rounds need a compact feedback summary

## When NOT to Use

Skip this skill when:

- a PR is awaiting initial review with no actionable feedback yet
- a PR is already merged or definitively abandoned
- the work is still in local development and has not entered PR review
- the problem is architectural discovery rather than feedback resolution

## Feedback Triage System

### Comment Classification

| Severity     | Type                           | Requires                  | Auto-Fix    | Revert | Example                 |
| ------------ | ------------------------------ | ------------------------- | ----------- | ------ | ----------------------- |
| **Trivial**  | Typo, formatting, comment      | Inline change             | ✅ Yes      | ❌ No  | Spelling error          |
| **Minor**    | Documentation, tests, metadata | Small code/doc change     | ✅ Optional | ❌ No  | Add docstring           |
| **Moderate** | Logic refinement               | Focused code change       | ❌ Manual   | ❌ No  | Suggest refactor        |
| **Major**    | Design flaw                    | Significant rework        | ❌ Manual   | ✅ Yes | Violates design pattern |
| **Blocker**  | Architectural or policy issue  | Scope or direction change | ❌ Escalate | ✅ Yes | Violates RFC            |

### Decision Tree

```asciiflow
Comment Received
├─ Trivial/Minor → Fix inline → Validate → Resolve thread / respond → Re-request review
├─ Moderate → Focused fix or discussion → Validate → Re-request review
└─ Major/Blocker
   ├─ Can refactor safely within scope → Fix + validate
   └─ Requires scope change or broader redesign → Revert to in_progress / escalate
```

## Workflow

### Execution Strategy

Run the feedback loop as a coordinator.

- Use the parent agent for triage, status decisions, and reviewer coordination.
- Use subagents for focused analysis and fixes.
- After each subagent pass, merge back only the compact result needed to decide the next step.
- Prefer one subagent per review thread or CI failure, and discard subagent-local detail once the compact summary has been merged into parent state.

### Phase 1: Fetch and Analyze

1. Fetch PR details, unresolved comments, requested changes, and failing checks.
2. Categorize comments by severity and topic.
   - Prefer a subagent to summarize comments into compact severity/topic clusters.
3. Assess impact:
   - blocker vs. non-blocker
   - code vs. docs vs. tests vs. policy
   - isolated fix vs. broader rework

### Phase 2: Decide Resolution Strategy

Choose the smallest safe path.

- **Trivial / Minor** → resolve inline when safe.
- **Moderate** → apply a focused fix and validate.
- **Major / Blocker** → decide whether to rework immediately or revert work item status to `in_progress` and escalate.
- **Mixed feedback** → resolve blockers first, then revisit non-blocking comments.

### Phase 3: Execute Resolution

For each resolution pass, prefer spawning a focused subagent for the smallest independent unit of work rather than carrying all review detail in the parent context.

Per pass:

1. Select the highest-priority unresolved item.
2. Delegate focused investigation or implementation.
3. Apply the fix.
4. Run the narrowest validation needed.
5. Update the PR or review thread state.
6. Reassess remaining feedback.

### Phase 4: Finalize

When the pass is complete:

- summarize what changed
- note validation results
- identify remaining blockers, if any
- decide whether to re-request review, continue another pass, or revert/escalate

## Interaction Modes

Uses `interaction-modes` aspect.

- `yolo`: triage and resolve low-risk feedback automatically
- `collaborative`: pause for ambiguity, moderate/major tradeoffs, or policy conflicts

## Tips & Best Practices

### 1. Keep Context Slim with Subagents

Use subagents to investigate and resolve one feedback cluster at a time.

Good parent-context summary:

```yaml
feedback_round: 2
blocking_items:
  - missing changeset
  - failing integration test
minor_items:
  - docstring clarification
next_action: fix blocking items, then re-request review
```

Avoid carrying:

- full CI logs
- full diff hunks
- every inline review comment verbatim
- repeated copies of unchanged PR state

### 2. Encourage Structured Feedback

Structured feedback improves triage quality and automation.

Example pattern:

```markdown
**[SEVERITY: BLOCKER]** Design violates RFC-007
Details: ...
Suggestion: Refactor to use decorator pattern
Priority: Must fix before merge
```

### 3. Escalate Early

If feedback suggests scope mismatch or policy conflict, escalate early instead of thrashing through repeated partial fixes.

### 4. Document Decisions

Capture major decisions in work item notes or PR summaries so later passes do not need to reconstruct prior reasoning.

## Summary

This skill provides a reusable, orchestrator-agnostic feedback loop that:

- triages PR feedback
- resolves low-risk issues efficiently
- identifies when broader rework is required
- minimizes context bloat
- composes cleanly with higher-level workflows
