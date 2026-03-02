"""OpenAI Vector Store synchronization with BMC Uruguay product knowledge base.

Sync strategy: Delta-based with Firestore index
1. Load products from JSON knowledge base files (pricing + core KB)
2. Transform to embedding-optimized text documents
3. Load existing file index from Firestore (avoids N+1 API calls)
4. Compute delta: new files to upload, stale files to delete
5. Execute uploads and deletions via AsyncOpenAI
6. Save updated index to Firestore
7. Report statistics

Data sources:
- bromyros_pricing_master.json: Product SKUs, families, pricing
- BMC_Base_Conocimiento_GPT-2.json: Detailed specs, autoportancia, BOM context

Cost impact:
- Vector store storage: $0.10/GB/day, first 1GB FREE
- ~100 products × ~500 bytes = ~50KB → well under free tier
- Delta sync avoids re-uploading unchanged products
"""

import io
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from .panelin_sync import (
    Product,
    load_products_from_kb,
    load_products_from_pricing,
    transform_products_to_documents,
)

logger = logging.getLogger(__name__)

INDEX_COLLECTION = "vector_store_index"
INDEX_DOCUMENT = "current"


@dataclass
class SyncStats:
    """Statistics from a vector store sync operation."""

    added: int = 0
    removed: int = 0
    unchanged: int = 0
    errors: int = 0
    total_products: int = 0


def _load_index_from_firestore(db) -> dict[str, str]:
    """Load {filename: file_id} mapping from Firestore."""
    try:
        doc = db.collection(INDEX_COLLECTION).document(INDEX_DOCUMENT).get()
        if doc.exists:
            return doc.to_dict().get("files", {})
    except Exception:
        logger.warning("Failed to load vector store index from Firestore", exc_info=True)
    return {}


def _save_index_to_firestore(db, index: dict[str, str]) -> None:
    """Save {filename: file_id} mapping to Firestore."""
    try:
        db.collection(INDEX_COLLECTION).document(INDEX_DOCUMENT).set({
            "files": index,
        })
    except Exception:
        logger.exception("Failed to save vector store index to Firestore")


async def _list_files_from_api(
    client: AsyncOpenAI,
    vector_store_id: str,
) -> dict[str, str]:
    """Fallback: list files from OpenAI API when Firestore index unavailable."""
    existing: dict[str, str] = {}
    try:
        vs_files = await client.vector_stores.files.list(
            vector_store_id=vector_store_id
        )
        for vs_file in vs_files.data:
            try:
                file_obj = await client.files.retrieve(vs_file.id)
                existing[file_obj.filename] = vs_file.id
            except Exception:
                logger.warning("Failed to retrieve file %s", vs_file.id)
    except Exception:
        logger.exception("Failed to list vector store files via API")
    return existing


def load_all_products(
    pricing_path: str = "bromyros_pricing_master.json",
    kb_path: str = "BMC_Base_Conocimiento_GPT-2.json",
) -> list[Product]:
    """Load products from all BMC knowledge base sources.

    Merges products from pricing master and core KB, deduplicating
    by SKU (KB version takes precedence for richer data).

    Args:
        pricing_path: Path to bromyros_pricing_master.json.
        kb_path: Path to BMC_Base_Conocimiento_GPT-2.json.

    Returns:
        Merged, deduplicated list of Product objects.
    """
    # Load from both sources
    pricing_products = load_products_from_pricing(pricing_path)
    kb_products = load_products_from_kb(kb_path)

    # Deduplicate: KB products take precedence (richer data)
    seen_skus: set[str] = set()
    merged: list[Product] = []

    for prod in kb_products:
        if prod.sku and prod.sku not in seen_skus:
            seen_skus.add(prod.sku)
            merged.append(prod)

    for prod in pricing_products:
        if prod.sku and prod.sku not in seen_skus:
            seen_skus.add(prod.sku)
            merged.append(prod)

    logger.info(
        "Merged products: %d from KB + %d from pricing = %d unique",
        len(kb_products),
        len(pricing_products),
        len(merged),
    )
    return merged


async def sync_vector_store(
    client: AsyncOpenAI,
    vector_store_id: str,
    products: list[Product],
    db=None,
) -> SyncStats:
    """Synchronize vector store with current BMC product list.

    Uses Firestore-based index for O(1) delta detection.
    Falls back to API-based listing if db is not provided.

    Args:
        client: Initialized AsyncOpenAI client.
        vector_store_id: Target vector store ID.
        products: Current list of products from KB.
        db: Optional Firestore client for index storage.

    Returns:
        SyncStats with operation counts.
    """
    stats = SyncStats(total_products=len(products))
    documents = transform_products_to_documents(products)

    new_docs = {filename: content for filename, content in documents}
    new_filenames = set(new_docs.keys())

    # Load existing file index
    if db:
        existing_files = _load_index_from_firestore(db)
    else:
        existing_files = await _list_files_from_api(client, vector_store_id)

    existing_filenames = set(existing_files.keys())

    # Compute delta
    to_add = new_filenames - existing_filenames
    to_remove = existing_filenames - new_filenames
    stats.unchanged = len(new_filenames & existing_filenames)

    uploaded_ids: dict[str, str] = {}

    # Upload new product files
    for filename in to_add:
        content = new_docs[filename]
        try:
            file_bytes = content.encode("utf-8")
            uploaded = await client.files.create(
                file=(filename, io.BytesIO(file_bytes)),
                purpose="assistants",
            )
            await client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=uploaded.id,
            )
            uploaded_ids[filename] = uploaded.id
            stats.added += 1
        except Exception:
            logger.exception("Failed to upload %s", filename)
            stats.errors += 1

    # Delete removed products (prevents AI from quoting discontinued items)
    for filename in to_remove:
        file_id = existing_files[filename]
        try:
            await client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id,
            )
            await client.files.delete(file_id=file_id)
            stats.removed += 1
        except Exception:
            logger.exception(
                "Failed to delete %s (file_id=%s)", filename, file_id
            )
            stats.errors += 1

    # Update Firestore index
    if db:
        updated_index = {
            k: v for k, v in existing_files.items() if k not in to_remove
        }
        updated_index.update(uploaded_ids)
        _save_index_to_firestore(db, updated_index)

    logger.info(
        "Vector store sync: added=%d removed=%d unchanged=%d errors=%d total=%d",
        stats.added, stats.removed, stats.unchanged,
        stats.errors, stats.total_products,
    )
    return stats


async def run_nightly_sync(
    openai_api_key: str,
    vector_store_id: str,
    pricing_path: str = "bromyros_pricing_master.json",
    kb_path: str = "BMC_Base_Conocimiento_GPT-2.json",
    db=None,
) -> SyncStats:
    """Run the complete nightly sync pipeline for BMC products.

    Orchestrates: load KB files → merge → transform → sync vector store.
    Called by Cloud Scheduler via POST /sync endpoint.

    Args:
        openai_api_key: OpenAI API key.
        vector_store_id: Target vector store ID.
        pricing_path: Path to bromyros_pricing_master.json.
        kb_path: Path to BMC_Base_Conocimiento_GPT-2.json.
        db: Optional Firestore client for index storage.

    Returns:
        SyncStats with operation counts.
    """
    products = load_all_products(pricing_path, kb_path)
    if not products:
        logger.warning("No products loaded from KB — skipping sync")
        return SyncStats()

    client = AsyncOpenAI(api_key=openai_api_key)
    return await sync_vector_store(client, vector_store_id, products, db=db)
