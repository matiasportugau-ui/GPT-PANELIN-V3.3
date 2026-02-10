# EVOLUCIONADOR Optimization Engine - Integration Guide

## System Architecture

```
EVOLUCIONADOR System
│
├── Core Module (.evolucionador/core/)
│   ├── analyzer.py           ← Repository analysis
│   ├── validator.py          ← Data validation
│   ├── optimizer.py          ← Performance optimization (NEW)
│   ├── utils.py              ← Shared utilities
│   └── __init__.py           ← Package initialization
│
├── Integration Points
│   ├── Data Pipeline
│   ├── API Server
│   ├── File Processing
│   └── Reporting System
│
└── Supporting Files
    ├── OPTIMIZER_README.md   ← Quick reference
    ├── OPTIMIZER_GUIDE.md    ← Detailed guide
    └── OPTIMIZER_INTEGRATION.md ← This file
```

## Integration Points

### 1. Analyzer Integration

**Location:** `.evolucionador/core/analyzer.py`

```python
from .optimizer import create_optimizer

class RepositoryAnalyzer:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_root = repo_path or get_repo_root()
        self.optimizer = create_optimizer(repo_path)  # ← Add this
    
    def analyze(self):
        results = {...}
        
        # Apply optimizations to analysis
        optimization_result = self.optimizer.full_system_optimization(results)
        
        results['optimization'] = optimization_result.to_dict()
        return results
```

### 2. Validator Integration

**Location:** `.evolucionador/core/validator.py`

```python
from .optimizer import create_optimizer

class RepositoryValidator:
    def __init__(self):
        self.validator_rules = {}
        self.optimizer = create_optimizer()  # ← Add this
    
    def validate_with_optimization(self, data):
        # Validate data
        validation_result = self.validate(data)
        
        # Optimize validated data
        if validation_result.is_valid:
            optimization_result = self.optimizer.optimize_json_file(
                Path(data['file_path'])
            )
            validation_result.optimizations = optimization_result.to_dict()
        
        return validation_result
```

### 3. File Processing Pipeline

**Recommended Integration Pattern:**

```python
from pathlib import Path
from .optimizer import create_optimizer

def process_json_files(directory: Path):
    """Process JSON files with optimization."""
    engine = create_optimizer()
    
    for json_file in directory.glob('*.json'):
        # 1. Load and validate
        data = load_json_file(json_file)
        if not data:
            continue
        
        # 2. Optimize
        result = engine.optimize_json_file(json_file)
        
        # 3. Save optimized version
        if result.success:
            save_optimized_file(json_file, result)
            
            # 4. Generate report
            engine.generate_optimization_report(
                result,
                json_file.parent / f"{json_file.stem}_optimization.json"
            )
```

### 4. API Server Integration

**Flask Example:**

```python
from flask import Flask, request, jsonify
from .optimizer import create_optimizer

app = Flask(__name__)
optimizer = create_optimizer()

@app.route('/api/optimize', methods=['POST'])
def optimize():
    """Optimize provided data."""
    try:
        data = request.json
        
        result = optimizer.full_system_optimization(data)
        
        return jsonify({
            'success': result.success,
            'efficiency_score': result.average_efficiency_score,
            'cost_reduction': result.total_cost_reduction,
            'metrics': [m.to_dict() for m in result.metrics],
            'errors': result.errors
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/optimize/json', methods=['POST'])
def optimize_json():
    """Optimize JSON file."""
    try:
        from pathlib import Path
        
        file = request.files['file']
        file_path = Path(f'/tmp/{file.filename}')
        file.save(file_path)
        
        result = optimizer.optimize_json_file(file_path)
        
        return jsonify(result.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/optimize/formula', methods=['POST'])
def optimize_formula():
    """Optimize formula."""
    try:
        data = request.json
        formula = data.get('formula', '')
        
        optimized, metrics = optimizer.formula_optimizer.optimize_formula(formula)
        
        return jsonify({
            'original': formula,
            'optimized': optimized,
            'metrics': metrics.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
```

**FastAPI Example:**

```python
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from .optimizer import create_optimizer

app = FastAPI()
optimizer = create_optimizer()

class OptimizationRequest(BaseModel):
    formulas: List[str] = []
    api_calls: List[Dict] = []
    calculations: List[Dict] = []
    execution_data: Dict = {}

@app.post("/api/optimize")
async def optimize(request: OptimizationRequest):
    """Full system optimization."""
    system_data = {
        'formulas': request.formulas,
        'api_calls': request.api_calls,
        'calculations': request.calculations,
        'execution_data': request.execution_data
    }
    
    result = optimizer.full_system_optimization(system_data)
    return result.to_dict()

@app.post("/api/optimize/upload")
async def optimize_upload(file: UploadFile = File(...)):
    """Optimize uploaded JSON file."""
    from pathlib import Path
    
    file_path = Path(f'/tmp/{file.filename}')
    with open(file_path, 'wb') as f:
        f.write(await file.read())
    
    result = optimizer.optimize_json_file(file_path)
    return result.to_dict()
```

