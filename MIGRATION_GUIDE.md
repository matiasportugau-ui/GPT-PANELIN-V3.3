# Panelin Agno — Guía de Migración y Deployment

## Arquitectura

```
Usuario → Agno Agent (backend posee el agente)
               ↓
         AgentOS (FastAPI + 50+ endpoints automáticos)
               ↓
    ┌──────────┼──────────┐
    │          │          │
Workflow   MCPTools   PostgresDb
(7 steps)  (25 tools)  (sessions)
    │
    ↓
Pipeline Determinístico v4.0 ($0.00 por paso)
classify → parse → SRE → BOM → pricing → validate
    │
    ↓
LLM Respond (~$0.02 por cotización)
```

## Estructura de Archivos Nuevos

```
src/
├── __init__.py
├── app.py                    # Entry point — AgentOS + Wolf API
├── core/
│   ├── __init__.py
│   └── config.py             # Pydantic settings (single source of truth)
├── quotation/
│   ├── __init__.py
│   ├── service.py            # QuotationService — wrapper del engine v4
│   └── tools.py              # Agno tool wrappers (@tool functions)
├── agent/
│   ├── __init__.py
│   ├── panelin.py            # Agente conversacional principal
│   ├── workflow.py           # Workflow de cotización (7 steps + LLM)
│   └── guardrails.py         # Output guardrails (anti-hallucination)
├── integration/
│   ├── __init__.py
│   ├── sheets_tools.py       # Google Sheets CRM tools
│   └── pdf_tools.py          # PDF generation tool
└── tests/
    ├── __init__.py
    └── test_workflow.py       # 29 integration tests
```

## Prerequisitos

- Python 3.10+
- PostgreSQL 16 (Cloud SQL ya existe)
- OpenAI API Key
- Google Cloud credentials (para Sheets + GCS)

## Instalación Local

```bash
# 1. Instalar dependencias
pip install -r requirements-agno.txt

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con:
#   OPENAI_API_KEY=sk-...
#   DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/panelin
#   WOLF_API_KEY=...
#   CORS_ALLOWED_ORIGINS=http://localhost:3000

# 3. Ejecutar tests
PYTHONPATH=. python -m pytest src/tests/test_workflow.py -v
PYTHONPATH=. python -m pytest panelin_v4/tests/test_engine.py -v

# 4. Ejecutar servidor
PYTHONPATH=. python -m src.app
# → http://localhost:8080/docs
```

## Docker Local

```bash
# Con PostgreSQL + pgvector
docker compose -f docker-compose.agno.yml up --build

# Verificar
curl http://localhost:8080/health
curl http://localhost:8080/docs
```

## Deploy a Cloud Run

### Opción 1: Cloud Build (CI/CD)

```bash
gcloud builds submit --config cloudbuild.agno.yaml
```

### Opción 2: Deploy directo

```bash
gcloud run deploy panelin-agno \
    --source . \
    --dockerfile Dockerfile.agno \
    --port 8080 \
    --region us-central1 \
    --memory 512Mi \
    --set-env-vars ENVIRONMENT=production \
    --set-secrets OPENAI_API_KEY=openai-api-key:latest,DATABASE_URL=database-url:latest
```

## Endpoints Disponibles

### AgentOS (automáticos)
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/v1/agents/{id}/runs` | POST | Ejecutar agente |
| `/v1/sessions` | CRUD | Gestión de sesiones |
| `/v1/memories` | CRUD | Gestión de memorias |
| `/docs` | GET | API docs interactiva |

### Custom (preservados de Wolf API)
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/calculate_quote` | POST | Cotización Wolf API |
| `/find_products` | POST | Búsqueda de productos |
| `/sheets/*` | CRUD | Google Sheets CRM |
| `/kb/*` | CRUD | Knowledge Base |

## Validación de la Documentación Agno

### 1. ¿Workflows soportan Steps con funciones Python puras?
**SÍ** — `Step(name="...", executor=función)` donde la función recibe `StepInput` y retorna `StepOutput`. Verificado con agno 2.5.6.

### 2. ¿MCPTools conecta a SSE existente?
**SÍ** — `MCPTools(url="http://host:8000/sse", transport="sse")`. Async-only (requiere `await agent.arun()`). SSE deprecated, pero funciona.

### 3. ¿PostgresDb funciona con Cloud SQL?
**SÍ** — `PostgresDb(db_url="postgresql+psycopg://user:pass@IP:5432/db")`. Compatible con Cloud SQL Auth Proxy en `127.0.0.1`.

### 4. ¿Router/Condition permiten skip selectivo?
**SÍ** — `Condition(evaluator=fn, steps=[...], else_steps=[...])` para branching. `Router(selector=fn, choices=[...])` para routing.

### 5. ¿AgentOS expone endpoints automáticamente?
**SÍ** — `AgentOS(agents=[...])` expone `/agents/*/runs`, `/sessions`, `/memories`, `/knowledge`, `/docs` automáticamente.

## Costos por Cotización

| Componente | Costo |
|-----------|-------|
| Classify (regex) | $0.00 |
| Parse (regex) | $0.00 |
| SRE (math) | $0.00 |
| BOM (math) | $0.00 |
| Pricing (lookup) | $0.00 |
| Validate (rules) | $0.00 |
| LLM Respond (~500 tokens) | ~$0.02 |
| **Total** | **~$0.02** |

## Bugs Corregidos (FASE 0)

1. **BOM wall dimensions swap** — Paneles de pared ahora usan `length_m` para panel count
2. **Pricing sub_familia** — Ahora filtra por sub_familia (EPS/PIR/3G)
3. **Hardcoded passwords** — Eliminados `mywolfykey123XYZ` defaults, usa `hmac.compare_digest`
4. **CORS wildcard** — Leído de `CORS_ALLOWED_ORIGINS` env var
5. **_load_catalog** — Usa `_get_gcs_bucket()` en vez de `storage_client` inexistente
6. **set_cotizacion_url** — Corregida indentación que causaba dead code
7. **Terraform** — `deletion_protection = true`
8. **.gitignore** — Agregados `*.tfstate*`, `*.tfvars`, `.terraform/`
