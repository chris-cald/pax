---
name: guiding-first-publish
description: "Guide a repository from zero release setup to first publish-ready state using a compact, reusable init flow. Handles release surface discovery, trust-boundary setup (npm OIDC, VS Code Marketplace PAT), CI policy gate discovery, and repo-local plumbing repair. Once the repository is validated as publish-ready, delegates all publish coordination to publishing-prerelease. Use when release infrastructure may be incomplete, platform trust boundaries are not yet established, or a first publish attempt has failed during setup. Supports: (1) release-surface discovery, (2) pre-PR gate discovery, (3) bootstrap validation, (4) guided trust-boundary setup, (5) repo-local plumbing repair, (6) handoff to publishing-prerelease"
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
          - id: delegate_publish
            label: "Delegate to publishing-prerelease"
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

Guide a repository from zero release setup to first publish-ready state, then hand off to `publishing-prerelease`.

This skill is the **initialization coordinator only**. It:

- discovers the repository's release surface
- discovers CI policy gates and repository ruleset requirements before any PR is opened
- validates external platform readiness
- distinguishes repo-local automation from human-gated trust setup
- coordinates repair and validation loops
- uses existing release skills and runbooks where available
- minimizes parent-context bloat throughout the flow

**Scope boundary:** This skill's responsibility ends when the repository is proven publish-ready. All publish coordination from that point—CI triggering, artifact staging, prerelease execution, registry/marketplace publication, and post-publish verification—belongs to `/publishing-prerelease`, invoked as a subagent.

## First-Run Principle

A first publish has two kinds of work:

### Repo-local work

This can often be automated:

- package metadata and manifest validation
- release workflows
- packaging configuration
- scripts
- changelog / README / changesets
- dry-run validation
- CI and PR readiness

### Trust-boundary work

This usually cannot be fully automated and must be guided:

- npm trusted publisher mapping (npmjs.com settings)
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
- active blockers (classified by type)
- files changed
- validation summary
- next_action (decision + exact next step)

### Parent / Subagent Split

#### Parent agent owns

- phase coordination
- go / no-go / publish-ready-only decisions
- trust-boundary gating
- selection of downstream skills
- final report and handoff to `publishing-prerelease`

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

- a first-publish initialization coordinator
- a compact-state reducer for verbose bootstrap/release loops
- a reusable zero-to-publish-ready decision engine that cleanly terminates with a `publishing-prerelease` handoff

## When to Use

Use this skill when:

- the repository has never published before
- the release path is partially configured or unknown
- trusted publishing / publisher setup may be incomplete
- the goal is to get from zero to first publish-ready state with guided flow instead of ad hoc setup
- a first publish attempt has failed during setup (manifest validation, naming misalignment, CI policy gates, or trust-boundary misconfiguration)

## When NOT to Use

Skip this skill when:

- external platform readiness is already known-good
- normal release automation is already in place and repeatable
- the task is only to perform a standard prerelease on an already bootstrapped repo — use `/publishing-prerelease` directly
- the task is general feature development rather than release setup

## Blocker Taxonomy

All blockers encountered during this skill must be classified before reporting them. The classification determines who resolves the blocker and how.

| Type                 | Example                                           | Who resolves | How                                      |
| -------------------- | ------------------------------------------------- | ------------ | ---------------------------------------- |
| **Repo-local**       | Missing `activationEvents` in extension manifest  | Agent        | Edit file, commit                        |
| **CI policy gate**   | Missing `.changeset/*.md` file                    | Agent        | Create file, commit                      |
| **CI policy gate**   | Missing `release_note` YAML block in PR body      | Agent        | Edit PR body                             |
| **Trust-boundary**   | npm trusted publisher not configured on npmjs.com | Human        | External platform settings               |
| **Trust-boundary**   | Marketplace publisher or PAT not established      | Human        | Azure DevOps / VS Code Marketplace setup |
| **Ruleset/approval** | PR requires approving review before merge         | Human        | Maintainer approves PR                   |

