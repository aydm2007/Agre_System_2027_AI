import os
import django
import sys

# Setup Django
sys.path.append(r'C:\tools\workspace\AgriAsset_v44_test\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models.report import AsyncReportRequest
from smart_agri.core.models.dynamic_report import ReportTemplate

def run_report_audit():
    print("💎 [SOVEREIGN AUDIT] Starting Phase 2c: Reporting Quality Audit...")
    
    # 1. Check for Failed Reports
    total_requests = AsyncReportRequest.objects.count()
    failed_reports = AsyncReportRequest.objects.filter(status='FAILED').count()
    if failed_reports > 0:
        print(f"🚨 [REPORT FAILURE] Found {failed_reports} failed report requests!")
    else:
        print(f"✅ All {total_requests} report requests were successful or are pending.")

    # 2. Check for Templates
    template_count = ReportTemplate.objects.count()
    print(f"✅ Found {template_count} active report templates.")

    print("\n📊 [REPORT AUDIT SUMMARY]")
    print(f"---------------------------------")
    print(f"Total Requests: {total_requests}")
    print(f"Failures: {failed_reports}")
    print(f"Status: {'✅ CRYSTAL OUTPUTS' if failed_reports == 0 else '🛡️ NEEDS TUNING'}")
    print(f"---------------------------------\n")

if __name__ == "__main__":
    run_report_audit()
