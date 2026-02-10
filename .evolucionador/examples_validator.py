"""
EVOLUCIONADOR Validator - Practical Examples
============================================
Real-world usage examples for all validator components.
"""

import sys
from pathlib import Path

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent / 'core'))

from validator import (
    ComprehensiveValidator, JSONSchemaValidator, FormulaValidator,
    PricingValidator, LoadBearingValidator, APIValidator,
    DocumentationValidator, CrossReferenceValidator,
    SeverityLevel
)


def example_1_validate_json_kb_files():
    """
    Example 1: Validate Knowledge Base JSON files.
    
    Use case: Ensure all KB files are valid JSON and contain expected data.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Validate Knowledge Base JSON Files")
    print("="*80)
    
    validator = JSONSchemaValidator()
    repo_root = Path('/home/runner/work/GPT-PANELIN-V3.2/GPT-PANELIN-V3.2')
    
    kb_files = [
        'BMC_Base_Conocimiento_GPT-2.json',
        'bromyros_pricing_gpt_optimized.json',
        'accessories_catalog.json',
    ]
    
    for kb_file in kb_files:
        file_path = repo_root / kb_file
        
        if not file_path.exists():
            print(f"⚠ Skipping {kb_file} (not found)")
            continue
        
        result = validator.validate_kb_file(file_path)
        
        status = "✓" if result.is_valid else "✗"
        print(f"{status} {kb_file}: {result.get_summary()}")
        
        if result.metadata:
            print(f"  - Entries: {result.metadata.get('entries_count', 'N/A')}")
        
        if result.errors:
            for error in result.errors[:2]:  # Show first 2 errors
                print(f"  ✗ {error.severity.value}: {error.message}")


def example_2_validate_quotation_formulas():
    """
    Example 2: Validate quotation calculation formulas.
    
    Use case: Ensure pricing formulas are correct before use in production.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Validate Quotation Calculation Formulas")
    print("="*80)
    
    validator = FormulaValidator()
    
    test_formulas = [
        {
            'name': 'Basic markup',
            'formula': 'price * 1.15',
            'base_price': 100,
            'expected_range': (114, 116)
        },
        {
            'name': 'With tax and labor',
            'formula': '(base_cost + labor) * (1 + tax_rate)',
            'base_price': 100,
            'expected_range': (110, 150)
        },
        {
            'name': 'Complex calculation',
            'formula': 'material_cost * quantity + fixed_labor + overhead',
            'base_price': 1000,
            'expected_range': (900, 2000)
        },
        {
            'name': 'Invalid formula',
            'formula': '(price * 1.15',  # Missing closing paren
            'is_invalid': True
        }
    ]
    
    for test in test_formulas:
        formula = test['formula']
        
        if test.get('is_invalid'):
            result = validator.validate_quotation_formula(formula)
            status = "✗" if result.is_valid else "✓"
            print(f"{status} {test['name']}: {result.get_summary()}")
        else:
            result = validator.validate_pricing_formula(
                formula,
                test.get('base_price', 100),
                test.get('expected_range', (0, 10000))
            )
            status = "✓" if result.is_valid else "✗"
            print(f"{status} {test['name']}: {result.get_summary()}")
            
            if 'test_result' in result.metadata:
                print(f"  - Result: {result.metadata['test_result']:.2f}")
            
            if result.errors:
                for error in result.errors:
                    print(f"  ✗ {error.message}")


