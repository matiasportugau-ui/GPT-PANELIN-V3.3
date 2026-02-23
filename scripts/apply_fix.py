#!/usr/bin/env python3
# EXPORT_SEAL
"""
apply_fix.py
Edits deploy_gpt_assistant.py to add a compat helper _get_vector_stores_api()
and replace direct uses of self.client.beta.vector_stores with a robust
compat implementation.

Uso: python3 scripts/apply_fix.py [--file PATH] [--dry-run]
"""
from pathlib import Path
import argparse
import sys

HELPER = '''
    # EXPORT_SEAL
    def _get_vector_stores_api(self):
        """
        Compat layer for different OpenAI Python SDK shapes:
        - prefer: self.client.beta.vector_stores
        - fallback: self.client.vector_stores
        Raises AttributeError if none available with a helpful message.
        """
        beta = getattr(self.client, "beta", None)
        if beta is not None:
            vs = getattr(beta, "vector_stores", None) or getattr(beta, "vectorStore", None)
            if vs is not None:
                return vs

        vs = getattr(self.client, "vector_stores", None) or getattr(self.client, "vectorStore", None)
        if vs is not None:
            return vs

        raise AttributeError(
            "OpenAI client does not expose a vector_stores API (tried beta.vector_stores and vector_stores). "
            "Please upgrade the openai Python package in this environment (e.g. `pip install --upgrade openai`) "
            "or verify which OpenAI client you are using."
        )
'''.rstrip("\n")

REPLACE_BLOCK_CREATE = '''
        # Create new vector store using compatibility helper
        vs_api = self._get_vector_stores_api()
        vs = vs_api.create(name=f"Panelin KB v{kb_version}", file_ids=all_file_ids)
        vs_id = getattr(vs, "id", None) or (vs.get("id") if isinstance(vs, dict) else None)
        print(f"  Created vector store: {vs_id}")

        # Wait for processing
        self._wait_for_vector_store_ready(vs_id)
'''.lstrip("\n")

REPLACE_METHOD_WAIT = '''
    def _wait_for_vector_store_ready(self, vs_id: str, timeout: int = 300) -> None:
        """Poll vector store until all files are processed."""
        print("  Waiting for vector store processing...", end="", flush=True)
        vs_api = self._get_vector_stores_api()
        import time
        start = time.time()
        while time.time() - start < timeout:
            vs = vs_api.retrieve(vs_id)
            # support both attribute-based and dict-based responses
            counts = getattr(vs, "file_counts", None) or (vs.get("file_counts") if isinstance(vs, dict) else None)
            if counts is None:
                print("\\n  WARNING: vector store response missing 'file_counts'; continuing without detailed checks.")
                return

            completed = getattr(counts, "completed", None) or (counts.get("completed") if isinstance(counts, dict) else 0)
            failed = getattr(counts, "failed", None) or (counts.get("failed") if isinstance(counts, dict) else 0)
            cancelled = getattr(counts, "cancelled", None) or (counts.get("cancelled") if isinstance(counts, dict) else 0)
            in_progress = getattr(counts, "in_progress", None) or (counts.get("in_progress") if isinstance(counts, dict) else 0)

            total = (completed or 0) + (failed or 0) + (cancelled or 0) + (in_progress or 0)
            if (in_progress or 0) == 0 and total > 0:
                print(f" done ({completed} ready, {failed} failed)")
                if failed and int(failed) > 0:
                    print(f"  WARNING: {failed} files failed processing")
                return

            print(".", end="", flush=True)
            time.sleep(3)
        raise TimeoutError(f"Vector store {vs_id} processing timed out after {timeout}s")
'''.rstrip("\n")

def apply_patch(text: str) -> str:
    # 1) Insert helper before def create_or_update_vector_store
    anchor = "\n    def create_or_update_vector_store"
    if "_get_vector_stores_api" in text:
        raise RuntimeError("Archivo ya contiene _get_vector_stores_api. Abortando para no duplicar.")
    text = text.replace(anchor, "\n" + HELPER + "\n\n    def create_or_update_vector_store")

    # 2) Replace the block that creates vector store
    import re
    pattern_create = re.compile(r"# Create new vector store[\\s\\S]*?self\\._wait_for_vector_store_ready\\(vs.id\\)\\n", re.MULTILINE)
    if not pattern_create.search(text):
        raise RuntimeError("No pude encontrar el bloque exacto de creación de vector store para reemplazar.")
    text = pattern_create.sub(REPLACE_BLOCK_CREATE + "\n", text, count=1)

    # 3) Replace entire _wait_for_vector_store_ready method
    start_marker = "def _wait_for_vector_store_ready(self, vs_id: str, timeout: int = 300) -> None:"
    si = text.find(start_marker)
    if si == -1:
        raise RuntimeError("No encontré el método _wait_for_vector_store_ready para reemplazar.")
    # find the next '\n\n    def ' or end of file
    ni = text.find("\n\n    def ", si)
    if ni == -1:
        ni = len(text)
    text = text[:si] + REPLACE_METHOD_WAIT + text[ni:]
    return text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="deploy_gpt_assistant.py", help="path to deploy_gpt_assistant.py")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    p = Path(args.file)
    if not p.exists():
        print(f"ERROR: file not found: {p}", file=sys.stderr)
        sys.exit(2)

    original = p.read_text(encoding="utf-8")
    try:
        patched = apply_patch(original)
    except Exception as e:
        print("ERROR during patch:", e, file=sys.stderr)
        sys.exit(3)

    if args.dry_run:
        print("Dry-run: patch would be applied. Exiting.")
        sys.exit(0)

    p.write_text(patched, encoding="utf-8")
    print(f"Patched {p} successfully.")

if __name__ == "__main__":
    main()
