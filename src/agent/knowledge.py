"""
src/agent/knowledge.py — Knowledge Base para Panelin (Agno Knowledge)

Fase 5: Búsqueda semántica sobre la KB de productos BMC Uruguay.

Usa JSONKnowledgeBase + PgVector para búsqueda vectorial de:
  - Especificaciones técnicas de paneles
  - Reglas de negocio
  - FAQ de clientes frecuentes

Requiere: pip install agno[pgvector] pgvector

ESTADO: Preparado para activar en FASE 5.
Para activar, cambiar USE_KNOWLEDGE_BASE=true en .env
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)

USE_KNOWLEDGE_BASE = os.environ.get("USE_KNOWLEDGE_BASE", "false").lower() == "true"

KB_ROOT = Path(__file__).resolve().parent.parent.parent


def build_panelin_knowledge():
    """Construye la Knowledge Base semántica para el agente Panelin.

    Usa PgVector (PostgreSQL) para almacenar embeddings de la KB de productos.
    El agente puede hacer búsquedas semánticas: "¿cuál es el panel más ligero?"

    Returns:
        Knowledge base configurada, o None si USE_KNOWLEDGE_BASE=false.
    """
    if not USE_KNOWLEDGE_BASE:
        logger.debug("Knowledge base desactivada (USE_KNOWLEDGE_BASE=false)")
        return None

    if not settings.database_url:
        logger.warning("Knowledge base requiere DATABASE_URL configurado")
        return None

    try:
        from agno.knowledge.json import JSONKnowledgeBase
        from agno.vectordb.pgvector import PgVector
        from agno.embedder.openai import OpenAIEmbedder

        vector_db = PgVector(
            db_url=settings.database_url,
            table_name="panelin_knowledge",
            embedder=OpenAIEmbedder(
                id="text-embedding-3-small",
                api_key=settings.openai_api_key,
            ),
        )

        # Fuentes de conocimiento de productos BMC
        knowledge_sources = []

        bmc_kb_path = KB_ROOT / settings.kb_core
        if bmc_kb_path.exists():
            kb = JSONKnowledgeBase(
                path=str(bmc_kb_path),
                vector_db=vector_db,
                name="bmc_knowledge",
            )
            knowledge_sources.append(kb)

        if not knowledge_sources:
            logger.warning("No se encontraron fuentes de conocimiento KB")
            return None

        logger.info("Knowledge base configurada con %d fuentes", len(knowledge_sources))
        return knowledge_sources[0] if len(knowledge_sources) == 1 else knowledge_sources

    except ImportError as exc:
        logger.warning(
            "agno[pgvector] no instalado. Knowledge base desactivada: %s", exc
        )
        return None
    except Exception as exc:
        logger.error("Error construyendo knowledge base: %s", exc, exc_info=True)
        return None


def load_knowledge_to_vector_db() -> bool:
    """Carga los documentos de KB al vector DB.

    Ejecutar UNA VEZ para indexar. Luego el vector DB se usa en cada consulta.

    Returns:
        True si se cargó exitosamente.
    """
    kb = build_panelin_knowledge()
    if kb is None:
        return False

    try:
        if hasattr(kb, "load"):
            kb.load(recreate=False)
            logger.info("Knowledge base cargada al vector DB")
        return True
    except Exception as exc:
        logger.error("Error cargando knowledge base: %s", exc, exc_info=True)
        return False
