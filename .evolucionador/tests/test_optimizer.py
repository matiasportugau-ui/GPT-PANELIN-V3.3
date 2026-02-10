"""
Tests for the EVOLUCIONADOR optimizer engine.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.optimizer import create_optimizer, OptimizationResult


def test_optimizer_creation():
    """Test that optimizer can be created."""
    optimizer = create_optimizer()
    assert optimizer is not None


def test_json_optimization():
    """Test JSON optimization."""
    optimizer = create_optimizer()
    
    # Test data with optimization potential
    test_data = {
        'key1': 'value',
        'key2': None,  # Can be removed
        'key3': [],    # Empty, can be removed
        'key4': {}     # Empty, can be removed
    }
    
    result = optimizer.json_optimizer.optimize(test_data)
    assert result.efficiency_gain > 0


def test_optimization_result_structure():
    """Test OptimizationResult structure."""
    result = OptimizationResult(
        optimizer_name='test',
        original_value=100,
        optimized_value=80,
        efficiency_gain=20.0,
        metrics={'reduction': '20%'}
    )
    
    assert result.optimizer_name == 'test'
    assert result.efficiency_gain == 20.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
