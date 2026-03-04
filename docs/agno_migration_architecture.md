# Panelin → Agno: arquitectura validada e implementación

## 1) Validación contra APIs reales de Agno (instalado: `agno==2.5.6`)

### Workflows con funciones Python puras
Validado por introspección local:

- `from agno.workflow import Workflow`
- `from agno.workflow.step import Step, StepInput, StepOutput`

Firma relevante:

- `Step(..., executor: Callable[[StepInput], StepOutput], ...)`
- `Workflow(..., steps=[Step(...), ...])`

Conclusión: **sí soporta** pasos con funciones Python puras (sin LLM en el medio).

---

### Router/Conditional para saltar pasos
Validado por introspección local:

- `from agno.workflow.router import Router`
- `from agno.workflow.condition import Condition`

Firma relevante:

- `Router(choices=[...], selector=callable)`

Conclusión: **sí permite** routing condicional (ejemplo en `src/agent/workflow.py`: `bom_router` para saltar BOM en `accessories_only`).

---

### MCPTools con servidor MCP SSE existente
Validado por código fuente de Agno:

- `from agno.tools.mcp import MCPTools, SSEClientParams`
- `MCPTools(transport="sse", server_params=SSEClientParams(url="http://localhost:8000/sse"))`

Notas reales de versión:

- Agno marca SSE como deprecado y recomienda `streamable-http`.
- En este repo existe colisión de nombres: carpeta local `mcp/` vs paquete PyPI `mcp`.
  Se resolvió con workaround en `src/agent/panelin.py` (import aislado).

---

### Persistencia de sesiones con PostgreSQL / Cloud SQL
En esta versión de Agno, la clase operativa es:

- `from agno.db.postgres import PostgresDb`

No existe `agno.storage.postgres.PostgresStorage` en 2.5.6.

Formato de conexión soportado:

- TCP: `postgresql+psycopg://user:pass@host:5432/db`
- Cloud SQL socket: `postgresql+psycopg://user:pass@/db?host=/cloudsql/PROJECT:REGION:INSTANCE`

Implementado en `src/core/config.py` (`postgres_db_url` y `build_postgres_db()`).

---

### AgentOS endpoints automáticos
Validado levantando `AgentOS(...).get_app()` y listando rutas.

Incluye (entre otros):

- `/agents`, `/agents/{agent_id}`, `/agents/{agent_id}/runs`
- `/workflows`, `/workflows/{workflow_id}`, `/workflows/{workflow_id}/runs`
- `/sessions`, `/sessions/{session_id}`, `/sessions/{session_id}/runs`
- `/memories`, `/knowledge/*`, `/traces/*`, `/metrics`

Total observado en runtime local: **78 rutas**.

---

## 2) Implementación por fases (estado en este branch)

## Fase 0 — hardening crítico

Aplicado:

- `wolf_api/main.py`: CORS deja de usar `allow_origins=["*"]`, ahora lee `CORS_ALLOW_ORIGINS`.
- `mcp/handlers/file_ops.py`: se elimina default inseguro `mywolfy`, se exige env y `hmac.compare_digest`.
- `mcp/handlers/wolf_kb_write.py`: idem.
- `wolf_api/kb_auth.py`: idem.
- `wolf_api/pdf_cotizacion.py` y `wolf_api/sheet_mover.py`: sin default API key inseguro.
- `.gitignore`: agrega `*.tfstate*`, `*.tfvars`.
- `terraform/main.tf`: `deletion_protection = true`.

> Nota: `panelin_v4/` se preserva como motor determinístico.

## Fase 1 — core domain layer

Nuevos archivos:

- `src/core/config.py` — configuración central con `pydantic-settings`
- `src/quotation/service.py` — `QuotationService` para pipeline determinístico
- `src/quotation/tools.py` — wrappers `@tool` para dominio e integración

## Fase 2 — agent + workflow Agno

Nuevos archivos:

- `src/agent/workflow.py`
  - 7 pasos determinísticos: classify → parse → sre → bom(router) → pricing → validate → sai
  - 1 router condicional (`bom_router`)
  - 1 paso de respuesta LLM opcional (`respond_llm`) + fallback determinístico
- `src/agent/panelin.py`
  - `Agent` conversacional con tools de dominio + wrappers legacy + MCPTools
  - guardrail de salida para evitar precios sin evidencia de tools
  - integración de memoria/knowledge opcional

## Fase 3 — integration layer

Implementado en `src/quotation/tools.py`:

- Wrapper catálogo (`/find_products`)
- Wrapper Sheets (`/sheets/consultations`)
- Wrapper PDF (`/cotizaciones/generar_pdf`)

## Fase 4 — AgentOS production

Nuevos archivos:

- `src/app.py` — entrypoint AgentOS montado sobre app legacy (sin romper rutas existentes)

Ajustes de runtime:

- `Dockerfile.production` ahora arranca `uvicorn src.app:app`.
- instala dependencias Agno y copia `src/`.

## Fase 5 — advanced

Base de configuración preparada en `src/core/config.py`:

- flags de knowledge/memory/mcp/provider
- URL Cloud SQL y tabla pgvector

(ingesta semántica y memoria de largo plazo quedan listas para iteración posterior).
