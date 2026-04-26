# START HERE — AgriAsset V4 Enterprise Candidate

1. Read `AGENTS.md` first.
2. For bootstrap, read `README_Install.md`.
3. For enterprise go-live, read `docs/operations/ENTERPRISE_PRODUCTION_RUNBOOK_V4.md`.
4. For backup/restore, read `docs/operations/BACKUP_RESTORE_RUNBOOK_V4.md`.
5. Run static checks:
   ```bash
   python backend/manage.py verify_static_v21
   ```
6. In a provisioned environment, run the release gate:
   ```bash
   python backend/manage.py verify_release_gate_v21
   ```
7. Legacy wrappers remain available and delegate to the same canonical commands:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/verify_static.ps1
   powershell -ExecutionPolicy Bypass -File scripts/verify_release_gate.ps1
   ```
