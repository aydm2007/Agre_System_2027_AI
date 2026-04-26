# Integration Status V21

تم دمج الحزمة المرجعية داخل المشروع تحت `docs/reference/`.

## الهدف
توحيد المرجعية التنفيذية بين:
- PRD
- AGENTS.md
- subtree AGENTS.md إن وجدت
- `.agent/skills`
- الكود الحالي

## نقطة الدخول
ابدأ من:
- `docs/reference/REFERENCE_MANIFEST_V21.yaml`

## التنبيه الحاكم
هذه الطبقة المرجعية ترفع الانضباط والتتبع، لكنها لا تمنح 100/100 وحدها.
الدرجة النهائية تعتمد أيضًا على:
- إصلاحات الكود
- الاختبارات
- runtime proof
- release gates
