# Panelin v5.0 — Guía de Migración a Agno Framework

## Arquitectura

```
Usuario → Agno Agent (backend posee el agente)
            ↓
    Backend controla el razonamiento
            ↓
    Agno Workflow (7 Steps determinísticos + 1 Agent LLM)
            ↓
    Pipeline explícito, no decidido por LLM
            ↓
    PostgresStorage (Cloud SQL) → Memoria conversacional
    MCPTools → 18 tools existentes
    PanelinTools → Engine v4 directo
```

### Antes vs Después

| Aspecto | v4 (Custom GPT) | v5 (Agno) |
|---------|-----------------|-----------|
| Control | OpenAI decide TODO | Backend controla pipeline |
| Memoria | Stateless (cada request independiente) | PostgresStorage persistente |
| Observabilidad | Caja negra de OpenAI | Tracing completo por step |
| Costo/cotización | ~$0.10 (múltiples tool calls) | ~$0.02-0.03 (solo understand+respond) |
| Vendor lock-in | 100% OpenAI | Swap: OpenAI/Claude/Gemini |
| Persistencia | Se pierden los resultados | PostgreSQL + GCS |
| Pipeline | LLM decide orden | 7 steps determinísticos |

## Estructura de Archivos

```
src/
├── __init__.py
├── app.py                          # FastAPI + Agno entry point
├── core/
│   ├── __init__.py
│   └── config.py                   # pydantic-settings, single source of truth
├── quotation/
│   ├── __init__.py
│   ├── service.py                  # QuotationService wrapping engine v4
│   └── tools.py                    # Agno @tool wrappers (PanelinTools)
├── agent/
│   ├── __init__.py
│   ├── panelin.py                  # Agno Agent conversacional
│   ├── workflow.py                 # Agno Workflow (7+1 steps)
│   └── memory.py                   # Memory v2 configuration
├── integrations/
│   ├── __init__.py
│   ├── sheets_tools.py             # Google Sheets CRM tools
│   ├── pdf_tools.py                # PDF generation tools
│   └── kb_tools.py                 # KB persistence tools
├── knowledge/
│   ├── __init__.py
│   └── product_kb.py               # JSONKnowledgeBase + PgVector
└── guardrails/
    ├── __init__.py
    └── price_guardrail.py           # Output guardrails (no inventar precios)
```

## Deployment

### Prerequisitos

1. **Python 3.11+**
2. **PostgreSQL 16** con extensión pgvector
3. **API Key** de OpenAI (o Anthropic/Google)
4. **Google Cloud** service account (para GCS y Sheets)

### Desarrollo Local

```bash
# 1. Clonar y configurar
cp .env.agno.example .env
# Editar .env con tus credenciales

# 2. Levantar con Docker Compose
docker compose -f docker-compose.agno.yml up -d

# 3. Verificar health
curl http://localhost:8080/health

# 4. Probar cotización
curl -X POST http://localhost:8080/api/quote \
  -H "Content-Type: application/json" \
  -d '{"text": "Isodec EPS 100mm / 6 paneles de 6.5mts / techo a metal"}'

# 5. Chat con el agente
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Necesito cotizar un techo de 10x7 con Isodec 100mm"}'
```

### Cloud Run (Producción)

```bash
# 1. Build Docker image
docker build -f Dockerfile.agno -t panelin-agno .

# 2. Tag y push a Artifact Registry
docker tag panelin-agno us-central1-docker.pkg.dev/PROJECT/cloud-run-repo/panelin-agno
docker push us-central1-docker.pkg.dev/PROJECT/cloud-run-repo/panelin-agno

# 3. Deploy a Cloud Run
gcloud run deploy panelin-api \
  --image us-central1-docker.pkg.dev/PROJECT/cloud-run-repo/panelin-agno \
  --region us-central1 \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "LLM_PROVIDER=openai" \
  --set-env-vars "LLM_MODEL_ID=gpt-4o" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest" \
  --set-secrets "DB_PASSWORD=db-secret:latest" \
  --set-env-vars "DB_HOST=/cloudsql/PROJECT:REGION:INSTANCE" \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE \
  --service-account cloud-run-service-account@PROJECT.iam.gserviceaccount.com
```

