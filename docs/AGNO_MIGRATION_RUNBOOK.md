# Panelin -> Agno Migration Runbook

## 1) Arquitectura objetivo implementada

- **AgentOS entrypoint**: `src/app.py`
- **Agente conversacional**: `src/agent/panelin.py`
- **Workflow determinístico**: `src/agent/workflow.py`
- **Servicio de dominio (engine v4)**: `src/quotation/service.py`
- **Tools Agno**: `src/quotation/tools.py`
- **Config centralizada**: `src/core/config.py`

La lógica determinística de `panelin_v4/` se mantiene sin cambios funcionales de diseño.

---

## 2) Validaciones de API real de Agno usadas

- Workflow con pasos Python puros:
  - `Step(executor=...)`
  - Firma compatible con `StepInput`, opcional `run_context` y `session_state`.
- Routing condicional:
  - `Router(choices=[...], selector=...)`
  - Selector puede recibir `session_state` y `step_choices`.
- Sesiones persistentes:
  - `Agent(db=PostgresDb(...))`
  - `Workflow(db=PostgresDb(...))`
- MCP SSE:
  - `MCPTools(transport="sse", server_params=SSEClientParams(url=...))`
- AgentOS endpoints automáticos:
  - `/agents/{agent_id}/runs`
  - `/workflows/{workflow_id}/runs`
  - `/sessions`
  - + endpoints de memories/knowledge/evals/metrics/traces.

---

## 3) Variables de entorno mínimas

```bash
# Core
PANELIN_USE_IN_MEMORY_DB=false
PANELIN_DB_USER=postgres
PANELIN_DB_PASSWORD=...
PANELIN_DB_NAME=app_database
PANELIN_CLOUD_SQL_CONNECTION_NAME=project:region:instance

# Models
PANELIN_MODEL_PROVIDER=openai
PANELIN_OPENAI_MODEL_ID=gpt-4o-mini
OPENAI_API_KEY=...

# MCP
PANELIN_ENABLE_MCP_TOOLS=true
PANELIN_MCP_TRANSPORT=sse
PANELIN_MCP_SSE_URL=http://panelin-mcp:8000/sse

# CORS/API
PANELIN_CORS_ALLOW_ORIGINS=https://chatgpt.com,https://chat.openai.com
WOLF_CORS_ALLOW_ORIGINS=https://chatgpt.com,https://chat.openai.com
WOLF_API_KEY=...
```

> Connection string Cloud SQL (si usás URL explícita):
> `postgresql+psycopg://USER:PASSWORD@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE`

---

## 4) Run local

```bash
python3 -m pip install -r requirements-agentos.txt
uvicorn src.app:app --host 0.0.0.0 --port 8080
```

Smoke checks:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/workflows
curl http://localhost:8080/agents
```

---

## 5) Tests recomendados

```bash
# Motor determinístico
python3 -m pytest panelin_v4/tests/test_engine.py -q

# Seguridad MCP
python3 -m pytest mcp/tests/test_wolf_kb_write.py mcp/tests/test_file_ops.py mcp/tests/test_kb_interaction.py -q

# Integración Agno
python3 -m pytest tests/test_panelin_agentos_integration.py -q
```

---

## 6) Deploy Cloud Run

1. Configurar secretos:
   - `panelin-db-password`
   - `openai-api-key`
   - `wolf-api-key`
2. Ajustar substitutions en `cloudbuild.yaml`.
3. Ejecutar Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml
```

4. Verificar endpoints:
   - Legacy Wolf: `/calculate_quote`, `/find_products`, `/sheets/*`, `/kb/*`
   - AgentOS: `/agents/{agent_id}/runs`, `/workflows/{workflow_id}/runs`, `/sessions`

---

## 7) Nota sobre costos

- Pipeline determinístico (classify/parse/SRE/BOM/pricing/validate/SAI): **sin costo LLM**.
- LLM usado sólo para respuesta final (step `format_user_response_llm`) cuando está habilitado.
- Para tests/entornos sin clave: fallback a respuesta determinística (`PANELIN_ENABLE_LLM_RESPONSE=false`).
