#!/usr/bin/env python
"""
Silent Exception Audit Script
AGRI-GUARDIAN: Forensic Audit Standards Enforcement

This script finds potential silent exception swallowing that violates
the Forensic Audit Standards: "try-except blocks swallowing DatabaseError 
or returning 0 silently are FORBIDDEN."

Usage:
    python scripts/audit_silent_exceptions.py
"""
import re
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate silent exception handling (forbidden)
FORBIDDEN_PATTERNS = [
    # except X: pass
    (r'except\s+\w+.*:\s*\n\s+pass\s*$', 'Silent pass after except'),
    # except: pass
    (r'except\s*:\s*\n\s+pass\s*$', 'Bare except with pass'),
    # except X: return 0
    (r'except\s+\w+.*:\s*\n\s+return\s+0\s*$', 'Silent return 0 on exception'),
    # DatabaseError swallowed
    (r'except\s+DatabaseError.*:\s*\n\s+(pass|\.\.\.)', 'DatabaseError silently swallowed'),
]

# Acceptable patterns (not flagged)
ACCEPTABLE_CONTEXTS = [
    'logging',
    'logger',
    'raise',
    'print(',
    'log(',
    'warning',
    'error',
]


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    Check a file for silent exception handling.
    Returns list of (line_number, line_content, issue_description)
    """
    issues = []
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Find except statements
            if re.match(r'\s*except\s+', line) or re.match(r'\s*except\s*:', line):
                # Check what follows (next 3 lines)
                following = '\n'.join(lines[i:i+4])
                
                # Check for forbidden patterns
                for pattern, description in FORBIDDEN_PATTERNS:
                    if re.search(pattern, following, re.MULTILINE):
                        # Verify no acceptable handling
                        block = '\n'.join(lines[i:i+6])
                        has_logging = any(ctx in block.lower() for ctx in ACCEPTABLE_CONTEXTS)
                        
                        if not has_logging:
                            issues.append((i+1, line.strip(), description))
                            break
                
                # Special check: broad except without specific handling
                if 'Exception' in line or re.match(r'\s*except\s*:', line):
                    block = '\n'.join(lines[i:i+6])
                    if 'pass' in block or '...' in block:
                        if not any(ctx in block.lower() for ctx in ACCEPTABLE_CONTEXTS):
                            issues.append((i+1, line.strip(), 'Broad exception possibly swallowed'))
    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return issues


def run_audit():
    """Run silent exception audit on the codebase."""
    print("\n" + "="*70)
    print("🛡️ AGRI-GUARDIAN SILENT EXCEPTION AUDIT")
    print("="*70 + "\n")
    
    # Determine paths
    script_dir = Path(__file__).parent
    smart_agri_dir = script_dir.parent / 'smart_agri'
    
    if not smart_agri_dir.exists():
        smart_agri_dir = script_dir.parent.parent / 'backend' / 'smart_agri'
    
    if not smart_agri_dir.exists():
        print(f"Error: Cannot find smart_agri directory")
        return
    
    all_issues = {}
    checked_files = 0
    
    # Exclude test files and venv
    for py_file in smart_agri_dir.rglob('*.py'):
        # Skip test files (tests are allowed to have broad excepts)
        if 'test' in str(py_file).lower() or 'venv' in str(py_file):
            continue
        
        checked_files += 1
        issues = check_file(py_file)
        
        if issues:
            relative_path = str(py_file.relative_to(smart_agri_dir.parent))
            all_issues[relative_path] = issues
    
    # Report
    print(f"📂 Checked {checked_files} files\n")
    
    if all_issues:
        total_issues = sum(len(v) for v in all_issues.values())
        print(f"⚠️  Found {total_issues} potential silent exception(s) in {len(all_issues)} file(s):\n")
        
        for filepath, issues in sorted(all_issues.items()):
            print(f"📄 {filepath}:")
            for line_no, line_content, description in issues:
                print(f"   Line {line_no}: {description}")
                print(f"      → {line_content[:60]}...")
            print()
        
        print("="*70)
        print("⚠️  ACTION REQUIRED: Review and add proper logging/re-raising")
        print("   Silent exception swallowing is FORBIDDEN by Agri-Guardian.")
    else:
        print("✅ No silent exception swallowing detected!")
        print("="*70)
    
    print(f"\nTotal issues: {sum(len(v) for v in all_issues.values())}")
    
    return all_issues


if __name__ == '__main__':
    run_audit()
