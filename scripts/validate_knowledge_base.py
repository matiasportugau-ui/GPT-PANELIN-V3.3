#!/usr/bin/env python3
"""
==============================================================================
GPT-PANELIN-V3.2 Knowledge Base Validation Script
==============================================================================
Validates all JSON files in the knowledge base for correctness and integrity.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def log_info(message: str) -> None:
    """Log info message."""
    print(f"{BLUE}[INFO]{NC} {message}")


def log_success(message: str) -> None:
    """Log success message."""
    print(f"{GREEN}[✓]{NC} {message}")


def log_error(message: str) -> None:
    """Log error message."""
    print(f"{RED}[✗]{NC} {message}")


def log_warning(message: str) -> None:
    """Log warning message."""
    print(f"{YELLOW}[!]{NC} {message}")


class KnowledgeBaseValidator:
    """Validator for knowledge base JSON files."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validated_files = 0
        
        # Define knowledge base files with their validation rules
        self.kb_files = {
            'bromyros_pricing_master.json': {
                'required': True,
                'min_size': 100000,
                'required_keys': ['meta', 'data'],
                'description': 'BROMYROS pricing master database'
            },
            'bromyros_pricing_gpt_optimized.json': {
                'required': True,
                'min_size': 50000,
                'required_keys': None,
                'description': 'BROMYROS pricing optimized for GPT'
            },
            'BMC_Base_Conocimiento_GPT-2.json': {
                'required': True,
                'min_size': 1000,
                'required_keys': None,
                'description': 'Core knowledge base'
            },
            'bom_rules.json': {
                'required': True,
                'min_size': 1000,
                'required_keys': None,
                'description': 'Bill of Materials rules'
            },
            'accessories_catalog.json': {
                'required': True,
                'min_size': 1000,
                'required_keys': None,
                'description': 'Accessories catalog'
            },
            'shopify_catalog_v1.json': {
                'required': True,
                'min_size': 50000,
                'required_keys': None,
                'description': 'Shopify product catalog'
            },
            'corrections_log.json': {
                'required': False,
                'min_size': 0,
                'required_keys': None,
                'description': 'Knowledge base corrections log'
            }
        }
    
    def validate_file(self, filename: str, config: Dict[str, Any]) -> bool:
        """Validate a single JSON file."""
        log_info(f"Validating {config['description']}: {filename}")
        
        file_path = self.project_root / filename
        
        # Check if file exists
        if not file_path.exists():
            if config['required']:
                self.errors.append(f"{filename}: Required file not found")
                log_error(f"{filename} not found")
                return False
            else:
                self.warnings.append(f"{filename}: Optional file not found")
                log_warning(f"{filename} not found (optional)")
                return True
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size < config['min_size']:
            self.warnings.append(
                f"{filename}: File size {file_size} is smaller than expected {config['min_size']}"
            )
            log_warning(f"{filename} size is {file_size} bytes (expected at least {config['min_size']})")
        
        # Validate JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required keys if specified
            if config['required_keys'] and isinstance(data, dict):
                missing_keys = [key for key in config['required_keys'] if key not in data]
                if missing_keys:
                    self.errors.append(f"{filename}: Missing required keys: {missing_keys}")
                    log_error(f"{filename} missing keys: {missing_keys}")
                    return False
            
            # File is valid
            if isinstance(data, dict):
                log_success(f"{filename} is valid (dict with {len(data)} keys, {file_size:,} bytes)")
            elif isinstance(data, list):
                log_success(f"{filename} is valid (list with {len(data)} items, {file_size:,} bytes)")
            else:
                log_success(f"{filename} is valid JSON ({file_size:,} bytes)")
            
            self.validated_files += 1
            return True
        
        except json.JSONDecodeError as e:
            self.errors.append(f"{filename}: Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}")
            log_error(f"{filename} has invalid JSON: {e}")
            return False
        
        except Exception as e:
            self.errors.append(f"{filename}: Error reading file: {str(e)}")
            log_error(f"{filename} error: {e}")
            return False
    
    def validate_pricing_structure(self) -> bool:
        """Validate pricing master file structure in detail."""
        log_info("Performing deep validation of pricing master structure")
        
        file_path = self.project_root / 'bromyros_pricing_master.json'
        if not file_path.exists():
            return True  # Already reported as error in basic validation
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check structure
            if 'data' not in data or 'products' not in data['data']:
                self.errors.append("bromyros_pricing_master.json: Missing data.products structure")
                log_error("Invalid pricing structure: missing data.products")
                return False
            
            products = data['data']['products']
            if not isinstance(products, list):
                self.errors.append("bromyros_pricing_master.json: products should be a list")
                log_error("Invalid pricing structure: products is not a list")
                return False
            
            # Validate sample products
            if len(products) == 0:
                self.warnings.append("bromyros_pricing_master.json: No products found")
                log_warning("No products in pricing database")
            else:
                log_success(f"Found {len(products)} products in pricing database")
                
                # Sample check first product
                product = products[0]
                required_fields = ['sku', 'specifications', 'pricing']
                missing = [f for f in required_fields if f not in product]
                if missing:
                    self.warnings.append(f"Sample product missing fields: {missing}")
                    log_warning(f"Sample product structure incomplete: {missing}")
                else:
                    log_success("Sample product has expected structure")
            
            return True
        
        except Exception as e:
            log_warning(f"Could not perform deep pricing validation: {e}")
            return True  # Don't fail on deep validation errors
    
    def validate_all(self) -> bool:
        """Validate all knowledge base files."""
        log_info("=" * 70)
        log_info("GPT-PANELIN-V3.2 Knowledge Base Validation")
        log_info("=" * 70)
        print()
        
        # Validate each file
        for filename, config in self.kb_files.items():
            self.validate_file(filename, config)
            print()
        
        # Perform deep validations
        self.validate_pricing_structure()
        print()
        
        # Print summary
        log_info("=" * 70)
        log_info("Validation Summary")
        log_info("=" * 70)
        log_info(f"Files validated: {self.validated_files}/{len(self.kb_files)}")
        
        if self.warnings:
            log_warning(f"Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            log_error(f"Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"  - {error}")
            print()
            log_error("Knowledge base validation FAILED")
            return False
        else:
            print()
            log_success("Knowledge base validation PASSED")
            return True


def main() -> int:
    """Main function."""
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Create validator
    validator = KnowledgeBaseValidator(project_root)
    
    # Run validation
    success = validator.validate_all()
    
    # Return exit code
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
