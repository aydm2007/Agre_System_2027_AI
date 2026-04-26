# ClamAV Integration Guide

## Status: Optional Production Add-on

## Configuration
- Set `AGRIASSET_ATTACHMENT_SCAN_MODE=clamav` in environment
- Set `CLAMD_SCAN_COMMAND=clamdscan` or configure TCP socket
- Verify via: `python backend/manage.py scan_pending_attachments`

## Verification
AttachmentPolicyService.security_runtime_summary() returns:
- cdr_enabled: true/false
- clamd_configured: true/false
- objectstore_enabled: true/false
