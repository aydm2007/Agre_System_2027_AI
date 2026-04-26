import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

import django
django.setup()

import io
from contextlib import redirect_stdout

from scripts import detect_zombies
from scripts import check_no_float_mutations
from scripts import check_idempotency_actions
from scripts import check_zakat_harvest_triggers

def run_all():
    results = {}
    
    # 1. Zombies
    f = io.StringIO()
    with redirect_stdout(f):
        try:
            detect_zombies.run()
        except SystemExit as e:
            print(f"Exited with {e.code}")
    results['zombies'] = f.getvalue()
    
    # 2. Floats
    f = io.StringIO()
    with redirect_stdout(f):
        try:
            check_no_float_mutations.run()
        except SystemExit as e:
            print(f"Exited with {e.code}")
    results['floats'] = f.getvalue()
    
    # 3. Idempotency
    f = io.StringIO()
    with redirect_stdout(f):
        try:
            check_idempotency_actions.run()
        except SystemExit as e:
            print(f"Exited with {e.code}")
    results['idempotency'] = f.getvalue()

    with open('compliance_output.txt', 'w', encoding='utf-8') as out:
        for k, v in results.items():
            out.write(f"=== {k.upper()} ===\n{v}\n\n")

if __name__ == '__main__':
    run_all()
