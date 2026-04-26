# الوضع المزدوج — YECO Hybrid Doctrine
> العقيدة الحاكمة لآلية التبديل بين الوضع البسيط والوضع الصارم.

## 1. مفتاح التحكم (SystemSettings Toggle)
- كل فحص مالي إجباري يتحقق من `SystemSettings.strict_erp_mode`.
- `True` (الصارم): يحظر العملية → `raise ValidationError`.
- `False` (المراقبة): يسمح بالعملية + يُنشئ `VarianceAlert` للمقر.
- `SystemSettings` = Singleton → `SystemSettings.get_settings()`.

## 2. قواعد لا تتغير بالوضع (Hard Blocks دائماً)
| القاعدة | الحالة |
|---------|--------|
| لا IoT → مدخلات يدوية فقط | ثابت |
| اللجان ≥ 3 أعضاء (الطواف، الشراك) | ثابت |
| `idempotency_key` إجباري | ثابت |
| `farm_id` على كل صف عملياتي | ثابت |
| الإيرادات → حساب القطاع (لا إنفاق مباشر) | ثابت |

## 3. قواعد مرنة حسب الوضع (Shadow)
- تجاوز ميزانية `DailyLog`:
  - **صارم**: `ValidationError`
  - **مراقبة**: يحسب الانحراف + `ShadowVarianceEngine` → `VarianceAlert`
- الحد المسموح قبل الإنذار: `SystemSettings.allowed_variance_percentage`.

## 4. خريطة الوحدات

| الوحدة | مراقبة (`false`) | صارم (`true`) |
|--------|:-:|:-:|
| لوحة التحكم | ✅ | ✅ |
| صندوق الاعتمادات | ✅ | ✅ |
| انحرافات التكاليف | ✅ | ✅ |
| السجل اليومي | ✅ | ✅ |
| التقارير | ✅ | ✅ |
| الرؤية التجارية | ❌ | ✅ |
| المبيعات | ❌ | ✅ |
| المالية | ❌ | ✅ |
| الخزينة | ❌ | ✅ |
| الموظفين | ❌ | ✅ |

> استثناء: المستخدمون مع `isFinanceLeader` يرون الوحدات المالية **دائماً**.

## 5. قواعد الانتقال
- التبديل بين الأوضاع **لا يتطلب migration بيانات**.
- الباكند يُعالج كل البيانات المالية بغض النظر عن الوضع.
- API: `GET /api/v1/system-mode/` (public) → `{strict_erp_mode, mode_label}`.
- Frontend: `AuthContext.js` → `strictErpMode`. `Nav.jsx` + `app.jsx` تفرض الوضع.
- فشل جلب `/system-mode/`: default = `false` (مقاومة ضعف الشبكة).

## 6. الأنماط الصارمة (Strict UI Guards)
- عمليات عالية المخاطر (Hard Close, Treasury): تتطلب صلاحيات `is_strict`.
- تنبيه بصري: `bg-amber-100` + أيقونة `Lock`.
- تأكيد إجباري (Modal/confirm) قبل التنفيذ.
