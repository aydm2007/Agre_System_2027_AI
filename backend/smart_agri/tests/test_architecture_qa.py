
"""
QA Automation Suite: System Architecture & Hygiene
Target: Entire Project Structure (Deep Scan)
Framework: Pytest
"""
import pytest
import os
import sys
from django.conf import settings
from django.apps import apps
from django.db import connection

# Define the root of the backend
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestSystemArchitectureQA:
    
    def test_zombie_files_extermination(self):
        """
        Verify that all known 'Zombie' files are physically deleted from the filesystem.
        """
        zombies = [
            os.path.join(BACKEND_ROOT, 'smart_agri', 'core', 'models', 'finance.py'),
            os.path.join(BACKEND_ROOT, 'smart_agri', 'core', 'models', 'commercial.py'),
            os.path.join(BACKEND_ROOT, 'smart_agri', 'core', 'api', 'viewsets', 'finance.py'),
            os.path.join(BACKEND_ROOT, 'smart_agri', 'core', 'api', 'viewsets', 'commercial.py'),
        ]
        
        print(f"\n🔍 QA CHECK: Scanning {len(zombies)} potential zombie locations...")
        for z in zombies:
            exists = os.path.exists(z)
            status = "❌ ALIVE" if exists else "✅ DEAD"
            print(f"   [{status}] {os.path.basename(z)}")
            assert not exists, f"Zombie file found: {z}"

    def test_app_registry_integrity(self):
        """
        Verify that the Django App Registry loads the NEW apps and NOT the legacy modules.
        """
        print("\n🔍 QA CHECK: App Registry")
        installed_apps = [app.name for app in apps.get_app_configs()]
        
        # Must have new apps
        assert 'smart_agri.finance' in installed_apps
        assert 'smart_agri.sales' in installed_apps
        assert 'smart_agri.inventory' in installed_apps
        
        # Verify Core Models don't contain 'FinancialLedger'
        core_config = apps.get_app_config('core')
        core_models = [m.__name__ for m in core_config.get_models()]
        
        print(f"   Core Models: {len(core_models)}")
        assert 'FinancialLedger' not in core_models, "CRITICAL: FinancialLedger still detected in Core App!"
        assert 'SalesInvoice' not in core_models, "CRITICAL: SalesInvoice still detected in Core App!"

    @pytest.mark.django_db
    def test_database_schema_hygiene(self):
        """
        Verify that the database does not contain 'zombie' tables (orphaned core_* tables that shouldn't exist).
        Note: This assumes we wanted to migrate away from them. 
        HOWEVER, our strategy was 'Safe-Move' (managed=False pointing to core_*).
        So we actually EXPECT 'core_salesinvoice' to exist, but correctly mapped.
        """
        print("\n🔍 QA CHECK: Database Schema")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [r[0] for r in cursor.fetchall()]
            
        # Verify we access the tables via the NEW apps
        from smart_agri.sales.models import SalesInvoice
        assert SalesInvoice._meta.db_table in tables
        print(f"   ✅ SalesInvoice maps to existing table: {SalesInvoice._meta.db_table}")

    def test_import_purity(self):
        """
        Grep content of core/__init__.py to ensure no forbidden imports.
        """
        init_path = os.path.join(BACKEND_ROOT, 'smart_agri', 'core', 'models', '__init__.py')
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        assert 'from .finance' not in content, "Legacy import (.finance) found in core/__init__.py"
        assert 'from .commercial' not in content, "Legacy import (.commercial) found in core/__init__.py"
        print("\n   ✅ Core Impor Hygiene: CLEAN")

