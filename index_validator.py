#!/usr/bin/env python3
"""
index_validator.py - Knowledge index validator for GPT-PANELIN-V3.2

This script validates the knowledge_index.json file, checking that:
- The index file exists and is valid JSON
- All indexed files exist
- File hashes match the index

Exit Codes:
    0 - Validation passed
    1 - Validation failed
    2 - Index file not found or invalid
"""

import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def log_info(message: str) -> None:
    """Log info message with timestamp"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] [INFO] {message}", flush=True)


def log_error(message: str) -> None:
    """Log error message with timestamp"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] [ERROR] {message}", file=sys.stderr, flush=True)


def log_success(message: str) -> None:
    """Log success message with timestamp"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] [SUCCESS] {message}", flush=True)


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_index(index_file: str = "knowledge_index.json") -> Dict:
    """
    Load and parse the knowledge index file
    
    Args:
        index_file: Path to index file
        
    Returns:
        Parsed index dictionary
        
    Raises:
        ValidationError: If index file is missing or invalid
    """
    index_path = Path(index_file)
    
    if not index_path.exists():
        raise ValidationError(f"Index file not found: {index_file}")
    
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in index file: {e}")
    except Exception as e:
        raise ValidationError(f"Failed to read index file: {e}")
    
    # Validate required fields
    required_fields = ["created", "files", "total_files", "total_size"]
    missing_fields = [field for field in required_fields if field not in index]
    
    if missing_fields:
        raise ValidationError(f"Index missing required fields: {', '.join(missing_fields)}")
    
    return index


def validate_file_entry(entry: Dict, knowledge_dir: str = "knowledge") -> Tuple[bool, str]:
    """
    Validate a single file entry from the index
    
    Args:
        entry: File entry dictionary
        knowledge_dir: Knowledge directory path
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    required_fields = ["path", "size", "sha256"]
    missing_fields = [field for field in required_fields if field not in entry]
    
    if missing_fields:
        return False, f"Missing fields: {', '.join(missing_fields)}"
    
    # Check file exists
    file_path = Path(knowledge_dir) / entry["path"]
    
    if not file_path.exists():
        return False, "File not found"
    
    if not file_path.is_file():
        return False, "Path is not a file"
    
    # Check file size
    actual_size = file_path.stat().st_size
    expected_size = entry["size"]
    
    if actual_size != expected_size:
        return False, f"Size mismatch (expected: {expected_size}, actual: {actual_size})"
    
    # Check hash
    actual_hash = calculate_sha256(file_path)
    expected_hash = entry["sha256"]
    
    if actual_hash != expected_hash:
        return False, f"Hash mismatch (expected: {expected_hash[:16]}..., actual: {actual_hash[:16]}...)"
    
    return True, ""


def validate_index(index: Dict, knowledge_dir: str = "knowledge") -> Tuple[bool, List[str]]:
    """
    Validate all entries in the index
    
    Args:
        index: Index dictionary
        knowledge_dir: Knowledge directory path
        
    Returns:
        Tuple of (all_valid, list of error messages)
    """
    files = index.get("files", [])
    errors = []
    
    if not files:
        log_info("Index contains no files")
        return True, []
    
    log_info(f"Validating {len(files)} file(s)...")
    
    valid_count = 0
    
    for i, entry in enumerate(files, 1):
        file_path = entry.get("path", f"<unknown-{i}>")
        
        is_valid, error_msg = validate_file_entry(entry, knowledge_dir)
        
        if is_valid:
            log_info(f"✓ [{i}/{len(files)}] {file_path} - OK")
            valid_count += 1
        else:
            log_error(f"✗ [{i}/{len(files)}] {file_path} - {error_msg}")
            errors.append(f"{file_path}: {error_msg}")
    
    log_info(f"Validation complete: {valid_count}/{len(files)} files valid")
    
    return len(errors) == 0, errors


def check_orphaned_files(index: Dict, knowledge_dir: str = "knowledge") -> List[str]:
    """
    Check for files in knowledge directory not in index
    
    Args:
        index: Index dictionary
        knowledge_dir: Knowledge directory path
        
    Returns:
        List of orphaned file paths
    """
    knowledge_path = Path(knowledge_dir)
    
    if not knowledge_path.exists():
        return []
    
    # Get indexed files
    indexed_files = set(entry["path"] for entry in index.get("files", []))
    
    # Get actual files
    actual_files = set(
        str(f.relative_to(knowledge_path))
        for f in knowledge_path.rglob("*")
        if f.is_file()
    )
    
    # Find orphaned files
    orphaned = actual_files - indexed_files
    
    return sorted(orphaned)


def main() -> int:
    """Main execution"""
    try:
        log_info("=== Knowledge index validation started ===")
        
        # Step 1: Load index
        log_info("Step 1: Loading index...")
        index = load_index()
        log_info(f"Index loaded: {index['total_files']} file(s), {index['total_size']} bytes")
        log_info(f"Index created: {index['created']}")
        
        # Step 2: Validate entries
        log_info("Step 2: Validating index entries...")
        all_valid, errors = validate_index(index)
        
        if not all_valid:
            log_error(f"Validation failed with {len(errors)} error(s):")
            for error in errors:
                log_error(f"  - {error}")
            return 1
        
        # Step 3: Check for orphaned files
        log_info("Step 3: Checking for orphaned files...")
        orphaned_files = check_orphaned_files(index)
        
        if orphaned_files:
            log_info(f"Warning: Found {len(orphaned_files)} orphaned file(s) not in index:")
            for file_path in orphaned_files:
                log_info(f"  - {file_path}")
        else:
            log_info("No orphaned files found")
        
        # Success
        log_success("=== Validation completed successfully ===")
        return 0
        
    except ValidationError as e:
        log_error(f"Validation error: {e}")
        return 2
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
