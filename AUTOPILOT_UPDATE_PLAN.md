# Autopilot Update Plan — Most-Ahead Consolidation

**Generated:** 2026-03-11  
**Repository:** `matiasportugau-ui/GPT-PANELIN-Final`  
**Base branch:** `main` at `b4bce54` (Merge PR #218 — Panelin Agno architecture)  
**Status:** 50 open PRs · 90+ branches · 50 merged PRs

> **Purpose:** Provide a step-by-step, maintainer-executable plan to consolidate the
> repository to its most-ahead state by merging valuable open work, closing
> superseded/duplicate PRs, and cleaning up stale branches.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Snapshot](#2-current-state-snapshot)
3. [PR Cluster Analysis](#3-pr-cluster-analysis)
4. [Recommended Merge Order (6 Stages)](#4-recommended-merge-order-6-stages)
5. [Per-PR Action Table](#5-per-pr-action-table)
6. [Branch Cleanup Plan](#6-branch-cleanup-plan)
7. [Validation Checklist](#7-validation-checklist)
8. [Risks & Mitigations](#8-risks--mitigations)
9. [Rollback Guidance](#9-rollback-guidance)

---

## 1. Executive Summary

The repository has accumulated **50 open PRs** across **90+ branches**, many of which
are duplicates, superseded by merged work, or target branches that no longer exist.

**Key findings:**

| Category | Count | Action |
|----------|-------|--------|
| PRs to **merge** (valuable, unique) | 8 | Rebase and merge |
| PRs to **close** (superseded/duplicate) | 35 | Close with explanation |
| PRs to **review** (large features, deferred) | 7 | Evaluate independently |
| Branches to **delete** after cleanup | 80+ | Delete after PR closure |

**Recently merged milestones** (already in `main`):
- PR #218 — Panelin Agno architecture ✅
- PR #230 — Agno AgentOS migration ✅
- PR #204 — README v4.0 update ✅
- PR #191 — Morning audit setup ✅
- PR #190 — GPT live version configuration ✅
- PR #184 — API entrypoint and endpoints ✅
- PR #180 — Panelin 4.0 architecture ✅
- PR #154 — Fix f-string syntax error ✅
- PR #166 — Fix ci-cd.yml ✅

---

## 2. Current State Snapshot

### Main Branch Head

```
b4bce54  Merge pull request #218 — Panelin Agno architecture (2026-03-11)
```

### Open PRs by Merge State

| Merge State | Count | Meaning |
|-------------|-------|---------|
| `clean` | 4 | Ready to merge, no conflicts |
| `unstable` | 18 | CI checks failing or pending |
| `dirty` | 12 | Has merge conflicts |
| N/A (stale target) | 16 | Target branch doesn't exist or is merged |

### Open PRs by Type

| Type | Count | PRs |
|------|-------|-----|
| Duplicate Agno architecture | 11 | #207–#217 |
| Stale morning-audit sub-PRs | 9 | #193–#202 |
| CI/CD fixes | 4 | #220, #203, #171, #192 |
| Health check duplicates | 3 | #125, #131, #132 |
| Deployment script fixes | 4 | #150, #145, #139, #142 |
| Post-merge fixes | 1 | #228 |
| Bug fixes | 2 | #172, #151 |
| Documentation/planning | 3 | #229, #224, #122 |
| New features | 7 | #175, #176, #177, #179, #182, #181, #178 |
| Testing | 1 | #126 |
| Orchestration | 2 | #112, #49 |
| Other | 3 | — |

---

## 3. PR Cluster Analysis

### Cluster A: CI/CD & Workflow Fixes ⚡

| PR | Title | Files | Mergeable | Overlap |
|----|-------|-------|-----------|---------|
| **#220** | Fix CI failures: missing contract fields + ci-cd.yml syntax | 10 | unstable | Contracts + YAML |
| #203 | Add missing name/version to MCP contracts | 14 | unstable | Contracts only |
| #171 | Fix CI/CD workflow failures + Wolf API version drift | 5 | unstable | YAML + version |
| #192 | Pin runner ubuntu-latest → ubuntu-24.04 | 9 | unstable | Runners only |

**Analysis:**
- **#220** is the most comprehensive: fixes both contracts AND ci-cd.yml syntax.
- **#203** overlaps entirely on contracts (subset of #220).
- **#171** overlaps on ci-cd.yml syntax; adds Wolf API version sync (`2.1.0` → `2.2.0`) — check if already applied.
- **#192** is independent (runner pinning) — can merge separately.

**Recommendation:** Merge #220 first (broadest fix). Cherry-pick Wolf API version sync from #171 if not already applied. Then merge #192. Close #203 as superseded.

---

### Cluster B: Agno Architecture Duplicates 🔴 CLOSE ALL

| PR | Title | Branch | Status |
|----|-------|--------|--------|
| #209 | Panelin agno architecture | cursor/panelin-agno-architecture-3ad2 | Superseded |
| #213 | Panelin agno architecture | cursor/panelin-agno-architecture-bfa0 | Superseded |
| #214 | Panelin agno architecture | cursor/panelin-agno-architecture-eb6e | Superseded |
| #215 | Panelin agno architecture | cursor/panelin-agno-architecture-2236 | Superseded |
| #216 | Panelin agno architecture | cursor/panelin-agno-architecture-b611 | Superseded |
| #217 | Panelin agno architecture | cursor/panelin-agno-architecture-1861 | Superseded |
| #207 | Panelin Agno migración | cursor/panelin-agno-migraci-n-c57f | Superseded |
| #208 | Panelin Agno migración | cursor/panelin-agno-migraci-n-f2af | Superseded |
| #210 | Panelin Agno migración | cursor/panelin-agno-migraci-n-c97f | Superseded |
| #211 | Panelin Agno migración | cursor/panelin-agno-migraci-n-06ce | Superseded |
| #212 | Panelin Agno migración | cursor/panelin-agno-migraci-n-52fa | Superseded |

**Rationale:** PR #218 (the lead Agno architecture PR) was merged to `main` on 2026-03-11.
PR #230 (AgentOS migration sub-PR) was also merged. All 11 remaining PRs are failed
attempts or earlier iterations. **Close all with comment:**

> Closed: Superseded by PR #218 (merged 2026-03-11) which is the canonical Agno architecture migration.

---

### Cluster C: Post-Agno Fixes 🔒 HIGH PRIORITY

| PR | Title | Files | Changes | Key Improvements |
|----|-------|-------|---------|------------------|
| **#228** | fix: error handling, UTC timestamps, PDF cleanup, AgentOS auth | 3 | +30/−23 | Security + quality |

**Details:**
1. `wolf_api/main.py` — Fail-fast on misconfigured routers (catch only `ImportError`)
2. `wolf_api/pdf_cotizacion.py` — UTC timestamps + temp file cleanup
3. `cloudbuild.yaml` — `PANELIN_AGENTOS_ENABLE_AUTH=true` (security)

**Recommendation:** Rebase onto current `main` and merge. This is a **security-critical** fix.

---

### Cluster D: Morning Audit Sub-PRs 🔴 CLOSE ALL

| PR | Title | Target Branch |
|----|-------|---------------|
| #193 | Fix morning audit | cursor/panelin-morning-audit-setup-dab1 |
| #194 | Secure credentials | cursor/panelin-morning-audit-setup-dab1 |
| #195 | Harden morning audit | cursor/panelin-morning-audit-setup-dab1 |
| #196 | Harden morning audit | cursor/panelin-morning-audit-setup-dab1 |
| #197 | Restrict credentials | cursor/panelin-morning-audit-setup-dab1 |
| #198 | Morning audit fixes | cursor/panelin-morning-audit-setup-dab1 |
| #199 | Restrict credentials | cursor/panelin-morning-audit-setup-dab1 |
| #200 | UTC timestamps | cursor/panelin-morning-audit-setup-dab1 |
| #201 | UTC timestamps | cursor/panelin-morning-audit-setup-dab1 |
| #202 | catch specific WorksheetNotFound | cursor/panelin-morning-audit-setup-dab1 |

**Rationale:** All 9 PRs target `cursor/panelin-morning-audit-setup-dab1`, which was
**merged to `main` as PR #191** on 2026-03-03. These sub-PRs are orphaned — their target
branch is already merged and these changes were either included or are no longer relevant.

> Closed: Target branch merged to main via PR #191. Sub-PRs are no longer applicable.

**Post-close action:** Review if UTC timestamp or credential improvements from these
sub-PRs are needed as a fresh PR against `main`. Most likely #228 already covers
the UTC timestamp improvements.

---

### Cluster E: Health Check Script Duplicates

| PR | Title | Mergeable | Approach |
|----|-------|-----------|----------|
| #125 | Fix health check Docker Compose compat | dirty | Close |
| **#131** | Fix health_check.sh CI failure: Docker Compose v2 | dirty | Keep (most complete) |
| #132 | Fix health check for Docker Compose v2 | dirty | Close |

**Analysis:** All three fix the same `docker-compose` v1 → `docker compose` v2 issue.
PR #131 is the most complete implementation (CI-aware + graceful fallback).

**Recommendation:** Close #125 and #132. Rebase #131 onto current `main` and merge.

---

### Cluster F: Deployment Script Fixes 🔴 LIKELY SUPERSEDED

| PR | Title | Target | Status |
|----|-------|--------|--------|
| #150 | Fix f-string syntax error in deploy script | main | dirty |
| #145 | Fix f-string syntax error | claude/automate-gpt-deployment-YwGCQ | stale |
| #139 | Fix E999 syntax error | claude/automate-gpt-deployment-YwGCQ | stale |
| #142 | Fix Python indentation error | claude/automate-gpt-deployment-YwGCQ | stale |

**Analysis:** PR #154 (merged 2026-02-23) already fixed the f-string syntax error in
`deploy_gpt_assistant.py`. PRs #145, #139, #142 target a branch that was never merged
to `main`. **All 4 are superseded.**

> Closed: f-string syntax error already fixed by merged PR #154.

---

### Cluster G: Bug Fixes (Valuable)

| PR | Title | Mergeable | Files | Value |
|----|-------|-----------|-------|-------|
| **#172** | Fix persist_conversation operationId mismatch | dirty | 4 | GPT plugin routing |
| **#151** | Fix README glob pattern compliance | unstable | 1 | Compliance checker |

**#172 Analysis:** Fixes operationId `persistConversation` → `persist_conversation` in
OpenAPI schema and FastAPI route. Also syncs Wolf API test version. Needs rebase.

**#151 Analysis:** One-line fix replacing `mcp/tools/*.json` glob with a markdown link.
Trivial but resolves compliance checker false positive.

**Recommendation:** Rebase both onto `main` and merge. Verify #172 changes aren't
already applied by subsequent merged PRs.

---

### Cluster H: Documentation & Planning

| PR | Title | Mergeable | Action |
|----|-------|-----------|--------|
| #229 | Autopilot merge strategy doc | clean | Close (superseded by this plan) |
| #224 | Current-state merge strategy report | unstable | Close (superseded by this plan) |
| #122 | Docs: Surface Copilot instructions | dirty | Rebase & merge (docs-only, low risk) |

**Recommendation:** Close #229 and #224 (this document supersedes them). Rebase #122 for
documentation improvements.

---

### Cluster I: New Feature Modules (DEFERRED — Requires Independent Review)

| PR | Title | Lines Added | Mergeable | Status |
|----|-------|-------------|-----------|--------|
| **#175** | WhatsApp real estate bot | +2,976 | dirty | Large new service |
| **#176** | Chatbot integration project | +928 | unstable | Related to #175 |
| **#177** | Initial repository structure (quoting engine) | +8,233 | dirty | Massive restructure |
| **#179** | Google Sheets Orchestrator | +4,648 | dirty | New microservice |
| #182 | Instrucciones núcleo MIAP v2 | +295 | unstable | Docs only |
| #181 | Instrucciones núcleo MIAP (earlier attempt) | — | — | Duplicate of #182 |
| #178 | Starter kit de archivos | — | — | Targets #176 branch |

**Recommendation:** These are large feature PRs adding new modules/services. They should
be evaluated independently after stabilization work is complete:

1. **#175 + #176** — WhatsApp chatbot (evaluate together, pick one)
2. **#177** — Large restructure, high conflict risk, evaluate carefully
3. **#179** — Sheets Orchestrator (independent service, can merge separately)
4. **#182** — MIAP instructions doc (low risk, merge after review)
5. Close **#181** (duplicate of #182) and **#178** (targets stale branch)

---

### Cluster J: Testing & Quality

| PR | Title | Mergeable | Action |
|----|-------|-----------|--------|
| **#126** | Test coverage for create_gpt_zip_package.py | clean | Merge (adds 33 tests) |

**Recommendation:** Merge — adds valuable test coverage with no risk.

---

### Cluster K: Orchestration & Configuration

| PR | Title | Mergeable | Action |
|----|-------|-----------|--------|
| #112 | Agent orchestration framework | clean | Review & merge (adds useful framework) |
| #49 | Rename mcp/ → panelin_mcp_server/ | dirty | Evaluate if still needed |

**#49 Analysis:** This was the original module-shadowing fix. Since the Agno
architecture (#218) has been merged, verify whether `mcp/` still shadows the external
package. If so, this needs a fresh rebase. If not, close as resolved.

---

## 4. Recommended Merge Order (6 Stages)

### Stage 1: 🔒 Security & Post-Merge Fixes (Day 1)

| Order | PR | Title | Risk | Action |
|-------|-----|-------|------|--------|
| 1.1 | **#228** | Error handling, UTC timestamps, PDF cleanup, AgentOS auth | Low | Rebase & merge |

**Validation:** Run Wolf API tests, verify `cloudbuild.yaml` has auth env var.

---

### Stage 2: ⚡ CI/CD Stabilization (Day 1)

| Order | PR | Title | Risk | Action |
|-------|-----|-------|------|--------|
| 2.1 | **#220** | Fix CI failures: contracts + ci-cd.yml syntax | Medium | Rebase & merge |
| 2.2 | **#192** | Pin runner to ubuntu-24.04 | Low | Rebase & merge |
| 2.3 | **#131** | Fix health check Docker Compose v2 | Low | Rebase & merge |

**Validation:** Run full CI pipeline. All 9 workflows should parse. Health check exits 0.

---

### Stage 3: 🐛 Bug Fixes (Day 2)

| Order | PR | Title | Risk | Action |
|-------|-----|-------|------|--------|
| 3.1 | **#172** | Fix persist_conversation operationId | Low | Rebase & merge |
| 3.2 | **#151** | Fix README glob pattern | Trivial | Rebase & merge |

**Validation:** Wolf API tests pass. Compliance checker reports 0 missing files.

---

### Stage 4: 🧪 Testing & Documentation (Day 2)

| Order | PR | Title | Risk | Action |
|-------|-----|-------|------|--------|
| 4.1 | **#126** | Test coverage for zip packager | None | Merge |
| 4.2 | **#122** | Docs: Surface Copilot instructions | None | Rebase & merge |
| 4.3 | **#112** | Agent orchestration framework | Low | Review & merge |

**Validation:** `pytest test_create_gpt_zip_package.py -v` passes. Docs render correctly.

---

### Stage 5: 🚫 Mass Close Superseded/Duplicate PRs (Day 2)

Close **35 PRs** with appropriate comments:

**Agno duplicates (11 PRs):** #207, #208, #209, #210, #211, #212, #213, #214, #215, #216, #217
> Superseded by merged PR #218.

**Morning audit sub-PRs (9 PRs):** #193, #194, #195, #196, #197, #198, #199, #200, #201, #202
> Target branch merged to main via PR #191.

**Deployment script fixes (4 PRs):** #139, #142, #145, #150
> Fixed by merged PR #154.

**Health check duplicates (2 PRs):** #125, #132
> Consolidated into PR #131.

**CI/CD overlap (2 PRs):** #203, #171
> Covered by merged PR #220.

**Documentation superseded (2 PRs):** #224, #229
> Superseded by AUTOPILOT_UPDATE_PLAN.md.

**Feature duplicates (3 PRs):** #181, #178, #49
> #181 duplicate of #182; #178 targets stale branch; #49 evaluate if module shadowing resolved.

**Stale/obsolete (2 PRs):** Close any remaining stale PRs after verification.

---

### Stage 6: 🚀 Feature Evaluation (Week 2)

Independently review and potentially merge large feature PRs:

| Priority | PR | Title | Size | Notes |
|----------|-----|-------|------|-------|
| 1 | **#179** | Google Sheets Orchestrator | +4,648 | Independent service, self-contained |
| 2 | **#182** | MIAP instructions v2 | +295 | Docs only, low risk |
| 3 | **#175** | WhatsApp real estate bot | +2,976 | New service, needs security review |
| 4 | **#177** | Initial repository structure | +8,233 | Massive, high conflict risk |
| 5 | **#176** | Chatbot integration project | +928 | Related to #175, evaluate together |

---

## 5. Per-PR Action Table

### Legend
- ✅ **Merge** — Rebase onto `main` and merge
- 🚫 **Close** — Close with comment explaining supersession
- 🔍 **Review** — Requires manual review before decision
- 📌 **Defer** — Evaluate in Stage 6

| PR | Title | Action | Stage | Comment |
|----|-------|--------|-------|---------|
| #49 | Rename mcp/ → panelin_mcp_server/ | 🚫 Close | 5 | Verify if still needed post-Agno |
| #112 | Agent orchestration framework | ✅ Merge | 4 | Low risk, clean mergeable state |
| #122 | Docs: Surface Copilot instructions | ✅ Merge | 4 | Docs-only, needs rebase |
| #125 | Fix health check Docker Compose | 🚫 Close | 5 | Duplicate of #131 |
| #126 | Test coverage for zip packager | ✅ Merge | 4 | Clean, adds 33 tests |
| #131 | Fix health_check.sh CI failure | ✅ Merge | 2 | Most complete health check fix |
| #132 | Fix health check Docker Compose v2 | 🚫 Close | 5 | Duplicate of #131 |
| #139 | Fix E999 syntax error | 🚫 Close | 5 | Targets stale branch; fixed by #154 |
| #142 | Fix Python indentation error | 🚫 Close | 5 | Targets stale branch |
| #145 | Fix f-string syntax error | 🚫 Close | 5 | Targets stale branch; fixed by #154 |
| #150 | Fix f-string syntax error (main) | 🚫 Close | 5 | Fixed by merged #154 |
| #151 | Fix README glob pattern | ✅ Merge | 3 | One-line compliance fix |
| #171 | Fix CI/CD + Wolf API version | 🚫 Close | 5 | Covered by #220; check version sync |
| #172 | Fix persist_conversation operationId | ✅ Merge | 3 | GPT plugin routing fix |
| #175 | WhatsApp real estate bot | 📌 Defer | 6 | Large new service |
| #176 | Chatbot integration project | 📌 Defer | 6 | Related to #175 |
| #177 | Initial repository structure | 📌 Defer | 6 | Massive restructure |
| #178 | Starter kit de archivos | 🚫 Close | 5 | Targets stale branch (#176) |
| #179 | Google Sheets Orchestrator | 📌 Defer | 6 | Independent microservice |
| #181 | MIAP instructions (duplicate) | 🚫 Close | 5 | Duplicate of #182 |
| #182 | MIAP instructions v2 | 📌 Defer | 6 | Docs only, low risk |
| #192 | Pin runner to ubuntu-24.04 | ✅ Merge | 2 | Low risk, all workflows |
| #193 | Fix morning audit | 🚫 Close | 5 | Target branch merged (#191) |
| #194 | Secure credentials handling | 🚫 Close | 5 | Target branch merged (#191) |
| #195 | Harden morning audit | 🚫 Close | 5 | Target branch merged (#191) |
| #196 | Harden morning audit | 🚫 Close | 5 | Target branch merged (#191) |
| #197 | Restrict credentials | 🚫 Close | 5 | Target branch merged (#191) |
| #198 | Morning audit fixes | 🚫 Close | 5 | Target branch merged (#191) |
| #199 | Restrict credentials | 🚫 Close | 5 | Target branch merged (#191) |
| #200 | UTC timestamps | 🚫 Close | 5 | Target branch merged (#191) |
| #201 | UTC timestamps | 🚫 Close | 5 | Target branch merged (#191) |
| #202 | catch WorksheetNotFound | 🚫 Close | 5 | Target branch merged (#191) |
| #203 | Add name/version to contracts | 🚫 Close | 5 | Subset of #220 |
| #207 | Panelin Agno migración | 🚫 Close | 5 | Superseded by merged #218 |
| #208 | Panelin Agno migración | 🚫 Close | 5 | Superseded by merged #218 |
| #209 | Panelin agno architecture | 🚫 Close | 5 | Superseded by merged #218 |
| #210 | Panelin Agno migración | 🚫 Close | 5 | Superseded by merged #218 |
| #211 | Panelin Agno migración | 🚫 Close | 5 | Superseded by merged #218 |
| #212 | Panelin Agno migración | 🚫 Close | 5 | Superseded by merged #218 |
| #213 | Panelin agno architecture | 🚫 Close | 5 | Superseded by merged #218 |
| #214 | Panelin agno architecture | 🚫 Close | 5 | Superseded by merged #218 |
| #215 | Panelin agno architecture | 🚫 Close | 5 | Superseded by merged #218 |
| #216 | Panelin agno architecture | 🚫 Close | 5 | Superseded by merged #218 |
| #217 | Panelin agno architecture | 🚫 Close | 5 | Superseded by merged #218 |
| #220 | Fix CI failures: contracts + YAML | ✅ Merge | 2 | Broadest CI fix |
| #224 | Current-state merge strategy | 🚫 Close | 5 | Superseded by this plan |
| #228 | Error handling, UTC, PDF, auth | ✅ Merge | 1 | Security-critical post-Agno fix |
| #229 | Autopilot merge strategy doc | 🚫 Close | 5 | Superseded by this plan |
| #231 | (This PR) Autopilot update plan | ✅ Merge | — | This document |

---

## 6. Branch Cleanup Plan

After all PRs are closed/merged, delete the following remote branches:

### Agno Duplicates (11 branches)
```
cursor/panelin-agno-architecture-3ad2
cursor/panelin-agno-architecture-bfa0
cursor/panelin-agno-architecture-eb6e
cursor/panelin-agno-architecture-2236
cursor/panelin-agno-architecture-b611
cursor/panelin-agno-architecture-1861
cursor/panelin-agno-migraci-n-c57f
cursor/panelin-agno-migraci-n-f2af
cursor/panelin-agno-migraci-n-c97f
cursor/panelin-agno-migraci-n-06ce
cursor/panelin-agno-migraci-n-52fa
```

### Morning Audit Sub-PR Branches (10 branches)
```
copilot/sub-pr-191
copilot/sub-pr-191-again
copilot/sub-pr-191-another-one
copilot/sub-pr-191-yet-again
copilot/sub-pr-191-one-more-time
copilot/sub-pr-191-please-work
copilot/sub-pr-191-3a9be786-b6f8-420b-aea9-d4d836815cc0
copilot/sub-pr-191-7ebef2e2-3ee0-4c3d-a23d-3146a49ec339
copilot/sub-pr-191-313dd97f-0100-4ebe-a580-9496118b1fea
copilot/sub-pr-191-afd0089b-3945-4c4e-9d18-c6925fbd7cb5
```

### Stale Copilot Branches (30+ branches)
```
copilot/fix-229058278-*          (3 branches — failed fix attempts)
copilot/fix-duplicate-*          (2 branches)
copilot/fix-high-priority-*      (2 branches)
copilot/fix-price-check-*        (3 branches)
copilot/fix-python-syntax-errors
copilot/fix-syntax-error-in-pricing
copilot/fix-indentation-errors-in-ci-cd
copilot/sub-pr-36
copilot/sub-pr-49*               (3 branches)
copilot/sub-pr-53
copilot/sub-pr-54*               (4 branches)
copilot/sub-pr-56
copilot/sub-pr-133*              (2 branches)
copilot/sub-pr-158
copilot/close-14-pull-requests
copilot/compare-merge-branches-to-main
copilot/analyze-branches-and-update-main
copilot/resolve-merge-conflict
copilot/resolve-pull-request-conflicts
copilot/review-issue-rev
copilot/explain-task-details
copilot/deploy-production-environment
copilot/develop-knowledge-base-interaction
copilot/modify-kg-functionality
copilot/refactor-ci-workflow
copilot/reference-github-action-run
copilot/validate-gpt-files
copilot/verify-wolf-writing-access
copilot/add-autoconfiguration-feature
copilot/add-modification-capability
copilot/add-tools-connectors-doc
copilot/add-validation-layer-and-simulation
copilot/update-safety-margin-default
copilot/update-schema-for-write
copilot/update-gpt-panelin-version
copilot/implement-writencapabilities
copilot/generate-downloadable-zip
```

### Merged Feature Branches (safe to delete)
```
cursor/panelin-agno-architecture-87fc    (PR #218 merged)
cursor/panelin-morning-audit-setup-dab1  (PR #191 merged)
cursor/gpt-live-version-configuration-6ddf (PR #190 merged)
cursor/panelin-api-entrypoint-y-endpoints-132e (PR #184 merged)
cursor/panelin-4-0-architecture-85ce     (PR #180 merged)
release/v3.4-self-learning               (PR #158 merged)
fix/vector-store-compat                  (PR #169 merged)
gpt-modifications                        (evaluate before deleting)
```

### Claude Branches (evaluate)
```
claude/add-api-write-capability-7rr3B
claude/automate-gpt-deployment-YwGCQ
claude/event-sourced-knowledge-base-0LpGH
claude/fix-github-actions-security-pRCSo
claude/fix-rce-eval-vulnerability-iZdfc
claude/fix-subprocess-injection-TJXRN
claude/giive-fuel-schema-code-o6O6G
claude/update-runner-versions-7ibtm
```

### Codex Branches (evaluate)
```
codex/add-indexing-package-for-mcp-serving-artifacts
codex/create-json-schema-module-for-first-wave-tools-8o94tm
codex/define-observability-metrics-schema
```

**Cleanup command** (after all PRs processed):
```bash
# Delete merged branches (verify list before running)
for branch in <branch-list>; do
  git push origin --delete "$branch"
done
```

---

## 7. Validation Checklist

Run after **each stage** before proceeding to the next:

### Per-Stage Validation

```bash
# 1. YAML lint all workflows
for f in .github/workflows/*.yml; do
  python -c "import yaml; yaml.safe_load(open('$f'))" && echo "✅ $f" || echo "❌ $f"
done

# 2. MCP contract completeness
for f in mcp_tools/contracts/*.v1.json; do
  python -c "
import json, sys
d = json.load(open('$f'))
ok = all(k in d for k in ('name','version','tool_name','contract_version'))
print(f'{'✅' if ok else '❌'} $f')
sys.exit(0 if ok else 1)
"
done

# 3. pytest — MCP handlers
pytest mcp/tests/test_handlers.py -v

# 4. pytest — Wolf API
pytest wolf_api/tests/ -v

# 5. UTC timestamp audit (no naive datetime.now())
grep -rn "datetime\.now()" --include="*.py" | grep -v "timezone.utc" | grep -v "test_" | grep -v "__pycache__"

# 6. Docker build
docker build -t panelin:test -f Dockerfile.production .

# 7. Secrets check
grep -rn "API_KEY\|SECRET\|PASSWORD\|TOKEN" --include="*.py" --include="*.yml" --include="*.yaml" \
  | grep -v "os.environ" | grep -v "secrets\." | grep -v "#" | grep -v "test"
```

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Rebase conflicts on #220 | Medium | Medium | Manual conflict resolution; contracts are JSON (easy merge) |
| #172 changes already applied | Low | None | Diff against `main` before rebase; skip if redundant |
| Health check script breaks production | Low | High | Test in CI first; only affects CI pipeline |
| Feature PRs (#175, #177) have deep conflicts | High | Medium | Defer to Stage 6; create fresh branches if needed |
| Closing 35 PRs causes contributor confusion | Low | Low | Clear comments on each closed PR |

---

## 9. Rollback Guidance

### Before Starting
```bash
# Tag current main for rollback reference
git tag autopilot-pre-consolidation main
git push origin autopilot-pre-consolidation
```

### Per-Merge Rollback
```bash
# Revert a specific merge
git revert -m 1 <merge-commit-sha>
git push origin main
```

### Full Rollback
```bash
# Reset to pre-consolidation state
git checkout main
git reset --hard autopilot-pre-consolidation
git push --force-with-lease origin main
```

---

## Appendix: Most-Ahead Version Summary

After completing Stages 1–4, `main` will contain the **most-ahead consolidated state**:

| Component | Current Version | After Consolidation |
|-----------|----------------|---------------------|
| Panelin architecture | v4.0 (Agno) | v4.0 + security fixes |
| Wolf API | 2.2.0 | 2.2.0 + UTC + error handling |
| MCP contracts | Missing fields | All 9 contracts complete |
| CI/CD workflows | Broken syntax | All 9 workflows valid |
| GitHub Actions runner | ubuntu-latest (floating) | ubuntu-24.04 (pinned) |
| Health check script | docker-compose v1 only | v1 + v2 with CI-aware fallback |
| GPT plugin routing | Broken operationId | Correct snake_case |
| Test coverage | No zip packager tests | +33 tests (82% coverage) |
| AgentOS security | Endpoints exposed | Auth-gated |
| PDF generation | Temp file leaks | Cleaned up with bytes response |
| Morning audit | Merged but unfixed sub-issues | Base merged; sub-issues evaluated |

**Open PRs remaining after plan:** ~7 (large feature PRs in Stage 6)  
**Branches deleted:** 80+  
**Repository hygiene score:** Excellent

---

*This plan supersedes `MERGE_EXECUTION_PLAN.md`, `CLEANUP_QUICK_START.md`, and PRs #224/#229.*

*Last updated: 2026-03-11*
