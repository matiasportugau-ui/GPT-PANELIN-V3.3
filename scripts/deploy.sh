#!/bin/bash
# ==============================================================================
# GPT-PANELIN-V3.2 Deployment Script
# ==============================================================================
# Usage: ./scripts/deploy.sh [staging|production]

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

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get docker-compose command
get_docker_compose_cmd() {
    # Try modern Docker Compose v2 first (docker compose)
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    # Fall back to legacy docker-compose v1
    elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    else
        echo ""
    fi
}

# Function to load environment file
load_env_file() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        log_info "Loading environment from $env_file"
        export $(grep -v '^#' "$env_file" | xargs)
        return 0
    else
        log_error "Environment file not found: $env_file"
        return 1
    fi
}

# Function to build Docker image
build_docker_image() {
    local tag="$1"
    log_info "Building Docker image with tag: $tag"
    
    cd "$PROJECT_ROOT"
    
    if docker build -t "gpt-panelin:${tag}" .; then
        log_success "Docker image built successfully"
        return 0
    else
        log_error "Docker build failed"
        return 1
    fi
}

# Function to push Docker image
push_docker_image() {
    local tag="$1"
    
    if [ -z "${DOCKER_REGISTRY:-}" ]; then
        log_warning "DOCKER_REGISTRY not set, skipping push"
        return 0
    fi
    
    log_info "Pushing Docker image to registry"
    
    local full_tag="${DOCKER_REGISTRY}/gpt-panelin:${tag}"
    docker tag "gpt-panelin:${tag}" "$full_tag"
    
    if docker push "$full_tag"; then
        log_success "Docker image pushed successfully"
        return 0
    else
        log_error "Docker push failed"
        return 1
    fi
}

# Function to deploy with docker-compose
deploy_docker_compose() {
    log_info "Deploying with docker-compose"
    
    cd "$PROJECT_ROOT"
    
    local compose_cmd=$(get_docker_compose_cmd)
    
    if [ -z "$compose_cmd" ]; then
        log_error "Docker Compose is not available"
        return 1
    fi
    
    # Use word splitting intentionally - compose_cmd contains either "docker compose" or "docker-compose"
    # Quoting would break "docker compose" by treating it as a single command name
    # shellcheck disable=SC2086
    if $compose_cmd down; then
        log_info "Stopped existing containers"
    fi
    
    # Use word splitting intentionally - compose_cmd contains either "docker compose" or "docker-compose"
    # shellcheck disable=SC2086
    if $compose_cmd up -d --build; then
        log_success "Deployment completed successfully"
        return 0
    else
        log_error "Deployment failed"
        return 1
    fi
}

# Function to run health checks
run_health_checks() {
    log_info "Running health checks"
    
    if [ -f "${SCRIPT_DIR}/health_check.sh" ]; then
        if bash "${SCRIPT_DIR}/health_check.sh" "$ENVIRONMENT"; then
            log_success "Health checks passed"
            return 0
        else
            log_error "Health checks failed"
            return 1
        fi
    else
        log_warning "Health check script not found, skipping"
        return 0
    fi
}

# Function to rollback deployment
rollback_deployment() {
    log_warning "Rolling back deployment"
    
    cd "$PROJECT_ROOT"
    
    local compose_cmd=$(get_docker_compose_cmd)
    
    if [ -n "$compose_cmd" ]; then
        # Stop current containers
        # Use word splitting intentionally - compose_cmd contains either "docker compose" or "docker-compose"
        # shellcheck disable=SC2086
        $compose_cmd down
    fi
    
    # Restore previous version (implement your rollback strategy here)
    log_info "Restoring previous version"
    
    # For example, you could:
    # - Pull and run previous Docker image tag
    # - Restore from backup
    # - Switch to previous git commit
    
    log_warning "Rollback completed - manual verification required"
}

# Main deployment function
main() {
    log_info "=== GPT-PANELIN-V3.2 Deployment ==="
    
    # Check arguments
    if [ $# -lt 1 ]; then
        log_error "Usage: $0 [staging|production]"
        exit 1
    fi
    
    ENVIRONMENT="$1"
    
    # Validate environment
    if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
        log_error "Invalid environment: $ENVIRONMENT (must be 'staging' or 'production')"
        exit 1
    fi
    
    log_info "Target environment: $ENVIRONMENT"
    
    # Check required commands
    if ! command_exists docker; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check for Docker Compose (v1 or v2)
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        log_error "Docker Compose is not installed"
        log_info "Please install Docker Compose v2 (docker compose) or v1 (docker-compose)"
        exit 1
    fi
    log_info "Using Docker Compose: $compose_cmd"
    
    # Load environment file
    ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
    if [ ! -f "$ENV_FILE" ]; then
        ENV_FILE="${PROJECT_ROOT}/.env"
    fi
    
    if [ -f "$ENV_FILE" ]; then
        load_env_file "$ENV_FILE" || exit 1
    else
        log_warning "No environment file found, using system environment"
    fi
    
    # Generate deployment tag
    DEPLOY_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
    log_info "Deployment tag: $DEPLOY_TAG"
    
    # Build Docker image
    if ! build_docker_image "$DEPLOY_TAG"; then
        log_error "Build failed"
        exit 1
    fi
    
    # Tag as latest for this environment
    docker tag "gpt-panelin:${DEPLOY_TAG}" "gpt-panelin:${ENVIRONMENT}-latest"
    
    # Push to registry (if configured)
    push_docker_image "$DEPLOY_TAG" || log_warning "Push to registry failed or skipped"
    
    # Deploy
    if ! deploy_docker_compose; then
        log_error "Deployment failed, initiating rollback"
        rollback_deployment
        exit 1
    fi
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 10
    
    # Run health checks
    if ! run_health_checks; then
        log_error "Health checks failed after deployment"
        read -p "Do you want to rollback? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback_deployment
            exit 1
        else
            log_warning "Continuing despite health check failure"
        fi
    fi
    
    # Success
    log_success "=== Deployment Completed Successfully ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Tag: $DEPLOY_TAG"
    log_info "Timestamp: $(date)"
    
    # Show running containers
    log_info "Running containers:"
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -n "$compose_cmd" ]; then
        # Use word splitting intentionally - compose_cmd contains either "docker compose" or "docker-compose"
        # shellcheck disable=SC2086
        $compose_cmd ps
    fi
}

# Run main function
main "$@"