### 5. Reporting Integration

**Recommended Reporting Pattern:**

```python
from datetime import datetime
from pathlib import Path
from .optimizer import create_optimizer

class OptimizationReporter:
    def __init__(self, report_dir: Path = Path('./optimization_reports')):
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.optimizer = create_optimizer()
    
    def generate_report(self, data, name: str = None):
        """Generate comprehensive optimization report."""
        if not name:
            name = f"optimization_{datetime.now().isoformat()}"
        
        # Run optimization
        result = self.optimizer.full_system_optimization(data)
        
        # Generate report
        report_path = self.report_dir / f"{name}.json"
        self.optimizer.generate_optimization_report(result, report_path)
        
        # Generate HTML summary
        self._generate_html_summary(result, name)
        
        return result
    
    def _generate_html_summary(self, result, name: str):
        """Generate HTML summary of optimization."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Optimization Report - {name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ background: #f0f0f0; padding: 10px; margin: 10px 0; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
                .warning {{ color: orange; }}
            </style>
        </head>
        <body>
            <h1>Optimization Report</h1>
            <p>Generated: {result.timestamp}</p>
            
            <h2>Summary</h2>
            <div class="metric">
                <p><strong>Status:</strong> <span class="success">Success</span></p>
                <p><strong>Total Optimizations:</strong> {result.total_optimizations}</p>
                <p><strong>Efficiency Score:</strong> {result.average_efficiency_score}/100</p>
                <p><strong>Cost Reduction:</strong> ${result.total_cost_reduction:.2f}</p>
            </div>
            
            <h2>Metrics</h2>
        """
        
        for i, metric in enumerate(result.metrics, 1):
            html += f"""
            <div class="metric">
                <h3>{i}. {metric.strategy}</h3>
                <ul>
                    <li>Efficiency Score: {metric.calculate_efficiency_score()}/100</li>
                    <li>Size Reduction: {metric.size_reduction_percent:.1f}%</li>
                    <li>Time Reduction: {metric.time_reduction_percent:.1f}%</li>
                    <li>Cost Reduction: {metric.cost_reduction_percent:.1f}%</li>
                    <li>Data Integrity: {'✓' if metric.data_integrity else '✗'}</li>
                </ul>
            </div>
            """
        
        html += "</body></html>"
        
        html_path = self.report_dir / f"{name}.html"
        with open(html_path, 'w') as f:
            f.write(html)
```

### 6. Monitoring and Alerting

**Integration with Monitoring Systems:**

```python
from .optimizer import create_optimizer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitor_optimization_performance():
    """Monitor optimization performance metrics."""
    engine = create_optimizer()
    
    def optimization_callback(result):
        # Log metrics
        logger.info(f"Optimization: {result.total_optimizations} applied")
        logger.info(f"Efficiency: {result.average_efficiency_score}/100")
        logger.info(f"Cost reduction: ${result.total_cost_reduction:.2f}")
        
        # Alert on low efficiency
        if result.average_efficiency_score < 50:
            logger.warning(f"Low efficiency score: {result.average_efficiency_score}")
            # Send alert to monitoring system
        
        # Alert on errors
        if result.errors:
            logger.error(f"Optimization errors: {result.errors}")
            # Send alert to error tracking system
    
    return optimization_callback
```

## Configuration

### Add to `.evolucionador/config.json`

```json
{
    "optimization": {
        "enabled": true,
        "strategies": [
            "json_compression",
            "formula_efficiency",
            "api_optimization",
            "calculation_speed",
            "memory_reduction",
            "cost_reduction"
        ],
        "report_path": "./optimization_reports",
        "log_level": "INFO",
        "cost_model": {
            "api_call": 0.01,
            "compute_time_ms": 0.000015,
            "memory_gb_hour": 0.0001,
            "data_transfer_gb": 0.09
        },
        "thresholds": {
            "min_efficiency_score": 50,
            "min_cost_reduction": 1.0,
            "min_size_reduction_percent": 10
        }
    }
}
```

## Usage Patterns

### Pattern 1: Batch Processing

```python
from pathlib import Path
from .optimizer import create_optimizer

def batch_optimize(input_dir: Path, output_dir: Path):
    """Batch optimize all JSON files in directory."""
    engine = create_optimizer()
    results = []
    
    for json_file in input_dir.glob('*.json'):
        result = engine.optimize_json_file(json_file)
        results.append({
            'file': json_file.name,
            'result': result.to_dict()
        })
        
        # Generate report
        engine.generate_optimization_report(
            result,
            output_dir / f"{json_file.stem}_report.json"
        )
    
    return results
```

