---
name: process-pr
description: "Process a pull request end-to-end by creating draft PRs when needed, assessing state, validating readiness, coordinating feedback handling, gating ready-for-review on green jobs, and iterating until the PR is merged or concretely blocked while keeping parent context slim through focused subagent delegation. Use when a PR must be advanced through review, validation, CI, comment resolution, and merge. Supports: (1) draft PR creation, (2) PR state assessment, (3) review/CI triage, (4) compact decision loops, (5) orchestration of downstream skills, (6) context minimization via subagents"
metadata:
  category: workflow
  aspects:
    - interaction-modes
  decisions:
    - id: pr_next_action
      trigger: after-assessment
      yolo: [choose_smallest_safe_path]
      collaborative:
        prompt: "Select PR next action"
        options:
          - id: continue_validation
            label: "Continue validation"
            action: validate-pr
          - id: handle_feedback
            label: "Handle review feedback"
            action: use-handle-pr-feedback
          - id: prepare_mergeable_state
            label: "Drive toward merge"
            action: prepare-mergeable
          - id: stop_and_report
            label: "Stop and report blockers"
            action: stop-with-report
          - id: custom
            label: "Other action..."
            allow_freeform: true
        resume: "Proceed with selected PR action"
license: MIT
---

# Process PR

## Overview

Process a pull request end-to-end by assessing its current state, validating readiness, coordinating feedback handling, and advancing it through merge to the target branch.

This skill acts as a PR-level coordinator. It does not hardcode one downstream path; instead, it evaluates PR state and composes focused skills and subagents as needed. When this flow creates the PR, it must create it as a draft and keep it draft until all jobs are green for the current head commit.

## Non-Negotiable Gates

Use this deterministic gate sequence for every merge-driving loop:

1. Discover effective target-branch policy before merge-driving actions.
2. If this flow creates the PR, create it as draft.
3. Keep draft until all jobs are green for the current head commit.
4. After every fix commit push, re-run `/handle-pr-feedback` on the new head commit before any mergeability decision.
5. Do not treat prose as state. Consume only the structured `feedback_gate` payload.
6. Require `feedback_gate.head_sha` to match the current head commit.
7. Require `freshness == clear`, `unresolved_required_threads == 0`, `blocking_requested_reviews == 0`, `stale_blocking_reviews == 0`, and `next_action == clear` before merge-driving actions.

If any required gate is missing, stale, or inconsistent, classify as `unknown` and block merge-driving actions.

## Input/Output Contract

This skill consumes and enforces `feedback_gate` exactly as defined by `/handle-pr-feedback`.

Canonical freshness invariant:

- Any stale, missing, or inconsistent `feedback_gate` state is treated as `unknown` and therefore blocking for merge-driving actions.

Required enforcement:

- `feedback_gate.head_sha` must match current PR head.
- Any nonzero `unresolved_required_threads`, `blocking_requested_reviews`, or `stale_blocking_reviews` is blocking.
- `next_action == clear` is required before merge-driving actions.
- Enforce the canonical freshness invariant above.

Subagent return contract (compact only):

- task performed
- result
- root cause
- files changed
- validation performed
- unresolved blockers

## Context Management

Pull request processing can expand across diff review, comments, CI failures, policy checks, and release concerns. Keep the parent context compact.

### Rule

Use the parent agent as the PR coordinator and prefer subagents for one narrow PR concern at a time.

Use subagents for:

- PR state inspection
- one CI failure at a time
- one review thread or feedback cluster at a time
- one policy/versioning concern at a time
- one focused remediation pass at a time

Keep in the parent context only:

- PR status summary
- blocking items
- validation results
- files changed
- chosen next action
- merged / blocked decision

### Parent / Subagent Split

#### Parent agent owns

- PR-level coordination
- next-action decisions
- downstream skill selection
- stop-condition handling
- final summary

#### Subagents own

- one review thread, failing check, or policy concern at a time
- one focused investigation or fix at a time
- compact summaries of findings and changes

Do not inline full review threads, full CI logs, or full diffs into the parent context unless required for a decision.

## Orchestrator Compatibility

This skill should remain closed for modification and open for extension.

