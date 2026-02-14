#!/usr/bin/env python3
"""MCP Server deployment and health check script.

This script:
1. Validates the server configuration
2. Checks all dependencies
3. Runs health checks on handlers
4. Can start the server in different modes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_dependencies() -> bool:
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        ('mcp', 'Model Context Protocol SDK'),
        ('uvicorn', 'ASGI server'),
        ('starlette', 'Web framework'),
        ('httpx', 'HTTP client'),
        ('pydantic', 'Data validation')
    ]
    
    missing = []
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {name} ({package})")
        except ImportError:
            print(f"  ✗ {name} ({package}) - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print(f"   Run: pip install {' '.join(missing)}")
        return False
    
    print("✅ All dependencies installed\n")
    return True


def check_kb_files() -> bool:
    """Check if all KB files exist."""
    print("📚 Checking Knowledge Base files...")
    
    kb_root = Path(__file__).parent.parent.parent
    kb_files = [
        'bromyros_pricing_master.json',
        'accessories_catalog.json',
        'bom_rules.json',
        'corrections_log.json'
    ]
    
    missing = []
    for kb_file in kb_files:
        path = kb_root / kb_file
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  ✓ {kb_file} ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ {kb_file} - MISSING")
            missing.append(kb_file)
    
    if missing:
        print(f"\n❌ Missing KB files: {', '.join(missing)}")
        return False
    
    print("✅ All KB files present\n")
    return True


def check_tool_schemas() -> bool:
    """Check if all tool schemas are valid."""
    print("🔧 Checking tool schemas...")
    
    tools_dir = Path(__file__).parent / 'tools'
    expected_tools = ['price_check', 'catalog_search', 'bom_calculate', 'report_error']
    
    missing = []
    invalid = []
    
    for tool_name in expected_tools:
        schema_path = tools_dir / f"{tool_name}.json"
        if not schema_path.exists():
            print(f"  ✗ {tool_name}.json - MISSING")
            missing.append(tool_name)
            continue
        
        try:
            with open(schema_path) as f:
                schema = json.load(f)
            
            # Validate basic structure
            required_keys = ['name', 'description', 'parameters']
            if all(k in schema for k in required_keys):
                print(f"  ✓ {tool_name}.json")
            else:
                print(f"  ⚠️  {tool_name}.json - Missing keys")
                invalid.append(tool_name)
        
        except json.JSONDecodeError:
            print(f"  ✗ {tool_name}.json - INVALID JSON")
            invalid.append(tool_name)
    
    if missing or invalid:
        print(f"\n❌ Tool schema issues found")
        return False
    
    print("✅ All tool schemas valid\n")
    return True


async def health_check_handlers() -> bool:
    """Run health checks on all handlers."""
    print("🏥 Running handler health checks...")
    
    from mcp.handlers.pricing import handle_price_check
    from mcp.handlers.catalog import handle_catalog_search
    from mcp.handlers.bom import handle_bom_calculate
    from mcp.handlers.errors import handle_report_error
    
    handlers = [
        ('price_check', handle_price_check, {'query': 'test'}),
        ('catalog_search', handle_catalog_search, {'query': 'panel'}),
        ('bom_calculate', handle_bom_calculate, {'product_family': 'ISOROOF', 'thickness_mm': 50, 'usage': 'techo', 'length_m': 10, 'width_m': 5}),
        ('report_error', handle_report_error, {'kb_file': 'test.json', 'field': 'test', 'wrong_value': '1', 'correct_value': '2', 'source': 'validation_check'})
    ]
    
    all_ok = True
    for name, handler, args in handlers:
        try:
            result = await handler(args)
            
            # Check v1 contract compliance
            if 'ok' in result and 'contract_version' in result:
                status = "✓" if result['ok'] else "✓ (expected error)"
                print(f"  {status} {name}")
            else:
                print(f"  ✗ {name} - Invalid response format")
                all_ok = False
        
        except Exception as e:
            print(f"  ✗ {name} - Exception: {e}")
            all_ok = False
    
    if all_ok:
        print("✅ All handlers healthy\n")
    else:
        print("❌ Some handlers failed health check\n")
    
    return all_ok


def start_server(transport: str = 'stdio', port: int = 8000):
    """Start the MCP server."""
    print(f"🚀 Starting MCP server ({transport} transport)...")
    
    if transport == 'stdio':
        print("   Running in stdio mode (for local testing / OpenAI Custom GPT)")
        print("   Use Ctrl+C to stop\n")
        import subprocess
        subprocess.run([sys.executable, '-m', 'mcp.server'], cwd=Path(__file__).parent.parent)
    
    elif transport == 'sse':
        print(f"   Running in SSE mode on port {port}")
        print(f"   Server URL: http://localhost:{port}")
        print("   Use Ctrl+C to stop\n")
        import subprocess
        subprocess.run([
            sys.executable, '-m', 'mcp.server',
            '--transport', 'sse',
            '--port', str(port)
        ], cwd=Path(__file__).parent.parent)


async def main():
    parser = argparse.ArgumentParser(description='MCP Server deployment and health check')
    parser.add_argument('command', choices=['check', 'start', 'test'], 
                       help='Command to run: check (validate setup), start (run server), test (run health checks)')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio',
                       help='Transport mode for start command')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port for SSE transport')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MCP SERVER DEPLOYMENT & HEALTH CHECK")
    print("=" * 60)
    print()
    
    if args.command == 'check':
        # Run all checks
        deps_ok = check_dependencies()
        kb_ok = check_kb_files()
        schemas_ok = check_tool_schemas()
        
        if deps_ok and kb_ok and schemas_ok:
            print("✅ All checks passed! Server is ready to deploy.")
            return 0
        else:
            print("❌ Some checks failed. Please fix the issues above.")
            return 1
    
    elif args.command == 'test':
        # Run health checks
        handlers_ok = await health_check_handlers()
        
        if handlers_ok:
            print("✅ All handler tests passed!")
            return 0
        else:
            print("❌ Some handler tests failed.")
            return 1
    
    elif args.command == 'start':
        # Run checks first
        deps_ok = check_dependencies()
        kb_ok = check_kb_files()
        schemas_ok = check_tool_schemas()
        
        if not (deps_ok and kb_ok and schemas_ok):
            print("❌ Pre-flight checks failed. Cannot start server.")
            return 1
        
        # Start server
        start_server(args.transport, args.port)
        return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
