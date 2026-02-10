"""
Test PDF Generation for BMC Uruguay Quotations
===============================================

Test script to verify PDF generation functionality with sample data.

Version: 2.0
"""

import os
import sys
from datetime import datetime

# Add parent directory to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from panelin_reports import build_quote_pdf, BMCStyles


def get_sample_quotation_data():
    """Returns sample quotation data for testing"""
    return {
        'client_name': 'Arquitecto Rodríguez',
        'client_address': 'Av. Italia 2525, Montevideo',
        'client_phone': '099 123 456',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'quote_description': 'Isopanel EPS 50mm + Isodec EPS 100mm',
        'autoportancia': '5.5',
        'apoyos': '3 (cada 2.75m)',
        'products': [
            {
                'name': 'Isopanel EPS 50mm (Fachada)',
                'unit_base': 'm²',
                'quantity': 180.0,
                'unit_price_usd': 33.21,
                'total_usd': 5977.80,
                'total_m2': 180.0,
            },
            {
                'name': 'Isodec EPS 100mm (Techo)',
                'unit_base': 'm²',
                'quantity': 120.0,
                'unit_price_usd': 46.07,
                'total_usd': 5528.40,
                'total_m2': 120.0,
            },
        ],
        'accessories': [
            {
                'name': 'Perfil U 50mm',
                'unit_base': 'ml',
                'quantity': 45.0,
                'unit_price_usd': 3.90,
                'total_usd': 175.50,
            },
            {
                'name': 'Gotero Frontal 50mm',
                'unit_base': 'ml',
                'quantity': 12.0,
                'unit_price_usd': 8.20,
                'total_usd': 98.40,
            },
            {
                'name': 'Babeta de Encastre 50mm',
                'unit_base': 'ml',
                'quantity': 10.0,
                'unit_price_usd': 12.50,
                'total_usd': 125.00,
            },
        ],
        'fixings': [
            {
                'name': 'Silicona Selladora',
                'unit_base': 'unidad',
                'quantity': 8,
                'unit_price_usd': 9.78,
                'total_usd': 78.24,
            },
            {
                'name': 'Tornillos Autoperforantes',
                'unit_base': 'unidad',
                'quantity': 200,
                'unit_price_usd': 0.12,
                'total_usd': 24.00,
            },
            {
                'name': 'Arandelas Carrocero',
                'unit_base': 'unidad',
                'quantity': 200,
                'unit_price_usd': 0.08,
                'total_usd': 16.00,
            },
        ],
        'shipping_usd': 280.0,
    }


def test_pdf_generation():
    """Test basic PDF generation with sample data"""
    print("=" * 60)
    print("Testing BMC PDF Generation v2.0")
    print("=" * 60)
    print()
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Get sample data
    data = get_sample_quotation_data()
    
    # Output path
    output_path = os.path.join(output_dir, 'test_quotation.pdf')
    
    print(f"Generating PDF: {output_path}")
    print()
    
    # Generate PDF
    try:
        result_path = build_quote_pdf(
            data=data,
            output_path=output_path,
            logo_path=None  # Auto-detect
        )
        
        print(f"✅ PDF generated successfully!")
        print(f"   Location: {result_path}")
        print(f"   Size: {os.path.getsize(result_path) / 1024:.1f} KB")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_minimal_quotation():
    """Test with minimal required data"""
    print("\nTesting minimal quotation (no accessories/fixings)...")
    
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    data = {
        'client_name': 'Cliente Ejemplo',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'quote_description': 'Panel Simple',
        'products': [
            {
                'name': 'Isopanel EPS 50mm',
                'unit_base': 'm²',
                'quantity': 100.0,
                'unit_price_usd': 33.21,
                'total_usd': 3321.00,
            },
        ],
        'shipping_usd': 280.0,
    }
    
    output_path = os.path.join(output_dir, 'test_minimal.pdf')
    
    try:
        result_path = build_quote_pdf(data, output_path)
        print(f"✅ Minimal PDF generated: {result_path}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_with_formatted_comments():
    """Test with custom formatted comments"""
    print("\nTesting with formatted comments...")
    
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    data = get_sample_quotation_data()
    
    # Add custom comments with different formatting
    data['comments'] = [
        ("Este es un comentario en NEGRITA importante.", "bold"),
        ("Este comentario es en ROJO para llamar la atención.", "red"),
        ("Este comentario es NEGRITA Y ROJO juntos.", "bold_red"),
        ("Este es un comentario normal sin formato especial.", "normal"),
    ]
    
    output_path = os.path.join(output_dir, 'test_formatted_comments.pdf')
    
    try:
        result_path = build_quote_pdf(data, output_path)
        print(f"✅ Formatted comments PDF generated: {result_path}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_default_comments():
    """Test with default BMC comments"""
    print("\nTesting with default BMC comments...")
    
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    data = get_sample_quotation_data()
    # Don't specify comments - should use defaults from BMCStyles
    
    output_path = os.path.join(output_dir, 'test_default_comments.pdf')
    
    try:
        result_path = build_quote_pdf(data, output_path)
        print(f"✅ Default comments PDF generated: {result_path}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_no_logo():
    """Test PDF generation when logo is not found"""
    print("\nTesting without logo...")
    
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    data = get_sample_quotation_data()
    output_path = os.path.join(output_dir, 'test_no_logo.pdf')
    
    try:
        result_path = build_quote_pdf(
            data,
            output_path,
            logo_path="/nonexistent/logo.png"  # Force no logo
        )
        print(f"✅ No-logo PDF generated: {result_path}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print()
    print("BMC Uruguay PDF Generation Test Suite")
    print("=" * 60)
    print()
    
    # Run tests
    results = []
    
    # Main test
    results.append(("Main template test", test_pdf_generation()))
    
    # Additional scenarios
    results.append(("Minimal quotation", test_minimal_quotation()))
    results.append(("Formatted comments", test_with_formatted_comments()))
    results.append(("Default comments", test_default_comments()))
    results.append(("No logo fallback", test_no_logo()))
    
    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("🎉 All tests passed!")
        print()
        print("Next steps:")
        print("  1. Review generated PDFs in panelin_reports/output/")
        print("  2. Add BMC Uruguay logo to panelin_reports/assets/bmc_logo.png")
        print("  3. Integrate with GPT Code Interpreter")
    else:
        print("⚠️  Some tests failed. Review errors above.")
    
    print()