CI policy gates are agent-resolvable but sequential—fix and revalidate one at a time, not all at once. Do not bundle all policy gate fixes into a single commit if they depend on CI running between them.

## Core Rules

- Prefer validation over mutation
- Prefer repository-native release flow over ad hoc commands
- Never store secrets in the repository
- Never print secret values to logs
- Never manually edit version fields when repo policy requires changesets
- Distinguish clearly between repo-local blockers, CI policy gate blockers, and trust-boundary blockers
- Stop on ambiguity rather than inventing release process
- Do not coordinate publish execution — hand off to `publishing-prerelease` once publish-ready

## Workflow

### Execution Strategy

Run the first-publish flow as a coordinator.

- Use the parent agent for phase transitions and hard decisions.
- Use subagents for focused inspection, repair, and verification.
- After each subagent pass, merge back only the compact result needed for the next decision.
- Prefer one subagent per independent blocker, and discard subagent-local detail once the compact summary has been merged into parent state.

---

### Phase 1: Discover Release Surface

Determine:

- whether the repo publishes npm packages
- whether the repo publishes a VS Code extension
- whether a repo-local release runbook exists
- whether publish should be CI-based, direct, or hybrid
- whether release policy appears to be changeset-driven
- whether the repository is near release-ready or still missing basic plumbing

Signals to inspect:

- package manifests (name, version, publisher, `publishConfig`)
- `.github/workflows/`
- release docs such as `docs/release-process.md` or `docs/release-drill.md`
- extension manifest / publisher fields (`name`, `publisher`, `activationEvents`, `main`)
- changeset config if present (`.changeset/config.json`)

Preferred delegation:

- one subagent for package inventory
- one subagent for workflow inventory
- one subagent for extension inventory
- one subagent for release-doc discovery

**For VS Code extensions specifically, inspect:**

- `name` field — should match the intended marketplace identity (not prefixed redundantly, e.g., prefer `templjs` over `vscode-templjs`)
- `publisher` field — must match the registered Marketplace publisher exactly
- `activationEvents` — must be present when `main` is present (vsce enforces this at manifest validation, before any network call; a missing field causes failures that may appear as auth errors in CI logs)
- artifact naming in workflows — must match the `name` field used for VSIX output

---

### Phase 2: Pre-PR Gate Discovery

**Run this phase before opening any PR or pushing to a protected branch.**

Discover all automated and policy-enforced gates that will block PR merge, so they can be satisfied before the first publish cycle begins rather than discovered one-by-one.

#### Repository ruleset

```bash
gh api repos/OWNER/REPO/rules/branches/TARGET_BRANCH \
  | jq '[.[] | {type, parameters}]'
```

Inspect for:

- `required_approving_review_count` — number of human approvals required
- `require_last_push_approval` — whether the most recent push must be approved by a non-author
- `required_status_checks` — list of CI check names that must pass before merge
- linear history requirements
- allowed merge methods

This determines whether auto-merge can be used and how many human approval cycles to expect.

#### CI policy jobs

Inspect `.github/workflows/` for job names that enforce PR-level content requirements, such as:

- "Require Changeset" — typically checks for a `.changeset/*.md` file in the PR
- "Require Release Metadata" — typically checks for a `release_note` YAML block in the PR body

If these jobs exist, document:

- what file or PR body content each check requires
- whether the requirement is conditional on the PR touching released artifacts

Satisfy these requirements before or during PR creation, not after CI runs.

#### Required checks list

```bash
gh api repos/OWNER/REPO/branches/TARGET_BRANCH/protection \
  | jq '.required_status_checks.contexts'
```

Use this to confirm which check names appear in both the CI workflow and the ruleset. Mismatches (job name changed but ruleset not updated) are a common source of permanently-failing checks.

---

### Phase 3: Validate Bootstrap Readiness

Use `/bootstrapping-release` as the outer coordinator.

For npm packages, route npm trusted publishing validation explicitly through `/bootstrapping-npm-trusted-publishing`. That skill handles:

