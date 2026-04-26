#!/usr/bin/env python
"""
API Stability Check Script
AGRI-GUARDIAN: Frontend Contract Enforcement

This script verifies that API endpoints and serializers used by the frontend
are not being modified without corresponding frontend updates.

Usage:
    python scripts/check_api_stability.py [serializer_name]
    
Example:
    python scripts/check_api_stability.py ActivitySerializer
"""
import sys
import os
import re
from pathlib import Path
from typing import Set, Dict, List

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def find_serializer_usages_in_frontend(serializer_fields: Set[str]) -> Dict[str, List[str]]:
    """
    Search frontend code for usages of serializer field names.
    Returns a dict mapping field names to files that use them.
    """
    frontend_dir = backend_dir.parent / 'frontend' / 'src'
    usages = {}
    
    if not frontend_dir.exists():
        print(f"Warning: Frontend directory not found: {frontend_dir}")
        return usages
    
    for f in frontend_dir.rglob('*.js'):
        content = f.read_text(encoding='utf-8', errors='ignore')
        for field in serializer_fields:
            # Check for .field_name, ['field_name'], data.field_name patterns
            patterns = [
                rf'\.\s*{field}\b',
                rf'\[\s*["\']?{field}["\']?\s*\]',
                rf'"{field}"\s*:',
                rf"'{field}'\s*:",
            ]
            for pattern in patterns:
                if re.search(pattern, content):
                    if field not in usages:
                        usages[field] = []
                    usages[field].append(str(f.relative_to(frontend_dir)))
                    break  # Only count once per file
    
    for f in frontend_dir.rglob('*.jsx'):
        content = f.read_text(encoding='utf-8', errors='ignore')
        for field in serializer_fields:
            patterns = [
                rf'\.\s*{field}\b',
                rf'\[\s*["\']?{field}["\']?\s*\]',
            ]
            for pattern in patterns:
                if re.search(pattern, content):
                    if field not in usages:
                        usages[field] = []
                    usages[field].append(str(f.relative_to(frontend_dir)))
                    break
    
    return usages


def extract_serializer_fields(serializer_name: str) -> Set[str]:
    """
    Extract field names from a Django REST Framework serializer.
    This is a simple regex-based extraction.
    """
    fields = set()
    serializers_dir = backend_dir / 'smart_agri' / 'core' / 'serializers'
    
    for f in serializers_dir.rglob('*.py'):
        content = f.read_text(encoding='utf-8', errors='ignore')
        
        # Check if this file defines the serializer
        if f'class {serializer_name}' in content:
            print(f"Found {serializer_name} in {f.name}")
            
            # Extract fields from Meta.fields = [...] or fields = (...)
            fields_match = re.search(r'fields\s*=\s*[\[(](.*?)[\])]', content, re.DOTALL)
            if fields_match:
                fields_str = fields_match.group(1)
                # Extract quoted strings
                extracted = re.findall(r'["\'](\w+)["\']', fields_str)
                fields.update(extracted)
            
            # Also extract field definitions like: name = serializers.CharField()
            field_defs = re.findall(r'^(\s+)(\w+)\s*=\s*serializers\.\w+', content, re.MULTILINE)
            for indent, field_name in field_defs:
                if not field_name.startswith('_') and field_name != 'Meta':
                    fields.add(field_name)
    
    return fields


def run_stability_check(serializer_name: str = None):
    """Run API stability check."""
    print("\n" + "="*60)
    print("🛡️ AGRI-GUARDIAN API STABILITY CHECK")
    print("="*60 + "\n")
    
    # Find all serializers if none specified
    serializers_dir = backend_dir / 'smart_agri' / 'core' / 'serializers'
    
    if serializer_name:
        serializers_to_check = [serializer_name]
    else:
        # Find all serializers
        serializers_to_check = []
        for f in serializers_dir.rglob('*.py'):
            content = f.read_text(encoding='utf-8', errors='ignore')
            matches = re.findall(r'class (\w+Serializer)', content)
            serializers_to_check.extend(matches)
    
    print(f"Checking {len(serializers_to_check)} serializers...\n")
    
    critical_fields = {}
    
    for serializer in serializers_to_check:
        fields = extract_serializer_fields(serializer)
        if fields:
            usages = find_serializer_usages_in_frontend(fields)
            if usages:
                print(f"📋 {serializer}:")
                for field, files in usages.items():
                    print(f"   • {field}: used in {len(files)} file(s)")
                    critical_fields[f"{serializer}.{field}"] = files
                print()
    
    # Summary
    print("="*60)
    if critical_fields:
        print(f"⚠️  {len(critical_fields)} fields are used by frontend")
        print("   Modifying these fields requires frontend updates!")
        print("\nCritical fields (DO NOT REMOVE WITHOUT FRONTEND UPDATE):")
        for field in sorted(critical_fields.keys())[:20]:
            print(f"   • {field}")
    else:
        print("✅ No critical frontend dependencies found")
    print("="*60 + "\n")
    
    return critical_fields


if __name__ == '__main__':
    serializer = sys.argv[1] if len(sys.argv) > 1 else None
    run_stability_check(serializer)
