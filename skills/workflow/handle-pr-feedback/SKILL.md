---
name: handle-pr-feedback
description: "Coordinate PR review loops by triaging feedback severity, resolving low-risk issues, reverting work items when major rework is required, and keeping parent context slim through focused subagent delegation. Use when a PR has unresolved review comments, failing checks, or requested changes. Supports: (1) comment triage by severity, (2) low-risk auto-resolution, (3) blocker-driven work item reversion, (4) feedback summarization, (5) context minimization via subagents"
metadata:
  category: workflow
  aspects:
    - interaction-modes
    - state-freshness-gate
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
            label: "Major (revert to in-progress)"
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

## Non-Negotiable Thread Protocol

For each actionable unresolved review thread, run this sequence in order:

1. Verify the finding against current head state.
2. Implement a fix or record a no-fix rationale.
3. Validate the change with the narrowest relevant checks.
4. Push the commit.
5. Post an explicit thread reply with fix summary and commit SHA (or rationale).
6. Resolve the thread.
7. Re-run freshness sweep on the current head commit and emit updated `feedback_gate`.

Do not emit `freshness: clear` unless every required thread has both an explicit reply and a resolved state.

## Input/Output Contract

Subagent output contract (compact only):

- issue addressed
- severity
- root cause
- files changed
- validation performed
- unresolved risks

Caller-facing output contract:

- Emit `feedback_gate` for the current head commit.
- Use the `feedback_gate` schema and semantics in this file as the canonical caller contract.
- Canonical freshness invariant: any missing fields, stale `head_sha`, incomplete thread pagination, or inconsistent counters is normalized to `freshness: unknown`.
- `freshness: clear` is valid only when required threads are resolved and actionable addressed threads include explicit replies.

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
- decision to keep fixing vs. revert to `in-progress`
- reviewer coordination and re-requesting review
- final summary

#### Subagents own

- one feedback thread at a time
- one CI failure at a time
- one narrow code/doc/test fix at a time
- compact summaries of findings and changes

Do not paste full logs, large diffs, or full comment threads back into the parent context unless they are required for a decision.

When this skill returns control to a caller such as `/process-pr`, it must return a compact, explicit review-state classification for the current head commit rather than a prose-only summary.

Return format:

```yaml
feedback_gate:
  head_sha: "<40-char git sha>"
  freshness: clear | blocking | unknown
  review_decision: "APPROVED | REVIEW_REQUIRED | CHANGES_REQUESTED | ''"
  require_thread_resolution: <boolean>
  unresolved_threads_total: <integer>
  unresolved_required_threads: <integer>
  unresolved_actionable_threads: <integer>
  unresolved_outdated_threads: <integer>
  blocking_requested_reviews: <integer>
  stale_blocking_reviews: <integer>
  next_action: fix-feedback | resolve-threads | dismiss-stale-review | wait-for-review | clear
```

Field semantics:

- `head_sha` must be the PR head commit actually inspected during the freshness sweep.
- `freshness` is the overall gate classification for merge-driving callers.
- `review_decision` must reflect the live GitHub review decision for `head_sha`.
- `require_thread_resolution` must reflect effective target-branch policy for the PR.
- `unresolved_threads_total` counts all unresolved review threads.
- `unresolved_required_threads` counts unresolved threads that must be cleared before merge under current policy.
- `unresolved_actionable_threads` counts unresolved threads that still require a code, docs, test, or policy response.
- `unresolved_outdated_threads` is informational and counts unresolved threads that are outdated.
- `blocking_requested_reviews` counts requested-change reviews that still block on the current head.
- `stale_blocking_reviews` counts requested-change reviews made stale by a newer head and still requiring explicit dismissal or classification.
- `next_action` is the single next caller action implied by the current gate state.

Derivation rule for `unresolved_required_threads`:

- when `require_thread_resolution == true`: `unresolved_required_threads = unresolved_threads_total`
- when `require_thread_resolution == false`: `unresolved_required_threads = unresolved_actionable_threads`

Caller rule:

- Apply the canonical freshness invariant above to all malformed or stale responses.
- If `freshness: clear` is paired with `unresolved_required_threads > 0`, normalize to `unknown`.
- If `require_thread_resolution == true` and `unresolved_required_threads != unresolved_threads_total`, normalize to `unknown`.
- If `require_thread_resolution == false` and `unresolved_required_threads != unresolved_actionable_threads`, normalize to `unknown`.
- If `freshness: clear` is emitted without explicit thread replies for actionable threads addressed in the pass, normalize to `unknown`.

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
- the next step is unclear: inline fix, broader rework, or revert to `in-progress`
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
  └─ Requires scope change or broader redesign → Revert to in-progress / escalate
