"""
دليل حدود المسؤوليات بين Python و SQL.

FORENSIC AUDIT DOCUMENTATION (2026-01-24): Phase 6

يحدد هذا الدليل بوضوح ما يديره كل من Python و SQL لتجنب
التضارب في المسؤوليات (Split-Brain) الذي يسبب أخطاء سكوتة.
"""

# =============================================================================
# حدود المسؤوليات - RESPONSIBILITY BOUNDARIES
# =============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                           دليل المسؤوليات                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║     Python هو المصدر الوحيد للحقيقة (Single Source of Truth)        ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                                                             │
│  المسؤولية                          المالك     الملاحظات                  │
│  ────────────────────────────────────────────────────────────────────────── │
│  تحديث ItemInventory.qty            Python    F('qty') + delta            │
│  تحديث ItemInventoryBatch           Python    مع التحقق من الصلاحية       │
│  تحديث LocationTreeStock            Python    عبر TreeStockManager        │
│  حساب التكاليف                      Python    مع STRICT_MODE=True        │
│  التحقق من المخزون السالب           Python    ValueError قبل التحديث     │
│  إنشاء TreeStockEvent               Python    لكل حركة مخزون أشجار       │
│                                                                             │
│  ────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║     SQL (Triggers & Constraints) - خط الدفاع الأخير فقط             ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                                                             │
│  المسؤولية                          النوع      الملاحظات                  │
│  ────────────────────────────────────────────────────────────────────────── │
│  منع المخزون السالب                 CHECK     iteminventory_qty_check    │
│  منع الحركات الصفرية                CHECK     stockmovement_delta_not_zero│
│  ضمان unicness للمخزون             UNIQUE    farm_location_item_uc       │
│  تحديث updated_at تلقائياً          TRIGGER   (احتياطي)                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""


# =============================================================================
# التريغرات المفعّلة - ACTIVE TRIGGERS
# =============================================================================

TRIGGERS_DOCUMENTATION = {
    "core_stockmovement_after_insert": {
        "table": "core_stockmovement",
        "event": "AFTER INSERT",
        "purpose": "تحديث احتياطي للمخزون (Python هو الأساسي)",
        "status": "ACTIVE - BACKUP ONLY",
        "notes": """
            تم تعديله في 2026-01-24 لدعم location_id.
            Python يدير المخزون أولاً، والتريغر احتياطي فقط.
            في حالة التضارب، Python يفوز.
        """,
    },
    "core_stockmovement_after_delete": {
        "table": "core_stockmovement",
        "event": "AFTER DELETE",
        "purpose": "عكس تأثير الحركة المحذوفة",
        "status": "ACTIVE",
        "notes": "يعمل بشكل صحيح مع location_id",
    },
    "tree_stock_event_after_insert": {
        "table": "core_treestockevent",
        "event": "AFTER INSERT",
        "purpose": "تحديث إحصائيات الأشجار",
        "status": "ACTIVE",
        "notes": "Python يدير TreeStockEvent، التريغر للإحصائيات فقط",
    },
}


# =============================================================================
# القيود المفعّلة - ACTIVE CONSTRAINTS
# =============================================================================

CONSTRAINTS_DOCUMENTATION = {
    "iteminventory_qty_check": {
        "table": "core_item_inventory",
        "type": "CHECK",
        "expression": "qty >= 0",
        "purpose": "خط دفاع أخير ضد المخزون السالب",
        "notes": "Python يمنع السالب أولاً، CHECK احتياطي",
    },
    "stockmovement_delta_not_zero": {
        "table": "core_stockmovement",
        "type": "CHECK",
        "expression": "qty_delta <> 0",
        "purpose": "منع الحركات الفارغة",
        "notes": "تجنب تضخم الجدول بسجلات لا معنى لها",
    },
    "iteminventory_farm_location_item_uc": {
        "table": "core_item_inventory",
        "type": "UNIQUE",
        "expression": "(farm_id, COALESCE(location_id, -1), item_id)",
        "purpose": "منع تكرار سجلات المخزون",
        "notes": "يدعم location_id = NULL",
    },
}


# =============================================================================
# قواعد الاستخدام - USAGE RULES
# =============================================================================

"""
قواعد يجب اتباعها:

1. ❌ لا تستخدم F('qty') + delta في Python إذا كان التريغر يفعل نفس الشيء
   ✅ الآن: Python فقط يحدث qty

2. ❌ لا تنتظر التريغر (time.sleep) - هذا سباق (race condition)
   ✅ الآن: Python ينشئ السجل مباشرة

3. ❌ لا ترجع Decimal("0") عند غياب إعدادات التكلفة
   ✅ الآن: ارفع ValueError مع رسالة واضحة

4. ❌ لا تقسم المخزون بين location=NULL و location=X
   ✅ الآن: التريغر يدعم location_id بشكل صحيح

5. ❌ لا تنشئ خدمات ضخمة (>400 سطر)
   ✅ الآن: Tree services مقسمة إلى 4 خدمات متخصصة
"""
