# Guía de despliegue: Panelin Agno en Cloud Run

## 1. Prerrequisitos

- Proyecto GCP con Cloud Run y Cloud SQL habilitados.
- Instancia PostgreSQL ya existente (Cloud SQL).
- Secrets configurados para:
  - `OPENAI_API_KEY` (o `ANTHROPIC_API_KEY`)
  - `DB_PASSWORD`
  - `WOLF_API_KEY`
- MCP server disponible por SSE (actualmente puerto 8000).

## 2. Variables mínimas recomendadas

```bash
export PANELIN_MODEL_PROVIDER=openai
export OPENAI_MODEL_ID=gpt-4o-mini
export ENABLE_LLM_RESPONSE_STEP=true

export DB_CONNECTION_NAME="PROJECT:REGION:INSTANCE"
export DB_USER="postgres"
export DB_PASSWORD="***"
export DB_NAME="app_database"

export PANELIN_ENABLE_MCP_TOOLS=true
export PANELIN_MCP_TRANSPORT=sse
export PANELIN_MCP_SSE_URL="http://localhost:8000/sse"

export CORS_ALLOW_ORIGINS="https://tu-frontend.com"
```

## 3. Build local de imagen

```bash
docker build -f Dockerfile.production -t panelin-agno:latest .
```

## 4. Smoke test local

```bash
docker run --rm -p 8080:8080 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e DB_CONNECTION_NAME="$DB_CONNECTION_NAME" \
  -e DB_USER="$DB_USER" \
  -e DB_PASSWORD="$DB_PASSWORD" \
  -e DB_NAME="$DB_NAME" \
  panelin-agno:latest
```

Verificar:

- `GET /health` (legacy)
- `GET /agents` (AgentOS)
- `GET /workflows` (AgentOS)

## 5. Deploy a Cloud Run

```bash
gcloud run deploy panelin-agno \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/panelin-agno:latest \
  --region=us-central1 \
  --platform=managed \
  --service-account=cloud-run-service-account@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances="$DB_CONNECTION_NAME" \
  --set-env-vars="DB_CONNECTION_NAME=$DB_CONNECTION_NAME,DB_USER=$DB_USER,DB_NAME=$DB_NAME,PANELIN_MODEL_PROVIDER=openai,OPENAI_MODEL_ID=gpt-4o-mini,PANELIN_ENABLE_MCP_TOOLS=true,PANELIN_MCP_TRANSPORT=sse,PANELIN_MCP_SSE_URL=http://localhost:8000/sse" \
  --set-secrets="DB_PASSWORD=DB_PASSWORD:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,WOLF_API_KEY=WOLF_API_KEY:latest" \
  --port=8080
```

## 6. Endpoints operativos después del deploy

- Legacy:
  - `/calculate_quote`
  - `/find_products`
  - `/sheets/*`
  - `/kb/*`
- AgentOS:
  - `/agents`
  - `/agents/{agent_id}/runs`
  - `/workflows`
  - `/workflows/{workflow_id}/runs`
  - `/sessions/*`
  - `/traces/*`

## 7. Test de integración post-deploy

1. Crear run de workflow:
   `POST /workflows/{workflow_id}/runs`
2. Crear run de agent:
   `POST /agents/{agent_id}/runs`
3. Verificar persistencia:
   `GET /sessions`
4. Verificar observabilidad:
   `GET /traces`

## 8. Rollback rápido

```bash
gcloud run services update-traffic panelin-agno --to-revisions=<REVISION_ANTERIOR>=100 --region=us-central1
```
