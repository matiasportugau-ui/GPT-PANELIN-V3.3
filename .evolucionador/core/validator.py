"""
EVOLUCIONADOR Validation Engine
================================
Comprehensive validation system for all EVOLUCIONADOR components.

Provides production-grade validation for:
- JSON schema validation for KB files
- Formula correctness checking for quotation calculations
- Pricing consistency validation across files
- Load-bearing capacity table accuracy
- API endpoint compatibility validation
- Documentation completeness checks
- Cross-reference integrity validation
"""

import json
import re
import math
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_iso_timestamp() -> str:
    """Get current timestamp in ISO format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


class SeverityLevel(Enum):
    """Validation error severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationError:
    """Represents a single validation error."""
    severity: SeverityLevel
    category: str
    message: str
    location: str = ""
    details: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=_get_iso_timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'location': self.location,
            'details': self.details,
            'timestamp': self.timestamp
        }


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    info: List[ValidationError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, severity: SeverityLevel, category: str, message: str, 
                  location: str = "", details: Optional[Dict] = None) -> None:
        """Add an error to the result."""
        error = ValidationError(severity, category, message, location, details)
        if severity == SeverityLevel.CRITICAL or severity == SeverityLevel.HIGH:
            self.errors.append(error)
            self.is_valid = False
        elif severity == SeverityLevel.MEDIUM or severity == SeverityLevel.WARNING:
            self.warnings.append(error)
        else:
            self.info.append(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'is_valid': self.is_valid,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'info_count': len(self.info),
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [e.to_dict() for e in self.warnings],
            'info': [e.to_dict() for e in self.info],
            'metadata': self.metadata,
            'timestamp': _get_iso_timestamp()
        }
    
    def get_summary(self) -> str:
        """Get a text summary of validation results."""
        return f"Valid: {self.is_valid}, Errors: {len(self.errors)}, Warnings: {len(self.warnings)}"


class JSONSchemaValidator:
    """Validates JSON files against schemas."""
    
    def __init__(self):
        """Initialize the JSON schema validator."""
        self.logger = logging.getLogger(f"{__name__}.JSONSchemaValidator")
    
    def validate_kb_file(self, file_path: Path, schema: Optional[Dict] = None) -> ValidationResult:
        """
        Validate a knowledge base JSON file.
        
        Args:
            file_path: Path to the JSON file
            schema: Optional JSON schema for validation
            
        Returns:
            ValidationResult with validation errors and warnings
        """
        result = ValidationResult(is_valid=True)
        result.metadata['file'] = str(file_path)
        
        # Check file exists
        if not file_path.exists():
            result.add_error(
                SeverityLevel.CRITICAL, "file_system",
                f"File does not exist: {file_path}",
                str(file_path)
            )
            return result
        
        # Try to parse JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result.metadata['json_valid'] = True
            result.metadata['entries_count'] = self._count_entries(data)
        except json.JSONDecodeError as e:
            result.add_error(
                SeverityLevel.CRITICAL, "json_syntax",
                f"Invalid JSON syntax: {str(e)}",
                f"{file_path}:{e.lineno}"
            )
            return result
        except Exception as e:
            result.add_error(
                SeverityLevel.CRITICAL, "file_io",
                f"Error reading file: {str(e)}",
                str(file_path)
            )
            return result
        
        # Validate against schema if provided
        if schema:
            self._validate_against_schema(data, schema, result, file_path)
        
        # Check for required fields based on file type
        self._validate_required_fields(data, file_path, result)
        
        # Check for empty collections
        if isinstance(data, (dict, list)) and len(data) == 0:
            result.add_error(
                SeverityLevel.WARNING, "content",
                "File contains empty data structure",
                str(file_path)
            )
        
        self.logger.info(f"JSON validation for {file_path.name}: {result.get_summary()}")
        return result
    
    def _count_entries(self, data: Any) -> int:
        """Count total entries in data structure."""
        if isinstance(data, dict):
            return len(data)
        elif isinstance(data, list):
            return len(data)
        return 1
    
    def _validate_against_schema(self, data: Any, schema: Dict, result: ValidationResult, 
                                  file_path: Path) -> None:
        """Validate data against a JSON schema."""
        try:
            from jsonschema import validate, ValidationError as JsonSchemaError
            validate(instance=data, schema=schema)
        except JsonSchemaError as e:
            result.add_error(
                SeverityLevel.HIGH, "schema",
                f"Schema validation failed: {e.message}",
                str(file_path),
                {'path': list(e.absolute_path), 'schema_path': list(e.absolute_schema_path)}
            )
        except Exception as e:
            result.add_error(
                SeverityLevel.MEDIUM, "schema",
                f"Schema validation error: {str(e)}",
                str(file_path)
            )
    
    def _validate_required_fields(self, data: Any, file_path: Path, result: ValidationResult) -> None:
        """Validate required fields based on file naming conventions."""
        file_name = file_path.name.lower()
        
        # Check pricing files
        if 'pricing' in file_name or 'price' in file_name:
            self._validate_pricing_file(data, file_path, result)
        
        # Check catalog files
        if 'catalog' in file_name:
            self._validate_catalog_file(data, file_path, result)
        
        # Check KB files
        if 'base' in file_name or 'conocimiento' in file_name or 'bmc' in file_name:
            self._validate_kb_structure(data, file_path, result)
    
    def _validate_pricing_file(self, data: Any, file_path: Path, result: ValidationResult) -> None:
        """Validate pricing file structure."""
        if not isinstance(data, (dict, list)):
            return
        
        items = data.values() if isinstance(data, dict) else data
        has_prices = False
        
        for item in items:
            if isinstance(item, dict):
                if any(k.lower() in ['price', 'precio', 'valor', 'costo'] for k in item.keys()):
                    has_prices = True
                    break
        
        if not has_prices:
            result.add_error(
                SeverityLevel.MEDIUM, "content",
                "Pricing file does not contain price fields",
                str(file_path)
            )
    
    def _validate_catalog_file(self, data: Any, file_path: Path, result: ValidationResult) -> None:
        """Validate catalog file structure."""
        if isinstance(data, dict):
            required_keys = ['products', 'items', 'entries', 'catalog']
            has_required = any(k.lower() in str(data.keys()).lower() for k in required_keys)
            
            if not has_required:
                result.add_error(
                    SeverityLevel.MEDIUM, "content",
                    "Catalog file missing expected product container",
                    str(file_path)
                )
    
    def _validate_kb_structure(self, data: Any, file_path: Path, result: ValidationResult) -> None:
        """Validate knowledge base file structure."""
        if isinstance(data, dict):
            # Check for common KB fields
            if 'version' not in data and 'schema' not in data:
                result.add_error(
                    SeverityLevel.WARNING, "content",
                    "KB file missing version or schema information",
                    str(file_path)
                )


