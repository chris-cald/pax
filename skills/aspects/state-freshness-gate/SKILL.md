---
name: state-freshness-gate
description: "Generic guard protocol for preventing stale or cached data from driving decisions. Requires freshness declaration, recency validation, blocking classification, and revalidation loops before final state transitions."
metadata:
  category: aspect
license: MIT
---

# State Freshness Gate

Use this aspect whenever a workflow decision depends on remote, asynchronous, eventually consistent, or cached state.

Examples:

- PR/review state
- CI run/check status
- issue or project board state
- release/publish status
- external platform provisioning status
- any tool output that may be stale by decision time

This aspect is intentionally generic and does not encode domain-specific sources, blocking rules, or remediation routes.

## Core Contract

Before a final state transition, gather a **fresh** snapshot of decision-critical state and record:

- source(s)
- snapshot timestamp
- target entity revision (for example: current head commit, run id, release id)

Do not make final decisions from earlier snapshots when newer events may have occurred.

## Open-Closed Extension Model

To keep this aspect OCP-compliant, workflows provide a domain adapter instead of changing this file.

Adapter contract:

- `sources`: how fresh state is collected
- `classify`: rules that map state to `clear | blocking | unknown`
- `remediation`: smallest safe action for `blocking | unknown`
- `terminal_precondition`: exact checks required before final state transition

The aspect consumes adapter outputs, but does not define domain rules itself.

## Freshness Requirements

1. Query the authoritative source as close as possible to decision time.
2. Confirm snapshot corresponds to the current target revision.
3. If source timestamps or revisions moved since prior read, treat prior state as stale.
4. If freshness cannot be verified, classify as `unknown` and block final transition.

## Blocking Rules

- Blocking: state indicates required action before final transition.
- Unknown: freshness cannot be proven, source unavailable, or conflicting signals.
- Clear: no blocking conditions and freshness is verified.

Unknown is not clear. Unknown must not be treated as pass.

## Required Revalidation Loop

1. Collect fresh snapshot.
2. Classify as clear, blocking, or unknown.
3. If blocking or unknown, perform the smallest safe remediation or data-refresh step.
4. Re-collect fresh snapshot.
5. Repeat until clear or explicit stop condition.

## Hard Precondition for Final Decision

Do not report terminal states (for example: mergeable, publish-ready, release-ready, complete) unless all are true:

- freshness verified for decision-critical data
- blocking conditions are zero
- state corresponds to current target revision

## Suggested Output Fields

```yaml
freshness_gate:
  status: clear | blocking | unknown
  checked_at: <timestamp>
  target_revision: <sha|id|version>
  adapter: <caller-provided adapter id>
  sources:
    - <source>
  blocking_items:
    - <item>
```
