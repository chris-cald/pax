---
name: github-branch-protection
description: "Query GitHub branch-protection and ruleset policy, detect automated approvers (CodeRabbit, Graphite, auto-approve workflows, etc.), then choose the correct PR feedback-resolution strategy. Use when PR feedback loops are blocked, mergeability is unclear, or branch policy constraints must drive resolution order."
---

# GitHub Branch Protection

Use this repo-local skill to determine the right resolution strategy for PR feedback and mergeability loops.

This skill is policy-first: before resolving review comments or retrying CI, query branch protection and rulesets for the PR base branch, then choose the smallest valid action sequence.

## When to use

Use when any of these are true:

- PR is blocked but root cause is unclear
- Required checks pass locally but GitHub still blocks merge
- Review comments are resolved but merge stays blocked
- You need to decide whether to push fixes, re-request review, sync base branch, or escalate

## Required inputs

- owner (for example: templjs)
- repo (for example: templ.js)
- pull number

Optional:

- base branch override (if not using PR base)

## Query workflow

Run these commands from repo root.

1. Fetch PR state and base branch.

```bash
rtk gh pr view <pull_number> --json number,title,isDraft,baseRefName,headRefName,reviewDecision,mergeStateStatus,statusCheckRollup
```

1. Capture base branch protection (classic protection API).

```bash
rtk gh api repos/<owner>/<repo>/branches/<base_branch>/protection
```

1. Capture branch rulesets that apply to the same branch.

```bash
rtk gh api repos/<owner>/<repo>/rules/branches/<base_branch>
```

1. Optional: confirm required checks currently expected by GitHub.

```bash
rtk gh pr checks <pull_number>
```

1. Detect automated approvers.

```bash
# List GitHub Apps installed on the repo (requires repo admin or token with read:org)
rtk gh api repos/<owner>/<repo>/apps --jq '[.[] | {slug, name}]'

# Scan workflow files for auto-approve patterns
rtk grep -rl "pr review.*approve\|auto.approve\|approve.*bot\|gh pr review" .github/workflows/ 2>/dev/null

# Check for known bot config files in the repo root and .github/
rtk ls -1 .coderabbit.yaml .coderabbit.yml reviewpad.yml .github/reviewpad.yml \
    .github/auto-approve.yml .github/coderabbit.yaml .github/coderabbit.yml 2>/dev/null

# Inspect recent automated review actors on the PR
rtk gh api repos/<owner>/<repo>/pulls/<pull_number>/reviews \
    --jq '[.[] | select(.user.type=="Bot") | {login: .user.login, state}]'
```

## Automated approver detection

After running step 5, classify each detected actor and factor the result into the current PR feedback-resolution strategy.

### Known automated approvers

| Slug / filename                               | Actor type                       | Relevant config          |
| --------------------------------------------- | -------------------------------- | ------------------------ |
| `coderabbit-ai`                               | Review bot (App)                 | `.coderabbit.yaml`       |
| `graphite-app`                                | Merge queue / stacking           | Graphite dashboard       |
| `kodiak`                                      | Auto-merge bot (App)             | `.kodiak.toml`           |
| `renovate`                                    | Dependency PR auto-approve       | `renovate.json`          |
| `dependabot`                                  | Dependency PR auto-approve       | `.github/dependabot.yml` |
| workflow `auto-approve*.yml`                  | GitHub Actions workflow approver | `.github/workflows/`     |
| workflow containing `gh pr review.*--approve` | GitHub Actions workflow approver | `.github/workflows/`     |

### Strategy adjustments per automated approver

1. **CodeRabbit (`coderabbit-ai`) present**
   - Expect a CodeRabbit summary comment on each push; wait for it before re-requesting human review.
   - Unresolved CodeRabbit inline threads count as required conversations if `conversation_resolution` is enabled.
   - Do not manually re-request CodeRabbit; it triggers automatically on push.
   - If CodeRabbit is the only reviewer left, confirm humans are also required; if not, a passing CodeRabbit review may be sufficient to unblock merge.

2. **Kodiak (`kodiak`) present**
   - Kodiak auto-merges when all checks pass and required approvals are met.
   - Do not manually click merge; Kodiak will handle it.
   - If Kodiak is stuck, check `.kodiak.toml` merge method matches the branch linear-history policy.

