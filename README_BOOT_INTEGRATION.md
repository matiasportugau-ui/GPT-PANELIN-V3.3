# BOOT Integration Guide

## Overview

The BOOT (Bootstrap, Operations, Orchestration, Testing) architecture provides a robust, idempotent initialization process for GPT-PANELIN-V3.2. This guide explains how to use the BOOT process, configure it, and test it.

## What is BOOT?

BOOT is an automated initialization process that:

1. **Creates and activates a Python virtual environment** - Isolates dependencies
2. **Installs dependencies** - From `requirements.txt`
3. **Preloads knowledge files** - Copies from `knowledge_src/` to `knowledge/`
4. **Creates a knowledge index** - With SHA256 hashes for integrity verification
5. **Optionally generates embeddings** - When explicitly enabled with API key
6. **Validates the system** - Ensures all files are indexed correctly
7. **Signals readiness** - Creates `.boot-ready` marker file

## Quick Start

### Basic Usage

```bash
# Run BOOT process (embeddings disabled by default)
./boot.sh
```

### With Embeddings

```bash
# Enable embeddings generation (requires OPENAI_API_KEY)
export GENERATE_EMBEDDINGS=1
export OPENAI_API_KEY="your-api-key-here"
./boot.sh
```

## Architecture

### Files and Components

| File | Purpose | Required |
|------|---------|----------|
| `boot.sh` | Main orchestrator script | Yes |
| `boot_preload.py` | Knowledge file preloader | Yes |
| `index_validator.py` | Index validation tool | Yes |
| `knowledge_src/` | Source directory for knowledge files | Optional |
| `knowledge/` | Processed knowledge files | Created automatically |
| `knowledge_index.json` | File index with hashes | Generated |
| `.boot-log` | Audit log with timestamps | Generated |
| `.boot-ready` | Readiness marker | Generated |
| `.venv/` | Python virtual environment | Created automatically |

### Process Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        boot.sh                              │
│  Main Orchestrator - Coordinates all BOOT steps             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Check Prerequisites                                │
│  - Verify Python 3.8+ is available                          │
│  - Acquire lock to prevent concurrent runs                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Setup Virtual Environment                          │
│  - Create .venv/ if it doesn't exist                        │
│  - Activate virtual environment                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Install Dependencies                               │
│  - Upgrade pip                                               │
│  - Install packages from requirements.txt                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Run boot_preload.py                                │
│  - Copy files from knowledge_src/ to knowledge/             │
│  - Calculate SHA256 hashes                                   │
│  - Generate knowledge_index.json                             │
│  - Optionally generate embeddings (if GENERATE_EMBEDDINGS=1)│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Run index_validator.py                             │
│  - Verify index file is valid JSON                          │
│  - Check all indexed files exist                            │
│  - Verify SHA256 hashes match                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Create Readiness Marker                            │
│  - Write timestamp to .boot-ready                           │
│  - Log completion to .boot-log                              │
└─────────────────────────────────────────────────────────────┘
```

## Environment Variables

### Core Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GENERATE_EMBEDDINGS` | `0` | Set to `1` to enable embeddings generation |
| `OPENAI_API_KEY` | (none) | OpenAI API key (required if `GENERATE_EMBEDDINGS=1`) |
| `PYTHON_BIN` | `python3` | Python binary to use |
| `VENV_DIR` | `.venv` | Virtual environment directory |

### Examples

```bash
# Disable embeddings (default, safe for CI)
GENERATE_EMBEDDINGS=0 ./boot.sh

# Enable embeddings with API key
GENERATE_EMBEDDINGS=1 OPENAI_API_KEY="sk-..." ./boot.sh

# Use specific Python version
PYTHON_BIN=python3.9 ./boot.sh

# Custom venv location
VENV_DIR=/opt/venv ./boot.sh
```

## Security Considerations

### ⚠️ CRITICAL: Never Commit Secrets

- **DO NOT** commit API keys to the repository
- **DO NOT** hardcode credentials in scripts
- **DO NOT** include secrets in `.boot-log`

### Best Practices

1. **Use environment variables** for all sensitive configuration
2. **Set secure permissions** on log files (600)
3. **Rotate logs** automatically (boot.sh rotates at 5MB)
4. **Validate inputs** to prevent injection attacks
5. **Use lock files** to prevent concurrent runs

### API Key Management

```bash
# ✅ GOOD: Use environment variables
export OPENAI_API_KEY="sk-..."
./boot.sh

# ✅ GOOD: Use .env file (add to .gitignore!)
echo "OPENAI_API_KEY=sk-..." > .env.local
source .env.local
./boot.sh

# ❌ BAD: Hardcoding in scripts
OPENAI_API_KEY="sk-..." ./boot.sh  # Visible in process list!
```

### Recommended .gitignore Entries

```gitignore
# BOOT artifacts
.boot-log
.boot-log.old
.boot-ready
.boot-lock/
.venv/
knowledge_index.json

# Secrets
.env.local
.env.production
*.pem
*.key
```

## Idempotency

The BOOT process is **idempotent** - safe to run multiple times:

