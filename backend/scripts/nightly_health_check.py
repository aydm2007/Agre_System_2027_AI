import os
import sys
import logging
from datetime import datetime
import django

# Setup Django Environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import Activity, TreeProductivityStatus
from verify_lifecycle import verify_lifecycle
from fix_mojibake import fix_mojibake

# Setup Logging
log_file = f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_file, encoding='utf-8'),
    logging.StreamHandler(sys.stdout)
])
logger = logging.getLogger(__name__)

def check_encoding():
    """Checks for Mojibake and attempts auto-fix."""
    logger.info("--- CHECK: Text Encoding (Mojibake) ---")
    bad_chars = ['Ø', 'Ù']
    found = False
    
    # Check TreeProductivityStatus
    for status in TreeProductivityStatus.objects.all():
        for char in bad_chars:
            if char in status.name_ar:
                logger.error(f"Mojibake found in status {status.code}: {status.name_ar}")
                found = True
                break
    
    if found:
        logger.warning("Encoding errors detected. Attempting AUTO-FIX...")
        try:
            fix_mojibake()
            logger.info("Auto-fix script executed successfully.")
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
    else:
        logger.info("Text encoding looks clean.")

def check_lifecycle():
    """Runs the verify_lifecycle simulation to ensure no 500 errors."""
    logger.info("--- CHECK: System Lifecycle (No 500 Errors) ---")
    try:
        verify_lifecycle()
        logger.info("Lifecycle verification passed.")
    except Exception as e:
        logger.critical(f"Lifecycle verification CRASHED: {e}")
        # In a real self-healing system, we might rollback or alert here
        # Since I cannot write code dynamically in this script safely, we just log.

def run_django_tests():
    """Runs the standard Django test suite."""
    logger.info("--- CHECK: Full Django Test Suite ---")
    from django.core.management import call_command
    try:
        # Capture output to log file? call_command output redirection is tricky in script.
        # We'll run it and catch exceptions.
        # Running only 'core' app tests to save time, or all? User said "Everything".
        # Let's run all.
        logger.info("Running 'python manage.py test' ... (This may take time)")
        # We redirect stdout/stderr to satisfy the logger
        call_command('test', interactive=False, verbosity=1)
        logger.info("Django Tests Passed.")
    except Exception as e:
        logger.error(f"Django Tests FAILED: {e}")

def check_and_run_migrations():
    """Checks for pending migrations and applies them."""
    logger.info("--- CHECK: Database Migrations ---")
    from django.core.management import call_command
    try:
        call_command('migrate', interactive=False)
        logger.info("Database is up to date.")
    except Exception as e:
        logger.error(f"Migration Failed: {e}")

def run_health_check():
    logger.info("=== STARTING FULL SYSTEM AUTOPILOT ===")
    
    try:
        check_and_run_migrations()
        check_encoding()
        check_lifecycle()
        run_django_tests()
        logger.info("=== AUTOPILOT COMPLETED ===")
        
    except Exception as e:
        logger.critical(f"=== AUTOPILOT CRASHED ===\nError: {e}")

if __name__ == "__main__":
    run_health_check()
