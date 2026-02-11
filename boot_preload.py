#!/usr/bin/env python3
"""
boot_preload.py - Knowledge Base Preloader

This script preloads knowledge files from knowledge_src/ to knowledge/ and generates
an index file with SHA256 hashes for validation.

Features:
- Idempotent file copying (skip unchanged files based on SHA256)
- Generates knowledge_index.json with metadata
- Optional embeddings generation (requires GENERATE_EMBEDDINGS=1 and valid API key)
- Clear error handling and exit codes

Exit codes:
    0 - Success
    1 - Critical error (missing source directory, index write failure, etc.)
    2 - Configuration error
"""

import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Configuration
SCRIPT_DIR = Path(__file__).parent.absolute()
KNOWLEDGE_SRC_DIR = SCRIPT_DIR / "knowledge_src"
KNOWLEDGE_DIR = SCRIPT_DIR / "knowledge"
INDEX_FILE = SCRIPT_DIR / "knowledge_index.json"

# Environment variables
GENERATE_EMBEDDINGS = os.environ.get("GENERATE_EMBEDDINGS", "0") == "1"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


def log(level: str, message: str) -> None:
    """Log a message with timestamp and level."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # Sanitize sensitive data from logs
    if "key" in message.lower() or "token" in message.lower():
        message = "*** REDACTED - contains sensitive data ***"
    print(f"[{timestamp}] [{level}] {message}", file=sys.stderr if level == "ERROR" else sys.stdout)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        log("ERROR", f"Failed to compute hash for {file_path}: {e}")
        raise


def ensure_directories() -> None:
    """Ensure required directories exist."""
    log("INFO", "Ensuring directories exist...")
    
    if not KNOWLEDGE_SRC_DIR.exists():
        log("ERROR", f"Source directory does not exist: {KNOWLEDGE_SRC_DIR}")
        log("ERROR", "Please create knowledge_src/ and add your knowledge files")
        sys.exit(1)
    
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    log("INFO", f"Knowledge directory ready: {KNOWLEDGE_DIR}")


def should_copy_file(src: Path, dst: Path) -> bool:
    """
    Determine if a file should be copied based on SHA256 hash comparison.
    Returns True if file should be copied (doesn't exist or hash differs).
    """
    if not dst.exists():
        return True
    
    try:
        src_hash = compute_sha256(src)
        dst_hash = compute_sha256(dst)
        return src_hash != dst_hash
    except Exception as e:
        log("WARN", f"Could not compare hashes, will copy: {e}")
        return True


def copy_knowledge_files() -> List[Dict[str, Any]]:
    """
    Copy files from knowledge_src/ to knowledge/ (idempotent).
    Returns list of file metadata entries.
    """
    log("INFO", "Scanning knowledge source files...")
    
    entries = []
    copied_count = 0
    skipped_count = 0
    
    # Get all files from knowledge_src recursively
    src_files = sorted(KNOWLEDGE_SRC_DIR.rglob("*"))
    
    for src_path in src_files:
        if not src_path.is_file():
            continue
        
        # Compute relative path
        rel_path = src_path.relative_to(KNOWLEDGE_SRC_DIR)
        dst_path = KNOWLEDGE_DIR / rel_path
        
        # Ensure destination directory exists
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if we need to copy
        if should_copy_file(src_path, dst_path):
            log("INFO", f"Copying: {rel_path}")
            shutil.copy2(src_path, dst_path)
            copied_count += 1
        else:
            log("INFO", f"Skipping (unchanged): {rel_path}")
            skipped_count += 1
        
        # Compute metadata for index
        try:
            file_hash = compute_sha256(dst_path)
            file_size = dst_path.stat().st_size
            
            entry = {
                "path": str(rel_path.as_posix()),
                "original": str(src_path.relative_to(SCRIPT_DIR).as_posix()),
                "size": file_size,
                "sha256": file_hash,
                "loaded_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            entries.append(entry)
        except Exception as e:
            log("ERROR", f"Failed to process {rel_path}: {e}")
            sys.exit(1)
    
    log("INFO", f"Files copied: {copied_count}, skipped: {skipped_count}, total: {len(entries)}")
    return entries


def generate_embeddings(entries: List[Dict[str, Any]]) -> None:
    """
    Generate embeddings for knowledge files (optional).
    
    This is a placeholder/hook for embeddings generation.
    Only runs when GENERATE_EMBEDDINGS=1 and a valid API key is present.
    Should NOT run in CI environments.
    """
    if not GENERATE_EMBEDDINGS:
        log("INFO", "Embeddings generation disabled (GENERATE_EMBEDDINGS=0)")
        return
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == "placeholder":
        log("WARN", "Embeddings generation requested but no valid API key provided")
        log("WARN", "Skipping embeddings generation")
        return
    
    log("INFO", "Embeddings generation enabled")
    log("INFO", "This is a placeholder hook for embeddings generation")
    log("INFO", "In a real implementation, this would:")
    log("INFO", "  1. Load each knowledge file")
    log("INFO", "  2. Split into chunks if needed")
    log("INFO", "  3. Call OpenAI embeddings API")
    log("INFO", "  4. Store embeddings in a vector database")
    log("INFO", "")
    log("INFO", f"Would process {len(entries)} files")
    log("WARN", "Embeddings generation not implemented - skipping")


def generate_index(entries: List[Dict[str, Any]]) -> None:
    """Generate knowledge_index.json with file metadata."""
    log("INFO", f"Generating index: {INDEX_FILE}")
    
    index_data = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "total_files": len(entries),
        "embeddings_enabled": GENERATE_EMBEDDINGS,
        "files": entries
    }
    
    try:
        with open(INDEX_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Ensure trailing newline
        log("INFO", f"Index generated successfully: {len(entries)} files indexed")
    except Exception as e:
        log("ERROR", f"Failed to write index file: {e}")
        sys.exit(1)


def validate_environment() -> None:
    """Validate environment configuration."""
    log("INFO", "Validating environment...")
    
    if GENERATE_EMBEDDINGS:
        log("INFO", "GENERATE_EMBEDDINGS=1 (embeddings generation enabled)")
        if not OPENAI_API_KEY:
            log("WARN", "GENERATE_EMBEDDINGS=1 but OPENAI_API_KEY is not set")
        elif OPENAI_API_KEY == "placeholder":
            log("WARN", "GENERATE_EMBEDDINGS=1 but OPENAI_API_KEY is placeholder")
    else:
        log("INFO", "GENERATE_EMBEDDINGS=0 (embeddings generation disabled)")


def main() -> int:
    """Main execution."""
    log("INFO", "=" * 60)
    log("INFO", "BOOT Preloader - Knowledge Base Initialization")
    log("INFO", "=" * 60)
    
    try:
        validate_environment()
        ensure_directories()
        
        # Copy files and build index
        entries = copy_knowledge_files()
        
        if not entries:
            log("WARN", "No files found in knowledge_src/")
            log("WARN", "Creating empty index")
        
        # Optional: Generate embeddings
        generate_embeddings(entries)
        
        # Generate index file
        generate_index(entries)
        
        log("INFO", "=" * 60)
        log("INFO", "Preload completed successfully")
        log("INFO", "=" * 60)
        return 0
        
    except KeyboardInterrupt:
        log("ERROR", "Interrupted by user")
        return 1
    except Exception as e:
        log("ERROR", f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
