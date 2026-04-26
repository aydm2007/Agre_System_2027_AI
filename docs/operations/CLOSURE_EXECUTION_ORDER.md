# Closure Execution Order

1. `make bootstrap-closure-env`
2. تفعيل البيئة:
   - `source .venv-closure/bin/activate`
3. ضبط متغيرات PostgreSQL الإنتاجية/الاختبار.
4. `python backend/manage.py verify_static_v21`
5. `python backend/manage.py run_closure_evidence_v21`
6. `python backend/manage.py verify_release_gate_v21`
7. مراجعة الأدلة تحت `docs/evidence/closure/<timestamp>/` أو `docs/evidence/closure/latest/`.
8. لا ترفع الدرجة النهائية إلى 98–99 إلا إذا كانت أوامر PostgreSQL + backend targeted suites + frontend lint/test/build كلها `PASS`.
