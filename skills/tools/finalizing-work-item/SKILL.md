---
name: finalizing-work-item
description: "Finalize templjs backlog work items. Use when moving a work item to closed after merge. Requires merged PR verification, test evidence, completed checklist items, and frontmatter validation before closure or archival."
---

# Finalize Work Item

Use this repo-local skill when closing a work item after implementation is merged.

## Required closure checks

Before setting status: closed, verify all of the following:

- Every remaining task checkbox is complete.
- Acceptance criteria are satisfied or explicitly updated to reflect the delivered scope.
- links.pull_requests contains the implementing PRs.
- Linked PRs are actually merged.
- Merged PRs completed with passing checks.
- links.evidence contains concrete `record:*` evidence.
- actual is populated.
- completed_date is set.
- pnpm run lint:frontmatter passes.

## Recommended verification commands

- gh pr view NUMBER --repo templjs/templ.js --json state,mergedAt,mergeCommit,statusCheckRollup
- pnpm run lint:frontmatter

## Closure rule

Do not mark a work item closed merely because code exists. Closure in this repo requires merged-PR evidence, test evidence, and completed checklist evidence.

## Archival note

If the repo process moves completed work items to backlog/archive/, perform that move only after the closure checks above are satisfied.
