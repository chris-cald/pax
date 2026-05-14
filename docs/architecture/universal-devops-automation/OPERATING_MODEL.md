# Operating Model and Phase Contracts

This document defines phase intent, inputs, outputs, and exit criteria.

## Decision Outcomes

Every phase must end with one of:

- continue
- needs_human_step
- publish_ready_only
- stop_blocked

## Phase 1: discover

### Intent

Build a normalized release surface model.

### Inputs

- repository path or URL
- optional user-provided target list
- optional policy profile

### Outputs

- detected targets
- required credentials and trust boundaries
- inferred release workflows and policy gates

### Exit Criteria

- release surface is complete enough to validate

## Phase 2: validate

### Intent

Measure current state against desired state.

### Inputs

- release surface model
- policy contracts
- environment and credential state metadata

### Outputs

- drift report
- blocker list grouped by type
- compliance status by target and gate

### Exit Criteria

- all blockers classified and actionable

## Phase 3: remediate

### Intent

Apply deterministic, low-risk alignment changes.

### Inputs

- actionable blocker list
- approved remediation policy

### Outputs

- change set with evidence
- post-change validation snapshot

### Exit Criteria

- no unresolved auto-remediable blockers remain

## Phase 4: authorize

### Intent

Resolve trust-boundary and escalation requirements.

### Inputs

- unresolved human-gated blockers
- approval policy

### Outputs

- approval decisions and scope grants
- denial records with rationale

### Exit Criteria

- required approvals obtained or run explicitly blocked

## Phase 5: handoff

### Intent

Delegate to publish-specific execution workflows.

### Inputs

- validated publish-ready payload
- target-specific handoff contracts

### Outputs

- handoff package and destination workflow ids
- pre-handoff verification result

### Exit Criteria

- receiving workflow accepted payload

## Phase 6: monitor

### Intent

Maintain steady-state alignment and detect drift.

### Inputs

- baseline desired state
- scheduled or event-driven checks

### Outputs

- drift events
- remediation recommendations
- optional approved auto-remediation actions

### Exit Criteria

- reporting complete for cycle and alerts delivered

## Minimal Data Contract (suggested)

```json
{
  "phase": "validate",
  "decision": "continue",
  "blockers": {
    "repo_local": [],
    "policy_gate": [],
    "trust_boundary": [],
    "external": []
  },
  "evidence": [],
  "next_action": "run_remediation"
}
```
