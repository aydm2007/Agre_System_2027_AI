# أوامر التحقق الإجبارية — Verification Commands
> [!WARNING]
> كل هذه الأوامر إجبارية قبل أي إطلاق. أي فشل = حاجز إطلاق (BLOCK).

## Working Directory Convention
- أوامر `manage.py`: CWD = `backend/`
- أوامر `scripts/`: CWD = جذر المستودع

---

## 1. أوامر Schema & Migrations
```bash
python manage.py showmigrations          # لا يوجد [ ] في تطبيقات الأعمال
python manage.py migrate --plan          # لا migrations معلقة
python manage.py check                   # لا أخطاء تكوين
```

## 2. أوامر الامتثال الفني
```bash
python scripts/check_no_float_mutations.py       # صفر float() في المالية
python scripts/check_idempotency_actions.py       # @idempotent في كل ViewSet مالي
python scripts/verification/detect_zombies.py     # صفر zombie tables
python scripts/verification/detect_ghost_triggers.py  # صفر ghost triggers
```

## 3. أوامر المحاور السيادية
```bash
python backend/scripts/check_zakat_harvest_triggers.py     # بوابة الزكاة
python backend/scripts/check_solar_depreciation_logic.py   # إهلاك الطاقة الشمسية
```

## 4. اختبارات Backend
```bash
python backend/manage.py test smart_agri.core.tests.test_zakat_policy_v2
python backend/manage.py test smart_agri.core.tests.test_labor_estimation_api --keepdb --noinput
python backend/manage.py test smart_agri.finance.tests.test_fiscal_lifecycle --keepdb --noinput
python backend/manage.py test smart_agri.core.tests.test_fiscal_close_e2e --keepdb --noinput
```

## 5. اختبارات Frontend
```bash
npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogResources.test.jsx --run
npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run
```

## 6. اختبارات E2E
> في Windows: استخدم `--workers=1` لتجنب عدم الاستقرار.
```bash
npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1
npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1
npm --prefix frontend run test:e2e -- tests/e2e/sales_financial_lifecycle.spec.js --workers=1
npm --prefix frontend run test:e2e -- tests/e2e/finance.spec.js --workers=1
```

## 7. أوامر الحوكمة غير الوظيفية
```bash
python scripts/verification/check_compliance_docs.py
python scripts/verification/check_backup_freshness.py
python scripts/verification/check_restore_drill_evidence.py
```

## 8. Runtime Probes (Fail-Fast)
```bash
python manage.py shell -c "from smart_agri.core.models.hr import Employee; Employee.objects.values_list('id','category')[:1]"
python manage.py shell -c "from smart_agri.core.models.log import IdempotencyRecord; IdempotencyRecord.objects.values_list('id','response_status','response_body')[:1]"
python manage.py shell -c "from smart_agri.core.models.log import DailyLog; DailyLog.objects.values_list('id','variance_status')[:1]"
python manage.py shell -c "from smart_agri.finance.models import FiscalPeriod; FiscalPeriod.objects.values_list('id','status')[:1]"
python manage.py shell -c "from smart_agri.core.models import Farm; Farm.objects.values_list('id','tier')[:1]"
python manage.py shell -c "from smart_agri.accounts.models import RoleDelegation; print('RoleDelegation table exists:', RoleDelegation.objects.model._meta.db_table)"
```

---

## حواجز الإطلاق (Release Blockers)
| الحالة | النتيجة |
|--------|---------|
| Migration معلق | **BLOCK** |
| `float()` في مسار مالي | **BLOCK** |
| Endpoint مالي بدون idempotency | **BLOCK** |
| Zombie table | **BLOCK** |
| فجوة زكاة أو إهلاك شمسي | **BLOCK** |
| فجوة حوكمة (tiering/delegation) | **BLOCK** |
| وثيقة غير وظيفية مفقودة | **BLOCK** |
| دليل DR أقدم من 45 يوماً | **BLOCK** |