- Do not encode assumptions about a specific upstream orchestrator.
- Do not reference specific caller workflows by name.
- Expose a stable PR-processing coordination pattern that any upstream skill can reuse.
- Let upstream skills decide when and why PR processing is invoked.

When composed by an upstream skill, this skill should behave as:

- a PR state and decision coordinator
- a compact-state reducer for verbose PR loops
- a reusable router to downstream validation and feedback-handling skills

## When to Use

Use this skill when:

- a PR must be advanced through validation and review
- a branch must become a draft PR and then be processed to merge
- the next action for the PR is unclear
- review comments, CI state, and policy checks must be interpreted together
- the goal is to keep iterating until the PR is merged or a true blocker prevents progress

## When NOT to Use

Skip this skill when:

- work has not yet reached PR stage
- the task is only to create a new PR without review/CI/merge follow-through
- the PR is already merged or abandoned
- the issue is purely local development with no PR coordination needed

## Core Responsibilities

- assess PR state
- interrogate target-branch protections or rulesets before merge-driving actions
- inspect comments, requested changes, and CI results
- determine the smallest safe next action
- run repository-defined preflight gates when a backlog-coupled workflow is configured
- create new PRs in draft mode when PR creation is part of the flow
- mark a draft PR ready for review only after every job is green for the current head commit
- delegate to focused downstream skills where appropriate
- maintain compact state across iterative PR processing
- enforce fresh-state decisions through `/handle-pr-feedback`
- keep iterating until all jobs pass, all reviews are complete, all comments are resolved, and the PR is merged to the target branch

### Target Branch Policy Discovery

At the start of PR processing, interrogate the target branch's effective merge policy and tailor the loop accordingly.

Discover, at minimum:

- whether classic branch protection or repository rulesets are in effect
- required status checks for the target branch
- required approvals count
- whether `require_last_push_approval` is enabled
- whether review thread resolution is required
- allowed merge methods
- whether auto-merge or merge queue is required by policy

Treat this discovered policy as part of the PR state and use it to drive subsequent decisions. Do not assume that "mergeable" means directly mergeable, and do not assume that green checks are sufficient without comparing them to the target branch's actual requirements.

### Repository preflight hook

When repository instructions define backlog-coupled PR flow, run a preflight before merge-driving actions:

- confirm implementation checklist state is truthful (`## Tasks` marked as delivered);
- confirm acceptance criteria are verified and marked;
- confirm work item status is `ready-for-review`;
- confirm draft PR is linked from the work item where required.

If any preflight check fails, return `blocked` with explicit remediation steps instead of proceeding toward merge.

## Workflow

### Execution Strategy

Run PR processing as a coordinator.

- Use the parent agent for PR-level decisions and downstream skill selection.
- Use subagents for focused state inspection, CI investigation, and remediation passes.
- After each subagent pass, merge back only the compact result needed to decide the next step.
- Prefer one subagent per independent PR concern, and discard subagent-local detail once the compact summary has been merged into parent state.

### Completion Contract

The successful terminal state is: PR merged to the target branch.

Until that happens, continue the loop unless a blocker requires user or maintainer intervention. A PR is not complete while any of the following remains true:

- any job/check is failed, cancelled, skipped unexpectedly, pending, queued, or missing
- the PR is draft after all jobs are green and review is ready to begin
- any review is pending, changes requested, or otherwise incomplete
- any comment or review thread is unresolved, including outdated comments
- the branch is not mergeable or is behind the target branch
- the merge has not been performed and confirmed on the target branch

Draft/ready gate:

- If this workflow creates the PR, create it as draft (`draft: true`, `--draft`, or connector equivalent).
- Do not mark the PR ready for review until all jobs are green for the current head commit.
- If a new commit is pushed after checks pass, repeat the job gate for the new head before any ready-for-review or merge decision.

### Phase 0: Discover Target Branch Policy

Before any merge-driving action:

1. Identify the target branch for the PR.
2. Interrogate classic branch protection and/or repository rulesets for that target branch.
3. Record the effective requirements that apply to this PR.
4. Tailor the PR loop to those requirements before assessing merge readiness.

This phase must happen even when the PR already exists.

### Phase 1: Ensure Draft PR Exists

If processing starts from a branch without an existing PR and PR creation is in scope:

1. Verify the head branch, target branch, and PR preconditions.
2. Create the PR in draft mode.
3. Record the PR number, head commit, and target branch.
4. Do not request review or mark ready for review during creation.

