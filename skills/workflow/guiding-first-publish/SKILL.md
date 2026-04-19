---
name: guiding-first-publish
description: "Guide a repository from zero release setup to first successful publish or first publish-ready state using a compact, reusable first-run flow. Use when release infrastructure may be incomplete, platform trust boundaries are not yet established, and the goal is to get from zero to first publish with minimal thrash. Supports: (1) release-surface discovery, (2) bootstrap validation, (3) guided trust-boundary setup, (4) repo-local release preparation, (5) first publish execution, (6) compact-state orchestration via subagents"
metadata:
  category: workflow
  aspects:
    - interaction-modes
  decisions:
    - id: first_publish_next_action
      trigger: after-phase-review
      yolo: [choose_smallest_safe_path]
      collaborative:
        prompt: "Select next first-publish action"
        options:
          - id: bootstrap
            label: "Run bootstrap validation"
            action: use-bootstrapping-release
          - id: remediate_bootstrap
            label: "Resolve bootstrap blockers"
            action: resolve-bootstrap-blockers
          - id: prepare_repo
            label: "Prepare repository for first publish"
            action: prepare-repo
          - id: validate_publish
            label: "Validate publish path"
            action: validate-publish-path
          - id: publish
            label: "Execute first publish"
            action: use-publishing-prerelease
          - id: stop
            label: "Stop and report blockers"
            action: stop-with-report
          - id: custom
            label: "Other action..."
            allow_freeform: true
        resume: "Proceed with selected first-publish action"
license: MIT
---

# Guide First Publish

## Overview

Guide a repository from zero release setup to first successful publish or first publish-ready state.

This skill is the reusable first-run coordinator. It does not hardcode a single publish mechanism. Instead, it:

- discovers the repository’s release surface
- validates external platform readiness
- distinguishes repo-local automation from human-gated trust setup
- coordinates repair and validation loops
- uses existing release skills and runbooks where available
- minimizes parent-context bloat throughout the flow

## First-Run Principle

A first publish has two kinds of work:

### Repo-local work

This can often be automated:

- package metadata
- release workflows
- packaging configuration
- scripts
- changelog / README / changesets
- dry-run validation
- CI and PR readiness

### Trust-boundary work

This usually cannot be fully automated and must be guided:

- npm trusted publisher mapping
- Azure DevOps organization / Marketplace publisher setup
- PAT creation
- CI secret provisioning
- external platform approval/configuration

This skill automates the first category and guides the second.

## Context Management

First-run flows sprawl quickly across external platforms, repo plumbing, validation, CI, and PR coordination.

### Rule

Use the parent agent as the first-publish coordinator and prefer subagents for one narrow concern at a time.

Use subagents for:

- one platform readiness check at a time
- one release workflow audit at a time
- one packaging/build blocker at a time
- one PR/review blocker at a time
- one narrowly scoped repair at a time

Keep in the parent context only:

- current phase
- discovered publish targets
- platform readiness summary
- active blockers
- files changed
- validation summary
- next_action (decision + exact next step)

### Parent / Subagent Split

#### Parent agent owns

- phase coordination
- go / no-go / publish-ready-only decisions
- trust-boundary gating
- selection of downstream skills
- final report

#### Subagents own

- one platform or workflow audit at a time
- one blocker diagnosis at a time
- one compact repair pass at a time
- one verification surface at a time

### Output Contract for Subagents

Each subagent should return only:

- task performed
- result
- root cause
- files changed
- validation performed
- unresolved blockers

Do not inline full logs, full workflow files, or long command transcripts into the parent context unless required for a hard decision.

## Orchestrator Compatibility

This skill should remain closed for modification and open for extension.

- Do not encode assumptions about a specific upstream orchestrator.
- Do not require a specific repository layout beyond discoverable release signals.
- Prefer repo-local runbooks when they exist.
- Fall back to direct skill orchestration when repo-local runbooks do not exist.

When composed by an upstream skill, this skill should behave as:

- a first-publish coordinator
- a compact-state reducer for verbose bootstrap/release loops
- a reusable zero-to-first-publish decision engine

## When to Use

Use this skill when:

- the repository has never published before
- the release path is partially configured or unknown
- trusted publishing / publisher setup may be incomplete
- the goal is to get from zero to first publish with guided flow instead of ad hoc setup
- the user wants one orchestrator to drive both setup and first release preparation

## When NOT to Use

Skip this skill when:

- external platform readiness is already known-good
- normal release automation is already in place and repeatable
- the task is only to perform a standard prerelease on an already bootstrapped repo
- the task is general feature development rather than release setup

## Core Rules

- Prefer validation over mutation
- Prefer repository-native release flow over ad hoc commands
- Never store secrets in the repository
- Never print secret values to logs
- Never manually edit version fields when repo policy requires changesets
- Distinguish clearly between repo-local blockers and trust-boundary blockers
- Stop on ambiguity rather than inventing release process

## Workflow

### Execution Strategy

Run the first-publish flow as a coordinator.

- Use the parent agent for phase transitions and hard decisions.
- Use subagents for focused inspection, repair, and verification.
- After each subagent pass, merge back only the compact result needed for the next decision.
- Prefer one subagent per independent blocker, and discard subagent-local detail once the compact summary has been merged into parent state.

### Phase 1: Discover Release Surface

Determine:

- whether the repo publishes npm packages
- whether the repo publishes a VS Code extension
- whether a repo-local release runbook exists
- whether publish should be CI-based, direct, or hybrid
- whether release policy appears to be changeset-driven
- whether the repository is near release-ready or still missing basic plumbing

Signals to inspect:

- package manifests
- `.github/workflows/`
- release docs such as `docs/release-drill.md`
- extension manifest / publisher fields
- changeset config if present

