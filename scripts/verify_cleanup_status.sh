#!/bin/bash
# PR Cleanup Verification Script
# Purpose: Verify current PR status and code health
# Generated: 2026-02-14

set -e

echo "=================================================="
echo "  PR Cleanup Status Verification"
echo "=================================================="
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI not installed - skipping PR list check"
    echo "   Install from: https://cli.github.com/"
    echo ""
else
    echo "📋 Current Open PRs:"
    echo "-------------------------------------------"
    gh pr list --limit 50 || echo "⚠️  Could not fetch PR list"
    echo ""
fi

echo "🔍 Code Health Check:"
echo "-------------------------------------------"

# Check Python compilation
echo "Testing Python file compilation..."
python_errors=0

# Check panelin_mcp_integration files
if python3 -m py_compile panelin_mcp_integration/panelin_mcp_server.py 2>&1; then
    echo "✅ panelin_mcp_integration/panelin_mcp_server.py compiles"
else
    echo "❌ panelin_mcp_integration/panelin_mcp_server.py has errors"
    python_errors=$((python_errors + 1))
fi

if python3 -m py_compile panelin_mcp_integration/panelin_openai_integration.py 2>&1; then
    echo "✅ panelin_mcp_integration/panelin_openai_integration.py compiles"
else
    echo "❌ panelin_mcp_integration/panelin_openai_integration.py has errors"
    python_errors=$((python_errors + 1))
fi

# Check mcp/handlers files
if [ -d "mcp/handlers" ]; then
    for file in mcp/handlers/*.py; do
        if [ -f "$file" ]; then
            if python3 -m py_compile "$file" 2>&1 > /dev/null; then
                echo "✅ $file compiles"
            else
                echo "❌ $file has errors"
                python_errors=$((python_errors + 1))
            fi
        fi
    done
fi

echo ""
echo "=================================================="
echo "  Summary"
echo "=================================================="

if [ $python_errors -eq 0 ]; then
    echo "✅ All Python files compile without errors"
else
    echo "❌ $python_errors Python file(s) have compilation errors"
fi

echo ""
echo "Expected state after cleanup:"
echo "  • 15 PRs closed"
echo "  • 4 PRs remaining open (#82, #74, #71, #68)"
echo "  • All Python files compile correctly"
echo ""
echo "For cleanup execution, run:"
echo "  ./scripts/close_stale_prs.sh"
echo ""
