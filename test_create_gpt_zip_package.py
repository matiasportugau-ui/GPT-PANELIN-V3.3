"""
Test suite for create_gpt_zip_package.py

Tests the GPTZipPackager class and its methods for creating
comprehensive ZIP packages for GPT configuration deployment.

These tests validate:
1. Class initialization and setup
2. File discovery and validation
3. README and manifest generation
4. ZIP package creation
5. Error handling and edge cases

Run from repository root:
    pytest test_create_gpt_zip_package.py -v
"""

import json
import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

import pytest

# Import the module to test
from create_gpt_zip_package import GPTZipPackager


class TestGPTZipPackagerInit:
    """Test GPTZipPackager initialization."""
    
    def test_init_with_valid_path(self, tmp_path):
        """Test initialization with valid repository path."""
        packager = GPTZipPackager(tmp_path)
        
        assert packager.repo_root == tmp_path
        assert packager.output_dir == tmp_path / "GPT_Complete_Package"
        assert packager.zip_filename.startswith("Panelin_GPT_Config_Package_")
        assert packager.zip_filename.endswith(".zip")
    
    def test_init_creates_timestamped_filename(self, tmp_path):
        """Test that zip filename contains timestamp."""
        packager = GPTZipPackager(tmp_path)
        
        # Extract timestamp from filename
        filename_parts = packager.zip_filename.split('_')
        assert len(filename_parts) >= 5
        # Should contain date in format YYYYMMDD (8 digits)
        date_part = filename_parts[-2]
        assert len(date_part) == 8
        assert date_part.isdigit()


class TestGetAllRequiredFiles:
    """Test get_all_required_files method."""
    
    def test_returns_dict_with_categories(self, tmp_path):
        """Test that method returns dictionary with all categories."""
        packager = GPTZipPackager(tmp_path)
        files = packager.get_all_required_files()
        
        assert isinstance(files, dict)
        
        # Check all expected categories are present
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
            assert category in files
            assert isinstance(files[category], list)
            assert len(files[category]) > 0
    
    def test_phase_1_contains_master_kb_files(self, tmp_path):
        """Test that Phase 1 contains expected master KB files."""
        packager = GPTZipPackager(tmp_path)
        files = packager.get_all_required_files()
        
        phase_1 = files["Phase_1_Master_KB"]
        
        # Check for critical master KB files
        assert "BMC_Base_Conocimiento_GPT-2.json" in phase_1
        assert "bromyros_pricing_master.json" in phase_1
        assert "accessories_catalog.json" in phase_1
        assert "bom_rules.json" in phase_1
    
    def test_all_files_are_strings(self, tmp_path):
        """Test that all file entries are strings."""
        packager = GPTZipPackager(tmp_path)
        files = packager.get_all_required_files()
        
        for category, file_list in files.items():
            for filename in file_list:
                assert isinstance(filename, str)
                assert len(filename) > 0


