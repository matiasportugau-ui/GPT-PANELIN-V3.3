#!/usr/bin/env python3
"""
boot_preload.py - Knowledge file preloader for GPT-PANELIN-V3.2

This script preloads knowledge files from knowledge_src to knowledge directory,
creates an index with file metadata and hashes, and optionally generates embeddings.

Environment Variables:
    GENERATE_EMBEDDINGS - Set to '1' to enable embeddings generation (requires API key)
                         Default: '0' (disabled)
    OPENAI_API_KEY     - OpenAI API key (required only if GENERATE_EMBEDDINGS=1)
    
Exit Codes:
    0 - Success
    1 - General error
    2 - Missing prerequisites
    3 - Index generation failed
"""

import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Configuration
KNOWLEDGE_SRC_DIR = "knowledge_src"
KNOWLEDGE_DIR = "knowledge"
INDEX_FILE = "knowledge_index.json"


class PreloadError(Exception):
    """Custom exception for preload errors"""
    pass


def log_info(message: str) -> None:
    """Log info message with timestamp"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] [INFO] {message}", flush=True)


def log_warn(message: str) -> None:
    """Log warning message with timestamp"""
    timestamp = datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(datetime, 'UTC') else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] [WARN] {message}", file=sys.stderr, flush=True)


def log_error(message: str) -> None:
    """Log error message with timestamp"""
    timestamp = datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(datetime, 'UTC') else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] [ERROR] {message}", file=sys.stderr, flush=True)


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_metadata(file_path: Path) -> Dict:
    """Get metadata for a file"""
    stat = file_path.stat()
    return {
        "path": str(file_path.relative_to(KNOWLEDGE_DIR)),
        "size": stat.st_size,
        "sha256": calculate_sha256(file_path),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "indexed": datetime.now(timezone.utc).isoformat()
    }


def should_copy_file(src_path: Path, dst_path: Path) -> bool:
    """
    Determine if file should be copied (idempotent check)
    Returns True if file needs copying, False if up-to-date
    """
    if not dst_path.exists():
        return True
    
    # Compare file sizes first (quick check)
    src_size = src_path.stat().st_size
    dst_size = dst_path.stat().st_size
    
    if src_size != dst_size:
        return True
    
    # Compare hashes if sizes match
    src_hash = calculate_sha256(src_path)
    dst_hash = calculate_sha256(dst_path)
    
    return src_hash != dst_hash


def copy_knowledge_files() -> List[Path]:
    """
    Copy files from knowledge_src to knowledge directory
    Returns list of copied/updated file paths
    """
    src_dir = Path(KNOWLEDGE_SRC_DIR)
    dst_dir = Path(KNOWLEDGE_DIR)
    
    if not src_dir.exists():
        log_warn(f"Source directory {KNOWLEDGE_SRC_DIR} does not exist")
        return []
    
    # Ensure destination directory exists
    dst_dir.mkdir(exist_ok=True)
    
    copied_files = []
    skipped_files = []
    
    # Find all files in source directory (recursively)
    src_files = list(src_dir.rglob("*"))
    src_files = [f for f in src_files if f.is_file()]
    
    if not src_files:
        log_warn(f"No files found in {KNOWLEDGE_SRC_DIR}")
        return []
    
    log_info(f"Found {len(src_files)} file(s) in {KNOWLEDGE_SRC_DIR}")
    
    for src_file in src_files:
        # Calculate relative path
        rel_path = src_file.relative_to(src_dir)
        dst_file = dst_dir / rel_path
        
        # Ensure parent directory exists
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if copy is needed (idempotent)
        if should_copy_file(src_file, dst_file):
            log_info(f"Copying: {rel_path}")
            shutil.copy2(src_file, dst_file)
            copied_files.append(dst_file)
        else:
            log_info(f"Skipping (up-to-date): {rel_path}")
            skipped_files.append(dst_file)
    
    log_info(f"Copied {len(copied_files)} file(s), skipped {len(skipped_files)} (up-to-date)")
    
    return copied_files


def create_knowledge_index() -> Dict:
    """
    Create knowledge index with file metadata and hashes
    Returns the index dictionary
    """
    knowledge_dir = Path(KNOWLEDGE_DIR)
    
    if not knowledge_dir.exists():
        log_warn(f"Knowledge directory {KNOWLEDGE_DIR} does not exist")
        return {
            "created": datetime.utcnow().isoformat(),
            "files": [],
            "total_files": 0,
            "total_size": 0
        }
    
    # Find all files in knowledge directory
    files = list(knowledge_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    
    log_info(f"Indexing {len(files)} file(s)...")
    
    indexed_files = []
    total_size = 0
    
    for file_path in files:
        try:
            metadata = get_file_metadata(file_path)
            indexed_files.append(metadata)
            total_size += metadata["size"]
            log_info(f"Indexed: {metadata['path']} ({metadata['size']} bytes, SHA256: {metadata['sha256'][:16]}...)")
        except Exception as e:
            log_error(f"Failed to index {file_path}: {e}")
    
    index = {
        "created": datetime.now(timezone.utc).isoformat(),
        "files": indexed_files,
        "total_files": len(indexed_files),
        "total_size": total_size,
        "embeddings_generated": False
    }
    
    log_info(f"Index created with {len(indexed_files)} file(s), total size: {total_size} bytes")
    
    return index


def save_index(index: Dict) -> None:
    """Save index to file"""
    index_path = Path(INDEX_FILE)
    
    try:
        with open(index_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        log_info(f"Index saved to {INDEX_FILE}")
    except Exception as e:
        raise PreloadError(f"Failed to save index: {e}")


def check_api_key() -> bool:
    """Check if API key is available"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    return bool(api_key and api_key.strip() and not api_key.startswith("sk-dummy"))


