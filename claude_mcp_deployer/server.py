#!/usr/bin/env python3
"""
Claude MCP Server for Panelin GPT Deployment
Enables automatic GPT deployment when Claude Desktop is opened
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Repository root
REPO_ROOT = Path(__file__).parent.parent.resolve()
DEPLOY_PACKAGE_DIR = REPO_ROOT / "GPT_Deploy_Package"

# Create server instance
server = Server("panelin-gpt-deployer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available deployment tools"""
    return [
        Tool(
            name="check_deployment_status",
            description="Check if GPT configuration is ready for deployment",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="generate_gpt_config",
            description="Generate GPT configuration package using autoconfig_gpt.py",
            inputSchema={
                "type": "object",
                "properties": {
                    "auto_approve": {
                        "type": "boolean",
                        "description": "Automatically approve configuration (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_deployment_guide",
            description="Get the deployment guide with step-by-step instructions",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_github_actions_status",
            description="Check if GitHub Actions has generated a configuration package",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_files_to_upload",
            description="List all files that need to be uploaded in phase order",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_openai_config",
            description="Get the OpenAI-compatible configuration JSON",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "check_deployment_status":
        return await check_deployment_status()
    
    elif name == "generate_gpt_config":
        auto_approve = arguments.get("auto_approve", True)
        return await generate_gpt_config(auto_approve)
    
    elif name == "get_deployment_guide":
        return await get_deployment_guide()
    
    elif name == "get_github_actions_status":
        return await get_github_actions_status()
    
    elif name == "list_files_to_upload":
        return await list_files_to_upload()
    
    elif name == "get_openai_config":
        return await get_openai_config()
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def check_deployment_status() -> list[TextContent]:
    """Check if configuration package is ready"""
    if DEPLOY_PACKAGE_DIR.exists():
        files = list(DEPLOY_PACKAGE_DIR.glob("*"))
        file_list = "\n".join([f"  - {f.name}" for f in files])
        
        # Check for required files
        required = [
            "gpt_deployment_config.json",
            "openai_gpt_config.json",
            "DEPLOYMENT_GUIDE.md"
        ]
        
        missing = [f for f in required if not (DEPLOY_PACKAGE_DIR / f).exists()]
        
        if missing:
            status = "⚠️  Package incomplete"
            details = f"Missing files: {', '.join(missing)}"
        else:
            status = "✅ Package ready for deployment"
            details = f"Found {len(files)} files"
        
        return [TextContent(
            type="text",
            text=f"""
{status}
{details}

Package location: {DEPLOY_PACKAGE_DIR}

Files in package:
{file_list}

Ready to deploy to OpenAI GPT Builder.
            """
        )]
    else:
        return [TextContent(
            type="text",
            text=f"""
❌ No deployment package found

Package directory does not exist: {DEPLOY_PACKAGE_DIR}

Please run 'generate_gpt_config' first or wait for GitHub Actions to complete.
            """
        )]


async def generate_gpt_config(auto_approve: bool = True) -> list[TextContent]:
    """Generate GPT configuration"""
    script_path = REPO_ROOT / "autoconfig_gpt.py"
    
    if not script_path.exists():
        return [TextContent(
            type="text",
            text=f"❌ Error: autoconfig_gpt.py not found at {script_path}"
        )]
    
    try:
        # Run autoconfig script
        if auto_approve:
            # Auto-approve by piping "yes" to the script
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(REPO_ROOT),
                text=True
            )
            stdout, stderr = process.communicate(input="yes\n")
        else:
            # Interactive mode
            process = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True
            )
            stdout = process.stdout
            stderr = process.stderr
        
        if process.returncode == 0 or (hasattr(process, 'returncode') and process.returncode == 0):
            return [TextContent(
                type="text",
                text=f"""
✅ GPT configuration generated successfully!

Output:
{stdout}

Package created at: {DEPLOY_PACKAGE_DIR}

Next step: Use Computer Use to deploy to OpenAI GPT Builder.
                """
            )]
        else:
            return [TextContent(
                type="text",
                text=f"""
❌ Error generating configuration

Exit code: {process.returncode}

Error output:
{stderr}

Output:
{stdout}
                """
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Exception: {str(e)}"
        )]


async def get_deployment_guide() -> list[TextContent]:
    """Get deployment guide"""
    guide_path = DEPLOY_PACKAGE_DIR / "DEPLOYMENT_GUIDE.md"
    
    if guide_path.exists():
        content = guide_path.read_text()
        return [TextContent(
            type="text",
            text=f"""
📄 Deployment Guide

{content}
            """
        )]
    else:
        # Return the comprehensive prompt from documentation
        doc_path = REPO_ROOT / "CLAUDE_COMPUTER_USE_AUTOMATION.md"
        if doc_path.exists():
            content = doc_path.read_text()
            # Extract the comprehensive prompt section
            if "Comprehensive Prompt Template" in content:
                start = content.find("Comprehensive Prompt Template")
                end = content.find("---", start + 100)
                if end > start:
                    prompt_section = content[start:end]
                    return [TextContent(
                        type="text",
                        text=f"📄 Deployment Instructions\n\n{prompt_section}"
                    )]
        
        return [TextContent(
            type="text",
            text="❌ Deployment guide not found. Run 'generate_gpt_config' first."
        )]


async def get_github_actions_status() -> list[TextContent]:
    """Check GitHub Actions status"""
    # This would require GitHub API access
    # For now, just check if package exists
    return await check_deployment_status()


async def list_files_to_upload() -> list[TextContent]:
    """List files in upload order"""
    
    upload_sequence = {
        "Phase 1 - Master Knowledge Base [CRITICAL]": [
            "BMC_Base_Conocimiento_GPT-2.json",
            "bromyros_pricing_master.json",
            "accessories_catalog.json",
            "bom_rules.json"
        ],
        "Phase 2 - Optimized Lookups [CRITICAL]": [
            "bromyros_pricing_gpt_optimized.json",
            "shopify_catalog_v1.json",
            "shopify_catalog_index_v1.csv"
        ],
        "Phase 3 - Validation": [
            "BMC_Base_Unificada_v4.json",
            "panelin_truth_bmcuruguay_web_only_v2.json"
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
            "README.md"
        ],
        "Phase 5 - Supporting Files": [
            "Instrucciones GPT.rtf",
            "Panelin_GPT_config.json"
        ],
        "Phase 6 - Assets": [
            "bmc_logo.png"
        ]
    }
    
    output = ["📂 File Upload Sequence", ""]
    
    for phase, files in upload_sequence.items():
        output.append(f"\n{phase}")
        output.append(f"Files: {len(files)}")
        for f in files:
            exists = (REPO_ROOT / f).exists()
            status = "✅" if exists else "❌"
            output.append(f"  {status} {f}")
        
        # Add pause instructions
        if "Phase 1" in phase:
            output.append("\n⏱️  PAUSE 2-3 MINUTES after uploading Phase 1")
        elif "Phase 6" not in phase:
            output.append("\n⏱️  PAUSE 2 MINUTES after uploading this phase")
    
    return [TextContent(
        type="text",
        text="\n".join(output)
    )]


async def get_openai_config() -> list[TextContent]:
    """Get OpenAI configuration"""
    config_path = DEPLOY_PACKAGE_DIR / "openai_gpt_config.json"
    
    if config_path.exists():
        content = config_path.read_text()
        config = json.loads(content)
        
        return [TextContent(
            type="text",
            text=f"""
📋 OpenAI GPT Configuration

Name: {config.get('name', 'N/A')}

Description:
{config.get('description', 'N/A')}

Capabilities:
{json.dumps(config.get('capabilities', {}), indent=2)}

Conversation Starters:
{json.dumps(config.get('conversation_starters', []), indent=2)}

Instructions: (see full JSON below)

Full Configuration:
```json
{json.dumps(config, indent=2)}
```
            """
        )]
    else:
        return [TextContent(
            type="text",
            text="❌ Configuration not found. Run 'generate_gpt_config' first."
        )]


async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
