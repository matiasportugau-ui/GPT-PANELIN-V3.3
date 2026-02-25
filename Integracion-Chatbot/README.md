# 🤖 Integración Chatbot: Agente Inmobiliario Cognitivo (v3.3)

> **Arquitectura Integral e Implementación de Asistente Inmobiliario Cognitivo:**  
> Sinergia entre PANELIN-API, WhatsApp Cloud, OpenAI v2 y Google Cloud Run

---

## Quick Start

```bash
# 1. Clonar el repositorio
git clone https://github.com/matiasportugau-ui/Integracion-Chatbot.git
cd Integracion-Chatbot

# 2. Crear entorno virtual e instalar dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales reales

# 4. Ejecutar el servidor
uvicorn src.main:app --host 0.0.0.0 --port 8080

# 5. Ejecutar el servidor MCP (en otra terminal)
python mcp_server/panelin_mcp.py
```

---

## Índice

1. [Fundamentos Arquitectónicos y Despliegue en Google Cloud Run](#1-fundamentos-arquitectónicos-y-despliegue-en-google-cloud-run)
2. [Integración de la Interfaz Conversacional: WhatsApp Cloud API](#2-integración-de-la-interfaz-conversacional-whatsapp-cloud-api)
3. [Evolución Cognitiva: OpenAI Assistants API v2, Responses API y RAG](#3-evolución-cognitiva-openai-assistants-api-v2-responses-api-y-rag)
4. [Sincronización de Datos Inmobiliarios: PANELIN-API (Inmoenter)](#4-sincronización-de-datos-inmobiliarios-panelin-api-inmoenter)
5. [Persistencia Multiturno y Control de Concurrencia con Cloud Firestore](#5-persistencia-multiturno-y-control-de-concurrencia-con-cloud-firestore)
6. [El Protocolo de Escalado Humano (Human-in-the-Loop)](#6-el-protocolo-de-escalado-humano-human-in-the-loop)
7. [Gestión Avanzada de Multimedia: Transmisión de PDFs](#7-gestión-avanzada-de-multimedia-transmisión-de-contratos-y-dossiers-en-pdf)
8. [Implementación del Código Fuente (FastAPI Asíncrono)](#8-implementación-del-código-fuente-fastapi-asíncrono)
9. [Guía de Implementación Asistida por IA (Cursor IDE)](#9-guía-de-implementación-asistida-por-ia-cursor-ide)

---

## Estructura del Proyecto

```
Integracion-Chatbot/
├── .cursor/rules/project-rules.mdc   # Reglas Cursor IDE (Sección 9.1)
├── .env.example                       # Template de variables de entorno
├── .gitignore
├── Dockerfile                         # Deploy en Google Cloud Run
├── README.md                          # Este documento
├── requirements.txt                   # Dependencias Python
├── src/
│   ├── __init__.py
│   ├── config.py                      # Configuración centralizada
│   ├── firestore_client.py            # Gestión de sesiones Firestore
│   ├── api_meta.py                    # Capa de transporte WhatsApp
│   ├── openai_router.py               # Enrutador OpenAI Responses API
│   └── main.py                        # FastAPI webhook principal
├── mcp_server/
│   └── panelin_mcp.py                 # Servidor MCP para CRM Inmoenter
└── scripts/
    └── sync_vector_store.py           # Sincronización Vector Store
```

---

## 1. Fundamentos Arquitectónicos y Despliegue en Google Cloud Run

El ecosistema técnico se estructura como una **arquitectura orientada a eventos y microservicios sin estado**. Google Cloud Run actúa como el núcleo orquestador, proporcionando un endpoint HTTPS seguro y escalable que procesa los webhooks entrantes de Meta y coordina las llamadas asíncronas hacia la API de OpenAI y el CRM inmobiliario.

La naturaleza *"stateless"* (sin estado) de Cloud Run exige que cualquier memoria a corto o largo plazo, así como los bloqueos transaccionales, se externalicen a servicios dedicados como **Firestore** y los **almacenes vectoriales de OpenAI**. Esta decisión de diseño garantiza que las instancias del contenedor puedan crearse o destruirse dinámicamente según las fluctuaciones del tráfico de red sin perder el contexto de las negociaciones con los clientes.

Una consideración crítica en el diseño de infraestructura para agentes cognitivos basados en Python es la **gestión de la concurrencia**. Las comunicaciones con las API de OpenAI, Meta y PANELIN-API involucran predominantemente operaciones limitadas por entrada/salida (I/O-bound) y tiempos de espera de red. Por ello, la industria ha abandonado los frameworks síncronos tradicionales (como Flask) en favor de **FastAPI**. El soporte nativo de FastAPI para operaciones asíncronas (`async/await`) resulta crítico y altamente eficiente al orquestar llamadas de red concurrentes, permitiendo escalar el rendimiento del contenedor de Cloud Run y procesar docenas de mensajes de WhatsApp simultáneamente sin bloquear el hilo principal de ejecución.

Adicionalmente, la configuración de facturación y asignación de CPU en Google Cloud Run tiene implicaciones directas en el comportamiento de las integraciones de IA. Si el sistema requiere ejecutar procesos analíticos en segundo plano después de devolver la respuesta inicial al webhook de Meta (para evitar timeouts en la API de WhatsApp), se debe configurar Cloud Run con la opción de **"CPU siempre asignada"** (*CPU always allocated*).

La infraestructura descrita asegura que la plataforma no solo sea reactiva, sino que posea la **resiliencia sistémica** necesaria para manejar picos de tráfico originados por campañas masivas.

---

## 2. Integración de la Interfaz Conversacional: WhatsApp Cloud API

La selección de la **API oficial de WhatsApp Cloud** administrada por Meta es un mandato arquitectónico irrenunciable para operaciones a escala empresarial, garantizando estabilidad frente a bloqueos y soporte oficial de plantillas.

La interacción entre el clúster de Cloud Run y la infraestructura de Meta se rige por un **paradigma de webhooks basado en eventos**. Meta requiere que el servidor exponga un endpoint público que responda a un desafío criptográfico inicial para verificar la propiedad del dominio.

### Seguridad: Verificación HMAC

Más allá de la verificación inicial, la seguridad operacional continua exige validar la cabecera `X-Hub-Signature-256`. El middleware en FastAPI debe computar dinámicamente el código HMAC utilizando el algoritmo **SHA-256** sobre la carga útil bruta de la petición, empleando el `App Secret` como clave criptográfica.

```python
async def verify_signature(request: Request):
    signature = request.headers.get("X-Hub-Signature-256")
    payload = await request.body()
    expected = hmac.new(APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, f"sha256={expected}"):
        raise HTTPException(status_code=401, detail="Firma inválida")
```

### Ventana de 24 Horas

El modelo comercial de Meta impone una **restricción de ventana de 24 horas**. Cuando un cliente envía un mensaje, se abre una ventana durante la cual las respuestas de formato libre incurren en tarifas de sesión. Si el agente necesita contactar al prospecto fuera de esta ventana temporal, el sistema está estrictamente obligado a utilizar **"Mensajes de Plantilla"** (*Template Messages*) preaprobados por Meta.

La arquitectura debe monitorear el tiempo transcurrido desde la última interacción (almacenada en Firestore) y cambiar automáticamente de formato si el umbral se excede.

---

## 3. Evolución Cognitiva: OpenAI Assistants API v2, Responses API y RAG

El núcleo de comprensión del lenguaje natural reside en los modelos fundacionales de OpenAI. Si bien la arquitectura actual se basa en la Assistants API v2, el ecosistema está en plena transición.

> ⚠️ **Nota de Migración:** OpenAI ha anunciado la eventual depreciación de la API de Asistentes en favor de la nueva y más flexible **Responses API** acoplada con el estándar **Model Context Protocol (MCP)**. Este proyecto implementa la Responses API como estándar.

Diseñar el sistema con una clara separación de responsabilidades facilita la migración: el enrutamiento y el historial en Firestore se mantienen idénticos, mientras que solo el objeto de llamada a la IA cambia a la nueva sintaxis de *Prompts* y *Conversations*.

### 3.1. Gestión de Almacenes Vectoriales (Vector Stores)

Los **Vector Stores** permiten que el conocimiento profundo de la agencia se consolide en un repositorio centralizado e indexado.

> ⚠️ **Política de Retención:** Los almacenes vectoriales creados dinámicamente y adjuntados a hilos de conversación heredan una política de expiración predeterminada de **7 días** tras su última actividad. Para garantizar que el inventario inmobiliario maestro permanezca disponible ininterrumpidamente, se debe sobrescribir explícitamente `expires_after` estableciéndola a valores prolongados o nulos.

#### Flujo RAG (Generación Aumentada por Recuperación) Inmobiliario

1. **Ingesta y Segmentación:** Los documentos (XML parseados a JSON/Markdown) se suben y asocian al almacén vectorial. OpenAI aplica algoritmos de fragmentación estáticos o dinámicos para preservar el contexto.
2. **Transformación Vectorial:** Se convierten a representaciones numéricas mediante modelos de embeddings (ej. `text-embedding-3-large`).
3. **Recuperación Semántica:** Al recibir una consulta ("Busco ático en la costa"), la herramienta `file_search` realiza una búsqueda de similitud espacial y extrae los fragmentos relevantes para inyectarlos en la ventana de contexto del LLM.

### 3.2. Model Context Protocol (MCP) para Integración Externa

Para interactuar en tiempo real con datos que no están en el Vector Store (por ejemplo, buscar disponibilidad de calendario de un agente o insertar un nuevo lead en el CRM Inmoenter), la arquitectura moderna recomienda el uso del **Model Context Protocol (MCP)**.

En lugar de definir esquemas JSON de `function_calling` frágiles en cada solicitud, un servidor MCP actúa como un **conector estandarizado**. El LLM descubre automáticamente las herramientas expuestas por el servidor MCP (ej. `create_lead`, `fetch_latest_properties`) y delega la ejecución de la API REST subyacente de PANELIN de manera segura y controlada.

```python
# Integración MCP en la Responses API
response = await client.responses.create(
    model="gpt-4o",
    input=user_text,
    tools=[
        {"type": "file_search", "max_num_results": 3},
        {"type": "mcp", "server_url": "http://localhost:8080"}
    ]
)
```

---

## 4. Sincronización de Datos Inmobiliarios: PANELIN-API (Inmoenter)

La inteligencia del agente conversacional depende de la **frescura de los datos** en la plataforma Inmoenter, accesible a través de PANELIN-API y sus feeds de sindicación XML (XCP / KML3).

### Flujo de Sincronización

1. Un proceso cronometrado (**Cloud Scheduler**) ejecuta una petición `GET` nocturna hacia los endpoints regionales de Inmoenter utilizando una API KEY.
2. Una vez que el documento XML es descargado en la memoria, el middleware de Python lo transforma en documentos legibles para el LLM.
3. Los documentos transformados se sincronizan al Vector Store de OpenAI (ver `scripts/sync_vector_store.py`).

### Integración Bidireccional

Cuando la IA cualifica a un prospecto en WhatsApp, las variables (presupuesto, ubicación) se extraen semánticamente. Posteriormente, utilizando herramientas invocables (a través del puente MCP), el backend de Cloud Run realiza una petición REST `POST` a Inmoenter para crear el lead y la "demanda", asignándolo automáticamente a los embudos de venta de los agentes humanos.

---

## 5. Persistencia Multiturno y Control de Concurrencia con Cloud Firestore

La API de OpenAI delega la gestión de la memoria secuencial, pero es responsabilidad de la capa de integración vincular cada número de WhatsApp con su hilo correspondiente.

### Esquema Documental

Google Cloud Firestore utiliza el número de teléfono (`wa_id`) como clave primaria:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `wa_id` | `string` | Número de teléfono del cliente |
| `thread_id` | `string` | ID del hilo de conversación OpenAI |
| `ai_active` | `boolean` | `true` = IA controla, `false` = humano controla |
| `last_interaction` | `timestamp` | Marca temporal de última interacción |

### Control de Concurrencia

Para manejar las ráfagas de mensajes asíncronos típicos de WhatsApp y evitar **condiciones de carrera** (creación de múltiples hilos para el mismo usuario de forma simultánea), las operaciones de lectura y escritura en Firestore se encapsulan dentro de **transacciones atómicas** del SDK de Firebase.

```python
@firestore.transactional
def execute_transaction(transaction, ref):
    snapshot = ref.get(transaction=transaction)
    # ... lógica atómica ...
    transaction.update(ref, {"last_interaction": now, "ai_active": ai_active})
    return ai_active, thread_id
```

---

## 6. El Protocolo de Escalado Humano (Human-in-the-Loop)

Depender exclusivamente de la IA representa un riesgo para negociaciones sensibles. El patrón de **"Escalado Humano"** (*Human Handoff*) actúa como el freno de emergencia del ecosistema.

### Flujo de Escalado

```
Cliente dice "quiero hablar con un agente"
    → LLM detecta intención de asistencia humana
    → ai_active = false en Firestore
    → IA responde: "Transfiriendo a un agente comercial..."
    → Mensajes subsiguientes → Cloud Run lee ai_active=false → HTTP 200 silencioso
    → Operador humano interactúa libremente

Timeout 24h sin interacción del operador:
    → ai_active revierte a true automáticamente
```

### Keywords de Activación

```python
HANDOFF_KEYWORDS = ["humano", "agente", "asesor"]

if any(word in user_text.lower() for word in HANDOFF_KEYWORDS):
    disable_ai_for_human(wa_id)
    return "Un agente comercial revisará este chat a la brevedad."
```

---

## 7. Gestión Avanzada de Multimedia: Transmisión de Contratos y Dossiers en PDF

La capacidad de despachar documentos técnicos (PDF) requiere una **orquestación en dos fases asíncronas** con la Graph API de Meta.

### Fase 1: Ingesta a Meta (obtención del `media_id`)

El sistema descarga el PDF o lo genera en memoria, y formula un `POST` al endpoint `/media` codificado como `multipart/form-data`.

> ⚠️ **Crítico:** En Python (usando `httpx`), enviar el archivo como una tupla estructurada: `('filename.pdf', file_bytes, 'application/pdf')`. Omitir esta estructura provocará un error `OAuthException Code 100` por parte de los servidores de Meta.

### Fase 2: Transmisión del Mensaje

Se emite una segunda petición `POST` al endpoint `/messages` con una carga útil JSON que inyecta el `media_id` recuperado, junto con el nombre del archivo (`filename`) y un texto descriptivo (`caption`).

```python
payload = {
    "messaging_product": "whatsapp", "to": to, "type": "document",
    "document": {"id": media_id, "filename": filename, "caption": "Documento adjunto."}
}
```

---

## 8. Implementación del Código Fuente (FastAPI Asíncrono)

Para maximizar el rendimiento en Cloud Run y evitar el bloqueo del GIL en Python durante llamadas I/O intensivas, la implementación se basa en **FastAPI** y clientes HTTP asíncronos (`httpx` y `AsyncOpenAI`).

### 8.1. Dependencias (`requirements.txt`)

```
fastapi>=0.109.0
uvicorn>=0.27.0
httpx>=0.26.0
openai>=1.14.0
firebase-admin>=6.5.0
fastmcp>=0.1.0
python-dotenv>=1.0.1
```

### 8.2. Arquitectura Modular

La implementación sigue una **arquitectura modular** en lugar de un archivo monolítico, facilitando el mantenimiento y las pruebas unitarias:

| Módulo | Responsabilidad |
|--------|----------------|
| `src/config.py` | Configuración centralizada de variables de entorno |
| `src/firestore_client.py` | Gestión transaccional de sesiones en Firestore |
| `src/api_meta.py` | Capa de transporte hacia WhatsApp Cloud API |
| `src/openai_router.py` | Enrutamiento de inferencia con OpenAI Responses API |
| `src/main.py` | Webhook FastAPI principal con verificación HMAC |
| `mcp_server/panelin_mcp.py` | Servidor MCP para integración CRM Inmoenter |

### 8.3. Despliegue con Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
# Build y deploy a Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/integracion-chatbot
gcloud run deploy integracion-chatbot \
  --image gcr.io/PROJECT_ID/integracion-chatbot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "VERIFY_TOKEN=...,WHATSAPP_TOKEN=..."
```

---

## 9. Guía de Implementación Asistida por IA (Cursor IDE)

La arquitectura descrita representa un sistema complejo con múltiples puntos de integración. Para acelerar el desarrollo y reducir la fricción, se recomienda encarecidamente la utilización de entornos de desarrollo impulsados por IA, como **Cursor IDE**.

### 9.1. Definición de Reglas de Proyecto (`.cursor/rules/`)

Para que el modelo de lenguaje mantenga la coherencia arquitectónica y no genere código con librerías obsoletas (como la antigua Assistants API), es mandatorio establecer **reglas de proyecto**. Cursor soporta archivos Markdown con metadatos (formato `.mdc`) almacenados en el directorio `.cursor/rules/`.

- **Forzar** el uso de FastAPI y httpx asíncrono para las integraciones web.
- **Especificar explícitamente** el uso de la Responses API de OpenAI y el estándar MCP.
- **Documentar** el patrón Human Handoff con Firestore para alinear al modelo.

### 9.2. Modos de Interacción: Composer vs. Chat

| Herramienta | Uso Ideal |
|-------------|-----------|
| **Composer (Agent Mode)** | Andamiaje y tareas multi-archivo: *"Genera la estructura de directorios, el archivo main.py con FastAPI y el panelin_mcp.py basándote en las reglas del proyecto"* |
| **Chat** | Depuración línea por línea: *"¿Por qué el webhook de Meta está devolviendo un error de validación HMAC en esta función?"* |

### 9.3. Gestión de Contexto mediante Indexación Semántica

Al trabajar con múltiples módulos, el agente necesita contexto preciso. Se recomienda invocar dependencias explícitamente utilizando el atajo `@` seguido del nombre del archivo o carpeta en el chat (por ejemplo, `@api_meta.py` o `@firestore_client.py`).

### 9.4. Planificación, Autonomía y Tolerancia a Fallos

- **Plan Mode:** Generar un plan de implementación antes de escribir código masivo. Guardar en `.cursor/plans/`.
- **YOLO Mode + TDD:** El agente ejecuta comandos en terminal, arranca el servidor (`uvicorn`), verifica errores de linting o ejecuta pruebas (`pytest`), corrigiendo recursivamente hasta que el sistema funcione.
- **Restore Checkpoint:** Si la IA genera código contraproducente, revertir con la funcionalidad de checkpoint en lugar de forzar correcciones iterativas.

---

## Licencia

Este proyecto es propiedad de [matiasportugau-ui](https://github.com/matiasportugau-ui). Todos los derechos reservados.
