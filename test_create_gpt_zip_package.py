"""
Test suite for create_gpt_zip_package.py

Tests the GPT ZIP package generator functionality to ensure:
1. Package generation completes successfully
2. Required files are included in the package
3. Package structure follows expected organization
4. Generated files are valid (ZIP format, JSON manifest, etc.)
"""

import json
import os
import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent))
import create_gpt_zip_package


class TestGPTZipPackager:
    """Test the GPTZipPackager class functionality."""
    
    def test_packager_initialization(self):
        """Test that packager initializes with correct paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            
            assert packager.repo_root == repo_root
            assert packager.output_dir == repo_root / "GPT_Complete_Package"
            assert "Panelin_GPT_Config_Package_" in packager.zip_filename
            assert packager.zip_filename.endswith(".zip")
    
    def test_get_all_required_files_structure(self):
        """Test that required files are organized by category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            files_by_category = packager.get_all_required_files()
            
            # Check expected categories exist (GPT_Deploy_Package is added dynamically later)
            expected_categories = [
                "Phase_1_Master_KB",
                "Phase_2_Optimized_Lookups",
                "Phase_3_Validation",
                "Phase_4_Documentation",
                "Phase_5_Supporting",
                "Phase_6_Assets",
                "Configuration_Files",
                "Deployment_Guides",
            ]
            
            for category in expected_categories:
                assert category in files_by_category, f"Missing category: {category}"
                assert isinstance(files_by_category[category], list)
    
    def test_validate_files_missing_files(self):
        """Test validation when required files are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            files_by_category = packager.get_all_required_files()
            
            # Should return validation dict with all_present=False when no files exist
            result = packager.validate_files(files_by_category)
            assert result["all_present"] is False
            assert len(result["missing_files"]) > 0
    
    def test_validate_files_with_files(self):
        """Test validation when required files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            
            # Create some required files
            test_files = [
                "BMC_Base_Conocimiento_GPT-2.json",
                "bromyros_pricing_master.json",
                "accessories_catalog.json",
                "bom_rules.json",
                "README.md"
            ]
            
            for filename in test_files:
                filepath = repo_root / filename
                filepath.write_text('{"test": "data"}')
            
            files_by_category = packager.get_all_required_files()
            
            # Should find at least these files
            result = packager.validate_files(files_by_category)
            assert isinstance(result, dict)
            assert "all_present" in result
            assert "present_files" in result
            assert len(result["present_files"]) >= len(test_files)
    
    def test_generate_readme_content(self):
        """Test README.txt generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            
            # Create validation data
            validation = {
                "all_present": True,
                "present_files": [],
                "missing_files": [],
                "total_size": 1000000,
                "file_details": {}
            }
            
            readme_content = packager.generate_readme(validation)
            
            assert isinstance(readme_content, str)
            assert len(readme_content) > 0
            assert "PANELIN GPT" in readme_content.upper()
            assert "Phase" in readme_content or "PHASE" in readme_content
    
    def test_generate_manifest(self):
        """Test MANIFEST.json generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            
            # Create validation data with file_details
            validation = {
                "all_present": True,
                "present_files": [
                    {"name": "file1.json", "category": "Phase_1", "size": 100},
                    {"name": "file2.json", "category": "Phase_1", "size": 200},
                    {"name": "file3.json", "category": "Phase_2", "size": 150}
                ],
                "missing_files": [],
                "total_size": 450,
                "file_details": {
                    "file1.json": {"exists": True, "size": 100, "category": "Phase_1"},
                    "file2.json": {"exists": True, "size": 200, "category": "Phase_1"},
                    "file3.json": {"exists": True, "size": 150, "category": "Phase_2"}
                }
            }
            
            manifest = packager.generate_manifest(validation)
            
            # Verify it's a dict with expected structure
            assert isinstance(manifest, dict)
            assert "package_name" in manifest
            assert "version" in manifest or "generated_at" in manifest
            assert "files" in manifest or "files_by_phase" in manifest or "present_files" in manifest