- package inventory and `publishConfig` inspection
- OIDC workflow readiness (`id-token: write`, provider path, publish placement)
- trusted-publisher mapping checklist per package
- private dependency auth review

**npm E409 environment-binding conflict:** A common first-publish failure. Occurs when a workflow specifies `--environment <name>` in the `npm publish` command AND a trusted-publisher entry is configured with that environment name on npmjs.com. If two jobs in the same workflow (e.g., `prerelease` and `release`) each try to bind a trusted publisher with different environment names to the same package, npm rejects one with E409 because npm allows only one trusted-publisher configuration per package.

Validate:

1. Count how many workflow jobs run `npm publish` for each package
2. For each job, check whether `--environment` is specified
3. Cross-reference against the npmjs.com trusted-publisher mappings
4. If a package has two environment-scoped entries, consolidate to one or remove the environment qualifier

Interpret the result as one of:

- `proceed_full_drill`
- `proceed_publish_ready_only`
- `stop_blocked`

Use the Phase 0 semantics from the repo-local release runbook when that runbook exists.

If bootstrap returns blockers, classify them using the Blocker Taxonomy (see above).

---

### Phase 4: Resolve Bootstrap Blockers

#### Repo-local bootstrap blockers

These may be addressed directly when safe, for example:

- missing workflow permissions
- missing packaging metadata
- missing or incorrect `activationEvents` in VS Code extension manifest
- missing `publisher` field or naming misalignment in extension manifest
- workflow artifact paths that don't match the extension `name` field
- workflow filename mismatch
- release-doc / script mismatch

Prefer the smallest safe repair and rerun only the narrowest validation.

**For VS Code extension manifest repairs:** After editing, always run a local dry-run package to confirm vsce is satisfied before committing:

```bash
npx @vscode/vsce@3.7.1 package --no-dependencies
```

This catches manifest validation errors (e.g., missing `activationEvents`) synchronously, before any CI or network call. In CI, vsce manifest errors often appear at the same step as authentication, causing misleading auth-looking failures.

#### CI policy gate blockers

These are agent-resolvable but must be resolved sequentially:

- **Missing changeset file:** Create `.changeset/<name>.md` with correct package name(s) and a user-facing changelog entry
- **Missing release metadata in PR body:** Add the `release_note` YAML block in the required format to the PR body

Create and commit each fix individually. Do not bundle CI policy gate fixes with unrelated repo-local repairs into the same commit unless they are logically inseparable.

#### Trust-boundary blockers

These must be guided, not forced.

Examples:

- npm trusted publisher not configured in npm UI
- Azure DevOps organization not established
- Marketplace publisher missing
- `VSCE_PAT` not yet created or stored as a CI secret
- external CI secret not provisioned

For trust-boundary blockers:

- produce one exact human action at a time
- wait for completion signal
- rerun bootstrap validation after each completed step

Do not bundle multiple human setup steps into one large wall of instructions unless explicitly requested.

#### Ruleset/approval blockers

These cannot be resolved by the agent. Report them explicitly:

- number of approvals required
- whether last-push approval is required (means: if you push a fix commit, the new commit also needs approval before merge)
- whether auto-merge can be enabled in advance

After reporting, proceed to enable auto-merge if the branch policy allows it, so merge executes automatically once the human approval is given.

---

### Phase 5: Validate First Publish Path

Before declaring publish-ready and handing off, confirm:

- the intended publish path is repository-native
- package/versioning state is valid
- packaging/dry-run checks succeed locally and in CI
- the selected publish target is actually in scope
- trust-boundary blockers are cleared or explicitly noted as out-of-scope
- CI policy gate blockers are resolved
- ruleset approval requirements are understood and communicated

Packaging dry-run commands to run before handoff:

**npm packages:**

```bash
pnpm pack --dry-run  # or npm pack --dry-run
```

**VS Code extension:**

```bash
npx @vscode/vsce@3.7.1 package --no-dependencies
```

If validation fails for packaging or release plumbing, delegate to `/triaging-release`.

If validation fails because PR/CI/review state is tangled, delegate to `/process-pr`.

