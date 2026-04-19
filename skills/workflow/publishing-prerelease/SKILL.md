---
name: publishing-prerelease
description: "Prepare, validate, and execute prerelease workflows for npm packages and VS Code extensions using repository-native processes, while keeping parent context slim through focused subagent delegation. Use when driving a repo from near-release-ready to prerelease-ready or prerelease-published state. Supports: (1) prerelease assessment, (2) dry-run packaging, (3) low-risk release repairs, (4) versioning readiness verification, (5) compact-state execution via subagents"
metadata:
  category: workflow
  aspects:
    - interaction-modes
  decisions:
    - id: prerelease_publish_path
      trigger: after-validation
      yolo: [use_repo_native_flow]
      collaborative:
        prompt: "Select prerelease publish path"
        options:
          - id: publish_ready_only
            label: "Stop at publish-ready state"
            action: stop-before-publish
          - id: ci_publish
            label: "Use repository-native CI publish path"
            action: use-ci-path
          - id: direct_publish
            label: "Use direct publish path if repo policy allows"
            action: use-direct-path
          - id: custom
            label: "Other action..."
            allow_freeform: true
        resume: "Proceed with selected publish path"
license: MIT
---

# Prerelease Publish

## Overview

Drive a repository to a valid prerelease-ready or prerelease-published state using the documented release workflow, with minimal and safe changes.

Prefer repository-native release flow over ad hoc commands. Treat versioning, packaging, CI, and publication as a coordinated release surface rather than isolated steps.

## Context Management

Prerelease work can quickly become verbose across package inventory, build output, packaging checks, CI state, and publication steps. Keep the parent context compact.

### Rule

Use the parent agent as the release coordinator and prefer subagents for one narrow release concern at a time.

Use subagents for:

- one package or artifact inventory pass at a time
- one dry-run or packaging failure at a time
- one versioning readiness check at a time
- one CI or workflow validation concern at a time
- one narrowly scoped repair at a time

Keep in the parent context only:

- current release phase
- package/extension readiness summary
- blockers
- files changed
- validation results
- chosen publish path
- next decision

### Parent / Subagent Split

#### Parent agent owns

- release phase coordination
- publish-path decision
- go / no-go determination
- stop-condition handling
- final report

#### Subagents own

- one package, extension, or artifact at a time
- one failing build/package/publishability check at a time
- one versioning or changeset check at a time
- one compact repair pass at a time

### Output Contract for Subagents

Each subagent should return only:

- task performed
- result
- root cause
- files changed
- validation performed
- unresolved blockers

Do not inline full logs, full CI transcripts, or long command output into the parent context unless required for a publish decision.

## Orchestrator Compatibility

This skill should remain closed for modification and open for extension.

- Do not encode assumptions about a specific upstream orchestrator.
- Do not reference specific caller workflows by name.
- Expose a stable release coordination pattern that any upstream skill can reuse.
- Let upstream skills decide when and why this prerelease flow is invoked.

When composed by an upstream skill, this skill should behave as:

- a release-readiness coordinator
- a compact-state reducer for verbose release loops
- a reusable validation-to-publish decision engine

## When to Use

Use this skill when:

- the user wants to ship a prerelease soon
- the repository is believed to be near release-ready
- release blockers are likely in packaging, metadata, scripts, versioning, or CI
- npm prerelease and/or VS Code pre-release are desired outcomes
- a compact but structured release-finisher loop is needed

## When NOT to Use

Skip this skill when:

- the repository is still in active feature development with no release target yet
- external platform/bootstrap readiness is unknown and unvalidated
- the work is a general feature implementation rather than release execution
- the problem is mainly architectural discovery rather than shipping

## Core Rules

- Always prefer the repository’s documented release process over ad hoc commands.
- Do not introduce workflows that conflict with changeset-based versioning, CI/CD release pipelines, or documented release process.
- Never manually edit package version fields.
- Prefer minimal, targeted changes over cleanup or refactors.
- Stop on ambiguity rather than inventing release process.

## Workflow

### Execution Strategy

Run the prerelease flow as a coordinator.

- Use the parent agent for release-phase decisions, publish-path selection, and final reporting.
- Use subagents for focused validation and repair work.
- After each subagent pass, merge back only the compact result needed to decide the next step.
- Prefer one subagent per failing check, package group, or versioning concern, and discard subagent-local detail once the compact summary has been merged into parent state.

### Phase 1: Discover and Assess

Determine:

- publishable npm packages
- VS Code extension target, if present
- release method: CI, direct, or hybrid
- current branch / changeset / artifact readiness

Prefer subagents for:

- package inventory
- extension inventory
- workflow inventory
- current registry / marketplace state checks

### Phase 2: Install and Validate

Run the minimum repository-native validation needed.

Typical commands may include:

```bash
pnpm install
pnpm build
pnpm test
```

If the repository defines narrower release validation commands, prefer those.

### Phase 3: Package Validation

Validate artifacts without publishing.

Typical checks may include:

```bash
npm pack --dry-run
pnpm dlx @vscode/vsce package --pre-release
```

Classify failures into:

- metadata
- packaging
- script wiring
- versioning
- source defect
- credentials/bootstrap gap
- workflow/publisher mismatch

### Phase 4: Low-Risk Repair

Allowed repair categories:

- metadata
- packaging includes/excludes
- scripts
- changelog / README / release note fixes
- changeset creation or correction
- narrow build/package defects directly blocking release

Do not:

- perform major refactors
- redesign architecture to satisfy release pressure
- manually edit version fields
- introduce ad hoc auth hacks

### Phase 5: Versioning Readiness

Follow repository policy:

- use changesets
- do not use manual version edits
- keep synchronized package groups aligned
- keep independently versioned artifacts independent

Determine whether the repository is in a valid prerelease-ready state according to local policy.

### Phase 6: Publish Decision

Choose the smallest safe publish path:

- stop at publish-ready state
- use repository-native CI publish path
- use direct publish path only if repository policy allows and readiness is already validated

Do not improvise a different release strategy midstream.

### Phase 7: Publish and Verify

If publication is in scope:

- execute the approved publish path
- stop on failure
- verify artifact and channel state after publication

If publication is not in scope:

- produce a complete publish-ready report
- state exact remaining human or CI actions

## Interaction Modes

Uses `interaction-modes` aspect.

- `yolo`: continue through low-risk release validation and repair automatically
- `collaborative`: pause for ambiguity, publish-path decisions, or policy conflicts

## Tips & Best Practices

### 1. Keep Context Slim with Subagents

Good parent-context summary:

```yaml
phase: versioning_readiness
packages_ready:
  - "@templjs/core"
  - "@templjs/cli"
vs_code_ready: true
blocking_items:
  - missing changeset for extension
next_action: add changeset, rerun narrow validation
```

Avoid carrying:

- full build logs
- repeated copies of unchanged registry state
- every dry-run output verbatim
- unrelated repo context

### 2. Prefer Repository-Native Flow

Use direct publish commands only when clearly consistent with repository policy.

### 3. Repair Narrowly

Treat prerelease work as release-finishing, not general cleanup.

### 4. Stop on Policy Conflicts

Escalate when requested publication behavior conflicts with repo versioning or CI rules.

## Summary

This skill provides a reusable, orchestrator-agnostic prerelease flow that:

- assesses release readiness
- validates packaging and versioning
- applies low-risk release fixes
- minimizes context bloat
- composes cleanly with higher-level workflows