def example_3_validate_pricing_data():
    """
    Example 3: Validate pricing consistency.
    
    Use case: Ensure pricing data is consistent and contains no negative values.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Validate Pricing Data Consistency")
    print("="*80)
    
    validator = PricingValidator()
    
    # Test case 1: Valid pricing
    print("\nTest 1: Valid pricing data")
    valid_pricing = {
        'item_basic': 100.00,
        'item_premium': 250.00,
        'item_deluxe': 500.00,
        'service_installation': 150.00,
        'service_training': 200.00,
    }
    
    result = validator.validate_pricing_consistency(valid_pricing)
    print(f"Status: {result.get_summary()}")
    
    if 'price_stats' in result.metadata:
        stats = result.metadata['price_stats']
        print(f"Statistics:")
        print(f"  - Min: ${stats['min']:.2f}")
        print(f"  - Max: ${stats['max']:.2f}")
        print(f"  - Mean: ${stats['mean']:.2f}")
        print(f"  - Count: {stats['count']}")
    
    # Test case 2: Invalid pricing (negative values)
    print("\nTest 2: Invalid pricing (with negative values)")
    invalid_pricing = {
        'item1': 100.00,
        'item2': -50.00,  # Negative!
        'item3': 200.00,
    }
    
    result = validator.validate_pricing_consistency(invalid_pricing)
    print(f"Status: {result.get_summary()}")
    
    if result.errors:
        for error in result.errors:
            print(f"✗ {error.message}")
    
    # Test case 3: Zero prices
    print("\nTest 3: Zero prices (warnings)")
    zero_pricing = {
        'free_item': 0.00,
        'standard_item': 100.00,
    }
    
    result = validator.validate_pricing_consistency(zero_pricing)
    print(f"Status: {result.get_summary()}")
    
    if result.warnings:
        for warning in result.warnings:
            print(f"⚠ {warning.message}")


def example_4_validate_cross_file_pricing():
    """
    Example 4: Validate pricing consistency across multiple files.
    
    Use case: Detect pricing inconsistencies between different sources/versions.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Cross-File Pricing Validation")
    print("="*80)
    
    validator = PricingValidator()
    
    files_data = {
        'pricing_v1.json': {
            'item_A001': 100.00,
            'item_A002': 250.00,
            'item_A003': 175.00,
        },
        'pricing_v2.json': {
            'item_A001': 100.00,  # ✓ Same
            'item_A002': 275.00,  # ✗ Different!
            'item_A003': 175.00,  # ✓ Same
        },
        'backup_pricing.json': {
            'item_A001': 100.00,
            'item_A002': 250.00,
            'item_A003': 175.00,
        }
    }
    
    result = validator.validate_cross_file_pricing(files_data)
    
    print(f"Consistency Check: {result.get_summary()}")
    print(f"Files checked: {result.metadata['files_checked']}")
    
    if result.errors:
        print("\nInconsistencies found:")
        for error in result.errors:
            print(f"✗ {error.message}")
            if error.details:
                print(f"  Details: {error.details}")


def example_5_validate_load_bearing_tables():
    """
    Example 5: Validate load-bearing capacity tables.
    
    Use case: Verify shelf and structure specifications meet capacity requirements.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Load-Bearing Table Validation")
    print("="*80)
    
    validator = LoadBearingValidator()
    
    # Test case 1: Valid shelving unit
    print("\nTest 1: Valid shelving unit")
    valid_table = {
        'shelf_level_1': {
            'width': 1200,
            'height': 400,
            'depth': 500,
            'capacity': 500,
            'unit': 'kg'
        },
        'shelf_level_2': {
            'width': 1200,
            'height': 400,
            'depth': 500,
            'capacity': 500,
            'unit': 'kg'
        },
        'shelf_level_3': {
            'width': 1200,
            'height': 400,
            'depth': 500,
            'capacity': 400,
            'unit': 'kg'
        }
    }
    
    result = validator.validate_load_table(valid_table)
    print(f"Status: {result.get_summary()}")
    
    # Test case 2: Invalid capacity
    print("\nTest 2: Invalid capacity (negative)")
    invalid_table = {
        'shelf': {
            'width': 1200,
            'height': 400,
            'depth': 500,
            'capacity': -500,  # Invalid!
            'unit': 'kg'
        }
    }
    
    result = validator.validate_load_table(invalid_table)
    print(f"Status: {result.get_summary()}")
    
    if result.errors:
        for error in result.errors:
            print(f"✗ {error.message}")


def example_6_validate_api_endpoints():
    """
    Example 6: Validate API endpoints and specifications.
    
    Use case: Ensure API endpoints follow conventions and are properly formatted.
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: API Endpoint Validation")
    print("="*80)
    
    validator = APIValidator()
    
    test_endpoints = [
        ('/api/quotation/calculate', True, 'Valid endpoint'),
        ('/api/quotation/list', True, 'Valid endpoint'),
        ('api/quotation/calculate', False, 'Missing leading slash'),
        ('/api/quotation/', False, 'Trailing slash'),
        ('/api/quotation//calculate', False, 'Double slash'),
    ]
    
    print("\nEndpoint validation:")
    for endpoint, should_be_valid, description in test_endpoints:
        result = validator.validate_endpoint(endpoint)
        
        if result.is_valid == should_be_valid:
            status = "✓"
        else:
            status = "✗"
        
        print(f"{status} {endpoint}")
        print(f"  Description: {description}")
        print(f"  Status: {result.get_summary()}")
        
        if result.errors:
            for error in result.errors[:1]:
                print(f"  Error: {error.message}")
        
        if result.warnings:
            for warning in result.warnings[:1]:
                print(f"  Warning: {warning.message}")
    
    # Test case 2: Complete API specification
    print("\n\nAPI Specification validation:")
    
    api_spec = {
        'name': 'Quotation System API',
        'version': '2.0.0',
        'base_url': 'https://api.panelin.com',
        'endpoints': [
            {
                'path': '/api/quotation/calculate',
                'method': 'POST',
                'description': 'Calculate quotation'
            },
            {
                'path': '/api/quotation/list',
                'method': 'GET',
                'description': 'List all quotations'
            },
            {
                'path': '/api/quotation/{id}',
                'method': 'GET',
                'description': 'Get quotation by ID'
            }
        ]
    }
    
    result = validator.validate_api_spec(api_spec)
    print(f"API Spec: {result.get_summary()}")
    
    if result.is_valid:
        print(f"✓ API Specification is valid")
        print(f"  Endpoints: {len(api_spec['endpoints'])}")
        print(f"  Version: {api_spec['version']}")