Once all checks pass: **this skill is complete**. Proceed to Phase 6.

---

### Phase 6: Hand Off to `publishing-prerelease`

Invoke `/publishing-prerelease` as a subagent.

Pass as context:

- discovered publish targets (npm packages, VS Code extension)
- platform readiness summary
- any known remaining human-gated actions (approvals, external config)
- changeset / versioning state

Do not continue to coordinate CI state, artifact paths, registry publication, or post-publish verification from this skill. All of that is `/publishing-prerelease`'s responsibility.

If this first run is constrained by Phase 3/4 outcomes and a full publish is not yet possible:

- do not force publish
- produce a publish-ready-only result with the exact remaining human or CI actions
- report the expected next trigger (e.g., "merge PR #N → staging push triggers release workflow")

---

### Phase 7: Verify and Baseline

After success or publish-ready completion, produce a reusable baseline:

- discovered release targets
- working publish path
- required external platform mappings
- remaining manual trust-boundary steps, if any
- recommended follow-up hardening actions

This phase turns a first-run experience into a repeatable future release path.

---

## Phase Decision Semantics

At the end of each major phase, choose exactly one:

### `continue`

Use when the current path is valid and the next phase may proceed.

### `needs_human_step`

Use when the next blocker is a trust-boundary or ruleset/approval action that must be completed outside the repo.

### `publish_ready_only`

Use when the repo can be driven to a publish-ready state but actual publish cannot be completed in this run.

### `stop_blocked`

Use when progression is not safe or the release target is too ambiguous.

---

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
pre_pr_gates:
  ruleset_approvals_required: <number>
  require_last_push_approval: true | false
  ci_policy_gates:
    - name: <check name>
      requires: <what file or PR content it checks for>
      status: satisfied | outstanding
blockers:
  repo_local:
    - <item>
  ci_policy_gate:
    - <item>
  trust_boundary:
    - <item>
  ruleset_approval:
    - <item>
files_changed:
  - <path>
validation:
  - <compact validation result>
next_action:
  decision: continue | needs_human_step | publish_ready_only | stop_blocked
  step: <exact next step>
```

---

## Interaction Modes

Uses `interaction-modes` aspect.

- `yolo`: continue through low-risk validation and repo-local repair automatically; pause for trust-boundary setup, ruleset approvals, and ambiguous release targets
- `collaborative`: pause for all trust-boundary setup, ambiguous release targets, policy conflicts, or risky workflow edits

---

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
  trust_boundary:
    - npm trusted publisher not configured
next_action:
  decision: needs_human_step
  step: >
    Configure trusted publisher for workflow release.yml in npm package settings,
    then rerun /bootstrapping-npm-trusted-publishing
```

### 2. Prefer Repo-Local Runbooks When Available

If the repo already has a credible release drill, use it instead of inventing a parallel flow.

### 3. Separate Publishability from Publishing

A successful first-run outcome may be:

- first publish completed (via `publishing-prerelease` subagent)
- or repo proven publish-ready with exact remaining external actions

Both are valid terminal states for this skill.

### 4. CI Passing ≠ Deployable

All CI checks passing is necessary but not sufficient. Repository rulesets can require human approval even when all automated checks are green. Always check ruleset requirements in Phase 2 and communicate approval gates clearly before opening a PR.

### 5. Produce a Reusable Baseline

The main value of the first run is not just the first publish—it is the reusable release path discovered and documented afterward.

---

## Summary

This skill provides a reusable initialization experience that:

- discovers the repository's release surface and extension/package identity
- discovers CI policy gates and ruleset approval requirements before any PR is opened
- validates external platform readiness via `/bootstrapping-release` and `/bootstrapping-npm-trusted-publishing`
- guides trust-boundary setup one step at a time
- coordinates repo-local release preparation including manifest validation
- classifies all blockers by type (repo-local, CI policy gate, trust-boundary, ruleset/approval)
- hands off cleanly to `/publishing-prerelease` once publish-ready
- leaves behind a reusable baseline for future releases
