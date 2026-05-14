---
name: updating-work-item
description: "Update backlog work items across repository workflows. Use when moving work items between statuses, linking PR/evidence records, recording commits, and preparing ready-for-review transitions with repository-specific policy gates."
---

# Update Work Item

Use this skill when editing an existing work item in a structured backlog.

## Repository policy inputs

Read repository guidance first and apply these policy toggles before transitions:

- `dependencyStartPolicy`: `closed-only` or `active-or-closed`.
- `requiresChecklistCompletionBeforeReadyForReview`: true or false.
- `requiresDraftPrLinkBeforeReadyForReview`: true or false.
- `requiresProcessPrAfterReadyForReview`: true or false.
- `automation.autoCloseOnMerge`: true or false.

## Required repo lifecycle

proposed -> ready -> in-progress -> ready-for-review -> closed

## Required checks before status changes

### Before moving to in-progress

- Read links.depends_on from the work item.
- Apply repository dependency policy:
  - `closed-only`: every dependency must be `closed`.
  - `active-or-closed`: every dependency must be `in-progress`, `ready-for-review`, or `closed`.
- Do not advance the item when any dependency violates the configured policy.
- Record execution start with `doc-vader work-item transition` and create/link a record if the start itself is meaningful evidence.

### Before moving to ready-for-review

- Ensure implementation work is complete for the current scope.
- If checklist gating is enabled, mark completed `## Tasks` items as implemented.
- If checklist gating is enabled, verify and mark `## Acceptance Criteria` only after evidence confirms each criterion.
- Record commits relevant to the work item.
- If PR-link gating is enabled, ensure `links.pull_requests` includes the draft PR for the active branch.
- Record validation evidence as `record:*` documents and link them under `links.evidence`.
- If process-pr routing is enabled, run `/process-pr` after linking the draft PR and validating readiness.
- Run pnpm run lint:frontmatter.

## Required metadata updates

- Keep actual updated as work progresses.
- Add commit hashes under commits.
- Add or link evidence with `pnpm run backlog:doc-vader -- record create ...` and `pnpm run backlog:doc-vader -- work-item link evidence ...`.
- Preserve status_reason only when the status requires it.

## Dependency validation guidance

If moving to in-progress, manually inspect dependent work item statuses first; do not rely on memory. Repository rules may be stricter than generic flows.
