# Panelin + Agno en Cloud Run (guia rapida)

## 1) Build de imagen

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/panelin-agentos:latest -f Dockerfile.agentos .
```

## 2) Variables de entorno minimas

```bash
OPENAI_API_KEY=...
WOLF_API_KEY=...
WOLF_KB_WRITE_PASSWORD=...
CORS_ALLOW_ORIGINS=https://chat.openai.com,https://tu-frontend.com
```

### PostgreSQL / Cloud SQL

Opcion A (recomendada, socket Unix Cloud Run):

```bash
CLOUDSQL_CONNECTION_NAME=proyecto:region:instancia
DB_USER=postgres
DB_PASSWORD=...
DB_NAME=app_database
```

El DSN resultante usado por la app:

```text
postgresql+psycopg://USER:PASSWORD@/DB_NAME?host=/cloudsql/PROJECT:REGION:INSTANCE
```

Opcion B (DSN directo):

```bash
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME
```

## 3) Deploy Cloud Run

```bash
gcloud run deploy panelin-agentos \
  --image gcr.io/$PROJECT_ID/panelin-agentos:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances "$CLOUDSQL_CONNECTION_NAME" \
  --set-env-vars "MODEL_PROVIDER=openai,OPENAI_MODEL=gpt-4o-mini,MCP_SSE_URL=http://127.0.0.1:8000/sse"
```

## 4) Endpoints automáticos de AgentOS

Con `src.app:app`, AgentOS expone automáticamente (ademas de rutas Wolf API):

- `GET /agents`
- `POST /agents/{agent_id}/runs`
- `GET /workflows`
- `POST /workflows/{workflow_id}/runs`
- `GET/POST /sessions`
- `GET /traces`, `POST /traces/search`
- `GET /metrics`
- `GET /docs`, `GET /openapi.json`

## 5) Verificaciones post deploy

```bash
curl "$URL/health"
curl "$URL/agents"
curl -X POST "$URL/workflows/panelin-workflow-v4/runs" -d 'input={"text":"isodec 100mm techo 7x10"}'
```
