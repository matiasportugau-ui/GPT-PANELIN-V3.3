#!/usr/bin/env python3
"""
GPT Configuration ZIP Package Generator
Creates a comprehensive downloadable ZIP file with all GPT configuration files,
knowledge bases, schemas, instructions, and documentation.
"""

import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib


class GPTZipPackager:
    """
    Creates a complete ZIP package for GPT configuration deployment
    """
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.output_dir = repo_root / "GPT_Complete_Package"
        self.zip_filename = f"Panelin_GPT_Config_Package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
    def get_all_required_files(self) -> Dict[str, List[str]]:
        """
        Define all files that should be included in the ZIP package
        Organized by category
        """
        
        files_by_category = {
            "Phase_1_Master_KB": [
                "BMC_Base_Conocimiento_GPT-2.json",
                "bromyros_pricing_master.json",
                "accessories_catalog.json",
                "bom_rules.json",
            ],
            "Phase_2_Optimized_Lookups": [
                "bromyros_pricing_gpt_optimized.json",
                "shopify_catalog_v1.json",
                "shopify_catalog_index_v1.csv",
            ],
            "Phase_3_Validation": [
                "BMC_Base_Unificada_v4.json",
                "panelin_truth_bmcuruguay_web_only_v2.json",
            ],
            "Phase_4_Documentation": [
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
            "Phase_5_Supporting": [
                "Instrucciones GPT.rtf",
                "Panelin_GPT_config.json",
                "Esquema json.rtf",
            ],
            "Phase_6_Assets": [
                "bmc_logo.png",
            ],
            "Configuration_Files": [
                "GPT_AUTOCONFIG_GUIDE.md",
                "GPT_AUTOCONFIG_FAQ.md",
                "AUTOCONFIG_QUICK_START.md",
                "GPT_UPLOAD_CHECKLIST.md",
                "QUICK_START_GPT_UPLOAD.md",
            ],
            "Deployment_Guides": [
                "DEPLOYMENT_CONFIG.md",
                "DEPLOYMENT_QUICK_REFERENCE.md",
                "DEPLOYMENT_CHECKLIST.md",
                "DEPLOYMENT_DOCS_INDEX.md",
            ],
        }
        
        return files_by_category
    
    def validate_files(self, files_by_category: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate that all required files exist
        """
        
        validation = {
            "all_present": True,
            "missing_files": [],
            "present_files": [],
            "total_size": 0,
            "file_details": {},
        }
        
        for category, files in files_by_category.items():
            for filename in files:
                filepath = self.repo_root / filename
                
                if filepath.exists():
                    size = filepath.stat().st_size
                    validation["present_files"].append({
                        "name": filename,
                        "category": category,
                        "size": size,
                        "path": str(filepath)
                    })
                    validation["total_size"] += size
                    validation["file_details"][filename] = {
                        "exists": True,
                        "size": size,
                        "category": category
                    }
                else:
                    validation["all_present"] = False
                    validation["missing_files"].append({
                        "name": filename,
                        "category": category
                    })
                    validation["file_details"][filename] = {
                        "exists": False,
                        "category": category
                    }
        
        return validation
    
    def format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def generate_readme(self, validation: Dict[str, Any]) -> str:
        """
        Generate README.txt for the ZIP package
        """
        
        readme_lines = [
            "=" * 80,
            "PANELIN GPT CONFIGURATION PACKAGE",
            "Complete Deployment Package for OpenAI Custom GPT",
            "=" * 80,
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Files: {len(validation['present_files'])}",
            f"Total Size: {self.format_size(validation['total_size'])}",
            "",
            "=" * 80,
            "CONTENTS",
            "=" * 80,
            "",
            "This package contains everything needed to deploy the Panelin GPT:",
            "",
            "1. Knowledge Base Files (21 files across 6 phases)",
            "   - Master KB, pricing data, catalogs, BOM rules",
            "   - Optimized lookup tables and indexes",
            "   - Validation and reference data",
            "   - Documentation and guides",
            "   - Supporting files and assets",
            "",
            "2. Configuration Files",
            "   - GPT_Deploy_Package/gpt_deployment_config.json",
            "   - GPT_Deploy_Package/openai_gpt_config.json",
            "   - GPT_Deploy_Package/validation_report.json",
            "",
            "3. Deployment Instructions",
            "   - GPT_Deploy_Package/DEPLOYMENT_GUIDE.md (comprehensive)",
            "   - GPT_Deploy_Package/QUICK_REFERENCE.txt (one-page)",
            "   - Configuration and setup guides",
            "",
            "=" * 80,
            "QUICK START",
            "=" * 80,
            "",
            "1. Extract this ZIP file to a folder",
            "",
            "2. Read 'GPT_Deploy_Package/DEPLOYMENT_GUIDE.md' for full instructions",
            "",
            "3. Go to OpenAI GPT Builder: https://chat.openai.com/gpts/editor",
            "",
            "4. Create a new GPT and configure basic settings:",
            "   - Name: Panelin - BMC Assistant Pro",
            "   - Description: Copy from openai_gpt_config.json",
            "   - Instructions: Copy from openai_gpt_config.json",
            "",
            "5. Upload Knowledge Base files in EXACT ORDER:",
            "",
            "   PHASE 1 - MASTER KB (CRITICAL - Upload first):",
            "   - BMC_Base_Conocimiento_GPT-2.json",
            "   - bromyros_pricing_master.json",
            "   - accessories_catalog.json",
            "   - bom_rules.json",
            "   ⏱️  PAUSE 2-3 MINUTES after Phase 1",
            "",
            "   PHASE 2 - OPTIMIZED LOOKUPS:",
            "   - bromyros_pricing_gpt_optimized.json",
            "   - shopify_catalog_v1.json",
            "   - shopify_catalog_index_v1.csv",
            "   ⏱️  PAUSE 2 MINUTES after Phase 2",
            "",
            "   PHASE 3 - VALIDATION:",
            "   - BMC_Base_Unificada_v4.json",
            "   - panelin_truth_bmcuruguay_web_only_v2.json",
            "   ⏱️  PAUSE 2 MINUTES after Phase 3",
            "",
            "   PHASE 4 - DOCUMENTATION:",
            "   - Aleros -2.rtf",
            "   - panelin_context_consolidacion_sin_backend.md",
            "   - PANELIN_KNOWLEDGE_BASE_GUIDE.md",
            "   - PANELIN_QUOTATION_PROCESS.md",
            "   - PANELIN_TRAINING_GUIDE.md",
            "   - GPT_INSTRUCTIONS_PRICING.md",
            "   - GPT_PDF_INSTRUCTIONS.md",
            "   - GPT_OPTIMIZATION_ANALYSIS.md",
            "   - README.md",
            "   ⏱️  PAUSE 2 MINUTES after Phase 4",
            "",
            "   PHASE 5 - SUPPORTING:",
            "   - Instrucciones GPT.rtf",
            "   - Panelin_GPT_config.json",
            "   ⏱️  PAUSE 2 MINUTES after Phase 5",
            "",
            "   PHASE 6 - ASSETS:",
            "   - bmc_logo.png",
            "",
            "6. Configure capabilities:",
            "   ✅ Enable: Web Browsing",
            "   ✅ Enable: DALL·E Image Generation",
            "   ✅ Enable: Code Interpreter",
            "",
            "7. Save and test your GPT",
            "",
            "=" * 80,
            "IMPORTANT NOTES",
            "=" * 80,
            "",
            "⚠️  CRITICAL:",
            "- Upload files in the exact order specified above",
            "- Wait 2-3 minutes between Phase 1 and Phase 2 (mandatory)",
            "- Wait 2 minutes between other phases",
            "- Do NOT skip phases or reorder files",
            "",
            "📋 File Upload Sequence:",
            "The order is critical for proper GPT knowledge indexing.",
            "Phase 1 contains core knowledge that other phases reference.",
            "",
            "🕒 Estimated Time:",
            "- Configuration setup: 5 minutes",
            "- File uploads: 10-15 minutes (including pauses)",
            "- Testing: 5 minutes",
            "- Total: 20-25 minutes",
            "",
            "=" * 80,
            "FILE MANIFEST",
            "=" * 80,
            "",
        ]
        
        # Add file manifest by category
        for category, files in self.get_all_required_files().items():
            readme_lines.append(f"\n{category.replace('_', ' ').upper()}:")
            for filename in files:
                file_info = validation["file_details"].get(filename, {})
                if file_info.get("exists"):
                    size_str = self.format_size(file_info["size"])
                    readme_lines.append(f"  ✅ {filename} ({size_str})")
                else:
                    readme_lines.append(f"  ❌ {filename} (MISSING)")
        
        if validation["missing_files"]:
            readme_lines.extend([
                "",
                "=" * 80,
                "⚠️  WARNING: MISSING FILES",
                "=" * 80,
                "",
                "The following files are missing from the package:",
                ""
            ])
            for missing in validation["missing_files"]:
                readme_lines.append(f"  ❌ {missing['name']} (Category: {missing['category']})")
            readme_lines.extend([
                "",
                "The package is incomplete. Please ensure all files are present",
                "before deploying to OpenAI.",
                ""
            ])
        
        readme_lines.extend([
            "",
            "=" * 80,
            "SUPPORT",
            "=" * 80,
            "",
            "Repository: https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3",
            "Documentation: See included DEPLOYMENT_GUIDE.md",
            "",
            "For detailed deployment instructions, troubleshooting, and FAQ:",
            "- Read GPT_Deploy_Package/DEPLOYMENT_GUIDE.md",
            "- See GPT_AUTOCONFIG_GUIDE.md for configuration details",
            "- Check DEPLOYMENT_CHECKLIST.md for step-by-step process",
            "",
            "=" * 80,
        ])
        
        return "\n".join(readme_lines)
    
    def generate_manifest(self, validation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate manifest file with all package contents
        """
        
        manifest = {
            "package_name": "Panelin GPT Configuration Package",
            "generated_at": datetime.now().isoformat(),
            "version": "3.3",
            "total_files": len(validation["present_files"]),
            "total_size_bytes": validation["total_size"],
            "total_size_readable": self.format_size(validation["total_size"]),
            "all_files_present": validation["all_present"],
            "missing_count": len(validation["missing_files"]),
            "files": []
        }
        
        for file_info in validation["present_files"]:
            manifest["files"].append({
                "name": file_info["name"],
                "category": file_info["category"],
                "size_bytes": file_info["size"],
                "size_readable": self.format_size(file_info["size"])
            })
        
        if validation["missing_files"]:
            manifest["missing_files"] = [
                {"name": f["name"], "category": f["category"]}
                for f in validation["missing_files"]
            ]
        
        return manifest
    
    def run_autoconfig(self) -> bool:
        """
        Run autoconfig_gpt.py to generate deployment package
        Returns True if successful, False otherwise
        """
        
        print("=" * 80)
        print("STEP 1: Generating GPT Configuration")
        print("=" * 80)
        print()
        
        autoconfig_script = self.repo_root / "autoconfig_gpt.py"
        
        if not autoconfig_script.exists():
            print(f"❌ Error: {autoconfig_script} not found")
            return False
        
        # Import and run the autoconfig module
        import importlib.util
        spec = importlib.util.spec_from_file_location("autoconfig_gpt", autoconfig_script)
        autoconfig_module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(autoconfig_module)
            
            # Run the configurator with auto-approval
            configurator = autoconfig_module.GPTAutoConfigurator(self.repo_root)
            
            # Suppress approval prompt by directly running steps
            base_config = configurator.load_base_config()
            validation = configurator.validate_required_files()
            deployment_config = configurator.generate_deployment_config(base_config)
            configurator.save_deployment_package(deployment_config, validation)
            
            print("✅ GPT configuration generated successfully")
            print(f"   Output: {self.repo_root / 'GPT_Deploy_Package'}")
            print()
            return True
            
        except Exception as e:
            print(f"❌ Error running autoconfig: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_zip_package(self, validation: Dict[str, Any]) -> Optional[Path]:
        """
        Create the ZIP package with all files
        """
        
        print("=" * 80)
        print("STEP 2: Creating ZIP Package")
        print("=" * 80)
        print()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = self.output_dir / self.zip_filename
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # Add README
                print("📝 Adding README.txt...")
                readme_content = self.generate_readme(validation)
                zipf.writestr("README.txt", readme_content)
                
                # Add manifest
                print("📝 Adding MANIFEST.json...")
                manifest = self.generate_manifest(validation)
                zipf.writestr("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False))
                
                # Add all knowledge base files by category
                files_by_category = self.get_all_required_files()
                
                for category, files in files_by_category.items():
                    print(f"\n📦 Adding {category.replace('_', ' ')} files...")
                    
                    for filename in files:
                        filepath = self.repo_root / filename
                        
                        if filepath.exists():
                            # Organize files in category folders within ZIP
                            arcname = f"{category}/{filename}"
                            zipf.write(filepath, arcname)
                            print(f"   ✅ {filename}")
                        else:
                            print(f"   ⚠️  Skipped (not found): {filename}")
                
                # Add GPT_Deploy_Package directory if it exists
                deploy_pkg_dir = self.repo_root / "GPT_Deploy_Package"
                if deploy_pkg_dir.exists():
                    print("\n📦 Adding GPT_Deploy_Package files...")
                    for file in deploy_pkg_dir.iterdir():
                        if file.is_file():
                            arcname = f"GPT_Deploy_Package/{file.name}"
                            zipf.write(file, arcname)
                            print(f"   ✅ {file.name}")
                
                print()
            
            return zip_path
            
        except Exception as e:
            print(f"❌ Error creating ZIP: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run(self) -> int:
        """
        Run the complete ZIP package generation process
        """
        
        print()
        print("=" * 80)
        print("GPT CONFIGURATION ZIP PACKAGE GENERATOR")
        print("Panelin - BMC Assistant Pro")
        print("=" * 80)
        print()
        
        try:
            # Step 1: Run autoconfig to generate deployment package
            if not self.run_autoconfig():
                print("\n⚠️  Warning: Autoconfig failed, continuing with available files...")
            
            # Step 2: Validate all required files
            files_by_category = self.get_all_required_files()
            validation = self.validate_files(files_by_category)
            
            print("=" * 80)
            print("File Validation")
            print("=" * 80)
            print(f"✅ Found: {len(validation['present_files'])} files")
            print(f"📦 Total size: {self.format_size(validation['total_size'])}")
            
            if validation['missing_files']:
                print(f"⚠️  Missing: {len(validation['missing_files'])} files")
                for missing in validation['missing_files']:
                    print(f"   - {missing['name']} ({missing['category']})")
            
            print()
            
            # Step 3: Create ZIP package
            zip_path = self.create_zip_package(validation)
            
            if not zip_path:
                print("\n❌ Failed to create ZIP package")
                return 1
            
            # Step 4: Display success message
            print("=" * 80)
            print("✅ ZIP PACKAGE CREATED SUCCESSFULLY")
            print("=" * 80)
            print()
            print(f"📦 Package: {zip_path}")
            print(f"📏 Size: {self.format_size(zip_path.stat().st_size)}")
            print(f"📁 Location: {self.output_dir}")
            print()
            print("Contents:")
            print(f"  - {len(validation['present_files'])} knowledge base files")
            print("  - GPT configuration files")
            print("  - Deployment guides and instructions")
            print("  - README.txt with quick start guide")
            print("  - MANIFEST.json with complete file listing")
            print()
            print("=" * 80)
            print("NEXT STEPS")
            print("=" * 80)
            print()
            print("1. Download or extract the ZIP file")
            print("2. Read README.txt for quick start instructions")
            print("3. Follow GPT_Deploy_Package/DEPLOYMENT_GUIDE.md for detailed steps")
            print("4. Deploy to OpenAI GPT Builder: https://chat.openai.com/gpts/editor")
            print()
            print("The ZIP package contains everything needed for GPT deployment!")
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
    
    packager = GPTZipPackager(repo_root)
    return packager.run()


if __name__ == "__main__":
    sys.exit(main())
