# GPT-PANELIN V3.2 - Pull Request Dependency Map

## Visual PR Relationship Map

```
┌─────────────────────────────────────────────────────────────────┐
│                           MAIN BRANCH                            │
│                    Current: 6c73ce4 (PR #66)                     │
└─────────────────────────────────────────────────────────────────┘
          │
          │
          ├─────> PR #77 (THIS PR)
          │       ├─ Status: Clean, 0 changes
          │       └─ Purpose: Documentation of cleanup strategy
          │
          ├─────> PR #49 ⚠️ CRITICAL - Module Shadowing Fix
          │       ├─ Status: DIRTY (conflicts)
          │       ├─ Changes: +57/-53 (20 files)
          │       ├─ Based on: OLD main (4022cab)
          │       └─ Duplicated by: PR #37, PR #44
          │
          ├─────> PR #54 ⭐ HIGH PRIORITY - V1 Contracts
          │       │  Status: DIRTY (conflicts)
          │       │  Changes: +1270/-136 (24 files)
          │       │  Based on: OLD main (4022cab)
          │       │
          │       ├─────> PR #58 (Sub-PR to #54)
          │       │       └─ May be obsolete after #54 merge
          │       │
          │       ├─────> PR #68 (Sub-PR to #54)
          │       │       └─ Fix price_check handler
          │       │
          │       ├─────> PR #71 (Sub-PR to #54)
          │       │       └─ Align v1 contracts
          │       │
          │       └─────> PR #76 (Attempted merge)
          │               └─ Status: DIRTY - CLOSE THIS
          │
          ├─────> PR #73 (Low Priority - README)
          │       └─ Can be recreated if needed
          │
          ├─────> PR #69 (Code Review Fixes)
          │       └─ Needs evaluation after Phase 1
          │
          └─────> PR #74 (CI/CD Pipeline - WIP)
                  └─ Wait for author to complete

┌──────────────────────────────────────────────────────────────┐
│                    Feature Branch: PR #49                     │
│              cursor/general-development-task-14a4             │
└──────────────────────────────────────────────────────────────┘
          │
          ├─────> PR #70 (Explanation doc)
          │       └─ Obsolete after #49 merges
          │
          ├─────> PR #75 (Another shadowing fix)
          │       └─ Duplicate - CLOSE THIS
          │
          └─────> (Also duplicated by PR #37, #44 → CLOSE)
```

## Color Legend

- ⚠️ **CRITICAL** - Blocks functionality
- ⭐ **HIGH PRIORITY** - Core feature baseline
- 🔴 **DIRTY** - Has merge conflicts
- ✅ **CLEAN** - No conflicts
- ❌ **CLOSE** - Duplicate or obsolete
- 📝 **WIP** - Work in progress

## Conflict Matrix

