---
name: updating-work-item
description: "Update templjs backlog work items. Use when moving a work item between statuses, linking PR/evidence records, recording commits, or advancing to in-progress or ready-for-review. Validates dependency readiness before in-progress transitions and requires pnpm run lint:frontmatter."
---

# Update Work Item

Use this repo-local skill when editing an existing work item in backlog/.

## Required repo lifecycle

proposed -> ready -> in-progress -> ready-for-review -> closed

## Required checks before status changes

### Before moving to in-progress

- Read links.depends_on from the work item.
- Confirm each dependency is already in-progress, ready-for-review, or closed.
- Do not advance the item if a dependency is still proposed or ready.
- Record execution start with `doc-vader work-item transition` and create/link a record if the start itself is meaningful evidence.

### Before moving to ready-for-review

- Ensure implementation work is complete for the current scope.
- Record commits relevant to the work item.
- Record validation evidence as `record:*` documents and link them under `links.evidence`.
- Run pnpm run lint:frontmatter.

## Required metadata updates

- Keep actual updated as work progresses.
- Add commit hashes under commits.
- Add or link evidence with `pnpm run backlog:doc-vader -- record create ...` and `pnpm run backlog:doc-vader -- work-item link evidence ...`.
- Preserve status_reason only when the status requires it.

## Dependency validation guidance

If moving to in-progress, manually inspect dependent work item statuses first; do not rely on memory. The backlog rules for this repo are stricter than generic work-item flows.
