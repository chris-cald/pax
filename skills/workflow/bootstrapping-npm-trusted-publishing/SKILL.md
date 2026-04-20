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
- workflow filename matches the package's trusted-publisher settings plan
- `permissions.id-token: write` is present on the job (not only at the workflow level if the job overrides permissions)
- publish runs on a supported cloud-hosted provider path (GitHub-hosted runner)
- package build/test steps occur before publish
- no `NPM_TOKEN` write-secret path is required for publish

#### Environment-scoped publish and E409 conflict

If `npm publish` is called with `--environment <name>`, the trusted-publisher configuration on npmjs.com must include an entry with that exact environment name, scoped to that specific workflow filename.

**E409 conflict pattern:** npm enforces a maximum of one trusted-publisher configuration per package. If two jobs in the same workflow (e.g., a `prerelease` job and a `release` job) each use a different `--environment` value, and both are registered as trusted-publisher entries for the same package, npm will reject the second registration with E409 (`409 Conflict`).

Validate for each package:

1. Count how many workflow jobs run `npm publish` for that package
2. For each job, check whether `--environment <name>` is specified
3. Record the intended npmjs.com trusted-publisher configuration for each job
4. If two jobs produce conflicting configurations (same package, different environments), flag as an E409 risk

Recommended resolution: Remove the `--environment` qualifier from `npm publish` in the workflow if environment-level scoping is not strictly required. A single trusted-publisher entry without environment binding covers all jobs in the workflow.

### Package Readiness

Inspect package metadata for:

- publishable package configuration
- `publishConfig` if present (must not specify `registry` pointing to an unintended registry)
- provenance-related settings if explicitly overridden
- access/publication assumptions

### Trusted Publisher Mapping

For each package, record the intended mapping:

- provider: GitHub Actions
- owner/org
- repository
- workflow filename (must match exactly, including path — e.g., `.github/workflows/release.yml`)
- optional environment name (omit if not using environment-scoped publish)

Verify the workflow filename in the mapping matches the actual workflow file on disk. A filename mismatch (e.g., `release.yml` vs `publish.yml`) will cause every publish attempt to fail with an auth error even if OIDC token exchange succeeds.

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
- environment-binding conflict analysis (E409 risk assessment)
- trusted-publisher configuration checklist
- private dependency auth notes
- exact npmjs.com settings a human must create or verify

## Human Bootstrap Checklist

For each package intended for trusted publishing:

1. Open npmjs.com → package → Settings → Publishing
2. Select "GitHub Actions" under Trusted Publisher
3. Enter:
   - organization/user
   - repository name
   - workflow filename (e.g., `release.yml`, not the full path)
   - environment name — **leave blank unless the workflow explicitly passes `--environment <name>` to `npm publish`**
4. Save
5. Ensure the referenced GitHub Actions workflow job requests `id-token: write`
6. Verify no other trusted-publisher entry exists for the same package that would conflict

**One entry per package.** If the workflow has multiple jobs that publish the same package (e.g., prerelease and release), use one trusted-publisher entry without an environment qualifier, or ensure exactly one job uses the environment-scoped path.

## Common Failure Modes

| Symptom                                                         | Likely Cause                                                            | Resolution                                                    |
| --------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| E409 on first publish                                           | Two trusted-publisher configs for same package                          | Remove one entry; remove `--environment` from publish command |
| Auth error despite correct OIDC setup                           | Workflow filename in trusted-publisher config doesn't match actual file | Correct the filename in npmjs.com trusted-publisher settings  |
| `npm whoami` fails in workflow                                  | Expected — `whoami` uses token auth, not OIDC                           | Not a meaningful health check for trusted publishing          |
| Publish succeeds in `prerelease` job but fails in `release` job | `release` job uses different `--environment` not registered             | Add a matching entry or remove environment qualifier          |

## Usage

```bash
bootstrapping-npm-trusted-publishing
```