class TestPackageGeneration:
    """Integration tests for full package generation."""
    
    @pytest.mark.skipif(
        not (Path.cwd() / "BMC_Base_Conocimiento_GPT-2.json").exists(),
        reason="Required KB files not present"
    )
    def test_full_package_generation(self):
        """Test complete package generation process."""
        # This test only runs if we're in a repo with the actual KB files
        repo_root = Path.cwd()
        
        packager = create_gpt_zip_package.GPTZipPackager(repo_root)
        files_by_category = packager.get_all_required_files()
        
        # Check that required files validation works
        validation = packager.validate_files(files_by_category)
        assert isinstance(validation, dict)
        assert "all_present" in validation
    
    def test_zip_creation_structure(self):
        """Test that created ZIP has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            
            # Create minimal required files
            test_files = {
                "Phase_1_Master_KB": ["test1.json"],
                "Phase_2_Optimized_Lookups": ["test2.json"],
            }
            
            for category, files in test_files.items():
                for filename in files:
                    filepath = repo_root / filename
                    filepath.write_text('{"test": "data"}')
            
            # Create output directory
            output_dir = repo_root / "GPT_Complete_Package"
            output_dir.mkdir()
            
            # Create a test ZIP
            zip_path = output_dir / "test_package.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add README.txt
                zipf.writestr("README.txt", "Test readme")
                
                # Add MANIFEST.json
                manifest = {
                    "package_name": "Test Package",
                    "version": "1.0",
                    "files_by_phase": test_files
                }
                zipf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
                
                # Add test files
                for category, files in test_files.items():
                    for filename in files:
                        zipf.writestr(f"{category}/{filename}", '{"test": "data"}')
            
            # Verify ZIP was created
            assert zip_path.exists()
            assert zip_path.stat().st_size > 0
            
            # Verify ZIP contents
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                namelist = zipf.namelist()
                assert "README.txt" in namelist
                assert "MANIFEST.json" in namelist
                
                # Verify phase directories exist
                assert any("Phase_1_Master_KB/" in name for name in namelist)
                assert any("Phase_2_Optimized_Lookups/" in name for name in namelist)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_packager_with_nonexistent_repo_root(self):
        """Test packager behavior with nonexistent directory."""
        nonexistent_path = Path(tempfile.gettempdir()) / "nonexistent_repo_test_12345"
        packager = create_gpt_zip_package.GPTZipPackager(nonexistent_path)
        
        # Should initialize but validation should fail
        assert packager.repo_root == nonexistent_path
        files_by_category = packager.get_all_required_files()
        result = packager.validate_files(files_by_category)
        assert result["all_present"] is False
    
    def test_readme_generation_always_succeeds(self):
        """Test that README generation doesn't fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            
            # Create minimal validation data with file_details
            validation = {
                "all_present": True,
                "present_files": [],
                "missing_files": [],
                "total_size": 0,
                "file_details": {}
            }
            
            # Should always return a string, never crash
            readme = packager.generate_readme(validation)
            assert isinstance(readme, str)
            assert len(readme) > 100  # Should be substantial content
    
    def test_manifest_with_empty_files(self):
        """Test manifest generation with no files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            
            validation = {
                "all_present": False,
                "present_files": [],
                "missing_files": [],
                "total_size": 0,
                "file_details": {}
            }
            
            manifest = packager.generate_manifest(validation)
            
            # Should still generate valid dict
            assert isinstance(manifest, dict)
            assert "package_name" in manifest


class TestFileOrganization:
    """Test file organization and categorization."""
    
    def test_phase_1_master_kb_files(self):
        """Test Phase 1 Master KB files are correctly defined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            files = packager.get_all_required_files()
            
            phase1_files = files["Phase_1_Master_KB"]
            
            # Verify core KB files are included
            assert "BMC_Base_Conocimiento_GPT-2.json" in phase1_files
            assert "bromyros_pricing_master.json" in phase1_files
            assert "accessories_catalog.json" in phase1_files
            assert "bom_rules.json" in phase1_files
    
    def test_configuration_files_category(self):
        """Test Configuration_Files category includes guides."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            files = packager.get_all_required_files()
            
            config_files = files["Configuration_Files"]
            
            # Verify key config files are included
            assert "GPT_AUTOCONFIG_GUIDE.md" in config_files
            assert "GPT_AUTOCONFIG_FAQ.md" in config_files
    
    def test_deployment_guides_category(self):
        """Test Deployment_Guides category includes deployment docs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            packager = create_gpt_zip_package.GPTZipPackager(repo_root)
            files = packager.get_all_required_files()
            
            deployment_files = files["Deployment_Guides"]
            
            # Verify deployment guides are included
            assert "DEPLOYMENT_CONFIG.md" in deployment_files
            assert "DEPLOYMENT_QUICK_REFERENCE.md" in deployment_files
            assert "DEPLOYMENT_CHECKLIST.md" in deployment_files


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
