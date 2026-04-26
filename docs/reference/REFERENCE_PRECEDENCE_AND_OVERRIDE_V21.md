# Reference Precedence and Override Policy (V21)

## الهدف
حل التعارض بين `PRD` و`AGENTS.md` وملفات المهارات والوثائق التنفيذية والكود الحالي، بحيث تصبح الأولوية واضحة ولا يتحول المشروع إلى مرجعيات متنافسة.

## الترتيب الحاكم
1. **PRD** يحكم حقيقة المنتج والأعمال والحوكمة ومعايير القبول.
2. **AGENTS.md الأعمق** يحكم فقط داخل subtree الخاص به.
3. **AGENTS.md الجذر** يحكم بروتوكول التنفيذ على مستوى الريبو.
4. **Canonical skills** توفر عدسات تنفيذ وتحقق متخصصة، لكنها لا تغير منطق المنتج.
5. **Doctrine / operations / reports** تشرح وتفصل وتوثق، لكنها لا تنقض الأعلى.
6. **الكود الحالي** هو الحقيقة التنفيذية المؤقتة فقط، ويُعد غير مطابق إذا خالف ما فوقه.

## قواعد حسم التعارض
### 1) إذا تعارض Skill مع PRD
يُرفض تطبيق الـ Skill أو يُقيّد. مثال: أي إصلاح dev-only غير آمن لا يجوز أن يمر إلى release إذا ناقض `PRD` أو `AGENTS`.

### 2) إذا تعارض AGENTS مع PRD
يُرفع التعارض صراحة ويُختار المسار الأكثر محافظة على الحوكمة والجاهزية والأدلة، مع تحديث الوثيقة الأدنى.

### 3) إذا تعارض الكود مع المرجعية
يُعتبر الكود **gap** لا مرجعًا. ويجب إصلاحه أو توثيق الانحراف بوصفه debt/blocked.

### 4) إذا وجدت نسختان من skill واحدة
يُستخدم فقط الملف المسمى في `SKILLS_CANONICALIZATION_V21.yaml` بوصفه canonical، وما عداه `deprecated` أو `archive_candidate`.

## قواعد خاصة
### PRD baseline
- المرجع النشط للمنتج هو `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`.
- أي ملفات PRD أقدم تبقى historical baselines للمقارنة أو التتبع فقط، ولا يجوز اعتبارها أعلى من V21 في قرارات التنفيذ الجديدة.

### SIMPLE vs STRICT
- المرجع الحاكم هنا: `PRD` ثم `AGENTS.md` ثم `agri_guardian` و`financial_integrity`.
- لا يكفي إخفاء UI؛ يجب وجود **backend enforcement** واختبارات تدعم ذلك.

### Smart Card contract
- العقد canonical لقراءة التنفيذ اليومي هو `smart_card_stack`.
- الحقول legacy مثل `task_focus` و`plan_metrics` و`control_metrics` و`variance_metrics` و`ledger_metrics` و`health_flags` تبقى compatibility-only، ولا يجوز أن تصبح أساسًا لسطوح جديدة.

### Ledger / Finance
- المرجع الحاكم: `PRD` ثم `financial_integrity` ثم `AGENTS.md`.
- يمنع أي skill أو runbook يسمح بتجاوز `append-only ledger` أو `reversal-based correction`.

### Schema / DB
- المرجع الحاكم: `PRD` ثم `AGENTS.md` ثم `schema_guardian/SKILL_V2.md` و`schema_sentinel/SKILL_NEW.md` و`sql_sync/SKILL.md`.

### Startup / Local Repair
- `startup_sentinel` **تشخيصي فقط**.
- لا يجوز نسخه إلى قواعد release أو اعتباره skill معيارية نهائية للإنتاج.

## قرار التبني النهائي
لأي merge أو release candidate:
- لا يُكتفى بوجود هذه الوثائق.
- يجب أن ترتبط كل قاعدة حساسة بـ:
  - code anchor
  - test anchor
  - gate anchor
  - evidence anchor

## ما الذي يرفعه هذا الملف؟
يرفع قابلية التنفيذ المرجعية ويمنع التضارب، لكنه لا يرفع التقييم بمفرده إلى مستوى 95+ ما لم تتبعه مصفوفات واختبارات وتشغيل.
