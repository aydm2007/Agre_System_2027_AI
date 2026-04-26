import os
import django
import sys

# Setup Django
sys.path.append(r'C:\tools\workspace\AgriAsset_v44_test\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models.log import DailyLog, SyncRecord
from smart_agri.core.models.sync_conflict import SyncConflictDLQ, OfflineSyncQuarantine

def run_sync_audit():
    print("💎 [SOVEREIGN AUDIT] Starting Phase 3: Offline Sync & Daily Log Audit...")
    
    # 1. Check for Sync Conflicts
    conflict_count = SyncConflictDLQ.objects.count()
    if conflict_count > 0:
        print(f"🚨 [CONFLICTS] Found {conflict_count} records in SyncConflictDLQ!")
    else:
        print("✅ No pending sync conflicts.")

    # 2. Check for Quarantined Records
    quarantine_count = OfflineSyncQuarantine.objects.count()
    if quarantine_count > 0:
        print(f"🚨 [QUARANTINE] Found {quarantine_count} records in OfflineSyncQuarantine!")
    else:
        print("✅ No quarantined sync records.")

    # 3. Check DailyLog Status Distribution
    total_logs = DailyLog.objects.count()
    draft_logs = DailyLog.objects.filter(status='DRAFT').count()
    variance_alerts = DailyLog.objects.filter(variance_status__in=['WARNING', 'CRITICAL']).count()
    
    if draft_logs > 0:
        print(f"⚠️ [DRAFT] Found {draft_logs} unsubmitted logs (DRAFT status).")
    
    if variance_alerts > 0:
        print(f"🚨 [VARIANCE] Found {variance_alerts} logs with WARNING or CRITICAL variance status!")
    else:
        print(f"✅ DailyLog metrics look consistent across {total_logs} records.")

    print("\n📊 [SYNC AUDIT SUMMARY]")
    print(f"---------------------------------")
    print(f"Conflicts: {conflict_count}")
    print(f"Quarantine: {quarantine_count}")
    print(f"Status: {'✅ CRYSTAL SYNC' if (conflict_count + quarantine_count) == 0 else '🛡️ NEEDS RESOLUTION'}")
    print(f"---------------------------------\n")

if __name__ == "__main__":
    run_sync_audit()