## Workflow Pipeline

El pipeline determinístico ejecuta 8 steps secuenciales:

| Step | Tipo | Costo | Función |
|------|------|-------|---------|
| 1. Understand | Agent (LLM) | ~$0.01 | Interpreta intención del usuario |
| 2. Classify | Python puro | $0.00 | Clasifica tipo + modo operación |
| 3. Parse | Python puro | $0.00 | Texto libre → QuoteRequest |
| 4. SRE | Python puro | $0.00 | Score de riesgo estructural |
| 5. BOM | Python puro | $0.00 | Bill of Materials |
| 6. Pricing | Python puro | $0.00 | Precios de KB (nunca inventa) |
| 7. Validate | Python puro | $0.00 | Validación 4 capas |
| 8. Respond | Agent (LLM) | ~$0.01 | Formato respuesta en español |

**Total por cotización: ~$0.02-0.03**

## MCP Integration

Conexión al servidor MCP existente (18 tools) via SSE:

```python
from agno.tools.mcp import MCPTools

async with MCPTools(
    transport="sse",
    url="http://localhost:8000/sse",
) as mcp_tools:
    agent = create_panelin_agent(mcp_tools=mcp_tools)
```

## PostgresStorage (Sesiones Persistentes)

```python
from agno.storage.postgres import PostgresStorage

storage = PostgresStorage(
    table_name="panelin_sessions",
    db_url="postgresql+psycopg://user:pass@host:5432/panelin",
)

agent = create_panelin_agent(storage=storage, session_id="client-123")
```

## Model Swapping

Cambiar proveedor de LLM sin modificar código:

```bash
# OpenAI (default)
LLM_PROVIDER=openai
LLM_MODEL_ID=gpt-4o

# Anthropic Claude
LLM_PROVIDER=anthropic
LLM_MODEL_ID=claude-sonnet-4-5

# Google Gemini
LLM_PROVIDER=google
LLM_MODEL_ID=gemini-2.0-flash
```

## Tests

```bash
# Tests del engine original (34 tests)
python -m pytest panelin_v4/tests/test_engine.py -v

# Tests de la nueva arquitectura (27 tests)
python -m pytest tests/ -v

# Todos los tests (61 tests)
python -m pytest panelin_v4/tests/ tests/ -v
```

## Validaciones contra Agno Docs

| Pregunta | Respuesta Verificada |
|----------|---------------------|
| ¿Workflows soporta Steps con funciones Python puras? | ✅ `Step(executor=my_function)` — function receives `StepInput`, returns `StepOutput` |
| ¿MCPTools conecta a SSE existente? | ✅ `MCPTools(transport="sse", url="http://host:8000/sse")` |
| ¿PostgresStorage funciona con Cloud SQL? | ✅ `db_url="postgresql+psycopg://user:pass@/db?host=/cloudsql/conn"` |
| ¿Router/Conditional steps permiten skip selectivo? | ✅ Condition con evaluator function, Router con selector function |
| ¿AgentOS expone endpoints automáticamente? | ✅ 50+ endpoints via `AgentOS(agents=[...])` |

## Bugs Corregidos (FASE 0)

1. **BOM dimensions swap**: `_add_wall_accessories` recibía `width_m` como `height_m`. Corregido swappeando argumentos en la llamada.
2. **Pricing sub_familia**: `_find_panel_price_m2` no filtraba por sub_familia (EPS vs PIR). Agregado matching de sub_familia.
3. **Hardcoded passwords**: Removidos defaults "mywolfy" y "mywolfykey123XYZ" en 5 archivos. Ahora usan string vacío como default (requiere env var).
4. **CORS wildcard**: `allow_origins=["*"]` reemplazado por `CORS_ALLOWED_ORIGINS` env var.
5. **Terraform state**: Agregados `*.tfstate*`, `*.tfvars`, `.terraform/` a `.gitignore`.
6. **Terraform deletion_protection**: Cambiado de `false` a `true`.
