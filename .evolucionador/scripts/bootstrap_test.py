#!/usr/bin/env python3
"""
Bootstrap validation script for CI:
- Verifies SHA1 checksums of panelin_reports files
- Runs panelin_reports/test_pdf_generation.py
- Writes results into .evolucionador/reports/bootstrap/
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path
import argparse
import time

EXPECTED = {
    "__init__.py": "e8238135f16a3674c02b318c4d6566c4ca0f417d",
    "pdf_styles.py": "bd22ecea67f69c1b1a14b0b7b739e32de1cae601",
    "pdf_generator.py": "1d0774196cafa25a5a3eb70012e6b73fa868cc24",
}

ROOT = Path(__file__).resolve().parents[2]
OUTDIR_DEFAULT = ROOT / ".evolucionador" / "reports" / "bootstrap"
TEST_TIMEOUT_SECONDS = 300  # 5 minutes for test execution


def sha1_of_file(p: Path):
    h = hashlib.sha1()
    with p.open("rb") as f:
        while True:
            b = f.read(8192)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def verify_checksums(out):
    results = []
    ok = True
    for fname, expected in EXPECTED.items():
        path = ROOT / "panelin_reports" / fname
        if not path.exists():
            results.append(f"- ❌ Missing file: {path}")
            ok = False
            continue
        actual = sha1_of_file(path)
        if actual != expected:
            results.append(f"- ⚠️ Checksum mismatch for {fname}: expected {expected}, actual {actual}")
            ok = False
        else:
            results.append(f"- ✅ {fname} checksum OK")
    with open(out / "checksums.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(results))
    return ok


def run_tests(out):
    # run the repository's test script which prints summary
    test_script = ROOT / "panelin_reports" / "test_pdf_generation.py"
    res_file = out / "test_output.txt"
    start = time.time()
    try:
        rc = subprocess.run([sys.executable, str(test_script)], check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=TEST_TIMEOUT_SECONDS)
        with open(res_file, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(rc.stdout)
        duration = time.time() - start
        return rc.returncode == 0, duration
    except Exception as e:
        with open(res_file, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"Exception running tests: {e}\n")
        return False, 0.0


def package_gpt_upload(out):
    # Create GPT_Upload_Package directory and a zip (basic packaging)
    pkg_dir = ROOT / "GPT_Upload_Package"
    pkg_dir.mkdir(exist_ok=True)
    # Copy critical files (Level 1 + docs)
    import shutil
    files_to_copy = [
        "IMPLEMENTATION_SUMMARY_V3.3.md",
        "README.md",
        "Panelin_GPT_config.json",
        "GPT_PDF_INSTRUCTIONS.md",
        "panelin_reports/__init__.py",
        "panelin_reports/pdf_generator.py",
        "panelin_reports/pdf_styles.py",
        "panelin_reports/test_pdf_generation.py",
    ]
    for f in files_to_copy:
        src = ROOT / f
        if src.exists():
            dst = pkg_dir / Path(f).name
            shutil.copy2(src, dst)
    zip_path = ROOT / "GPT_Upload_Package.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix('')), 'zip', pkg_dir)
    return zip_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default=str(OUTDIR_DEFAULT))
    args = parser.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    report_lines = []
    report_lines.append("# Bootstrap validation report")
    ok_checks = verify_checksums(out)
    report_lines.append("\n## Checksums")
    with open(out / "checksums.txt", encoding="utf-8") as fh:
        report_lines.append(fh.read())

    report_lines.append("\n## Test run")
    tests_ok, duration = run_tests(out)
    report_lines.append(f"- Tests passed: {tests_ok}")
    report_lines.append(f"- Duration: {duration:.2f}s")
    if tests_ok:
        report_lines.append("\nAll tests passed ✅")
    else:
        report_lines.append("\nTests failed ❌")

    # package GPT upload
    zip_path = package_gpt_upload(out)
    report_lines.append(f"\n## GPT upload package")
    report_lines.append(f"- Created: {zip_path}")

    # Write report
    with open(out / "bootstrap_report.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(report_lines))

    # exit non-zero on failure
    if not ok_checks or not tests_ok:
        print("Bootstrap validation failed. See report in", out)
        sys.exit(2)
    print("Bootstrap validation succeeded. Report in", out)
    sys.exit(0)

if __name__ == "__main__":
    main()
