"""
Panelin v5.0 — Product Knowledge Base

Loads BMC product data into Agno Knowledge with PgVector for semantic search.
This enables the agent to answer product questions using RAG.

Data sources:
    - bromyros_pricing_master.json (96 products)
    - accessories_catalog.json (70+ accessories)
    - BMC_Base_Conocimiento_GPT-2.json (specs, formulas)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.core.config import get_settings


def create_product_knowledge(
    db_url: Optional[str] = None,
    table_name: str = "panelin_knowledge",
):
    """Create a Knowledge base backed by PgVector for product search.

    Requires:
        - PostgreSQL with pgvector extension
        - pip install agno[pgvector]

    Returns:
        Knowledge instance ready to be passed to an Agent.
    """
    settings = get_settings()
    url = db_url or settings.database_url

    try:
        from agno.knowledge.knowledge import Knowledge
        from agno.knowledge.reader.json_reader import JSONReader
        from agno.vectordb.pgvector import PgVector, SearchType

        vector_db = PgVector(
            table_name=table_name,
            db_url=url,
            search_type=SearchType.hybrid,
        )

        knowledge = Knowledge(vector_db=vector_db)
        return knowledge
    except ImportError as e:
        raise ImportError(
            "PgVector dependencies not installed. "
            "Run: pip install 'agno[pgvector]' pgvector"
        ) from e


def load_product_data(knowledge, kb_root: Optional[Path] = None) -> None:
    """Load all product JSON files into the knowledge base.

    Args:
        knowledge: Knowledge instance from create_product_knowledge().
        kb_root: Root directory containing KB JSON files.
    """
    from agno.knowledge.reader.json_reader import JSONReader

    settings = get_settings()
    root = kb_root or settings.kb_root

    files = [
        root / settings.kb_pricing_master,
        root / settings.kb_accessories,
        root / settings.kb_core,
    ]

    reader = JSONReader()
    for file_path in files:
        if file_path.exists():
            knowledge.insert(path=str(file_path), reader=reader)
