# Panelin v5.0 — Guía de Migración a Agno Framework

## Resumen de la Arquitectura

### Antes (Pasiva)
```
Usuario → ChatGPT Custom GPT → OpenAI decide TODO → Wolf API (pasivo)
```

### Después (Agentic)
```
Usuario → Agno Agent (backend controla) → Workflow determinístico → PostgreSQL
```

## Estructura de Archivos Nuevos

```
src/
├── core/
│   └── config.py              # Configuración centralizada (pydantic-settings)
├── quotation/
│   ├── service.py             # Wrapper del engine v4 (sin modificar el engine)
│   └── tools.py               # Funciones-herramienta para el agente Agno
├── agent/
│   ├── workflow.py            # Workflow con 7 steps determinísticos + 1 LLM
│   └── panelin.py             # Agente conversacional Panelin
├── integrations/
│   ├── mcp_bridge.py          # Conexión MCP via SSE (25 tools existentes)
│   ├── sheets.py              # Google Sheets como herramientas del agente
│   └── pdf.py                 # Generación de PDF como herramienta del agente
├── knowledge/
│   └── product_kb.py          # Knowledge base con PgVector
├── guardrails/
│   └── price_validation.py    # Prevención de alucinación de precios
└── app.py                     # Entry point con AgentOS

tests/
├── test_quotation_service.py  # 17 tests del service layer
├── test_workflow.py           # 13 tests de los workflow steps
└── test_guardrails.py         # 5 tests del guardrail de precios
```

## Bugs Corregidos (FASE 0)

1. **BOM wall dimensions swap**: Corregido cálculo de panel_count para paredes
   (usa `length_m` en vez de `width_m` para determinar cantidad de paneles)
2. **Pricing sub_familia match**: Agregada validación de sub_familia al buscar
   precios en `bromyros_pricing_master.json`
3. **Passwords hardcodeados**: Eliminados todos los defaults `"mywolfy"` y
   `"mywolfykey123XYZ"` — ahora requieren variables de entorno
4. **CORS wildcard**: `allow_origins=["*"]` reemplazado por lectura de
   `CORS_ALLOWED_ORIGINS` del entorno
5. **Import roto**: `pdf_drive_integration` fallback graceful cuando el módulo
   no existe
6. **.gitignore**: Agregados `*.tfstate*`, `*.tfvars`, `.terraform/`

## Validación contra Documentación Agno

### ¿El API de Workflows soporta Steps con funciones Python puras?
**SÍ.** `Step(executor=mi_funcion)` donde la función recibe `StepInput` y
retorna `StepOutput`. Verificado en Agno 2.5.6.

### ¿MCPTools puede conectarse a un servidor MCP SSE existente?
**SÍ.** `MCPTools(url="http://host:8000/sse", transport="sse")`.
Requiere `pip install mcp`.

### ¿PostgresDb funciona con Cloud SQL?
**SÍ.** Connection string: `postgresql+psycopg://user:pass@/db?host=/cloudsql/PROJECT:REGION:INSTANCE`
Requiere `pip install psycopg[binary]`.

### ¿Router/Conditional steps permiten skip selectivo de pasos?
**SÍ.** `Condition(evaluator=bool_func, steps=[...])` ejecuta los steps solo
si el evaluador retorna `True`.

### ¿AgentOS expone endpoints automáticamente?
**SÍ.** AgentOS auto-genera:
- `POST /v1/agents/{agent_id}/runs` — Ejecutar el agente
- `POST /v1/workflows/{workflow_id}/runs` — Ejecutar el workflow
- Health checks, session management, tracing

## Deployment

### Desarrollo Local
```bash
# 1. Copiar .env
cp .env.example .env
# Configurar: OPENAI_API_KEY, DATABASE_URL, MCP_SERVER_URL

# 2. Iniciar servicios
docker compose -f docker-compose.agno.yml up -d

# 3. Verificar
curl http://localhost:8080/health
```

### Cloud Run
```bash
# 1. Build
docker build -f Dockerfile.agno -t panelin-agno .

# 2. Tag y push
docker tag panelin-agno gcr.io/PROJECT/panelin-agno
docker push gcr.io/PROJECT/panelin-agno

# 3. Deploy
gcloud run deploy panelin-api \
  --image gcr.io/PROJECT/panelin-agno \
  --port 8080 \
  --set-env-vars "OPENAI_API_KEY=...,DATABASE_URL=...,CORS_ALLOWED_ORIGINS=..." \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE \
  --memory 1Gi \
  --min-instances 1
```

### Variables de Entorno Requeridas
| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key de OpenAI | `sk-...` |
| `DATABASE_URL` | PostgreSQL Cloud SQL | `postgresql+psycopg://...` |
| `WOLF_API_KEY` | API key para Wolf API | (generar) |
| `CORS_ALLOWED_ORIGINS` | Orígenes CORS permitidos | `https://app.example.com` |
| `MCP_SERVER_URL` | URL del servidor MCP | `http://mcp:8000/sse` |

## Costo por Cotización
- Steps 1-7 (Python puro): **$0.00**
- Step 8 (LLM formatting): **~$0.02** (gpt-4o-mini)
- **Total: ~$0.02 por cotización**

## Tests
```bash
# Todos los tests (69 tests)
python -m pytest panelin_v4/tests/ tests/ -v

# Solo engine (34 tests)
python -m pytest panelin_v4/tests/test_engine.py -v

# Solo migración (35 tests)
python -m pytest tests/ -v
```
