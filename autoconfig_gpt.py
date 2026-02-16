#!/usr/bin/env python3
"""
GPT Autoconfiguration Tool
Generates complete GPT configuration for deployment to OpenAI GPTs
Includes interactive approval workflow and validation
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib


class GPTAutoConfigurator:
    """
    Generates and validates complete GPT configuration for deployment
    """
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config_file = repo_root / "Panelin_GPT_config.json"
        self.output_dir = repo_root / "GPT_Deploy_Package"
        self.changes_log = []
        
    def load_base_config(self) -> Dict[str, Any]:
        """Load base GPT configuration"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Base config not found: {self.config_file}")
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_required_files(self) -> Dict[str, Any]:
        """Validate all required files exist and are accessible"""
        
        # Define required files by phase
        required_files = {
            "Phase 1 - Master KB": [
                "BMC_Base_Conocimiento_GPT-2.json",
                "bromyros_pricing_master.json",
                "accessories_catalog.json",
                "bom_rules.json",
            ],
            "Phase 2 - Optimized Lookups": [
                "bromyros_pricing_gpt_optimized.json",
                "shopify_catalog_v1.json",
                "shopify_catalog_index_v1.csv",
            ],
            "Phase 3 - Validation": [
                "BMC_Base_Unificada_v4.json",
                "panelin_truth_bmcuruguay_web_only_v2.json",
            ],
            "Phase 4 - Documentation": [
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
            "Phase 5 - Supporting": [
                "Instrucciones GPT.rtf",
                "Panelin_GPT_config.json",
            ],
            "Phase 6 - Assets": [
                "bmc_logo.png",
            ],
        }
        
        validation_results = {
            "all_files_present": True,
            "missing_files": [],
            "file_details": {},
            "total_size_bytes": 0,
        }
        
        for phase, files in required_files.items():
            for filename in files:
                filepath = self.repo_root / filename
                if filepath.exists():
                    size = filepath.stat().st_size
                    validation_results["file_details"][filename] = {
                        "exists": True,
                        "size": size,
                        "phase": phase,
                        "path": str(filepath),
                    }
                    validation_results["total_size_bytes"] += size
                else:
                    validation_results["all_files_present"] = False
                    validation_results["missing_files"].append(filename)
                    validation_results["file_details"][filename] = {
                        "exists": False,
                        "phase": phase,
                    }
        
        return validation_results
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def generate_deployment_config(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete deployment configuration"""
        
        deployment_config = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "gpt_configuration": {
                "name": base_config.get("name", "Panelin - BMC Assistant Pro"),
                "description": base_config.get("description", ""),
                "instructions": base_config.get("instructions", ""),
                "instructions_version": base_config.get("instructions_version", ""),
                "conversation_starters": base_config.get("conversation_starters", []),
                "capabilities": {
                    "web_browsing": base_config.get("capabilities", {}).get("web_browsing", True),
                    "code_interpreter": base_config.get("capabilities", {}).get("code_interpreter", True),
                    "image_generation": base_config.get("capabilities", {}).get("image_generation", True),
                    "canvas": base_config.get("capabilities", {}).get("canvas", True),
                },
                "knowledge_base": base_config.get("knowledge_base", {}),
            },
            "deployment_instructions": {
                "platform": "OpenAI GPT Builder",
                "url": "https://chat.openai.com/gpts/editor",
                "steps": [
                    "1. Go to OpenAI GPT Builder (https://chat.openai.com/gpts/editor)",
                    "2. Click 'Create' to start a new GPT",
                    "3. Configure basic information:",
                    "   - Name: Use the 'name' field from this config",
                    "   - Description: Use the 'description' field from this config",
                    "4. Enable capabilities:",
                    "   - Web Browsing: Enabled",
                    "   - Code Interpreter: Enabled (CRITICAL for PDF generation)",
                    "   - Image Generation: Enabled",
                    "   - Canvas: Enabled",
                    "5. Add instructions:",
                    "   - Copy the 'instructions' field from this config",
                    "   - Paste into the Instructions box in GPT Builder",
                    "6. Add conversation starters:",
                    "   - Copy the 'conversation_starters' from this config",
                    "   - Add them one by one in GPT Builder",
                    "7. Upload knowledge base files:",
                    "   - See 'file_upload_sequence' below for exact order",
                    "   - CRITICAL: Follow phase order and pause times",
                    "8. (Optional) Configure Actions/API integration:",
                    "   - Import OpenAPI schema from 'Esquema json.rtf'",
                    "   - Configure API Key authentication",
                    "9. Test the GPT with verification queries",
                    "10. Publish the GPT (private or public as desired)",
                ],
            },
            "file_upload_sequence": self._generate_upload_sequence(),
            "verification_queries": [
                "¿Cuánto cuesta ISODEC 100mm?",
                "¿Cuánto cuesta un gotero frontal?",
                "Necesito una cotización para Isopanel EPS 50mm de 5x10 metros",
                "Genera un PDF para una cotización",
            ],
        }
        
        return deployment_config
    
    def _generate_upload_sequence(self) -> List[Dict[str, Any]]:
        """Generate file upload sequence with phases and pause times"""
        
        upload_sequence = [
            {
                "phase": 1,
                "name": "Master Knowledge Base",
                "description": "Primary source of truth - UPLOAD FIRST",
                "files": [
                    "BMC_Base_Conocimiento_GPT-2.json",
                    "bromyros_pricing_master.json",
                    "accessories_catalog.json",
                    "bom_rules.json",
                ],
                "pause_after_minutes": "2-3",
                "critical": True,
            },
            {
                "phase": 2,
                "name": "Optimized Lookups",
                "description": "Fast lookup indices and product catalogs",
                "files": [
                    "bromyros_pricing_gpt_optimized.json",
                    "shopify_catalog_v1.json",
                    "shopify_catalog_index_v1.csv",
                ],
                "pause_after_minutes": "2",
                "critical": True,
            },
            {
                "phase": 3,
                "name": "Validation & Dynamic Data",
                "description": "Cross-reference and web pricing snapshots",
                "files": [
                    "BMC_Base_Unificada_v4.json",
                    "panelin_truth_bmcuruguay_web_only_v2.json",
                ],
                "pause_after_minutes": "2",
                "critical": False,
            },
            {
                "phase": 4,
                "name": "Documentation & Guides",
                "description": "Process guides and usage documentation",
                "files": [
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
                "pause_after_minutes": "2",
                "critical": False,
            },
            {
                "phase": 5,
                "name": "Supporting Files",
                "description": "Additional context and reference",
                "files": [
                    "Instrucciones GPT.rtf",
                    "Panelin_GPT_config.json",
                ],
                "pause_after_minutes": "2",
                "critical": False,
            },
            {
                "phase": 6,
                "name": "Assets",
                "description": "Logo and brand assets",
                "files": [
                    "bmc_logo.png",
                ],
                "pause_after_minutes": "Complete",
                "critical": False,
            },
        ]
        
        return upload_sequence
    
    def display_config_summary(self, config: Dict[str, Any]) -> None:
        """Display summary of configuration for approval"""
        
        print("\n" + "=" * 80)
        print("GPT AUTOCONFIGURATION SUMMARY")
        print("=" * 80)
        print()
        print(f"GPT Name: {config['gpt_configuration']['name']}")
        print(f"Version: {config['gpt_configuration']['instructions_version']}")
        print(f"KB Version: {config['gpt_configuration']['knowledge_base'].get('version', 'Unknown')}")
        print(f"Generated: {config['generated_at']}")
        print()
        
        print("CAPABILITIES:")
        for cap, enabled in config['gpt_configuration']['capabilities'].items():
            status = "✅ Enabled" if enabled else "❌ Disabled"
            print(f"  - {cap.replace('_', ' ').title()}: {status}")
        print()
        
        print("CONVERSATION STARTERS:")
        for i, starter in enumerate(config['gpt_configuration']['conversation_starters'], 1):
            print(f"  {i}. {starter}")
        print()
        
        print("FILE UPLOAD SEQUENCE:")
        for phase in config['file_upload_sequence']:
            critical_marker = " [CRITICAL]" if phase['critical'] else ""
            print(f"\n  Phase {phase['phase']}: {phase['name']}{critical_marker}")
            print(f"  {phase['description']}")
            print(f"  Files: {len(phase['files'])}")
            for filename in phase['files']:
                print(f"    - {filename}")
            print(f"  ⏱️  Pause after upload: {phase['pause_after_minutes']} minutes")
        print()
    
    def request_approval(self) -> bool:
        """Request user approval for configuration"""
        
        print("=" * 80)
        print("APPROVAL REQUIRED")
        print("=" * 80)
        print()
        print("Please review the configuration summary above.")
        print("This configuration will be used to deploy a NEW GPT in OpenAI.")
        print()
        
        while True:
            response = input("Do you approve this configuration? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                print("\n✅ Configuration APPROVED")
                return True
            elif response in ['no', 'n']:
                print("\n❌ Configuration REJECTED")
                return False
            else:
                print("Please enter 'yes' or 'no'")
    
    def save_deployment_package(self, config: Dict[str, Any], validation: Dict[str, Any]) -> Path:
        """Save complete deployment package"""
        
        # Create output directory
        if self.output_dir.exists():
            import shutil
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)
        
        # Save main configuration
        config_path = self.output_dir / "gpt_deployment_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Save OpenAI-compatible export (simplified format)
        openai_export = {
            "name": config['gpt_configuration']['name'],
            "description": config['gpt_configuration']['description'],
            "instructions": config['gpt_configuration']['instructions'],
            "conversation_starters": config['gpt_configuration']['conversation_starters'],
            "capabilities": config['gpt_configuration']['capabilities'],
        }
        
        openai_path = self.output_dir / "openai_gpt_config.json"
        with open(openai_path, 'w', encoding='utf-8') as f:
            json.dump(openai_export, f, indent=2, ensure_ascii=False)
        
        # Save validation report
        validation_path = self.output_dir / "validation_report.json"
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation, f, indent=2, ensure_ascii=False)
        
        # Generate deployment guide
        self._generate_deployment_guide(config, validation)
        
        # Generate quick reference
        self._generate_quick_reference(config)
        
        return self.output_dir
    
    def _generate_deployment_guide(self, config: Dict[str, Any], validation: Dict[str, Any]) -> None:
        """Generate comprehensive deployment guide"""
        
        guide_content = [
            "# GPT Deployment Guide - Panelin",
            "",
            f"**Generated:** {config['generated_at']}",
            f"**GPT Name:** {config['gpt_configuration']['name']}",
            f"**Version:** {config['gpt_configuration']['instructions_version']}",
            "",
            "## 📋 Pre-Deployment Checklist",
            "",
            "Before deploying, ensure:",
            "",
        ]
        
        if validation['all_files_present']:
            guide_content.append("✅ All required files are present")
        else:
            guide_content.append(f"❌ Missing {len(validation['missing_files'])} files:")
            for missing_file in validation['missing_files']:
                guide_content.append(f"   - {missing_file}")
        
        guide_content.extend([
            "",
            f"**Total Files:** {len([f for f in validation['file_details'].values() if f.get('exists', False)])}",
            f"**Total Size:** {self.format_size(validation['total_size_bytes'])}",
            "",
            "## 🚀 Deployment Steps",
            "",
        ])
        
        for i, step in enumerate(config['deployment_instructions']['steps'], 1):
            guide_content.append(step)
        
        guide_content.extend([
            "",
            "## 📂 File Upload Sequence",
            "",
            "**CRITICAL:** Upload files in this exact order with pauses between phases.",
            "",
        ])
        
        for phase in config['file_upload_sequence']:
            critical_marker = " **[CRITICAL]**" if phase['critical'] else ""
            guide_content.extend([
                f"### Phase {phase['phase']}: {phase['name']}{critical_marker}",
                "",
                f"**Description:** {phase['description']}",
                "",
                "**Files to upload:**",
                "",
            ])
            
            for filename in phase['files']:
                file_info = validation['file_details'].get(filename, {})
                if file_info.get('exists', False):
                    size = self.format_size(file_info['size'])
                    guide_content.append(f"- ✅ {filename} ({size})")
                else:
                    guide_content.append(f"- ❌ {filename} (MISSING)")
            
            guide_content.extend([
                "",
                f"**⏱️ PAUSE {phase['pause_after_minutes']} minutes after uploading this phase**",
                "",
            ])
        
        guide_content.extend([
            "## ✅ Verification",
            "",
            "After deployment, test the GPT with these queries:",
            "",
        ])
        
        for query in config['verification_queries']:
            guide_content.append(f"- \"{query}\"")
        
        guide_content.extend([
            "",
            "## 📚 Additional Resources",
            "",
            "- `gpt_deployment_config.json` - Complete configuration details",
            "- `openai_gpt_config.json` - OpenAI-compatible format",
            "- `validation_report.json` - File validation results",
            "- `QUICK_REFERENCE.txt` - One-page quick reference",
            "",
            "## 🔧 Troubleshooting",
            "",
            "### Issue: File upload fails",
            "**Solution:** Wait 1-2 minutes and try again. Check file size limits.",
            "",
            "### Issue: GPT gives wrong prices",
            "**Solution:** Verify Phase 1 files were uploaded first in correct order.",
            "",
            "### Issue: PDF generation fails",
            "**Solution:** Verify Code Interpreter is enabled and bmc_logo.png was uploaded.",
            "",
            "### Issue: GPT can't find information",
            "**Solution:** Wait 5 minutes for reindexing, then try again.",
            "",
            "---",
            "",
            "**Ready to deploy!** Follow the steps above to create your new GPT in OpenAI.",
        ])
        
        guide_path = self.output_dir / "DEPLOYMENT_GUIDE.md"
        with open(guide_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(guide_content))
    
    def _generate_quick_reference(self, config: Dict[str, Any]) -> None:
        """Generate one-page quick reference"""
        
        ref_content = [
            "=" * 80,
            "GPT DEPLOYMENT QUICK REFERENCE",
            "=" * 80,
            "",
            f"GPT Name: {config['gpt_configuration']['name']}",
            f"Version: {config['gpt_configuration']['instructions_version']}",
            f"Generated: {config['generated_at']}",
            "",
            "DEPLOYMENT URL:",
            "https://chat.openai.com/gpts/editor",
            "",
            "REQUIRED CAPABILITIES:",
            "✅ Web Browsing",
            "✅ Code Interpreter (CRITICAL)",
            "✅ Image Generation",
            "✅ Canvas",
            "",
            "FILE UPLOAD ORDER (with pauses):",
        ]
        
        for phase in config['file_upload_sequence']:
            ref_content.append(f"\n{phase['phase']}. {phase['name']} ({len(phase['files'])} files)")
            ref_content.append(f"   ⏱️  Pause: {phase['pause_after_minutes']} min")
        
        ref_content.extend([
            "",
            "CONVERSATION STARTERS:",
        ])
        
        for starter in config['gpt_configuration']['conversation_starters']:
            ref_content.append(f"- {starter}")
        
        ref_content.extend([
            "",
            "VERIFICATION QUERIES:",
        ])
        
        for query in config['verification_queries']:
            ref_content.append(f"- \"{query}\"")
        
        ref_content.extend([
            "",
            "FILES INCLUDED:",
            "- gpt_deployment_config.json (complete configuration)",
            "- openai_gpt_config.json (OpenAI-compatible export)",
            "- DEPLOYMENT_GUIDE.md (detailed instructions)",
            "- validation_report.json (file validation)",
            "",
            "=" * 80,
            "Ready to deploy! See DEPLOYMENT_GUIDE.md for detailed steps.",
            "=" * 80,
        ])
        
        ref_path = self.output_dir / "QUICK_REFERENCE.txt"
        with open(ref_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(ref_content))
    
    def run(self) -> int:
        """Run the autoconfiguration process"""
        
        try:
            print("=" * 80)
            print("GPT AUTOCONFIGURATION TOOL")
            print("Panelin - BMC Assistant Pro")
            print("=" * 80)
            print()
            
            # Load base configuration
            print("📄 Loading base configuration...")
            base_config = self.load_base_config()
            print(f"✅ Loaded: {self.config_file.name}")
            print()
            
            # Validate required files
            print("🔍 Validating required files...")
            validation = self.validate_required_files()
            
            if validation['all_files_present']:
                print(f"✅ All {len(validation['file_details'])} required files found")
                print(f"📦 Total size: {self.format_size(validation['total_size_bytes'])}")
            else:
                print(f"⚠️  Missing {len(validation['missing_files'])} files:")
                for missing_file in validation['missing_files']:
                    print(f"   - {missing_file}")
                print()
                print("⚠️  Deployment will proceed but may be incomplete.")
            print()
            
            # Generate deployment configuration
            print("⚙️  Generating deployment configuration...")
            deployment_config = self.generate_deployment_config(base_config)
            print("✅ Configuration generated")
            print()
            
            # Display summary
            self.display_config_summary(deployment_config)
            
            # Request approval
            if not self.request_approval():
                print()
                print("Autoconfiguration cancelled by user.")
                return 1
            
            print()
            
            # Save deployment package
            print("💾 Saving deployment package...")
            output_path = self.save_deployment_package(deployment_config, validation)
            print(f"✅ Package saved to: {output_path}")
            print()
            
            # Display success message
            print("=" * 80)
            print("✅ AUTOCONFIGURATION COMPLETE")
            print("=" * 80)
            print()
            print("Next steps:")
            print(f"1. Navigate to: {output_path}")
            print("2. Read DEPLOYMENT_GUIDE.md for complete instructions")
            print("3. Use openai_gpt_config.json for OpenAI import")
            print("4. Follow file upload sequence in correct order")
            print()
            print("Quick start:")
            print("  See QUICK_REFERENCE.txt for one-page overview")
            print()
            print(f"Deploy at: https://chat.openai.com/gpts/editor")
            print()
            
            return 0
            
        except Exception as e:
            print(f"\n❌ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Main entry point"""
    repo_root = Path(__file__).parent.resolve()
    
    configurator = GPTAutoConfigurator(repo_root)
    return configurator.run()


if __name__ == "__main__":
    sys.exit(main())
