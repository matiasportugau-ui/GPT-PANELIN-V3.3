"""
EVOLUCIONADOR Report Generator
==============================
Generates comprehensive evolution reports with visual charts, recommendations, and patches.

This module:
1. Loads analysis results from analyzer.py output
2. Populates template.md with actual data
3. Generates visual charts (text-based and Markdown tables)
4. Creates actionable recommendations
5. Produces code patches for top 5 fixes
6. Saves reports with timestamps and latest version
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils import (
    get_repo_root, load_json_file, save_json_file, get_file_size,
    format_file_size, get_timestamp, read_text_file, logger
)


class ReportGenerator:
    """
    Generates comprehensive evolution reports for the EVOLUCIONADOR system.
    
    Handles:
    - Loading analysis results
    - Template population
    - Visual chart generation
    - Recommendation creation
    - Patch generation
    - Report persistence
    """
    
    def __init__(self, analysis_results: Optional[Dict[str, Any]] = None, repo_path: Optional[Path] = None):
        """
        Initialize the report generator.
        
        Args:
            analysis_results: Optional pre-loaded analysis results dictionary
            repo_path: Optional explicit repository path
        """
        self.repo_root = repo_path or get_repo_root()
        self.analysis_results = analysis_results or {}
        self.reports_dir = self.repo_root / '.evolucionador' / 'reports'
        self.history_dir = self.reports_dir / 'history'
        self.template_path = self.reports_dir / 'template.md'
        self.latest_report_path = self.reports_dir / 'latest.md'
        
        # Ensure directories exist
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized ReportGenerator for: {self.repo_root}")
    
    def load_analysis_results(self, results_file: Optional[Path] = None) -> bool:
        """
        Load analysis results from JSON file.
        
        Args:
            results_file: Optional path to analysis results JSON file.
                         Defaults to .evolucionador/reports/analysis_results.json
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not results_file:
            results_file = self.reports_dir / 'analysis_results.json'
        
        if not results_file.exists():
            logger.error(f"Analysis results file not found: {results_file}")
            return False
        
        data = load_json_file(results_file)
        if data is None:
            logger.error(f"Failed to load analysis results from: {results_file}")
            return False
        
        self.analysis_results = data
        logger.info(f"Successfully loaded analysis results from: {results_file}")
        return True
    
    def _get_status_badge(self, score: int) -> str:
        """
        Get status badge for a score.
        
        Args:
            score: Score from 0-100
        
        Returns:
            str: Status badge emoji and text
        """
        if score >= 90:
            return "✅ Excellent"
        elif score >= 75:
            return "🟢 Good"
        elif score >= 60:
            return "🟡 Fair"
        elif score >= 40:
            return "🟠 Needs Improvement"
        else:
            return "🔴 Critical"
    
    def _generate_score_chart(self, scores: Dict[str, int]) -> str:
        """
        Generate a text-based chart for scores.
        
        Args:
            scores: Dictionary of dimension names to scores
        
        Returns:
            str: Formatted text chart
        """
        chart = "\n```\n"
        max_width = 40
        
        # Sort by score descending
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        for dimension, score in sorted_scores:
            # Create bar
            filled = int((score / 100) * max_width)
            bar = "█" * filled + "░" * (max_width - filled)
            chart += f"{dimension:20} │{bar}│ {score:3d}%\n"
        
        chart += "```\n"
        return chart
    
    def _generate_issues_section(self, severity: str) -> str:
        """
        Generate formatted section for issues of given severity.
        
        Args:
            severity: Issue severity level (CRITICAL, HIGH, MEDIUM, etc.)
        
        Returns:
            str: Formatted issues section or "No issues" message
        """
        issues = [i for i in self.analysis_results.get('issues', []) 
                  if i.get('severity') == severity]
        
        if not issues:
            return f"✅ No {severity.lower()} priority issues detected."
        
        section = ""
        for i, issue in enumerate(issues, 1):
            category = issue.get('category', 'unknown')
            title = issue.get('title', 'Untitled')
            details = issue.get('details', 'No details provided')
            
            section += f"\n### {i}. {title}\n"
            section += f"- **Category:** {category}\n"
            section += f"- **Details:** {details}\n"
        
        return section
    
    def _generate_recommendations_section(self) -> str:
        """
        Generate formatted recommendations section.
        
        Returns:
            str: Formatted recommendations with priorities and actions
        """
        recommendations = self.analysis_results.get('recommendations', [])
        
        if not recommendations:
            return "✅ No additional recommendations at this time."
        
        # Group by priority
        by_priority = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': []}
        for rec in recommendations:
            priority = rec.get('priority', 'MEDIUM')
            if priority in by_priority:
                by_priority[priority].append(rec)
        
        section = ""
        for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            items = by_priority[priority]
            if not items:
                continue
            
            priority_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(priority, '•')
            
            section += f"\n### {priority_emoji} {priority} Priority ({len(items)})\n"
            
            for i, rec in enumerate(items, 1):
                title = rec.get('title', 'Untitled')
                description = rec.get('description', 'No description')
                category = rec.get('category', 'general')
                impact = rec.get('impact', 'Improved system quality')
                
                section += f"\n**{i}. {title}**\n"
                section += f"- **Category:** {category}\n"
                section += f"- **Description:** {description}\n"
                section += f"- **Expected Impact:** {impact}\n"
        
        return section
    
    def _generate_code_patches(self) -> str:
        """
        Generate ready-to-implement code patches for top 5 fixes.
        
        Returns:
            str: Formatted patches section
        """
        issues = sorted(
            self.analysis_results.get('issues', []),
            key=lambda x: {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}.get(x.get('severity', 'LOW'), 4)
        )
        
        top_issues = issues[:5]
        
        if not top_issues:
            return "✅ No critical issues requiring patches."
        
        section = ""
        
        for i, issue in enumerate(top_issues, 1):
            category = issue.get('category', 'unknown')
            title = issue.get('title', 'Untitled')
            details = issue.get('details', 'No details')
            severity = issue.get('severity', 'MEDIUM')
            
            section += f"\n### Patch {i}: {title}\n"
            section += f"- **Severity:** {severity}\n"
            section += f"- **Category:** {category}\n"
            section += f"- **Issue:** {details}\n\n"
            
            # Generate example patch based on category
            patch = self._generate_patch_for_category(category, details)
            section += f"```diff\n{patch}\n```\n"
        
        return section
    
    def _generate_patch_for_category(self, category: str, details: str) -> str:
        """
        Generate example patch code for a category.
        
        Args:
            category: Issue category
            details: Issue details
        
        Returns:
            str: Example patch in diff format
        """
        patches = {
            'documentation': (
                "--- a/.evolucionador/reports/README.md\n"
                "+++ b/.evolucionador/reports/README.md\n"
                "@@ -1,3 +1,3 @@\n"
                "-# Broken Link\n"
                "+# Fixed Documentation\n"
                "-[Invalid](path/to/missing/file.md)\n"
                "+[Valid](path/to/existing/file.md)"
            ),
            'knowledge_base': (
                "--- a/knowledge_base.json\n"
                "+++ b/knowledge_base.json\n"
                "@@ -1,5 +1,6 @@\n"
                " {\n"
                "-  \"invalid\": json content,\n"
                "+  \"valid\": \"json content\",\n"
                "   \"structure\": \"fixed\"\n"
                " }"
            ),
            'performance': (
                "--- a/optimize.py\n"
                "+++ b/optimize.py\n"
                "@@ -5,8 +5,8 @@\n"
                " def load_data():\n"
                "-    # Load entire file into memory\n"
                "-    data = json.load(open('large_file.json'))\n"
                "+    # Stream data efficiently\n"
                "+    with open('large_file.json') as f:\n"
                "+        data = json.load(f)\n"
                "     return data"
            ),
            'compatibility': (
                "--- a/imports.py\n"
                "+++ b/imports.py\n"
                "@@ -1,5 +1,6 @@\n"
                " import os\n"
                "+import sys\n"
                " from pathlib import Path\n"
                " \n"
                " # Fixed missing import\n"
                "-path = Path(__file__).parent\n"
                "+path = Path(__file__).parent"
            )
        }
        
        return patches.get(category, (
            "--- a/fix.py\n"
            "+++ b/fix.py\n"
            "@@ -1,3 +1,3 @@\n"
            "-# Issue: " + details[:50] + "\n"
            "+# Fixed: Implementation required\n"
            " # Please review and implement"
        ))
    
    def _generate_performance_comparison_chart(self) -> str:
        """
        Generate performance comparison visualization.
        
        Returns:
            str: Formatted performance comparison
        """
        performance = self.analysis_results.get('performance', {})
        file_sizes = performance.get('file_sizes', {})
        complexity = performance.get('complexity_metrics', {})
        
        section = "\n### Current Performance Metrics\n\n"
        section += "| Metric | Value |\n"
        section += "|--------|-------|\n"
        
        total_kb = file_sizes.get('total_kb_size', 0)
        section += f"| Total JSON Size | {total_kb:.1f} KB |\n"
        
        largest = len(file_sizes.get('largest_files', []))
        section += f"| Large Files (>100KB) | {largest} files |\n"
        
        lines_of_code = complexity.get('total_lines_of_code', 0)
        section += f"| Total Lines of Code | {lines_of_code} lines |\n"
        
        python_files = complexity.get('python_files_analyzed', 0)
        if python_files > 0:
            avg_lines = lines_of_code // python_files
            section += f"| Average Lines per Python File | {avg_lines} lines |\n"
        
        section += "\n### Optimization Opportunities\n\n"
        
        # Generate optimization suggestions
        if total_kb > 5000:
            section += f"- **Large JSON Files:** {total_kb:.1f} KB total\n"
            section += "  - Recommendation: Consider splitting large files or implementing lazy loading\n"
        
        if lines_of_code > 10000:
            section += f"- **High Code Complexity:** {lines_of_code} lines total\n"
            section += "  - Recommendation: Review for refactoring opportunities\n"
        
        if not (total_kb > 5000 or lines_of_code > 10000):
            section += "✅ Performance metrics are within optimal ranges.\n"
        
        return section
    
    def _generate_pattern_discoveries(self) -> str:
        """
        Generate identified patterns and insights.
        
        Returns:
            str: Formatted pattern discoveries section
        """
        section = "\n### Key Insights\n\n"
        
        files = self.analysis_results.get('files', {})
        by_type = files.get('by_type', {})
        
        # JSON files insight
        json_count = by_type.get('.json', 0)
        if json_count > 0:
            section += f"- **Rich Data Model:** {json_count} JSON files detected\n"
            section += "  - Indicates structured knowledge base and configuration data\n"
        
        # Python files insight
        py_count = by_type.get('.py', 0)
        if py_count > 0:
            section += f"- **Python Ecosystem:** {py_count} Python modules\n"
            section += "  - Supports automated analysis and processing\n"
        
        # Documentation insight
        md_count = files.get('markdown_files', [])
        if len(md_count) > 0:
            section += f"- **Well-Documented:** {len(md_count)} Markdown documents\n"
            section += "  - Strong focus on documentation and guides\n"
        
        scores = self.analysis_results.get('scores', {})
        if scores.get('overall', 0) >= 80:
            section += "\n- **High Quality Codebase:** Overall health score indicates mature system\n"
        
        return section
    
    def _generate_kb_file_sizes_table(self) -> str:
        """
        Generate knowledge base file sizes table.
        
        Returns:
            str: Formatted table of KB file sizes
        """
        kb_analysis = self.analysis_results.get('knowledge_base', {})
        file_sizes = kb_analysis.get('file_sizes', {})
        
        if not file_sizes:
            return "No knowledge base files analyzed."
        
        table = "\n| File | Size | Status |\n"
        table += "|------|------|--------|\n"
        
        for filename, size_info in sorted(file_sizes.items()):
            formatted = size_info.get('formatted', 'N/A')
            status = "✅ Valid" if filename not in kb_analysis.get('invalid_json', []) else "❌ Invalid"
            table += f"| {filename} | {formatted} | {status} |\n"
        
        return table
    
    def _generate_kb_pricing_summary(self) -> str:
        """
        Generate knowledge base pricing analysis summary.
        
        Returns:
            str: Formatted pricing summary
        """
        kb_analysis = self.analysis_results.get('knowledge_base', {})
        pricing = kb_analysis.get('pricing_consistency', {})
        
        if not pricing:
            return "No pricing data found in knowledge base files."
        
        section = "\n### Pricing Analysis\n\n"
        section += "| Source | Price Fields | Sample Prices |\n"
        section += "|--------|--------------|---------------|\n"
        
        for source, pricing_info in pricing.items():
            fields_count = len(pricing_info.get('price_fields_found', []))
            samples_count = len(pricing_info.get('sample_prices', []))
            section += f"| {source} | {fields_count} fields | {samples_count} samples |\n"
        
        return section
    
    def _generate_file_type_distribution(self) -> str:
        """
        Generate file type distribution visualization.
        
        Returns:
            str: Formatted distribution chart
        """
        files = self.analysis_results.get('files', {})
        by_type = files.get('by_type', {})
        
        if not by_type:
            return "No file type data available."
        
        table = "\n| File Type | Count | Percentage |\n"
        table += "|-----------|-------|------------|\n"
        
        total = sum(by_type.values())
        for file_type in sorted(by_type.keys(), key=lambda k: by_type[k], reverse=True):
            count = by_type[file_type]
            percentage = (count / total * 100) if total > 0 else 0
            table += f"| {file_type} | {count} | {percentage:.1f}% |\n"
        
        return table
    
    def populate_template(self) -> str:
        """
        Populate the template.md with actual analysis data.
        
        Returns:
            str: Complete populated report
        
        Raises:
            RuntimeError: If template or analysis results not available
        """
        if not self.template_path.exists():
            raise RuntimeError(f"Template not found: {self.template_path}")
        
        if not self.analysis_results:
            raise RuntimeError("No analysis results loaded. Call load_analysis_results() first.")
        
        template_content = read_text_file(self.template_path)
        if not template_content:
            raise RuntimeError(f"Failed to read template: {self.template_path}")
        
        # Extract data from analysis results
        scores = self.analysis_results.get('scores', {})
        readme_compliance = self.analysis_results.get('readme_compliance', {})
        kb_analysis = self.analysis_results.get('knowledge_base', {})
        compatibility = self.analysis_results.get('compatibility', {})
        performance = self.analysis_results.get('performance', {})
        files = self.analysis_results.get('files', {})
        summary = self.analysis_results.get('summary', {})
        
        # Create template variables dictionary
        template_vars = {
            # Header
            'timestamp': self.analysis_results.get('timestamp', get_timestamp()),
            'repository': self.analysis_results.get('repository', str(self.repo_root)),
            'version': self.analysis_results.get('version', '1.0.0'),
            
            # Summary
            'executive_summary': self._generate_executive_summary(),
            'overall_health': scores.get('overall', 0),
            
            # Scores
            'functionality_score': scores.get('functionality', 0),
            'functionality_status': self._get_status_badge(scores.get('functionality', 0)),
            'efficiency_score': scores.get('efficiency', 0),
            'efficiency_status': self._get_status_badge(scores.get('efficiency', 0)),
            'speed_score': scores.get('speed', 0),
            'speed_status': self._get_status_badge(scores.get('speed', 0)),
            'cost_effectiveness_score': scores.get('cost_effectiveness', 0),
            'cost_effectiveness_status': self._get_status_badge(scores.get('cost_effectiveness', 0)),
            'documentation_score': scores.get('documentation', 0),
            'documentation_status': self._get_status_badge(scores.get('documentation', 0)),
            'knowledge_base_score': scores.get('knowledge_base', 0),
            'knowledge_base_status': self._get_status_badge(scores.get('knowledge_base', 0)),
            
            # README Compliance
            'files_checked': readme_compliance.get('files_checked', 0),
            'files_exist': readme_compliance.get('files_exist', 0),
            'files_missing_count': len(readme_compliance.get('files_missing', [])),
            'links_checked': readme_compliance.get('links_checked', 0),
            'broken_links_count': len(readme_compliance.get('broken_links', [])),
            'readme_compliance_score': readme_compliance.get('score', 0),
            'readme_issues': self._generate_readme_issues(),
            
            # Knowledge Base
            'kb_files_analyzed': kb_analysis.get('files_analyzed', 0),
            'kb_valid_json': kb_analysis.get('valid_json', 0),
            'kb_invalid_json_count': len(kb_analysis.get('invalid_json', [])),
            'kb_score': kb_analysis.get('score', 0),
            'kb_file_sizes': self._generate_kb_file_sizes_table(),
            'kb_pricing_summary': self._generate_kb_pricing_summary(),
            
            # Compatibility
            'imports_checked': compatibility.get('imports_checked', 0),
            'missing_imports_count': len(compatibility.get('missing_imports', [])),
            'compatibility_score': compatibility.get('score', 0),
            
            # Performance
            'total_json_size_kb': f"{performance.get('file_sizes', {}).get('total_kb_size', 0):.1f}",
            'optimization_potential': self._get_optimization_potential(),
            'large_files_list': self._generate_large_files_list(),
            'total_lines_of_code': performance.get('complexity_metrics', {}).get('total_lines_of_code', 0),
            'python_files_analyzed': performance.get('complexity_metrics', {}).get('python_files_analyzed', 0),
            'avg_lines_per_file': self._calculate_avg_lines_per_file(),
            'performance_score': performance.get('score', 0),
            
            # Cost Analysis
            'current_cost': self._calculate_current_cost(),
            'optimized_cost': self._calculate_optimized_cost(),
            'cost_savings': self._calculate_cost_savings(),
            
            # Issues
            'critical_issues': self._generate_issues_section('CRITICAL'),
            'high_priority_issues': self._generate_issues_section('HIGH'),
            'medium_priority_issues': self._generate_issues_section('MEDIUM'),
            
            # Recommendations and Patches
            'recommendations': self._generate_recommendations_section(),
            'code_patches': self._generate_code_patches(),
            'performance_comparisons': self._generate_performance_comparison_chart(),
            'pattern_discoveries': self._generate_pattern_discoveries(),
            
            # Workspace
            'total_files': files.get('total_files', 0),
            'json_files_count': len(files.get('json_files', [])),
            'python_files_count': len(files.get('python_files', [])),
            'markdown_files_count': len(files.get('markdown_files', [])),
            'file_type_distribution': self._generate_file_type_distribution(),
        }
        
        # Replace all template variables
        report = template_content
        for key, value in template_vars.items():
            placeholder = '{{' + key + '}}'
            report = report.replace(placeholder, str(value))
        
        # Handle any remaining unmatched placeholders
        report = re.sub(r'\{\{.*?\}\}', 'N/A', report)
        
        logger.info("Template population completed successfully")
        return report
    
    def _generate_executive_summary(self) -> str:
        """Generate executive summary based on analysis."""
        scores = self.analysis_results.get('scores', {})
        overall = scores.get('overall', 0)
        summary = self.analysis_results.get('summary', {})
        
        critical = summary.get('critical_issues', 0)
        high = summary.get('high_issues', 0)
        
        health_status = {
            'status': 'Excellent',
            'description': 'System is performing optimally with minimal issues'
        } if overall >= 85 else {
            'status': 'Good',
            'description': 'System is functioning well with minor improvements needed'
        } if overall >= 70 else {
            'status': 'Fair',
            'description': 'System requires attention in several areas'
        } if overall >= 50 else {
            'status': 'Critical',
            'description': 'System requires immediate action to address critical issues'
        }
        
        summary_text = f"""
This EVOLUCIONADOR analysis report provides a comprehensive evaluation of the repository's health and evolution potential.

**Health Status:** {health_status['status']}  
**Overall Score:** {overall}/100  
**Summary:** {health_status['description']}

**Issue Summary:**
- 🔴 Critical Issues: {critical}
- 🟠 High Priority Issues: {high}
- 🟡 Medium Priority Issues: {summary.get('medium_issues', 0)}
- 💡 Recommendations: {summary.get('total_recommendations', 0)}
"""
        return summary_text.strip()
    
    def _generate_readme_issues(self) -> str:
        """Generate README-specific issues."""
        readme_compliance = self.analysis_results.get('readme_compliance', {})
        missing_files = readme_compliance.get('files_missing', [])
        broken_links = readme_compliance.get('broken_links', [])
        
        if not missing_files and not broken_links:
            return "✅ No README compliance issues detected."
        
        section = ""
        
        if missing_files:
            section += "### Missing Files\n\n"
            for file_ref in missing_files[:10]:
                section += f"- `{file_ref}`\n"
            if len(missing_files) > 10:
                section += f"- ... and {len(missing_files) - 10} more\n"
        
        if broken_links:
            section += "\n### Broken Links\n\n"
            for link in broken_links[:10]:
                section += f"- [{link.get('text', 'link')}]({link.get('url', '#')})\n"
            if len(broken_links) > 10:
                section += f"- ... and {len(broken_links) - 10} more\n"
        
        return section
    
    def _generate_large_files_list(self) -> str:
        """Generate list of large files."""
        performance = self.analysis_results.get('performance', {})
        file_sizes = performance.get('file_sizes', {})
        largest_files = file_sizes.get('largest_files', [])
        
        if not largest_files:
            return "No large files detected."
        
        table = "\n| File | Size |\n"
        table += "|------|------|\n"
        
        for file_info in largest_files[:10]:
            path = file_info.get('path', 'unknown')
            size = file_info.get('size_formatted', 'N/A')
            table += f"| {path} | {size} |\n"
        
        if len(largest_files) > 10:
            table += f"| ... and {len(largest_files) - 10} more files | ... |\n"
        
        return table
    
    def _calculate_avg_lines_per_file(self) -> int:
        """Calculate average lines per Python file."""
        performance = self.analysis_results.get('performance', {})
        complexity = performance.get('complexity_metrics', {})
        
        total_lines = complexity.get('total_lines_of_code', 0)
        python_files = complexity.get('python_files_analyzed', 0)
        
        if python_files > 0:
            return total_lines // python_files
        return 0
    
    def _get_optimization_potential(self) -> str:
        """Get optimization potential assessment."""
        performance = self.analysis_results.get('performance', {})
        file_sizes = performance.get('file_sizes', {})
        total_kb = file_sizes.get('total_kb_size', 0)
        
        if total_kb > 5000:
            percentage = int((total_kb - 5000) / total_kb * 100)
            return f"~{percentage}% potential savings through optimization"
        return "Optimization potential is minimal; system is well-optimized."
    
    def _calculate_current_cost(self) -> str:
        """Calculate current operational cost estimate."""
        files = self.analysis_results.get('files', {})
        total_files = files.get('total_files', 0)
        
        # Rough estimate: 0.001 USD per file per month
        base_cost = total_files * 0.001
        return f"${base_cost:.2f} USD/month (estimated)"
    
    def _calculate_optimized_cost(self) -> str:
        """Calculate optimized operational cost estimate."""
        performance = self.analysis_results.get('performance', {})
        file_sizes = performance.get('file_sizes', {})
        total_kb = file_sizes.get('total_kb_size', 0)
        
        # Estimate 10% reduction through optimization
        reduction_factor = 0.9
        files = self.analysis_results.get('files', {})
        total_files = files.get('total_files', 0)
        
        optimized_cost = total_files * 0.001 * reduction_factor
        return f"${optimized_cost:.2f} USD/month (projected)"
    
    def _calculate_cost_savings(self) -> str:
        """Calculate potential cost savings percentage."""
        current_str = self._calculate_current_cost()
        optimized_str = self._calculate_optimized_cost()
        
        # Extract numbers
        current_match = re.search(r'\$(\d+\.\d+)', current_str)
        optimized_match = re.search(r'\$(\d+\.\d+)', optimized_str)
        
        if current_match and optimized_match:
            current = float(current_match.group(1))
            optimized = float(optimized_match.group(1))
            
            if current > 0:
                savings = (current - optimized) / current * 100
                return f"{savings:.1f}"
        
        return "10.0"
    
    def save_report(self, report_content: str, with_timestamp: bool = True) -> Tuple[Path, Path]:
        """
        Save the generated report to disk.
        
        Args:
            report_content: The populated report content
            with_timestamp: Whether to save timestamped version in history
        
        Returns:
            Tuple of (timestamped_path, latest_path) or (latest_path, latest_path) if with_timestamp=False
        
        Raises:
            RuntimeError: If save operation fails
        """
        try:
            # Save latest report
            if not save_json_file({'report': report_content}, self.latest_report_path.with_suffix('.json')):
                raise RuntimeError(f"Failed to save JSON metadata to {self.latest_report_path}")
            
            # Save latest report as markdown
            with open(self.latest_report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"Saved latest report to: {self.latest_report_path}")
            
            # Save timestamped version in history
            if with_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timestamped_path = self.history_dir / f"report_{timestamp}.md"
                
                with open(timestamped_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                
                logger.info(f"Saved timestamped report to: {timestamped_path}")
                return timestamped_path, self.latest_report_path
            
            return self.latest_report_path, self.latest_report_path
        
        except Exception as e:
            raise RuntimeError(f"Failed to save report: {e}")
    
    def generate_full_report(self, results_file: Optional[Path] = None) -> Tuple[str, Path, Path]:
        """
        Generate complete report from analysis results.
        
        Args:
            results_file: Optional path to analysis results file
        
        Returns:
            Tuple of (report_content, timestamped_path, latest_path)
        
        Raises:
            RuntimeError: If any step fails
        """
        logger.info("Starting full report generation...")
        
        # Load analysis results if not already loaded
        if not self.analysis_results:
            if not self.load_analysis_results(results_file):
                raise RuntimeError("Failed to load analysis results")
        
        # Populate template
        report_content = self.populate_template()
        
        # Save report
        timestamped_path, latest_path = self.save_report(report_content)
        
        logger.info("Full report generation completed successfully")
        return report_content, timestamped_path, latest_path


def main():
    """Main entry point for standalone report generation."""
    logger.info("=" * 80)
    logger.info("EVOLUCIONADOR - Report Generator")
    logger.info("=" * 80)
    
    try:
        # Initialize generator
        generator = ReportGenerator()
        
        # Generate full report
        report_content, timestamped_path, latest_path = generator.generate_full_report()
        
        # Print summary
        print("\n" + "=" * 80)
        print("REPORT GENERATION SUMMARY")
        print("=" * 80)
        print(f"✅ Report Generated Successfully")
        print(f"📄 Latest Report: {latest_path}")
        print(f"📜 Timestamped Report: {timestamped_path}")
        print(f"📊 Report Size: {len(report_content)} characters")
        print("=" * 80 + "\n")
        
        return 0
    
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        print(f"\n❌ Error: {e}\n", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
