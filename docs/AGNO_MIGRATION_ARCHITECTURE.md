# Migración Panelin → Agno (Arquitectura Implementada)

## 1) Resumen ejecutivo

Se implementó una capa nueva `src/` para migrar Panelin desde una arquitectura pasiva a una arquitectura agentic:

- **Workflow determinístico explícito** (sin LLM en el core):  
  `classify -> parse -> sre -> (router bom/pricing o skip) -> validate -> sai`
- **1 paso LLM opcional** para redacción final (`format_response`).
- **Agente conversacional** con tools de dominio + integración MCP.
- **Persistencia de sesiones** con `PostgresDb` (Cloud SQL compatible) o fallback SQLite.
- **AgentOS** como runtime HTTP con endpoints automáticos + capa de compatibilidad de rutas legacy.

> El motor `panelin_v4/` se mantiene intacto como lógica de dominio principal.

---

## 2) Validación contra APIs reales de Agno (versión instalada)

### 2.1 Workflows con funciones Python puras

**Sí, soportado.**  
API validada:

- `from agno.workflow import Step`
- `Step(name="...", executor=mi_funcion_python)`
- Firma esperada de función: `def fn(step_input: StepInput, ...) -> StepOutput`

Implementado en:
- `src/agent/workflow.py` (`classify_step`, `parse_step`, `sre_step`, `bom_step`, `pricing_step`, `validate_step`, `sai_step`)

### 2.2 Router/Conditional para skip selectivo

**Sí, soportado.**

- `from agno.workflow import Router, Steps, Step`
- Selector retorna nombre de paso (`str`) o Step(s)
- Se puede elegir rama “skip” en runtime

Implementado:
- `bom_pricing_router` en `src/agent/workflow.py`
- Si `request_type == accessories_only`, ejecuta `skip_bom_pricing`

### 2.3 MCP SSE existente

**Sí, soportado.**  
Sintaxis validada (Agno 2.5.6):

```python
from agno.tools.mcp import MCPTools
from agno.tools.mcp.params import SSEClientParams

params = SSEClientParams(url="http://127.0.0.1:8000/sse", headers={...})
mcp_tools = MCPTools(transport="sse", server_params=params, timeout_seconds=15)
await mcp_tools.connect()
```

Implementado:
- `src/agent/panelin.py` (`_build_mcp_tools`, `startup`, `shutdown`)

### 2.4 PostgresStorage / Session storage / Cloud SQL

En esta versión de Agno, la clase pública usada en runtime es **`PostgresDb`** (no `PostgresStorage`).

Uso validado:

```python
from agno.db.postgres import PostgresDb
db = PostgresDb(db_url="postgresql+psycopg://user:pass@host:5432/db", db_schema="panelin")
agent = Agent(db=db)
workflow = Workflow(db=db)
```

Formato Cloud SQL (unix socket) soportado por configuración:

`postgresql+psycopg://USER:PASSWORD@/DB_NAME?host=/cloudsql/PROJECT:REGION:INSTANCE`

Implementado:
- `src/core/config.py` (`resolved_db_url`)
- `src/agent/panelin.py` (`_build_db`)

### 2.5 AgentOS endpoints automáticos

**Sí, AgentOS expone endpoints automáticamente.**  
Validado por introspección de `AgentOS.get_app().routes`.

Incluye (entre otros):
- `/agents`, `/agents/{id}`, `/agents/{id}/runs`, ...
- `/workflows`, `/workflows/{id}/runs`, ...
- `/sessions`, `/sessions/{id}`, ...
- `/traces`, `/metrics`, `/approvals`, `/knowledge`, ...

Implementado:
- `src/app.py` (instancia `AgentOS` con `agents=[runtime.agent]`, `workflows=[runtime.workflow]`)

---

## 3) Implementación por fases

## FASE 0 (hardening + bugs críticos)

Aplicado:
- Fix BOM muro (swap dimensiones): `panelin_v4/engine/bom_engine.py`
- Fix pricing por sub_familia: `panelin_v4/engine/pricing_engine.py`
- Passwords default removidos y comparación constante en handlers críticos:
  - `wolf_api/kb_auth.py`
  - `mcp/handlers/file_ops.py`
  - `mcp/handlers/wolf_kb_write.py`
  - `wolf_api/sheet_mover.py`
  - `wolf_api/pdf_cotizacion.py`
- CORS por entorno: `wolf_api/main.py` (`CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS`)
- Terraform:
  - `.gitignore` ignora `*.tfstate*`, `*.tfvars*`
  - `terraform/main.tf`: `deletion_protection = true`

Validación:
- `panelin_v4/tests/test_engine.py` → **34 passed**

## FASE 1 (core domain layer)

Nuevos archivos:
- `src/core/config.py`
- `src/quotation/service.py`
- `src/quotation/tools.py`
- `src/quotation/schemas.py`

## FASE 2 (agent + workflow)

Nuevos archivos:
- `src/agent/workflow.py`
- `src/agent/panelin.py`
- `src/agent/mcp_compat.py`

## FASE 3 (integration layer)

Implementado en:
- `src/app.py`:
  - Capa de compatibilidad legacy (`/calculate_quote`, `/find_products`, `/kb/*`, `/sheets/*`, `/api/*`)
  - Integración con AgentOS sobre misma app base.

## FASE 4 (AgentOS production baseline)

Implementado:
- `src/app.py`:
  - `AgentOS(...)`
  - JWT/RBAC configurable (`AGENTOS_AUTHORIZATION`, `JWT_VERIFICATION_KEYS`, etc.)
  - Tracing flag (`AGENTOS_TRACING`)

Pendiente recomendado:
- completar wiring de observabilidad externa (LangSmith/Langfuse) con OTLP.

## FASE 5 (avanzado)

Base preparada:
- `Settings` incluye flags para conocimiento/memoria.
- Falta activar carga de KB vectorial según políticas de costo/operación.

---

## 4) Docker + Cloud Run (guía paso a paso)

## 4.1 Variables mínimas

- `OPENAI_API_KEY` o `ANTHROPIC_API_KEY`
- `DATABASE_URL` **o** (`DB_CONNECTION_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)
- `WOLF_API_KEY` (si se usa auth API/MCP)
- `MCP_SSE_URL` (default: `http://127.0.0.1:8000/sse`)

## 4.2 Run local

```bash
python3 -m uvicorn src.app:app --host 0.0.0.0 --port 8080
```

## 4.3 Cloud Run (resumen)

1. Build container con entrypoint `src.app:app`
2. Deploy a Cloud Run puerto `8080`
3. Configurar secretos/env vars
4. Si Cloud SQL: montar conexión por `DB_CONNECTION_NAME` o `DATABASE_URL`
5. Verificar endpoints:
   - `/health`
   - `/agents`
   - `/workflows`
   - `/api/quote`

---

## 5) Tests de integración

Nuevo test:
- `tests/integration/test_panelin_agno_workflow.py`

Cobertura:
- ejecución workflow end-to-end
- rama `accessories_only` con skip BOM/pricing
- reuso de `session_id`

Comando:

```bash
python3 -m pytest tests/integration/test_panelin_agno_workflow.py -q
```

