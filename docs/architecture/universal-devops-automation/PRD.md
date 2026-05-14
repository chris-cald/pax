# PRD: Universal DevOps Automation

## 1. Problem Statement

Teams repeatedly rebuild first-time release automation across fragmented targets (GitHub, npm, VS Code Marketplace, and others). Existing tools are strong in isolated domains but weak at deterministic end-to-end readiness with explicit trust-boundary handling.

## 2. Product Vision

Provide a deterministic control plane that moves a repository from unknown release state to publish-ready handoff, with explicit handling of policy gates, drift, and human authorization.

## 3. Goals

- reduce time to first publish-ready state
- make phase decisions deterministic and explainable
- separate reusable core orchestration from target-specific adapters
- treat human authorization as a first-class workflow primitive

## 4. Non-Goals

- one-click full automation for every publication target
- replacing native platform ownership/governance models
- bypassing required human approvals or compliance controls

## 5. Primary Users

- platform teams managing many repositories
- open source maintainers with multi-target releases
- DevOps engineers standardizing release onboarding

## 6. Core Capabilities

### discover

- detect release surface from repository signals and user inputs
- inventory targets, workflows, policies, and required credentials

### validate

- compare current state to desired policy/state contracts
- detect drift, missing prerequisites, and compliance gaps

### remediate

- execute deterministic, low-risk corrections
- emit evidence for each change and revalidation result

### authorize

- pause on trust boundaries and privileged actions
- support upfront and realtime approval prompts
- scope approvals by capability, resource, and expiry

### handoff

- produce machine-readable publish-ready payload
- delegate to target-specific publish sub-workflows

### monitor

- perform steady-state drift checks
- report deviations and optionally auto-remediate approved classes

## 7. Functional Requirements (MVP)

- stateful phase execution with explicit transition outcomes
- JSON contracts for phase input/output
- policy evaluation for gate pass/fail decisions
- approval prompt broker for human-gated actions
- adapters for GitHub, npm, and VS Code Marketplace
- immutable run log with decisions, approvals, and evidence

## 8. Non-Functional Requirements

- deterministic reruns given same inputs and external state snapshot
- auditable outputs suitable for compliance review
- adapter failures isolated without corrupting orchestration state
- clear failure classification: repo-local, policy-gate, trust-boundary, external

## 9. Success Metrics

- median time to publish-ready handoff
- first-run success rate by target profile
- number of manual steps per onboarding run
- drift detection precision (true positives / all alerts)
- approval latency for trust-boundary steps

## 10. Risks and Mitigations

- API variability across targets: use adapter contracts and versioned schemas
- policy drift: enforce policy-as-code and scheduled revalidation
- over-automation risk: keep explicit human authorization checkpoints

## 11. MVP Exit Criteria

- complete at least 3 representative onboarding scenarios end-to-end
- demonstrate deterministic phase outputs and stable decision traces
- verify safe handling of at least one human-gated path per target
