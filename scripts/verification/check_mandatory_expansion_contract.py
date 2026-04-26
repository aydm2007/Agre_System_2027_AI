#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
roadmap = ROOT / 'docs' / 'doctrine' / 'MANDATORY_EXPANSION_ROADMAP_V5.md'
if not roadmap.exists():
    print('FAIL: mandatory expansion roadmap missing')
    sys.exit(1)
text = roadmap.read_text(encoding='utf-8')
required_sections = [
    'الأول: التوسعة التشغيلية',
    'الثاني: التوسعة المالية',
    'الثالث: التوسعة الرقابية',
    'الرابع: التوسعة التخطيطية',
    'الخامس: التوسعة الإدارية',
    'السادس: التوسعة التقنية والبنية',
    'السابع: التوسعة التحليلية والذكاء',
]
for section in required_sections:
    if section not in text:
        print(f'FAIL: roadmap missing section {section}')
        sys.exit(1)
print('PASS: mandatory expansion roadmap is structurally complete for V5 candidate')
