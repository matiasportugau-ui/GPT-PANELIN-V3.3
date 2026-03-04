# Panelin → Agno Migration Guide

## Arquitectura implementada

```
Usuario → Agno Agent (backend posee el agente)
         ↓
Backend controla el razonamiento
Agno Workflow (7 Steps determinísticos + 1 Agent LLM)
         ↓
Pipeline explícito, no decidido por LLM
PostgresDb (Cloud SQL) → Memoria conversacional
MCPTools → 18 tools existentes
```

## Estado de la migración

### ✅ FASE 0: Critical Bug Fixes (COMPLETO)

| Bug | Archivo | Fix |
|-----|---------|-----|
| BOM wall dimensions swap | `panelin_v4/engine/bom_engine.py:256-260` | `width_m, length_m` swapped (horizontal → U-profiles, vertical → sealant) |
| Pricing sub_familia ignored | `panelin_v4/engine/pricing_engine.py:165` | Added `sub_match` check alongside `familia_match` |
| CORS allow_origins=["*"] | `wolf_api/main.py:35` | Reads from `CORS_ORIGINS` env var |
| "mywolfy" default passwords | `wolf_api/kb_auth.py`, `mcp/handlers/wolf_kb_write.py`, `mcp/handlers/file_ops.py` | All empty defaults → 503 if not configured |
| pdf_cotizacion.py syntax | `wolf_api/pdf_cotizacion.py` | Fixed indentation of `generate_pdf_bytes` body and `preview_pdf` |
| sheet_mover.py indentation | `wolf_api/sheet_mover.py` | Full rewrite with correct indentation + hmac timing-safe comparison |
| .gitignore terraform state | `.gitignore` | Added `*.tfstate*`, `terraform.tfvars`, `*.auto.tfvars` |

### ✅ FASE 1: Core Domain Layer (COMPLETO)

| File | Purpose |
|------|---------|
| `src/core/config.py` | pydantic-settings, single source of truth for all env vars |
| `src/quotation/service.py` | QuotationService façade over panelin_v4 engine |
| `src/quotation/tools.py` | Agno-compatible tool functions (cotizar_panel, calcular_bom, etc.) |

### ✅ FASE 2: Agno Agent + Workflow (COMPLETO)

