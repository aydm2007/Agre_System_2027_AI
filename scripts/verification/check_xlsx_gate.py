"""
TI-10: XLSX Integrity Gate Verification
Verifies that no test or source files contain dangerous XLSX macro patterns or external rels.
Part of the release readiness snapshot V21.
"""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path


def check_xlsx_files(root: Path) -> list[str]:
    failures = []
    
    for root_dir, dirs, files in os.walk(root):
        if ".git" in dirs:
            dirs.remove(".git")
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        if ".venv" in dirs:
            dirs.remove(".venv")
            
        for file in files:
            if not file.lower().endswith(".xlsx"):
                continue
                
            path = Path(root_dir) / file
            try:
                with zipfile.ZipFile(path) as zf:
                    for info in zf.infolist():
                        filename = (info.filename or "").lower()
                        if "vbaproject.bin" in filename or (filename.endswith(".bin") and "xl/" in filename):
                            failures.append(f"{path}: Contains macro/binary payload ({filename})")
                        if filename.endswith(".rels"):
                            rel_data = zf.read(info).decode("utf-8", errors="ignore")
                            if 'TargetMode="External"' in rel_data:
                                failures.append(f"{path}: Contains external relation in OOXML")
            except zipfile.BadZipFile:
                # Corrupt XLSX files shouldn't be in the repo either
                failures.append(f"{path}: Bad/corrupt zip container")
            except Exception as exc:
                failures.append(f"{path}: Error probing container: {exc}")
                
    return failures


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    print(f"Scanning for dangerous XLSX files in {repo_root}...")
    failures = check_xlsx_files(repo_root)
    
    if failures:
        print("\n❌ FAILED. Found dangerous XLSX files:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
        
    print("\n✅ PASS: No dangerous XLSX macro or external-rel patterns found in repo.")
    sys.exit(0)


if __name__ == "__main__":
    main()
