---
name: bootstrapping-vscode-marketplace-pat
description: "Validate VS Code Marketplace publishing readiness through Azure DevOps-backed publisher management and PAT-based vsce authentication, while keeping parent context slim via focused subagents."
metadata:
  category: workflow
  aspects:
    - interaction-modes
license: MIT
---

# Bootstrap VS Code Marketplace PAT

## Overview

Prepare and validate Visual Studio Code extension publishing readiness.

This skill covers:

- extension manifest readiness
- Azure DevOps organization access
- VS Marketplace publisher readiness
- PAT requirements for `vsce`
- CI/local secret handling for `VSCE_PAT`

## Context Management

Marketplace bootstrap spans manifest checks, publisher identity, Azure DevOps access, and PAT handling.

### Rule

Prefer subagents for one readiness concern at a time.

Use subagents for:

- extension manifest/packageability checks
- publisher identity verification
- Azure DevOps organization readiness
- PAT / CI secret path validation
- publish-path recommendation

Keep in the parent context only:

- manifest readiness summary
- publisher readiness summary
- PAT readiness summary
- publish-path recommendation
- blockers

### Output Contract for Subagents

Each subagent should return only:

- check performed
- result
- root cause of blocker
- files inspected
- validation performed
- exact next action

Do not inline full manifest files, PAT values, or long package output into parent context.

## Important Constraints

- `vsce` publishing requires a PAT
- PATs must never be stored in the repository
- CI should use a secure secret such as `VSCE_PAT`
- local bootstrap may use `vsce login <publisher>` if a human is intentionally configuring machine-local auth

## Checks

### Extension Manifest Readiness

Inspect the extension package and validate:

- `publisher` exists
- extension name/id is stable
- version exists
- README / CHANGELOG / LICENSE expectations are satisfied
- packaging succeeds

Suggested command:

```bash
pnpm dlx @vscode/vsce package --pre-release
```

### Azure DevOps Readiness

Validate or document:

- Azure DevOps organization exists and is accessible to the human operator
- PAT will be created under the correct Microsoft account
- PAT scope includes Marketplace Manage
- organization selection is compatible with publisher management

### Marketplace Publisher Readiness

Validate or document:

- publisher exists
- publisher identifier matches the extension’s `package.json`
- publisher has been verified through `vsce login` or equivalent secure CI usage

### PAT Readiness

Preferred validation path:

- CI secret exists as `VSCE_PAT`, or
- human is prepared to run local `vsce login <publisher>`

Optional local validation path:

```bash
pnpm dlx @vscode/vsce login <publisher>
```

### Publish Path Readiness

Determine whether publish is expected to be:

- direct local `vsce publish --pre-release`
- CI-based `vsce publish --pre-release`
- manual VSIX upload

## Allowed Actions

- inspect manifest/package settings
- validate packageability
- document exact PAT and publisher setup steps
- recommend CI secret wiring

## Ask First

- changing publisher id
- changing extension identity
- modifying publish strategy

## Never

- store PAT in the repository
- echo PAT to terminal logs
- assume the Azure DevOps account and Marketplace publisher already match without verification

## Outputs

Produce:

- manifest readiness
- publisher readiness
- Azure DevOps / PAT readiness
- local vs CI publish-path recommendation
- exact human steps required

## Human Bootstrap Checklist

1. Open Azure DevOps
2. Create or confirm organization access
3. Create a PAT with Marketplace Manage scope
4. Open Marketplace publisher management
5. Create or confirm the publisher
6. Ensure the extension `publisher` field matches the Marketplace publisher id
7. Either:
   - store the PAT as CI secret `VSCE_PAT`, or
   - run `vsce login <publisher>` locally for machine-local publish auth

## Usage

```bash
bootstrapping-vscode-marketplace-pat
```
