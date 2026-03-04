# Panelin → Agno Migration Guide

Arquitectura agentic con Agno Framework para el sistema de cotizaciones BMC Uruguay.

---

## Estructura del Proyecto Post-Migración

```
src/
├── core/
│   └── config.py              # Configuración centralizada (pydantic-settings)
├── quotation/
│   ├── service.py             # QuotationService (wrapper del engine v4)
│   └── tools.py               # Agno @tool wrappers (domain functions)
├── agent/
│   ├── workflow.py            # Agno Workflow (pipeline determinístico)
│   ├── panelin.py             # Agente conversacional principal
│   ├── guardrails.py          # Output validation (no inventar precios)
│   ├── pdf_tool.py            # PDF generation como Agno tool
│   ├── knowledge.py           # Fase 5: Knowledge Base semántica
│   └── memory.py              # Fase 5: Long-term memory
├── tests/
│   └── test_agno_integration.py  # 23 integration tests
└── app.py                     # FastAPI app (legacy + v2 routes)
```

---

## Cambios por Fase

### FASE 0: Bugs Críticos Corregidos ✅

| Bug | Archivo | Fix |
|-----|---------|-----|
| BOM wall dimensions swap | `panelin_v4/engine/bom_engine.py:256-260` | Swapped `length_m`/`width_m` en `_add_wall_accessories()` |
| Pricing ignora sub_familia | `panelin_v4/engine/pricing_engine.py:165` | Agregado check `norm_sub in sku or norm_sub in name` |
| Default password "mywolfy" | `wolf_api/kb_auth.py`, `mcp/handlers/*.py` | Default vacío `""` — falla explícitamente |
| CORS allow_origins=["*"] | `wolf_api/main.py:33` | Lee `CORS_ORIGINS` del environment |
| Terraform deletion_protection=false | `terraform/main.tf:119` | Cambiado a `true` |
| .gitignore sin terraform state | `.gitignore` | Agregado `*.tfstate*`, `*.tfvars` |

### FASE 1: Core Domain Layer ✅

- **`src/core/config.py`**: `PanelinSettings` — pydantic-settings, fuente única de verdad
- **`src/quotation/service.py`**: `QuotationService` — wrapper del pipeline v4
- **`src/quotation/tools.py`**: 6 domain tools para el agente

### FASE 2: Agno Agent + Workflow ✅

- **`src/agent/workflow.py`**: `build_panelin_workflow()` con 3 steps + Router
  - `step_classify` — función Python pura ($0.00)
  - Router → full_pipeline o accessories_branch
  - `step_pipeline` — ejecuta `process_quotation()` ($0.00)
  - `step_respond` — Agente LLM formatea respuesta (~$0.02)
- **`src/agent/panelin.py`**: `build_panelin_agent()` — agente conversacional
  - Historial conversacional via `add_history_to_context=True`
  - Persistencia en PostgreSQL via `PostgresDb`
  - MCPTools para las 18 tools del servidor MCP existente

### FASE 3: Integration Layer ✅

- **`src/app.py`**: FastAPI app con rutas legacy preservadas + rutas `/v2/*`
- **`src/agent/pdf_tool.py`**: PDF generation como Agno tool
- **`src/agent/guardrails.py`**: Output validation

### FASE 4: Production Config ✅

- **`Dockerfile.agno`**: Multi-stage Docker para Cloud Run
- **`requirements-agno.txt`**: Dependencias Agno

### FASE 5: Advanced (pendiente activar) 📋

- **`src/agent/knowledge.py`**: JSONKnowledgeBase + PgVector — activar con `USE_KNOWLEDGE_BASE=true`
- **`src/agent/memory.py`**: Long-term memory — activar con `USE_LONG_TERM_MEMORY=true`

---

## Variables de Entorno Requeridas

```bash
# LLM
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini          # Recomendado para costo (~$0.02/cotización)

# PostgreSQL (Cloud SQL)
DATABASE_URL=postgresql+psycopg://user:pass@/panelin?host=/cloudsql/PROJECT:REGION:INSTANCE

# CORS (separado por comas, vacío = solo desarrollo local)
CORS_ORIGINS=https://bmcuruguay.com.uy,https://app.bmcuruguay.com.uy

# Wolf API (legado)
WOLF_API_KEY=<tu-api-key-segura>
KB_WRITE_PASSWORD=<password-segura>  # Nunca vacío en producción

# MCP Server
MCP_SERVER_URL=http://mcp-service:8000/sse

# Google Cloud
KB_GCS_BUCKET=panelin-kb-prod
SHEETS_SPREADSHEET_ID=1...
```

---

## Nuevas Rutas API

```
GET  /v2/health                  # Health check Agno
POST /v2/chat                    # Chat con agente (Workflow determinístico)
POST /v2/quote                   # Cotización directa (sin LLM, < 1ms)
GET  /v2/session/{session_id}    # Historial de sesión
```

### Ejemplo: POST /v2/chat

```json
{
  "message": "Necesito cotizar un techo de ISODEC EPS 100mm, 10 metros por 7",
  "session_id": "session_uuid_aqui",
  "user_id": "cliente@email.com",
  "mode": "pre_cotizacion",
  "client_name": "Juan García",
  "use_workflow": true
}
```

### Ejemplo: POST /v2/quote (directo, sin LLM)

```json
{
  "text": "ISODEC EPS 100mm techo 10x7 metros",
  "mode": "pre_cotizacion"
}
```

---

## Deployment en Cloud Run

```bash
# 1. Build y push imagen
docker build -f Dockerfile.agno -t gcr.io/PROJECT/panelin-agno:latest .
docker push gcr.io/PROJECT/panelin-agno:latest

# 2. Deploy en Cloud Run
gcloud run deploy panelin-agno \
  --image gcr.io/PROJECT/panelin-agno:latest \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars="OPENAI_MODEL=gpt-4o-mini" \
  --set-secrets="OPENAI_API_KEY=openai-key:latest,WOLF_API_KEY=wolf-api-key:latest,DATABASE_URL=db-url:latest"
```

---

## Tests

```bash
# Solo engine v4 (34 tests, sin deps externas)
python3 -m pytest panelin_v4/tests/ -v

# Integración Agno (23 tests, sin LLM)
PYTHONPATH=/workspace python3 -m pytest src/tests/ -v

# Todos (57 tests)
PYTHONPATH=/workspace python3 -m pytest panelin_v4/tests/ src/tests/ -v
```

---

## Costo por Cotización

| Step | LLM | Costo estimado |
|------|-----|----------------|
| classify | No (regex) | $0.00 |
| pipeline (parse→SRE→BOM→pricing→validate) | No | $0.00 |
| respond | Sí (gpt-4o-mini) | ~$0.02 |
| **TOTAL** | | **~$0.02** |

Comparado con Custom GPT: ~$0.05-0.15 por interacción (OpenAI controla todo).

---

## Nota: Conflicto de Namespace `mcp`

El directorio local `/workspace/mcp/` crea un conflicto con el paquete instalado `mcp`.
**En producción (Docker)**: no hay conflicto — el `Dockerfile.agno` estructura el PYTHONPATH correctamente.
**En desarrollo local**: correr tests con `PYTHONPATH=/workspace python3 -m pytest src/tests/` desde fuera del workspace root, o usar el Dockerfile.

Para los tests de integración Agno, el import de `MCPTools` se hace lazy (solo en producción con `use_mcp=True`).
