# GPT-PANELIN-V3.2 Deployment Guide

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Deployment Methods](#deployment-methods)
- [Health Checks](#health-checks)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)
- [Security Considerations](#security-considerations)

---

## Overview

This guide provides comprehensive instructions for deploying the GPT-PANELIN-V3.2 MCP (Model Context Protocol) server to production environments. The system provides OpenAI integration for quotation calculations, pricing lookups, and BOM (Bill of Materials) generation for the BROMYROS product line.

### Key Features

- **MCP Server**: Python-based server with stdio/SSE transport support
- **12 Tools**: Price check, catalog search, BOM calculation, batch operations, task management
- **Knowledge Base**: Multi-source pricing data, accessories catalog, BOM rules
- **Background Tasks**: Async processing for batch operations
- **PDF Generation**: Professional quotation reports with BMC branding

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 GPT-PANELIN Container                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │          MCP Server (Python 3.11)                │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │  Handlers (pricing, catalog, bom)        │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │  Background Task Manager                 │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │  PDF Report Generator                    │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Knowledge Base (JSON Files)                │
│  - bromyros_pricing_master.json (141 KB)               │
│  - bromyros_pricing_gpt_optimized.json (131 KB)        │
│  - accessories_catalog.json (48 KB)                     │
│  - bom_rules.json (20 KB)                               │
│  - shopify_catalog_v1.json (759 KB)                     │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Runtime**: Python 3.11+
- **Framework**: MCP SDK 1.0+, Uvicorn/Starlette
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus metrics, Sentry (optional)
- **Logging**: Structured JSON logging with rotation

---

## Prerequisites

### Required Software

- **Docker**: 20.10+ with Docker Compose v2+
- **Git**: For repository access
- **Python**: 3.11+ (for local development)

### Required Credentials

- `OPENAI_API_KEY`: OpenAI API key for GPT integration
- `DOCKER_REGISTRY` (optional): Docker Hub or private registry credentials
- `SENTRY_DSN` (optional): For error tracking

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 2 GB
- Disk: 5 GB free space

**Recommended:**
- CPU: 4 cores
- RAM: 4 GB
- Disk: 10 GB free space

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/matiasportugau-ui/GPT-PANELIN-V3.2.git
cd GPT-PANELIN-V3.2
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

Edit `.env` and set the following critical variables:

```bash
# Required
OPENAI_API_KEY=sk-your-actual-api-key-here
ENVIRONMENT=production

# Optional but recommended
SENTRY_DSN=https://your-sentry-dsn-here
LOG_LEVEL=INFO
```

### 4. Review Configuration

Review and adjust production configuration:

```bash
cat config/production.yaml
```

Key settings to verify:
- Server host, port, workers
- Security settings (API key requirement, rate limiting)
- Monitoring endpoints
- Knowledge base paths

---

## Deployment Methods

### Method 1: Docker Compose (Recommended)

#### Quick Start

```bash
# Build and start services
docker-compose up -d --build

# View logs
docker-compose logs -f panelin-bot

# Check status
docker-compose ps
```

#### Production Deployment

```bash
# Run pre-deployment checks
./scripts/pre_deploy_check.sh

# Deploy to production
./scripts/deploy.sh production

# Verify deployment
./scripts/health_check.sh production
```

### Method 2: Docker Only

```bash
# Build image
docker build -t gpt-panelin:latest .

# Run container
docker run -d \
  --name gpt-panelin \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/panelin_reports/output:/app/panelin_reports/output \
  gpt-panelin:latest
```

### Method 3: Direct Python Execution

**For development only:**

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r mcp/requirements.txt

# Run server
python -m mcp.server
```

---

## Health Checks

### Automated Health Check Script

```bash
./scripts/health_check.sh production
```

This checks:
- MCP server process status
- Knowledge base file integrity
- API endpoint availability
- Quotation calculator functionality
- Docker resource status
- Disk space availability

### Manual Health Checks

#### Check Container Status

```bash
docker-compose ps
docker-compose logs panelin-bot --tail=50
```

#### Verify Knowledge Base

```bash
python3 scripts/validate_knowledge_base.py
```

#### Test MCP Server Import

```bash
docker exec gpt-panelin-v32 python -c "from mcp.server import Server; print('OK')"
```

---

## Monitoring

### Health Endpoint

The MCP server exposes health and metrics endpoints (if implemented):

```bash
# Health check
curl http://localhost:8000/health

# Metrics (Prometheus format)
curl http://localhost:9090/metrics
```

### Logs

#### View Live Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f panelin-bot

# Last 100 lines
docker-compose logs --tail=100 panelin-bot
```

#### Log Files

Logs are stored in:
- `logs/panelin.log` - Main application log
- `logs/panelin-error.log` - Error-only log
- `logs/panelin-json.log` - Structured JSON log

#### Log Rotation

Logs automatically rotate when they reach 10 MB, keeping 5 backup copies.

### Metrics

If Prometheus integration is enabled:
- Metrics endpoint: `http://localhost:9090/metrics`
- Grafana dashboards can be configured to visualize metrics

### Error Tracking

If Sentry is configured:
- Errors are automatically reported to Sentry
- View error details, stack traces, and trends in Sentry dashboard

---

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs for errors
docker-compose logs panelin-bot

# Common causes:
# - Missing or invalid .env file
# - Knowledge base files not found
# - Port 8000 already in use
```

**Solution:**
```bash
# Verify .env file
ls -la .env

# Check port availability
sudo lsof -i :8000

# Validate knowledge base
python3 scripts/validate_knowledge_base.py
```

#### 2. Knowledge Base Errors

```bash
# Symptoms: Handler errors, missing product data

# Validate knowledge base
python3 scripts/validate_knowledge_base.py

# Check file permissions
ls -la *.json

# Verify JSON syntax
python3 -m json.tool bromyros_pricing_master.json > /dev/null
```

#### 3. High Memory Usage

```bash
# Check container stats
docker stats gpt-panelin-v32

# Adjust memory limits in docker-compose.yml
# Under deploy.resources.limits.memory
```

#### 4. Performance Issues

```bash
# Increase workers in config/production.yaml
# server.workers: 4 → 8

# Enable caching
# knowledge_base.cache_enabled: true

# Restart services
docker-compose restart
```

### Debug Mode

To enable debug logging:

```bash
# Update .env
LOG_LEVEL=DEBUG

# Or config/production.yaml
logging:
  level: "DEBUG"

# Restart container
docker-compose restart panelin-bot
```

---

## Rollback Procedures

### Quick Rollback

```bash
# Stop current deployment
docker-compose down

# Pull previous version
docker pull gpt-panelin:production-previous

# Start previous version
docker-compose up -d
```

### Automated Rollback

The deployment script includes automatic rollback on failure:

```bash
./scripts/deploy.sh production
# If health checks fail, automatically rolls back
```

### Manual Rollback Steps

1. **Identify previous working version:**
   ```bash
   docker images gpt-panelin
   ```

2. **Tag previous version as latest:**
   ```bash
   docker tag gpt-panelin:production-20240213-120000 gpt-panelin:latest
   ```

3. **Restart services:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Verify rollback:**
   ```bash
   ./scripts/health_check.sh production
   ```

### Database/Storage Rollback

If knowledge base was updated:

```bash
# Restore from backup
cp backup/bromyros_pricing_master.json.backup bromyros_pricing_master.json

# Restart services
docker-compose restart
```

---

## Security Considerations

### Secrets Management

**DO NOT commit secrets to version control!**

```bash
# Store secrets in .env file
# Add .env to .gitignore (already done)

# For production, use secret management systems:
# - Kubernetes Secrets
# - AWS Secrets Manager
# - HashiCorp Vault
# - GitHub Secrets (for CI/CD)
```

### Docker Security

The Dockerfile implements security best practices:

- ✅ Non-root user (`panelin` user, UID 1000)
- ✅ Multi-stage build to minimize image size
- ✅ Minimal base image (`python:3.11-slim`)
- ✅ No unnecessary packages
- ✅ Read-only knowledge base mounts (where applicable)

### Network Security

```yaml
# In docker-compose.yml
security:
  api_key_required: true
  cors_enabled: false
  rate_limiting: true
```

### File Permissions

```bash
# Ensure correct permissions
chmod 600 .env
chmod 700 scripts/*.sh
chmod 755 logs/
```

### SSL/TLS

For production, deploy behind a reverse proxy with SSL:

```nginx
# Nginx example
server {
    listen 443 ssl;
    server_name api.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Continuous Deployment

### GitHub Actions CI/CD

The repository includes automated CI/CD workflows:

**CI Pipeline (`.github/workflows/ci-cd.yml`):**
- Runs on every push to main and PRs
- Executes tests, linting, knowledge base validation
- Builds Docker image
- Deploys to staging automatically
- Deploys to production with manual approval

**Test Workflow (`.github/workflows/test.yml`):**
- Matrix testing across Python 3.10, 3.11, 3.12
- Unit tests, integration tests
- Knowledge base validation

**Health Check Workflow (`.github/workflows/health-check.yml`):**
- Runs every 6 hours
- Validates system health
- Can be triggered manually

### Required GitHub Secrets

Configure these in GitHub repository settings:

```
OPENAI_API_KEY           # Required
DOCKER_USERNAME          # For Docker Hub (if using)
DOCKER_PASSWORD          # For Docker Hub (if using)
PRODUCTION_SERVER_SSH_KEY # For SSH deployment (if applicable)
SENTRY_DSN               # For error tracking (optional)
```

---

## Backup and Recovery

### Backup Knowledge Base

```bash
# Create backup directory
mkdir -p backup

# Backup all JSON files
cp *.json backup/
tar -czf backup/kb-$(date +%Y%m%d-%H%M%S).tar.gz *.json

# Automated daily backup (add to crontab)
0 2 * * * cd /path/to/GPT-PANELIN-V3.2 && tar -czf backup/kb-$(date +\%Y\%m\%d).tar.gz *.json
```

### Restore from Backup

```bash
# Extract backup
tar -xzf backup/kb-20240214.tar.gz

# Restart services
docker-compose restart
```

---

## Performance Tuning

### Optimize for High Load

1. **Increase workers:**
   ```yaml
   # config/production.yaml
   server:
     workers: 8  # Increase from 4
   ```

2. **Enable caching:**
   ```yaml
   knowledge_base:
     cache_enabled: true
     cache_ttl_seconds: 3600
   ```

3. **Adjust resource limits:**
   ```yaml
   # docker-compose.yml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 4G
   ```

4. **Enable connection pooling:**
   ```yaml
   performance:
     connection_pool_size: 20
     connection_max_overflow: 40
   ```

---

## Support and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Review logs for errors
- Check disk space
- Verify backup integrity
- Update dependencies (if needed)

**Monthly:**
- Update Docker base images
- Review and optimize knowledge base
- Analyze performance metrics
- Security audit

### Getting Help

- **Issues**: GitHub Issues tracker
- **Documentation**: README.md, this guide
- **Logs**: Check `logs/panelin-error.log` for details

---

## Appendix

### Deployment Checklist

Before deploying to production:

- [ ] Run pre-deployment checks: `./scripts/pre_deploy_check.sh`
- [ ] Validate knowledge base: `python3 scripts/validate_knowledge_base.py`
- [ ] All tests pass: `pytest test_mcp_handlers_v1.py`
- [ ] Environment variables set in `.env`
- [ ] Docker and docker-compose installed
- [ ] Secrets configured (GitHub Secrets for CI/CD)
- [ ] Monitoring enabled (Sentry, Prometheus)
- [ ] Backup system in place
- [ ] Rollback plan documented
- [ ] Team notified of deployment

### Useful Commands

```bash
# View all running containers
docker-compose ps

# Restart specific service
docker-compose restart panelin-bot

# View resource usage
docker stats

# Execute command in container
docker exec -it gpt-panelin-v32 /bin/bash

# Remove all stopped containers
docker-compose down

# View container logs with timestamps
docker-compose logs -f -t panelin-bot

# Export logs to file
docker-compose logs panelin-bot > deployment.log
```

---

**Last Updated**: February 14, 2026  
**Version**: 1.0  
**Maintainer**: GPT-PANELIN Team
