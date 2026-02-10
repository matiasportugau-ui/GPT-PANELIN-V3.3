#!/usr/bin/env python3
"""
boot_preload.py - Panelin GPT Knowledge Ingestion Pipeline

Purpose:
    Prepares and indexes knowledge base files for GPT consumption.
    Creates knowledge_index.json with metadata and file hashes.
    Optionally generates vector embeddings for semantic search.

Environment Variables:
    PANELIN_ROOT          - Repository root directory
    GENERATE_EMBEDDINGS   - Generate embeddings (0=no, 1=yes, default: 0)
    PANELIN_API_KEY       - API key for embeddings service (if GENERATE_EMBEDDINGS=1)
    KNOWLEDGE_DIRS        - Colon-separated list of dirs to index (default: auto-detect)
    ALLOWED_EXTENSIONS    - Comma-separated file extensions (default: .json,.md,.txt,.csv,.rtf)

Exit Codes:
    0 - Success
    1 - Configuration error
    2 - File access error
    3 - Indexing error
    4 - Embedding generation error
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)

# Configuration
PANELIN_ROOT = Path(os.getenv('PANELIN_ROOT', Path(__file__).parent))
GENERATE_EMBEDDINGS = int(os.getenv('GENERATE_EMBEDDINGS', '0'))
PANELIN_API_KEY = os.getenv('PANELIN_API_KEY', '')
KNOWLEDGE_INDEX_PATH = PANELIN_ROOT / 'knowledge_index.json'

# Default knowledge directories to scan
DEFAULT_KNOWLEDGE_DIRS = [
    'docs',
    'panelin_reports',
    '.evolucionador/knowledge',
]

# Allowed file extensions for knowledge base
DEFAULT_ALLOWED_EXTENSIONS = {'.json', '.md', '.txt', '.csv', '.rtf'}

# File patterns to exclude
EXCLUDE_PATTERNS = {
    'node_modules',
    '.git',
    '.venv',
    'venv',
    '__pycache__',
    '.pyc',
    'package-lock.json',
    '.boot-log',
    '.boot-ready',
}


class KnowledgeIndexer:
    """Indexes knowledge base files and creates metadata."""
    
    def __init__(
        self,
        root_dir: Path,
        knowledge_dirs: Optional[List[str]] = None,
        allowed_extensions: Optional[Set[str]] = None
    ):
        self.root_dir = root_dir
        self.knowledge_dirs = knowledge_dirs or DEFAULT_KNOWLEDGE_DIRS
        self.allowed_extensions = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS
        self.index: Dict = {
            'version': '1.0',
            'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'root_directory': str(root_dir),
            'embeddings_enabled': bool(GENERATE_EMBEDDINGS),
            'files': []
        }
        self.stats = {
            'total_files': 0,
            'indexed_files': 0,
            'total_size_bytes': 0,
            'errors': 0
        }
    
    def should_include_file(self, file_path: Path) -> bool:
        """Check if file should be included in index."""
        # Check extension
        if file_path.suffix.lower() not in self.allowed_extensions:
            return False
        
        # Check exclude patterns
        parts = file_path.parts
        for pattern in EXCLUDE_PATTERNS:
            if pattern in parts or pattern in file_path.name:
                return False
        
        return True
    
    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash {file_path}: {e}")
            raise
    
    def validate_json_file(self, file_path: Path) -> bool:
        """Validate that a JSON file is parseable."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return False
    
    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from a file."""
        try:
            stat = file_path.stat()
            file_hash = self.compute_file_hash(file_path)
            
            metadata = {
                'path': str(file_path.relative_to(self.root_dir)),
                'absolute_path': str(file_path),
                'name': file_path.name,
                'extension': file_path.suffix.lower(),
                'size_bytes': stat.st_size,
                'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z'),
                'sha256': file_hash,
                'valid': True
            }
            
            # Validate JSON files
            if file_path.suffix.lower() == '.json':
                metadata['valid'] = self.validate_json_file(file_path)
            
            return metadata
        
        except Exception as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            self.stats['errors'] += 1
            return None
    
    def scan_directory(self, directory: Path) -> List[Path]:
        """Recursively scan directory for knowledge files."""
        files = []
        
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return files
        
        try:
            for item in directory.rglob('*'):
                if item.is_file() and self.should_include_file(item):
                    files.append(item)
                    self.stats['total_files'] += 1
        except Exception as e:
            logger.error(f"Error scanning {directory}: {e}")
            self.stats['errors'] += 1
        
        return files
    
    def index_files(self):
        """Index all knowledge base files."""
        logger.info("Starting knowledge base indexing")
        logger.info(f"Root directory: {self.root_dir}")
        logger.info(f"Knowledge directories: {self.knowledge_dirs}")
        logger.info(f"Allowed extensions: {self.allowed_extensions}")
        
        all_files = []
        
        # Scan each knowledge directory
        for dir_name in self.knowledge_dirs:
            dir_path = self.root_dir / dir_name
            logger.info(f"Scanning directory: {dir_path}")
            files = self.scan_directory(dir_path)
            all_files.extend(files)
            logger.info(f"Found {len(files)} files in {dir_name}")
        
        # Also index root-level knowledge files
        for pattern in ['*.json', '*.md', '*.txt', '*.csv', '*.rtf']:
            for file_path in self.root_dir.glob(pattern):
                if self.should_include_file(file_path) and file_path not in all_files:
                    all_files.append(file_path)
                    self.stats['total_files'] += 1
        
        logger.info(f"Total files found: {len(all_files)}")
        
        # Extract metadata for each file
        for file_path in all_files:
            metadata = self.extract_metadata(file_path)
            if metadata:
                self.index['files'].append(metadata)
                self.stats['indexed_files'] += 1
                self.stats['total_size_bytes'] += metadata['size_bytes']
        
        # Sort files by path for consistent ordering
        self.index['files'].sort(key=lambda x: x['path'])
        
        # Add statistics to index
        self.index['statistics'] = {
            'total_files_scanned': self.stats['total_files'],
            'files_indexed': self.stats['indexed_files'],
            'total_size_bytes': self.stats['total_size_bytes'],
            'total_size_mb': round(self.stats['total_size_bytes'] / (1024 * 1024), 2),
            'errors': self.stats['errors']
        }
        
        logger.info(f"Indexed {self.stats['indexed_files']} files")
        logger.info(f"Total size: {self.index['statistics']['total_size_mb']} MB")
        
        if self.stats['errors'] > 0:
            logger.warning(f"Encountered {self.stats['errors']} errors during indexing")
    
    def generate_embeddings(self):
        """Generate vector embeddings for knowledge base (placeholder)."""
        if not GENERATE_EMBEDDINGS:
            logger.info("Embedding generation disabled (GENERATE_EMBEDDINGS=0)")
            return
        
        if not PANELIN_API_KEY:
            logger.warning("PANELIN_API_KEY not set, skipping embeddings")
            logger.warning("Set PANELIN_API_KEY to enable embedding generation")
            return
        
        logger.info("Embedding generation requested but not yet implemented")
        logger.info("This is a placeholder for future embedding pipeline")
        logger.info("Files are indexed and ready for embedding integration")
        
        # Add embedding placeholder to index
        self.index['embeddings'] = {
            'enabled': True,
            'status': 'not_implemented',
            'note': 'Embedding pipeline is a placeholder for future implementation'
        }
    
    def save_index(self):
        """Save the knowledge index to disk."""
        try:
            logger.info(f"Writing index to {KNOWLEDGE_INDEX_PATH}")
            
            with open(KNOWLEDGE_INDEX_PATH, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Knowledge index saved successfully")
            logger.info(f"Index contains {len(self.index['files'])} files")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise


def validate_environment():
    """Validate environment and configuration."""
    logger.info("Validating environment")
    
    # Check root directory
    if not PANELIN_ROOT.exists():
        logger.error(f"Root directory does not exist: {PANELIN_ROOT}")
        sys.exit(1)
    
    if not PANELIN_ROOT.is_dir():
        logger.error(f"Root path is not a directory: {PANELIN_ROOT}")
        sys.exit(1)
    
    # Check write permissions
    if not os.access(PANELIN_ROOT, os.W_OK):
        logger.error(f"No write permission to root directory: {PANELIN_ROOT}")
        sys.exit(2)
    
    logger.info(f"Environment validation passed")
    logger.info(f"Root: {PANELIN_ROOT}")
    logger.info(f"Embeddings: {GENERATE_EMBEDDINGS}")


def main():
    """Main execution function."""
    logger.info("="*60)
    logger.info("Panelin GPT Knowledge Ingestion Pipeline")
    logger.info("="*60)
    
    try:
        # Validate environment
        validate_environment()
        
        # Parse custom knowledge directories if provided
        knowledge_dirs_env = os.getenv('KNOWLEDGE_DIRS', '')
        knowledge_dirs = knowledge_dirs_env.split(':') if knowledge_dirs_env else None
        
        # Parse custom extensions if provided
        extensions_env = os.getenv('ALLOWED_EXTENSIONS', '')
        allowed_extensions = set(extensions_env.split(',')) if extensions_env else None
        
        # Create indexer
        indexer = KnowledgeIndexer(
            root_dir=PANELIN_ROOT,
            knowledge_dirs=knowledge_dirs,
            allowed_extensions=allowed_extensions
        )
        
        # Run indexing
        indexer.index_files()
        
        # Generate embeddings if requested
        indexer.generate_embeddings()
        
        # Save index
        indexer.save_index()
        
        logger.info("="*60)
        logger.info("Knowledge ingestion completed successfully")
        logger.info("="*60)
        
        return 0
    
    except Exception as e:
        logger.error(f"Knowledge ingestion failed: {e}")
        logger.error("See logs above for details")
        return 3


if __name__ == '__main__':
    sys.exit(main())
