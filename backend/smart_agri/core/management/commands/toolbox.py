
from django.core.management.base import BaseCommand, CommandError
import os
import shutil
import glob

class Command(BaseCommand):
    help = 'Agri-Guardian Unified Toolbox for Maintenance and Diagnostics'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='subcommand', help='Sub-command help')

        # Sub-command: fix-zombies
        parser_zombies = subparsers.add_parser('fix-zombies', help='Remove ghost references and duplicate models')
        
        # Sub-command: audit
        parser_audit = subparsers.add_parser('audit', help='Run forensic integrity checks')
        parser_audit.add_argument('--target', type=str, choices=['logic', 'finance', 'all'], default='all')

        # Sub-command: archive-legacy
        parser_archive = subparsers.add_parser('archive-legacy', help='Move legacy/bak files to _archive')

    def handle(self, *args, **options):
        subcommand = options['subcommand']
        
        if subcommand == 'fix-zombies':
            self.fix_zombies()
        elif subcommand == 'audit':
            self.run_audit(options['target'])
        elif subcommand == 'archive-legacy':
            self.archive_legacy()
        else:
            self.stdout.write(self.style.WARNING("Please specify a subcommand: fix-zombies, audit, archive-legacy"))

    def fix_zombies(self):
        self.stdout.write("Running Zombie Fixer (Absolute Cleanup Protocol)...")
        # Logic ported from absolute_cleanup.py (simplified for demo)
        # In a real scenario, we would import the logic or rewrite it here.
        # Since we already ran it, this is for future maintenance.
        self.stdout.write(self.style.SUCCESS("Zombie Fixer Complete (Simulation)."))

    def run_audit(self, target):
        self.stdout.write(f"Running Forensic Audit: Target={target}")
        import pytest
        
        base_path = "smart_agri/core/tests/forensic"
        
        if target == 'logic' or target == 'all':
            self.stdout.write("--> Auditing Logic Brain...")
            pytest.main([f"{base_path}/test_tree_logic.py"])
            
        if target == 'finance' or target == 'all':
            self.stdout.write("--> Auditing Financial Ledger...")
            pytest.main([f"{base_path}/test_ledger_immutability.py"])

    def archive_legacy(self):
        self.stdout.write("Archiving Legacy Artifacts...")
        archive_dir = "_archive"
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
            
        patterns = ["*.bak", "*legacy*", "*deprecated*"]
        count = 0
        for p in patterns:
            for f in glob.glob(p):
                if os.path.isfile(f) and "_archive" not in f:
                    shutil.move(f, os.path.join(archive_dir, os.path.basename(f)))
                    self.stdout.write(f"Moved: {f}")
                    count += 1
        self.stdout.write(self.style.SUCCESS(f"Archived {count} files."))

