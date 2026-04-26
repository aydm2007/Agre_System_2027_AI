# خطة الإغلاق النهائية V37

هذه الخطة تربط كل فجوة متبقية بأمر إثبات واضح ومعيار إغلاق محدد. لا تُعد الفجوة مغلقة حتى يظهر دليل PASS محفوظ داخل `docs/evidence/closure/`.

## 1) PostgreSQL Runtime Closure
- **الفجوة:** لا يوجد إثبات حي على PostgreSQL.
- **الأوامر:**
  - `python backend/manage.py check`
  - `python backend/manage.py showmigrations --plan`
  - `python backend/manage.py migrate --plan`
  - `python backend/manage.py runtime_probe_v21`
  - `python backend/manage.py release_readiness_snapshot`
- **شرط الإغلاق:** جميع الأوامر تحفظ مخرجات PASS على PostgreSQL حي، ويظهر `vendor=postgresql` واسم قاعدة البيانات ومسار الإعدادات الصحيح.

## 2) Attachment / Evidence Closure
- **الفجوة:** أوامر المرفقات والمراجعات البعيدة غير مثبتة تشغيليًا.
- **الأوامر:**
  - `python backend/manage.py scan_pending_attachments`
  - `python backend/manage.py report_due_remote_reviews`
  - `python backend/manage.py archive_due_attachments --dry-run`
  - `python backend/manage.py purge_expired_transient_attachments --dry-run`
- **شرط الإغلاق:** PASS مع قاعدة PostgreSQL مهيأة ووجود snapshots محفوظة تحت `docs/evidence/closure/attachments/`.

## 3) Worker / Outbox Closure
- **الفجوة:** الـ outbox موجود لكن الإثبات التشغيلي غير مغلق بالكامل.
- **الأوامر:**
  - `python backend/manage.py dispatch_outbox`
  - `python backend/manage.py retry_dead_letters`
  - `python backend/manage.py purge_dispatched_outbox --dry-run`
  - endpoint `/api/health/integration-hub/outbox/`
- **شرط الإغلاق:** PASS مع worker/beat شغالين ووجود snapshot queue + dead-letter counts.

## 4) Frontend Quality Closure
- **الفجوة:** lint وfrontend tests غير مغلقة.
- **الأوامر:**
  - `npm ci`
  - `npm run lint`
  - `npm run test -- --run`
  - `npm run build`
- **شرط الإغلاق:** PASS كامل دون تجاوزات أو تعطيل للقواعد.

## 5) Backend Test Closure
- **الفجوة:** backend tests غير مثبتة تشغيلًا.
- **الأوامر:**
  - `python backend/manage.py test smart_agri.core.tests.test_route_breach_middleware --noinput`
  - `python backend/manage.py test smart_agri.finance.tests.test_farm_finance_authority_service --noinput`
  - `python backend/manage.py test smart_agri.core.tests.test_runtime_probe_v21 --noinput`
- **شرط الإغلاق:** PASS محفوظ لكل suite داخل `docs/evidence/closure/backend-tests/`.

## 6) Release Gate Closure
- **الفجوة:** release gate النهائي غير مثبت بالكامل.
- **الأوامر:**
  - `make verify-static`
  - `make verify-runtime-proof`
  - `make verify-release-gate-fast`
- **شرط الإغلاق:** PASS لكل target مع حفظ المخرجات وعدم الاعتماد على ملفات مؤقتة.

## 7) قرار الإطلاق
- **لا يوصى** بالانتقال إلى 98–99% إلا بعد إغلاق البنود 1–6 بالأدلة.
- **الوصول الدفاعي المستهدف:**
  - 95–96% بعد إغلاق PostgreSQL + tests + lint + release gate
  - 98–99% فقط بعد stack حي كامل مع PostgreSQL + Redis + worker + beat + snapshots محفوظة
