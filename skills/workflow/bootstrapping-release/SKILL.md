---
name: bootstrapping-release
description: "Bootstrap and validate prerelease publishing readiness across GitHub, npm trusted publishing, and VS Code Marketplace/Azure DevOps, while keeping parent context slim through focused subagent delegation. Use before release execution when platform readiness, auth, workflow mapping, or publisher state is uncertain. Supports: (1) target discovery, (2) per-platform readiness validation, (3) safe bootstrap guidance, (4) compact readiness reporting, (5) context minimization via subagents"
metadata:
  category: workflow
  aspects:
    - interaction-modes
  decisions:
    - id: bootstrap_targets
      trigger: after-discovery
      yolo: [auto-detect]
      collaborative:
        prompt: "Select bootstrap targets"
        options:
          - id: github_only
            label: "GitHub only"
            action: bootstrapping-github-release-access
          - id: npm_only
            label: "npm trusted publishing only"
            action: bootstrapping-npm-trusted-publishing
          - id: vscode_only
            label: "VS Code Marketplace only"
            action: bootstrapping-vscode-marketplace-pat
          - id: all_targets
            label: "All applicable targets"
            action: dispatch-all-targets-inline
          - id: custom
            label: "Custom..."
            allow_freeform: true
        resume: "Proceed with selected bootstrap targets"
license: MIT
---

# Release Bootstrap

## Overview

Validate and initialize the external platform state required to publish from this repository.

This skill does not blindly mutate secrets or publish artifacts. It:

- discovers which release targets exist
- validates GitHub, npm, and VS Code Marketplace readiness
- initializes safe local/project configuration where appropriate
- produces an explicit readiness report
- identifies exact human actions required for any remaining setup

## Context Management

Bootstrap work spans multiple external systems and can quickly bloat the active context window.

### Rule

Use the parent agent as the coordinator and prefer subagents for one platform or one narrow readiness check at a time.

Use subagents for:

- GitHub repo/workflow inspection
- npm trusted-publishing validation
- VS Code Marketplace / Azure DevOps readiness
- one workflow-file audit at a time
- one auth/config blocker at a time

Keep in the parent context only:

- discovered targets
- per-platform readiness summary
- blockers
- recommended next action
- whether release execution may proceed

### Parent / Subagent Split

#### Parent agent owns

- target discovery
- deciding which bootstrap targets apply
- consolidating readiness across platforms
- deciding whether bootstrap is sufficient for release execution
- final report

#### Subagents own

- one platform at a time
- one workflow or registry configuration audit at a time
- one auth or publisher readiness check at a time
- compact summaries of findings

### Output Contract for Subagents

Each subagent should return only:

- target checked
- readiness result
- root cause of any blocker
- files inspected or changed
- validation performed
- exact remaining blocker

Do not inline full workflow files, full CLI output, or full settings dumps into the parent context unless required for a decision.

## Orchestrator Compatibility

This skill should remain closed for modification and open for extension.

- Do not encode assumptions about a specific upstream orchestrator.
- Do not reference specific caller workflows by name.
- Expose a stable platform-readiness coordination pattern that any upstream skill can reuse.
- Let upstream skills decide when and why this bootstrap flow is invoked.

When composed by an upstream skill, this skill should behave as:

- a release-platform readiness coordinator
- a compact-state reducer for verbose bootstrap loops
- a reusable platform validation and next-action engine

## When to Use

Use this skill when:

- release publishing has never been configured
- auth or CI state is unknown
- npm trusted publishing readiness is uncertain
- the VS Code Marketplace publisher or PAT may be missing
- a release flow should stop failing on setup friction

## When NOT to Use

Skip this skill when:

- GitHub, npm, and VS Code Marketplace bootstrap are already known-good
- the task is only to run a normal release flow
- credentials are intentionally managed entirely outside the repo and already validated
- the work is general feature development rather than platform/bootstrap validation

## Bootstrap Principles

- Prefer validation over mutation
- Prefer repository-native CI/CD over ad hoc local publishing
- Never store secrets in the repository
- Never print secrets to logs
- Never replace npm trusted publishing with long-lived npm write tokens if trusted publishing is available
- Use PAT only for VS Code Marketplace publishing, where `vsce` requires it