class TestValidateFiles:
    """Test validate_files method."""
    
    def test_validate_with_all_files_present(self, tmp_path):
        """Test validation when all files are present."""
        packager = GPTZipPackager(tmp_path)
        
        # Create a simple file structure
        test_files = {
            "Phase_1_Test": ["test1.json", "test2.json"],
            "Phase_2_Test": ["test3.json"]
        }
        
        # Create the files
        for category, filenames in test_files.items():
            for filename in filenames:
                filepath = tmp_path / filename
                filepath.write_text("test content")
        
        validation = packager.validate_files(test_files)
        
        assert validation["all_present"] is True
        assert len(validation["missing_files"]) == 0
        assert len(validation["present_files"]) == 3
        assert validation["total_size"] > 0
    
    def test_validate_with_missing_files(self, tmp_path):
        """Test validation when some files are missing."""
        packager = GPTZipPackager(tmp_path)
        
        test_files = {
            "Phase_1_Test": ["exists.json", "missing.json"]
        }
        
        # Create only one file
        (tmp_path / "exists.json").write_text("test content")
        
        validation = packager.validate_files(test_files)
        
        assert validation["all_present"] is False
        assert len(validation["missing_files"]) == 1
        assert validation["missing_files"][0]["name"] == "missing.json"
        assert len(validation["present_files"]) == 1
    
    def test_validate_returns_file_details(self, tmp_path):
        """Test that validation returns detailed file information."""
        packager = GPTZipPackager(tmp_path)
        
        test_files = {"Phase_Test": ["test.json"]}
        (tmp_path / "test.json").write_text("test content")
        
        validation = packager.validate_files(test_files)
        
        assert "file_details" in validation
        assert "test.json" in validation["file_details"]
        
        file_detail = validation["file_details"]["test.json"]
        assert file_detail["exists"] is True
        assert file_detail["size"] > 0
        assert file_detail["category"] == "Phase_Test"
    
    def test_validate_calculates_total_size(self, tmp_path):
        """Test that total size is correctly calculated."""
        packager = GPTZipPackager(tmp_path)
        
        test_files = {"Phase_Test": ["file1.json", "file2.json"]}
        
        # Create files with known sizes
        (tmp_path / "file1.json").write_text("a" * 100)  # 100 bytes
        (tmp_path / "file2.json").write_text("b" * 200)  # 200 bytes
        
        validation = packager.validate_files(test_files)
        
        assert validation["total_size"] == 300


class TestFormatSize:
    """Test format_size method."""
    
    def test_format_bytes(self, tmp_path):
        """Test formatting bytes."""
        packager = GPTZipPackager(tmp_path)
        
        assert packager.format_size(512) == "512.00 B"
        assert packager.format_size(1) == "1.00 B"
    
    def test_format_kilobytes(self, tmp_path):
        """Test formatting kilobytes."""
        packager = GPTZipPackager(tmp_path)
        
        assert packager.format_size(1024) == "1.00 KB"
        assert packager.format_size(2048) == "2.00 KB"
        assert packager.format_size(1536) == "1.50 KB"
    
    def test_format_megabytes(self, tmp_path):
        """Test formatting megabytes."""
        packager = GPTZipPackager(tmp_path)
        
        assert packager.format_size(1024 * 1024) == "1.00 MB"
        assert packager.format_size(5 * 1024 * 1024) == "5.00 MB"
    
    def test_format_gigabytes(self, tmp_path):
        """Test formatting gigabytes."""
        packager = GPTZipPackager(tmp_path)
        
        assert packager.format_size(1024 * 1024 * 1024) == "1.00 GB"


class TestGenerateReadme:
    """Test generate_readme method."""
    
    def test_readme_contains_header(self, tmp_path):
        """Test that README contains proper header."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [],
            "total_size": 0,
            "file_details": {}
        }
        
        readme = packager.generate_readme(validation)
        
        assert "PANELIN GPT CONFIGURATION PACKAGE" in readme
        assert "Complete Deployment Package" in readme
        assert "=" * 80 in readme
    
    def test_readme_includes_file_count(self, tmp_path):
        """Test that README includes file count."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [{"name": "test1.json"}, {"name": "test2.json"}],
            "missing_files": [],
            "total_size": 1024,
            "file_details": {}
        }
        
        readme = packager.generate_readme(validation)
        
        assert "Total Files: 2" in readme
    
    def test_readme_includes_quick_start(self, tmp_path):
        """Test that README includes quick start section."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [],
            "total_size": 0,
            "file_details": {}
        }
        
        readme = packager.generate_readme(validation)
        
        assert "QUICK START" in readme
        assert "PHASE 1 - MASTER KB" in readme
        assert "PHASE 2 - OPTIMIZED LOOKUPS" in readme
    
    def test_readme_shows_missing_files_warning(self, tmp_path):
        """Test that README warns about missing files."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [{"name": "missing.json", "category": "Phase_1"}],
            "total_size": 0,
            "file_details": {"missing.json": {"exists": False}}
        }
        
        readme = packager.generate_readme(validation)
        
        assert "WARNING: MISSING FILES" in readme
        assert "missing.json" in readme


