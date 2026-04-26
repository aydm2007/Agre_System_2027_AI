# سياسة اشتقاق Word من التوثيق الحي

> Reference class: public documentation policy.
> Canonical format: HTML/MkDocs.
> This file governs delivery-copy derivation only. It is not a replacement for `AGENTS.md` or doctrine.

## 1. القاعدة الأساسية

- النسخة الحية والمرجعية من الأدلة هي `HTML/MkDocs`
- أي نسخة `Word` أو `PDF` هي نسخة مشتقة فقط
- لا يتم تحرير `Word` مباشرة ثم إعادة اعتباره source of truth

## 2. لماذا هذه السياسة؟

لأنها تقلل:

- drift بين النسخ
- الروابط المكسورة
- اختلاف الادعاءات بين public docs وcanonical docs
- تكلفة الصيانة عند كل تغيير في الكود أو المرجع

## 3. ما الذي يمكن تصديره؟

النسخ المسموح اشتقاقها:

- `docs/user_guide_ar.md`
- `docs/developer_guide_ar.md`

ويمكن لاحقًا اشتقاق نسخ رسمية من مستندات عامة أخرى عند الحاجة.

## 4. metadata المطلوبة في النسخة المشتقة

أي نسخة Word مشتقة يجب أن تحتوي بوضوح على:

- اسم الدليل
- تاريخ التوليد
- عبارة:
  - `هذه نسخة مشتقة من المرجع HTML canonical`
- path أو source reference إلى ملف markdown الأصلي

## 5. سياسة التحديث

عند تعديل الدليل الحي:

1. يحدث markdown أولًا
2. تُراجع الروابط والمحتوى
3. تمر اختبارات docs اللازمة
4. بعدها فقط يُعاد اشتقاق Word

إذا لم تُشتق النسخة Word بعد، يبقى HTML هو المرجع الوحيد الصحيح.

## 6. التوليد في هذه البيئة

هذه البيئة لا توفر حاليًا أداة export مثبتة مثل `pandoc`.

لذلك:

- تم اعتماد policy والتجهيز البنيوي
- لكن توليد `.docx` الفعلي يعتمد على توفر أداة export في بيئة النشر أو بيئة التسليم

## 7. الأدوات الموصى بها

الأدوات المناسبة لاحقًا:

- `pandoc` لتوليد `docx` من markdown
- أو pipeline موحد في CI/CD إذا تم اعتماده لاحقًا

### مثال policy-only

```bash
pandoc docs/user_guide_ar.md -o dist/docs/user_guide_ar.docx
pandoc docs/developer_guide_ar.md -o dist/docs/developer_guide_ar.docx
```

هذه الأوامر ليست canonical بحد ذاتها؛ canonical هو مضمون markdown المصدر.

## 8. ما الذي لا يجوز؟

- إنشاء Word مستقل ثم تحريره يدويًا بعيدًا عن HTML
- claim في Word غير موجود في المصدر الحي
- استخدام نسخة Word أقدم من HTML ثم اعتبارها المرجع الحالي
