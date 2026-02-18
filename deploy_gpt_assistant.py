#!/usr/bin/env python3
"""
GPT Assistant Deployment Tool
Deploys Panelin GPT as an OpenAI Assistant via the Assistants API.
Reads Panelin_GPT_config.json as source of truth and creates/updates
the assistant with knowledge base files in a vector store.

Usage:
    python deploy_gpt_assistant.py [--dry-run] [--force] [--model gpt-4o] [--rollback]
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class AssistantDeployer:
    """Deploys Panelin GPT configuration as an OpenAI Assistant."""

    STATE_FILE = ".gpt_assistant_state.json"
    STATE_BACKUP = ".gpt_assistant_state.json.bak"
    CONFIG_FILE = "Panelin_GPT_config.json"

    # Assistants API capability mapping notes
    CAPABILITY_MAPPING = {
        "code_interpreter": {"supported": True, "tool_type": "code_interpreter"},
        "file_search": {"supported": True, "tool_type": "file_search"},
        "web_browsing": {"supported": False, "note": "Not available in Assistants API"},
        "image_generation": {"supported": False, "note": "Not available in Assistants API"},
        "canvas": {"supported": False, "note": "Not available in Assistants API"},
    }

    def __init__(
        self,
        repo_root: Path,
        api_key: str,
        dry_run: bool = False,
        model: str = "gpt-4o",
        force: bool = False,
    ):
        self.repo_root = repo_root
        self.api_key = api_key
        self.dry_run = dry_run
        self.model = model
        self.force = force
        self.config: Dict[str, Any] = {}
        self.client = None

    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            print("ERROR: openai package not installed. Run: pip install openai>=1.0.0", file=sys.stderr)
            sys.exit(1)

    def load_config(self) -> Dict[str, Any]:
        """Load the master GPT configuration."""
        config_path = self.repo_root / self.CONFIG_FILE
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        return self.config

    def compute_config_hash(self) -> str:
        """Compute SHA-256 hash of config fields that affect the assistant."""
        hash_input = json.dumps(
            {
                "instructions": self.config.get("instructions", ""),
                "name": self.config.get("name", ""),
                "description": self.config.get("description", ""),
                "capabilities": self.config.get("capabilities", {}),
                "actions": self.config.get("actions", []),
                "business_rules_v6": self.config.get("business_rules_v6", {}),
                "conversation_starters": self.config.get("conversation_starters", []),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    def compute_file_hashes(self) -> Dict[str, str]:
        """Compute SHA-256 hashes for all KB files to upload."""
        files_to_upload = self.config.get("deployment", {}).get("files_to_upload", [])
        hashes = {}
        for filename in files_to_upload:
            filepath = self.repo_root / filename
            if filepath.exists():
                sha = hashlib.sha256(filepath.read_bytes()).hexdigest()
                hashes[filename] = sha
        return hashes

    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load the deployment state file if it exists."""
        state_path = self.repo_root / self.STATE_FILE
        if not state_path.exists():
            return None
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("WARNING: State file corrupted, treating as first deployment")
            return None

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save the deployment state file."""
        state_path = self.repo_root / self.STATE_FILE
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def backup_state(self) -> None:
        """Backup current state file before deployment."""
        state_path = self.repo_root / self.STATE_FILE
        backup_path = self.repo_root / self.STATE_BACKUP
        if state_path.exists():
            shutil.copy2(state_path, backup_path)

    def _run_validation(self) -> int:
        """Run the existing file validation script."""
        validate_script = self.repo_root / "validate_gpt_files.py"
        if not validate_script.exists():
            print("WARNING: validate_gpt_files.py not found, skipping validation")
            return 0
        result = subprocess.run(
            [sys.executable, str(validate_script)],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        return result.returncode

    def map_config_to_assistant_params(self) -> Dict[str, Any]:
        """Map Panelin config to OpenAI Assistants API parameters."""
        config = self.config
        tools: List[Dict[str, Any]] = []

        # Code interpreter
        if config.get("capabilities", {}).get("code_interpreter"):
            tools.append({"type": "code_interpreter"})

        # File search (for knowledge base)
        tools.append({"type": "file_search"})

        # Wolf API actions as function-calling tools
        function_tools = self._map_actions_to_functions()
        tools.extend(function_tools)

        description = config.get("description", "")
        if len(description) > 512:
            description = description[:509] + "..."

        return {
            "name": config.get("name", "Panelin - BMC Assistant Pro"),
            "description": description,
            "instructions": config.get("instructions", ""),
            "model": self.model,
            "tools": tools,
            "metadata": {
                "config_version": config.get("instructions_version", "")[:512],
                "kb_version": config.get("knowledge_base", {}).get("version", ""),
                "panelin_version": config.get("metadata", {}).get("panelin_version", ""),
                "deployed_at": datetime.now(timezone.utc).isoformat(),
                "config_hash": self.compute_config_hash()[:64],
            },
        }

    def _map_actions_to_functions(self) -> List[Dict[str, Any]]:
        """Map Wolf API actions to Assistants API function-calling tools."""
        function_tools = []
        for action in self.config.get("actions", []):
            endpoint = action.get("endpoint")
            if not endpoint:
                continue  # Only map actions with explicit API endpoints

            properties = {}
            for param_name, param_def in action.get("parameters", {}).items():
                prop = {
                    "type": param_def.get("type", "string"),
                    "description": param_def.get("description", ""),
                }
                if "enum" in param_def:
                    prop["enum"] = param_def["enum"]
                # Convert array types to proper JSON schema
                if prop["type"] == "array":
                    prop["items"] = {"type": "string"}
                properties[param_name] = prop

            function_tools.append({
                "type": "function",
                "function": {
                    "name": action["name"],
                    "description": action.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": [],
                    },
                },
            })
        return function_tools

    def upload_files(self, current_state: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Upload KB files via the Files API, skipping unchanged files."""
        files_to_upload = self.config.get("deployment", {}).get("files_to_upload", [])
        new_hashes = self.compute_file_hashes()
        old_hashes = (current_state or {}).get("file_hashes", {})
        old_file_ids = (current_state or {}).get("file_ids", {})

        file_ids: Dict[str, str] = {}
        uploaded_count = 0
        skipped_count = 0
        failed_count = 0

        for filename in files_to_upload:
            filepath = self.repo_root / filename
            if not filepath.exists():
                print(f"  WARNING: {filename} not found, skipping")
                failed_count += 1
                continue

            # Skip upload if file hasn't changed and old ID exists
            if (
                not self.force
                and filename in old_hashes
                and old_hashes[filename] == new_hashes.get(filename)
                and filename in old_file_ids
            ):
                file_ids[filename] = old_file_ids[filename]
                print(f"  SKIP (unchanged): {filename}")
                skipped_count += 1
                continue

            if self.dry_run:
                file_ids[filename] = f"dry-run-{filename}"
                print(f"  DRY-RUN would upload: {filename}")
                uploaded_count += 1
                continue

            # Upload new file first
            try:
                with open(filepath, "rb") as f:
                    uploaded = self.client.files.create(file=f, purpose="assistants")
                file_ids[filename] = uploaded.id
                print(f"  UPLOADED: {filename} -> {uploaded.id}")
                uploaded_count += 1
            except Exception as e:
                print(f"  FAILED: {filename} - {e}")
                failed_count += 1

        print(f"\n  Summary: {uploaded_count} uploaded, {skipped_count} unchanged, {failed_count} failed")
        return file_ids

    def create_or_update_vector_store(
        self, file_ids: Dict[str, str], current_state: Optional[Dict[str, Any]]
    ) -> str:
        """Create or replace a vector store with the uploaded files."""
        all_file_ids = list(file_ids.values())
        old_vs_id = (current_state or {}).get("vector_store_id")
        kb_version = self.config.get("knowledge_base", {}).get("version", "?")

        if self.dry_run:
            print(f"  DRY-RUN would create vector store with {len(all_file_ids)} files")
            return old_vs_id or "dry-run-vs-id"

        if not all_file_ids:
            raise RuntimeError("No files to add to vector store")

        # Create new vector store
        vs = self.client.beta.vector_stores.create(
            name=f"Panelin KB v{kb_version}",
            file_ids=all_file_ids,
        )
        print(f"  Created vector store: {vs.id}")

        # Wait for processing
        self._wait_for_vector_store_ready(vs.id)

        # NOTE:
        # We intentionally do NOT delete the old vector store here.
        # Deleting it immediately after creating the new one is unsafe because
        # subsequent assistant update/verification steps may fail while
        # production still references the old vector store. In that case,
        # rollback would not be able to recover the deleted vector store.
        # Instead, the old vector store (if any) should be garbage-collected
        # explicitly after a successful deployment/verification step.
        if old_vs_id and old_vs_id != vs.id:
            print(
                f"  NOTE: Old vector store remains: {old_vs_id} "
                f"(eligible for cleanup after successful deployment)"
            )

        return vs.id

    def _wait_for_vector_store_ready(self, vs_id: str, timeout: int = 300) -> None:
        """Poll vector store until all files are processed."""
        print("  Waiting for vector store processing...", end="", flush=True)
        start = time.time()
        while time.time() - start < timeout:
            vs = self.client.beta.vector_stores.retrieve(vs_id)
            counts = vs.file_counts
            total = counts.completed + counts.failed + counts.cancelled + counts.in_progress
            if counts.in_progress == 0 and total > 0:
                print(f" done ({counts.completed} ready, {counts.failed} failed)")
                if counts.failed > 0:
                    print(f"  WARNING: {counts.failed} files failed processing")
                return
            print(".", end="", flush=True)
            time.sleep(3)
        raise TimeoutError(f"Vector store {vs_id} processing timed out after {timeout}s")

    def deploy_assistant(
        self, params: Dict[str, Any], vector_store_id: str, current_state: Optional[Dict[str, Any]]
    ) -> str:
        """Create or update the assistant. Returns assistant ID."""
        assistant_id = (current_state or {}).get("assistant_id")

        # Attach vector store
        params["tool_resources"] = {
            "file_search": {"vector_store_ids": [vector_store_id]},
        }

        if self.dry_run:
            action = "update" if assistant_id else "create"
            print(f"  DRY-RUN would {action} assistant")
            print(f"    Name: {params['name']}")
            print(f"    Model: {params['model']}")
            # Extract list comprehension with nested f-string to avoid E999 syntax error
            tools_list = [
                f"fn:{t.get('function', {}).get('name', '?')}" if t.get('type') == 'function' 
                else t.get('type', '?') 
                for t in params['tools']
            ]
            print(f"    Tools: {tools_list}")
            return assistant_id or "dry-run-assistant-id"

        if assistant_id:
            try:
                assistant = self.client.beta.assistants.update(
                    assistant_id=assistant_id, **params
                )
                print(f"  UPDATED assistant: {assistant.id}")
                return assistant.id
            except Exception as e:
                if "No assistant found" in str(e) or "not found" in str(e).lower():
                    print(f"  WARNING: Assistant {assistant_id} not found, creating new one")
                else:
                    raise

        # Create new assistant
        assistant = self.client.beta.assistants.create(**params)
        print(f"  CREATED assistant: {assistant.id}")
        return assistant.id

    def verify_deployment(self, assistant_id: str) -> bool:
        """Verify the deployed assistant matches expectations."""
        if self.dry_run:
            print("  DRY-RUN: Skipping verification")
            return True

        try:
            assistant = self.client.beta.assistants.retrieve(assistant_id)
        except Exception as e:
            print(f"  VERIFY FAILED: Could not retrieve assistant - {e}")
            return False

        checks = []

        # Check name
        expected_name = self.config.get("name", "Panelin - BMC Assistant Pro")
        if assistant.name == expected_name:
            checks.append(("Name", True, expected_name))
        else:
            checks.append(("Name", False, f"expected '{expected_name}', got '{assistant.name}'"))

        # Check model
        if assistant.model == self.model:
            checks.append(("Model", True, self.model))
        else:
            checks.append(("Model", False, f"expected '{self.model}', got '{assistant.model}'"))

        # Check tools include code_interpreter and file_search
        tool_types = [t.type for t in assistant.tools]
        capabilities = self.config.get("capabilities", {})
        code_interpreter_requested = bool(capabilities.get("code_interpreter"))

        if code_interpreter_requested:
            if "code_interpreter" in tool_types:
                checks.append(("Code Interpreter", True, "enabled"))
            else:
                checks.append(("Code Interpreter", False, "not found in tools"))
        else:
            # Code interpreter not requested in config; do not treat absence as a failure
            checks.append(("Code Interpreter", True, "not requested in config"))

        if "file_search" in tool_types:
            checks.append(("File Search", True, "enabled"))
        else:
            checks.append(("File Search", False, "not found in tools"))

        # Check vector store attachment
        vs_ids = []
        if assistant.tool_resources and assistant.tool_resources.file_search:
            vs_ids = assistant.tool_resources.file_search.vector_store_ids or []
        if vs_ids:
            checks.append(("Vector Store", True, vs_ids[0]))
        else:
            checks.append(("Vector Store", False, "no vector store attached"))

        # Print results
        all_passed = True
        for check_name, passed, detail in checks:
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check_name}: {detail}")
            if not passed:
                all_passed = False

        return all_passed

    def rollback(self) -> int:
        """Restore the previous deployment from backup state."""
        backup_path = self.repo_root / self.STATE_BACKUP
        if not backup_path.exists():
            print("ERROR: No backup state found (.gpt_assistant_state.json.bak)")
            return 1

        with open(backup_path, "r", encoding="utf-8") as f:
            old_state = json.load(f)

        print("Restoring from backup state...")
        print(f"  Assistant ID: {old_state.get('assistant_id', 'N/A')}")
        print(f"  Config version: {old_state.get('config_version', 'N/A')}")
        print(f"  Last deployed: {old_state.get('last_deployed', 'N/A')}")

        if self.dry_run:
            print("  DRY-RUN: Would restore above state")
            return 0

        self._init_client()

        # Re-read config to get the instructions from the old version
        # We can only restore the assistant params, not revert file contents
        # The rollback re-applies the state's metadata to the assistant
        assistant_id = old_state.get("assistant_id")
        if not assistant_id:
            print("ERROR: No assistant_id in backup state")
            return 1

        try:
            # Restore vector store attachment
            vs_id = old_state.get("vector_store_id")
            update_params: Dict[str, Any] = {}
            if vs_id:
                update_params["tool_resources"] = {
                    "file_search": {"vector_store_ids": [vs_id]},
                }

            self.client.beta.assistants.update(assistant_id, **update_params)
            print(f"  Restored assistant {assistant_id}")
        except Exception as e:
            print(f"  ERROR: Rollback failed - {e}")
            return 1

        # Restore state file
        self.save_state(old_state)
        print("  Rollback complete")
        return 0

    def _print_summary(self, state: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Print deployment summary."""
        print()
        print("=" * 70)
        print("DEPLOYMENT SUMMARY")
        print("=" * 70)
        print(f"  Assistant ID:    {state.get('assistant_id', 'N/A')}")
        print(f"  Vector Store ID: {state.get('vector_store_id', 'N/A')}")
        print(f"  Model:           {state.get('model', 'N/A')}")
        print(f"  Config Version:  {state.get('config_version', 'N/A')}")
        print(f"  KB Version:      {state.get('kb_version', 'N/A')}")
        print(f"  Files Uploaded:  {len(state.get('file_ids', {}))}")
        print(f"  Deployed At:     {state.get('last_deployed', 'N/A')}")
        if self.dry_run:
            print(f"  Mode:            DRY-RUN (no changes made)")
        print()

        # Print capability notes
        print("CAPABILITY MAPPING:")
        for cap, info in self.CAPABILITY_MAPPING.items():
            if info["supported"]:
                print(f"  [OK]   {cap}")
            else:
                print(f"  [N/A]  {cap} - {info['note']}")

        # Print unsupported features
        print()
        print("NOTE: Conversation starters are a Custom GPT UI feature")
        print("      and are not available in the Assistants API.")
        print()
        print("For Custom GPT deployment (manual), run:")
        print("  python autoconfig_gpt.py")
        print()

    def run(self) -> int:
        """Execute the full deployment flow."""
        try:
            print("=" * 70)
            print("GPT ASSISTANT DEPLOYMENT")
            print("Panelin - BMC Assistant Pro")
            print("=" * 70)
            print()

            # 1. Load config
            print("[1/8] Loading configuration...")
            self.load_config()
            print(f"  Loaded: {self.CONFIG_FILE}")
            print(f"  Version: {self.config.get('instructions_version', 'N/A')}")
            print()

            # 2. Validate files
            print("[2/8] Validating KB files...")
            validation_result = self._run_validation()
            if validation_result != 0:
                print("  WARNING: Validation found issues. Continuing anyway...")
            print()

            # 3. Initialize client
            if not self.dry_run:
                print("[3/8] Initializing OpenAI client...")
                self._init_client()
                print("  Client ready")
            else:
                print("[3/8] DRY-RUN mode - skipping client initialization")
            print()

            # 4. Load state and check for changes
            print("[4/8] Checking deployment state...")
            current_state = self.load_state()
            if current_state:
                print(f"  Previous deployment found: {current_state.get('last_deployed', 'unknown')}")
                print(f"  Assistant ID: {current_state.get('assistant_id', 'N/A')}")
            else:
                print("  No previous deployment found (first deployment)")

            if not self.force and current_state:
                current_hash = self.compute_config_hash()
                current_file_hashes = self.compute_file_hashes()
                if (
                    current_state.get("config_hash") == current_hash
                    and current_state.get("file_hashes") == current_file_hashes
                    and current_state.get("model") == self.model
                ):
                    print("  No changes detected. Use --force to deploy anyway.")
                    return 0
                else:
                    print("  Changes detected, proceeding with deployment")
            print()

            # Backup state before deployment
            self.backup_state()

            # 5. Map config to assistant params
            print("[5/8] Mapping configuration to Assistants API...")
            params = self.map_config_to_assistant_params()
            tool_summary = []
            for t in params["tools"]:
                if "type" in t and t["type"] != "function":
                    tool_summary.append(t["type"])
                elif t.get("type") == "function":
                    tool_summary.append(f"fn:{t['function']['name']}")
            print(f"  Tools: {', '.join(tool_summary)}")
            print()

            # 6. Upload files
            print("[6/8] Uploading KB files...")
            file_ids = self.upload_files(current_state)
            if not file_ids:
                print("  ERROR: No files were uploaded successfully")
                return 1
            print()

            # 7. Create/update vector store
            print("[7/8] Setting up vector store...")
            vector_store_id = self.create_or_update_vector_store(file_ids, current_state)
            print()

            # 8. Deploy assistant
            print("[8/8] Deploying assistant...")
            assistant_id = self.deploy_assistant(params, vector_store_id, current_state)
            print()

            # Verify
            print("Verifying deployment...")
            verified = self.verify_deployment(assistant_id)
            if not verified and not self.dry_run:
                print("ERROR: Deployment verification failed!")
                return 1
            print()

            # Save state
            new_state = {
                "assistant_id": assistant_id,
                "vector_store_id": vector_store_id,
                "file_ids": file_ids,
                "file_hashes": self.compute_file_hashes(),
                "config_hash": self.compute_config_hash(),
                "last_deployed": datetime.now(timezone.utc).isoformat(),
                "model": self.model,
                "config_version": self.config.get("instructions_version", ""),
                "kb_version": self.config.get("knowledge_base", {}).get("version", ""),
            }
            if not self.dry_run:
                self.save_state(new_state)

            self._print_summary(new_state, params)

            print("=" * 70)
            if self.dry_run:
                print("DRY-RUN COMPLETE - No changes were made")
            else:
                print("DEPLOYMENT COMPLETE")
            print("=" * 70)

            return 0

        except Exception as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Panelin GPT via OpenAI Assistants API"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making API calls",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force deployment even if no changes detected",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="OpenAI API key (default: OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback to previous deployment state",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")

    if not api_key and not args.dry_run:
        print("ERROR: OPENAI_API_KEY not set. Use --api-key or set the env var.", file=sys.stderr)
        print("       Use --dry-run to preview without an API key.", file=sys.stderr)
        sys.exit(1)

    repo_root = Path(__file__).parent.resolve()

    deployer = AssistantDeployer(
        repo_root=repo_root,
        api_key=api_key,
        dry_run=args.dry_run,
        model=args.model,
        force=args.force,
    )

    if args.rollback:
        sys.exit(deployer.rollback())
    else:
        sys.exit(deployer.run())


if __name__ == "__main__":
    main()
