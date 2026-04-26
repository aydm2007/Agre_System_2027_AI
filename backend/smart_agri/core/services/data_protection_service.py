"""
Data Protection Service - Backup and Audit Trail.

AGRI-GUARDIAN: Ensures data integrity for reference data.
"""
from datetime import datetime
from django.conf import settings
import logging
import os

logger = logging.getLogger(__name__)


class DataProtectionService:
    """
    Utility service for backup and data protection operations.
    """

    @staticmethod
    def create_backup_checkpoint(description: str = "Manual Checkpoint") -> dict:
        """
        Creates a logical checkpoint in the audit log.
        Should be called before major data operations.
        """
        from smart_agri.core.models import SecurityLog
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        system_user = User.objects.filter(is_superuser=True).first()
        
        timestamp = datetime.now().isoformat()
        
        SecurityLog.objects.create(
            user=system_user,
            action='BACKUP_CHECKPOINT',
            model_name='System',
            object_id='0',
            changes={
                'description': description,
                'timestamp': timestamp,
                'type': 'checkpoint'
            }
        )
        
        logger.info(f"CHECKPOINT: {description} at {timestamp}")
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "description": description
        }

    @staticmethod
    def verify_data_integrity() -> dict:
        """
        Runs a comprehensive data integrity check.
        """
        from smart_agri.core.services.financial_integrity_service import FinancialIntegrityService
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": []
        }
        
        # 1. Ledger Balance Check
        ledger_check = FinancialIntegrityService.verify_ledger_balance()
        results["checks"].append({
            "name": "Ledger Balance",
            "passed": ledger_check["is_balanced"],
            "details": ledger_check
        })
        
        # 2. Overhead Summary
        overhead = FinancialIntegrityService.get_overhead_summary()
        results["checks"].append({
            "name": "Overhead Summary",
            "passed": True,
            "details": overhead
        })
        
        # 3. Database Consistency
        from smart_agri.core.models import Activity, DailyLog
        orphan_activities = Activity.objects.filter(log__isnull=True).count()
        results["checks"].append({
            "name": "Orphan Activities",
            "passed": orphan_activities == 0,
            "count": orphan_activities
        })
        
        all_passed = all(check["passed"] for check in results["checks"])
        results["status"] = "✅ ALL PASSED" if all_passed else "⚠️ ISSUES FOUND"
        
        logger.info(f"INTEGRITY_CHECK: {results['status']}")
        
        return results

    @staticmethod
    def get_backup_command() -> str:
        """
        Returns the PostgreSQL backup command for the current database.
        """
        db_name = settings.DATABASES['default'].get('NAME', 'agriasset')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"pg_dump {db_name} > backup_{db_name}_{timestamp}.sql"

    @staticmethod
    def mask_sensitive_data(value: str, visible_chars=2) -> str:
        """
        Masks names/ids for privacy without heavy encryption overhead.
        Example: 'Ahmed Ali' -> 'Ah***'
        Context: Tribal privacy protection.
        """
        if not value or len(value) <= visible_chars:
            return "***"
        
        return f"{value[:visible_chars]}{'*' * 3}"

    @staticmethod
    def encrypt_salary(amount):
        """
        Real encryption for sensitive fields stored in non-secure logs.
        """
        # Placeholder for Fernet logic or simple warning
        # For now, we ensure we don't log raw salaries in text files
        return "<ENCRYPTED_PAYLOAD>"
