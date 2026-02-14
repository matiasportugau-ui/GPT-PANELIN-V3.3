# Repository Cleanup: Execution Plan

**Goal**: Clean up 14 open PRs and resolve merge conflicts in the GPT-PANELIN-V3.2 repository

## Prerequisites

- [x] Full repository analysis completed
- [x] Conflict patterns identified
- [ ] Maintainer approval for plan
- [ ] Backup of current main branch

## Execution Steps

### PHASE 1: Foundation - Critical Bug Fixes

#### Step 1.1: Merge PR #49 - Fix Module Shadowing

**PR #49**: Rename `mcp/` to `panelin_mcp_server/`  
**Status**: Dirty (conflicts with main)  
**Branch**: `cursor/general-development-task-14a4`  
**Base**: main (`4022cab` → needs update to `6c73ce4`)

**Why Critical**: The local `mcp/` directory shadows the external `mcp` PyPI package, preventing the MCP server from starting.

**Commands**:
```bash
# Fetch latest changes
git fetch origin main
git fetch origin cursor/general-development-task-14a4

# Create a working branch
git checkout -b fix-module-shadowing-rebase origin/cursor/general-development-task-14a4

# Rebase on current main
git rebase origin/main

# Resolve conflicts (see conflict guide below)
# After resolving each conflict:
git add <resolved-files>
git rebase --continue

# Test the changes
python -c "from panelin_mcp_server.server import app; print('Import successful')"

# Push for review
git push origin fix-module-shadowing-rebase

# Create new PR or update existing #49
```

**Expected Conflicts**:
- Import statements in ~20 files
- Documentation references to `mcp/` directory
- Test files referencing old paths

**Conflict Resolution Pattern**:
```python
# BEFORE (conflicts with external mcp package)
from mcp.handlers.pricing import handle_price_check
from mcp.server import app

# AFTER (no conflict)
from panelin_mcp_server.handlers.pricing import handle_price_check
from panelin_mcp_server.server import app
```

**Testing Checklist**:
- [ ] MCP server starts without import errors
- [ ] `from mcp.server import Server` imports external package
- [ ] All internal imports use `panelin_mcp_server`
- [ ] Documentation updated with new paths

---

#### Step 1.2: Merge PR #54 - Add v1 MCP Contracts

**PR #54**: Add v1 MCP tool contracts and align tool-call extraction  
**Status**: Dirty (conflicts with main)  
**Branch**: `codex/create-json-schema-module-for-first-wave-tools-8o94tm`  
**Base**: main (`4022cab` → needs update to `6c73ce4`)

**Why Important**: Establishes contract baseline for all MCP tool integrations.

**Commands**:
```bash
# Fetch latest
git fetch origin codex/create-json-schema-module-for-first-wave-tools-8o94tm

# Create working branch
git checkout -b add-v1-contracts-rebase origin/codex/create-json-schema-module-for-first-wave-tools-8o94tm

# Rebase on main (with #49 merged)
git rebase origin/main

# Resolve conflicts
git add <resolved-files>
git rebase --continue

# Test contracts
python -c "from mcp_tools.contracts import TOOL_CONTRACT_VERSIONS; print(TOOL_CONTRACT_VERSIONS)"

# Run contract validation tests
pytest -q openai_ecosystem/test_client.py

# Push for review
git push origin add-v1-contracts-rebase
```

**Expected Conflicts**:
- Handler files that may reference `mcp/` paths (if any)
- Documentation mentioning tool versions

**Testing Checklist**:
- [ ] Contract schema files are valid JSON
- [ ] `pytest openai_ecosystem/test_client.py` passes (36 tests)
- [ ] Tool call extraction works correctly
- [ ] Contract registry accessible

---

### PHASE 2: Cleanup - Close Duplicates

These PRs duplicate work in #49 or are superseded:

#### Step 2.1: Close PR #37
```
Title: Fix module shadowing: rename mcp/ to panelin_mcp_server/
Reason: Duplicate of PR #49
Action: Close with comment pointing to #49
```

#### Step 2.2: Close PR #44
```
Title: Rename mcp/ to panelin_mcp_server/ to resolve module shadowing
Reason: Duplicate of PR #49
Action: Close with comment pointing to #49
```

#### Step 2.3: Close PR #76
```
Title: Review and merge all branches to main
Reason: Superseded by this PR #77
Action: Close with comment pointing to #77
```

#### Step 2.4: Close PR #73 (Optional - Low Priority)
```
Title: Readme missing files
Reason: Low priority documentation that can be recreated
Action: Close with note to reopen if needed
```

**GitHub Commands** (These cannot be done programmatically):
- Navigate to each PR
- Add closing comment explaining why
- Click "Close pull request" button

---

### PHASE 3: Evaluate Dependent PRs

After #49 and #54 are merged, reassess these PRs:

#### PR #58: Address PR #54 review feedback
**Base**: `codex/create-json-schema-module-for-first-wave-tools-8o94tm` (feature branch)  
**Action**: 
- If #54 is merged, this PR becomes moot (feedback already addressed)
- **Recommendation**: Close as resolved by #54 merge

#### PR #68: Fix price_check handler
**Base**: `codex/create-json-schema-module-for-first-wave-tools-8o94tm` (feature branch)  
**Action**:
- Examine if fixes are still needed after #54 merges
- If yes, rebase onto main
- If no, close

#### PR #70: Explain merge conflict resolution
**Base**: `cursor/general-development-task-14a4` (feature branch)  
**Action**:
- This is explanatory documentation for resolving conflicts in #49
- **Recommendation**: Close once #49 is merged (no longer needed)

