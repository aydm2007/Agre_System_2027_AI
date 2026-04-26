# AgriAsset Reference Pack (V21)

هذه الحزمة ليست بديلًا عن إصلاح الكود أو التشغيل أو الاختبارات. هي طبقة مرجعية نشطة لتقليل التعارض بين `PRD` و`AGENTS.md` والمهارات، ولرفع جودة التقييمات والمراجعات والبرومبتات التشغيلية.

## ماذا تحتوي الحزمة؟
- `docs/reference/REFERENCE_MANIFEST_V21.yaml`
- `docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`
- `docs/reference/PHASE_INTAKE_PROTOCOL_V21.md`
- `docs/reference/SKILLS_CANONICALIZATION_V21.yaml`
- `docs/reference/READINESS_MATRIX_V21.yaml`
- `docs/reference/ROLE_PERMISSION_MATRIX_V21.md`
- `docs/reference/ATTACHMENT_POLICY_MATRIX_V21.yaml`
- `docs/reference/RUNTIME_PROOF_CHECKLIST_V21.md`
- `docs/reference/CANONICAL_UNIFIED_PROMPT_V21.md`
- `docs/reference/REFERENCE_LAYER_AUDIT_V21.md`
- `docs/reference/IMPLEMENTATION_GAPS_TO_100_V21.md`

## قاعدة مهمة: precedence ليس هو read order
- `REFERENCE_MANIFEST_V21.yaml` هو نقطة الدخول المرجعية الأولى وخريطة التحميل.
- `REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md` هو المرجع الحاكم لحل التعارض.
- الـ matrices وملفات readiness وaudit هي مراجع مساعدة للفحص والتنفيذ، لكنها لا تعلو على:
  1. `PRD V21`
  2. `deeper AGENTS.md` داخل subtree المستهدف
  3. `root AGENTS.md`
  4. `canonical skills`
  5. doctrine/reference aids
  6. code

## كيف تستخدم الحزمة؟
1. ابدأ بـ `REFERENCE_MANIFEST_V21.yaml` لمعرفة ما الذي يجب قراءته.
2. استخدم `PHASE_INTAKE_PROTOCOL_V21.md` عندما تبدأ مرحلة جديدة أو تريد تحويل طلب جديد إلى phase decision-complete.
3. إذا ظهر تعارض، عد فورًا إلى `REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`.
4. لا ترفع doctrine أو matrices فوق `AGENTS.md` إلا إذا كان الـ manifest يذكر override صريحًا.
5. اعتبر skills عدسات تنفيذ فقط، لا طبقة truth أعلى.
6. لا تمنح أكثر من `95/100` دون `runtime proof` و`release gates` ونتائج اختبارات فعلية.

## كيف تبني prompt مراجعة أو تقييم متوافق مع AgriAsset؟
استخدم البرومبتات كـ execution scaffold فقط. يجب أن تلتزم بترتيب المرجعية الفعلي، لا أن تخترع precedence جديدة.

### البرومبت الموحد canonical
- الملف المعتمد للاستخدام اليومي هو:
  - `docs/reference/CANONICAL_UNIFIED_PROMPT_V21.md`
- هذا الملف:
  - يجمع `Review Mode` و`Implementation Mode`
  - يمنع الادعاء الثابت بـ `100/100`
  - يلزم `BLOCKED` عند غياب runtime evidence
  - يفرض الاستكشاف قبل التنفيذ
  - يبقي البرومبت scaffold تنفيذيًا لا طبقة truth أعلى من `PRD` أو `AGENTS.md`

### الصيغة المختصرة canonical
1. اقرأ `PRD V21`.
2. اقرأ `deeper AGENTS.md` إن وجد داخل المسار المستهدف.
3. اقرأ `root AGENTS.md`.
4. اقرأ `canonical skills`.
5. اقرأ doctrine/reference matrices/readiness docs كطبقة فحص ودعم.
6. راجع الكود والاختبارات.

### إلزامات أي prompt جيد
- اذكر بوضوح الفرق بين:
  - المرجع الحاكم بالprecedence
  - ملفات الفحص والقراءة المطلوبة
- استخدم `REFERENCE_MANIFEST_V21.yaml` كخريطة تحميل، لا كبديل عن precedence.
- استخدم `REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md` لحل التعارض.
- اطلب دائمًا:
  - `code anchor`
  - `test anchor`
  - `gate anchor`
  - `evidence anchor`
- عالج تعذر إنتاج الأدلة التشغيلية كحالة `BLOCKED` لا `PASS`.
- امنع `100/100` عند وجود:
  - reference conflict
  - active debt في الطبقة النشطة
  - blocked runtime proof
  - gate failure

### أمثلة prompts
#### 1. Prompt تقييم صارم
```md
أنت تعمل على مشروع AgriAsset (YECO Edition). اتبع المرجعية بالترتيب الحاكم التالي:
1. PRD V21
2. deeper AGENTS.md داخل المسار المستهدف إن وجد
3. root AGENTS.md
4. canonical skills
5. doctrine/reference matrices/readiness docs
6. existing code

استخدم REFERENCE_MANIFEST_V21.yaml كخريطة تحميل فقط، واستخدم REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md لحل أي تعارض.

قيّم بصرامة evidence-first. لا تمنح 100/100 مع reference conflict أو debt حي أو blocked runtime proof أو gate failure.
اربط كل claim بـ code anchor + test anchor + gate anchor + evidence anchor.
إذا تعذر إنتاج evidence runtime أو smoke أو gate فعامل الحالة كـ BLOCKED.
```

#### 2. Prompt مراجعة تكامل
```md
قيّم تكامل هذا المسار مع SIMPLE/STRICT والحوكمة والمالية وفق PRD V21 وAGENTS.md.
ابدأ بذكر المرجع الذي اعتمدت عليه، ثم أعطني:
1. التقييم الصارم من 100
2. الفجوات المرجعية
3. الفجوات التشغيلية
4. الفجوات بين SIMPLE وSTRICT
5. الفجوات في الأدوار والحوكمة
6. خطة decision-complete للإغلاق
لا تمنح PASS إذا كانت الأدلة التشغيلية blocked.
```

#### 3. Prompt إغلاق readiness
```md
تعامل مع هذا الطلب كـ readiness closure task.
لا تعتبر الوثائق وحدها كافية. شغّل checks/gates/tests المطلوبة، واربط الحكم النهائي بالأدلة الفعلية.
إذا كانت أي خطوة runtime أو release gate غير قابلة للتنفيذ، فالحكم BLOCKED لا PASS.
```

## التقييم الصارم
- `REFERENCE_MANIFEST_V21.yaml` وحده: لا يكفي لإغلاق الجاهزية.
- الحزمة المرجعية كاملة: قوية جدًا كطبقة تنظيمية، لكنها لا تثبت الجاهزية الإنتاجية وحدها.
- الوصول إلى `100/100`: يحتاج كود + اختبارات + runtime proof + release gates، لا وثائق فقط.

## ملاحظات صريحة
- أكبر فائدة للحزمة: تحويل المرجع من ملفات قوية ولكن متفرقة إلى نظام مرجعي منظم وقابل للتفعيل.
- أكبر فشل شائع في البرومبتات: خلط precedence مع read order.
- أكبر فشل شائع في التقييمات: إعطاء `PASS` عندما تكون الأدلة التشغيلية غير متاحة أصلًا.
