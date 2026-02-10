#!/usr/bin/env bash
################################################################################
# boot.sh - Panelin GPT BOOT Orchestrator
# 
# Purpose: Idempotent initialization script for Panelin GPT system
# - Validates environment and dependencies
# - Prepares knowledge base and indexes
# - Signals readiness with .boot-ready flag
# - Comprehensive logging to .boot-log
#
# Usage:
#   ./boot.sh [--force] [--no-embeddings] [--verbose]
#
# Environment Variables:
#   PANELIN_ROOT           - Repository root (default: current directory)
#   GENERATE_EMBEDDINGS    - Generate vector embeddings (default: 0)
#   PANELIN_API_KEY        - Optional API key for embeddings
#   PYTHON_BIN             - Python binary (default: python3)
#   BOOT_LOG_MAX_SIZE_MB   - Max log size before rotation (default: 10)
#
# Exit Codes:
#   0 - Success (boot completed)
#   1 - Environment validation failed
#   2 - Dependency check failed
#   3 - Knowledge ingestion failed
#   4 - Permission/write error
################################################################################

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PANELIN_ROOT="${PANELIN_ROOT:-$SCRIPT_DIR}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BOOT_LOG="${PANELIN_ROOT}/.boot-log"
BOOT_READY="${PANELIN_ROOT}/.boot-ready"
BOOT_LOG_MAX_SIZE_MB="${BOOT_LOG_MAX_SIZE_MB:-10}"
GENERATE_EMBEDDINGS="${GENERATE_EMBEDDINGS:-0}"
FORCE_BOOT=0
VERBOSE=0

# --- Parse Arguments ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --force)
      FORCE_BOOT=1
      shift
      ;;
    --no-embeddings)
      GENERATE_EMBEDDINGS=0
      shift
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--force] [--no-embeddings] [--verbose]"
      echo ""
      echo "Options:"
      echo "  --force          Force re-run BOOT even if already completed"
      echo "  --no-embeddings  Disable embedding generation"
      echo "  --verbose        Enable verbose output"
      echo "  -h, --help       Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--force] [--no-embeddings] [--verbose]" >&2
      exit 1
      ;;
  esac
done

# --- Logging Functions ---
log() {
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "[$timestamp] $*" | tee -a "$BOOT_LOG"
}

log_info() {
  log "INFO: $*"
}

log_warn() {
  log "WARN: $*"
}

log_error() {
  log "ERROR: $*"
}

log_step() {
  log "==> $*"
  if [[ $VERBOSE -eq 1 ]]; then
    echo "==> $*" >&2
  fi
}

# --- Log Rotation ---
rotate_log_if_needed() {
  if [[ -f "$BOOT_LOG" ]]; then
    local size_mb
    size_mb=$(du -m "$BOOT_LOG" | cut -f1)
    if [[ $size_mb -ge $BOOT_LOG_MAX_SIZE_MB ]]; then
      local backup="${BOOT_LOG}.$(date +%Y%m%d-%H%M%S)"
      mv "$BOOT_LOG" "$backup"
      log_info "Rotated log to $backup (size: ${size_mb}MB)"
      # Keep only last 5 rotated logs
      ls -t "${BOOT_LOG}".* 2>/dev/null | tail -n +6 | xargs -r rm -f
    fi
  fi
}

# --- Idempotency Check ---
check_if_boot_needed() {
  if [[ -f "$BOOT_READY" && $FORCE_BOOT -eq 0 ]]; then
    local boot_time
    boot_time=$(stat -c %Y "$BOOT_READY" 2>/dev/null || stat -f %m "$BOOT_READY" 2>/dev/null || echo "0")
    log_info "System already booted at $(date -d @"$boot_time" 2>/dev/null || date -r "$boot_time" 2>/dev/null || echo 'unknown time')"
    log_info "Use --force to re-run BOOT process"
    exit 0
  fi
}

# --- Environment Validation ---
validate_environment() {
  log_step "Validating environment"
  
  # Check writable directories
  log_info "Checking write permissions..."
  if [[ ! -w "$PANELIN_ROOT" ]]; then
    log_error "PANELIN_ROOT is not writable: $PANELIN_ROOT"
    exit 4
  fi
  log_info "Write permissions OK"
  
  # Check Python availability
  log_info "Checking Python..."
  if ! command -v "$PYTHON_BIN" &> /dev/null; then
    log_error "Python not found: $PYTHON_BIN"
    log_error "Set PYTHON_BIN environment variable or install Python 3.8+"
    exit 2
  fi
  
  local python_version
  python_version=$("$PYTHON_BIN" --version 2>&1 | head -1 | grep -oP '\d+\.\d+' || echo "unknown")
  log_info "Python version: $python_version"
  
  # Check required files
  log_info "Checking required files..."
  local required_files=(
    "requirements.txt"
    "validate_gpt_files.py"
    "package_gpt_files.py"
  )
  
  for file in "${required_files[@]}"; do
    if [[ ! -f "$PANELIN_ROOT/$file" ]]; then
      log_error "Required file missing: $file"
      exit 1
    fi
  done
  log_info "Required files OK"
  
  # Warn if embeddings requested but no API key
  if [[ $GENERATE_EMBEDDINGS -eq 1 && -z "${PANELIN_API_KEY:-}" ]]; then
    log_warn "GENERATE_EMBEDDINGS=1 but PANELIN_API_KEY not set"
    log_warn "Embeddings will be skipped or may fail"
  fi
  
  log_info "Environment validation passed"
}