def example_7_validate_documentation():
    """
    Example 7: Validate documentation completeness.
    
    Use case: Ensure all functions have proper documentation.
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Documentation Validation")
    print("="*80)
    
    validator = DocumentationValidator()
    
    # Test case 1: Good docstring
    print("\nTest 1: Complete docstring")
    good_docstring = """
    Calculate the final quotation price.
    
    This function takes the base price and applies all markups,
    discounts, and taxes to produce the final quotation price.
    
    Args:
        base_price: Float - the base product cost
        quantity: Int - number of units
        discount_percent: Float - optional discount (0-100)
        tax_rate: Float - tax rate (0.0-1.0)
    
    Returns:
        float: The final price including all adjustments
    
    Raises:
        ValueError: If prices are negative
        TypeError: If quantity is not an integer
    
    Examples:
        >>> calculate_price(100, 2, discount_percent=10, tax_rate=0.15)
        193.5
    """
    
    result = validator.validate_docstring(good_docstring)
    print(f"Status: {result.get_summary()}")
    print(f"Documented sections: {result.metadata.get('documented_sections', [])}")
    
    # Test case 2: Incomplete docstring
    print("\nTest 2: Incomplete docstring")
    incomplete_docstring = "Calculate something"
    
    result = validator.validate_docstring(incomplete_docstring)
    print(f"Status: {result.get_summary()}")
    
    if result.warnings:
        for warning in result.warnings:
            print(f"⚠ {warning.message}")
    
    # Test case 3: Missing docstring
    print("\nTest 3: Missing docstring")
    result = validator.validate_docstring("")
    print(f"Status: {result.get_summary()}")
    
    if result.errors:
        for error in result.errors:
            print(f"✗ {error.message}")


def example_8_comprehensive_validation():
    """
    Example 8: Run complete validation suite.
    
    Use case: Perform all validations at once for system health check.
    """
    print("\n" + "="*80)
    print("EXAMPLE 8: Comprehensive Validation Suite")
    print("="*80)
    
    validator = ComprehensiveValidator()
    
    # Define test data
    repo_root = Path('/home/runner/work/GPT-PANELIN-V3.2/GPT-PANELIN-V3.2')
    
    kb_files = [
        repo_root / 'BMC_Base_Conocimiento_GPT-2.json',
        repo_root / 'bromyros_pricing_gpt_optimized.json',
    ]
    
    api_specs = [{
        'name': 'Main API',
        'version': '2.0.0',
        'endpoints': [
            {'path': '/api/quotation/calculate'},
            {'path': '/api/quotation/list'}
        ]
    }]
    
    pricing_data = {
        'standard': 100.00,
        'premium': 250.00,
        'enterprise': 500.00
    }
    
    # Run suite
    results = validator.run_full_validation_suite(
        kb_files=[f for f in kb_files if f.exists()],
        api_specs=api_specs,
        pricing_data=pricing_data
    )
    
    # Display results
    print(f"\nValidation Suite Results:")
    print(f"Overall Valid: {results['overall_valid']}")
    print(f"\nSummary:")
    print(f"  - Total Checks: {results['summary']['total_checks']}")
    print(f"  - Passed: {results['summary']['passed']}")
    print(f"  - Failed: {results['summary']['failed']}")
    print(f"  - Warnings: {results['summary']['warnings']}")
    
    # Show KB validation results
    if results['kb_validation']:
        print(f"\nKB File Validation:")
        for file, validation in results['kb_validation'].items():
            status = "✓" if validation['is_valid'] else "✗"
            file_name = Path(file).name
            print(f"  {status} {file_name}")
            if validation['error_count'] > 0:
                print(f"    - Errors: {validation['error_count']}")


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("EVOLUCIONADOR VALIDATOR - PRACTICAL EXAMPLES")
    print("="*80)
    
    examples = [
        example_1_validate_json_kb_files,
        example_2_validate_quotation_formulas,
        example_3_validate_pricing_data,
        example_4_validate_cross_file_pricing,
        example_5_validate_load_bearing_tables,
        example_6_validate_api_endpoints,
        example_7_validate_documentation,
        example_8_comprehensive_validation,
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ Error in {example_func.__name__}: {e}")
    
    print("\n" + "="*80)
    print("Examples completed successfully!")
    print("="*80)


if __name__ == '__main__':
    main()
