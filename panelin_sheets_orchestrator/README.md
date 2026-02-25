# Panelin Sheets Orchestrator

Microservicio Cloud Run que automatiza el llenado de planillas Google Sheets
para Panelin v3.3, usando OpenAI Structured Outputs para generar planes de
escritura validados contra una allowlist de rangos.

## Arquitectura

```
Usuario/GPT → POST /v1/fill → Sheets Orchestrator (Cloud Run)
                                   ├─ OpenAI Responses API (plan JSON)
                                   ├─ Validación allowlist
                                   ├─ Google Sheets batchUpdate
                                   └─ Idempotencia (Firestore / memoria)
```

## Endpoints

| Método | Ruta               | Descripción                                    |
|--------|--------------------|-------------------------------------------------|
| GET    | `/healthz`         | Health check                                    |
| POST   | `/v1/fill`         | Generar plan IA + escribir en Sheet             |
| POST   | `/v1/queue/process`| Procesar jobs PENDING desde una hoja QUEUE      |

Autenticación: header `X-API-Key` (mismo patrón que Wolf API).

## Setup local

```bash
cd panelin_sheets_orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # editar con tus credenciales
./scripts/test.sh
./scripts/local_run.sh
```

## Deploy

```bash
export GCP_PROJECT_ID=<tu-proyecto>
export GCP_REGION=us-central1
./scripts/set_secrets.sh
./scripts/deploy_gcloud.sh
```

O usar Terraform:

```bash
cd infra/terraform
terraform init && terraform apply \
  -var="project_id=<GCP_PROJECT_ID>" \
  -var="region=<GCP_REGION>"
```

## Templates

Los templates en `templates/sheets/` definen:
- `writes_allowlist`: rangos donde se permite escribir
- `read_ranges`: rangos a leer como contexto para OpenAI
- `hints`: metadata para guiar la generación del plan

## Seguridad

- Secretos en Google Secret Manager (`OPENAI_API_KEY`, `PANELIN_ORCH_API_KEY`)
- Service account con least privilege (`secretAccessor`, `datastore.user`)
- CI/CD sin llaves: Workload Identity Federation (WIF) para GitHub Actions
- Allowlist de rangos impide escritura en celdas con fórmulas