```

## Workflow

### Execution Strategy

Run the feedback loop as a coordinator.

- Use the parent agent for triage, status decisions, and reviewer coordination.
- Use subagents for focused analysis and fixes.
- After each subagent pass, merge back only the compact result needed to decide the next step.
- Prefer one subagent per review thread or CI failure, and discard subagent-local detail once the compact summary has been merged into parent state.

### Freshness Guard

This workflow is the PR-specific freshness adapter for `state-freshness-gate`.

Before any final mergeable/release-ready handoff decision, perform a fresh PR review-state sweep against the current head commit:

```bash
gh pr view <PR_NUMBER> --json reviewDecision,mergeStateStatus,updatedAt,statusCheckRollup,reviews,latestReviews
gh api graphql -f query='query { repository(owner:"OWNER", name:"REPO") { pullRequest(number:<PR_NUMBER>) { reviewThreads(first:100) { nodes { isResolved isOutdated path comments(first:5) { nodes { author { login } body url createdAt } } } } } } }'
```

Thread completeness requirement:

- paginate review threads until `hasNextPage == false`
- if pagination is incomplete or uncertain, classify as `unknown`

Freshness classification:

- `reviewDecision == CHANGES_REQUESTED` -> blocking
- unresolved required review thread -> blocking
- source unavailable/conflicting/uncertain recency -> unknown
- otherwise -> clear

Structured return rule:

- `clear` is valid only when the sweep targets the current `head_sha`, required thread rules are satisfied, and all required `feedback_gate` fields are populated.
- `blocking` is required when there are unresolved required threads, blocking requested changes, or stale blocking reviews that still need dismissal.
- `unknown` is required when the sweep was not run on the current head commit, output shape/fields are incomplete, or review-thread completeness cannot be established.

Actionability test:

- Actionable: requests a code/doc/test change or identifies a behavioral/policy risk.
- Non-actionable: status dashboards, coverage bots, summaries, or outdated threads with no required change.

COMMENTED review guard (hard prohibition):

`latestReviews[].state == "COMMENTED"` indicates only that a reviewer left a comment-type review. It says nothing about whether that reviewer has open inline threads. A `COMMENTED` review is NOT a non-blocking signal.

- Any `latestReviews` entry with `state: COMMENTED` **must** trigger a `reviewThreads` GraphQL fetch before classifying that reviewer's input as non-blocking.
- Do NOT conclude "the review is just a comment so it doesn't block" — that reasoning collapses two orthogonal concerns (approval state vs. thread resolution state) and will produce false-clear results.
- This rule applies to all reviewers: humans, bots, and automated tools such as `copilot-pull-request-reviewer`.

### Phase 1: Fetch and Analyze

1. Fetch PR details, unresolved comments, requested changes, and failing checks.
2. Categorize comments by severity and topic.
   - Prefer a subagent to summarize comments into compact severity/topic clusters.
3. Assess impact:
   - blocker vs. non-blocker
   - code vs. docs vs. tests vs. policy
   - isolated fix vs. broader rework

If freshness status is `unknown`, do not continue with stale data. Refresh first.

### Phase 2: Decide Resolution Strategy

Choose the smallest safe path.

- **Trivial / Minor** → resolve inline when safe.
- **Moderate** → apply a focused fix and validate.
- **Major / Blocker** → decide whether to rework immediately or revert work item status to `in-progress` and escalate.
- **Mixed feedback** → resolve blockers first, then revisit non-blocking comments.

When reverting status, preserve checklist truthfulness: do not leave previously marked checklist items checked if the reverted scope invalidates them.

### Phase 3: Execute Resolution

For each resolution pass, prefer spawning a focused subagent for the smallest independent unit of work rather than carrying all review detail in the parent context.

Per pass:

1. Select the highest-priority unresolved item.
2. Delegate focused investigation or implementation.
3. Apply the fix.
4. Run the narrowest validation needed.
5. Post explicit thread feedback and resolve addressed threads.
6. Reassess remaining feedback.

### Phase 4: Finalize

When the pass is complete:

- summarize what changed
- note validation results
- identify remaining blockers, if any
- decide whether to re-request review, continue another pass, or revert/escalate

Hard precondition before reporting `clear`, `mergeable`, `publish-ready`, or `release-ready` to callers:

- freshness sweep executed for current head commit
- `reviewDecision != CHANGES_REQUESTED`
- unresolved required review threads == 0
- stale blocking reviews requiring dismissal == 0
- all required output fields populated for the current head commit
- `feedback_gate` emitted in the required shape

If any precondition fails, return `blocking` or `unknown` with explicit next action.

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
