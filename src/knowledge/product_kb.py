"""
Panelin v5.0 - Product Knowledge Base
=======================================

JSONKnowledgeBase + PgVector for semantic search over product catalogs.
Enables RAG-based product lookup when the agent needs detailed specs.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_product_knowledge(
    db_url: str,
    json_paths: Optional[list[str]] = None,
):
    """Create a JSONKnowledgeBase backed by PgVector for product search.

    Args:
        db_url: PostgreSQL connection string (must have pgvector extension).
        json_paths: List of JSON file paths to ingest.
                    Defaults to the standard KB files.

    Returns:
        Configured Knowledge instance ready to attach to an Agent.
    """
    if json_paths is None:
        json_paths = [
            "bromyros_pricing_master.json",
            "accessories_catalog.json",
            "BMC_Base_Conocimiento_GPT-2.json",
        ]

    try:
        from agno.knowledge.json import JSONKnowledgeBase
        from agno.vectordb.pgvector import PgVector
        from agno.embedder.openai import OpenAIEmbedder

        embedder = OpenAIEmbedder(id="text-embedding-3-small")

        vector_db = PgVector(
            table_name="panelin_product_embeddings",
            db_url=db_url,
            embedder=embedder,
        )

        knowledge = JSONKnowledgeBase(
            path=json_paths,
            vector_db=vector_db,
        )

        logger.info(f"Product knowledge base created with {len(json_paths)} sources")
        return knowledge

    except ImportError as e:
        logger.warning(f"Knowledge base dependencies not available: {e}")
        logger.warning("Install: pip install agno[pgvector] openai")
        return None
    except Exception as e:
        logger.error(f"Failed to create knowledge base: {e}")
        return None
