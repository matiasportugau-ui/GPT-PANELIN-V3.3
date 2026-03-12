# Current Merge Plan — GPT-PANELIN-Final

> **This is the single source of truth for PR merge strategy.**
> Generated: 2026-03-11 | Supersedes: `MERGE_EXECUTION_PLAN.md`, `CLEANUP_QUICK_START.md`

---

## 1. PR Topology Summary

As of 2026-03-11 there are **60+ open PRs** grouped into the following clusters:

| Cluster | PRs | Status |
|---------|-----|--------|
| **CI/CD fixes** | #171, #203, #220 | Ready / Near-ready |
| **Agno architecture migration** | #208–#218 (11 PRs), #228 | #218 is lead candidate; rest are duplicates/drafts |
| **Morning-audit stack** | #191–#202 (9 sub-PRs) | All based on a stale base branch |
| **Docs / merge plan** | #122, #224, #229 | Superseded by this PR |
| **Module-shadowing rename** | #37, #44, #49, #70, #79, #80, #81 | Largely stale; mcp/ still used on main |
| **Pricing fixes** | #84, #85, #86, #87, #96, #97 | Empty or no-op diffs vs current main |
| **Other stale/WIP** | #58, #68, #71, #82, #83, #112, #125, #126, #131, #132, #139, #142, #145, #150, #151, #172, #175–#182, #192–#199 | See per-PR actions §4 |

---

## 2. Recommended Merge Order

Follow **low-risk → high-value** sequencing. Complete each stage and validate before proceeding.

```
Stage 1 (CI stabilisation)
  └─ Merge  PR #220   ← Fixes CI contract fields + ci-cd.yml syntax
  └─ Review PR #171   ← Overlapping CI fixes + Wolf API version sync

Stage 2 (Security-critical fixes)
  └─ Merge  PR #228   ← Must land with or just after #218; security + correctness

Stage 3 (Agno architecture — main migration line)
  └─ Merge  PR #218   ← The single lead Agno PR (non-draft, 48 files, 1 864 +/- 738)
      → Requires: #228 already applied OR cherry-picked onto #218 first

Stage 4 (Morning audit consolidation)
  └─ Create fresh branch `fix/morning-audit-main` off main
  └─ Cherry-pick best commits from PR #198 / #193
  └─ Close PRs #193–#202 with supersession note

Stage 5 (Docs / minor improvements)
  └─ Merge  PR #192   ← Pin ubuntu-24.04 (low risk, 1-line change)
  └─ Review PR #172   ← operationId fix for GPT plugin routing
  └─ Merge  PR #122   ← Surface Copilot instructions in doc hierarchy
  └─ Close  PR #224   ← Superseded by this PR (#229)

Stage 6 (Deferred / close)
  └─ Close all remaining stale/duplicate PRs (see §4)
```

---

## 3. Agno Migration: Single Source of Truth

### The problem
Eleven PRs share the "Panelin agno architecture / migración" title. They were generated in parallel by automated agents from similar prompts and contain heavily overlapping content.

### Why PR #218 is the lead candidate

