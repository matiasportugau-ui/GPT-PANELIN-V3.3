#!/usr/bin/env python3
"""
Panelin GPT Automatic Preload System
=====================================

This module automatically initializes the Panelin GPT system on first user interaction.
It verifies all required knowledge base files, pre-caches critical data, and provides
full visibility of the system configuration, files, and paths.

Features:
- Automatic file validation (17 required files)
- Pre-caching of pricing, BOM rules, and autoportancia tables
- Startup visibility report generation
- No user validation required
- Explains what's being loaded and why

Version: 1.0
Compatible with: Panelin GPT v3.3, KB v7.0
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class PanelinPreloadSystem:
    """
    Automatic preload system for Panelin GPT.
    
    Validates and pre-loads all required knowledge base files on first interaction,
    providing full visibility without requiring user validation.
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        """
        Initialize the preload system.
        
        Args:
            root_path: Root path for knowledge base files. 
                      If None, uses current directory.
        """
        self.root_path = root_path or Path(__file__).parent
        self.startup_context_path = self.root_path / "gpt_startup_context.json"
        self.startup_context = None
        self.validation_results = {}
        self.cache = {}
        
    def load_startup_context(self) -> Dict:
        """Load the startup context configuration."""
        try:
            with open(self.startup_context_path, 'r', encoding='utf-8') as f:
                self.startup_context = json.load(f)
            return self.startup_context
        except FileNotFoundError:
            return {
                "error": f"Startup context file not found: {self.startup_context_path}",
                "status": "fallback_mode"
            }
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON in startup context: {e}",
                "status": "fallback_mode"
            }
    
    def verify_required_files(self) -> Dict[str, Dict]:
        """
        Verify that all required knowledge base files exist and are accessible.
        
        Returns:
            Dictionary with validation results for each file phase.
        """
        if not self.startup_context:
            self.load_startup_context()
        
        results = {}
        required_files = self.startup_context.get("required_files", {})
        
        for phase_name, phase_data in required_files.items():
            phase_results = {
                "description": phase_data.get("description", ""),
                "files": []
            }
            
            files = phase_data.get("files", [])
            for file_info in files:
                file_name = file_info if isinstance(file_info, str) else file_info.get("name")
                file_path = self.root_path / file_name
                
                file_result = {
                    "name": file_name,
                    "exists": file_path.exists(),
                    "path": str(file_path),
                    "size": file_path.stat().st_size if file_path.exists() else 0,
                    "priority": file_info.get("priority", "NORMAL") if isinstance(file_info, dict) else "NORMAL",
                    "purpose": file_info.get("purpose", "") if isinstance(file_info, dict) else ""
                }
                
                # Validate JSON files
                if file_name.endswith('.json') and file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json.load(f)
                        file_result["valid_json"] = True
                    except json.JSONDecodeError:
                        file_result["valid_json"] = False
                        file_result["error"] = "Invalid JSON format"
                
                phase_results["files"].append(file_result)
            
            results[phase_name] = phase_results
        
        self.validation_results = results
        return results
    
    def preload_critical_data(self) -> Dict[str, bool]:
        """
        Pre-load and cache critical knowledge base data.
        
        Returns:
            Dictionary with status of each preload operation.
        """
        preload_status = {}
        
        # Preload pricing data
        try:
            pricing_path = self.root_path / "BMC_Base_Conocimiento_GPT-2.json"
            if pricing_path.exists():
                with open(pricing_path, 'r', encoding='utf-8') as f:
                    self.cache["pricing_data"] = json.load(f)
                preload_status["pricing_data"] = True
            else:
                preload_status["pricing_data"] = False
        except Exception as e:
            preload_status["pricing_data"] = False
            preload_status["pricing_error"] = str(e)
        
        # Preload accessories catalog
        try:
            accessories_path = self.root_path / "accessories_catalog.json"
            if accessories_path.exists():
                with open(accessories_path, 'r', encoding='utf-8') as f:
                    self.cache["accessories_catalog"] = json.load(f)
                preload_status["accessories_catalog"] = True
            else:
                preload_status["accessories_catalog"] = False
        except Exception as e:
            preload_status["accessories_catalog"] = False
            preload_status["accessories_error"] = str(e)
        
        # Preload BOM rules
        try:
            bom_path = self.root_path / "bom_rules.json"
            if bom_path.exists():
                with open(bom_path, 'r', encoding='utf-8') as f:
                    bom_data = json.load(f)
                    self.cache["bom_rules"] = bom_data
                    # Extract autoportancia table for quick access
                    self.cache["autoportancia_tables"] = bom_data.get("tabla_autoportancia_general", {})
                preload_status["bom_rules"] = True
                preload_status["autoportancia_tables"] = True
            else:
                preload_status["bom_rules"] = False
                preload_status["autoportancia_tables"] = False
        except Exception as e:
            preload_status["bom_rules"] = False
            preload_status["bom_error"] = str(e)
        
        # Preload optimized pricing index
        try:
            optimized_path = self.root_path / "bromyros_pricing_gpt_optimized.json"
            if optimized_path.exists():
                with open(optimized_path, 'r', encoding='utf-8') as f:
                    self.cache["pricing_optimized"] = json.load(f)
                preload_status["pricing_optimized"] = True
            else:
                preload_status["pricing_optimized"] = False
        except Exception as e:
            preload_status["pricing_optimized"] = False
            preload_status["optimized_error"] = str(e)
        
        return preload_status
    
    def generate_visibility_report(self, language: str = "es") -> str:
        """
        Generate a comprehensive visibility report of the system configuration.
        
        Args:
            language: Language for the report ('es' or 'en')
        
        Returns:
            Formatted markdown report showing system status and configuration.
        """
        if not self.startup_context:
            self.load_startup_context()
        
        messages = self.startup_context.get("startup_messages", {}).get(language, {})
        
        # Build the report
        report_parts = []
        
        # Startup header
        report_parts.append(messages.get("preload_start", ""))
        report_parts.append("")
        
        # Progress indicators
        progress = messages.get("preload_progress", [])
        for item in progress:
            report_parts.append(item)
        report_parts.append("")
        
        # Completion message
        report_parts.append(messages.get("preload_complete", ""))
        report_parts.append("")
        
        # Visibility header
        report_parts.append(messages.get("visibility_header", ""))
        report_parts.append("")
        
        # Knowledge base info
        report_parts.append(messages.get("kb_info", ""))
        report_parts.append("")
        
        # Capabilities info
        report_parts.append(messages.get("capabilities_info", ""))
        report_parts.append("")
        
        # Paths info
        report_parts.append(messages.get("paths_info", ""))
        report_parts.append("")
        
        # Add file validation summary
        if self.validation_results:
            report_parts.append("### 📊 Estado de Validación de Archivos\n")
            
            total_files = 0
            valid_files = 0
            critical_missing = []
            
            for phase_name, phase_data in self.validation_results.items():
                for file_info in phase_data.get("files", []):
                    total_files += 1
                    if file_info.get("exists"):
                        valid_files += 1
                    elif file_info.get("priority") == "CRITICAL":
                        critical_missing.append(file_info.get("name"))
            
            report_parts.append(f"**Archivos validados:** {valid_files}/{total_files}")
            
            if critical_missing:
                report_parts.append(f"\n⚠️ **Archivos críticos faltantes:** {', '.join(critical_missing)}")
            else:
                report_parts.append("\n✅ **Todos los archivos críticos están disponibles**")
            
            report_parts.append("")
        
        # Add cache status
        if self.cache:
            report_parts.append("### 💾 Caché Inicializado\n")
            cache_items = []
            for key in self.cache:
                if isinstance(self.cache[key], dict):
                    size = len(self.cache[key])
                    cache_items.append(f"✓ {key} ({size} items)")
                else:
                    cache_items.append(f"✓ {key}")
            report_parts.append("\n".join(cache_items))
            report_parts.append("")
        
        # System info
        system_info = self.startup_context.get("system_info", {})
        report_parts.append("### ℹ️ Información del Sistema\n")
        report_parts.append(f"**Versión:** {system_info.get('version', 'N/A')}")
        report_parts.append(f"**KB Version:** {system_info.get('kb_version', 'N/A')}")
        report_parts.append(f"**Última actualización:** {system_info.get('last_updated', 'N/A')}")
        report_parts.append("")
        
        # Ready message
        report_parts.append("---\n")
        report_parts.append("**🚀 Sistema completamente operativo y listo para asistirte.**\n")
        
        return "\n".join(report_parts)
    
    def initialize(self, show_report: bool = True, language: str = "es") -> Dict:
        """
        Perform complete initialization of the Panelin GPT system.
        
        This is the main entry point called on first user interaction.
        
        Args:
            show_report: Whether to generate and return the visibility report
            language: Language for the report ('es' or 'en')
        
        Returns:
            Dictionary with initialization status and optional visibility report.
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "initialized"
        }
        
        # Load configuration
        context = self.load_startup_context()
        if "error" in context:
            result["status"] = "error"
            result["error"] = context["error"]
            return result
        
        result["system_info"] = context.get("system_info", {})
        
        # Verify files
        validation = self.verify_required_files()
        result["file_validation"] = validation
        
        # Count files
        total_files = 0
        valid_files = 0
        critical_missing = []
        
        for phase_data in validation.values():
            for file_info in phase_data.get("files", []):
                total_files += 1
                if file_info.get("exists"):
                    valid_files += 1
                elif file_info.get("priority") == "CRITICAL":
                    critical_missing.append(file_info.get("name"))
        
        result["files_total"] = total_files
        result["files_valid"] = valid_files
        result["critical_missing"] = critical_missing
        
        # Preload data
        preload_config = context.get("preload_config", {})
        cache_on_startup_value = preload_config.get("cache_on_startup")

        # Support both boolean and list forms for cache_on_startup.
        # - If it's a list, a non-empty list enables preloading; an empty list disables it.
        # - If it's a boolean, use it directly.
        # - For any other type, fall back to standard truthiness.
        if isinstance(cache_on_startup_value, list):
            should_preload = bool(cache_on_startup_value)
            # Surface the requested keys for visibility, even if the underlying
            # preload implementation currently loads a fixed set.
            result["requested_preload_keys"] = cache_on_startup_value
        elif isinstance(cache_on_startup_value, bool):
            should_preload = cache_on_startup_value
        else:
            should_preload = bool(cache_on_startup_value)

        if should_preload:
            preload_status = self.preload_critical_data()
            result["preload_status"] = preload_status
        
        # Generate visibility report
        if show_report and preload_config.get("show_visibility_report", True):
            result["visibility_report"] = self.generate_visibility_report(language)
        
        return result


def auto_initialize(root_path: Optional[Path] = None, language: str = "es") -> Dict:
    """
    Convenience function to automatically initialize Panelin GPT system.
    
    This function is designed to be called automatically on first user interaction
    without requiring any user validation.
    
    Args:
        root_path: Root path for knowledge base files. If None, uses current directory.
        language: Language for reports ('es' or 'en')
    
    Returns:
        Dictionary with initialization results and visibility report.
    """
    preload = PanelinPreloadSystem(root_path)
    return preload.initialize(show_report=True, language=language)


def get_system_status(root_path: Optional[Path] = None) -> Dict:
    """
    Get current system status without full initialization.
    
    Args:
        root_path: Root path for knowledge base files.
    
    Returns:
        Dictionary with system status information.
    """
    preload = PanelinPreloadSystem(root_path)
    preload.load_startup_context()
    validation = preload.verify_required_files()
    
    total_files = sum(len(p.get("files", [])) for p in validation.values())
    valid_files = sum(
        1 for p in validation.values() 
        for f in p.get("files", []) 
        if f.get("exists")
    )
    
    return {
        "system_ready": valid_files == total_files,
        "files_total": total_files,
        "files_valid": valid_files,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    """
    Command-line interface for testing the preload system.
    """
    print("=" * 70)
    print("Panelin GPT Automatic Preload System - Test Mode")
    print("=" * 70)
    print()
    
    # Initialize system
    result = auto_initialize(language="es")
    
    # Print status
    print(f"Status: {result.get('status')}")
    print(f"System: {result.get('system_info', {}).get('name')} v{result.get('system_info', {}).get('version')}")
    print(f"KB Version: {result.get('system_info', {}).get('kb_version')}")
    print(f"Files: {result.get('files_valid')}/{result.get('files_total')} validated")
    
    if result.get('critical_missing'):
        print(f"⚠️  Critical files missing: {', '.join(result['critical_missing'])}")
    else:
        print("✅ All critical files available")
    
    print()
    print("-" * 70)
    print("VISIBILITY REPORT:")
    print("-" * 70)
    print()
    
    # Print visibility report
    if "visibility_report" in result:
        print(result["visibility_report"])
    
    # Exit with appropriate code
    if result.get("status") == "initialized" and not result.get('critical_missing'):
        sys.exit(0)
    else:
        sys.exit(1)