### Phase 2: Assess PR State

Determine:

- PR open/draft/mergeable status
- current head commit and target branch
- effective branch-policy requirements discovered in Phase 0
- unresolved comments or requested changes
- failing or pending checks
- skipped/cancelled/missing jobs that require interpretation
- policy/versioning concerns
- whether the PR is on a release-critical path

Run `/handle-pr-feedback` in this phase to establish fresh PR review state and actionable-thread status.

`/handle-pr-feedback` is the authoritative coordinator for:

- freshness sweeps against the current head commit
- actionable unresolved review-thread detection
- explicit review-thread resolution when feedback is addressed
- dismissal or classification of stale blocking bot reviews

`/process-pr` must consume `/handle-pr-feedback` as a structured gate, not a prose hint. Apply the Input/Output Contract section above.

Policy interpretation for unresolved threads:

- when `require_thread_resolution == true`, require `unresolved_required_threads == unresolved_threads_total`
- when `require_thread_resolution == false`, require `unresolved_required_threads == unresolved_actionable_threads`
- treat any mismatch between these rules and the payload as `unknown`

Prefer subagents for:

- metadata/state inspection
- CI status inspection
- review-thread summarization

### Phase 3: Classify Blockers

Classify issues into:

- review feedback
- CI/build/test failures
- pending, skipped, cancelled, or missing jobs
- packaging/release concerns
- versioning/policy concerns
- mergeability / branch-state concerns

Use blocking/actionability classification returned by `/handle-pr-feedback`.

Determine whether the smallest safe next step is:

- continue validation
- handle review feedback
- remediate policy/versioning issues
- drive toward merge
- stop and report blockers

If blocking feedback state exists, the next step must be `handle review feedback`.

If any job is not green for the current head commit, the next step must be job remediation or waiting for completion. A draft PR must stay draft while this is true.

If target-branch policy requires approvals, last-push approval, thread resolution, specific checks, a merge queue, or auto-merge, classify those as explicit blockers until they are satisfied for the current head commit.

### Phase 4: Delegate Focused Work

Delegate only the narrowest appropriate work.

Examples:

- use `handle-pr-feedback` for structured review-loop resolution
- use prerelease or release-oriented skills when the PR is on a release path
- use focused subagents for one failing check or one blocker at a time
- mark the PR ready for review only after the current head has all jobs green

Follow the required loop in `/handle-pr-feedback` until the PR feedback state is clear.

After any fix commit pushed in response to review feedback:

1. refresh PR state for the new head commit
2. re-run `/handle-pr-feedback` before any mergeability decision
3. compare current checks and review state to the target branch policy discovered in Phase 0
4. reject any stale `/handle-pr-feedback` result whose `head_sha` does not match the current PR head
5. reject any `/handle-pr-feedback` result that is not emitted in the required `feedback_gate` shape

Never skip this post-push checkpoint. A commit that fixes code but does not refresh and consume the current `feedback_gate` is not merge-ready state.

Immediately before any merge-driving action:

1. re-run `/handle-pr-feedback` for the current head commit
2. if `unresolved_required_threads > 0`, run the resolve-threads path
3. re-run `/handle-pr-feedback` and require `unresolved_required_threads == 0`
4. only continue when `freshness == clear` and `next_action == clear`

### Phase 5: Reassess and Decide

After focused work returns:

- update compact PR state
- determine remaining blockers
- decide whether to continue, mark ready for review, merge, escalate, or stop
- report whether the PR is merged, still iterating, or blocked

Hard preconditions before marking ready for review:

- all jobs are green for the current head commit
- the PR is still open and points at the expected target branch

Hard preconditions before merging:

- all jobs are green for the current head commit
- all target-branch required checks are present and green for the current head commit
- `/handle-pr-feedback` returns `freshness == clear` for the current head commit
- `/handle-pr-feedback` returns a valid `feedback_gate` payload for the current head commit
- `/handle-pr-feedback.head_sha` matches the current PR head commit
- `/handle-pr-feedback.unresolved_required_threads == 0`
- when `/handle-pr-feedback.require_thread_resolution == true`, `/handle-pr-feedback.unresolved_threads_total == 0`
- `/handle-pr-feedback.blocking_requested_reviews == 0`
- `/handle-pr-feedback.stale_blocking_reviews == 0`
- `/handle-pr-feedback.next_action == clear`
- all reviews are complete with no outstanding requested changes
- target-branch approval requirements are satisfied for the current head commit
- target-branch merge method and queue or auto-merge requirements are satisfied
- the branch is mergeable against the target branch