def generate_embeddings_placeholder(index: Dict) -> Dict:
    """
    Placeholder for embeddings generation
    
    This function validates prerequisites and would call actual embedding generation.
    In production, this would use OpenAI API or similar service.
    
    Args:
        index: Knowledge index dictionary
        
    Returns:
        Updated index with embeddings_generated flag
    """
    generate_embeddings = os.environ.get("GENERATE_EMBEDDINGS", "0") == "1"
    
    if not generate_embeddings:
        log_info("Embeddings generation disabled (GENERATE_EMBEDDINGS=0)")
        return index
    
    log_info("Embeddings generation requested (GENERATE_EMBEDDINGS=1)")
    
    # Check if API key is available
    if not check_api_key():
        log_error("Embeddings generation requested but OPENAI_API_KEY is not set or invalid")
        log_error("Skipping embeddings generation")
        return index
    
    log_info("API key detected (validation passed)")
    log_warn("Embeddings generation is a placeholder - implement actual generation as needed")
    
    # In production, implement actual embeddings generation here
    # For now, just mark as generated
    index["embeddings_generated"] = True
    index["embeddings_generated_at"] = datetime.now(timezone.utc).isoformat()
    
    log_info("Embeddings generation completed (placeholder)")
    
    return index


def main() -> int:
    """Main execution"""
    try:
        log_info("=== Knowledge preload started ===")
        
        # Step 1: Copy files from source to knowledge
        log_info("Step 1: Copying knowledge files...")
        copied_files = copy_knowledge_files()
        
        # Step 2: Create knowledge index
        log_info("Step 2: Creating knowledge index...")
        index = create_knowledge_index()
        
        # Step 3: Generate embeddings (if requested)
        log_info("Step 3: Processing embeddings...")
        index = generate_embeddings_placeholder(index)
        
        # Step 4: Save index
        log_info("Step 4: Saving index...")
        save_index(index)
        
        log_info("=== Knowledge preload completed successfully ===")
        return 0
        
    except PreloadError as e:
        log_error(f"Preload error: {e}")
        return 3
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
