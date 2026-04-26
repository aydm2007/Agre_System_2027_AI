# V18 Gap Closure Matrix

| Gap | V17 status | V18 action | Evidence | Residual risk |
|---|---|---|---|---|
| Sector role modeling below 90 | Roles existed but lacked grouped workbench visibility | Added role workbench snapshot + API + inbox surface | `approval_service.py`, `api_approval.py`, `ApprovalInbox.jsx` | Full per-role dashboards still pending |
| Small-farm remote-review enforcement below 90 | Commands referenced a missing report helper | Added `RemoteReviewService.report_due_reviews()` and governance snapshot | `remote_review_service.py`, maintenance commands | Scheduler/runtime proof still pending |
| Upload hardening below 90 | Extension/MIME/signature only | Added PDF JS/OpenAction blocking + XLSX macro/zip-bomb heuristics | `attachment_policy_service.py`, tests | AV/CDR still pending |
