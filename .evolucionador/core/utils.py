"""
EVOLUCIONADOR Utility Functions
===============================
Common utility functions used across the EVOLUCIONADOR system.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_repo_root() -> Path:
    """
    Get the repository root directory.
    
    Returns:
        Path: The absolute path to the repository root
    """
    repo_path = os.environ.get('REPO_PATH')
    if repo_path:
        return Path(repo_path)
    
    # Default to current directory's parent's parent (from .evolucionador/core/)
    return Path(__file__).parent.parent.parent


def load_json_file(file_path: Path) -> Optional[Dict]:
    """
    Safely load a JSON file with error handling.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dict if successful, None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None


def save_json_file(data: Dict, file_path: Path, indent: int = 2) -> bool:
    """
    Safely save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to save the file
        indent: JSON indentation level
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")
        return False


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        int: File size in bytes, or 0 if error
    """
    try:
        return file_path.stat().st_size
    except Exception:
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_timestamp() -> str:
    """
    Get current timestamp in ISO format.
    
    Returns:
        str: ISO formatted timestamp with Z suffix
    """
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_json_schema(data: Dict, schema: Dict) -> Tuple[bool, List[str]]:
    """
    Validate JSON data against a schema.
    
    Args:
        data: JSON data to validate
        schema: JSON schema
        
    Returns:
        tuple: (is_valid, list of error messages)
    """
    try:
        from jsonschema import validate, ValidationError
        validate(instance=data, schema=schema)
        return True, []
    except ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]


def calculate_score(value: float, min_val: float, max_val: float, reverse: bool = False) -> int:
    """
    Calculate a score from 0-100 based on a value and range.
    
    Args:
        value: The value to score
        min_val: Minimum value in range
        max_val: Maximum value in range
        reverse: If True, lower values get higher scores
        
    Returns:
        int: Score from 0-100
    """
    if max_val == min_val:
        return 100
    
    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0, min(1, normalized))
    
    if reverse:
        normalized = 1 - normalized
    
    return int(normalized * 100)


def find_files_by_pattern(root: Path, patterns: List[str]) -> List[Path]:
    """
    Find files matching patterns in directory tree.
    
    Args:
        root: Root directory to search
        patterns: List of glob patterns (e.g., ['*.json', '*.py'])
        
    Returns:
        List[Path]: List of matching file paths
    """
    files = []
    for pattern in patterns:
        files.extend(root.rglob(pattern))
    return sorted(files)


def read_text_file(file_path: Path) -> Optional[str]:
    """
    Read a text file with error handling.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str if successful, None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None
