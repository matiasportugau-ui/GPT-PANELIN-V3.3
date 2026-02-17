#!/usr/bin/env python3
"""
GPT Configuration Files Exporter

Reads Panelin_GPT_config.json as the single source of truth, collects every
referenced GPT configuration and knowledge-base file, and exports them into
an organized ZIP package ready for upload to OpenAI GPT Builder.

Usage:
    python3 export_gpt_config.py              # export to gpt_config_export/
    python3 export_gpt_config.py -o /tmp/out  # custom output directory

The script is fully non-interactive and uses only the Python standard library.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = "Panelin_GPT_config.json"

# Mapping from knowledge_base.hierarchy keys → upload phase number + label.
# Order matters: it determines which phase a file falls into when it appears
# in multiple hierarchy levels (first match wins).
HIERARCHY_TO_PHASE: List[Tuple[List[str], int, str, str]] = [
    # (hierarchy key prefixes, phase#, phase dir name, description)
    (
        ["level_1_master", "level_1_2", "level_1_3"],
        1,
        "Phase_1_Master_KB",
        "Master Knowledge Base – UPLOAD FIRST",
    ),
    (
        ["level_1_5", "level_1_6"],
        2,
        "Phase_2_Optimized_Lookups",
        "Optimized Lookups & Catalogs",
    ),
    (
        ["level_2", "level_3"],
        3,
        "Phase_3_Validation",
        "Validation & Dynamic Data",
    ),
    (
        ["level_4"],
        4,
        "Phase_4_Documentation",
        "Documentation & Guides",
    ),
]

PHASE_5_DIR = "Phase_5_Supporting"
PHASE_5_DESC = "Supporting Files"

PHASE_6_DIR = "Phase_6_Assets"
PHASE_6_DESC = "Assets & Branding"

# Files that are always required regardless of config references.
ALWAYS_REQUIRED: List[str] = [
    CONFIG_FILENAME,
    "Instrucciones GPT.rtf",
    "Esquema json.rtf",
    "bmc_logo.png",
]

# Files that belong in Phase 6 (assets).
ASSET_FILES: Set[str] = {"bmc_logo.png"}

# Pause instructions per phase (minutes).
PAUSE_AFTER: Dict[int, str] = {
    1: "2-3 minutes (CRITICAL — let GPT reindex master KB)",
    2: "2 minutes",
    3: "2 minutes",
    4: "2 minutes",
    5: "2 minutes",
    6: "Done!",
}

DEFAULT_OUTPUT_DIR = "gpt_config_export"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Return hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def load_config(repo_root: Path) -> Dict[str, Any]:
    """Load and return Panelin_GPT_config.json."""
    config_path = repo_root / CONFIG_FILENAME
    if not config_path.exists():
        print(f"❌  Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_files_from_config(config: Dict[str, Any]) -> Dict[int, List[str]]:
    """
    Derive the complete, deduplicated file list from the config and organise
    it into upload phases.

    Returns {phase_number: [filename, ...]} with phases 1-6.
    """
    hierarchy: Dict[str, List[str]] = (
        config.get("knowledge_base", {}).get("hierarchy", {})
    )
    deploy_files: List[str] = config.get("deployment", {}).get("files_to_upload", [])

    # --- Step 1: map hierarchy levels → phases ---
    assigned: Set[str] = set()
    phases: Dict[int, List[str]] = {i: [] for i in range(1, 7)}

    for prefixes, phase_num, _dir, _desc in HIERARCHY_TO_PHASE:
        for key, files in hierarchy.items():
            if not isinstance(files, list):
                continue
            if any(key.startswith(p) for p in prefixes):
                for fname in files:
                    if fname not in assigned:
                        phases[phase_num].append(fname)
                        assigned.add(fname)

    # --- Step 2: add deployment.files_to_upload extras to Phase 4 (docs) ---
    for fname in deploy_files:
        if fname not in assigned:
            phases[4].append(fname)
            assigned.add(fname)

    # --- Step 3: always-required extras ---
    for fname in ALWAYS_REQUIRED:
        if fname in assigned:
            continue
        if fname in ASSET_FILES:
            phases[6].append(fname)
        else:
            phases[5].append(fname)
        assigned.add(fname)

    # --- Step 4: ensure assets are in Phase 6, not elsewhere ---
    for phase_num in list(phases.keys()):
        for fname in list(phases[phase_num]):
            if fname in ASSET_FILES and phase_num != 6:
                phases[phase_num].remove(fname)
                if fname not in phases[6]:
                    phases[6].append(fname)

    return phases


def phase_dirname(phase_num: int) -> str:
    """Return the directory name for a given upload phase."""
    mapping = {entry[1]: entry[2] for entry in HIERARCHY_TO_PHASE}
    mapping[5] = PHASE_5_DIR
    mapping[6] = PHASE_6_DIR
    return mapping.get(phase_num, f"Phase_{phase_num}")


def phase_description(phase_num: int) -> str:
    """Return the description for a given upload phase."""
    mapping = {entry[1]: entry[3] for entry in HIERARCHY_TO_PHASE}
    mapping[5] = PHASE_5_DESC
    mapping[6] = PHASE_6_DESC
    return mapping.get(phase_num, "")


def validate_and_hash(
    repo_root: Path, phases: Dict[int, List[str]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate that every referenced file exists, compute sizes and hashes.

    Returns (file_records, missing_files).
    """
    records: List[Dict[str, Any]] = []
    missing: List[str] = []

    for phase_num in sorted(phases):
        for fname in phases[phase_num]:
            fpath = repo_root / fname
            if not fpath.exists():
                missing.append(fname)
                records.append(
                    {
                        "filename": fname,
                        "phase": phase_num,
                        "phase_dir": phase_dirname(phase_num),
                        "exists": False,
                    }
                )
            else:
                size = fpath.stat().st_size
                records.append(
                    {
                        "filename": fname,
                        "phase": phase_num,
                        "phase_dir": phase_dirname(phase_num),
                        "exists": True,
                        "size_bytes": size,
                        "size_readable": format_size(size),
                        "sha256": sha256_file(fpath),
                    }
                )

    return records, missing