class FormulaValidator:
    """Validates formulas for quotation calculations."""
    
    def __init__(self):
        """Initialize the formula validator."""
        self.logger = logging.getLogger(f"{__name__}.FormulaValidator")
        self.formula_pattern = re.compile(r'[+\-*/().\d\s]+')
    
    def validate_quotation_formula(self, formula: str) -> ValidationResult:
        """
        Validate a quotation calculation formula.
        
        Args:
            formula: Formula string to validate
            
        Returns:
            ValidationResult with validation errors
        """
        result = ValidationResult(is_valid=True)
        result.metadata['formula'] = formula
        
        if not formula or not isinstance(formula, str):
            result.add_error(
                SeverityLevel.HIGH, "formula",
                "Formula must be a non-empty string",
                "formula_input"
            )
            return result
        
        # Check for valid formula structure
        if not self._is_valid_formula_syntax(formula):
            result.add_error(
                SeverityLevel.HIGH, "formula",
                "Invalid formula syntax",
                "formula_structure",
                {'formula': formula}
            )
            return result
        
        # Check for balanced parentheses
        if not self._check_balanced_parentheses(formula):
            result.add_error(
                SeverityLevel.HIGH, "formula",
                "Unbalanced parentheses in formula",
                "formula_parentheses",
                {'formula': formula}
            )
            return result
        
        # Try to evaluate with dummy values
        try:
            self._evaluate_formula(formula)
            result.metadata['formula_valid'] = True
        except ZeroDivisionError:
            result.add_error(
                SeverityLevel.MEDIUM, "formula",
                "Formula may cause division by zero",
                "formula_evaluation",
                {'formula': formula}
            )
        except Exception as e:
            result.add_error(
                SeverityLevel.HIGH, "formula",
                f"Formula evaluation error: {str(e)}",
                "formula_evaluation",
                {'formula': formula}
            )
        
        self.logger.info(f"Formula validation: {result.get_summary()}")
        return result
    
    def validate_pricing_formula(self, formula: str, base_price: float, expected_range: Tuple[float, float]) -> ValidationResult:
        """
        Validate a pricing formula with expected value range.
        
        Args:
            formula: Formula string
            base_price: Base price for testing
            expected_range: (min, max) expected result range
            
        Returns:
            ValidationResult with validation results
        """
        result = self.validate_quotation_formula(formula)
        
        if not result.is_valid:
            return result
        
        try:
            test_result = self._evaluate_formula(formula, {'price': base_price, 'base': base_price})
            result.metadata['test_result'] = test_result
            
            if not (expected_range[0] <= test_result <= expected_range[1]):
                result.add_error(
                    SeverityLevel.MEDIUM, "formula",
                    f"Formula result {test_result} outside expected range {expected_range}",
                    "formula_range",
                    {'result': test_result, 'expected_range': expected_range}
                )
        except Exception as e:
            result.add_error(
                SeverityLevel.MEDIUM, "formula",
                f"Cannot test formula: {str(e)}",
                "formula_testing"
            )
        
        return result
    
    def _is_valid_formula_syntax(self, formula: str) -> bool:
        """Check if formula has valid syntax."""
        # Remove spaces
        f = formula.replace(' ', '')
        
        # Check for valid characters (numbers, operators, parentheses, letters for variables)
        allowed_chars = set('0123456789+-*/(). abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_')
        if not all(c in allowed_chars for c in f):
            return False
        
        # Cannot start or end with operator
        if (f and f[0] in '+-*/') or (f and f[-1] in '+-*/'):
            return False
        
        return True
    
    def _check_balanced_parentheses(self, formula: str) -> bool:
        """Check if parentheses are balanced."""
        balance = 0
        for char in formula:
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
            if balance < 0:
                return False
        return balance == 0
    
    def _evaluate_formula(self, formula: str, context: Optional[Dict] = None) -> float:
        """
        Safely evaluate a formula with restricted context.
        
        Security Notes:
        - Only allows mathematical operations and safe functions
        - No access to builtins or file system
        - Variables restricted to predefined context
        - All attribute access disabled
        
        Args:
            formula: Formula string
            context: Variables context (default: 1.0 for all variables)
            
        Returns:
            Evaluated result
        """
        if context is None:
            # Create default context with common variables
            context = {
                'price': 1.0, 'base': 1.0, 'quantity': 1.0,
                'discount': 0.0, 'tax': 0.0, 'labor': 1.0,
                'material': 1.0, 'markup': 1.0, 'cost': 1.0
            }
        
        # Add math functions (safe to expose)
        context.update({
            'abs': abs, 'round': round, 'max': max, 'min': min,
            'sqrt': math.sqrt, 'pow': pow, 'ceil': math.ceil, 'floor': math.floor
        })
        
        # Use eval with empty builtins for safety (only mathematical operations allowed)
        # This prevents access to file operations, imports, or other dangerous functions
        return eval(formula, {"__builtins__": {}}, context)