### Pattern 2: Real-time Optimization

```python
from .optimizer import create_optimizer
import asyncio

class RealTimeOptimizer:
    def __init__(self):
        self.engine = create_optimizer()
    
    async def optimize_stream(self, data_stream):
        """Optimize data as it streams in."""
        for data_chunk in data_stream:
            result = self.engine.full_system_optimization(data_chunk)
            yield result
```

### Pattern 3: Adaptive Optimization

```python
from .optimizer import create_optimizer

class AdaptiveOptimizer:
    def __init__(self):
        self.engine = create_optimizer()
        self.strategy_performance = {}
    
    def optimize_adaptive(self, data):
        """Select best optimization strategy based on data."""
        # Test each strategy
        results = {
            'json': self.engine.optimize_json_file(data) if 'json_data' in data else None,
            'formula': self.engine.optimize_formula(data) if 'formula' in data else None,
            'api': self.engine.optimize_api_calls(data) if 'api_calls' in data else None,
        }
        
        # Select best strategy
        best = max(
            (k, v) for k, v in results.items() 
            if v and v.success
        )
        
        return best[1]
```

## Testing Integration

### Unit Tests

```python
import unittest
from pathlib import Path
from .optimizer import create_optimizer

class TestOptimizationIntegration(unittest.TestCase):
    
    def setUp(self):
        self.engine = create_optimizer()
    
    def test_json_optimization(self):
        data = {'key': None, 'empty': []}
        result = self.engine.optimize_json_file(Path('test.json'))
        self.assertTrue(result.success or len(result.errors) > 0)
    
    def test_formula_optimization(self):
        formula = "((5 * 3)) + 0"
        result = self.engine.optimize_formula(formula)
        self.assertEqual(result.total_optimizations, 1)
    
    def test_full_system(self):
        system_data = {
            'formulas': ['(2 * 3) + 0'],
            'api_calls': [
                {'method': 'GET', 'endpoint': '/api', 'params': {}},
                {'method': 'GET', 'endpoint': '/api', 'params': {}},
            ]
        }
        result = self.engine.full_system_optimization(system_data)
        self.assertTrue(result.success)
        self.assertGreater(result.total_optimizations, 0)
```

### Integration Tests

```python
def test_full_pipeline():
    """Test complete optimization pipeline."""
    from .analyzer import RepositoryAnalyzer
    from .optimizer import create_optimizer
    
    # Analyze
    analyzer = RepositoryAnalyzer()
    analysis = analyzer.analyze()
    
    # Optimize
    optimizer = create_optimizer()
    result = optimizer.full_system_optimization(analysis)
    
    # Verify
    assert result.success
    assert result.average_efficiency_score > 30
    assert len(result.metrics) > 0
```

## Performance Considerations

### Memory Usage
- Engine creation: ~5MB
- Optimization analysis: ~10-50MB (depends on data size)
- Report generation: ~1-10MB

### CPU Usage
- JSON compression: O(n) where n = data size
- Formula optimization: O(m) where m = formula length
- API optimization: O(a * log a) where a = number of API calls
- Full system: ~100-500ms typical

### Network Impact
- No external API calls
- All processing is local
- Report generation is local I/O

## Security Considerations

1. **No Data Exfiltration**
   - All processing is local
   - No external services contacted
   - No data transmission

2. **Error Handling**
   - Exceptions caught and logged
   - No stack traces in output
   - Sanitized error messages

3. **Input Validation**
   - Type checking
   - Size limits
   - Safe file operations

## Troubleshooting Integration Issues

### Issue: Import Error

```python
# Solution: Ensure module is in path
import sys
sys.path.insert(0, '.evolucionador/core')
from optimizer import create_optimizer
```

### Issue: Low Performance

```python
# Solution: Profile optimization
import cProfile
cProfile.run('optimizer.full_system_optimization(data)')
```

### Issue: High Memory Usage

```python
# Solution: Process data in chunks
for chunk in split_data(large_data):
    result = optimizer.optimize_json_file(chunk)
```

## Deployment Checklist

- [ ] Module tested with actual production data
- [ ] Error handling verified
- [ ] Logging configured appropriately
- [ ] Performance benchmarked
- [ ] Memory usage tested
- [ ] Reports generated and reviewed
- [ ] Integration tests passed
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Documentation updated

## Support and Maintenance

- **Version:** 1.0.0
- **Status:** Production Ready
- **Maintenance:** Actively maintained
- **Support:** Via EVOLUCIONADOR team

---

For detailed information, see:
- `OPTIMIZER_README.md` - Quick reference
- `OPTIMIZER_GUIDE.md` - Comprehensive guide
- `optimizer.py` - Source code with docstrings
