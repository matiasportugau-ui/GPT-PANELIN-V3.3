# EVOLUCIONADOR Report Generator

## Overview

The Report Generator transforms analysis results into comprehensive, beautifully formatted Markdown reports with visual charts, actionable recommendations, and ready-to-implement code patches.

## Quick Start

```bash
# Generate a report
cd /path/to/repository
python .evolucionador/reports/generator.py
```

## Features

### Core Capabilities

- **Analysis Loading**: Loads JSON results from analyzer.py
- **Template Population**: Populates template.md with real data
- **Visual Charts**: Text-based progress bars and Markdown tables
- **Smart Recommendations**: Prioritized suggestions based on analysis
- **Code Patches**: Top 5 ready-to-implement fixes in diff format
- **Report History**: Timestamped versions in reports/history/
- **Latest Tracking**: Current report in reports/latest.md

### Production Quality

- Full type hints and docstrings
- Comprehensive error handling
- Logging support
- UTF-8 file handling
- Standalone execution
- Security checked

## Usage

### Programmatic

```python
from evolucionador.reports.generator import ReportGenerator

# Generate full report
generator = ReportGenerator()
content, timestamped, latest = generator.generate_full_report()

# Or step by step
generator.load_analysis_results()
report = generator.populate_template()
timestamped, latest = generator.save_report(report)
```

### Command Line

```bash
# Default (auto-detects analysis results)
python .evolucionador/reports/generator.py

# With specific analysis file
python -c "
from evolucionador.reports.generator import ReportGenerator
from pathlib import Path
gen = ReportGenerator()
gen.generate_full_report(Path('custom_analysis.json'))
"
```

## Output Files

```
.evolucionador/reports/
├── latest.md                    # Current report (Markdown)
├── latest.json                  # Current report metadata
└── history/
    ├── report_20260210_081941.md
    ├── report_20260210_082052.md
    └── ...                      # Historical reports
```

## Report Sections

Generated reports include:

1. **Executive Summary** - Overall health and status
2. **Dimensional Scores** - 6 key performance dimensions with status badges
3. **README Compliance** - Documentation validation matrix
4. **Knowledge Base Analysis** - JSON consistency and pricing data
5. **File Compatibility** - Import and cross-reference checks
6. **Performance Benchmarks** - File sizes and code complexity metrics
7. **Cost Analysis** - Current and optimized operational costs
8. **Issues** - Categorized by severity (Critical, High, Medium)
9. **Recommendations** - Actionable improvements with impact assessment
10. **Code Patches** - Ready-to-implement fixes in diff format
11. **Performance Comparisons** - Current vs. optimized metrics
12. **Pattern Discoveries** - Key insights and patterns identified
13. **Detailed Metrics** - File inventory and distribution analysis

## API Reference

### ReportGenerator

#### `__init__(analysis_results=None, repo_path=None)`
Initialize the generator.

#### `load_analysis_results(results_file=None) -> bool`
Load analysis results from JSON file.

#### `populate_template() -> str`
Populate template.md with analysis data.

#### `save_report(report_content, with_timestamp=True) -> (Path, Path)`
Save report to disk with optional timestamped version.

#### `generate_full_report(results_file=None) -> (str, Path, Path)`
Complete workflow: load → populate → save.

## Visualizations

### Score Chart
```
functionality     │████████████████████████████████████████│ 95%
speed             │████████████████████████████████████░░░░│ 90%
efficiency        │███████████████████████████████░░░░░░░░░░│ 85%
```

### Status Badges
- ✅ Excellent (90-100)
- 🟢 Good (75-89)
- 🟡 Fair (60-74)
- 🟠 Needs Improvement (40-59)
- 🔴 Critical (<40)

### Issue Priority Icons
- 🔴 Critical
- 🟠 High
- 🟡 Medium
- 🟢 Low

## Template Variables

Supported variables in template.md:

### Header
- `{{timestamp}}` - Generation time
- `{{repository}}` - Repository path
- `{{version}}` - Analysis version

### Scores (all 0-100)
- `{{overall_health}}`
- `{{functionality_score}}`
- `{{efficiency_score}}`
- `{{speed_score}}`
- `{{cost_effectiveness_score}}`
- `{{documentation_score}}`
- `{{knowledge_base_score}}`

### Status Badges
- `{{functionality_status}}`
- `{{efficiency_status}}`
- `{{speed_status}}`
- `{{cost_effectiveness_status}}`
- `{{documentation_status}}`
- `{{knowledge_base_status}}`

### Detailed Metrics
- `{{total_files}}`
- `{{json_files_count}}`
- `{{python_files_count}}`
- `{{markdown_files_count}}`
- `{{total_json_size_kb}}`
- `{{total_lines_of_code}}`
- `{{python_files_analyzed}}`
- `{{avg_lines_per_file}}`

### Issues and Recommendations
- `{{critical_issues}}`
- `{{high_priority_issues}}`
- `{{medium_priority_issues}}`
- `{{recommendations}}`
- `{{code_patches}}`

### Analysis Tables
- `{{readme_issues}}`
- `{{kb_file_sizes}}`
- `{{kb_pricing_summary}}`
- `{{large_files_list}}`
- `{{file_type_distribution}}`

### Cost Analysis
- `{{current_cost}}`
- `{{optimized_cost}}`
- `{{cost_savings}}`

### Summaries
- `{{executive_summary}}`
- `{{performance_comparisons}}`
- `{{pattern_discoveries}}`

## Error Handling

```python
try:
    generator = ReportGenerator()
    content, _, latest = generator.generate_full_report()
except RuntimeError as e:
    print(f"Generation failed: {e}")
```

Errors are logged to the EVOLUCIONADOR logger for debugging.

## Integration

Works seamlessly with the full EVOLUCIONADOR pipeline:

```bash
# Complete workflow
python .evolucionador/core/analyzer.py      # Generate analysis_results.json
python .evolucionador/reports/generator.py   # Generate report from analysis
```

## Performance

- Generation time: < 1 second
- Typical report size: 4-5 KB
- History storage: Minimal (< 1 MB for 100+ reports)

## Security

- ✅ Safe template substitution (no eval)
- ✅ Proper UTF-8 encoding
- ✅ CodeQL security checks passed
- ✅ Only uses Python stdlib
- ✅ Safe path handling

## Troubleshooting

### Analysis results not found
```
Error: Analysis results file not found

Solution: Run analyzer first
$ python .evolucionador/core/analyzer.py
```

### Template not found
```
Error: Template not found

Solution: Ensure .evolucionador/reports/template.md exists
```

### Report contains "N/A"
```
Cause: Template variable not populated

Solution: Check analysis_results.json is valid JSON
```

## Related Files

- `.evolucionador/core/analyzer.py` - Analysis engine
- `.evolucionador/core/utils.py` - Utility functions
- `.evolucionador/reports/template.md` - Report template
- `.evolucionador/reports/analysis_results.json` - Analysis input

## License

Part of the EVOLUCIONADOR system. See LICENSE file.