#### PR #71: Align v1 MCP contract schemas
**Base**: `codex/create-json-schema-module-for-first-wave-tools-8o94tm` (feature branch)  
**Action**:
- Examine alignment after #54 merges
- Rebase if still needed, close if superseded

#### PR #75: Resolve module shadowing
**Base**: `cursor/general-development-task-14a4` (feature branch)  
**Action**:
- Another attempt at fixing module shadowing
- **Recommendation**: Close after #49 is merged

---

### PHASE 4: Remaining Infrastructure PRs

#### PR #69: Code review: Fix indentation errors and security vulnerabilities
**Base**: main  
**Status**: Unknown  
**Action**:
1. Fetch and examine the PR
2. Rebase on current main (with #49 and #54 merged)
3. Run security scans to verify fixes
4. Merge if valuable

#### PR #74: Implement automated deployment infrastructure
**Base**: main  
**Status**: Unknown (marked as WIP)  
**Action**:
1. Contact PR author to check if ready
2. If ready, rebase and review
3. If not ready, leave open but add "work-in-progress" label

---

## Conflict Resolution Cheat Sheet

### Import Statement Conflicts

**Scenario**: File has both old and new import paths

**Resolution**:
```python
# Keep this:
from panelin_mcp_server.handlers.pricing import handle_price_check

# Remove this:
from mcp.handlers.pricing import handle_price_check
```

### Path Reference Conflicts

**Scenario**: Documentation or configuration files reference old paths

**Resolution**:
```markdown
<!-- Keep this -->
See `panelin_mcp_server/server.py` for implementation

<!-- Remove this -->
See `mcp/server.py` for implementation
```

### Contract Schema Conflicts

**Scenario**: Multiple PRs modify the same contract file

**Resolution Strategy**:
1. Accept the version from PR #54 as baseline
2. Manually merge additional improvements from other PRs
3. Validate JSON schema after merge
4. Run contract tests

---

## Risk Mitigation

### Before Each Merge

1. **Create Recovery Point**:
```bash
git checkout main
git tag backup-before-pr-XX
git push origin backup-before-pr-XX
```

2. **Test Locally**:
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest

# Manual smoke test
python -c "from panelin_mcp_server.server import app"
```

### After Each Merge

1. **Verify Main**:
```bash
git checkout main
git pull origin main
git status
```

2. **Update Documentation**:
- Update REPOSITORY_CLEANUP_ANALYSIS.md progress
- Update this file's checklist

3. **Notify Stakeholders**:
- Comment on merged PR
- Update any dependent PRs

---

## Communication Templates

### For Closing Duplicate PRs

```markdown
Thank you for this PR! However, we're consolidating this work into PR #[number] which addresses the same issue. 

To avoid duplicate effort and merge conflicts, we're closing this PR. If you have additional changes beyond what's in PR #[number], please feel free to add them there or create a new PR after that one merges.

Related: [link to consolidation PR]
```

### For Closing Superseded PRs

```markdown
This PR has been superseded by our repository cleanup effort in PR #77. The work here is being addressed through a more comprehensive merge strategy.

For status updates, please follow PR #77: [link]

Thank you for your contribution!
```

---

## Success Metrics

Track progress using this checklist:

### Phase 1: Foundation
- [ ] PR #49 rebased and conflicts resolved
- [ ] PR #49 tests passing
- [ ] PR #49 merged to main
- [ ] PR #54 rebased and conflicts resolved  
- [ ] PR #54 tests passing
- [ ] PR #54 merged to main

### Phase 2: Cleanup
- [ ] PR #37 closed
- [ ] PR #44 closed
- [ ] PR #76 closed
- [ ] PR #73 closed (optional)

### Phase 3: Dependent PRs
- [ ] PR #58 evaluated and resolved
- [ ] PR #68 evaluated and resolved
- [ ] PR #70 evaluated and resolved
- [ ] PR #71 evaluated and resolved
- [ ] PR #75 evaluated and resolved

### Phase 4: Infrastructure
- [ ] PR #69 evaluated and resolved
- [ ] PR #74 evaluated and resolved

### Final State
- [ ] Open PR count reduced from 14 to < 5
- [ ] No duplicate PRs remain
- [ ] Main branch has module shadowing fix
- [ ] Main branch has v1 contracts
- [ ] All tests passing on main
- [ ] Documentation updated

---

## Rollback Procedures

If something goes wrong:

### Rollback a Merge

```bash
# Find the merge commit
git log --oneline -10

# Revert the merge (creates new commit)
git revert -m 1 <merge-commit-sha>

# Push revert
git push origin main
```

### Restore from Backup Tag

```bash
# List backup tags
git tag | grep backup

# Reset main to backup (DANGEROUS - only if necessary)
git checkout main
git reset --hard backup-before-pr-XX
git push --force origin main  # Requires force-push permissions
```

---

## Timeline

**Estimated Duration**: 1-2 days

- **Phase 1**: 4-6 hours (includes testing)
- **Phase 2**: 30 minutes
- **Phase 3**: 2-4 hours
- **Phase 4**: 2-4 hours

**Buffer**: Add 50% for unexpected conflicts and testing issues

---

## Notes

- This plan assumes access to force-push and close PRs
- Some operations require maintainer permissions
- Testing time may vary based on test suite size
- Communication with PR authors is recommended
- Consider pairing on complex conflict resolution

---

## Approval Required

Before proceeding:

- [ ] Plan reviewed by repository maintainer
- [ ] Timing coordinated with team
- [ ] Backup strategy confirmed
- [ ] Rollback procedure understood
- [ ] Communication plan approved

**Approved by**: _________________  
**Date**: _________________
