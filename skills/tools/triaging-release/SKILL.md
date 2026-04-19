---
name: triaging-release
description: "Diagnose and repair release blockers quickly, with a bias toward packaging, metadata, workflow, and configuration fixes over source-code churn, while keeping parent context slim through focused subagent delegation. Use when packaging or prerelease publication fails and the blocker must be diagnosed and repaired quickly. Supports: (1) blocker classification, (2) release-focused repair sequencing, (3) compact-state triage loops, (4) safe escalation boundaries, (5) context minimization via subagents"
metadata:
  category: tool
  aspects:
    - interaction-modes
license: MIT
---

# Release Triage

## Overview

Diagnose and repair release blockers quickly, with a bias toward packaging, metadata, workflow, and configuration fixes over source-code churn.

Treat release triage as a constrained repair loop: isolate the blocker, apply the smallest safe fix, rerun only the narrowest validating step, and stop when the issue is resolved or clearly exceeds release-plumbing scope.

## Context Management

Release failure analysis can become noisy because build logs, pack output, CI logs, and workflow diagnostics all expand quickly.

### Rule

Use the parent agent as the triage coordinator and prefer subagents for one failing release concern at a time.

Use subagents for:

- one failing build or packaging check at a time
- one workflow/publisher mismatch at a time
- one versioning or metadata defect at a time
- one narrowly scoped remediation pass at a time

Keep in the parent context only:

- blocker summary
- root-cause hypothesis
- chosen repair path
- files changed
- validation outcome
- whether publish may proceed

### Parent / Subagent Split

#### Parent agent owns

- blocker prioritization
- repair-path decision
- stop/escalate decision
- final triage report

#### Subagents own

- one failing check at a time
- one package or artifact concern at a time
- one narrow repair and rerun cycle at a time
- compact summaries of findings and changes

### Output Contract for Subagents

Each subagent should return only:

- issue investigated
- result
- root cause
- files changed
- validation performed
- unresolved blockers

Do not inline full build logs, full CI logs, or long command transcripts into the parent context unless required for an escalation decision.

## Orchestrator Compatibility

This skill should remain closed for modification and open for extension.

- Do not encode assumptions about a specific upstream orchestrator.
- Do not reference specific caller workflows by name.
- Expose a stable triage pattern that any upstream skill can reuse.
- Let upstream skills decide when and why release triage is invoked.

When composed by an upstream skill, this skill should behave as:

- a release-blocker diagnosis coordinator
- a compact-state reducer for noisy failure loops
- a reusable root-cause-to-repair decision engine

## Goal

Diagnose and repair release blockers quickly, with a bias toward packaging and metadata fixes over source-code churn.

## Diagnose In This Order

1. repository state issues
2. missing or invalid credentials
3. incorrect versions or prerelease strategy
4. missing package metadata
5. packaging include/exclude problems
6. broken release scripts
7. workflow or marketplace-specific constraints
8. true source-code defects

## Preferred Repair Order

1. docs and metadata
2. package scripts
3. packaging config
4. version alignment
5. workflow / publisher / auth configuration
6. narrow code fix required for packaging/build
7. stop and report if broader than release plumbing

## Common Checks

```bash
rtk git status
rtk pnpm build
rtk pnpm test
rtk npx vsce package --pre-release
rtk npm pack --dry-run
```

## Repair Policy

Automatically repair:

- missing metadata fields
- script wiring errors
- changelog/readme issues
- version mismatches allowed by repository policy
- packaging path errors
- missing included assets
- small workflow / config mismatches that are clearly release-plumbing issues

Do not automatically repair:

- deep runtime bugs
- major test failures unrelated to packaging
- architecture-level problems
- broad refactors disguised as release fixes

## Workflow

### Execution Strategy

Run triage as a constrained coordinator.

- Use the parent agent for prioritization and escalation decisions.
- Use subagents for focused diagnosis and narrow repairs.
- After each subagent pass, merge back only the compact result needed to decide the next step.
- Prefer one subagent per independent blocker, and discard subagent-local detail once the compact summary has been merged into parent state.

### Phase 1: Identify the Active Blocker

Determine:

- which command failed
- whether the failure is local, CI-based, or marketplace/registry-based
- whether the blocker is packaging/configuration versus deeper source behavior

### Phase 2: Classify Root Cause

Classify the failure into the diagnose order above.

Prefer the simplest explanation consistent with the evidence.

### Phase 3: Apply Narrow Repair

Apply the smallest safe fix in preferred repair order.

Then rerun only the narrowest validation command necessary to confirm the fix.

### Phase 4: Decide Whether to Continue

After each repair pass, decide whether:

- the blocker is resolved
- another narrow pass is warranted
- the issue has escalated beyond release-plumbing scope

## Interaction Modes

Uses `interaction-modes` aspect.

- `yolo`: continue through low-risk triage and narrow repairs automatically
- `collaborative`: pause when cause is ambiguous, repair scope expands, or policy conflicts arise

## Tips & Best Practices

### 1. Keep Context Slim with Subagents

Good parent-context summary:

```yaml
active_blocker: vsce packaging failure
root_cause: missing packaged asset
files_changed:
  - src/extensions/vscode/package.json
validation: rtk npx vsce package --pre-release
status: resolved
next_action: resume release flow
```

Avoid carrying:

- full pack output
- full CI logs
- repeated copies of unchanged blocker state
- unrelated feature-development context

### 2. Repair in the Smallest Possible Slice

Do not combine unrelated fixes in the same triage pass.

### 3. Prefer Release-Plumbing Fixes First

Exhaust metadata, packaging, script, workflow, and publisher issues before treating the blocker as a source-code problem.

### 4. Escalate Cleanly

If the issue is broader than release-plumbing scope, stop and produce a clear escalation summary instead of thrashing.

## Final Output

Always state:

- root cause
- exact fix made
- exact command rerun
- whether the blocker is resolved
- whether publish may proceed
