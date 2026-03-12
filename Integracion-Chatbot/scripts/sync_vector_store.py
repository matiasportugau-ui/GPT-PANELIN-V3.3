"""
Script de sincronización del catálogo inmobiliario a OpenAI Vector Store.

Sube documentos (JSON/Markdown exportados desde Inmoenter) al almacén
vectorial de OpenAI para habilitar búsqueda semántica RAG.

Uso:
    python scripts/sync_vector_store.py

Prerequisitos:
    - Variable de entorno OPENAI_API_KEY configurada.
    - Archivo de catálogo exportado disponible en disco.
"""

import asyncio

from openai import AsyncOpenAI

client = AsyncOpenAI()


async def sync_catalog_to_rag(file_path: str) -> None:
    """Sincroniza un archivo de catálogo al Vector Store de OpenAI.

    Crea un nuevo Vector Store, sube el archivo con chunking estático
    optimizado para contenido inmobiliario, y reporta el ID resultante.

    Args:
        file_path: Ruta al archivo de catálogo a sincronizar.
    """
    v_store = await client.beta.vector_stores.create(name="Inmoenter_Maestro")

    with open(file_path, "rb") as f:
        batch = await client.beta.vector_stores.file_batches.create_and_poll(
            vector_store_id=v_store.id,
            files=[f],
            chunking_strategy={
                "type": "static",
                "static": {
                    "max_chunk_size_tokens": 800,
                    "chunk_overlap_tokens": 200,
                },
            },
        )

    print(f"Sincronización completa. Vector Store ID: {v_store.id}")
    print(f"Batch status: {batch.status}")


if __name__ == "__main__":
    asyncio.run(sync_catalog_to_rag("catalogo_exportado.json"))
