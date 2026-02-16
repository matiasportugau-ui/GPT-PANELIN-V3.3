#!/bin/bash
# ==============================================================================
# GPT-PANELIN-V3.2 Health Check Script
# ==============================================================================
# Usage: ./scripts/health_check.sh [staging|production]

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

# Default values
ENVIRONMENT="${1:-production}"
MCP_SERVER_URL="${MCP_SERVER_URL:-http://localhost:8000}"
TIMEOUT=10
MAX_RETRIES=3

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

# Exit status
HEALTH_CHECK_FAILED=0

# Function to check if URL is accessible
check_url() {
    local url="$1"
    local description="$2"
    
    log_info "Checking: $description"
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -f -s -m "$TIMEOUT" "$url" > /dev/null 2>&1; then
            log_success "$description is accessible"
            return 0
        else
            if [ $i -lt $MAX_RETRIES ]; then
                log_warning "Attempt $i failed, retrying..."
                sleep 2
            fi
        fi
    done
    
    log_error "$description is not accessible after $MAX_RETRIES attempts"
    HEALTH_CHECK_FAILED=1
    return 1
}

# Function to check MCP server
check_mcp_server() {
    log_info "Checking MCP server status"
    
    # Check if server process is running (Docker context)
    if command -v docker >/dev/null 2>&1; then
        if docker-compose ps | grep -q "panelin-bot.*Up"; then
            log_success "MCP server container is running"
        else
            log_error "MCP server container is not running"
            HEALTH_CHECK_FAILED=1
            return 1
        fi
    fi
    
    # Check if server file exists (local context)
    if [ -f "${PROJECT_ROOT}/mcp/server.py" ]; then
        log_success "MCP server file exists"
    else
        log_error "MCP server file not found"
        HEALTH_CHECK_FAILED=1
        return 1
    fi
    
    return 0
}

# Function to check knowledge base files
check_knowledge_base() {
    log_info "Checking knowledge base files"
    
    local kb_files=(
        "bromyros_pricing_master.json"
        "bromyros_pricing_gpt_optimized.json"
        "BMC_Base_Conocimiento_GPT-2.json"
        "bom_rules.json"
        "accessories_catalog.json"
        "shopify_catalog_v1.json"
    )
    
    local missing_files=0
    
    for file in "${kb_files[@]}"; do
        if [ -f "${PROJECT_ROOT}/${file}" ]; then
            log_success "$file exists"
        else
            log_error "$file is missing"
            missing_files=$((missing_files + 1))
            HEALTH_CHECK_FAILED=1
        fi
    done
    
    if [ $missing_files -eq 0 ]; then
        return 0
    else
        log_error "$missing_files knowledge base file(s) missing"
        return 1
    fi
}

# Function to check API endpoints
check_api_endpoints() {
    log_info "Checking API endpoints"
    
    # If MCP_SERVER_URL is accessible, try to check health endpoint
    if command -v curl >/dev/null 2>&1; then
        # Try health endpoint if it exists
        local health_endpoint="${MCP_SERVER_URL}/health"
        if curl -f -s -m "$TIMEOUT" "$health_endpoint" > /dev/null 2>&1; then
            log_success "Health endpoint is responding"
        else
            log_warning "Health endpoint not accessible (may not be implemented)"
        fi
        
        # Try metrics endpoint if it exists
        local metrics_endpoint="${MCP_SERVER_URL}/metrics"
        if curl -f -s -m "$TIMEOUT" "$metrics_endpoint" > /dev/null 2>&1; then
            log_success "Metrics endpoint is responding"
        else
            log_warning "Metrics endpoint not accessible (may not be implemented)"
        fi
    else
        log_warning "curl not available, skipping endpoint checks"
    fi
    
    return 0
}

# Function to test quotation calculator
check_quotation_calculator() {
    log_info "Checking quotation calculator"
    
    if [ -f "${PROJECT_ROOT}/quotation_calculator_v3.py" ]; then
        log_success "Quotation calculator file exists"
        
        # Try to import it (basic validation)
        if command -v python3 >/dev/null 2>&1; then
            if python3 -c "import sys; sys.path.insert(0, '${PROJECT_ROOT}'); import quotation_calculator_v3" 2>/dev/null; then
                log_success "Quotation calculator can be imported"
            else
                log_warning "Quotation calculator import failed (may need dependencies)"
            fi
        fi
    else
        log_warning "Quotation calculator file not found (optional)"
    fi
    
    return 0
}

# Function to check Docker resources
check_docker_resources() {
    log_info "Checking Docker resources"
    
    if ! command -v docker >/dev/null 2>&1; then
        log_warning "Docker not available, skipping resource checks"
        return 0
    fi
    
    # Check Docker daemon
    if docker info > /dev/null 2>&1; then
        log_success "Docker daemon is running"
    else
        log_error "Docker daemon is not accessible"
        HEALTH_CHECK_FAILED=1
        return 1
    fi
    
    # Check running containers
    local container_count=$(docker-compose ps -q 2>/dev/null | wc -l)
    if [ "$container_count" -gt 0 ]; then
        log_success "$container_count container(s) running"
    else
        log_warning "No containers are currently running"
    fi
    
    return 0
}

# Function to check disk space
check_disk_space() {
    log_info "Checking disk space"
    
    local available_space=$(df -h "${PROJECT_ROOT}" | awk 'NR==2 {print $4}')
    local usage_percent=$(df -h "${PROJECT_ROOT}" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    log_info "Available space: $available_space (${usage_percent}% used)"
    
    if [ "$usage_percent" -gt 90 ]; then
        log_error "Disk usage is critical (${usage_percent}%)"
        HEALTH_CHECK_FAILED=1
    elif [ "$usage_percent" -gt 80 ]; then
        log_warning "Disk usage is high (${usage_percent}%)"
    else
        log_success "Disk space is adequate"
    fi
    
    return 0
}

# Main function
main() {
    log_info "=== GPT-PANELIN-V3.2 Health Check ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Timestamp: $(date)"
    echo ""
    
    # Run all checks
    check_mcp_server
    echo ""
    
    check_knowledge_base
    echo ""
    
    check_api_endpoints
    echo ""
    
    check_quotation_calculator
    echo ""
    
    check_docker_resources
    echo ""
    
    check_disk_space
    echo ""
    
    # Summary
    log_info "=== Health Check Summary ==="
    if [ $HEALTH_CHECK_FAILED -eq 0 ]; then
        log_success "All critical checks passed"
        exit 0
    else
        log_error "Some checks failed"
        exit 1
    fi
}

# Run main function
main
