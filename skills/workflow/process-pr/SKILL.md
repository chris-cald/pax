---
name: process-pr
description: "Process a pull request end-to-end by assessing state, validating readiness, coordinating feedback handling, and moving toward mergeable or release-ready status while keeping parent context slim through focused subagent delegation. Use when a PR must be advanced through review, validation, and decision-making. Supports: (1) PR state assessment, (2) review/CI triage, (3) compact decision loops, (4) orchestration of downstream skills, (5) context minimization via subagents"
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
            label: "Drive to mergeable state"
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

Process a pull request end-to-end by assessing its current state, validating readiness, coordinating feedback handling, and advancing it toward a mergeable or release-ready outcome.

This skill acts as a PR-level coordinator. It does not hardcode one downstream path; instead, it evaluates PR state and composes focused skills and subagents as needed.

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
- mergeability / release-readiness decision

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

### Output Contract for Subagents

Each subagent should return only:

- task performed
- result
- root cause
- files changed
- validation performed
- unresolved blockers

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
- the next action for the PR is unclear
- review comments, CI state, and policy checks must be interpreted together
- the goal is to reach mergeable, releasable, or clearly blocked state

## When NOT to Use

Skip this skill when:

- work has not yet reached PR stage
- the task is only to create a new PR
- the PR is already merged or abandoned
- the issue is purely local development with no PR coordination needed

## Core Responsibilities

- assess PR state
- inspect comments, requested changes, and CI results
- determine the smallest safe next action
- delegate to focused downstream skills where appropriate
- maintain compact state across iterative PR processing

## Workflow

### Execution Strategy

Run PR processing as a coordinator.

- Use the parent agent for PR-level decisions and downstream skill selection.
- Use subagents for focused state inspection, CI investigation, and remediation passes.
- After each subagent pass, merge back only the compact result needed to decide the next step.
- Prefer one subagent per independent PR concern, and discard subagent-local detail once the compact summary has been merged into parent state.

### Phase 1: Assess PR State

Determine:

- PR open/draft/mergeable status
- unresolved comments or requested changes
- failing or pending checks
- policy/versioning concerns
- whether the PR is on a release-critical path

Prefer subagents for:

- metadata/state inspection
- CI status inspection
- review-thread summarization

### Phase 2: Classify Blockers

Classify issues into:

- review feedback
- CI/build/test failures
- packaging/release concerns
- versioning/policy concerns
- mergeability / branch-state concerns

Determine whether the smallest safe next step is:

- continue validation
- handle review feedback
- remediate policy/versioning issues
- prepare mergeable state
- stop and report blockers

### Phase 3: Delegate Focused Work

Delegate only the narrowest appropriate work.

Examples:

- use `handle-pr-feedback` for structured review-loop resolution
- use prerelease or release-oriented skills when the PR is on a release path
- use focused subagents for one failing check or one blocker at a time

### Phase 4: Reassess and Decide

After focused work returns:

- update compact PR state
- determine remaining blockers
- decide whether to continue, escalate, or stop
- report whether the PR is now mergeable, release-ready, or still blocked

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

## Summary

This skill provides a reusable, orchestrator-agnostic PR-processing flow that:

- assesses PR state
- classifies blockers
- coordinates downstream action
- minimizes context bloat
- composes cleanly with higher-level workflows
