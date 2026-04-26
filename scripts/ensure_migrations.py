import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / 'backend'
APPS = [
    'smart_agri/core',
    'smart_agri/accounts',
    'smart_agri/sales',
    'smart_agri/integrations',
    'smart_agri/inventory',
    'smart_agri/finance',
]

missing = []
for app in APPS:
    mig_path = BASE_DIR / app / 'migrations'
    init_file = mig_path / '__init__.py'
    
    if not mig_path.exists():
        print(f"Creating missing migration dir: {mig_path}")
        mig_path.mkdir(parents=True, exist_ok=True)
        
    if not init_file.exists():
        print(f"Creating missing __init__.py: {init_file}")
        with open(init_file, 'w') as f:
            pass
        missing.append(str(init_file))

if missing:
    print(f"Fixed {len(missing)} missing migration packages.")
else:
    print("All migration packages exist.")
