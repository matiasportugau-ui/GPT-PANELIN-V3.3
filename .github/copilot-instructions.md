# GitHub Copilot Instructions for Panelin GPT

---

## ⚠️ INSTRUCCIONES MAESTRAS - ARQUITECTO DE SISTEMAS AI

Eres un **Arquitecto de Sistemas AI** trabajando en el repositorio GPT-PANELIN. Tu objetivo es mantener la integridad de la "Knowledge Base" (KB) y orquestar los agentes autónomos.

### JERARQUÍA DE VERDAD (NO ROMPER NUNCA)

Al sugerir código o respuestas, respeta estrictamente esta prioridad:

1. **NIVEL 1 (Master):** `BMC_Base_Conocimiento_GPT-2.json` (Precios base, fórmulas oficiales).
2. **NIVEL 1.2:** `accessories_catalog.json` (Precios de accesorios).
3. **NIVEL 1.3:** `bom_rules.json` (Reglas paramétricas de construcción).
4. **CÓDIGO:** `quotation_calculator_v3.py` (Lógica de cálculo validada).

### ZONAS DE TRABAJO

Clasifica cada tarea en una de estas zonas antes de generar código:

- **ZONA 1 (Core):** Motor de cálculo y prompts.
- **ZONA 2 (Interfaces):** Wolf API y Webhooks.
- **ZONA 3 (Infra):** Docker, Cloud Run, Scripts de validación (`validate_gpt_files.py`).
- **ZONA 6 (Ops):** El agente `Evolucionador` y reportes.

### REGLAS DE DESARROLLO

1. **Validación Obligatoria:** Antes de dar por finalizado un cambio en JSON, sugiere ejecutar: `python validate_gpt_files.py`.
2. **Autonomía:** Si detectas un error de precio, no lo cambies en el código. Genera una entrada para `corrections_log.json`.
3. **Evolucionador:** Si te pido "optimizar", consulta primero `.evolucionador/reports/latest.md` para ver qué recomienda el agente autónomo.

### ESTILO DE CÓDIGO ESPECÍFICO

- **Python:** Tipado estricto, Docstrings en español para funciones de dominio (KB, cálculo).
- **JSON:** Sin comentarios, validación de esquema estricta.
- **Commits:** Mensajes descriptivos que referencian la zona de trabajo modificada.

---

## Project Overview

Panelin is an advanced AI assistant specialized in generating professional quotations for construction panel systems (BMC Uruguay). This repository contains GPT configuration files, knowledge bases, MCP server integration, and automated deployment tools.

**Core Purpose:** Technical sales assistant for panel systems with accurate BOM generation, technical validation, and professional PDF quotations.

---

## Technology Stack

### Languages & Frameworks
- **Python 3.11** (standard across all Docker images and CI/CD)
- **Flask** for web services (frontend/backend)
- **MCP (Model Context Protocol)** v0.3.0 for AI integration
- **pytest** for testing with async support

### Key Dependencies
- `reportlab` and `pillow` for PDF generation
- `pytest-asyncio` for async testing
- Decimal for financial calculations (never use float for money)

### Infrastructure
- **Docker**: Multi-stage builds with Python 3.11-slim base
- **GCP Cloud Run**: Deployment target with Cloud SQL
- **Terraform**: Infrastructure as Code
- **GitHub Actions**: CI/CD workflows

---

## Coding Standards

### Python Style

#### Indentation & Formatting
- **CRITICAL:** Use exactly 4 spaces per indentation level (PEP 8)
- Never use tabs or non-standard indentation (e.g., 6-space indents)
- Follow PEP 8 style guidelines throughout

#### Type Hints
- Use Python typing for all function signatures
- Define TypedDict classes for structured data
- Example:
  ```python
  from typing import TypedDict, Optional, List
  
  class QuotationResult(TypedDict):
      quotation_id: str
      product_name: str
      area_m2: float
  ```

#### Financial Calculations
- **ALWAYS** use `Decimal` for financial calculations, never `float`
- Import: `from decimal import Decimal, ROUND_HALF_UP`
- All monetary values must be deterministic and verifiable
- Include `calculation_verified: True` flag in results

#### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Documentation
- Add docstrings to all public functions and classes
- Keep comments minimal unless explaining complex logic
- Match existing comment style in the file
- Document critical architecture principles at module level

---

## Testing Practices

### Running Tests
- **ALWAYS** run pytest from repository root, never from test directory
- Correct: `pytest mcp/tests/test_handlers.py`
- Wrong: `cd mcp/tests && pytest test_handlers.py` (causes ModuleNotFoundError)

### Test Patterns
- Use `@pytest.mark.asyncio` decorators for async tests
- Never use `asyncio.run()` wrapper pattern
- Example:
  ```python
  @pytest.mark.asyncio
  async def test_handler():
      result = await my_async_function()
      assert result is not None
  ```

### MCP Testing
- Import error codes from `mcp_tools.contracts` instead of hardcoding
- Test MCP handlers using pytest: `pytest mcp/tests/test_handlers.py`
- All MCP handlers have optional `legacy_format: bool = False` parameter

### Test Requirements
- All new features must have corresponding tests
- Test coverage is tracked in CI/CD
- Run tests before committing changes

---

## MCP Server Patterns

