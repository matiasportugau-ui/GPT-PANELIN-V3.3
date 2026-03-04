# Panelin -> Agno: arquitectura de migracion (validada)

## Estado actual

- Engine v4 (`panelin_v4/engine`) se conserva como capa de dominio deterministica.
- Wolf API y rutas legacy siguen operativas.
- Se agrega capa agentic en `src/` con Agno.

## Fase 0 (aplicada)

- Fix BOM paredes (swap largo/alto) en `panelin_v4/engine/bom_engine.py`.
- Fix pricing por `sub_familia` + filtro de tipo panel en `panelin_v4/engine/pricing_engine.py`.
- Endurecimiento seguridad:
  - sin default `"mywolfy"` en handlers de escritura,
  - `hmac.compare_digest` para password checks.
- CORS por `CORS_ALLOW_ORIGINS` en `wolf_api/main.py`.
- `.gitignore` actualizado (`*.tfstate*`, `*.tfvars*`).
- Terraform `deletion_protection = true`.

## Fase 1-2 (implementada en `src/`)

### Config

- `src/core/config.py`
  - `pydantic-settings` como source of truth.
  - DSN PostgreSQL/Cloud SQL:
    - `DATABASE_URL` directo, o
    - `postgresql+psycopg://USER:PASS@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE`.

### Dominio

- `src/quotation/service.py`: servicio que envuelve classifier/parser/SRE/BOM/pricing/validation/SAI.
- `src/quotation/tools.py`: tools Agno (`@tool`) para quote, validate, SAI y batch.

### Workflow deterministico

- `src/agent/workflow.py`
  - Steps con `executor=function`:
    1. classify
    2. parse
    3. apply defaults
    4. sre
    5. bom/pricing (via router)
    6. validation + output
    7. sai
  - Router condicional:
    - `accessories_only` salta BOM estructural.
  - Paso LLM opcional para formatear respuesta final.

### Agente conversacional

- `src/agent/panelin.py`
  - `Agent` con:
    - tools de dominio,
    - tools Wolf API,
    - MCPTools (SSE),
    - knowledge (filesystem o pgvector),
    - guardrail de salida anti-precios no validados.
  - `PostgresDb` como storage persistente de sesiones/memoria/trazas.

### App / AgentOS

- `src/app.py`
  - monta AgentOS sobre FastAPI legado (`wolf_api.main.app`).
  - preserva `/calculate_quote`, `/find_products`, `/sheets/*`, `/kb/*`.
  - expone endpoints automaticos de AgentOS para agents/workflows/sessions/traces.

## Fase 3 (integracion)

- `src/integration/wolf_tools.py`: wrappers de endpoints Wolf API como tools Agno.

## Fase 4 (deploy)

- `Dockerfile.agentos`.
- `docs/agno_cloud_run_deploy.md` con pasos Cloud Run + Cloud SQL.

## Fase 5 (preparado)

- Knowledge vectorial opcional con `PgVector` + `OpenAIEmbedder`.
- JWT habilitable por config (`agentos_authorization` + `AuthorizationConfig`).

## Validacion de APIs Agno usadas

- Workflows con funciones Python puras: `Step(executor=...)`.
- Router/Conditional para saltos selectivos: `Router(choices=..., selector=...)`, `Condition(...)`.
- MCP SSE: `MCPTools(transport="sse", server_params=SSEClientParams(url=...))`.
- Persistencia Postgres: `PostgresDb(db_url=...)` en `Agent`, `Workflow`, `AgentOS`.
- AgentOS endpoints automáticos: `/agents`, `/workflows`, `/sessions`, `/traces`, `/metrics`, etc.
