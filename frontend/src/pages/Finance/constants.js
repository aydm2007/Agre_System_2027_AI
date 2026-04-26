export const ACCOUNT_CODES = [
  { code: '4000-OVERHEAD', label: 'نفقات عامة' },
  { code: '1000-LABOR', label: 'تكلفة العمالة' },
  { code: '2000-MATERIAL', label: 'تكلفة المواد' },
  { code: '3000-MACHINERY', label: 'تكلفة الآليات' },
  { code: '2100-SECTOR-PAY', label: 'حساب القطاع الإنتاجي' },
]

export const ACCOUNT_LABELS = {
  '1000-LABOR': { name: 'تكلفة العمالة', color: 'amber' },
  '2000-MATERIAL': { name: 'تكلفة المواد', color: 'emerald' },
  '3000-MACHINERY': { name: 'تكلفة الآليات', color: 'blue' },
  '4000-OVERHEAD': { name: 'نفقات عامة', color: 'purple' },
  '5000-REVENUE': { name: 'إيرادات المبيعات', color: 'green' },
  '1200-RECEIVABLE': { name: 'ذمم مدينة', color: 'cyan' },
  '1300-INV-ASSET': { name: 'أصول المخزون', color: 'orange' },
  '6000-COGS': { name: 'تكلفة البضاعة', color: 'red' },
  '1400-WIP': { name: 'أعمال تحت التنفيذ', color: 'indigo' },
  '7000-DEP-EXP': { name: 'مصروف الاستهلاك', color: 'gray' },
  '1500-ACC-DEP': { name: 'الاستهلاك المتراكم', color: 'slate' },
  '2000-PAY-SAL': { name: 'رواتب مستحقة', color: 'pink' },
  '2100-SECTOR-PAY': { name: 'حساب القطاع الإنتاجي', color: 'rose' },
  '9999-SUSPENSE': { name: 'حساب معلق', color: 'rose' },
}