def build_manifest(
    config: Dict[str, Any],
    records: List[Dict[str, Any]],
    missing: List[str],
) -> Dict[str, Any]:
    """Build the MANIFEST.json content."""
    present = [r for r in records if r["exists"]]
    total_size = sum(r["size_bytes"] for r in present)

    return {
        "package": "Panelin GPT Configuration Export",
        "gpt_name": config.get("name", ""),
        "gpt_version": config.get("instructions_version", ""),
        "kb_version": config.get("knowledge_base", {}).get("version", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(present),
        "total_size_bytes": total_size,
        "total_size_readable": format_size(total_size),
        "all_files_present": len(missing) == 0,
        "missing_count": len(missing),
        "missing_files": missing,
        "files": [
            {
                "filename": r["filename"],
                "phase": r["phase"],
                "phase_dir": r["phase_dir"],
                "size_bytes": r["size_bytes"],
                "size_readable": r["size_readable"],
                "sha256": r["sha256"],
            }
            for r in present
        ],
    }


def build_readme(
    config: Dict[str, Any],
    phases: Dict[int, List[str]],
    records: List[Dict[str, Any]],
    missing: List[str],
) -> str:
    """Build the README.txt included in the export."""
    present = [r for r in records if r["exists"]]
    total_size = sum(r["size_bytes"] for r in present)
    rec_by_name = {r["filename"]: r for r in records}

    lines = [
        "=" * 78,
        "PANELIN GPT CONFIGURATION EXPORT",
        f"  {config.get('name', 'Panelin - BMC Assistant Pro')}",
        "=" * 78,
        "",
        f"Generated : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Files     : {len(present)}",
        f"Total size: {format_size(total_size)}",
        "",
        "=" * 78,
        "UPLOAD INSTRUCTIONS",
        "=" * 78,
        "",
        "1. Open OpenAI GPT Builder:  https://chat.openai.com/gpts/editor",
        "2. Create a new GPT (or edit an existing one).",
        "3. Configure:",
        f"   - Name: {config.get('name', '')}",
        "   - Description: copy from Panelin_GPT_config.json",
        "   - Instructions: copy from Panelin_GPT_config.json",
        "4. Enable capabilities: Web Browsing, Code Interpreter, Image Generation.",
        "5. Upload knowledge-base files IN PHASE ORDER (see below).",
        "6. Save & test the GPT.",
        "",
        "=" * 78,
        "FILE UPLOAD SEQUENCE",
        "=" * 78,
    ]

    for phase_num in sorted(phases):
        files = phases[phase_num]
        if not files:
            continue
        dirname = phase_dirname(phase_num)
        desc = phase_description(phase_num)
        pause = PAUSE_AFTER.get(phase_num, "")

        lines.append("")
        lines.append(f"--- Phase {phase_num}: {desc} ---")
        lines.append(f"    Directory: {dirname}/")
        lines.append("")

        for fname in files:
            rec = rec_by_name.get(fname, {})
            if rec.get("exists"):
                size = rec.get("size_readable", "")
                lines.append(f"  ✅  {fname}  ({size})")
            else:
                lines.append(f"  ❌  {fname}  (MISSING)")

        lines.append("")
        lines.append(f"  ⏱️  After this phase: pause {pause}")

    if missing:
        lines.extend(
            [
                "",
                "=" * 78,
                "⚠️  MISSING FILES",
                "=" * 78,
                "",
            ]
        )
        for fname in missing:
            lines.append(f"  ❌  {fname}")
        lines.append("")
        lines.append("Locate these files before uploading to OpenAI.")

    lines.extend(
        [
            "",
            "=" * 78,
            "VERIFICATION",
            "=" * 78,
            "",
            "After uploading, test the GPT with:",
            '  - "¿Cuánto cuesta ISODEC 100mm?"',
            '  - "¿Cuánto cuesta un gotero frontal?"',
            '  - "Genera un PDF para cotización de ISODEC 100mm"',
            "",
            "=" * 78,
            "SUPPORT",
            "=" * 78,
            "",
            "Repository : https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3",
            "Checklist  : GPT_UPLOAD_CHECKLIST.md",
            "Deployment : DEPLOYMENT_CONFIG.md",
            "",
            "=" * 78,
        ]
    )

    return "\n".join(lines) + "\n"


def create_export(
    repo_root: Path,
    output_dir: Path,
    config: Dict[str, Any],
    phases: Dict[int, List[str]],
    records: List[Dict[str, Any]],
    missing: List[str],
) -> Optional[Path]:
    """
    Create the export directory tree and ZIP archive.

    Returns the path to the generated ZIP, or None on failure.
    """
    # Clean previous export
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Copy files into phase subdirectories
    for phase_num in sorted(phases):
        pdir = output_dir / phase_dirname(phase_num)
        pdir.mkdir(exist_ok=True)
        for fname in phases[phase_num]:
            src = repo_root / fname
            if src.exists():
                shutil.copy2(src, pdir / Path(fname).name)

    # Write MANIFEST.json
    manifest = build_manifest(config, records, missing)
    manifest_path = output_dir / "MANIFEST.json"
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Write README.txt
    readme = build_readme(config, phases, records, missing)
    readme_path = output_dir / "README.txt"
    with open(readme_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(readme)

    # Create ZIP
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"Panelin_GPT_Config_Export_{timestamp}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add README and manifest at the root of the ZIP
        zf.write(readme_path, "README.txt")
        zf.write(manifest_path, "MANIFEST.json")

        # Add phase directories
        for phase_num in sorted(phases):
            pdir_name = phase_dirname(phase_num)
            pdir = output_dir / pdir_name
            if pdir.exists():
                for item in sorted(pdir.iterdir()):
                    if item.is_file():
                        zf.write(item, f"{pdir_name}/{item.name}")

    return zip_path


# ---------------------------------------------------------------------------
# CLI & main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export all GPT configuration files into an organized ZIP package."
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--config",
        default=CONFIG_FILENAME,
        help=f"Path to GPT config JSON (default: {CONFIG_FILENAME})",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).parent.resolve()
    output_dir = (repo_root / args.output).resolve()

    # Ensure output stays inside repo
    try:
        output_dir.relative_to(repo_root)
    except ValueError:
        print(
            f"❌  Output directory must be inside the repository root: {repo_root}",
            file=sys.stderr,
        )
        return 1

    # --- Load config ---
    print()
    print("=" * 60)
    print("  GPT Configuration Files Exporter")
    print("=" * 60)
    print()

    config_path = repo_root / args.config
    if not config_path.exists():
        print(f"❌  Config not found: {config_path}", file=sys.stderr)
        return 1

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    print(f"📄  Config     : {config_path.name}")
    print(f"📦  GPT name   : {config.get('name', '?')}")
    print(f"📋  KB version : {config.get('knowledge_base', {}).get('version', '?')}")
    print()

    # --- Collect & validate ---
    phases = collect_files_from_config(config)
    records, missing = validate_and_hash(repo_root, phases)
    present = [r for r in records if r["exists"]]
    total_size = sum(r["size_bytes"] for r in present)

    print(f"🔍  Files found : {len(present)}")
    print(f"📏  Total size  : {format_size(total_size)}")

    if missing:
        print(f"⚠️   Missing     : {len(missing)}")
        for fname in missing:
            print(f"     ❌  {fname}")
    else:
        print("✅  All files present")
    print()

    # --- Build export ---
    print(f"📂  Exporting to: {output_dir}")
    zip_path = create_export(repo_root, output_dir, config, phases, records, missing)

    if zip_path is None:
        print("❌  Export failed", file=sys.stderr)
        return 1

    # --- Summary ---
    print()
    for phase_num in sorted(phases):
        files = phases[phase_num]
        if not files:
            continue
        dirname = phase_dirname(phase_num)
        desc = phase_description(phase_num)
        print(f"  Phase {phase_num}: {desc}")
        for fname in files:
            rec = {r["filename"]: r for r in records}.get(fname, {})
            if rec.get("exists"):
                print(f"    ✅  {fname} ({rec.get('size_readable', '')})")
            else:
                print(f"    ❌  {fname} (MISSING)")
        print()

    print("=" * 60)
    print(f"✅  ZIP created: {zip_path.name}")
    print(f"    Size: {format_size(zip_path.stat().st_size)}")
    print(f"    Path: {zip_path}")
    print("=" * 60)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