If any precondition fails, report `blocked` and route to the appropriate remediation or feedback handling.

If all merge preconditions pass, merge the PR to the target branch and confirm the merge completed. Do not stop at "mergeable" when merge permission and policy allow the merge.

### Phase 6: Post-Merge Cleanup (Merge-Type Guarded)

After merge confirmation, run branch cleanup as an explicit, deterministic phase.

#### Required cleanup invariants

- Confirm PR is merged before cleanup (`state == MERGED`, `mergedAt != null`).
- Fetch and prune remotes before delete decisions.
- If currently on the merged head branch, switch to base branch first.
- Never delete local branches with unpushed or extra commits unless the selected guarded routine explicitly allows it.
- For any destructive local delete path, validate the guard condition first; if guard fails, report `blocked` with reason.

#### Merge-type selector

Select exactly one cleanup routine based on merge method:

1. `squash` (includes auto-merge configured as squash)
2. `rebase`
3. `merge-commit`

When merge method is not directly available from API output, infer with this fallback:

- If PR was merged by explicit `--squash` or auto-merge with squash policy, choose `squash`.
- Else if target policy allows only rebase and merge completed under that policy, choose `rebase`.
- Else choose `merge-commit`.

If merge type remains ambiguous, classify as `unknown` and block cleanup until resolved.

#### Common pre-cleanup script (run for all merge types)

```bash
# Inputs:
#   PR_NUMBER, HEAD_BRANCH, BASE_BRANCH

gh pr view "$PR_NUMBER" --json state,mergedAt,headRefName,baseRefName

git fetch origin --prune

current_branch="$(git branch --show-current)"
if [[ "$current_branch" == "$HEAD_BRANCH" ]]; then
  git switch "$BASE_BRANCH"
fi

git pull --ff-only origin "$BASE_BRANCH"
```

#### Guarded cleanup routine: squash

Use this for squash merges, where ancestry-based safe delete (`-d`) often fails by design.

```bash
# Remote cleanup (best effort)
git push origin --delete "$HEAD_BRANCH" || true
git fetch origin --prune

# Guard: local branch tip must match merged PR head SHA
local_tip="$(git rev-parse "$HEAD_BRANCH" 2>/dev/null || true)"

if [[ -z "$local_tip" ]]; then
  echo "local branch already absent"
elif [[ "$local_tip" == "$PR_HEAD_SHA" ]]; then
  git branch -D "$HEAD_BRANCH"
else
  echo "blocked: local branch tip differs from merged PR head; manual review required"
  exit 1
fi
```

#### Guarded cleanup routine: rebase

For rebase merges, ancestry should usually hold.

```bash
# Remote cleanup (best effort)
git push origin --delete "$HEAD_BRANCH" || true
git fetch origin --prune

if git merge-base --is-ancestor "$HEAD_BRANCH" "origin/$BASE_BRANCH"; then
  git branch -d "$HEAD_BRANCH"
else
  echo "blocked: branch not ancestor of base after expected rebase merge"
  exit 1
fi
```

#### Guarded cleanup routine: merge-commit

For merge-commit strategy, ancestry is required.

```bash
# Remote cleanup (best effort)
git push origin --delete "$HEAD_BRANCH" || true
git fetch origin --prune

if git merge-base --is-ancestor "$HEAD_BRANCH" "origin/$BASE_BRANCH"; then
  git branch -d "$HEAD_BRANCH"
else
  echo "blocked: branch not ancestor of base after merge-commit"
  exit 1
fi
```

#### Auto-merge note

Auto-merge does not replace cleanup. After auto-merge completion event:

1. Refresh PR merged state.
2. Resolve effective merge type (`squash`, `rebase`, or `merge-commit`).
3. Execute the corresponding guarded cleanup routine above.

#### Post-cleanup verification

```bash
git fetch origin --prune
git branch -vv
```

Report:

