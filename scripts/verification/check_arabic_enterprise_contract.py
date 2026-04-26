#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)

settings = (ROOT / 'backend' / 'smart_agri' / 'settings.py').read_text(encoding='utf-8')
if 'LANGUAGE_CODE = "ar"' not in settings and "LANGUAGE_CODE = 'ar'" not in settings:
    fail('backend language code is not Arabic')
if 'TIME_ZONE = "Asia/Aden"' not in settings and "TIME_ZONE = 'Asia/Aden'" not in settings:
    fail('backend timezone is not Asia/Aden')

index_html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
if '<html lang="ar" dir="rtl">' not in index_html:
    fail('frontend index.html missing Arabic RTL root shell')

main = (ROOT / 'frontend' / 'src' / 'main.jsx').read_text(encoding='utf-8')
if 'applyArabicEnterpriseShell()' not in main:
    fail('frontend main.jsx does not apply Arabic enterprise shell')

app_shell = ROOT / 'frontend' / 'src' / 'bootstrap' / 'appShell.js'
if not app_shell.exists():
    fail('Arabic enterprise app shell helper missing')

required_docs = [
    ROOT / 'README_AR.md',
    ROOT / 'docs' / 'doctrine' / 'ARABIC_ENTERPRISE_READINESS_V5.md',
    ROOT / 'docs' / 'doctrine' / 'MANDATORY_EXPANSION_ROADMAP_V5.md',
    ROOT / 'docs' / 'doctrine' / 'V5_COMPLETION_READINESS.md',
    ROOT / 'docs' / 'operations' / 'GO_LIVE_CHECKLIST_AR_V5.md',
]
missing = [str(p.relative_to(ROOT)) for p in required_docs if not p.exists()]
if missing:
    fail('missing Arabic enterprise docs: ' + ', '.join(missing))

make_text = (ROOT / 'Makefile').read_text(encoding='utf-8')
for target in ['verify-arabic-enterprise-static', 'verify-v5-static']:
    if re.search(rf'^{re.escape(target)}:', make_text, flags=re.M) is None:
        fail(f'Makefile missing target {target}')

env_text = (ROOT / '.env.enterprise.example').read_text(encoding='utf-8')
for key in ['DEFAULT_LOCALE=ar_YE', 'DEFAULT_DIRECTION=rtl', 'DEFAULT_TIMEZONE=Asia/Aden']:
    if key not in env_text:
        fail(f'.env.enterprise.example missing {key}')

workflow = ROOT / '.github' / 'workflows' / 'v5-arabic-enterprise-static.yml'
if not workflow.exists():
    fail('GitHub workflow for Arabic enterprise gate is missing')

print('PASS: Arabic enterprise contract is present for V5 candidate')
