# AgriAsset V25 Reference Pack (V21)

هذه الحزمة ليست بديلًا عن إصلاح الكود والتشغيل والاختبارات، لكنها **طبقة مرجعية حاكمة** مصممة لتقليل التعارض بين `PRD` و`AGENTS.md` وملفات المهارات داخل `.agent/skills`، ورفع جاهزية التوثيق المرجعي إلى مستوى أعلى وأكثر قابلية للتنفيذ.

## ماذا تحتوي الحزمة؟
- `docs/reference/REFERENCE_MANIFEST_V21.yaml`
- `docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`
- `docs/reference/SKILLS_CANONICALIZATION_V21.yaml`
- `docs/reference/READINESS_MATRIX_V21.yaml`
- `docs/reference/ROLE_PERMISSION_MATRIX_V21.md`
- `docs/reference/ATTACHMENT_POLICY_MATRIX_V21.yaml`
- `docs/reference/RUNTIME_PROOF_CHECKLIST_V21.md`
- `docs/reference/REFERENCE_LAYER_AUDIT_V21.md`
- `docs/reference/IMPLEMENTATION_GAPS_TO_100_V21.md`

## التقييم الصارم
- `REFERENCE_MANIFEST_V21.yaml` وحده: **74/100**
- الحزمة المرجعية كاملة: **94/100**
- الوصول إلى **100/100**: غير ممكن بالوثائق فقط؛ يحتاج **إغلاقًا في الكود + اختبارات + runtime proof + release gates**.

## كيف تُستخدم؟
1. انسخ مجلد `docs/reference` إلى جذر مشروع الإصدار 25.
2. اعتبر `REFERENCE_MANIFEST_V21.yaml` نقطة الدخول المرجعية الأولى.
3. طبّق `REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md` لحل أي تعارض بين `PRD` و`AGENTS.md` والمهارات.
4. اعتمد `SKILLS_CANONICALIZATION_V21.yaml` لتحديد المهارات canonical والمهارات deprecated أو advisory-only.
5. اربط `READINESS_MATRIX_V21.yaml` مع أوامر التحقق والاختبارات والـ gates الموجودة فعليًا في المشروع.
6. حوّل `ROLE_PERMISSION_MATRIX_V21.md` و`ATTACHMENT_POLICY_MATRIX_V21.yaml` إلى اختبارات وتنفيذ backend/frontend.
7. لا تمنح المشروع أكثر من **95+** إلا بعد إكمال `RUNTIME_PROOF_CHECKLIST_V21.md` بنجاح.

## ملاحظات صريحة
- هذه الحزمة صالحة لرفع جودة المرجعية ومنع التضارب، لكنها **لا تثبت الإنتاجية وحدها**.
- أكبر فائدتها: تحويل المرجع الحالي من وثائق قوية ولكن متفرقة إلى **نظام مرجعي منظم وقابل للتفعيل**.
- أكبر نقص باقٍ بعد اعتمادها: التنفيذ الفعلي للحدود بين `SIMPLE/STRICT`، وإغلاق الأمن، وتشغيل الـ stack وإثباته.
