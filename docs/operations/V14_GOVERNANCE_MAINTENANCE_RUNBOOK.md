# V14 Governance Maintenance Runbook

## الغرض
تشغيل المهام الدورية الخاصة بالموافقات، المزارع البعيدة، والمرفقات الحاكمة.

## التواتر الموصى به
- كل ساعة: `scan_pending_attachments`
- كل ساعتين: `report_approval_workqueues`
- كل 4 ساعات: `escalate_overdue_approval_requests`
- يومياً: `report_due_remote_reviews` و `enforce_due_remote_reviews`
- يومياً: `archive_due_attachments`
- يومياً: `purge_expired_transient_attachments`
- كأمر موحد بديل: `run_governance_maintenance_cycle`

## مخرجات المراقبة
- عدد الطلبات المتأخرة
- عدد المرفقات التي جرى فحصها/حجرها
- عدد المرفقات المؤرشفة/المحذوفة
- عدد المزارع الصغيرة البعيدة المتأخرة في المراجعة

## تنبيهات حرجة
- أي `quarantined > 0` يجب أن يولد تذكرة متابعة.
- أي مزرعة `remote_site=true` متأخرة عن المراجعة يجب أن تظهر في لوحة القطاع.
- أي backlog approval مرتفع أو overdue متكرر يجب أن يُرفع لمدير القطاع.