### Handler Structure
- All MCP handlers must have `legacy_format: bool = False` parameter for backwards compatibility
- Handlers are async and use `@pytest.mark.asyncio` for testing
- Import error codes from `mcp_tools.contracts`:
  - `PRICE_CHECK_ERROR_CODES`
  - `CATALOG_SEARCH_ERROR_CODES`
  - `BOM_CALCULATE_ERROR_CODES`

### Example Handler Signature
```python
async def handle_price_check(
    query: str,
    filter_type: str,
    thickness_mm: Optional[int] = None,
    legacy_format: bool = False
) -> dict:
    # Implementation
    pass
```

### Validation
- `query`: minLength 2
- `filter_type`: sku/family/type/search
- `thickness_mm`: 20-250 range when provided

---

## Docker & Deployment

### Dockerfile Standards
- Base image: `python:3.11-slim` (always use 3.11, not 3.9)
- Multi-stage builds for optimization
- Non-root user: `panelin` with UID 1000
- Include `HEALTHCHECK` directives
- Set environment variables:
  - `PYTHONUNBUFFERED=1`
  - `PYTHONDONTWRITEBYTECODE=1`
- Always create and use `.dockerignore` files

### GCP Cloud Run
- Unix socket format for Cloud SQL: `/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME`
- Use `os.environ.get()` for all environment variables:
  - `PORT`, `PROJECT_ID`, `DB_CONNECTION_NAME`
  - `DB_USER`, `DB_PASSWORD`, `DB_NAME`
  - `BACKEND_SERVICE_URL`

---

## Security Guidelines

### API Keys & Secrets
- **NEVER** hardcode API keys or secrets
- Inject from GitHub Secrets in workflows (e.g., `WOLF_API_KEY`)
- Test scripts must fail with clear error if secrets not set
- Example validation:
  ```bash
  if [ -z "$WOLF_API_KEY" ]; then
    echo "Error: WOLF_API_KEY not set"
    exit 1
  fi
  ```

### Input Validation
- Always validate user inputs before processing
- Use sanitization functions to prevent XSS
- Validate ranges and constraints (e.g., thickness 20-250mm)

### Dependencies
- Check GitHub advisory database before adding new dependencies
- Only add dependencies from supported ecosystems
- Keep dependencies up-to-date

---

## Memory Storage

### When to Store Facts
Store facts that are:
- Likely to help future coding/review tasks
- Independent of current task changes
- Unlikely to change over time
- Can't be easily inferred from limited code samples
- Contain no secrets or sensitive data

### Fact Categories
- `bootstrap_and_build`: How to build/test the project
- `user_preferences`: Coding style, conventions, library preferences
- `general`: File-independent facts about the codebase
- `file_specific`: Information about specific files

### Examples of Good Facts
- "Use ErrKind wrapper for every public API error"
- "Follow PEP 8: 4 spaces per indentation level"
- "Run tests from repository root: pytest mcp/tests/"
- "All Docker images use Python 3.11-slim base"

---

## Repository-Specific Conventions

### Quotation Calculator
- Zero-waste optimization: suggest panel lengths in 5cm steps when waste >5%
- Autoportancia validation: default safety_margin is 0.0 (exact manufacturer limits)
- Integration: `suggest_optimization()` called within `calculate_panel_quote()`

### File Organization
- MCP handlers: `/mcp/handlers/`
- MCP tests: `/mcp/tests/`
- Background tasks: `/background_tasks/`
- Documentation: Root level `.md` files
- Workflows: `.github/workflows/`
- Agent definitions: `.github/agents/`

### Git Practices
- Never use `git reset` or `git rebase` (force push not available)
- Use descriptive commit messages
- Keep changes minimal and focused
- Review files before committing

---

## Don't Do

- Don't use floats for financial calculations (use Decimal)
- Don't hardcode API keys or secrets
- Don't use tabs or non-standard indentation
- Don't run pytest from test directories (use repo root)
- Don't add comments unnecessarily (match existing style)
- Don't create temporary files in the repository (use `/tmp`)
- Don't modify working code unless fixing security issues
- Don't add new linting/testing tools without necessity
- Don't remove or modify unrelated tests

---

## Common Commands

### Testing
```bash
# Run all MCP tests
pytest mcp/tests/test_handlers.py -v

# Run with coverage
pytest mcp/tests/test_handlers.py -v --cov=mcp/handlers --cov-report=term-missing

# Run specific test
pytest mcp/tests/test_handlers.py::test_function_name -v
```

### Building
```bash
# Docker build
docker build -t panelin:latest .

# Docker compose
docker-compose up -d
```

### Virtual Environment
```bash
# Create and activate
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r mcp/requirements.txt
```

---

## Quick Reference

| Topic | Key Point |
|-------|-----------|
| **Python Version** | 3.11 (standard everywhere) |
| **Indentation** | Exactly 4 spaces (PEP 8) |
| **Money** | Always use Decimal, never float |
| **Testing** | Run from repo root, use @pytest.mark.asyncio |
| **Docker** | Python 3.11-slim, non-root user (panelin:1000) |
| **Secrets** | GitHub Secrets only, never hardcode |
| **MCP** | Import error codes from mcp_tools.contracts |
| **Memory** | Store facts about conventions and patterns |

---

*Last updated: 2026-02-16*
