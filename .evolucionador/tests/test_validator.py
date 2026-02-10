"""
Tests for the EVOLUCIONADOR validator engine.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validator import ComprehensiveValidator, ValidationResult


def test_validator_initialization():
    """Test that validator initializes correctly."""
    validator = ComprehensiveValidator()
    assert validator is not None


def test_json_validation():
    """Test JSON validation."""
    validator = ComprehensiveValidator()
    
    # Test valid JSON
    valid_data = {"test": "data"}
    result = validator.json_validator.validate(valid_data, 'test.json')
    assert result.is_valid


def test_pricing_validation():
    """Test pricing consistency validation."""
    validator = ComprehensiveValidator()
    
    # Test pricing comparison
    pricing_data = {
        'file1': {'product_a': 100.0},
        'file2': {'product_a': 102.0}  # Within 5% tolerance
    }
    result = validator.pricing_validator.validate(pricing_data)
    # Should pass as within tolerance


def test_validation_result_structure():
    """Test ValidationResult structure."""
    result = ValidationResult(
        validator_name='test',
        is_valid=True,
        score=95,
        errors=[],
        warnings=[],
        metrics={'test': 1}
    )
    
    assert result.validator_name == 'test'
    assert result.is_valid is True
    assert result.score == 95


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
