#!/usr/bin/env python3
"""
GPT Files Validation Script
Validates that all required files for GPT upload exist and are properly formatted.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

# Define required files by category
REQUIRED_FILES = {
    "Phase 1: Master Knowledge Base (Level 1)": [
        "BMC_Base_Conocimiento_GPT-2.json",
        "bromyros_pricing_master.json",
        "accessories_catalog.json",
        "bom_rules.json",
    ],
    "Phase 2: Optimized Lookups (Level 1.5-1.6)": [
        "bromyros_pricing_gpt_optimized.json",
        "shopify_catalog_v1.json",
        "shopify_catalog_index_v1.csv",
    ],
    "Phase 3: Validation & Dynamic Data (Level 2-3)": [
        "BMC_Base_Unificada_v4.json",
        "panelin_truth_bmcuruguay_web_only_v2.json",
    ],
    "Phase 4: Documentation & Guides (Level 4)": [
        "Aleros -2.rtf",
        "panelin_context_consolidacion_sin_backend.md",
        "PANELIN_KNOWLEDGE_BASE_GUIDE.md",
        "PANELIN_QUOTATION_PROCESS.md",
        "PANELIN_TRAINING_GUIDE.md",
        "GPT_INSTRUCTIONS_PRICING.md",
        "GPT_PDF_INSTRUCTIONS.md",
        "GPT_OPTIMIZATION_ANALYSIS.md",
        "README.md",
    ],
    "Phase 5: Supporting Files": [
        "Instrucciones GPT.rtf",
        "Panelin_GPT_config.json",
    ],
    "Phase 6: Assets": [
        "bmc_logo.png",
    ],
}

# File size expectations (min, max) in KB
FILE_SIZE_RANGES = {
    "BMC_Base_Conocimiento_GPT-2.json": (5, 2000),
    "accessories_catalog.json": (10, 500),
    "bom_rules.json": (5, 500),
    "bromyros_pricing_master.json": (50, 5000),
    "bromyros_pricing_gpt_optimized.json": (50, 1000),
    "shopify_catalog_v1.json": (200, 2000),
    "shopify_catalog_index_v1.csv": (10, 1000),
    "BMC_Base_Unificada_v4.json": (5, 1000),
    "panelin_truth_bmcuruguay_web_only_v2.json": (3, 500),
    "bmc_logo.png": (10, 200),
}


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def validate_json_file(filepath: Path) -> Tuple[bool, str]:
    """Validate that a JSON file is properly formatted."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, "Valid JSON"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"


def validate_file(filepath: Path) -> Dict:
    """Validate a single file."""
    result = {
        "exists": False,
        "size": 0,
        "size_formatted": "0 bytes",
        "size_ok": True,
        "valid": True,
        "message": "",
    }

    # Check if file exists
    if not filepath.exists():
        result["message"] = "❌ File not found"
        return result

    result["exists"] = True

    # Get file size
    size = filepath.stat().st_size
    result["size"] = size
    result["size_formatted"] = format_size(size)

    # Check file size if expectations defined
    filename = filepath.name
    if filename in FILE_SIZE_RANGES:
        min_kb, max_kb = FILE_SIZE_RANGES[filename]
        size_kb = size / 1024
        if size_kb < min_kb or size_kb > max_kb:
            result["size_ok"] = False
            result["message"] = f"⚠️  Size {result['size_formatted']} outside expected range ({min_kb}-{max_kb} KB)"

    # Validate JSON files
    if filepath.suffix == '.json':
        valid, msg = validate_json_file(filepath)
        result["valid"] = valid
        if not valid:
            result["message"] = f"❌ {msg}"
        elif result["size_ok"]:
            result["message"] = "✅ Valid"
    elif result["size_ok"]:
        result["message"] = "✅ Exists"

    return result


def main():
    """Main validation function."""
    print("=" * 80)
    print("GPT FILES VALIDATION - Panelin 3.3")
    print("=" * 80)
    print()

    repo_root = Path(__file__).parent
    os.chdir(repo_root)

    all_valid = True
    total_size = 0
    total_files = 0
    missing_files = []
    invalid_files = []

    # Validate each phase
    for phase, files in REQUIRED_FILES.items():
        print(f"\n{phase}")
        print("-" * 80)

        for filename in files:
            total_files += 1
            filepath = repo_root / filename

            result = validate_file(filepath)

            # Print result
            status = result["message"]
            size_info = f"[{result['size_formatted']}]" if result["exists"] else ""
            print(f"  {filename:50s} {status:20s} {size_info}")

            # Track status
            if result["exists"]:
                total_size += result["size"]
            else:
                all_valid = False
                missing_files.append(filename)

            if not result["valid"]:
                all_valid = False
                invalid_files.append(filename)

    # Print summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total files checked: {total_files}")
    print(f"Total size: {format_size(total_size)}")
    print()

    if missing_files:
        print(f"❌ Missing files ({len(missing_files)}):")
        for f in missing_files:
            print(f"   - {f}")
        print()

    if invalid_files:
        print(f"❌ Invalid files ({len(invalid_files)}):")
        for f in invalid_files:
            print(f"   - {f}")
        print()

    if all_valid and not missing_files:
        print("✅ All files are present and valid!")
        print()
        print("You are ready to upload files to the GPT.")
        print("Follow the upload order in GPT_UPLOAD_CHECKLIST.md")
        print()
        return 0
    else:
        print("⚠️  Some files are missing or invalid.")
        print("Please fix the issues above before uploading to GPT.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
