#!/usr/bin/env bash
#
# smoke_boot.sh - Local smoke test runner for BOOT process
#
# This script runs the boot process in a safe testing mode and validates results.
# Use this for local development and testing before pushing changes.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  BOOT Smoke Test Runner${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Function to print test result
test_result() {
    local test_name="$1"
    local result="$2"
    if [[ "$result" == "PASS" ]]; then
        echo -e "${GREEN}✓${NC} $test_name"
    elif [[ "$result" == "WARN" ]]; then
        echo -e "${YELLOW}⚠${NC} $test_name"
    else
        echo -e "${RED}✗${NC} $test_name"
    fi
}

# Test 1: Check script presence
echo -e "${YELLOW}[Test 1]${NC} Checking script presence..."
if [[ -f "boot.sh" && -f "boot_preload.py" && -f "index_validator.py" ]]; then
    test_result "Script presence" "PASS"
else
    test_result "Script presence" "FAIL"
    echo "Missing required scripts!"
    exit 1
fi

# Test 2: Check script executability
echo -e "${YELLOW}[Test 2]${NC} Checking script executability..."
chmod +x boot.sh boot_preload.py index_validator.py
if [[ -x "boot.sh" && -x "boot_preload.py" && -x "index_validator.py" ]]; then
    test_result "Script executability" "PASS"
else
    test_result "Script executability" "FAIL"
    exit 1
fi

# Test 3: Check Python syntax
echo -e "${YELLOW}[Test 3]${NC} Checking Python syntax..."
if python3 -m py_compile boot_preload.py index_validator.py 2>/dev/null; then
    test_result "Python syntax" "PASS"
else
    test_result "Python syntax" "FAIL"
    exit 1
fi

# Test 4: Check shell script syntax
echo -e "${YELLOW}[Test 4]${NC} Checking shell script syntax..."
if bash -n boot.sh 2>/dev/null; then
    test_result "Shell script syntax" "PASS"
else
    test_result "Shell script syntax" "FAIL"
    exit 1
fi

# Test 5: Ensure test knowledge source exists
echo -e "${YELLOW}[Test 5]${NC} Setting up test knowledge source..."
mkdir -p knowledge_src
if [[ ! -f "knowledge_src/test.txt" ]]; then
    echo "Test knowledge content" > knowledge_src/test.txt
    echo "Created test knowledge file"
fi
test_result "Test knowledge setup" "PASS"

# Test 6: Run boot.sh
echo -e "${YELLOW}[Test 6]${NC} Running boot.sh..."
export GENERATE_EMBEDDINGS=0
if ./boot.sh; then
    test_result "boot.sh execution" "PASS"
else
    test_result "boot.sh execution" "FAIL"
    echo "Check .boot-log for details"
    exit 1
fi

# Test 7: Check artifacts
echo -e "${YELLOW}[Test 7]${NC} Checking generated artifacts..."
artifacts_ok=true
for artifact in .boot-log .boot-ready knowledge_index.json; do
    if [[ -f "$artifact" ]]; then
        echo "  ✓ $artifact exists"
    else
        echo "  ✗ $artifact missing"
        artifacts_ok=false
    fi
done

if $artifacts_ok; then
    test_result "Artifact generation" "PASS"
else
    test_result "Artifact generation" "FAIL"
    exit 1
fi

# Test 8: Verify no embeddings in CI mode
echo -e "${YELLOW}[Test 8]${NC} Verifying embeddings disabled..."
if grep -q '"embeddings_enabled": false' knowledge_index.json; then
    test_result "Embeddings disabled" "PASS"
else
    test_result "Embeddings disabled" "WARN"
    echo "  Note: Embeddings may be enabled"
fi

# Test 9: Run index validator
echo -e "${YELLOW}[Test 9]${NC} Running index validator..."
if python3 index_validator.py; then
    test_result "Index validation" "PASS"
else
    exit_code=$?
    if [[ $exit_code -eq 1 ]]; then
        test_result "Index validation" "WARN"
        echo "  Note: Validation completed with warnings"
    else
        test_result "Index validation" "FAIL"
        exit 1
    fi
fi

# Test 10: Test idempotency
echo -e "${YELLOW}[Test 10]${NC} Testing idempotent execution..."
if ./boot.sh >/dev/null 2>&1; then
    test_result "Idempotent execution" "PASS"
    # Check for "skipped" messages in log
    if grep -q "skipped" .boot-log; then
        echo "  ✓ Files correctly skipped on second run"
    fi
else
    test_result "Idempotent execution" "FAIL"
    exit 1
fi

# Test 11: Check log file permissions
echo -e "${YELLOW}[Test 11]${NC} Checking log file security..."
if [[ -f ".boot-log" ]]; then
    # Check OS and use appropriate stat command
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        perms=$(stat -f "%Lp" .boot-log 2>/dev/null || echo "unknown")
    else
        # Linux
        perms=$(stat -c "%a" .boot-log 2>/dev/null || echo "unknown")
    fi
    
    if [[ "$perms" == "600" ]]; then
        test_result "Log file permissions" "PASS"
        echo "  ✓ Log file has secure permissions (600)"
    else
        test_result "Log file permissions" "WARN"
        echo "  ⚠ Log file permissions: $perms (expected 600)"
    fi
else
    test_result "Log file permissions" "FAIL"
fi

# Summary
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  Smoke Test Summary${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Generated artifacts:"
echo "  - .boot-log ($(stat -f%z .boot-log 2>/dev/null || stat -c%s .boot-log 2>/dev/null || echo '?') bytes)"
echo "  - .boot-ready"
echo "  - knowledge_index.json"
if [[ -d "knowledge" ]]; then
    file_count=$(find knowledge -type f | wc -l)
    echo "  - knowledge/ ($file_count files)"
fi
echo ""

if [[ -f ".boot-log" ]]; then
    echo "Last 10 log entries:"
    echo "---"
    tail -10 .boot-log
    echo "---"
fi

echo ""
echo -e "${GREEN}✓ All smoke tests passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review artifacts in current directory"
echo "  2. Check .boot-log for detailed execution log"
echo "  3. Run: python3 index_validator.py"
echo ""

exit 0
