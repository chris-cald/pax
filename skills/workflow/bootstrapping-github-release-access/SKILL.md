---
name: bootstrapping-github-release-access
description: "Validate GitHub repository, branch, push, and Actions workflow readiness for release automation while keeping parent context slim through focused subagent checks."
metadata:
  category: workflow
  aspects:
    - interaction-modes
license: MIT
---

# Bootstrap GitHub Release Access

## Overview

Validate the GitHub side of release readiness.

This skill verifies repository connectivity, branch strategy, and Actions workflow readiness. It does not create secrets or rewrite workflows unless explicitly authorized.

## Context Management

GitHub readiness checks often involve multiple workflows, branches, and auth paths.

### Rule

Prefer subagents for one GitHub concern at a time.

Use subagents for:

- remote/auth validation
- workflow inventory
- one workflow-file audit at a time
- branch / PR readiness checks

Keep in the parent context only:

- repo connectivity status
- GitHub auth status
- relevant workflow inventory
- OIDC readiness summary
- exact blockers

### Output Contract for Subagents

Each subagent should return only:

- check performed
- result
- root cause of failure
- files inspected
- exact next action

Do not inline entire workflow YAML files or long CLI output into parent context unless required for a decision.

## Checks

### Repository Access

Validate:

- git remote configuration
- expected origin/upstream repository
- current branch and release branch policy
- ability to fetch and push to intended branches

Suggested commands:

```bash
git remote -v
git branch --show-current
git fetch --all --tags
```

### GitHub CLI / Auth

If GitHub CLI is available, validate:

```bash
gh auth status
gh repo view
gh workflow list
```

If GitHub CLI is not available, fall back to git remote and repository file inspection.

### Workflow Discovery

Inspect `.github/workflows/` and identify:

- release workflow(s)
- tag-triggered workflow(s)
- staging/prerelease workflow(s)
- workflow file names relevant to npm trusted publishing
- workflow(s) responsible for VS Code Marketplace publishing

### OIDC Readiness for npm

If a workflow is intended to publish npm packages via trusted publishing, verify:

- `permissions.id-token: write`
- `contents: read` or stronger as needed
- the workflow file name matches the intended npm trusted-publisher configuration
- if `workflow_call` is used, parent and child workflows both have OIDC permissions when required

### Branch / PR Readiness

Validate:

- release branch policy is documented
- status checks relevant to release are discoverable
- the current branch can be used for a release drill or PR loop

## Allowed Actions

- inspect workflow files
- inspect remotes and branches
- inspect GitHub state
- recommend workflow changes

## Ask First

- editing GitHub Actions workflows
- changing branch protection assumptions
- modifying release triggers

## Never

- create or rotate secrets automatically
- force-push release branches without explicit authorization
- bypass branch protections

## Outputs

Produce:

- repo connectivity status
- GitHub auth status
- workflow inventory relevant to release
- OIDC readiness summary for npm
- release branch / PR readiness
- exact next step
