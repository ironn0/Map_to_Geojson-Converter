# GitHub Projects PM Workflow

This document defines the operational project management workflow for this repository using **GitHub Projects + Issues + Pull Requests + Milestones**.

## 1) Source of truth

- **Planning and execution board:** GitHub Project (single board for v1 roadmap execution).
- **Work items:** GitHub Issues.
- **Delivery unit:** Pull Request linked to an Issue.
- **Release grouping:** Milestones M1-M4.

## 2) Board columns

Recommended board columns:

1. **Backlog** - captured work, not yet prioritized.
2. **Ready** - refined, prioritized, and unblocked.
3. **In Progress** - actively implemented.
4. **In Review** - PR opened, waiting for review/merge.
5. **Done** - merged and verified against acceptance criteria.

Entry/exit rules:

- Move to **Ready** only when issue has `type:*`, `area:*`, `prio:*`, and a milestone.
- Move to **In Progress** only when assignee starts implementation.
- Move to **In Review** when a PR references the issue (`Closes #...`).
- Move to **Done** only after merge and post-merge verification.

## 3) Label taxonomy

Use exactly one label from each mandatory group:

- `type:*` (mandatory)
  - `type:bug`
  - `type:feature`
  - `type:tech-debt`
- `area:*` (mandatory)
  - `area:backend`
  - `area:frontend`
  - `area:docs`
- `prio:*` (mandatory)
  - `prio:P0`
  - `prio:P1`
  - `prio:P2`

Additional operational label:

- `ready` - issue is refined and can be pulled into active execution.

## 4) Milestone mapping (roadmap alignment)

Milestones are mapped 1:1 with `docs/ROADMAP_V1.md`:

- **M1 Core Reliability**
- **M2 Quality Baseline Expansion**
- **M3 Architecture Cleanup**
- **M4 v1 Product Readiness**

Rule: every issue must be assigned to one roadmap milestone before entering **Ready**.

## 5) Governance cadence

Minimum cadence:

- **Weekly triage (30 min):**
  - Review new issues.
  - Apply labels + milestone.
  - Promote eligible items to `ready`.
- **Weekly planning (30 min):**
  - Pull highest-priority `ready` items into **In Progress**.
  - Confirm owner and target PR window.
- **PR review cadence (continuous):**
  - Review open PRs daily when possible.
  - Keep **In Review** queue small and moving.
- **Release checkpoint (end of milestone):**
  - Confirm milestone acceptance criteria and unresolved P1/P0 items.

## 6) Release flow

1. Scope work by milestone (M1-M4).
2. Ensure each issue has acceptance criteria.
3. Merge PRs linked to milestone issues.
4. Run quality gate (`python scripts/verify.py`) before cut.
5. Update `CHANGELOG.md`.
6. Create release tag/version when milestone exit criteria are met.

## 7) Bootstrap labels/milestones with gh

Preferred (idempotent):

```bash
python scripts/bootstrap_github_pm.py
```

Optional explicit repo:

```bash
python scripts/bootstrap_github_pm.py --repo owner/name
```

## 8) Manual fallback commands (if bootstrap/auth fails)

If `gh` auth is missing:

```bash
gh auth login
```

Create labels:

```bash
gh label create "type:bug" --color d73a4a --description "Defect or regression"
gh label create "type:feature" --color 0e8a16 --description "New capability or enhancement"
gh label create "type:tech-debt" --color 6f42c1 --description "Refactor, cleanup, or maintenance work"
gh label create "area:backend" --color 1d76db --description "Backend/API related work"
gh label create "area:frontend" --color a2eeef --description "Frontend/UI related work"
gh label create "area:docs" --color fef2c0 --description "Documentation work"
gh label create "prio:P0" --color b60205 --description "Highest urgency"
gh label create "prio:P1" --color d93f0b --description "High priority"
gh label create "prio:P2" --color fbca04 --description "Normal priority"
gh label create "ready" --color 0e8a16 --description "Ready to pull into active execution"
```

Create milestones:

```bash
gh api repos/{owner}/{repo}/milestones --method POST -f title="M1 Core Reliability"
gh api repos/{owner}/{repo}/milestones --method POST -f title="M2 Quality Baseline Expansion"
gh api repos/{owner}/{repo}/milestones --method POST -f title="M3 Architecture Cleanup"
gh api repos/{owner}/{repo}/milestones --method POST -f title="M4 v1 Product Readiness"
```

If labels already exist, either skip those commands or use:

```bash
gh label edit "type:bug" --color d73a4a --description "Defect or regression"
```

## 9) Project board operating notes

- Keep one active PR per issue whenever possible.
- Prefer small PRs (single issue scope) for faster review.
- Close stale issues only after triage confirmation.
- Documentation changes follow the same flow (issue -> milestone -> PR).
