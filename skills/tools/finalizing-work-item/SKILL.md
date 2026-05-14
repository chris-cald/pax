---
name: finalizing-work-item
description: "Finalize backlog work items after implementation merge. Supports automation-first repos where close/archive is system-driven, plus manual closure checks for reconciliation or non-automated workflows."
---

# Finalize Work Item

Use this skill when determining whether a work item should be manually closed and archived after implementation is merged.

## Automation-first rule

If repository config indicates `automation.autoCloseOnMerge: true`, do not manually set `status: closed` or move files to archive during normal feature execution.

In automation mode:

- keep the work item accurate through `ready-for-review` with checklist and PR linkage complete;
- run `/process-pr` for the review/merge loop;
- allow automation to create/link evidence and perform close/archive transitions after merge validation.

Use manual finalization only for explicit reconciliation or repair work.

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
