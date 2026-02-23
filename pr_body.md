# EXPORT_SEAL
## Fix: Compat-layer for OpenAI vector_stores API

### Resumen
Este PR añade una capa de compatibilidad para la API de *vector stores* del cliente OpenAI:
- Detecta y usa `client.beta.vector_stores` o `client.vector_stores`.
- Añade tolerancia a respuestas como objetos con atributos o como `dict`.
- Evita el `AttributeError: 'Beta' object has no attribute 'vector_stores'` visto durante el despliegue.

### Cambios principales
- `deploy_gpt_assistant.py`
  - Añadido `_get_vector_stores_api()` (compat helper).
  - Reemplazada la creación y polling de vector store por llamadas a la API retornada por el helper.
  - Manejo tolerante de `vs` y `file_counts` si vienen como objeto o dict.

### Checklist antes de merge
- [ ] Ejecutar `python deploy_gpt_assistant.py --dry-run` en runner local/CI con `openai` actualizado.
- [ ] Actualizar `requirements.txt` (o lockfile) con `openai>=1.0.0`.
- [ ] Re-run CI job y verificar paso `[7/8] Setting up vector store...` sin errores.
- [ ] (Opcional) Revisar shapes reales de la respuesta `vector_stores.retrieve` en tu entorno y ajustar si difieren.