3. **Auto-approve workflow present (GitHub Actions)**
   - Determine trigger condition (label, actor, branch pattern).
   - If the workflow fired but approval did not appear, check workflow run status: `rtk gh run list --workflow <filename>`.
   - A failed auto-approve run means an approval that policy depends on is missing; fix the workflow condition or approve manually.

4. **Renovate / Dependabot auto-approve present**
   - Usually scoped to dependency-only PRs.
   - For feature PRs, assume human approval is still required unless policy explicitly allows bot-only approval.

5. **No automated approvers detected**
   - All approvals must come from human reviewers.
   - No strategy changes from the base resolution order.

## Decision mapping for PR feedback resolution

Interpret policy first, then choose strategy.

1. Required approving reviews present

Signal:

- `required_pull_request_reviews.required_approving_review_count > 0`

Strategy:

- Resolve highest-severity review findings first
- Push minimal fix set
- Re-request review from required reviewers/code owners
- Do not attempt merge until required approvals are restored

1. Dismiss stale approvals enabled

Signal:

- `required_pull_request_reviews.dismiss_stale_reviews == true`

Strategy:

- Batch related fixes into one push when possible
- After push, assume previous approvals are invalid
- Immediately re-request review and verify new approval state

1. Code owner review required

Signal:

- `required_pull_request_reviews.require_code_owner_reviews == true`

Strategy:

- Prioritize files owned by CODEOWNERS in first pass
- Request reviews from explicit code owners
- Avoid extra churn on owned files once approvals start

1. Conversation resolution required

Signal:

- `required_conversation_resolution.enabled == true` or equivalent ruleset requirement

Strategy:

- Treat unresolved review threads as merge blockers
- Resolve threads before spending cycles on non-blocking polish
- Re-check thread state after each comment cluster is addressed

1. Required status checks configured

Signal:

- `required_status_checks` present, including contexts/checks

Strategy:

- Fix failing required checks before non-required checks
- Validate only failing surfaces locally where possible
- Push, then wait for required checks to report green

1. Strict status checks (branch must be up to date)

Signal:

- `required_status_checks.strict == true`

Strategy:

- Sync head with base branch before final approval loop
- Re-run validation after sync
- Expect checks to rerun; do not treat previous green runs as final

1. Linear history required

Signal:

- `required_linear_history.enabled == true` or equivalent ruleset

Strategy:

- Keep branch history clean (rebase/squash flow)
- Avoid merge commits in fix loop
- Ensure final merge method matches policy

1. Force pushes or deletions disallowed

Signal:

- `allow_force_pushes.enabled == false`
- `allow_deletions.enabled == false`

Strategy:

- Use additive corrective commits
- Avoid rewrite-based recovery tactics

1. Admin enforcement enabled

Signal:

- `enforce_admins.enabled == true` or ruleset applies to admins

Strategy:

- Do not plan on admin bypass
- Treat all policy failures as hard blockers

## Resolution order template

Use this order unless policy indicates a different hard blocker:

1. Draft status and obvious merge-state blockers
2. Required failing checks
3. Required review findings
4. Required thread/conversation resolution
5. Base-branch sync requirements (`strict`)
6. Approval refresh requirements (stale/code-owner)
7. Final mergeability check

## Compact output contract

After running this skill, return only:

- policy summary (reviews/checks/threads/sync/admin)
- automated approvers detected (name, type, strategy impact)
- current blockers mapped to policy
- priority basis used (policy-first ordering)
- exact next action in the PR feedback loop (single highest-priority step)
- next_decision: continue-loop | escalate-process-pr | stop

Example:

```yaml
policy:
  approvals_required: 1
  code_owner_reviews: true
  dismiss_stale_reviews: true
  strict_checks: true
  conversation_resolution: true
automated_approvers:
  - name: coderabbit-ai
    type: review-bot
    strategy_impact: wait for CodeRabbit summary after next push; unresolved inline threads are blockers
blockers:
  - failing required check: test (ubuntu-latest)
  - unresolved review thread in src/extensions/vscode/src/...
priority_basis:
  - required checks before non-required feedback
  - required conversations before polish
next_action: fix failing required check first, push once, then wait for CodeRabbit pass, resolve thread, re-request code-owner review
next_decision: continue-loop
```

## Guardrails

- Query policy before proposing merge tactics
- Do not assume admin bypass is allowed
- Do not recommend manual version edits or unrelated refactors
- Keep fixes minimal and tied to active blockers
