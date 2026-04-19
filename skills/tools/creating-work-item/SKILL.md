---
name: creating-work-item
description: "Create templjs backlog work items. Use when creating a new work item, backlog task, story, or epic in this repo. Enforces numeric-only file/id conventions, requires dependency review, and validates with pnpm run lint:frontmatter before completion."
---

# Create Work Item

Use this repo-local skill when adding a new work item under backlog/.

## Required repo rules

- Create files in backlog/ using numeric prefixes only: 001_style.md, 090_example.md.
- Frontmatter id must use wi-NNN format.
- Review and populate links.depends_on before finishing the draft.
- Do not invent decimal IDs, mixed formats, or missing dependency sections.
- Run pnpm run lint:frontmatter before considering the new item complete.

## Required workflow

1. Find the next unused numeric backlog file number in backlog/.
2. Create a matching file name and wi-NNN frontmatter id.
3. Ask whether the item depends on any existing WIs; if none, record an empty or omitted dependency section consistently with schema.
4. Add Goal, Background, Tasks, Deliverables, and Acceptance Criteria sections.
5. Keep initial status within the repo lifecycle: proposed, ready, in-progress, ready-for-review, closed.
6. Run pnpm run lint:frontmatter and fix any schema or dependency errors.

## Numeric-only guardrail

Never create file names like 001.5_foo.md or ids that are not numeric-backed wi-NNN values.

## Dependency prompt

Before finishing, explicitly confirm whether links.depends_on should reference any existing work items. If the work is blocked by prior items, add wikilinks immediately so validation and planning can enforce them.
