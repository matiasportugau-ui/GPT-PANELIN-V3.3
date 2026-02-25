"""OpenAI Vector Store synchronization with Inmoenter property feed.

Sync strategy: Delta-based with Firestore index (Fix H5)
1. Fetch current property feed from Inmoenter XML
2. Transform to text documents
3. Load existing file index from Firestore (avoids N+1 API calls)
4. Compute delta: new files to upload, stale files to delete
5. Execute uploads and deletions
6. Save updated index to Firestore
7. Report statistics

Uses AsyncOpenAI (Fix C1) for non-blocking file operations.
Firestore index db parameter is optional (Fix cross-#2) — falls
back to API-based listing if db is not provided.

Cost impact:
- Vector store storage: $0.10/GB/day, first 1GB FREE
- 1000 properties × ~500 bytes = ~500KB → well under free tier
- Delta sync avoids re-uploading unchanged properties
- Firestore index eliminates N+1 OpenAI API calls for delta detection
"""

import io
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from .inmoenter_sync import (
    Property,
    fetch_property_feed,
    transform_properties_to_documents,
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
    total_properties: int = 0


def _load_index_from_firestore(db) -> dict[str, str]:
    """Load {filename: file_id} mapping from Firestore.

    Returns empty dict if index doesn't exist yet (first sync).
    """
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
    """Fallback: list files from OpenAI API when Firestore index unavailable.

    WARNING: This is O(N) API calls where N = number of files in vector store.
    Use Firestore index whenever possible.
    """
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


async def sync_vector_store(
    client: AsyncOpenAI,
    vector_store_id: str,
    properties: list[Property],
    db=None,
) -> SyncStats:
    """Synchronize vector store with current property list.

    Uses Firestore-based index for O(1) delta detection (Fix H5).
    Falls back to API-based listing if db is not provided.

    Args:
        client: Initialized AsyncOpenAI client.
        vector_store_id: Target vector store ID.
        properties: Current list of properties from feed.
        db: Optional Firestore client for index storage.

    Returns:
        SyncStats with operation counts.
    """
    stats = SyncStats(total_properties=len(properties))
    documents = transform_properties_to_documents(properties)

    # Map property IDs to document content
    new_docs = {filename: content for filename, content in documents}
    new_filenames = set(new_docs.keys())

    # Load existing file index (Firestore preferred, API fallback)
    if db:
        existing_files = _load_index_from_firestore(db)
    else:
        existing_files = await _list_files_from_api(client, vector_store_id)

    existing_filenames = set(existing_files.keys())

    # Compute delta
    to_add = new_filenames - existing_filenames
    to_remove = existing_filenames - new_filenames
    stats.unchanged = len(new_filenames & existing_filenames)

    # Track uploaded file IDs for index update
    uploaded_ids: dict[str, str] = {}

    # Upload new files
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

    # Delete removed files (prevents hallucination of sold properties)
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
        stats.added,
        stats.removed,
        stats.unchanged,
        stats.errors,
        stats.total_properties,
    )
    return stats


async def run_nightly_sync(
    openai_api_key: str,
    vector_store_id: str,
    feed_url: str,
    inmoenter_api_key: str,
    db=None,
) -> SyncStats:
    """Run the complete nightly sync pipeline.

    Orchestrates: fetch feed → transform → sync vector store.
    Called by Cloud Scheduler via POST /sync endpoint.

    Args:
        openai_api_key: OpenAI API key.
        vector_store_id: Target vector store ID.
        feed_url: Inmoenter XML feed URL.
        inmoenter_api_key: Inmoenter API key.
        db: Optional Firestore client for index storage.

    Returns:
        SyncStats with operation counts.
    """
    # Step 1: Fetch property feed
    properties = await fetch_property_feed(feed_url, inmoenter_api_key)
    if not properties:
        logger.warning("No properties fetched from feed — skipping sync")
        return SyncStats()

    # Step 2: Sync vector store
    client = AsyncOpenAI(api_key=openai_api_key)
    return await sync_vector_store(client, vector_store_id, properties, db=db)
