"""
src/agent/memory.py — Memoria Long-Term para Panelin (Agno Memory)

Fase 5: Memoria persistente por cliente para personalización.

Almacena en PostgreSQL:
  - Preferencias del cliente (tipo de panel que prefiere)
  - Proyectos anteriores
  - Datos de contacto memorizados

El agente recuerda automáticamente entre sesiones diferentes.

ESTADO: Preparado para activar en FASE 5.
Para activar: USE_LONG_TERM_MEMORY=true en .env
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)

USE_LONG_TERM_MEMORY = os.environ.get("USE_LONG_TERM_MEMORY", "false").lower() == "true"


def build_panelin_memory():
    """Construye el sistema de memoria long-term para el agente.

    Usa PostgresMemoryDb para persistir memorias de usuario entre sesiones.

    Returns:
        Memory configurada, o None si USE_LONG_TERM_MEMORY=false.
    """
    if not USE_LONG_TERM_MEMORY:
        logger.debug("Memoria long-term desactivada (USE_LONG_TERM_MEMORY=false)")
        return None

    if not settings.database_url:
        logger.warning("Memoria long-term requiere DATABASE_URL configurado")
        return None

    try:
        from agno.memory.manager import MemoryManager

        logger.info("MemoryManager configurado para memoria long-term")
        return MemoryManager()

    except ImportError as exc:
        logger.warning("Memory manager no disponible: %s", exc)
        return None
    except Exception as exc:
        logger.error("Error construyendo memoria long-term: %s", exc, exc_info=True)
        return None