class TestGenerateManifest:
    """Test generate_manifest method."""
    
    def test_manifest_structure(self, tmp_path):
        """Test that manifest has correct structure."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [
                {"name": "test.json", "category": "Phase_1", "size": 1024}
            ],
            "missing_files": [],
            "total_size": 1024,
            "all_present": True
        }
        
        manifest = packager.generate_manifest(validation)
        
        assert isinstance(manifest, dict)
        assert "package_name" in manifest
        assert "generated_at" in manifest
        assert "version" in manifest
        assert "total_files" in manifest
        assert "files" in manifest
        
        assert manifest["package_name"] == "Panelin GPT Configuration Package"
        # Verify version field exists (don't hardcode specific version)
        assert isinstance(manifest["version"], str)
        assert len(manifest["version"]) > 0
        assert manifest["total_files"] == 1
    
    def test_manifest_includes_file_list(self, tmp_path):
        """Test that manifest includes list of files."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [
                {"name": "file1.json", "category": "Phase_1", "size": 100},
                {"name": "file2.json", "category": "Phase_2", "size": 200}
            ],
            "missing_files": [],
            "total_size": 300,
            "all_present": True
        }
        
        manifest = packager.generate_manifest(validation)
        
        assert len(manifest["files"]) == 2
        assert manifest["files"][0]["name"] == "file1.json"
        assert manifest["files"][0]["size_bytes"] == 100
        assert manifest["files"][1]["name"] == "file2.json"
    
    def test_manifest_includes_missing_files_when_present(self, tmp_path):
        """Test that manifest lists missing files when any are missing."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [{"name": "missing.json", "category": "Phase_1"}],
            "total_size": 0,
            "all_present": False
        }
        
        manifest = packager.generate_manifest(validation)
        
        assert "missing_files" in manifest
        assert len(manifest["missing_files"]) == 1
        assert manifest["missing_files"][0]["name"] == "missing.json"


class TestCreateZipPackage:
    """Test create_zip_package method."""
    
    def test_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [],
            "total_size": 0,
            "file_details": {}
        }
        
        assert not packager.output_dir.exists()
        
        packager.create_zip_package(validation)
        
        assert packager.output_dir.exists()
        assert packager.output_dir.is_dir()
    
    def test_creates_zip_file(self, tmp_path):
        """Test that ZIP file is created."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [],
            "total_size": 0,
            "all_present": True,
            "file_details": {}
        }
        
        zip_path = packager.create_zip_package(validation)
        
        assert zip_path is not None
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"
    
    def test_zip_contains_readme(self, tmp_path):
        """Test that ZIP contains README.txt."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [],
            "total_size": 0,
            "all_present": True,
            "file_details": {}
        }
        
        zip_path = packager.create_zip_package(validation)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            namelist = zipf.namelist()
            assert "README.txt" in namelist
            
            # Verify README content
            readme_content = zipf.read("README.txt").decode('utf-8')
            assert "PANELIN GPT CONFIGURATION PACKAGE" in readme_content
    
    def test_zip_contains_manifest(self, tmp_path):
        """Test that ZIP contains MANIFEST.json."""
        packager = GPTZipPackager(tmp_path)
        
        validation = {
            "present_files": [],
            "missing_files": [],
            "total_size": 0,
            "all_present": True,
            "file_details": {}
        }
        
        zip_path = packager.create_zip_package(validation)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            namelist = zipf.namelist()
            assert "MANIFEST.json" in namelist
            
            # Verify manifest is valid JSON
            manifest_content = zipf.read("MANIFEST.json").decode('utf-8')
            manifest = json.loads(manifest_content)
            assert "package_name" in manifest
    
    def test_zip_organizes_files_by_category(self, tmp_path, monkeypatch):
        """Test that ZIP organizes files into category folders."""
        packager = GPTZipPackager(tmp_path)
        
        # Create test files
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": true}')
        
        # Use custom file structure instead of the default one
        test_files = {"Phase_1_Test": ["test.json"]}
        
        # Manually create the validation structure as the method would
        validation = {
            "all_present": True,
            "missing_files": [],
            "present_files": [{"name": "test.json", "category": "Phase_1_Test", "size": test_file.stat().st_size, "path": str(test_file)}],
            "total_size": test_file.stat().st_size,
            "file_details": {"test.json": {"exists": True, "size": test_file.stat().st_size, "category": "Phase_1_Test"}}
        }
        
        # Use monkeypatch to override the get_all_required_files method
        monkeypatch.setattr(packager, 'get_all_required_files', lambda: test_files)
        
        zip_path = packager.create_zip_package(validation)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            namelist = zipf.namelist()
            assert "Phase_1_Test/test.json" in namelist


class TestRunAutoconfig:
    """Test run_autoconfig method."""
    
    def test_run_autoconfig_returns_false_when_script_missing(self, tmp_path):
        """Test that run_autoconfig returns False when autoconfig script is missing."""
        packager = GPTZipPackager(tmp_path)
        
        # autoconfig_gpt.py doesn't exist in tmp_path
        result = packager.run_autoconfig()
        
        assert result is False
    
    def test_run_autoconfig_with_existing_script(self, tmp_path):
        """Test run_autoconfig with existing autoconfig script."""
        # This test would require mocking the entire autoconfig module
        # For now, we'll test the error path
        packager = GPTZipPackager(tmp_path)
        
        result = packager.run_autoconfig()
        assert isinstance(result, bool)


class TestRun:
    """Test the main run method."""
    
    @patch.object(GPTZipPackager, 'run_autoconfig')
    @patch.object(GPTZipPackager, 'create_zip_package')
    def test_run_returns_success_code(self, mock_create_zip, mock_autoconfig, tmp_path):
        """Test that run returns 0 on success."""
        packager = GPTZipPackager(tmp_path)
        
        # Mock successful execution
        mock_autoconfig.return_value = True
        mock_zip_path = tmp_path / "test.zip"
        mock_zip_path.write_text("test")
        mock_create_zip.return_value = mock_zip_path
        
        result = packager.run()
        
        assert result == 0
    
    @patch.object(GPTZipPackager, 'run_autoconfig')
    @patch.object(GPTZipPackager, 'create_zip_package')
    def test_run_returns_error_code_on_failure(self, mock_create_zip, mock_autoconfig, tmp_path):
        """Test that run returns 1 on failure."""
        packager = GPTZipPackager(tmp_path)
        
        # Mock failed ZIP creation
        mock_autoconfig.return_value = True
        mock_create_zip.return_value = None
        
        result = packager.run()
        
        assert result == 1
    
    @patch.object(GPTZipPackager, 'run_autoconfig')
    def test_run_continues_on_autoconfig_failure(self, mock_autoconfig, tmp_path):
        """Test that run continues even if autoconfig fails."""
        packager = GPTZipPackager(tmp_path)
        
        # Mock autoconfig failure
        mock_autoconfig.return_value = False
        
        # Run should continue and attempt to create ZIP
        # This will fail because no files exist, but we're testing
        # that it doesn't exit early
        result = packager.run()
        
        # Should have attempted to continue
        assert mock_autoconfig.called


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_handles_special_characters_in_filenames(self, tmp_path):
        """Test handling of filenames with spaces (e.g., 'Esquema json.rtf')."""
        packager = GPTZipPackager(tmp_path)
        
        test_files = {"Phase_Test": ["Esquema json.rtf"]}
        (tmp_path / "Esquema json.rtf").write_text("test content")
        
        validation = packager.validate_files(test_files)
        
        assert validation["all_present"] is True
        assert len(validation["present_files"]) == 1
    
    def test_handles_empty_file(self, tmp_path):
        """Test handling of empty files."""
        packager = GPTZipPackager(tmp_path)
        
        test_files = {"Phase_Test": ["empty.json"]}
        (tmp_path / "empty.json").write_text("")
        
        validation = packager.validate_files(test_files)
        
        assert validation["all_present"] is True
        assert validation["file_details"]["empty.json"]["size"] == 0
    
    def test_format_size_with_zero(self, tmp_path):
        """Test format_size with zero bytes."""
        packager = GPTZipPackager(tmp_path)
        
        assert packager.format_size(0) == "0.00 B"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