## Workflow

### Execution Strategy

Run the bootstrap flow as a coordinator.

- Use the parent agent for target selection, readiness decisions, and final reporting.
- Use subagents for focused per-platform checks.
- After each subagent pass, merge back only the compact result needed for the next decision.
- Prefer one subagent per platform, workflow audit, or auth blocker, and discard subagent-local detail once the compact summary has been merged into parent state.

### Inline Dispatch for `dispatch-all-targets-inline`

When the selected action is `dispatch-all-targets-inline`, do not look for a separate skill named `bootstrapping-all`.

Instead, dispatch inline from this skill in the following order:

1. run `bootstrapping-github-release-access`
2. run `bootstrapping-npm-trusted-publishing` if npm publication is in scope
3. run `bootstrapping-vscode-marketplace-pat` if a VS Code extension is in scope
4. merge the compact summaries into one readiness report

The parent context should keep only:

- target inventory
- per-platform readiness
- shared blockers
- recommended next action

### Phase 1: Discover Targets

Detect whether the repo contains:

- publishable npm packages
- a VS Code extension
- GitHub Actions release workflows
- Azure DevOps / Marketplace publishing requirements

Questions to answer:

- Does the repo publish to npm?
- Does the repo publish a VS Code extension?
- Is npm publication intended through GitHub Actions trusted publishing?
- Is VS Code publishing intended through local `vsce`, CI `vsce`, or manual VSIX upload?

Prefer separate subagents for:

- package inventory
- extension inventory
- workflow inventory

### Phase 2: Validate GitHub Access

Validate:

- git remote points to the expected GitHub repository
- current user can read repo state
- current user can push to intended release branches
- GitHub Actions workflows exist for release paths
- relevant workflows can read repository contents
- npm publish workflows request `id-token: write` if trusted publishing is used

### Phase 3: Validate npm Trusted Publishing

Validate:

- package targets are known
- package publish path is CI-based, not local-token-based
- workflow file names and paths match intended trusted-publisher configuration
- workflow requests `permissions: id-token: write`
- runtime is compatible with trusted publishing
- any private dependency install path uses read-only auth rather than a write token

### Phase 4: Validate VS Code Marketplace / Azure DevOps

Validate:

- extension package has a `publisher`
- Azure DevOps organization access exists
- Marketplace publisher exists and matches the extension manifest
- PAT is available through secure means
- `vsce` can package locally
- CI secrets or local auth path for `VSCE_PAT` are clear

### Phase 5: Summarize Readiness

Classify each target:

- ✅ ready
- ⚠️ partially ready
- ❌ blocked

Produce:

- per-target readiness
- exact blockers
- safe next action
- whether release execution may proceed
- whether publish may proceed

## Interaction Modes

Uses `interaction-modes` aspect.

- `yolo`: auto-detect targets and continue through low-risk validation
- `collaborative`: pause for ambiguous target selection, policy uncertainty, or manual bootstrap decisions

## Tips & Best Practices

### 1. Keep Context Slim with Subagents

Good parent-context summary:

```yaml
discovered_targets:
  github: true
  npm: true
  vscode_marketplace: true
readiness:
  github: ready
  npm: blocked
  vscode_marketplace: partial
blocking_items:
  - trusted publisher mapping missing for release workflow
  - VSCE_PAT not configured in CI
next_action: complete platform setup before publish-capable release run
```

Avoid carrying:

- full workflow YAML files
- full registry settings dumps
- long CLI auth output
- repeated copies of unchanged readiness state

### 2. Validate Before Mutating

Prefer detecting exact readiness gaps before suggesting bootstrap steps.

### 3. Keep Secrets Out of Context

Never paste tokens, PATs, or secret-like values into active context or repository files.

### 4. Separate Bootstrap from Release Execution

Use this skill to make the environment ready, then let release execution use that validated state.

## Summary

This skill provides a reusable, orchestrator-agnostic bootstrap flow that:

- discovers release targets
- validates platform readiness
- identifies exact bootstrap gaps
- minimizes context bloat
- composes cleanly with higher-level workflows
