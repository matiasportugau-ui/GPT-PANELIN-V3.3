#!/usr/bin/env bash
#
# boot.sh - Bootstrap script for GPT-PANELIN-V3.2
# 
# This script orchestrates the BOOT (Bootstrap, Operations, Orchestration, Testing)
# process. It creates a Python virtual environment, installs dependencies,
# preloads knowledge files, and validates the system.
#
# Environment Variables:
#   GENERATE_EMBEDDINGS - Set to 1 to enable embeddings generation (requires API key)
#                        Default: 0 (disabled)
#   PYTHON_BIN         - Python binary to use (default: python3)
#   VENV_DIR           - Virtual environment directory (default: .venv)
#
# Exit Codes:
#   0 - Success
#   1 - General error
#   2 - Lock acquisition failed (concurrent run)
#   3 - Python or dependency error
#   4 - Preload or validation error
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOT_LOG="${SCRIPT_DIR}/.boot-log"
BOOT_READY="${SCRIPT_DIR}/.boot-ready"
BOOT_LOCK="${SCRIPT_DIR}/.boot-lock"
MAX_LOG_SIZE=$((5 * 1024 * 1024))  # 5MB
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
GENERATE_EMBEDDINGS="${GENERATE_EMBEDDINGS:-0}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "[${timestamp}] [${level}] ${message}" >> "${BOOT_LOG}"
    echo -e "${message}"
}

log_info() {
    log "INFO" "${BLUE}[INFO]${NC} $*"
}

log_success() {
    log "SUCCESS" "${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    log "WARN" "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    log "ERROR" "${RED}[ERROR]${NC} $*"
}

# Error handler
error_exit() {
    log_error "$1"
    release_lock
    exit "${2:-1}"
}

# Lock management
acquire_lock() {
    local max_wait=30
    local waited=0
    
    while [ -d "${BOOT_LOCK}" ]; do
        if [ $waited -ge $max_wait ]; then
            error_exit "Another BOOT process is running (lock exists). Wait or remove ${BOOT_LOCK} if stale." 2
        fi
        log_warn "Waiting for lock... ($waited/${max_wait}s)"
        sleep 1
        waited=$((waited + 1))
    done
    
    mkdir "${BOOT_LOCK}" 2>/dev/null || error_exit "Failed to acquire lock" 2
    log_info "Lock acquired"
}

release_lock() {
    if [ -d "${BOOT_LOCK}" ]; then
        rmdir "${BOOT_LOCK}" 2>/dev/null || true
        log_info "Lock released"
    fi
}

# Cleanup on exit
cleanup() {
    release_lock
}

trap cleanup EXIT INT TERM

# Log rotation
rotate_log() {
    if [ -f "${BOOT_LOG}" ]; then
        local log_size
        log_size=$(stat -f%z "${BOOT_LOG}" 2>/dev/null || stat -c%s "${BOOT_LOG}" 2>/dev/null || echo 0)
        
        if [ "$log_size" -gt "$MAX_LOG_SIZE" ]; then
            log_info "Rotating log file (size: $log_size bytes)"
            mv "${BOOT_LOG}" "${BOOT_LOG}.old"
            touch "${BOOT_LOG}"
            chmod 600 "${BOOT_LOG}"
        fi
    fi
}

# Initialize log file
init_log() {
    touch "${BOOT_LOG}"
    chmod 600 "${BOOT_LOG}"
    rotate_log
    log_info "=== BOOT process started ==="
    log_info "Working directory: ${SCRIPT_DIR}"
    log_info "Python binary: ${PYTHON_BIN}"
    log_info "Virtual environment: ${VENV_DIR}"
    log_info "Generate embeddings: ${GENERATE_EMBEDDINGS}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v "${PYTHON_BIN}" &> /dev/null; then
        error_exit "Python not found. Please install Python 3.8+ or set PYTHON_BIN environment variable." 3
    fi
    
    local python_version
    python_version=$("${PYTHON_BIN}" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    log_info "Found Python ${python_version}"
    
    # Check Python version (need 3.8+)
    local major minor
    major=$(echo "${python_version}" | cut -d. -f1)
    minor=$(echo "${python_version}" | cut -d. -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
        error_exit "Python 3.8 or higher is required. Found: ${python_version}" 3
    fi
    
    log_success "Prerequisites check passed"
}

# Setup virtual environment
setup_venv() {
    log_info "Setting up virtual environment..."
    
    if [ -d "${VENV_DIR}" ]; then
        log_info "Virtual environment already exists at ${VENV_DIR}"
    else
        log_info "Creating virtual environment at ${VENV_DIR}"
        "${PYTHON_BIN}" -m venv "${VENV_DIR}" || error_exit "Failed to create virtual environment" 3
        log_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate" || error_exit "Failed to activate virtual environment" 3
    log_info "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        log_warn "requirements.txt not found, skipping dependency installation"
        return 0
    fi
    
    # Upgrade pip
    log_info "Upgrading pip..."
    python -m pip install --upgrade pip --quiet || log_warn "Failed to upgrade pip"
    
    # Install requirements
    log_info "Installing packages from requirements.txt..."
    python -m pip install -r requirements.txt --quiet || error_exit "Failed to install dependencies" 3
    
    log_success "Dependencies installed"
}

# Run preload script
run_preload() {
    log_info "Running knowledge preload..."
    
    if [ ! -f "boot_preload.py" ]; then
        log_warn "boot_preload.py not found, skipping preload"
        return 0
    fi
    
    export GENERATE_EMBEDDINGS
    python boot_preload.py || error_exit "Preload script failed" 4
    
    log_success "Knowledge preload completed"
}

# Validate system
validate_system() {
    log_info "Validating system..."
    
    # Check if index validator exists
    if [ -f "index_validator.py" ]; then
        log_info "Running index validation..."
        python index_validator.py || error_exit "Index validation failed" 4
        log_success "Index validation passed"
    else
        log_warn "index_validator.py not found, skipping validation"
    fi
}

# Create readiness marker
create_ready_marker() {
    local timestamp
    timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "${timestamp}" > "${BOOT_READY}"
    chmod 644 "${BOOT_READY}"
    log_success "BOOT process completed successfully"
    log_info "Readiness marker created at ${BOOT_READY}"
}

# Main execution
main() {
    cd "${SCRIPT_DIR}"
    
    # Remove old ready marker
    rm -f "${BOOT_READY}"
    
    # Initialize
    init_log
    acquire_lock
    
    # Execute BOOT steps
    check_prerequisites
    setup_venv
    install_dependencies
    run_preload
    validate_system
    create_ready_marker
    
    log_info "=== BOOT process finished ==="
}

# Run main
main "$@"