| Criterion | PR #218 | Others (#208–#217) |
|-----------|---------|--------------------|
| Draft | **No** — mergeable | Yes (all drafts) |
| Commits | 2 (focused) | Varies |
| Changed files | 48 | Overlapping |
| Review comments | 4 (addressed by #228) | 0–2 |
| Base branch | `main` | `main` |
| Last updated | 2026-03-11 | Stale |

### Recommended approach for Agno consolidation

```
Option A (Recommended) — merge #218 + #228 as a pair
  1. Merge PR #228 into branch cursor/panelin-agno-architecture-87fc first
     (or cherry-pick its 3 changed files onto the branch)
  2. Rebase cursor/panelin-agno-architecture-87fc onto latest main
     to resolve the current "dirty" state
  3. Squash-merge PR #218 into main with a detailed commit message
  4. Close PRs #208–#217 with comment:
     "Superseded by #218 (merged). See CURRENT_MERGE_PLAN.md."

Option B — Fresh consolidation branch
  1. git checkout -b migration/agno-consolidation main
  2. Cherry-pick the unique additions from the best draft PRs (if any)
  3. Apply PR #228 fixes on top
  4. Open a new clean PR and merge it
  5. Close #208–#218 as superseded
```

**Use Option A** unless a code review of #218 reveals significant issues that make Option B necessary.

---

## 4. Per-PR Actions

### Stage 1 — CI stabilisation

#### PR #220 — Fix CI failures: missing contract fields and ci-cd.yml syntax errors
- **Action**: ✅ **MERGE** (squash)
- **Why**: Restores Health Check and CI/CD reliability; fixes 9 contract JSON files and 3 YAML bugs
- **Risks**: Overlaps with #171 on `ci-cd.yml`; resolve conflict by taking #220's version of that file
- **Validation**:
  - [ ] `health-check.yml` passes in CI
  - [ ] `ci-cd.yml` parses without errors (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"`)
  - [ ] All 9 `mcp_tools/contracts/*.v1.json` contain `name` and `version` fields

#### PR #171 — Fix CI/CD workflow failures and Wolf API version drift
- **Action**: 🔍 **REVIEW before merging** — extract unique value
- **Why**: Partially overlaps #220; contains unique Wolf API version sync (`2.1.0` → `2.2.0`) and `deploy-wolf-api.yml` pre-flight secrets validation
- **Unique value not in #220**:
  - `wolf_api/__init__.py`, `wolf_api/DEPLOYMENT.md`, `wolf_api/tests/test_kb_conversations.py` version bump to 2.2.0
  - `deploy-wolf-api.yml` pre-flight secrets check step
- **Recommendation**: If merging #220 first, cherry-pick only the Wolf API version/secrets changes from #171's branch into main, then close #171
- **Validation**:
  - [ ] `wolf_api/tests/test_kb_conversations.py` version assertion passes
  - [ ] `deploy-wolf-api.yml` secrets validation step present

---

### Stage 2 — Security-critical fixes

#### PR #228 — fix: error handling, UTC timestamps, PDF temp file cleanup, AgentOS auth
- **Action**: ✅ **MERGE** onto PR #218's branch first, then land with #218
- **Why**: Security fix (AgentOS auth env var), temp file leak, and fail-fast startup — all affect the Agno migration branch directly
- **Files changed**: `wolf_api/main.py`, `wolf_api/pdf_cotizacion.py`, `cloudbuild.yaml`
- **Base**: `cursor/panelin-agno-architecture-87fc` (PR #218's branch)
- **Risks**: None — surgical fixes; no behaviour changes outside the three files
- **Validation**:
  - [ ] `wolf_api/main.py` — `_include_optional_router` re-raises non-`ImportError` exceptions
  - [ ] `wolf_api/pdf_cotizacion.py` — no `datetime.now()` calls remain (all use `timezone.utc`)
  - [ ] `wolf_api/pdf_cotizacion.py` — `generar_pdf` returns `Response` bytes, not `CotizacionResponse` with `file://` URL
  - [ ] `cloudbuild.yaml` — `PANELIN_AGENTOS_ENABLE_AUTH=true` present in `--set-env-vars`
  - [ ] `pytest wolf_api/tests/` passes

---

### Stage 3 — Agno architecture migration

#### PR #218 — Panelin agno architecture
- **Action**: ✅ **MERGE** (squash, after rebasing on main)
- **Why**: Only non-draft Agno PR; reviewed; fixes Phase 0 bugs (BOM dimension swap, `sub_familia` pricing, security hardening); introduces Agno workflow/agent framework
- **Prerequisites**: PR #220 merged; PR #228 applied on branch; branch rebased on latest main
- **Risks**:
  - Large diff (48 files, +1864/-738) — review carefully for regression
  - Currently "dirty" (needs rebase)
  - Introduces new dependencies (agno, AgentOS); ensure `requirements.txt` / `pyproject.toml` updated
- **Validation**:
  - [ ] `pytest mcp/tests/test_handlers.py` passes
  - [ ] `pytest wolf_api/tests/` passes
  - [ ] Docker image builds (`docker build -f Dockerfile.production .`)
  - [ ] Agno workflow can be imported without error
  - [ ] No hardcoded passwords or API keys introduced
  - [ ] CORS origins not set to `*`

#### PRs #208–#217 — Agno architecture duplicates
- **Action**: 🚫 **CLOSE ALL** after #218 is merged
- **Comment to post**: "Superseded by #218 (squash-merged into main). See `CURRENT_MERGE_PLAN.md` for rationale."

---

### Stage 4 — Morning audit consolidation

#### PRs #193–#202 — Morning audit sub-PRs
- **Background**: All target base branch `cursor/panelin-morning-audit-setup-dab1`, which is itself not merged into main. They are a nested stack of incremental fixes on top of that stale branch.
- **Action**: 🔄 **CONSOLIDATE into fresh branch**

**Steps:**
```bash
# 1. Create fresh branch
git checkout -b fix/morning-audit-consolidated main

# 2. Cherry-pick best commits
#    PR #201: UTC timestamp fix (most focused)
#    PR #202: WorksheetNotFound specific exception
#    PR #199: credentials cleanup in manual_audit workflow
git cherry-pick <sha-from-201> <sha-from-202> <sha-from-199>

# 3. Open a new clean PR against main
# 4. Close PRs #193–#202 with supersession comment
```

- **Validation**:
  - [ ] `scripts/morning_audit.py` uses `datetime.now(timezone.utc)` throughout
  - [ ] `.github/workflows/manual_audit.yml` does not write credentials to disk unnecessarily
  - [ ] Specific `WorksheetNotFound` exception caught instead of bare `Exception`

---

### Stage 5 — Low-risk improvements

#### PR #192 — Pin GitHub Actions runner to ubuntu-24.04
- **Action**: ✅ **MERGE** (fast)
- **Risk**: Minimal — runner image pin is best practice
- **Validation**: [ ] CI passes on ubuntu-24.04

#### PR #172 — Fix persist_conversation operationId mismatch
- **Action**: 🔍 **REVIEW** — if diff is still valid against current main, merge
- **Risk**: Low (GPT plugin routing fix)
- **Validation**: [ ] OpenAPI schema validates with `python validate_gpt_files.py`

#### PR #122 — Surface Copilot instructions in documentation hierarchy
- **Action**: ✅ **MERGE** (docs only)
- **Risk**: None
- **Validation**: None required beyond manual review

#### PR #224 — Earlier merge strategy report
- **Action**: 🚫 **CLOSE** — superseded by this PR (#229)
- **Comment**: "Superseded by #229 which produces `CURRENT_MERGE_PLAN.md` as the authoritative plan."

---

### Stage 6 — Close stale/duplicate/empty PRs

The following PRs should be **closed without merging**. Post the indicated comment on each.

#### Module-shadowing rename (stale — `mcp/` directory is intentional on main)

| PR | Title | Comment |
|----|-------|---------|
| #37 | Fix module shadowing: rename mcp/ | "The `mcp/` directory is intentional. Closing as stale per `CURRENT_MERGE_PLAN.md`." |
| #44 | Rename mcp/ to panelin_mcp_server/ | Same as above |
| #49 | General development task | "Vague scope, no clear diff value. Closing per merge plan." |
| #70 | Explain merge conflict resolution | "Documentation-only explanation of conflicts that no longer exist." |
| #79 | Consolidate 14 open PRs | "Consolidation attempt superseded by current plan. Closing." |
| #80 | Fix module shadowing (analyze branches) | "Superseded. mcp/ rename not needed." |
| #81 | Resolve PR #76 merge conflicts | "PR #76 closed; this has no remaining value." |

#### Pricing fixes (0-diff vs current main)

| PR | Title | Comment |
|----|-------|---------|
| #84 | Fix Python SyntaxError in pricing.py | "Issue does not exist in current main. Closing per merge plan." |
| #85 | Fix syntax errors in pricing module | Same |
| #86 | Fix multiple issues in handle_price_check | Same |
| #87 | Fix syntax errors in pricing.py | Same |
| #96 | Fix SyntaxError from duplicate function definition | "Superseded; issue resolved in main." |
| #97 | Fix SyntaxError in pricing.py | Same |

#### Old sub-PRs on stale bases

| PR | Title | Comment |
|----|-------|---------|
| #58 | Address PR #54 review feedback | "PR #54 merged; feedback PR is stale." |
| #68 | Fix price_check handler (sub-PR of #54) | "Base PR #54 merged. Closing stale sub-PR." |
| #71 | Add test suite (sub-PR on codex branch) | "Base branch never merged. Closing." |
| #82 | Add shortcuts MCP tools | "WIP, no tests, stale base. Closing." |
| #83 | Fix E999 IndentationError | "Applied in main via PR #88. Closing." |
| #112 | Agent orchestration framework | "Broad scope WIP. Closing per plan; re-open as a new focused PR if needed." |
| #125 | Fix health check Docker compat | "Superseded by #132 and subsequent CI work. Closing." |
| #126 | Add test coverage for zip package | "WIP. Closing; re-open if test coverage is desired." |
| #131 | Fix health_check.sh CI failure | "Superseded. Closing." |
| #132 | Fix health check script Docker Compose v2 | "Superseded by CI improvements in #220. Closing." |
| #139 | Fix E999 syntax in deploy_gpt_assistant.py | "Base branch `claude/automate-gpt-deployment-YwGCQ` not merged. Closing." |
| #142 | Fix Python indentation in workflow | "Same stale base as #139. Closing." |
| #145 | Fix f-string syntax in deploy_gpt_assistant.py | "Same stale base. Closing." |
| #150 | Fix f-string syntax error (deployment script) | "Draft, stale. Closing." |
| #151 | Fix README glob pattern | "Low-value; README glob pattern is non-blocking. Closing." |

#### Off-topic / chatbot project PRs

| PR | Title | Comment |
|----|-------|---------|
| #175 | Arquitectura asistente inmobiliario | "Unrelated project scope. Closing per merge plan." |
| #176 | Proyecto integracion chatbot | Same |
| #177 | Initial repository structure (chatbot) | "Off-topic branch, closing." |
| #178 | Starter kit de archivos | "Sub-PR of #176. Closing." |
| #179 | Orquestador de Google Sheets | "Superseded by panelin_sheets_orchestrator/ module on main. Closing." |
| #181 | Instrucciones núcleo MIAP | "Draft, unrelated scope. Closing." |
| #182 | Instrucciones núcleo MIAP (duplicate) | "Duplicate of #181. Closing." |
| #121 | Fix issues in export_gpt_config.py | "Stale base branch. Closing." |

---

## 5. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PR #218 rebase introduces merge conflicts | High | Medium | Rebase incrementally; use `git mergetool` |
| PR #220 and #171 conflict on `ci-cd.yml` | High | Low | Apply #220 first; cherry-pick unique #171 hunks |
| Agno dependencies missing in `requirements.txt` | Medium | High | Verify `pip install -r requirements.txt` succeeds in Docker build |
| `cloudbuild.yaml` `PANELIN_AGENTOS_ENABLE_AUTH=true` breaks unauthenticated clients | Low | Medium | Ensure GCP IAM / service account grants are in place before deploying |
| Merging morning-audit cherry-picks introduces duplicate code | Medium | Low | Review diff carefully before opening consolidation PR |
| Closing 40+ PRs triggers GitHub notification storm | Low | Low | Batch-close with a single comment referencing this doc |

---

## 6. Rollback Guidance

Before merging any stage, tag the current `main` tip:

```bash
git tag pre-merge-stage-N main
git push origin pre-merge-stage-N
```

To roll back a bad merge:

```bash
# Option A: revert the merge commit
git revert -m 1 <merge-sha>
git push origin main

# Option B: reset to tag (force — requires branch protection temporarily disabled)
git checkout main
git reset --hard pre-merge-stage-N
git push --force-with-lease origin main
```

---

## 7. Validation Checklist (all stages)

After each stage is complete, run the following:

```bash
# 1. CI/CD workflow YAML validity
python -c "
import yaml, os, sys
workflows = [f for f in os.listdir('.github/workflows') if f.endswith('.yml')]
for w in workflows:
    with open(f'.github/workflows/{w}') as fh:
        yaml.safe_load(fh)
    print(f'OK: {w}')
"

# 2. MCP contract completeness
python -c "
import json, os, sys
ok = True
for f in os.listdir('mcp_tools/contracts'):
    if not f.endswith('.json'): continue
    with open(f'mcp_tools/contracts/{f}') as fh:
        d = json.load(fh)
    for field in ('name', 'version', 'tool_name', 'contract_version'):
        if field not in d:
            print(f'MISSING {field} in {f}'); ok = False
if ok: print('All contracts OK')
"

# 3. MCP handler tests
pytest mcp/tests/test_handlers.py -v

# 4. Wolf API tests
pytest wolf_api/tests/ -v

# 5. UTC timestamp check (no naive datetime.now() in critical files)
grep -rn 'datetime\.now()' wolf_api/ mcp/ scripts/ || echo 'No naive datetime.now() found'

# 6. Docker build
docker build -f Dockerfile.production -t panelin-test:latest . --no-cache

# 7. No hardcoded secrets (basic check)
grep -rn 'password\s*=\s*["\x27][^"\x27{][^"\x27]*["\x27]' wolf_api/ mcp/ panelin_v4/ || echo 'No obvious hardcoded passwords'
```

---

## 8. Document Update History

| Date | Change |
|------|--------|
| 2026-03-11 | Initial version created (PR #229). Supersedes `MERGE_EXECUTION_PLAN.md` and `CLEANUP_QUICK_START.md`. |