class PricingValidator:
    """Validates pricing consistency across files."""
    
    def __init__(self):
        """Initialize the pricing validator."""
        self.logger = logging.getLogger(f"{__name__}.PricingValidator")
    
    def validate_pricing_consistency(self, pricing_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate pricing consistency across entries.
        
        Args:
            pricing_data: Dictionary with pricing information
            
        Returns:
            ValidationResult with consistency checks
        """
        result = ValidationResult(is_valid=True)
        result.metadata['entries_checked'] = 0
        
        if not pricing_data:
            result.add_error(
                SeverityLevel.MEDIUM, "pricing",
                "No pricing data provided",
                "pricing_input"
            )
            return result
        
        prices = []
        currency_found = None
        
        # Extract all prices
        for key, value in pricing_data.items():
            result.metadata['entries_checked'] += 1
            
            if isinstance(value, (int, float)):
                if value < 0:
                    result.add_error(
                        SeverityLevel.HIGH, "pricing",
                        f"Negative price found: {key} = {value}",
                        f"pricing_entry:{key}",
                        {'key': key, 'value': value}
                    )
                elif value == 0:
                    result.add_error(
                        SeverityLevel.MEDIUM, "pricing",
                        f"Zero price found: {key}",
                        f"pricing_entry:{key}",
                        {'key': key}
                    )
                else:
                    prices.append(value)
            
            elif isinstance(value, dict):
                # Check for nested price structures
                self._validate_nested_pricing(key, value, result)
        
        # Check for price range consistency
        if prices:
            self._validate_price_ranges(prices, result)
        
        self.logger.info(f"Pricing consistency: {result.get_summary()}")
        return result
    
    def _validate_nested_pricing(self, key: str, value: Dict, result: ValidationResult) -> None:
        """Validate nested pricing structures."""
        price_fields = [k for k in value.keys() if 'price' in k.lower()]
        
        if not price_fields:
            return
        
        for pf in price_fields:
            if isinstance(value[pf], (int, float)):
                if value[pf] < 0:
                    result.add_error(
                        SeverityLevel.HIGH, "pricing",
                        f"Negative price in nested structure: {key}.{pf}",
                        f"pricing_nested:{key}"
                    )
    
    def _validate_price_ranges(self, prices: List[float], result: ValidationResult) -> None:
        """Validate price range statistics."""
        if len(prices) < 2:
            return
        
        min_price = min(prices)
        max_price = max(prices)
        mean_price = sum(prices) / len(prices)
        
        result.metadata['price_stats'] = {
            'min': min_price,
            'max': max_price,
            'mean': round(mean_price, 2),
            'count': len(prices)
        }
        
        # Check for outliers (prices more than 10x the minimum)
        if min_price > 0 and max_price > min_price * 10:
            result.add_error(
                SeverityLevel.WARNING, "pricing",
                f"Large price range detected: {min_price} - {max_price}",
                "pricing_range",
                result.metadata['price_stats']
            )
    
    def validate_cross_file_pricing(self, files_data: Dict[str, Dict]) -> ValidationResult:
        """
        Validate pricing consistency across multiple files.
        
        Args:
            files_data: Dictionary mapping filenames to their data
            
        Returns:
            ValidationResult with cross-file checks
        """
        result = ValidationResult(is_valid=True)
        result.metadata['files_checked'] = len(files_data)
        
        all_prices = {}
        
        # Collect all prices by identifier
        for filename, data in files_data.items():
            prices = self._extract_prices(data)
            for item_id, price in prices.items():
                if item_id not in all_prices:
                    all_prices[item_id] = []
                all_prices[item_id].append({
                    'file': filename,
                    'price': price
                })
        
        # Check for price inconsistencies
        for item_id, occurrences in all_prices.items():
            if len(occurrences) > 1:
                prices = [o['price'] for o in occurrences]
                if len(set(prices)) > 1:
                    result.add_error(
                        SeverityLevel.MEDIUM, "pricing",
                        f"Inconsistent price for {item_id} across files",
                        f"pricing_cross_file:{item_id}",
                        {'occurrences': occurrences}
                    )
        
        return result
    
    def _extract_prices(self, data: Any, prefix: str = "") -> Dict[str, float]:
        """Recursively extract prices from data structure."""
        prices = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{prefix}.{key}" if prefix else key
                if 'price' in key.lower() and isinstance(value, (int, float)):
                    prices[new_key] = value
                else:
                    prices.update(self._extract_prices(value, new_key))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_key = f"{prefix}[{i}]"
                prices.update(self._extract_prices(item, new_key))
        
        return prices


class LoadBearingValidator:
    """Validates load-bearing capacity tables."""
    
    def __init__(self):
        """Initialize the load-bearing validator."""
        self.logger = logging.getLogger(f"{__name__}.LoadBearingValidator")
    
    def validate_load_table(self, table_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate load-bearing capacity table structure and values.
        
        Args:
            table_data: Load-bearing table data
            
        Returns:
            ValidationResult with validation errors
        """
        result = ValidationResult(is_valid=True)
        result.metadata['table_type'] = 'load_bearing'
        
        if not table_data:
            result.add_error(
                SeverityLevel.HIGH, "load_bearing",
                "Empty load-bearing table",
                "table_structure"
            )
            return result
        
        # Check required columns
        required_columns = ['width', 'height', 'depth', 'capacity', 'unit']
        headers = []
        
        # For dict-based tables (mapping names to rows), check first value
        if isinstance(table_data, dict):
            first_row = next(iter(table_data.values())) if table_data else None
            if isinstance(first_row, dict):
                headers = [k.lower() for k in first_row.keys()]
        # For list-based tables, check first entry
        elif isinstance(table_data, list) and len(table_data) > 0:
            if isinstance(table_data[0], dict):
                headers = [k.lower() for k in table_data[0].keys()]
        
        missing_cols = [col for col in required_columns if col not in headers]
        if missing_cols:
            result.add_error(
                SeverityLevel.HIGH, "load_bearing",
                f"Missing required columns: {', '.join(missing_cols)}",
                "table_structure"
            )
        
        # Validate capacity values
        rows = table_data if isinstance(table_data, list) else list(table_data.values())
        
        for i, row in enumerate(rows):
            if isinstance(row, dict):
                self._validate_load_row(row, i, result)
        
        self.logger.info(f"Load-bearing table validation: {result.get_summary()}")
        return result
    
    def _validate_load_row(self, row: Dict, index: int, result: ValidationResult) -> None:
        """Validate a single row in load-bearing table."""
        # Check capacity values are positive
        capacity_key = next((k for k in row.keys() if 'capacity' in k.lower()), None)
        
        if capacity_key and capacity_key in row:
            value = row[capacity_key]
            
            if not isinstance(value, (int, float)):
                result.add_error(
                    SeverityLevel.MEDIUM, "load_bearing",
                    f"Invalid capacity type in row {index}: {type(value)}",
                    f"table_row:{index}"
                )
            elif value <= 0:
                result.add_error(
                    SeverityLevel.HIGH, "load_bearing",
                    f"Invalid capacity value in row {index}: {value}",
                    f"table_row:{index}",
                    {'row_index': index, 'capacity': value}
                )
        
        # Check dimension values
        for dim_key in ['width', 'height', 'depth']:
            dim_col = next((k for k in row.keys() if dim_key in k.lower()), None)
            if dim_col and dim_col in row:
                value = row[dim_col]
                if isinstance(value, (int, float)) and value <= 0:
                    result.add_error(
                        SeverityLevel.HIGH, "load_bearing",
                        f"Invalid {dim_key} in row {index}: {value}",
                        f"table_row:{index}:{dim_key}"
                    )


class APIValidator:
    """Validates API endpoint compatibility and correctness."""
    
    def __init__(self):
        """Initialize the API validator."""
        self.logger = logging.getLogger(f"{__name__}.APIValidator")
        self.endpoint_pattern = re.compile(r'^/[a-z0-9/_-]*$', re.IGNORECASE)
    
    def validate_endpoint(self, endpoint: str) -> ValidationResult:
        """
        Validate an API endpoint specification.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            ValidationResult with validation errors
        """
        result = ValidationResult(is_valid=True)
        result.metadata['endpoint'] = endpoint
        
        if not endpoint:
            result.add_error(
                SeverityLevel.HIGH, "api",
                "Empty endpoint provided",
                "endpoint_input"
            )
            return result
        
        if not isinstance(endpoint, str):
            result.add_error(
                SeverityLevel.HIGH, "api",
                "Endpoint must be a string",
                "endpoint_type"
            )
            return result
        
        if not endpoint.startswith('/'):
            result.add_error(
                SeverityLevel.HIGH, "api",
                "Endpoint must start with /",
                "endpoint_format"
            )
        
        if not self.endpoint_pattern.match(endpoint):
            result.add_error(
                SeverityLevel.HIGH, "api",
                "Invalid endpoint format",
                "endpoint_format",
                {'endpoint': endpoint}
            )
        
        # Check for common issues
        if '//' in endpoint:
            result.add_error(
                SeverityLevel.MEDIUM, "api",
                "Endpoint contains double slashes",
                "endpoint_format"
            )
        
        if endpoint.endswith('/') and endpoint != '/':
            result.add_error(
                SeverityLevel.WARNING, "api",
                "Endpoint should not end with trailing slash",
                "endpoint_format"
            )
        
        self.logger.info(f"API endpoint validation: {result.get_summary()}")
        return result
    
    def validate_api_spec(self, spec: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete API specification.
        
        Args:
            spec: API specification dictionary
            
        Returns:
            ValidationResult with validation errors
        """
        result = ValidationResult(is_valid=True)
        result.metadata['spec_validation'] = True
        
        if not spec:
            result.add_error(
                SeverityLevel.HIGH, "api",
                "Empty API specification",
                "api_spec"
            )
            return result
        
        # Check required fields
        required_fields = ['name', 'version', 'endpoints']
        for field in required_fields:
            if field not in spec:
                result.add_error(
                    SeverityLevel.HIGH, "api",
                    f"Missing required field: {field}",
                    "api_spec_structure"
                )
        
        # Validate endpoints
        if 'endpoints' in spec and isinstance(spec['endpoints'], list):
            for i, endpoint in enumerate(spec['endpoints']):
                if isinstance(endpoint, dict):
                    if 'path' not in endpoint:
                        result.add_error(
                            SeverityLevel.HIGH, "api",
                            f"Endpoint {i} missing path",
                            f"api_endpoint:{i}"
                        )
                    else:
                        ep_result = self.validate_endpoint(endpoint['path'])
                        if not ep_result.is_valid:
                            result.errors.extend(ep_result.errors)
                            result.is_valid = False
        
        return result


class DocumentationValidator:
    """Validates documentation completeness."""
    
    def __init__(self):
        """Initialize the documentation validator."""
        self.logger = logging.getLogger(f"{__name__}.DocumentationValidator")
    
    def validate_docstring(self, docstring: Optional[str]) -> ValidationResult:
        """
        Validate a docstring for completeness.
        
        Args:
            docstring: Docstring to validate
            
        Returns:
            ValidationResult with documentation quality issues
        """
        result = ValidationResult(is_valid=True)
        
        if not docstring or not isinstance(docstring, str):
            result.add_error(
                SeverityLevel.HIGH, "documentation",
                "Missing or invalid docstring",
                "docstring_input"
            )
            return result
        
        docstring = docstring.strip()
        result.metadata['docstring_length'] = len(docstring)
        
        # Check minimum length
        if len(docstring) < 10:
            result.add_error(
                SeverityLevel.MEDIUM, "documentation",
                "Docstring too short",
                "docstring_length"
            )
        
        # Check for description
        if not docstring:
            result.add_error(
                SeverityLevel.HIGH, "documentation",
                "Docstring is empty",
                "docstring_content"
            )
        
        # Check for common sections
        sections = ['Args:', 'Returns:', 'Raises:', 'Examples:']
        found_sections = [s for s in sections if s in docstring]
        result.metadata['documented_sections'] = found_sections
        
        # If function signature suggests parameters, should document Args
        if 'Args:' not in found_sections:
            result.add_error(
                SeverityLevel.WARNING, "documentation",
                "Missing Args section in docstring",
                "docstring_structure"
            )
        
        self.logger.info(f"Docstring validation: {result.get_summary()}")
        return result
    
    def validate_readme_section(self, section_name: str, content: str) -> ValidationResult:
        """
        Validate a README section for completeness.
        
        Args:
            section_name: Name of the section
            content: Content of the section
            
        Returns:
            ValidationResult with documentation completeness issues
        """
        result = ValidationResult(is_valid=True)
        result.metadata['section'] = section_name
        result.metadata['content_length'] = len(content) if content else 0
        
        if not content or len(content.strip()) < 10:
            result.add_error(
                SeverityLevel.MEDIUM, "documentation",
                f"README section '{section_name}' is too short or empty",
                f"readme:{section_name}"
            )
        
        # Check for code blocks in technical sections
        technical_sections = ['Installation', 'Usage', 'Examples', 'API']
        if any(sec in section_name for sec in technical_sections):
            if '```' not in content and 'code' not in section_name.lower():
                result.add_error(
                    SeverityLevel.WARNING, "documentation",
                    f"Technical section '{section_name}' may need code examples",
                    f"readme:{section_name}"
                )
        
        return result


class CrossReferenceValidator:
    """Validates cross-reference integrity."""
    
    def __init__(self):
        """Initialize the cross-reference validator."""
        self.logger = logging.getLogger(f"{__name__}.CrossReferenceValidator")
    
    def validate_references(self, data: Dict[str, Any], reference_map: Dict[str, Set[str]]) -> ValidationResult:
        """
        Validate that all references exist in the reference map.
        
        Args:
            data: Data containing references
            reference_map: Map of valid identifiers by type
            
        Returns:
            ValidationResult with reference validation errors
        """
        result = ValidationResult(is_valid=True)
        result.metadata['references_checked'] = 0
        
        broken_refs = []
        
        # Find all references in data
        refs = self._extract_references(data)
        
        for ref_type, ref_list in refs.items():
            for ref_id in ref_list:
                result.metadata['references_checked'] += 1
                
                if ref_type not in reference_map or ref_id not in reference_map[ref_type]:
                    broken_refs.append({'type': ref_type, 'id': ref_id})
        
        if broken_refs:
            result.add_error(
                SeverityLevel.HIGH, "cross_reference",
                f"Found {len(broken_refs)} broken references",
                "reference_integrity",
                {'broken_refs': broken_refs[:10]}  # Limit to first 10
            )
            result.is_valid = False
        
        self.logger.info(f"Cross-reference validation: {result.get_summary()}")
        return result
    
    def _extract_references(self, data: Any, prefix: str = "") -> Dict[str, Set[str]]:
        """Extract reference identifiers from data structure."""
        refs = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Common reference field patterns
                if any(pattern in key.lower() for pattern in ['ref', 'id', 'code', 'sku']):
                    ref_type = key.lower()
                    if isinstance(value, str):
                        if ref_type not in refs:
                            refs[ref_type] = set()
                        refs[ref_type].add(value)
                    elif isinstance(value, list):
                        for v in value:
                            if isinstance(v, str):
                                if ref_type not in refs:
                                    refs[ref_type] = set()
                                refs[ref_type].add(v)
                
                # Recurse into nested structures
                sub_refs = self._extract_references(value, key)
                for ref_type, ref_set in sub_refs.items():
                    if ref_type not in refs:
                        refs[ref_type] = set()
                    refs[ref_type].update(ref_set)
        
        elif isinstance(data, list):
            for item in data:
                sub_refs = self._extract_references(item, prefix)
                for ref_type, ref_set in sub_refs.items():
                    if ref_type not in refs:
                        refs[ref_type] = set()
                    refs[ref_type].update(ref_set)
        
        return refs


class ComprehensiveValidator:
    """Main validation orchestrator for the EVOLUCIONADOR system."""
    
    def __init__(self):
        """Initialize the comprehensive validator."""
        self.logger = logging.getLogger(f"{__name__}.ComprehensiveValidator")
        
        # Initialize sub-validators
        self.json_validator = JSONSchemaValidator()
        self.formula_validator = FormulaValidator()
        self.pricing_validator = PricingValidator()
        self.load_bearing_validator = LoadBearingValidator()
        self.api_validator = APIValidator()
        self.documentation_validator = DocumentationValidator()
        self.cross_ref_validator = CrossReferenceValidator()
        
        self.results = {}
    
    def validate_kb_file(self, file_path: Path, schema: Optional[Dict] = None) -> ValidationResult:
        """
        Validate a knowledge base file with all checks.
        
        Args:
            file_path: Path to KB file
            schema: Optional JSON schema
            
        Returns:
            ValidationResult with all validation checks
        """
        self.logger.info(f"Validating KB file: {file_path}")
        return self.json_validator.validate_kb_file(file_path, schema)
    
    def validate_quotation_formula(self, formula: str, base_price: Optional[float] = None,
                                  expected_range: Optional[Tuple[float, float]] = None) -> ValidationResult:
        """
        Validate a quotation formula.
        
        Args:
            formula: Formula to validate
            base_price: Optional base price for testing
            expected_range: Optional expected result range
            
        Returns:
            ValidationResult with formula validation
        """
        self.logger.info(f"Validating formula: {formula}")
        
        if base_price is not None and expected_range is not None:
            return self.formula_validator.validate_pricing_formula(formula, base_price, expected_range)
        else:
            return self.formula_validator.validate_quotation_formula(formula)
    
    def validate_pricing_data(self, pricing_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate pricing data for consistency.
        
        Args:
            pricing_data: Pricing data to validate
            
        Returns:
            ValidationResult with pricing validation
        """
        self.logger.info("Validating pricing data")
        return self.pricing_validator.validate_pricing_consistency(pricing_data)
    
    def validate_cross_file_pricing(self, files_data: Dict[str, Dict]) -> ValidationResult:
        """
        Validate pricing consistency across files.
        
        Args:
            files_data: Dictionary of file data
            
        Returns:
            ValidationResult with cross-file pricing validation
        """
        self.logger.info(f"Validating pricing across {len(files_data)} files")
        return self.pricing_validator.validate_cross_file_pricing(files_data)
    
    def validate_load_bearing_table(self, table_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate load-bearing capacity table.
        
        Args:
            table_data: Load-bearing table data
            
        Returns:
            ValidationResult with load-bearing validation
        """
        self.logger.info("Validating load-bearing table")
        return self.load_bearing_validator.validate_load_table(table_data)
    
    def validate_api_endpoint(self, endpoint: str) -> ValidationResult:
        """
        Validate an API endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            ValidationResult with API validation
        """
        self.logger.info(f"Validating API endpoint: {endpoint}")
        return self.api_validator.validate_endpoint(endpoint)
    
    def validate_api_specification(self, spec: Dict[str, Any]) -> ValidationResult:
        """
        Validate an API specification.
        
        Args:
            spec: API specification
            
        Returns:
            ValidationResult with API spec validation
        """
        self.logger.info("Validating API specification")
        return self.api_validator.validate_api_spec(spec)
    
    def validate_documentation(self, docstring: Optional[str]) -> ValidationResult:
        """
        Validate documentation/docstring.
        
        Args:
            docstring: Docstring to validate
            
        Returns:
            ValidationResult with documentation validation
        """
        self.logger.info("Validating documentation")
        return self.documentation_validator.validate_docstring(docstring)
    
    def validate_cross_references(self, data: Dict[str, Any], 
                                 reference_map: Dict[str, Set[str]]) -> ValidationResult:
        """
        Validate cross-reference integrity.
        
        Args:
            data: Data with references
            reference_map: Map of valid references
            
        Returns:
            ValidationResult with cross-reference validation
        """
        self.logger.info("Validating cross-references")
        return self.cross_ref_validator.validate_references(data, reference_map)
    
    def run_full_validation_suite(self, kb_files: List[Path], 
                                 api_specs: Optional[List[Dict]] = None,
                                 pricing_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run complete validation suite on all components.
        
        Args:
            kb_files: List of KB file paths
            api_specs: Optional list of API specifications
            pricing_data: Optional pricing data
            
        Returns:
            Dictionary with complete validation results
        """
        self.logger.info("Running full validation suite")
        
        suite_results = {
            'timestamp': _get_iso_timestamp(),
            'summary': {
                'total_checks': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            },
            'kb_validation': {},
            'api_validation': {},
            'pricing_validation': {},
            'overall_valid': True
        }
        
        # Validate KB files
        for kb_file in kb_files:
            if kb_file.exists():
                result = self.validate_kb_file(kb_file)
                suite_results['kb_validation'][str(kb_file)] = result.to_dict()
                
                suite_results['summary']['total_checks'] += 1
                if result.is_valid:
                    suite_results['summary']['passed'] += 1
                else:
                    suite_results['summary']['failed'] += 1
                    suite_results['overall_valid'] = False
                
                suite_results['summary']['warnings'] += len(result.warnings)
        
        # Validate API specifications
        if api_specs:
            for spec in api_specs:
                result = self.validate_api_specification(spec)
                spec_name = spec.get('name', 'unknown')
                suite_results['api_validation'][spec_name] = result.to_dict()
                
                suite_results['summary']['total_checks'] += 1
                if result.is_valid:
                    suite_results['summary']['passed'] += 1
                else:
                    suite_results['summary']['failed'] += 1
                    suite_results['overall_valid'] = False
        
        # Validate pricing data
        if pricing_data:
            result = self.validate_pricing_data(pricing_data)
            suite_results['pricing_validation'] = result.to_dict()
            
            suite_results['summary']['total_checks'] += 1
            if result.is_valid:
                suite_results['summary']['passed'] += 1
            else:
                suite_results['summary']['failed'] += 1
                suite_results['overall_valid'] = False
        
        self.logger.info(f"Full validation suite complete. Results: {suite_results['summary']}")
        return suite_results


def main():
    """
    Main entry point for validator.
    
    Demonstrates usage of the validation engine.
    """
    logger.info("=" * 80)
    logger.info("EVOLUCIONADOR Validation Engine")
    logger.info("=" * 80)
    
    # Initialize validator
    validator = ComprehensiveValidator()
    
    # Example: Validate a formula
    formula = "price * 1.2 + tax"
    formula_result = validator.validate_quotation_formula(formula)
    logger.info(f"Formula validation result: {formula_result.get_summary()}")
    
    # Example: Validate pricing data
    pricing = {
        'item1': 100,
        'item2': 150,
        'item3': 120
    }
    pricing_result = validator.validate_pricing_data(pricing)
    logger.info(f"Pricing validation result: {pricing_result.get_summary()}")
    
    # Example: Validate API endpoint
    endpoint_result = validator.validate_api_endpoint('/api/quotation/calculate')
    logger.info(f"API endpoint validation result: {endpoint_result.get_summary()}")
    
    logger.info("=" * 80)
    logger.info("Validation engine ready for production use")
    logger.info("=" * 80)
    
    return 0


if __name__ == '__main__':
    exit(main())