# --- Dependency Installation ---
install_dependencies() {
  log_step "Installing/verifying dependencies"
  
  # Check if virtualenv exists, create if not
  if [[ ! -d "$PANELIN_ROOT/venv" ]]; then
    log_info "Creating virtual environment"
    "$PYTHON_BIN" -m venv "$PANELIN_ROOT/venv"
  fi
  
  # Activate virtualenv
  # shellcheck disable=SC1091
  source "$PANELIN_ROOT/venv/bin/activate"
  
  # Install/upgrade pip
  pip install --quiet --upgrade pip
  
  # Install requirements
  if [[ -f "$PANELIN_ROOT/requirements.txt" ]]; then
    log_info "Installing requirements from requirements.txt"
    pip install --quiet -r "$PANELIN_ROOT/requirements.txt"
  fi
  
  # Install evolucionador requirements if present
  if [[ -f "$PANELIN_ROOT/.evolucionador/requirements.txt" ]]; then
    log_info "Installing evolucionador requirements"
    pip install --quiet -r "$PANELIN_ROOT/.evolucionador/requirements.txt"
  fi
  
  log_info "Dependencies installed successfully"
}

# --- Knowledge Ingestion ---
run_knowledge_ingestion() {
  log_step "Running knowledge ingestion pipeline"
  
  # Activate virtualenv if not already active
  if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    # shellcheck disable=SC1091
    source "$PANELIN_ROOT/venv/bin/activate"
  fi
  
  # Run boot_preload.py
  if [[ -f "$PANELIN_ROOT/boot_preload.py" ]]; then
    log_info "Executing boot_preload.py"
    export GENERATE_EMBEDDINGS
    export PANELIN_ROOT
    
    if ! "$PYTHON_BIN" "$PANELIN_ROOT/boot_preload.py"; then
      log_error "Knowledge ingestion failed"
      exit 3
    fi
    log_info "Knowledge ingestion completed"
  else
    log_warn "boot_preload.py not found, skipping knowledge ingestion"
  fi
}

# --- File Validation ---
validate_files() {
  log_step "Validating GPT configuration files"
  
  if [[ -f "$PANELIN_ROOT/validate_gpt_files.py" ]]; then
    if ! "$PYTHON_BIN" "$PANELIN_ROOT/validate_gpt_files.py"; then
      log_error "File validation failed"
      exit 3
    fi
    log_info "File validation passed"
  else
    log_warn "validate_gpt_files.py not found, skipping validation"
  fi
}

# --- Signal Readiness ---
signal_ready() {
  log_step "Signaling system ready"
  
  local boot_info
  boot_info=$(cat <<EOF
BOOT completed successfully
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Python: $("$PYTHON_BIN" --version 2>&1)
Embeddings: $GENERATE_EMBEDDINGS
Root: $PANELIN_ROOT
EOF
)
  
  echo "$boot_info" > "$BOOT_READY"
  log_info "Created .boot-ready flag"
  log_info "BOOT process completed successfully"
}

# --- Main Execution ---
main() {
  log_info "=========================================="
  log_info "Panelin GPT BOOT Process Starting"
  log_info "=========================================="
  log_info "Root: $PANELIN_ROOT"
  log_info "Python: $PYTHON_BIN"
  log_info "Embeddings: $GENERATE_EMBEDDINGS"
  log_info "Force: $FORCE_BOOT"
  
  # Rotate log if needed
  rotate_log_if_needed
  
  # Check if boot is needed
  check_if_boot_needed
  
  # Remove old boot-ready flag if forcing
  if [[ $FORCE_BOOT -eq 1 && -f "$BOOT_READY" ]]; then
    rm -f "$BOOT_READY"
    log_info "Removed old .boot-ready flag (forced reboot)"
  fi
  
  # Execute boot steps
  validate_environment
  install_dependencies
  validate_files
  run_knowledge_ingestion
  signal_ready
  
  log_info "=========================================="
  log_info "BOOT Complete - System Ready"
  log_info "=========================================="
  
  exit 0
}

# Run main function
main "$@"