| PR# | Conflicts With | Reason |
|-----|----------------|--------|
| 49  | main (6c73ce4) | Based on old main (4022cab), ~20 files changed |
| 54  | main (6c73ce4) | Based on old main (4022cab), ~24 files changed |
| 58  | Branch base    | Base branch (PR #54) has conflicts |
| 68  | Branch base    | Base branch (PR #54) has conflicts |
| 71  | Branch base    | Base branch (PR #54) has conflicts |
| 76  | Branch base    | Base branch (PR #54) has conflicts |
| 70  | Branch base    | Base branch (PR #49) has conflicts |
| 75  | Branch base    | Base branch (PR #49) has conflicts |

## Merge Order (To Minimize Conflicts)

```
Step 1: Merge PR #49 (Module Shadowing)
   └─> This fixes the critical import bug
   └─> Affects: ~20 files with import statements
   └─> After merge: PRs #37, #44, #70, #75 become obsolete

Step 2: Merge PR #54 (V1 Contracts)
   └─> This establishes the contract baseline
   └─> Affects: ~24 files with contracts and handlers
   └─> After merge: Evaluate if #58, #68, #71, #76 are still needed

Step 3: Close Duplicate/Obsolete PRs
   └─> Close: #37, #44, #70, #73, #75, #76
   └─> Reason: Duplicates or superseded

Step 4: Evaluate Remaining PRs
   └─> Review: #58, #68, #69, #71, #74
   └─> Rebase needed PRs on updated main
   └─> Merge valuable work
```

## File Impact Analysis

### Files Changed by PR #49 (Module Shadowing)
```
panelin_mcp_server/                   (renamed from mcp/)
├── __init__.py                       (import updates)
├── server.py                         (import updates)
├── handlers/
│   ├── pricing.py                   (import updates)
│   ├── catalog.py                   (import updates)
│   └── bom.py                       (import updates)
└── requirements.txt                 (no change needed)

Documentation:
├── MCP_QUICK_START.md               (path references)
├── MCP_IMPLEMENTATION_SUMMARY.md    (path references)
└── README.md                        (path references)

Test Files:
└── test_mcp_handlers_v1.py          (import updates)
```

### Files Changed by PR #54 (V1 Contracts)
```
mcp_tools/contracts/                 (NEW directory)
├── __init__.py                      (NEW - contract registry)
├── price_check.v1.json             (NEW)
├── catalog_search.v1.json          (NEW)
├── bom_calculate.v1.json           (NEW)
├── quotation_store.v1.json         (NEW)
└── examples/                        (NEW - test fixtures)

openai_ecosystem/
├── client.py                        (tool-call extraction)
└── test_client.py                  (new tests)

docs/
└── README.md                        (compatibility table)
```

### Overlap Analysis
- **Direct Overlap**: Minimal (different directories)
- **Import Conflicts**: Yes (if #54 files import from mcp/)
- **Documentation Conflicts**: Yes (both update docs/)

## Resolution Strategy for Each Conflict Type

### Type 1: Import Path Conflicts (PR #49)
```python
# Conflict in mcp/handlers/pricing.py vs panelin_mcp_server/handlers/pricing.py
<<<<<<< HEAD (main)
from mcp.handlers.catalog import search_catalog
=======
from panelin_mcp_server.handlers.catalog import search_catalog
>>>>>>> PR #49

# Resolution: Use panelin_mcp_server (new name)
from panelin_mcp_server.handlers.catalog import search_catalog
```

### Type 2: Contract Schema Conflicts (PR #54)
```json
# Conflict in mcp_tools/contracts/price_check.v1.json
<<<<<<< HEAD (main)
(file doesn't exist)
=======
{
  "contract_version": "v1",
  ...
}
>>>>>>> PR #54

# Resolution: Accept entire new file from PR #54
```

### Type 3: Documentation Conflicts
```markdown
# Conflict in docs/README.md
<<<<<<< HEAD (main)
See `mcp/` directory for implementation
=======
See `panelin_mcp_server/` directory for implementation
And see `mcp_tools/contracts/` for v1 schemas
>>>>>>> PR #54

# Resolution: Combine both changes
See `panelin_mcp_server/` directory for implementation
and `mcp_tools/contracts/` for v1 schemas
```

## Testing Impact

### After PR #49 Merge
**Must Test**:
- [ ] MCP server starts: `python -m panelin_mcp_server.server`
- [ ] External mcp imports work: `python -c "from mcp.server import Server"`
- [ ] Internal imports work: `python -c "from panelin_mcp_server.handlers.pricing import handle_price_check"`
- [ ] All tests pass: `pytest`

### After PR #54 Merge
**Must Test**:
- [ ] Contract schemas validate: `python -c "import json; json.load(open('mcp_tools/contracts/price_check.v1.json'))"`
- [ ] Contract registry loads: `python -c "from mcp_tools.contracts import TOOL_CONTRACT_VERSIONS; print(TOOL_CONTRACT_VERSIONS)"`
- [ ] Tool-call extraction tests pass: `pytest openai_ecosystem/test_client.py`

## Estimated Conflict Resolution Time

| PR# | Files with Conflicts | Resolution Time | Complexity |
|-----|---------------------|-----------------|------------|
| 49  | ~20 files           | 2-3 hours       | Medium     |
| 54  | ~24 files           | 2-3 hours       | Medium     |
| 58  | Unknown             | 1-2 hours       | Low        |
| 68  | Unknown             | 1-2 hours       | Low        |
| 71  | Unknown             | 1-2 hours       | Low        |

**Total**: 8-12 hours for all conflicts

## Risk Mitigation Checklist

Before starting:
- [ ] Create backup branch: `git checkout main && git checkout -b backup-main-$(date +%Y%m%d)`
- [ ] Tag current main: `git tag backup-before-cleanup`
- [ ] Verify tests run on current main
- [ ] Document current test pass rate

During merges:
- [ ] Test after each merge
- [ ] Create checkpoint tags
- [ ] Update CHANGELOG if present
- [ ] Notify team of progress

After completion:
- [ ] Full test suite pass
- [ ] Documentation updated
- [ ] Close obsolete PRs with comments
- [ ] Archive old branches (optional)

## Communication Plan

### When Closing Duplicate PRs
```
Template:
"Thank you for this PR! We're consolidating module shadowing fixes into PR #49.
To avoid duplicates and conflicts, we're closing this PR.

Related: #49 (Module Shadowing Fix)
For status: #77 (Cleanup Coordination)"
```

### When Evaluating Dependent PRs
```
Template:
"This PR was based on [feature-branch]. Now that [feature-branch] has been
merged to main, we need to evaluate if this PR is still needed.

Please rebase on current main if you'd like to continue this work.
Otherwise, we'll close this in [X] days to clean up the PR backlog.

Related: #77 (Cleanup Coordination)"
```

## Success Metrics Dashboard

| Metric | Start | Target | Current |
|--------|-------|--------|---------|
| Open PRs | 14 | < 5 | 14 |
| PRs with conflicts | ~10 | 0 | ~10 |
| Duplicate PRs | 4 | 0 | 4 |
| Days since oldest PR | ~30 | N/A | ~30 |
| Test pass rate | ?% | 100% | ?% |

## Quick Reference Commands

```bash
# Check status of all PRs
gh pr list --limit 20

# View specific PR
gh pr view 49

# Check conflicts for PR
gh pr diff 49

# Close PR with message
gh pr close 37 --comment "Duplicate of #49"

# Rebase a PR
git fetch origin pull/49/head:pr-49
git checkout pr-49
git rebase origin/main

# Create backup
git tag backup-$(date +%Y%m%d-%H%M%S)
git push origin --tags
```

---

**Last Updated**: 2026-02-14  
**Status**: Analysis Complete, Awaiting Approval  
**Next Action**: Review MERGE_EXECUTION_PLAN.md for detailed steps
