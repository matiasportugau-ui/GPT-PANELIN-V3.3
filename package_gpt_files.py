#!/usr/bin/env python3
"""
GPT Files Packaging Script
Creates organized directories for each upload phase to make the upload process easier.
"""

import json
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Define files by upload phase
UPLOAD_PHASES = {
    "Phase_1_Master_KB": {
        "description": "Master Knowledge Base (Level 1) - UPLOAD FIRST",
        "files": [
            "BMC_Base_Conocimiento_GPT-2.json",
            "accessories_catalog.json",
            "bom_rules.json",
        ],
        "pause_after": "2-3 minutes",
    },
    "Phase_2_Optimized_Lookups": {
        "description": "Optimized Lookups (Level 1.5-1.6)",
        "files": [
            "bromyros_pricing_gpt_optimized.json",
            "shopify_catalog_v1.json",
        ],
        "pause_after": "2 minutes",
    },
    "Phase_3_Validation": {
        "description": "Validation & Dynamic Data (Level 2-3)",
        "files": [
            "BMC_Base_Unificada_v4.json",
            "panelin_truth_bmcuruguay_web_only_v2.json",
        ],
        "pause_after": "2 minutes",
    },
    "Phase_4_Documentation": {
        "description": "Documentation & Guides (Level 4)",
        "files": [
            "PANELIN_KNOWLEDGE_BASE_GUIDE.md",
            "PANELIN_QUOTATION_PROCESS.md",
            "PANELIN_TRAINING_GUIDE.md",
            "GPT_INSTRUCTIONS_PRICING.md",
            "GPT_PDF_INSTRUCTIONS.md",
            "GPT_OPTIMIZATION_ANALYSIS.md",
            "README.md",
        ],
        "pause_after": "2 minutes",
    },
    "Phase_5_Supporting": {
        "description": "Supporting Files",
        "files": [
            "Instrucciones GPT.rtf",
            "Panelin_GPT_config.json",
        ],
        "pause_after": "2 minutes",
    },
    "Phase_6_Assets": {
        "description": "Assets",
        "files": [
            "bmc_logo.png",
        ],
        "pause_after": "Complete!",
    },
}


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def create_upload_package(output_dir: str = "GPT_Upload_Package"):
    """Create organized package of files for GPT upload."""
    repo_root = Path(__file__).parent
    os.chdir(repo_root)

    output_path = repo_root / output_dir
    
    # Clean and create output directory
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir()

    print("=" * 80)
    print("GPT FILES PACKAGING - Panelin 3.3")
    print("=" * 80)
    print(f"\nCreating upload package in: {output_path}")
    print()

    total_files = 0
    total_size = 0
    missing_files = []

    # Create README for the package
    readme_content = [
        "# GPT Upload Package - Panelin 3.3",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n## Upload Instructions\n",
        "Upload files to OpenAI GPT Builder in this order:\n",
    ]

    # Process each phase
    for phase_dir, phase_info in UPLOAD_PHASES.items():
        phase_path = output_path / phase_dir
        phase_path.mkdir()

        print(f"Creating {phase_dir}/")
        print(f"  Description: {phase_info['description']}")
        print(f"  Files:")

        # Add phase to README
        readme_content.append(f"\n### {phase_dir}")
        readme_content.append(f"{phase_info['description']}\n")
        
        phase_size = 0
        phase_file_count = 0

        # Copy files for this phase
        for filename in phase_info['files']:
            source = repo_root / filename
            dest = phase_path / filename

            if not source.exists():
                print(f"    ❌ {filename} - NOT FOUND")
                missing_files.append(filename)
                readme_content.append(f"- ❌ {filename} - MISSING")
                continue

            # Copy file
            shutil.copy2(source, dest)
            file_size = source.stat().st_size
            phase_size += file_size
            total_size += file_size
            phase_file_count += 1
            total_files += 1

            print(f"    ✅ {filename} ({format_size(file_size)})")
            readme_content.append(f"- {filename} ({format_size(file_size)})")

        readme_content.append(f"\n**Pause after uploading: {phase_info['pause_after']}**\n")
        print(f"  Phase Total: {phase_file_count} files, {format_size(phase_size)}")
        print(f"  ⏱️  PAUSE {phase_info['pause_after']} after uploading this phase")
        print()

        # Create phase-specific instructions
        phase_instructions = [
            f"# {phase_dir}",
            f"\n{phase_info['description']}\n",
            "## Files in this phase:\n",
        ]
        for i, filename in enumerate(phase_info['files'], 1):
            phase_instructions.append(f"{i}. {filename}")
        
        phase_instructions.append(f"\n## Upload Instructions:\n")
        phase_instructions.append("1. Go to OpenAI GPT Builder: https://chat.openai.com/gpts/editor")
        phase_instructions.append("2. Upload each file one at a time (don't batch upload)")
        phase_instructions.append("3. Wait for each file to finish uploading before starting the next")
        phase_instructions.append(f"4. After uploading ALL files in this phase, PAUSE for {phase_info['pause_after']}")
        phase_instructions.append("5. Then proceed to the next phase")
        
        with open(phase_path / "INSTRUCTIONS.txt", 'w') as f:
            f.write('\n'.join(phase_instructions))

    # Write main README
    readme_content.extend([
        f"\n## Summary\n",
        f"- Total files: {total_files}",
        f"- Total size: {format_size(total_size)}",
        f"- Estimated upload time: 10-15 minutes (with pauses)",
    ])

    if missing_files:
        readme_content.append(f"\n⚠️  **Missing files ({len(missing_files)}):**")
        for f in missing_files:
            readme_content.append(f"- {f}")
        readme_content.append("\nPlease locate these files before uploading.")

    readme_content.extend([
        "\n## Important Notes\n",
        "- Upload phases in order (Phase_1 first, Phase_6 last)",
        "- Upload one file at a time within each phase",
        "- Pause between phases as indicated for GPT to reindex",
        "- Refer to GPT_UPLOAD_CHECKLIST.md for detailed instructions",
        "\n## Verification\n",
        "After uploading all files, test the GPT:",
        '- Ask: "¿Cuánto cuesta ISODEC 100mm?" (should return Level 1 price)',
        '- Ask: "¿Cuánto cuesta un gotero frontal?" (should return accessories price)',
        "- Request a complete quotation with BOM",
        "- Request PDF generation",
    ])

    with open(output_path / "README.txt", 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(readme_content))

    # Copy the main checklist
    checklist_source = repo_root / "GPT_UPLOAD_CHECKLIST.md"
    if checklist_source.exists():
        shutil.copy2(checklist_source, output_path / "GPT_UPLOAD_CHECKLIST.md")
        print("✅ Copied GPT_UPLOAD_CHECKLIST.md to package")
        print()

    # Print summary
    print("=" * 80)
    print("PACKAGING COMPLETE")
    print("=" * 80)
    print(f"Total files packaged: {total_files}")
    print(f"Total size: {format_size(total_size)}")
    print(f"Output directory: {output_path}")
    print()

    if missing_files:
        print(f"⚠️  Missing files: {len(missing_files)}")
        print("Some files could not be found. Please locate them before uploading.")
        print()
        return 1
    else:
        print("✅ All files packaged successfully!")
        print()
        print("Next steps:")
        print(f"1. Navigate to: {output_path}")
        print("2. Read README.txt for upload instructions")
        print("3. Upload phases in order, starting with Phase_1_Master_KB")
        print("4. Follow pause instructions between phases")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(create_upload_package())
