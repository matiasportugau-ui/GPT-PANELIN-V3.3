# Contributing to GPT-PANELIN-V3.3

Thank you for your interest in contributing to GPT-PANELIN-V3.3! This document provides guidelines and instructions for contributing to the project.

> **📘 Developer Guidelines:** Before contributing, please review our comprehensive [GitHub Copilot Instructions](.github/copilot-instructions.md) which cover coding standards, testing practices, MCP patterns, Docker conventions, and security guidelines. These instructions are used by GitHub Copilot and serve as the authoritative reference for all development work.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Knowledge Base Updates](#knowledge-base-updates)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and professional in all interactions.

---

## Getting Started

### Prerequisites

- Python 3.10, 3.11, or 3.12
- Git
- Docker and Docker Compose (for testing deployment)
- OpenAI API key (for integration testing)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/GPT-PANELIN-V3.2.git
   cd GPT-PANELIN-V3.2
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/matiasportugau-ui/GPT-PANELIN-V3.2.git
   ```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# MCP server dependencies
pip install -r mcp/requirements.txt

# Development dependencies
pip install -r requirements-prod.txt
```

### 3. Create Environment File

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 4. Verify Setup

```bash
# Run tests
pytest test_mcp_handlers_v1.py -v

# Validate knowledge base
python scripts/validate_knowledge_base.py

# Check MCP server imports
python -c "from mcp.server import Server; print('OK')"
```

---

## Making Changes

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch (if applicable)
- Feature branches: `feature/your-feature-name`
- Bug fixes: `fix/issue-description`
- Hotfixes: `hotfix/critical-issue`

### Creating a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-new-feature
```

### Commit Guidelines

Use clear, descriptive commit messages:

```bash
# Good examples
git commit -m "Add batch BOM calculation endpoint"
git commit -m "Fix pricing calculation for ISODEC panels"
git commit -m "Update knowledge base with new accessories"

# Poor examples (avoid)
git commit -m "Fixed stuff"
git commit -m "WIP"
git commit -m "Updates"
```

**Commit Message Format:**
```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

---

## Testing

### Running Tests Locally

#### Unit Tests

```bash
# Run all tests
pytest test_mcp_handlers_v1.py -v

# Run with coverage
pytest test_mcp_handlers_v1.py --cov=mcp --cov-report=term-missing

# Run specific test
pytest test_mcp_handlers_v1.py::TestPriceCheckV1Contract -v
```

#### Knowledge Base Validation

```bash
python scripts/validate_knowledge_base.py
```

#### MCP Server Tests

```bash
# Test MCP handlers
python -c "
from mcp.handlers import pricing, catalog, bom
print('All handlers imported successfully')
"
```

#### Integration Tests

```bash
# Test with real data
python -c "
from mcp.handlers.pricing import handle_price_check
result = handle_price_check('ISODEC', thickness_mm=100)
print('Price check:', result['ok'])
"
```

### Pre-deployment Testing

Before submitting a PR, run:

```bash
# Full pre-deployment check
./scripts/pre_deploy_check.sh
```

This validates:
- ✅ All tests pass
- ✅ Knowledge base is valid
- ✅ No uncommitted changes
- ✅ Docker configuration is correct
- ✅ Code quality (linting)

---

## CI/CD Pipeline

### Understanding the CI Pipeline

When you open a PR, GitHub Actions automatically runs:

1. **Test Workflow** (`.github/workflows/test.yml`)
   - Tests on Python 3.10, 3.11, 3.12
   - Unit tests with coverage
   - MCP integration tests
   - Knowledge base validation

2. **CI/CD Pipeline** (`.github/workflows/ci-cd.yml`)
   - Linting (flake8, black, mypy)
   - JSON validation
   - Docker build test

### Viewing CI Results

1. Go to your PR on GitHub
2. Scroll to "Checks" section
3. Click on failed checks to see logs
4. Fix issues and push updates

### Common CI Failures and Fixes

#### Test Failures

```bash
# Run tests locally first
pytest test_mcp_handlers_v1.py -v

# Check specific failure
pytest test_mcp_handlers_v1.py::test_name -vv
```

#### Linting Failures

```bash
# Check for syntax errors
flake8 mcp/ --select=E9,F63,F7,F82 --show-source

# Format code with black
black mcp/ --line-length=127

# Type checking
mypy mcp/ --ignore-missing-imports
```

#### Knowledge Base Issues

```bash
# Validate JSON files
python scripts/validate_knowledge_base.py

# Check specific file
python -m json.tool bromyros_pricing_master.json > /dev/null
```

### Testing Before Deployment

The CI pipeline includes deployment stages:

- **Staging**: Automatically deploys to staging on merge to `main`
- **Production**: Requires manual approval in GitHub

To test deployment locally:

```bash
# Test Docker build
docker build -t gpt-panelin:test .

# Test with docker-compose
docker-compose up -d --build

# Run health checks
./scripts/health_check.sh
```

---

## Submitting Changes

### Pull Request Process

1. **Ensure all tests pass locally:**
   ```bash
   pytest test_mcp_handlers_v1.py -v
   ./scripts/pre_deploy_check.sh
   ```

2. **Push your changes:**
   ```bash
   git push origin feature/my-feature
   ```

3. **Create Pull Request:**
   - Go to GitHub repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in PR template

4. **PR Description should include:**
   - What changes were made
   - Why the changes are needed
   - How to test the changes
   - Any breaking changes
   - Related issues (e.g., "Closes #42")

### PR Review Process

- All PRs require review before merging
- CI checks must pass
- Address reviewer feedback
- Keep PR focused and reasonably sized

### After PR is Merged

1. **Delete your feature branch:**
   ```bash
   git checkout main
   git pull upstream main
   git branch -d feature/my-feature
   git push origin --delete feature/my-feature
   ```

2. **Monitor deployment:**
   - Check staging deployment if auto-deployed
   - Watch for any issues in production

---

## Code Style

> **📘 Comprehensive Guidelines:** For complete coding standards, testing practices, MCP patterns, Docker conventions, and security guidelines, see [.github/copilot-instructions.md](.github/copilot-instructions.md). The following is a summary of key points.

### Python Style Guide

We follow PEP 8 with some modifications:

- **Indentation**: Exactly 4 spaces per level (CRITICAL - PEP 8 standard)
- **Line length**: 127 characters
- **Imports**: Organized (standard library, third-party, local)
- **Docstrings**: Use for public functions and classes
- **Type hints**: Use Python typing for all function signatures
- **Financial calculations**: ALWAYS use `Decimal`, never `float`

### Formatting

Use `black` for automatic formatting:

```bash
# Format specific file
black mcp/handlers/pricing.py

# Format entire directory
black mcp/

# Check without modifying
black --check mcp/
```

### Linting

```bash
# Critical errors only
flake8 mcp/ --select=E9,F63,F7,F82 --show-source

# All checks
flake8 mcp/ --max-line-length=127
```

### Example Code Style

```python
"""Module docstring."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def handle_price_check(
    query: str,
    thickness_mm: Optional[int] = None,
    legacy_format: bool = False
) -> Dict[str, Any]:
    """
    Check prices for products matching query.
    
    Args:
        query: Product SKU or search term
        thickness_mm: Optional thickness filter
        legacy_format: Return legacy format if True
    
    Returns:
        Dict with 'ok', 'contract_version', and result data
    """
    # Implementation
    pass
```

---

## Knowledge Base Updates

### Updating JSON Files

When updating knowledge base files:

1. **Validate before committing:**
   ```bash
   python -m json.tool bromyros_pricing_master.json > /dev/null
   python scripts/validate_knowledge_base.py
   ```

2. **Format consistently:**
   - Use 2-space indentation
   - UTF-8 encoding
   - Unix line endings (LF)

3. **Test impact:**
   ```bash
   # Run relevant tests
   pytest test_mcp_handlers_v1.py -v
   ```

4. **Document changes:**
   - Update `corrections_log.json` if fixing errors
   - Note changes in PR description

### Adding New Products

When adding products to the catalog:

1. Follow existing JSON schema structure
2. Include all required fields (SKU, name, specifications, pricing)
3. Validate against contract schemas
4. Test with actual queries

### Price Updates

For price updates:

1. Update `bromyros_pricing_master.json` (authoritative source)
2. Optionally update `bromyros_pricing_gpt_optimized.json` (GPT-friendly)
3. Document in commit message with date and source
4. Test price_check tool with updated data

---

## Additional Resources

### Development Guidelines
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - **Comprehensive developer guidelines** (coding standards, testing, security)

### Project Documentation
- [README.md](README.md) - Project overview and features
- [DEPLOYMENT.md](DEPLOYMENT.md) - Comprehensive deployment guide
- [MCP_QUICK_START.md](MCP_QUICK_START.md) - MCP server guide
- [PANELIN_KNOWLEDGE_BASE_GUIDE.md](PANELIN_KNOWLEDGE_BASE_GUIDE.md) - KB architecture
- [.evolucionador/README.md](.evolucionador/README.md) - EVOLUCIONADOR autonomous evolution system

---

## Getting Help

- **Issues**: Check existing GitHub issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Review docs/ directory for detailed guides

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing to GPT-PANELIN-V3.3!** 🚀
