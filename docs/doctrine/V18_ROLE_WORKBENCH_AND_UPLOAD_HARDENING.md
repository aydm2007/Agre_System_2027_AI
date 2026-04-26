# V18 Role Workbench and Upload Hardening

## Scope
This doctrine closes practical gaps left after V17 in three areas:
1. Sector-role workload visibility
2. Remote-review governance maintenance consistency
3. Attachment intake hardening before evidence promotion

## Sector role workbench
- Source of truth: `ApprovalGovernanceService.role_workbench_snapshot()`
- Surface: `/finance/approval-requests/role-workbench/` and Approval Inbox summary cards
- Buckets: grouped by current required role + farm
- Metrics: count, overdue count, oldest age hours, sample request ids

## Remote review governance
- `RemoteReviewService.report_due_reviews()` is canonical for maintenance runs and backlog reporting.
- Remote farms with overdue reviews remain under compensating-control pressure for STRICT finance actions.

## Upload hardening
- Block PDF files containing JavaScript/OpenAction markers.
- Block XLSX containers containing `vbaProject.bin`.
- Block suspicious compression ratios/member counts that resemble zip bombs.
- Preserve quarantine/archive lifecycle from V17.
