"""
Tests for the EVOLUCIONADOR analyzer engine.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analyzer import RepositoryAnalyzer


def test_analyzer_initialization():
    """Test that analyzer initializes correctly."""
    analyzer = RepositoryAnalyzer()
    assert analyzer.repo_root is not None
    assert isinstance(analyzer.results, dict)
    assert 'timestamp' in analyzer.results
    assert 'version' in analyzer.results


def test_workspace_scan():
    """Test workspace scanning functionality."""
    analyzer = RepositoryAnalyzer()
    result = analyzer.scan_workspace()
    
    assert 'total_files' in result
    assert result['total_files'] > 0
    assert 'by_type' in result
    assert 'json_files' in result


def test_readme_compliance():
    """Test README compliance validation."""
    analyzer = RepositoryAnalyzer()
    result = analyzer.validate_readme_compliance()
    
    assert 'score' in result
    assert 'files_checked' in result
    assert isinstance(result['score'], int)
    assert 0 <= result['score'] <= 100


def test_knowledge_base_analysis():
    """Test knowledge base analysis."""
    analyzer = RepositoryAnalyzer()
    result = analyzer.analyze_knowledge_base()
    
    assert 'files_analyzed' in result
    assert 'valid_json' in result
    assert 'score' in result


def test_efficiency_scores():
    """Test efficiency score calculation."""
    analyzer = RepositoryAnalyzer()
    analyzer.scan_workspace()
    scores = analyzer.calculate_efficiency_scores()
    
    assert 'overall' in scores
    assert 'functionality' in scores
    assert 'efficiency' in scores
    assert 0 <= scores['overall'] <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
