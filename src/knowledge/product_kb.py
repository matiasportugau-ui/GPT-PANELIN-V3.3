"""
Panelin v5.0 — Knowledge Base (Vector Search)
=================================================

Loads BMC product data into an Agno Knowledge base backed by PgVector
for semantic search. This allows the agent to find relevant products
based on natural language queries.

Data sources:
    - bromyros_pricing_master.json (96 panel products)
    - accessories_catalog.json (70+ accessories)
    - BMC_Base_Conocimiento_GPT-2.json (specs, formulas, business rules)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def build_product_knowledge(
    db_url: Optional[str] = None,
    table_name: str = "panelin_product_vectors",
):
    """Build an Agno Knowledge base with PgVector for product search.

    Returns:
        Configured Knowledge instance with product data loaded.
    """
    from agno.knowledge.json import JSONKnowledgeBase
    from agno.vectordb.pgvector import PgVector, SearchType

    from src.core.config import get_settings

    settings = get_settings()
    url = db_url or settings.db_url

    vector_db = PgVector(
        table_name=table_name,
        db_url=url,
        search_type=SearchType.hybrid,
    )

    kb_root = Path(__file__).resolve().parent.parent.parent

    json_files = [
        kb_root / "bromyros_pricing_master.json",
        kb_root / "accessories_catalog.json",
    ]

    existing_files = [str(f) for f in json_files if f.exists()]

    if not existing_files:
        logger.warning("No KB JSON files found at %s", kb_root)
        return None

    knowledge = JSONKnowledgeBase(
        path=existing_files,
        vector_db=vector_db,
    )

    logger.info("Product knowledge base configured with %d files", len(existing_files))
    return knowledge


def load_bmc_kb_as_context() -> str:
    """Load the BMC knowledge base as a context string for the agent.

    This provides product specs, business rules, and formulas
    as system context without vector search overhead.
    """
    kb_root = Path(__file__).resolve().parent.parent.parent
    kb_path = kb_root / "BMC_Base_Conocimiento_GPT-2.json"

    if not kb_path.exists():
        logger.warning("BMC KB not found at %s", kb_path)
        return ""

    try:
        with open(kb_path, encoding="utf-8") as f:
            kb = json.load(f)

        sections = []

        reglas = kb.get("reglas_negocio", {})
        if reglas:
            sections.append("## Reglas de Negocio BMC")
            sections.append(f"- IVA: {reglas.get('iva', 0.22) * 100}%")
            sections.append(f"- Moneda: {reglas.get('moneda', 'USD')}")
            derivacion = reglas.get("derivacion", {})
            if derivacion:
                sections.append(f"- Derivación: {derivacion.get('regla_oro', '')}")

        products = kb.get("products", {})
        if products:
            sections.append("\n## Productos BMC")
            for name, data in products.items():
                if isinstance(data, dict):
                    sections.append(f"- **{name}**: {data.get('descripcion', data.get('tipo', ''))}")

        datos_ref = kb.get("datos_referencia_uruguay", {})
        if datos_ref:
            sections.append("\n## Datos de Referencia Uruguay")
            kwh = datos_ref.get("precio_kwh_uruguay", {})
            if kwh:
                sections.append(f"- Precio kWh residencial: USD {kwh.get('residencial', 'N/A')}")
                sections.append(f"- Precio kWh comercial: USD {kwh.get('comercial', 'N/A')}")

        return "\n".join(sections)
    except Exception as e:
        logger.error("Error loading BMC KB: %s", e)
        return ""
