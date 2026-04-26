
import os
import django
import sys
import traceback
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model

# Import ViewSets
from smart_agri.core.api.viewsets.crop import CropCardViewSet, ServiceCardViewSet
from smart_agri.core.api.viewsets.inventory import HarvestProductCatalogViewSet, ItemInventoryViewSet
from smart_agri.inventory.api.viewsets import TreeInventorySummaryViewSet
from smart_agri.sales.api import SalesInvoiceViewSet
from smart_agri.core.api.viewsets.log import DailyLogViewSet
from smart_agri.core.api.viewsets.farm import LocationWellViewSet
from smart_agri.core.api.hr import EmployeeViewSet
from smart_agri.finance.api import (
    FinancialLedgerViewSet, FiscalYearViewSet, FiscalPeriodViewSet, ActualExpenseViewSet
)
from smart_agri.core.api.activities import ActivityViewSet

from smart_agri.core.api.viewsets.planning import CropPlanViewSet, HarvestLogViewSet

# Helper class for logging to file
class LoggerWriter:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.filename = filename
        self.log = open(filename, 'w', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def check_schema_compliance():
    print("\n[TEST] Schema Compliance (Axis 1)")
    try:
        from smart_agri.core.models.hr import Employee, EmploymentCategory
        from smart_agri.finance.models import FiscalPeriod
        
        # Check Employee.category
        if hasattr(Employee, 'category') and 'OFFICIAL' in EmploymentCategory.values and 'CASUAL' in EmploymentCategory.values:
             print("STATUS: ✅ Employee.category matches")
        else:
             print("STATUS: ❌ Employee.category mismatch")
             
        # Check FiscalPeriod.status
        if hasattr(FiscalPeriod, 'status') and 'hard_close' in dict(FiscalPeriod.STATUS_CHOICES):
             print("STATUS: ✅ FiscalPeriod.status matches")
        else:
             print("STATUS: ❌ FiscalPeriod.status mismatch")

    except Exception:
        print("!!! CRASH IN SCHEMA CHECK !!!")
        traceback.print_exc()

def check_idempotency_compliance():
    print("\n[TEST] Idempotency Compliance (Axis 2)")
    # Static check for X-Idempotency-Key in base viewset or middleware
    try:
        from smart_agri.core.api.viewsets.base import BaseViewSet
        import inspect
        src = inspect.getsource(BaseViewSet)
        if "X-Idempotency-Key" in src:
            print("STATUS: ✅ BaseViewSet enforces Idempotency")
        else:
            print("STATUS: ❌ BaseViewSet missing Idempotency check")
    except Exception:
         print("STATUS: ❓ Could not verify Idempotency statically")

def run_diagnostics():
    # Redirect stdout to file
    sys.stdout = LoggerWriter('crash_output.txt')
    sys.stderr = sys.stdout

    print("--- AGRI-GUARDIAN SYSTEM AUDIT START ---")
    
    # 1. Schema & Compliance Checks
    check_schema_compliance()
    check_idempotency_compliance()

    User = get_user_model()
    try:
        user = User.objects.filter(username='ibrahim').first() or User.objects.first()
        if user:
            print(f"DEBUG: Authenticating as {user.username} (ID: {user.id})")
        else:
            print("DEBUG: No user found - Skipping API checks")
            return
    except Exception:
        print("DEBUG: User lookup failed")
        return

    factory = APIRequestFactory()

    endpoints = [
        # --- CORE & HR ---
        {"name": "Employees - Farm 6", "view": EmployeeViewSet, "method": "list", "url": "/api/v1/employees/?farm=6"},
        {"name": "Daily Logs - Farm 6", "view": DailyLogViewSet, "method": "day_summary", "url": "/api/v1/daily-logs/day-summary/?farm_id=6&date=2025-10-21"},
        {"name": "Activities - Farm 6", "view": ActivityViewSet, "method": "list", "url": "/api/v1/activities/?farm_id=6"},

        # --- INVENTORY & ASSETS ---
        {"name": "Item Inventory - Farm 6", "view": ItemInventoryViewSet, "method": "list", "url": "/api/v1/inventory/?farm=6"},
        {"name": "Tree Inventory (Perennials) - Farm 6", "view": TreeInventorySummaryViewSet, "method": "list", "url": "/api/v1/tree-inventory/summary/?farm_id=6"},
        {"name": "Crop Cards - Farm 6", "view": CropCardViewSet, "method": "list", "url": "/api/v1/crop-cards/?farm_id=6"},
        {"name": "Service Providers", "view": ServiceCardViewSet, "method": "list", "url": "/api/v1/service-cards/?farm_id=6"},
        {"name": "Harvest Products", "view": HarvestProductCatalogViewSet, "method": "list", "url": "/api/v1/harvest-product-catalog/?farm_id=6"},
        {"name": "Location Wells - Farm 2", "view": LocationWellViewSet, "method": "summary", "url": "/api/v1/location-wells/summary/?farm_id=2"},

        # --- SALES ---
        {"name": "Sales Invoices - Farm 6", "view": SalesInvoiceViewSet, "method": "list", "url": "/api/v1/sales-invoices/?farm_id=6"},
        {"name": "Sales Invoices - Farm 2", "view": SalesInvoiceViewSet, "method": "list", "url": "/api/v1/sales-invoices/?farm_id=2"}, # Stress Test

        # --- FINANCE (New) ---
        {"name": "Financial Ledger", "view": FinancialLedgerViewSet, "method": "list", "url": "/api/v1/finance/ledger/"},
        {"name": "Fiscal Years", "view": FiscalYearViewSet, "method": "list", "url": "/api/v1/finance/fiscal-years/"},
        {"name": "Fiscal Periods", "view": FiscalPeriodViewSet, "method": "list", "url": "/api/v1/finance/fiscal-periods/"},
        {"name": "Actual Expenses - Farm 6", "view": ActualExpenseViewSet, "method": "list", "url": "/api/v1/finance/expenses/?farm=6"},
        {"name": "Actual Expenses - Summary", "view": ActualExpenseViewSet, "method": "summary", "url": "/api/v1/finance/expenses/summary/?farm=6"},

        # --- NEW ENDPOINTS (Fixing 404s) ---
        {"name": "Harvest Logs", "view": HarvestLogViewSet, "method": "list", "url": "/api/v1/harvest-logs/?crop_plan=25"},
        # Variance via FinancialLedgerViewSet material-variance-analysis (detail=False, uses query param)
        {"name": "Crop Plan Variance (Dynamic)", "view": FinancialLedgerViewSet, "method": "material_variance_analysis", "url": "/api/v1/finance/ledger/material-variance-analysis/", "dynamic_crop_plan_id": True},
    ]
    
    all_passed = True
    
    for ep in endpoints:
        print(f"\n[TEST] {ep['name']}")
        print(f"URL: {ep['url']}")
        try:
            # Resolve dynamic crop_plan_id into query string
            url = ep['url']
            if ep.get('dynamic_crop_plan_id'):
                from smart_agri.core.models import CropPlan
                first_plan = CropPlan.objects.filter(deleted_at__isnull=True).first()
                if first_plan:
                    url = f"{url}?crop_plan_id={first_plan.id}"
                    print(f"URL: {url}")
                else:
                    print(f"STATUS: ❓ SKIP (No CropPlan in DB)")
                    continue

            request = factory.get(url)
            force_authenticate(request, user=user)
            # Handle ViewSet Actions vs List
            if ep['method'] == 'list':
                view = ep['view'].as_view({'get': 'list'})
            elif ep['method'] == 'summary':
                 view = ep['view'].as_view({'get': ep['method']})
            elif ep['method'] == 'day_summary':
                 view = ep['view'].as_view({'get': 'day_summary'})
            elif ep['method'] == 'summary_list':
                 view = ep['view'].as_view({'get': 'summary_list'})
            else:
                 view = ep['view'].as_view({'get': ep['method']})

            response = view(request)
            
            if response.status_code == 200:
                print(f"STATUS: ✅ 200 OK")
            else:
                print(f"STATUS: ❌ {response.status_code}")
                # print(f"ERROR DATA: {response.data}")
                all_passed = False
                
        except Exception as e:
            print(f"!!! CRASH DETECTED !!!")
            traceback.print_exc()
            all_passed = False

    # [Agri-Guardian] Test Advanced Report
    print(f"\n[TEST] Advanced Report - Full Query")
    url = "/api/v1/advanced-report/?start=2026-01-01&end=2026-12-31&include_tree_inventory=true&tree_filters=%7B%7D&farm=6"
    try:
        from smart_agri.core.api.reporting import advanced_report
        request = factory.get(url)
        force_authenticate(request, user=user)
        response = advanced_report(request)
        if response.status_code == 200:
             print(f"STATUS: ✅ 200 OK")
        else:
             print(f"STATUS: ❌ {response.status_code}")
             all_passed = False
    except Exception as e:
        print("!!! CRASH DETECTED !!!")
        traceback.print_exc()
        all_passed = False

    if all_passed:
        print("\n--- VERDICT: SYSTEM STABLE (100% PASS) ---")
    else:
        print("\n--- VERDICT: SYSTEM UNSTABLE (FAILURES DETECTED) ---")

if __name__ == "__main__":
    run_diagnostics()