- cleanup routine selected
- local branch deleted or retained
- remote branch deleted or already absent
- any blocked guard and required human action

## Strict Thread Resolution Handling

When branch policy requires review thread resolution, treat every unresolved review thread as blocking, with no heuristic filtering.

### Required Source of Truth

- Pull request review threads must be fetched directly from the `pullRequest.reviewThreads` GraphQL field.
- `reviews`, `reviewDecision`, and status checks are not valid substitutes for thread state.
- If the `reviewThreads` query fails, is partial, or is older than the current head SHA, state is blocking.

### COMMENTED Review Anti-Pattern (Hard Prohibition)

`latestReviews[].state == "COMMENTED"` indicates only that a reviewer left a comment-type review. It says nothing about whether that reviewer has open inline threads.

**Never** classify a `COMMENTED` review as non-blocking without first fetching `reviewThreads`.

The following reasoning pattern is always wrong and always blocked:

> "The review state is COMMENTED, not APPROVED or CHANGES_REQUESTED, so it doesn't count and can be ignored."

The correct rule:

- Any `latestReviews` entry with `state: COMMENTED` **must** trigger a `reviewThreads` GraphQL fetch before any blocker classification or merge-driving action.
- A `COMMENTED` review entry is an explicit signal to inspect inline threads, not a signal that threads are absent or non-blocking.
- This rule applies to all reviewers without exception: humans, bots, and automated tools such as `copilot-pull-request-reviewer`.

### Blocking Rule

- If `require_thread_resolution` is true, merging is blocked unless `unresolved_threads_total` equals `0`.
- `unresolved_actionable_threads` is triage-only telemetry and must never be used as a merge gate when `require_thread_resolution` is true.
- `unresolved_required_threads` must equal `unresolved_threads_total` when `require_thread_resolution` is true. Any mismatch is blocking.

### Mandatory Pre-Merge Thread Gate

Immediately before any merge action, re-run `/handle-pr-feedback` for the current head SHA and enforce the Non-Negotiable Gates block and canonical freshness invariant above. If any gate value is nonzero where zero is required, do not merge.

### Merge-Attempt Recovery

If merge returns blocked by policy, do not wait blindly. Immediately:

1. Refresh current head SHA
2. Re-run thread gate snapshot
3. Classify blocker as `unresolved_thread`, `missing_approval`, `last_push_approval`, `missing_required_check`, or `queue_or_auto_merge_requirement`
4. Report required human action when the actor cannot satisfy the blocker

### Self-Approval Constraint

When the actor is the PR author, treat required approval as human-blocked unless another eligible reviewer has approved. Never retry merge in a loop without a changed approval state.

## Interaction Modes

Uses `interaction-modes` aspect.

- `yolo`: continue through low-risk PR validation and routing automatically
- `collaborative`: pause for ambiguity, policy conflicts, or tradeoff decisions

## Tips & Best Practices

### 1. Keep Context Slim with Subagents

Good parent-context summary:

```yaml
pr_state:
  status: open
  mergeable: false
blocking_items:
  - failing required check: integration-tests
  - unresolved review thread: missing changeset
next_action: delegate CI investigation, then run handle-pr-feedback
```

Avoid carrying:

- full PR diffs
- full review comment history verbatim
- full CI logs
- repeated copies of unchanged PR metadata

### 2. Choose the Smallest Safe Path

Do not default to broad remediation when a single focused step will clarify the next decision.

### 3. Separate Coordination from Execution

Let this skill coordinate. Let downstream skills and subagents do narrow work.

### 4. Stop on Ambiguity

Escalate when mergeability, policy, or release implications are unclear.

### 5. Fresh State Before Final Decision

Always re-run `/handle-pr-feedback` immediately before final classification. New reviews can arrive after CI succeeds and invalidate earlier conclusions.

### 6. Merge Is the Finish Line

Do not treat "ready for review", "approved", or "mergeable" as final states. Continue processing until the PR is merged to the target branch or a concrete blocker prevents further progress.

## Summary

This skill provides a reusable, orchestrator-agnostic PR-processing flow that:

- assesses PR state
- classifies blockers
- coordinates downstream action
- minimizes context bloat
- gates ready-for-review on green jobs
- drives PRs through confirmed merge
- composes cleanly with higher-level workflows