- **Virtual environment**: Created only if missing
- **Dependencies**: Installed only if requirements change
- **Knowledge files**: Copied only if source differs (hash check)
- **Index**: Regenerated with current state
- **Lock**: Prevents concurrent runs

### Re-running BOOT

```bash
# Safe to run multiple times
./boot.sh
./boot.sh  # Second run will skip unchanged files
./boot.sh  # Third run will skip unchanged files
```

## Error Handling

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Lock acquisition failed (concurrent run) |
| `3` | Python or dependency error |
| `4` | Preload or validation error |

### Common Errors

#### Lock Already Exists

**Error**: `Another BOOT process is running`

**Solution**:
```bash
# Wait for other process to finish, or remove stale lock:
rm -rf .boot-lock
./boot.sh
```

#### Python Not Found

**Error**: `Python not found`

**Solution**:
```bash
# Install Python 3.8+ or specify path:
PYTHON_BIN=/usr/bin/python3.9 ./boot.sh
```

#### Missing Dependencies

**Error**: `Failed to install dependencies`

**Solution**:
```bash
# Check requirements.txt exists and is valid
# Upgrade pip first:
python3 -m pip install --upgrade pip
./boot.sh
```

## Manual Testing

### Test 1: Basic BOOT (No Embeddings)

```bash
# Clean start
rm -rf .venv/ .boot-log .boot-ready knowledge/ knowledge_index.json

# Create sample knowledge file
mkdir -p knowledge_src
echo "Sample knowledge content" > knowledge_src/sample.txt

# Run BOOT
./boot.sh

# Verify outputs
test -d .venv && echo "✓ Virtual environment created"
test -f .boot-log && echo "✓ Boot log created"
test -f .boot-ready && echo "✓ Readiness marker created"
test -f knowledge_index.json && echo "✓ Index created"
test -f knowledge/sample.txt && echo "✓ Knowledge file copied"

# Validate index
python index_validator.py
```

### Test 2: Idempotency Check

```bash
# Run BOOT twice
./boot.sh
./boot.sh

# Check log for "skipped" messages
grep -i "skipped" .boot-log
```

### Test 3: With Embeddings (Requires API Key)

```bash
# Set API key
export OPENAI_API_KEY="sk-your-real-key-here"
export GENERATE_EMBEDDINGS=1

# Run BOOT
./boot.sh

# Check index for embeddings flag
grep "embeddings_generated" knowledge_index.json
```

### Test 4: Lock Mechanism

```bash
# Start BOOT in background
./boot.sh &

# Try to run again immediately (should fail with code 2)
./boot.sh
# Expected: "Another BOOT process is running"
```

### Test 5: Validation

```bash
# Run BOOT
./boot.sh

# Validate index
python index_validator.py

# Corrupt a file and re-validate (should fail)
echo "corrupted" >> knowledge/sample.txt
python index_validator.py
# Expected: Hash mismatch error
```

## CI/CD Integration

### GitHub Actions

See `.github/workflows/boot-smoke.yml` for CI integration example.

**Key points**:
- Set `GENERATE_EMBEDDINGS=0` in CI
- No API keys required
- Smoke test validates scripts exist
- Runs validator if index exists

### Docker

See `Dockerfile` for container integration example.

**Key points**:
- Run BOOT at container start
- Embeddings disabled by default
- Mount `knowledge_src/` as volume for updates
- Health check uses `.boot-ready`

## Troubleshooting

### Check Logs

```bash
# View full log
cat .boot-log

# View recent errors
grep -i error .boot-log

# View last 20 lines
tail -20 .boot-log
```

### Verify System State

```bash
# Check if BOOT completed
test -f .boot-ready && echo "BOOT ready" || echo "BOOT not ready"

# Check virtual environment
source .venv/bin/activate
python --version
pip list

# Validate index
python index_validator.py
```

### Clean Reset

```bash
# Remove all BOOT artifacts
rm -rf .venv/ .boot-lock/ .boot-log .boot-ready knowledge/ knowledge_index.json

# Start fresh
./boot.sh
```

## Advanced Usage

### Custom Knowledge Sources

```bash
# Symlink external knowledge directory
ln -s /path/to/external/knowledge knowledge_src

# Run BOOT
./boot.sh
```

### Multiple Environments

```bash
# Development environment
VENV_DIR=.venv-dev ./boot.sh

# Production environment  
VENV_DIR=.venv-prod GENERATE_EMBEDDINGS=1 ./boot.sh
```

### Automated Workflows

```bash
# Update knowledge and re-BOOT
rsync -av external-source/ knowledge_src/
./boot.sh

# Scheduled re-indexing (cron)
0 */6 * * * cd /path/to/project && ./boot.sh >> /var/log/boot-cron.log 2>&1
```

## Support

For issues or questions:

1. Check `.boot-log` for error details
2. Review this documentation
3. Run validation: `python index_validator.py`
4. Check GitHub issues
5. Contact maintainers

## Version History

- **v1.0.0** (2026-02-11): Initial BOOT implementation
  - Idempotent file copying
  - SHA256 hash verification
  - Optional embeddings generation
  - Comprehensive logging and error handling
