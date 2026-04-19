---
name: bootstrapping-npm-trusted-publishing
description: "Validate npm trusted publishing via OIDC for GitHub Actions-based releases, using focused subagents to keep parent context compact."
metadata:
  category: workflow
  aspects:
    - interaction-modes
license: MIT
---

# Bootstrap npm Trusted Publishing

## Overview

Prepare and validate npm publication through trusted publishing.

This skill assumes the preferred publish path is CI-based OIDC trusted publishing, not local `npm login` or long-lived npm write tokens.

## Context Management

npm trusted-publishing checks can expand quickly across packages, workflows, and registry settings.

### Rule

Prefer subagents for one package group, one workflow, or one registry-mapping concern at a time.

Use subagents for:

- package inventory
- runtime compatibility checks
- one workflow readiness audit at a time
- one trusted-publisher mapping at a time
- private dependency auth review

Keep in the parent context only:

- package inventory summary
- runtime compatibility status
- workflow readiness summary
- trusted-publisher mapping summary
- blockers

### Output Contract for Subagents

Each subagent should return only:

- package or workflow checked
- readiness result
- root cause of blocker
- files inspected
- validation performed
- exact next action

Do not inline entire package manifests, registry settings dumps, or full workflow YAML into parent context unless required for a decision.

## Important Constraints

- Do NOT use `npm login` as the primary bootstrap for trusted publishing
- Do NOT require `npm whoami` to pass as proof of trusted-publishing readiness
- Do NOT introduce long-lived npm write tokens when trusted publishing is available
- Trusted publishing applies to `npm publish`; it does not replace auth required for other npm operations such as private dependency installation

## Checks

### Runtime Compatibility

Validate toolchain requirements for trusted publishing:

- Node runtime version
- npm CLI version

Suggested checks:

```bash
node -v
npm -v
```

### Publish Targets

Identify publishable packages and collect:

- package name
- access level
- release workflow file
- expected publish command
- whether package provenance should be enabled

### Workflow Readiness

Inspect the release workflow intended to run `npm publish` and validate:

- workflow exists under `.github/workflows/`
- workflow filename matches the package’s trusted-publisher settings plan
- `permissions.id-token: write` is present
- publish runs on a supported cloud-hosted provider path
- package build/test steps occur before publish
- no `NPM_TOKEN` write-secret path is required for publish

### Package Readiness

Inspect package metadata for:

- publishable package configuration
- `publishConfig` if present
- provenance-related settings if explicitly overridden
- access/publication assumptions

### Trusted Publisher Mapping

For each package, record the intended mapping:

- provider: GitHub Actions
- owner/org
- repository
- workflow filename
- optional environment name

### Private Dependency Auth

If the workflow installs private dependencies, validate that it uses:

- a read-only token for install
- no write token for publish

## Allowed Actions

- inspect package metadata
- inspect workflow files
- produce trusted-publisher configuration instructions
- recommend secure read-only install auth for private dependencies

## Ask First

- editing release workflows
- editing package publish settings
- changing provenance behavior

## Never

- add long-lived npm write tokens to the repo
- claim OIDC readiness based on `npm whoami`
- convert a trusted-publishing design back to token-based publish without explicit approval

## Outputs

Produce:

- package inventory
- runtime compatibility status
- OIDC workflow readiness
- trusted-publisher configuration checklist
- private dependency auth notes
- exact npmjs.com settings a human must create or verify

## Human Bootstrap Checklist

For each package intended for trusted publishing:

1. Open npmjs.com package settings
2. Configure Trusted Publisher
3. Select GitHub Actions
4. Enter:
   - organization/user
   - repository
   - workflow filename
   - optional environment name
5. Save
6. Ensure the referenced GitHub Actions workflow requests `id-token: write`

## Usage

```bash
bootstrapping-npm-trusted-publishing
```
