# 🎯 Guía de Orquestación de Agentes — GPT-PANELIN v3.4

**Versión:** 3.4-Orchestrator  
**Fecha:** 2026-02-16  
**Propósito:** Framework de orquestación para agentes autónomos y workflows del proyecto GPT-PANELIN  

---

## 📋 Contenido

1. [Visión General](#visión-general)
2. [Estructura de Archivos](#estructura-de-archivos)
3. [Jerarquía de Verdad](#jerarquía-de-verdad)
4. [Agentes Disponibles](#agentes-disponibles)
5. [Workflows Definidos](#workflows-definidos)
6. [Uso en VS Code](#uso-en-vs-code)
7. [Uso con GitHub Copilot](#uso-con-github-copilot)

---

## 🎯 Visión General

Este framework transforma la forma de trabajar con el proyecto GPT-PANELIN, pasando de **"programar scripts"** a **"dirigir agentes"**. Cada agente tiene un rol específico y puede ser invocado de forma independiente o como parte de un workflow coordinado.

### Beneficios Clave

- ✅ **Validación Automatizada:** Los agentes verifican la integridad de la KB antes de cualquier cambio
- ✅ **Separación de Responsabilidades:** Cada agente se especializa en una tarea específica
- ✅ **Workflows Reproducibles:** Los procesos comunes están documentados y automatizados
- ✅ **Integración con Copilot:** GitHub Copilot entiende la estructura y puede sugerir workflows

---

## 📁 Estructura de Archivos

```
GPT-PANELIN-V3.3/
├── .github/
│   └── copilot-instructions.md    # Instrucciones maestras para Copilot
├── .vscode/
│   └── tasks.json                 # Tareas de VS Code
├── agent_orchestrator.json        # Manifiesto de agentes y workflows
├── .evolucionador/
│   ├── core/
│   │   └── analyzer.py           # Motor de análisis (qa_auditor)
│   └── reports/
│       └── generator.py          # Generador de reportes
├── mcp/
│   ├── server.py                 # Servidor MCP (mcp_operator)
│   └── config/
│       └── mcp_server_config.json
├── validate_gpt_files.py         # Validador pre-vuelo (deploy_manager)
└── package_gpt_files.py          # Empaquetador (deploy_manager)
```

---

## 🏆 Jerarquía de Verdad

**NUNCA romper esta prioridad al hacer cambios:**

1. **NIVEL 1 (Master):** `BMC_Base_Conocimiento_GPT-2.json` — Precios base, fórmulas oficiales
2. **NIVEL 1.2:** `accessories_catalog.json` — Precios de accesorios
3. **NIVEL 1.3:** `bom_rules.json` — Reglas paramétricas de construcción
4. **CÓDIGO:** `quotation_calculator_v3.py` — Lógica de cálculo validada

### Regla de Oro

> **Si detectas un error de precio, NO lo cambies en el código.**  
> Genera una entrada para `corrections_log.json` y ejecuta el agente `qa_auditor`.

---

## 🤖 Agentes Disponibles

### 1. El Evolucionador (`qa_auditor`)

**Rol:** Quality Assurance & Self-Correction  
**Archivo:** `.evolucionador/core/analyzer.py`

**Capacidades:**
- ✅ Validación de esquemas JSON
- ✅ Verificación de integridad de fórmulas
- ✅ Optimización de estructura de precios

**Comando:**
```bash
python .evolucionador/core/analyzer.py && python .evolucionador/reports/generator.py
```

**Output:** `.evolucionador/reports/latest.json`

---

### 2. Gatekeeper de Despliegue (`deploy_manager`)

**Rol:** Release Management  
**Archivo:** `validate_gpt_files.py`

**Capacidades:**
- ✅ Pre-flight checks antes de deploy
- ✅ Generación de paquetes organizados por fase

**Comando:**
```bash
python validate_gpt_files.py && python package_gpt_files.py
```

**Output:** `GPT_Upload_Package/INSTRUCTIONS.txt`

---

### 3. Wolf API Bridge (`mcp_operator`)

**Rol:** Live Data Interaction  
**Archivo:** `mcp/server.py`  
**Config:** `mcp/config/mcp_server_config.json`

**Herramientas Activas:**
- `price_check` — Consulta de precios
- `catalog_search` — Búsqueda en catálogo
- `bom_calculate` — Cálculo de BOM
- `report_error` — Reporte de errores
- `quotation_store` — Almacenamiento de cotizaciones
- `persist_conversation` — Persistencia de conversaciones
- `register_correction` — Registro de correcciones
- `save_customer` / `lookup_customer` — Gestión de clientes
- `batch_bom_calculate` — Cálculo batch de BOMs
- `bulk_price_check` — Consulta masiva de precios
- `full_quotation` — Cotización completa
- `task_status` / `task_result` / `task_list` / `task_cancel` — Gestión de tareas

**Transporte:** Server-Sent Events (SSE)

---

## 🔄 Workflows Definidos

### 1. `daily_health_check`

**Descripción:** Auditoría diaria de la Knowledge Base  
**Agentes:** `qa_auditor`

**Cuándo ejecutar:**
- Al inicio del día
- Después de cambios en archivos JSON de nivel 1

**Comando VS Code:** `🤖 ACTIVAR EVOLUCIONADOR (Auditoría)`

---

### 2. `release_cycle`

**Descripción:** Ciclo completo de validación y empaquetado para despliegue  
**Agentes:** `qa_auditor` → `deploy_manager`

**Cuándo ejecutar:**
- Antes de subir cambios al GPT
- Antes de crear un release

**Comando VS Code:** `📦 EMPAQUETAR PARA GPT (Deploy)`

---

### 3. `fix_pricing_error`

**Descripción:** Reportar y corregir error de precio detectado  
**Pasos:** `mcp_operator.report_error` → `qa_auditor`

**Cuándo ejecutar:**
- Cuando se detecta un precio incorrecto
- Después de registrar una corrección

---

### 4. `optimize_structure`

**Descripción:** Analizar y optimizar estructura de precios  
**Agentes:** `qa_auditor`

**Cuándo ejecutar:**
- Mensualmente para análisis de rendimiento
- Cuando se detectan oportunidades de optimización

---

## 💻 Uso en VS Code

### Tareas Disponibles

Presiona `Cmd/Ctrl + Shift + P` y escribe "Tasks: Run Task" para ver:

1. **🤖 ACTIVAR EVOLUCIONADOR (Auditoría)**
   - Ejecuta los 7 validadores
   - Genera reporte de salud del proyecto

2. **📦 EMPAQUETAR PARA GPT (Deploy)**
   - Valida JSONs
   - Crea carpeta `GPT_Upload_Package`

3. **🔌 LEVANTAR SERVIDOR MCP (Local)**
   - Inicia servidor para pruebas con Claude/OpenAI
   - Solicita `WOLF_API_KEY`

4. **✅ VALIDAR ARCHIVOS GPT**
   - Validación rápida de esquemas JSON
   - Verifica estructura de KB

5. **🧪 EJECUTAR TESTS MCP**
   - Suite completa de tests del servidor MCP

### Atajos de Teclado

Puedes crear atajos personalizados en `.vscode/keybindings.json`:

```json
[
  {
    "key": "cmd+shift+v",
    "command": "workbench.action.tasks.runTask",
    "args": "✅ VALIDAR ARCHIVOS GPT"
  }
]
```

---

## 🤝 Uso con GitHub Copilot

### Conversación Natural

Con las instrucciones maestras en `.github/copilot-instructions.md`, puedes interactuar así:

**Tú:**
> @workspace Quiero actualizar el precio del ISOPANEL a 45 USD. ¿Qué debo hacer?

**Copilot:**
> Detecto que quieres cambiar un precio Nivel 1. No edites el código.  
> 1. Edita `BMC_Base_Conocimiento_GPT-2.json`
> 2. Ejecuta la tarea `🤖 ACTIVAR EVOLUCIONADOR` para validar integridad

---

**Tú:**
> Copilot, el reporte del Evolucionador dice que hay "inconsistencias de esquema". Arréglalo.

**Copilot:**
> Revisando `.evolucionador/reports/latest.json`...  
> Error encontrado: [descripción específica]  
> Propongo este patch: [código]

---

### Comandos Útiles

- `@workspace ¿Qué workflow debo usar para [tarea]?`
- `@workspace Ejecuta el health check`
- `@workspace Prepara el proyecto para deploy`
- `@workspace ¿Qué herramientas tiene el mcp_operator?`

---

## 🚀 Próximos Pasos

1. **Familiarízate con los workflows:**
   - Ejecuta `daily_health_check` una vez
   - Revisa el output de cada agente

2. **Personaliza según tu flujo:**
   - Agrega nuevos workflows a `agent_orchestrator.json`
   - Crea tareas personalizadas en `.vscode/tasks.json`

3. **Integra con tu equipo:**
   - Comparte los workflows definidos
   - Documenta nuevos agentes que desarrolles

---

## 📚 Referencias

- [Copilot Instructions](.github/copilot-instructions.md)
- [Agent Orchestrator](agent_orchestrator.json)
- [VS Code Tasks](.vscode/tasks.json)
- [MCP Quick Start](MCP_QUICK_START.md)
- [MCP Agent Architect Prompt](MCP_AGENT_ARCHITECT_PROMPT.md)

---

**¿Dudas o sugerencias?**  
Abre un issue o consulta con GitHub Copilot usando `@workspace`.

---

*Última actualización: 2026-02-16*
