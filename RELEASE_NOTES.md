# Release Notes – V4 enterprise candidate

## Added
- `docker-compose.enterprise.yml`
- `.env.enterprise.example`
- `scripts/ops/pg_backup_custom.sh`
- `scripts/ops/pg_restore_custom.sh`
- `scripts/ops/preflight_enterprise.sh`
- `scripts/verification/check_enterprise_readiness.py`
- enterprise runbooks and readiness doctrine docs

## Improved
- production compose health checks and startup dependencies
- Makefile enterprise targets
- release gate now includes enterprise readiness static contract
- bootstrap documentation aligned with enterprise candidate posture

## Honest status
V4 improves enterprise-operational readiness, but full `100/100` still requires provisioned runtime evidence.


## V13 Phase-1 Gap Closure Addendum
- قطاع STRICT صار يملك تقارير work queues وSLA escalation للموافقات عبر أوامر إدارة.
- تم تشديد دور المدير المالي للمزرعة داخل دورات Petty Cash / Supplier Settlement / Fiscal Close.
- المزرعة البعيدة الصغيرة أصبحت قابلة للحجب في بعض إجراءات STRICT عند تأخر المراجعة القطاعية.
- تمت إضافة legal hold / restore commands وتحسين سياسات رفع الملفات وفحص التوقيع والبصمة ومنع التكرار المؤقت.