| File | Purpose |
|------|---------|
| `src/agent/workflow.py` | PanelinWorkflow — 7 deterministic steps + 1 LLM respond step |
| `src/agent/panelin.py` | Conversational Agent with PostgresDb + MCPTools |
| `src/app.py` | FastAPI app exposing /v4/* endpoints |

Pipeline steps:
1. `classify` — Regex classifier (0 LLM, $0.00)
2. `parse` — Free-text → QuoteRequest (0 LLM, $0.00)
3. `sre` — Structural Risk Engine score (0 LLM, $0.00)
4. `bom_router` — Conditional: skips BOM for accessories_only ($0.00)
5. `bom` — Bill of Materials (0 LLM, $0.00)
6. `pricing` — KB price lookup, NEVER invents ($0.00)
7. `validate` — 4-layer validation ($0.00)
8. `respond` — GPT-4o format in Spanish (~$0.02)

**Total cost per quotation: ~$0.02**

### ✅ FASE 3: Integration Layer (COMPLETO)

- Wolf API legacy routes preserved (backwards compatible)
- `src/tests/test_agno_integration.py` — 28 integration tests (all passing)
- All existing 34 engine tests still passing

### 🔲 FASE 4: AgentOS Production (PENDIENTE)

- `Dockerfile.agno` — Production Dockerfile for Cloud Run (ready to build)
- JWT auth + RBAC — Requires AgentOS license
- Distributed tracing — OpenTelemetry → PostgreSQL
- Cloud Run deployment — See deployment steps below

### 🔲 FASE 5: Advanced (FUTURO)

- JSONKnowledgeBase + PgVector for semantic product search
- Memory v2 for long-term client memory
- Output Guardrails for price validation against KB
- HITL for formal quotation approval
- Multi-channel: WhatsApp, Telegram

## Test Results

```
panelin_v4/tests/test_engine.py  — 34/34 tests passing ✅
src/tests/test_agno_integration.py — 28/28 tests passing ✅
Total: 62/62 tests passing ✅
```

## Deployment — Google Cloud Run

### Pre-requisites

```bash
# Required env vars in Cloud Run
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
WOLF_API_KEY=<strong-random-key>
KB_WRITE_PASSWORD=<strong-random-password>
WOLF_KB_WRITE_PASSWORD=<strong-random-password>
CORS_ORIGINS=https://yourdomain.com
MCP_SERVER_URL=http://localhost:8000
```

### Build and Deploy

```bash
# Build production image
docker build -f Dockerfile.agno -t gcr.io/PROJECT_ID/panelin-v4:latest .

# Push to GCR
docker push gcr.io/PROJECT_ID/panelin-v4:latest

# Deploy to Cloud Run
gcloud run deploy panelin-v4 \
  --image gcr.io/PROJECT_ID/panelin-v4:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --set-env-vars DATABASE_URL=$DATABASE_URL \
  --set-env-vars WOLF_API_KEY=$WOLF_API_KEY \
  --set-env-vars KB_WRITE_PASSWORD=$KB_WRITE_PASSWORD \
  --set-env-vars WOLF_KB_WRITE_PASSWORD=$WOLF_KB_WRITE_PASSWORD \
  --set-env-vars CORS_ORIGINS="https://yourdomain.com" \
  --set-env-vars ENVIRONMENT=production
```

### Local Development

```bash
# Install dependencies
pip install -r requirements-agno.txt

# Set environment
export OPENAI_API_KEY=sk-...
export DATABASE_URL=postgresql+psycopg://localhost/panelin

# Run
python -m uvicorn src.app:app --reload --port 8080
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v4/health` | GET | Health check |
| `/v4/chat` | POST | Conversational agent (session memory) |
| `/v4/quote` | POST | Direct workflow execution (structured result) |
| `/v4/quick-quote` | POST | Engine only, no LLM, $0.00 |
| `/v4/batch-quote` | POST | Batch processing, no LLM |
| `/v4/price/{familia}/{sub}/{espesor}` | GET | Price lookup from KB |
| `/v4/autoportancia/{familia}/{sub}/{espesor}/{luz}` | GET | Structural verification |
| `/wolf/*` | * | Wolf API legacy routes (preserved) |
| `/docs` | GET | Swagger UI |

## Agno API Summary (verified v2.5.6)

```python
# Workflow with Steps
from agno.workflow.workflow import Workflow, Router
from agno.workflow.step import Step, StepInput, StepOutput

workflow = Workflow(
    name="panelin",
    steps=[
        Step(name="step1", executor=my_fn),           # Python function, $0.00
        Router(name="router", choices=[step2], selector=select_fn),  # Conditional
        Step(name="step3", agent=my_agent),           # LLM step, ~$0.02
    ]
)
result = workflow.run(input="User message")
# Access step outputs:
# result.step_results — list of StepOutput objects
# step_output.content — the step's output (any type)
# For Router: step_output.steps[0].content — inner step's output

# Agent with PostgreSQL memory
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat

db = PostgresDb(
    db_url="postgresql+psycopg://user:pass@host/db",
    session_table="panelin_sessions",
)
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    add_history_to_context=True,
    num_history_runs=10,
)

# MCPTools for SSE transport
from agno.tools.mcp import MCPTools
async with MCPTools(url="http://localhost:8000/sse", transport="sse") as mcp:
    agent = Agent(tools=[mcp, ...])
```

## Architecture Decision Log

### Why Agno Workflow instead of raw LLM orchestration?

| Aspect | Before (Custom GPT) | After (Agno Workflow) |
|--------|---------------------|----------------------|
| Control | OpenAI decides everything | Backend controls all pipeline steps |
| Cost | ~$0.10-0.20 per quote (LLM at every step) | ~$0.02 per quote (LLM only for formatting) |
| Observability | Black box | Full step-by-step tracing |
| Memory | Stateless (each HTTP request fresh) | PostgresDb persistent sessions |
| Model swap | Tied to OpenAI | Swap GPT-4o ↔ Claude ↔ Gemini in config |
| Vendor lock | 100% OpenAI | 0% lock-in |

### Why StepOutput.steps for Router access?

When a step runs inside an Agno Router, its result appears in subsequent steps as:
- `prev_outputs["bom_router"]` → Router's StepOutput
- `prev_outputs["bom_router"].steps[0].content` → Inner step's content

This is the correct pattern for accessing Router-nested step results.

### Why `geometry.length_m` and not `QuoteRequest.length_m`?

The panelin_v4 QuoteRequest stores dimensions inside `geometry: ProjectGeometry`:
- `req.geometry.length_m` — panel span / wall height
- `req.geometry.width_m` — panel count direction
- `req.geometry.panel_lengths` — explicit panel lengths for cut optimization

The workflow pipeline flattens these to dict keys for easier cross-step access.
