@echo off
set LOG_DIR=docs\evidence\closure\latest
echo Running Phase 6 Batch...
python backend\manage.py prepare_e2e_auth_v21 > %LOG_DIR%\m6_prepare.log 2>&1
python backend\manage.py seed_runtime_governance_evidence > %LOG_DIR%\m6_seed.log 2>&1
python backend\manage.py dispatch_outbox > %LOG_DIR%\outbox\dispatch.log 2>&1
python backend\manage.py retry_dead_letters > %LOG_DIR%\outbox\retry.log 2>&1
python backend\manage.py purge_dispatched_outbox --dry-run > %LOG_DIR%\outbox\purge.log 2>&1
python backend\manage.py scan_pending_attachments > %LOG_DIR%\m6_scan.log 2>&1
python backend\manage.py report_due_remote_reviews > %LOG_DIR%\m6_report_due.log 2>&1
python backend\manage.py run_governance_maintenance_cycle --dry-run > %LOG_DIR%\m6_maintenance.log 2>&1
python scripts\verification\check_backup_freshness.py > %LOG_DIR%\m6_backup.log 2>&1
python scripts\verification\check_restore_drill_evidence.py > %LOG_DIR%\m6_restore.log 2>&1
echo Done.
exit /b %ERRORLEVEL%
