#!/bin/bash
# ==============================================================================
# GPT-PANELIN-V3.2 Pre-Deployment Checklist Script
# ==============================================================================
# Automated checks before deployment to ensure system is ready

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Check status
CHECKS_FAILED=0

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Function to run a check
run_check() {
    local check_name="$1"
    shift
    local check_command="$@"
    
    log_info "Checking: $check_name"
    
    if eval "$check_command" > /dev/null 2>&1; then
        log_success "$check_name: PASSED"
        return 0
    else
        log_error "$check_name: FAILED"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
}

# Check if tests pass
check_tests() {
    log_info "Running tests"
    
    cd "$PROJECT_ROOT"
    
    if command -v python3 >/dev/null 2>&1 && command -v pytest >/dev/null 2>&1; then
        if python3 -m pytest test_mcp_handlers_v1.py -v; then
            log_success "All tests passed"
            return 0
        else
            log_error "Some tests failed"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            return 1
        fi
    else
        log_warning "pytest not available, skipping tests"
        return 0
    fi
}

# Check knowledge base validity
check_knowledge_base() {
    log_info "Validating knowledge base"
    
    if [ -f "${SCRIPT_DIR}/validate_knowledge_base.py" ]; then
        if python3 "${SCRIPT_DIR}/validate_knowledge_base.py"; then
            log_success "Knowledge base is valid"
            return 0
        else
            log_error "Knowledge base validation failed"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            return 1
        fi
    else
        log_warning "Knowledge base validation script not found"
        return 0
    fi
}

# Check environment variables
check_environment_variables() {
    log_info "Checking environment variables"
    
    local required_vars=()
    local missing_vars=()
    
    # Check if .env file exists
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        log_success ".env file exists"
        
        # Check for critical variables (adjust as needed)
        if grep -q "OPENAI_API_KEY" "${PROJECT_ROOT}/.env"; then
            log_success "OPENAI_API_KEY is set in .env"
        else
            log_warning "OPENAI_API_KEY not found in .env"
        fi
    else
        log_warning ".env file not found (may use system environment)"
    fi
    
    return 0
}

# Check dependencies are up to date
check_dependencies() {
    log_info "Checking dependencies"
    
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        log_success "requirements.txt exists"
    else
        log_error "requirements.txt not found"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
    
    if [ -f "${PROJECT_ROOT}/mcp/requirements.txt" ]; then
        log_success "mcp/requirements.txt exists"
    else
        log_error "mcp/requirements.txt not found"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
    
    return 0
}

# Check Docker configuration
check_docker_config() {
    log_info "Checking Docker configuration"
    
    if [ -f "${PROJECT_ROOT}/Dockerfile" ]; then
        log_success "Dockerfile exists"
    else
        log_error "Dockerfile not found"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
    
    if [ -f "${PROJECT_ROOT}/docker-compose.yml" ]; then
        log_success "docker-compose.yml exists"
        
        # Validate docker-compose file syntax
        if command -v docker-compose >/dev/null 2>&1; then
            if docker-compose config > /dev/null 2>&1; then
                log_success "docker-compose.yml is valid"
            else
                log_error "docker-compose.yml has syntax errors"
                CHECKS_FAILED=$((CHECKS_FAILED + 1))
                return 1
            fi
        fi
    else
        log_error "docker-compose.yml not found"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
    
    return 0
}

# Check documentation is current
check_documentation() {
    log_info "Checking documentation"
    
    local doc_files=("README.md" "DEPLOYMENT.md")
    
    for doc in "${doc_files[@]}"; do
        if [ -f "${PROJECT_ROOT}/${doc}" ]; then
            log_success "$doc exists"
        else
            log_warning "$doc not found"
        fi
    done
    
    return 0
}

# Check for pending critical PRs
check_pending_prs() {
    log_info "Checking for pending critical PRs"
    
    # This is a placeholder - in a real scenario, you would use GitHub API
    # to check for open PRs with "critical" or "blocker" labels
    
    log_info "Manual check required: Review open PRs on GitHub"
    return 0
}

# Check code quality (linting)
check_code_quality() {
    log_info "Checking code quality"
    
    cd "$PROJECT_ROOT"
    
    # Check if flake8 is available
    if command -v flake8 >/dev/null 2>&1; then
        log_info "Running flake8..."
        if flake8 mcp/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
            log_success "No critical flake8 errors"
        else
            log_warning "Flake8 found some issues (not blocking)"
        fi
    else
        log_info "flake8 not available, skipping"
    fi
    
    return 0
}

# Check Git status
check_git_status() {
    log_info "Checking Git status"
    
    cd "$PROJECT_ROOT"
    
    if command -v git >/dev/null 2>&1; then
        # Check if there are uncommitted changes
        if git diff --quiet && git diff --cached --quiet; then
            log_success "No uncommitted changes"
        else
            log_warning "There are uncommitted changes"
        fi
        
        # Check current branch
        local current_branch=$(git branch --show-current)
        log_info "Current branch: $current_branch"
    else
        log_info "Git not available"
    fi
    
    return 0
}

# Main function
main() {
    log_info "=" * 70
    log_info "GPT-PANELIN-V3.2 Pre-Deployment Checklist"
    log_info "=" * 70
    log_info "Timestamp: $(date)"
    echo ""
    
    # Run all checks
    check_git_status
    echo ""
    
    check_dependencies
    echo ""
    
    check_environment_variables
    echo ""
    
    check_docker_config
    echo ""
    
    check_tests
    echo ""
    
    check_knowledge_base
    echo ""
    
    check_code_quality
    echo ""
    
    check_documentation
    echo ""
    
    check_pending_prs
    echo ""
    
    # Summary
    log_info "=" * 70
    log_info "Pre-Deployment Checklist Summary"
    log_info "=" * 70
    
    if [ $CHECKS_FAILED -eq 0 ]; then
        log_success "All checks passed - ready for deployment"
        exit 0
    else
        log_error "$CHECKS_FAILED check(s) failed"
        log_error "Please fix the issues before deploying"
        exit 1
    fi
}

# Run main function
main
