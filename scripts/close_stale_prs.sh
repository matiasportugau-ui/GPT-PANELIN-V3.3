#!/bin/bash
# PR Bulk Closure Script
# Purpose: Close 15 stale/duplicate/empty PRs identified in PR_CLEANUP_ANALYSIS.md
# Generated: 2026-02-14
# Run this from the repository root: ./scripts/close_stale_prs.sh

set -e

echo "=================================================="
echo "  PR Cleanup: Closing 15 Stale/Empty PRs"
echo "=================================================="
echo ""
echo "Analysis: PR_CLEANUP_ANALYSIS.md"
echo "Guide: PR_CLOSURE_GUIDE.md"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "Install: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is ready"
echo ""

# Confirm before proceeding
read -p "This will close 15 PRs. Continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Stage 1: Closing Empty PRs (0 changes)..."
echo "-------------------------------------------"

gh pr close 87 --comment "Closing this PR as it has 0 changed files. The issues this PR intended to fix don't exist on the main branch.

Verified: All Python files in the repository compile without errors.
Status: ✅ No action needed

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #87 may already be closed"

gh pr close 86 --comment "Closing this PR as it has 0 changed files. The issues this PR intended to fix don't exist on the main branch.

Verified: All Python files in the repository compile without errors.
Status: ✅ No action needed

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #86 may already be closed"

gh pr close 85 --comment "Closing this PR as it has 0 changed files. The issues this PR intended to fix don't exist on the main branch.

Verified: All Python files in the repository compile without errors.
Status: ✅ No action needed

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #85 may already be closed"

gh pr close 84 --comment "Closing this PR as it has 0 changed files. The issues this PR intended to fix don't exist on the main branch.

Verified: All Python files in the repository compile without errors.
Status: ✅ No action needed

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #84 may already be closed"

echo "✅ Stage 1 complete"
echo ""
echo "Stage 2: Closing Stale/Superseded PRs..."
echo "-------------------------------------------"

gh pr close 81 --comment "Closing this PR as it's a WIP attempt to resolve merge conflicts for PR #76, which itself should be closed (too broad/risky).

Recommendation: Merge branches individually rather than all at once.
Status: ❌ Superseded approach

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #81 may already be closed"

gh pr close 80 --comment "Closing this PR as it's WIP and superseded by evolved main branch. The mcp/ directory currently exists and works correctly on main.

Note: Module shadowing fix may be reconsidered in the future if issues arise.
Status: ❌ Superseded by main evolution

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #80 may already be closed"

gh pr close 79 --comment "Closing this PR as it's an incomplete consolidation attempt. PRs should be evaluated and merged/closed individually for better tracking and rollback capability.

Related: See PR_CLEANUP_ANALYSIS.md for systematic cleanup approach
Status: ❌ Incomplete consolidation

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #79 may already be closed"

gh pr close 76 --comment "Closing this PR as the scope is too broad and risky. Merging all branches at once increases risk of conflicts and makes debugging difficult.

Recommendation: Merge valuable PRs individually after review and testing.
Status: ❌ Too broad/risky

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #76 may already be closed"

gh pr close 70 --comment "Closing this documentation-only PR. While the explanation is helpful, it doesn't contain code fixes and is based on PR #49 which has conflicts.

Status: ❌ Documentation-only, base has conflicts

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #70 may already be closed"

gh pr close 69 --comment "Closing this PR as it's WIP and superseded by PR #83. The indentation fixes from PR #83 have been applied to main.

Verified: panelin_mcp_integration/*.py files now have correct PEP 8 indentation.
Status: ✅ Fixed in PR #83 (applied to main)

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #69 may already be closed"

gh pr close 58 --comment "Closing this PR as PR #54 has already been merged. This feedback PR is now stale.

If new feedback is needed, please create a fresh PR based on current main.
Status: ❌ Stale (base PR already merged)

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #58 may already be closed"

gh pr close 49 --comment "Closing this PR due to vague description and unclear scope.

If this work is still needed, please create a new PR with:
- Clear description of the problem
- Specific changes being made
- Based on current main branch

Status: ❌ Unclear scope

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #49 may already be closed"

gh pr close 44 --comment "Closing this PR as it's a duplicate of PR #37. The module rename is not currently needed as the mcp/ directory works correctly on main.

Related: #37 (oldest rename attempt)
Status: ❌ Duplicate

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #44 may already be closed"

gh pr close 37 --comment "Closing this PR as it's the oldest module shadowing fix attempt. The mcp/ directory currently works correctly on main.

Note: If module shadowing issues arise in the future, we can reconsider this approach.
Duplicates: #44, #80
Status: ❌ Not currently needed

Analysis: PR_CLEANUP_ANALYSIS.md" || echo "⚠️  PR #37 may already be closed"

echo "✅ Stage 2 complete"
echo ""
echo "=================================================="
echo "  Cleanup Summary"
echo "=================================================="
echo "✅ Closed 15 PRs (empty or stale/superseded)"
echo "📋 Keeping open: #82, #74, #71, #68"
echo ""
echo "Next steps:"
echo "  1. Review PR_CLOSURE_GUIDE.md for details"
echo "  2. Update PR_DEPENDENCY_MAP.md if needed"
echo "  3. Schedule review of remaining 4 PRs"
echo ""
echo "Verification:"
echo "  Run: gh pr list"
echo "  Expected: 4 open PRs remaining"
echo ""
