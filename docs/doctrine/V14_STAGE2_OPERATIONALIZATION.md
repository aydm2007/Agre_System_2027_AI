# V14 Stage-2 Operationalization

## الهدف
تحويل مكاسب V12/V13 من سياسات وبذور حوكمة إلى تشغيل يومي حي داخل النظام.

## ما أضيف في هذه المرحلة
1. **صندوق اعتماد مرحلي حي** يعتمد على `queue_snapshot` و `stage_chain` و `queue-summary`.
2. **Maintenance cycle** موحد عبر الأمر `run_governance_maintenance_cycle`.
3. **مسار مرفقات أشد حوكمة** يضيف `archive_backend`, `archive_key`, `scanned_at`, `quarantined_at`, `restored_at`.
4. **فحص pending attachments** وتحويلها إلى Passed أو Quarantined قبل الثقة بها.
5. **تحسين الواجهة** لإظهار SLA والتأخر والتقدم المرحلي داخل Approval Inbox.

## القيود
- ما زال الفحص المضاد للبرمجيات الخبيثة heuristic-first وليس AV/CDR إنتاجياً كاملاً.
- الأرشفة ما زالت filesystem-backed وليست object-storage مؤسسية كاملة.
- الـ runtime proof الكامل ما زال مطلوباً خارج هذه المرحلة.

## أوامر التشغيل
```bash
python manage.py scan_pending_attachments
python manage.py report_approval_workqueues
python manage.py escalate_overdue_approval_requests
python manage.py report_due_remote_reviews
python manage.py enforce_due_remote_reviews
python manage.py archive_due_attachments
python manage.py purge_expired_transient_attachments
python manage.py run_governance_maintenance_cycle
```
