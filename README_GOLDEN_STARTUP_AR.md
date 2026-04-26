# الدليل الذهبي للتشغيل المحلي

هذا الدليل يصف السلوك المعتمد لـ `start_dev_stack.bat` بعد تحديثه ليصبح launcher محلي كامل ومتسق مع `AGENTS.md`.

## السلوك الافتراضي

التشغيل الافتراضي أصبح **Full Stack**:

- Django backend
- Vite frontend
- Celery worker
- Celery beat

المتطلبات المحلية:

- PostgreSQL جاهزة مسبقًا ومُدارة خارج السكربت
- Redis مطلوبة للـ async stack
- Node.js `>= 20`
- npm `>= 10`

## قواعد مهمة

- تحميل بيئة قاعدة البيانات يتم عبر:
  - `scripts/windows/load_backend_db_env.cmd`
- لا يوجد قتل واسع للمنافذ. الإيقاف يستهدف فقط عمليات هذا المستودع.
- لا يوجد fallback صامت إلى `CELERY_TASK_ALWAYS_EAGER=True` داخل التشغيل الافتراضي.
- `runserver --noreload` هو الافتراضي للاستقرار.
- `reload` خيار تشخيصي يدوي فقط.

## الأوامر الأساسية

- فحص شامل بدون تشغيل:
  - `start_dev_stack.bat check`
- فحص تشخيصي بدون Redis/Celery:
  - `start_dev_stack.bat check app-only`
- تشغيل محلي كامل:
  - `start_dev_stack.bat local migrate`
- تشغيل محلي كامل مع autoreload:
  - `start_dev_stack.bat local reload`
- تحقق canonical بدون تشغيل:
  - `start_dev_stack.bat verify`
- تحقق واختبارات وبناء بدون تشغيل:
  - `start_dev_stack.bat test`

## سلوك Redis

- إذا كانت Redis تعمل على `127.0.0.1:6379` فسيتم استخدامها كما هي.
- إذا لم تكن تعمل لكن `redis-server` متاح في `PATH` فسيحاول السكربت تشغيلها محليًا.
- إذا لم تكن متاحة، سيفشل التشغيل الكامل برسالة علاج واضحة.

## سلوك PostgreSQL

- السكربت لا يقوم بإنشاء PostgreSQL أو تشغيلها.
- لكنه يتحقق من جاهزية البيئة وقابلية أوامر Django التالية:
  - `manage.py check`
  - `manage.py showmigrations --plan`
  - `manage.py migrate --plan`

## ملاحظات تشغيلية

- `check` و`verify` و`test` لا تطلق نوافذ تشغيل.
- `app-only` مخصص للتشخيص وليس هو الوضع المرجعي الكامل.
- readiness النهائية بعد التشغيل تُقاس عبر:
  - `/api/health/live/`
  - `/api/health/ready/`

## ملاحظة صريحة

هذا launcher يحسن التشغيل المحلي ويجعله أقرب إلى الحقيقة التشغيلية للنظام، لكنه لا يغيّر canonical release authority ولا يغني عن أوامر التحقق المعتمدة داخل evidence وrelease gates.