Preferred delegation:

- one subagent for package inventory
- one subagent for workflow inventory
- one subagent for extension inventory
- one subagent for release-doc discovery

### Phase 2: Validate Bootstrap Readiness

Use `/bootstrapping-release`.

Interpret the result as one of:

- `proceed_full_drill`
- `proceed_publish_ready_only`
- `stop_blocked`

Use the Phase 0 semantics from the repo-local release runbook when that runbook exists.

If bootstrap returns blockers, classify them into:

- repo-local bootstrap blockers
- trust-boundary blockers
- ambiguous blockers

### Phase 3: Resolve Bootstrap Blockers

#### Repo-local bootstrap blockers

These may be addressed directly when safe, for example:

- missing workflow permissions
- missing packaging metadata
- missing publisher field
- workflow filename mismatch
- release-doc / script mismatch

Prefer the smallest safe repair and rerun only the narrowest validation.

#### Trust-boundary blockers

These must be guided, not forced.

Examples:

- npm trusted publisher not configured in npm UI
- Azure DevOps organization not established
- Marketplace publisher missing
- `VSCE_PAT` not yet created or stored
- external CI secret not provisioned

For trust-boundary blockers:

- produce one exact human action at a time
- wait for completion signal
- rerun bootstrap validation after each completed step

Do not bundle multiple human setup steps into one large wall of instructions unless explicitly requested.

### Phase 4: Prepare Repository for First Publish

If a repo-local `release-drill.md` exists and is credible, use it as the runbook.

If a repo-local runbook is used, treat it as authoritative for release sequencing and use direct skill orchestration only to fill gaps the runbook does not cover.

If not, orchestrate equivalent phases directly using:

- `/triaging-release` for packaging, workflow, or release-plumbing blockers
- `/process-pr` when PR-level state is ambiguous
- `/handle-pr-feedback` when the PR state is straightforward and the main need is review-loop resolution
- `/publishing-prerelease` for prerelease execution readiness and publish coordination

At this phase, drive the repository toward one of:

- fully publishable
- publish-ready-only
- blocked with exact next action

### Phase 5: Validate First Publish Path

Before executing the first publish, confirm:

- the intended publish path is repository-native
- package/versioning state is valid
- packaging/dry-run checks succeed
- the selected publish target is actually in scope
- trust-boundary blockers are cleared or deliberately out of scope

If validation fails for packaging or release plumbing, delegate to `/triaging-release`.

If validation fails because PR/CI/review state is tangled, delegate to `/process-pr`.

### Phase 6: Execute First Publish

Use `/publishing-prerelease` as the publish coordinator.

If this first run is constrained by Phase 2/3 outcomes:

- do not force publish
- produce a publish-ready-only result instead
- list the exact remaining human or CI actions

If publish fails:

- do not switch strategies mid-run
- do not introduce new auth mechanisms ad hoc
- return to triage or stop with a clear failure report

### Phase 7: Verify and Baseline

After success or publish-ready completion, produce a reusable baseline:

- discovered release targets
- working publish path
- required external platform mappings
- remaining manual trust-boundary steps, if any
- recommended follow-up hardening actions

This phase turns a first-run experience into a repeatable future release path.

## Phase Decision Semantics

At the end of each major phase, choose exactly one:

### `continue`

Use when the current path is valid and the next phase may proceed.

### `needs_human_step`

Use when the next blocker is a trust-boundary action that must be completed outside the repo.

### `publish_ready_only`

Use when the repo can be driven to a publish-ready state but actual publish cannot be completed in this run.

### `stop_blocked`

Use when progression is not safe or the release target is too ambiguous.

## Output Template

```yaml
phase: <current_phase>
release_surface:
  npm: true | false
  vscode: true | false
  repo_runbook: present | absent
bootstrap_decision: proceed_full_drill | proceed_publish_ready_only | stop_blocked | not_run
active_decision: continue | needs_human_step | publish_ready_only | stop_blocked
readiness:
  github: ready | partial | blocked | not_applicable
  npm: ready | partial | blocked | not_applicable
  vscode: ready | partial | blocked | not_applicable
blockers:
  - <item>
files_changed:
  - <path>
validation:
  - <compact validation result>
next_action:
  decision: continue | needs_human_step | publish_ready_only | stop_blocked
  step: <exact next step>
```

## Interaction Modes

Uses `interaction-modes` aspect.

- `yolo`: continue through low-risk validation and repo-local repair automatically
- `collaborative`: pause for trust-boundary setup, ambiguous release targets, policy conflicts, or risky workflow edits

## Tips & Best Practices

### 1. Treat Human-Gated Setup as a Queue

For first-run setup, avoid giving ten steps at once.

Prefer:

- one exact blocker
- one exact action
- one revalidation

Good pattern:

```yaml
active_decision: needs_human_step
blockers:
  - npm trusted publisher not configured
next_action:
  decision: needs_human_step
  step: configure trusted publisher for workflow release.yml in npm package settings, then rerun /bootstrapping-release
```

### 2. Prefer Repo-Local Runbooks When Available

If the repo already has a credible release drill, use it instead of inventing a parallel flow.

### 3. Separate Publishability from Publishing

A successful first-run outcome may be:

- first publish completed
- or repo proven publish-ready with exact remaining external actions

Both are useful states.

### 4. Produce a Reusable Baseline

The main value of the first run is not just the first publish — it is the reusable release path discovered and documented afterward.

## Summary

This skill provides a reusable first-run experience that:

- discovers the repository’s release surface
- validates external platform readiness
- guides trust-boundary setup one step at a time
- coordinates repo-local release preparation
- executes or prepares the first publish
- leaves behind a reusable baseline for future releases
