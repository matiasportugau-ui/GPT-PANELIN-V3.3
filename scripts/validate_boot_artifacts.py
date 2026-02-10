#!/usr/bin/env python3
"""
validate_boot_artifacts.py - Validates BOOT Process Artifacts

Purpose:
    Validates that BOOT process created correct artifacts:
    - .boot-ready flag with valid metadata
    - .boot-log with proper format and no secrets
    - knowledge_index.json with valid structure and file hashes

Usage:
    python3 scripts/validate_boot_artifacts.py [--strict]

Exit Codes:
    0 - All validations passed
    1 - Validation failed
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Validation results
PASSED = 0
FAILED = 0

# Sensitive patterns that should not appear in logs
SENSITIVE_PATTERNS = [
    r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}',
    r'password["\']?\s*[:=]\s*["\']?[^\s"\']{8,}',
    r'secret["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}',
    r'token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}',
    r'Bearer\s+[a-zA-Z0-9_.-]{20,}',  # JWT Bearer tokens with dots
]


def log_pass(message: str):
    """Log a passed validation."""
    global PASSED
    print(f"✓ PASS: {message}")
    PASSED += 1


def log_fail(message: str):
    """Log a failed validation."""
    global FAILED
    print(f"✗ FAIL: {message}")
    FAILED += 1


def log_warn(message: str):
    """Log a warning."""
    print(f"⚠ WARN: {message}")


def log_info(message: str):
    """Log informational message."""
    print(f"ℹ INFO: {message}")


def validate_boot_ready(root_dir: Path, strict: bool = False) -> bool:
    """Validate .boot-ready flag file."""
    boot_ready = root_dir / '.boot-ready'
    
    print("\n=== Validating .boot-ready ===")
    
    if not boot_ready.exists():
        log_fail(".boot-ready file not found")
        return False
    
    log_pass(".boot-ready file exists")
    
    try:
        content = boot_ready.read_text()
        
        # Check for required fields
        if 'BOOT completed successfully' in content:
            log_pass("Contains completion message")
        else:
            log_fail("Missing completion message")
        
        if 'Timestamp:' in content:
            log_pass("Contains timestamp")
        else:
            log_fail("Missing timestamp")
        
        if 'Python:' in content:
            log_pass("Contains Python version")
        else:
            log_warn("Missing Python version")
        
        # Check timestamp format
        timestamp_match = re.search(r'Timestamp:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', content)
        if timestamp_match:
            try:
                datetime.fromisoformat(timestamp_match.group(1).replace('Z', '+00:00'))
                log_pass("Timestamp format is valid ISO 8601")
            except ValueError:
                log_fail("Timestamp format is invalid")
        
        return True
        
    except Exception as e:
        log_fail(f"Error reading .boot-ready: {e}")
        return False


def validate_boot_log(root_dir: Path, strict: bool = False) -> bool:
    """Validate .boot-log file."""
    boot_log = root_dir / '.boot-log'
    
    print("\n=== Validating .boot-log ===")
    
    if not boot_log.exists():
        log_fail(".boot-log file not found")
        return False
    
    log_pass(".boot-log file exists")
    
    try:
        content = boot_log.read_text()
        lines = content.split('\n')
        
        log_info(f"Log has {len(lines)} lines")
        
        # Check timestamp format in log entries
        timestamp_pattern = r'^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]'
        lines_with_timestamps = 0
        
        for line in lines:
            if line.strip() and re.match(timestamp_pattern, line):
                lines_with_timestamps += 1
        
        if lines_with_timestamps > 0:
            log_pass(f"{lines_with_timestamps} log entries have proper timestamps")
        else:
            log_fail("No log entries with proper timestamps found")
        
        # Check for no secrets in log
        secrets_found = False
        for pattern in SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                log_fail(f"Found potential secret in log: {pattern}")
                secrets_found = True
        
        if not secrets_found:
            log_pass("No secrets detected in log")
        
        # Check for common log messages
        if 'Panelin GPT BOOT Process Starting' in content:
            log_pass("Contains startup message")
        
        if 'Environment validation passed' in content or 'Environment validation' in content:
            log_pass("Contains environment validation messages")
        
        return not secrets_found
        
    except Exception as e:
        log_fail(f"Error reading .boot-log: {e}")
        return False


def validate_knowledge_index(root_dir: Path, strict: bool = False) -> bool:
    """Validate knowledge_index.json structure and integrity."""
    index_path = root_dir / 'knowledge_index.json'
    
    print("\n=== Validating knowledge_index.json ===")
    
    if not index_path.exists():
        if strict:
            log_fail("knowledge_index.json not found (strict mode)")
            return False
        else:
            log_warn("knowledge_index.json not found (optional)")
            return True
    
    log_pass("knowledge_index.json exists")
    
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        log_pass("knowledge_index.json is valid JSON")
        
        # Check required fields
        required_fields = ['version', 'generated_at', 'files', 'statistics']
        for field in required_fields:
            if field in index:
                log_pass(f"Contains required field: {field}")
            else:
                log_fail(f"Missing required field: {field}")
        
        # Check files array
        if 'files' in index and isinstance(index['files'], list):
            log_info(f"Index contains {len(index['files'])} files")
            
            # Validate a sample of file entries
            sample_size = min(5, len(index['files']))
            for i in range(sample_size):
                file_entry = index['files'][i]
                
                required_file_fields = ['path', 'name', 'sha256', 'size_bytes']
                all_fields_present = all(field in file_entry for field in required_file_fields)
                
                if all_fields_present:
                    if i == 0:  # Only log for first entry
                        log_pass("File entries have required fields")
                    
                    # Verify hash if file exists
                    file_path = root_dir / file_entry['path']
                    if file_path.exists() and strict:
                        actual_hash = compute_file_hash(file_path)
                        if actual_hash == file_entry['sha256']:
                            if i == 0:
                                log_pass("File hash verification passed")
                        else:
                            log_fail(f"Hash mismatch for {file_entry['path']}")
                else:
                    log_fail(f"File entry missing required fields: {file_entry.get('path', 'unknown')}")
        
        # Check statistics
        if 'statistics' in index:
            stats = index['statistics']
            if 'files_indexed' in stats:
                log_pass(f"Statistics: {stats['files_indexed']} files indexed")
            if 'total_size_mb' in stats:
                log_info(f"Total size: {stats['total_size_mb']} MB")
        
        return True
        
    except json.JSONDecodeError as e:
        log_fail(f"knowledge_index.json is invalid JSON: {e}")
        return False
    except Exception as e:
        log_fail(f"Error validating knowledge_index.json: {e}")
        return False


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description='Validate BOOT process artifacts'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Enable strict validation mode'
    )
    parser.add_argument(
        '--root',
        type=str,
        default='.',
        help='Repository root directory (default: current directory)'
    )
    
    args = parser.parse_args()
    root_dir = Path(args.root).resolve()
    
    print("=" * 60)
    print("BOOT Artifacts Validation")
    print("=" * 60)
    print(f"Root: {root_dir}")
    print(f"Strict mode: {args.strict}")
    print()
    
    # Run validations
    results = [
        validate_boot_ready(root_dir, args.strict),
        validate_boot_log(root_dir, args.strict),
        validate_knowledge_index(root_dir, args.strict),
    ]
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    print(f"Passed: {PASSED}")
    print(f"Failed: {FAILED}")
    print()
    
    if FAILED == 0 and all(results):
        print("✓ All validations passed!")
        return 0
    else:
        print("✗ Some validations failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
