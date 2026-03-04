"""
Panelin v5.0 - Memory Configuration
=====================================

Configures Agno Memory v2 for persistent client memory across sessions.
Stores facts about clients, past quotations, and preferences.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_agent_memory(db_url: str):
    """Create Agno Memory v2 with PostgreSQL persistence.

    Stores:
        - Client names, phones, locations
        - Past quotation references
        - Product preferences
        - Project details for follow-ups

    Args:
        db_url: PostgreSQL connection string.

    Returns:
        Configured Memory instance, or None if unavailable.
    """
    try:
        from agno.memory.v2 import Memory
        from agno.memory.db.postgres import PostgresMemoryDb

        memory_db = PostgresMemoryDb(
            table_name="panelin_memories",
            db_url=db_url,
        )

        memory = Memory(
            db=memory_db,
            update_memory_on_run=True,
            create_user_memories=True,
            create_session_summary=True,
        )

        logger.info("Memory v2 initialized with PostgreSQL persistence")
        return memory

    except ImportError as e:
        logger.warning(f"Memory v2 dependencies not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to create Memory v2: {e}")
        return None
