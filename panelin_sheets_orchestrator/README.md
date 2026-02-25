# Panelin Sheets Orchestrator

Microservicio Cloud Run que automatiza el llenado de planillas Google Sheets
para Panelin v3.3, usando OpenAI Structured Outputs para generar planes de
escritura validados contra una allowlist de rangos y reglas de negocio Panelin.

## Arquitectura

```
Usuario/GPT ──► POST /v1/fill ──► Sheets Orchestrator (Cloud Run)
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
            validators.py      openai_planner.py       sheets_client.py
            (autoportancia,    (Responses API,         (batchGet/Update,
             BOM, precios,      Structured Outputs,     cache TTL,
             dimensiones)       prompt Panelin)         retries 429)
                │                      │                      │
                └──────────────────────┼──────────────────────┘
                                       │
                                  audit.py
                              (Cloud Logging JSON,
                               trazabilidad completa)
                                       │
                              Idempotency Store
                         (Firestore prod / memoria dev)
```

## Módulos

| Módulo | Responsabilidad |
|--------|----------------|
| `config.py` | Configuración centralizada (env vars, defaults, business rules) |
| `models.py` | Modelos Pydantic para todos los endpoints |
| `service.py` | FastAPI app con 8 endpoints |
| `sheets_client.py` | Cliente Sheets API con cache, retries, audit |
| `openai_planner.py` | Generación de planes de escritura con prompt Panelin |
| `validators.py` | Validación de autoportancia, BOM, dimensiones, precios |
| `audit.py` | Logging estructurado JSON compatible con Cloud Logging |

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| POST | `/v1/fill` | Generar plan IA + escribir en Sheet |
| POST | `/v1/read` | Leer rangos de una Sheet |
| POST | `/v1/validate` | Validar autoportancia/BOM (sin IA ni Sheets) |
| GET | `/v1/templates` | Listar templates disponibles |
| GET | `/v1/templates/{id}` | Obtener un template específico |
| GET | `/v1/jobs/{job_id}` | Consultar estado de un job |
| POST | `/v1/queue/process` | Procesar jobs PENDING de una hoja QUEUE |

Autenticación: header `X-API-Key` (mismo patrón que Wolf API).

## Templates disponibles

| Template | Familia | Uso |
|----------|---------|-----|
| `cotizacion_isodec_eps_v1` | ISODEC EPS | Techos/cubiertas |
| `cotizacion_isodec_pir_v1` | ISODEC PIR | Techos resistentes al fuego |
| `cotizacion_isoroof_3g_v1` | ISOROOF 3G | Techos livianos |
| `cotizacion_isopanel_eps_v1` | ISOPANEL EPS | Paredes/fachadas |
| `cotizacion_isofrig_pir_v1` | ISOFRIG PIR | Cámaras frigoríficas |

## Validación de negocio

El endpoint `/v1/validate` permite validar sin IA ni Sheets:

```bash
curl -X POST http://localhost:8080/v1/validate \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "product_family": "ISODEC_EPS",
    "thickness_mm": 100,
    "length_m": 5.0,
    "width_m": 10.0,
    "usage": "techo",
    "structure": "metal"
  }'
```

Respuesta incluye: `panels_needed`, `supports`, `fixing_points`,
`rods_varilla_3_8`, `nuts_tuercas`, `area_m2`, y validación de autoportancia
con margen de seguridad del 15%.

## Reglas de negocio implementadas

- **Autoportancia**: Tablas completas para 6 familias de paneles (ISODEC EPS/PIR, ISOROOF 3G, ISOPANEL EPS, ISOWALL PIR, ISOFRIG PIR)
- **BOM**: Cálculo de paneles, apoyos, puntos de fijación, varillas, tuercas
- **Fijación techo vs pared**: Fórmulas diferenciadas según uso
- **Metal vs hormigón**: Tuercas dobles (metal) vs simples + tacos (hormigón)
- **Precios IVA incluido**: 22% ya incluido, nunca agregar
- **Moneda**: Siempre USD
- **Redondeo**: Siempre ceil (hacia arriba)
- **Formulas prohibidas**: Valores que empiezan con `=` son rechazados

## Setup local

```bash
cd panelin_sheets_orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # editar con tus credenciales
./scripts/test.sh      # 100 tests
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

## Seguridad

- Secretos en Google Secret Manager (`OPENAI_API_KEY`, `PANELIN_ORCH_API_KEY`)
- Service account con least privilege (`secretAccessor`, `datastore.user`)
- CI/CD sin llaves: Workload Identity Federation (WIF) para GitHub Actions
- Allowlist de rangos impide escritura en celdas con fórmulas
- Validación de valores rechaza fórmulas (`=SUM(...)` etc.)
- Constant-time API key comparison (`hmac.compare_digest`)

## Observabilidad

- Audit logging JSON compatible con Cloud Logging (`jsonPayload`)
- Cada operación registra: action, job_id, spreadsheet_id, elapsed_ms
- OpenAI calls: input/output tokens, duración
- Sheets API calls: operación, cantidad de rangos, duración
- Queue batches: procesados, exitosos, fallidos
