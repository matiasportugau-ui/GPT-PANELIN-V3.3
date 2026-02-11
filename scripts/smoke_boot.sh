#!/usr/bin/env bash
#
# smoke_boot.sh - Local smoke test for BOOT process
#
# This script runs basic smoke tests on the BOOT architecture locally.
# It's useful for manual testing before committing changes.
#
# Usage:
#   ./scripts/smoke_boot.sh
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $*"
}

# Test assertion
assert_file_exists() {
    local file="$1"
    local description="${2:-File check}"
    
    if [ -f "$file" ]; then
        log_success "$description: $file exists"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "$description: $file NOT FOUND"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_dir_exists() {
    local dir="$1"
    local description="${2:-Directory check}"
    
    if [ -d "$dir" ]; then
        log_success "$description: $dir exists"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "$description: $dir NOT FOUND"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_command_success() {
    local description="$1"
    shift
    
    if "$@" &>/dev/null; then
        log_success "$description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "$description FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test artifacts..."
    rm -rf .venv .boot-log .boot-log.old .boot-ready .boot-lock knowledge knowledge_index.json
    log_info "Cleanup complete"
}

# Test 1: Check required scripts exist
test_scripts_exist() {
    log_test "Test 1: Checking required scripts exist"
    
    assert_file_exists "boot.sh" "Boot orchestrator"
    assert_file_exists "boot_preload.py" "Preload script"
    assert_file_exists "index_validator.py" "Validator script"
    assert_file_exists "requirements.txt" "Requirements file"
}

# Test 2: Create sample knowledge source
test_create_sample_knowledge() {
    log_test "Test 2: Creating sample knowledge source"
    
    mkdir -p knowledge_src
    echo "Sample knowledge content" > knowledge_src/sample.txt
    echo "# Markdown sample" > knowledge_src/sample.md
    mkdir -p knowledge_src/subdir
    echo "Nested file" > knowledge_src/subdir/nested.txt
    
    assert_file_exists "knowledge_src/sample.txt" "Sample file"
    assert_file_exists "knowledge_src/subdir/nested.txt" "Nested file"
    
    log_success "Sample knowledge source created"
}

# Test 3: Run BOOT process
test_run_boot() {
    log_test "Test 3: Running BOOT process"
    
    export GENERATE_EMBEDDINGS=0
    
    if ./boot.sh; then
        log_success "BOOT process completed successfully"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "BOOT process FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 4: Verify BOOT artifacts
test_verify_artifacts() {
    log_test "Test 4: Verifying BOOT artifacts"
    
    assert_file_exists ".boot-log" "Boot log"
    assert_file_exists ".boot-ready" "Ready marker"
    assert_dir_exists ".venv" "Virtual environment"
    assert_file_exists "knowledge_index.json" "Knowledge index"
    assert_dir_exists "knowledge" "Knowledge directory"
}

# Test 5: Verify knowledge files copied
test_verify_knowledge_files() {
    log_test "Test 5: Verifying knowledge files copied"
    
    assert_file_exists "knowledge/sample.txt" "Copied sample.txt"
    assert_file_exists "knowledge/sample.md" "Copied sample.md"
    assert_file_exists "knowledge/subdir/nested.txt" "Copied nested file"
}

# Test 6: Validate index
test_validate_index() {
    log_test "Test 6: Validating index"
    
    # Activate venv and run validator
    # shellcheck disable=SC1091
    source .venv/bin/activate
    
    if python index_validator.py; then
        log_success "Index validation passed"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "Index validation FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 7: Test idempotency
test_idempotency() {
    log_test "Test 7: Testing idempotency (second run)"
    
    export GENERATE_EMBEDDINGS=0
    
    if ./boot.sh; then
        log_success "Second BOOT run completed (idempotency verified)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "Second BOOT run FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 8: Check log contents
test_check_logs() {
    log_test "Test 8: Checking log contents"
    
    if [ -f ".boot-log" ]; then
        local log_lines
        log_lines=$(wc -l < .boot-log)
        log_info "Boot log contains $log_lines lines"
        
        # Check for expected log entries
        if grep -q "BOOT process started" .boot-log && \
           grep -q "BOOT process completed successfully" .boot-log; then
            log_success "Log contains expected entries"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            log_error "Log missing expected entries"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        log_error "Boot log not found"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 9: Verify no secrets in logs
test_no_secrets_in_logs() {
    log_test "Test 9: Checking for secrets in logs"
    
    if grep -iE "(api[_-]?key|secret|password|token)" .boot-log; then
        log_error "Potential secrets found in log!"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    else
        log_success "No secrets found in logs"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "================================"
    echo "   Smoke Test Results"
    echo "================================"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
    echo "================================"
    
    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        return 1
    fi
}

# Main execution
main() {
    log_info "=== BOOT Smoke Test Suite ==="
    log_info "Starting smoke tests..."
    echo ""
    
    # Cleanup first
    cleanup
    
    # Run tests
    test_scripts_exist
    test_create_sample_knowledge
    test_run_boot
    test_verify_artifacts
    test_verify_knowledge_files
    test_validate_index
    test_idempotency
    test_check_logs
    test_no_secrets_in_logs
    
    # Print summary and return result
    echo ""
    print_summary
}

# Run main
main "$@"
