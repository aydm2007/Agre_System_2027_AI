const hasArabic = (value) => /[\u0600-\u06ff]/.test(String(value || ''))

const normalizeKey = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[()]/g, '')
    .replace(/[\s/-]+/g, '_')

const splitCountSuffix = (value) => {
  const raw = String(value || '').trim()
  const match = raw.match(/^(.*?)(?:\s*\((\d+)\))$/)
  if (!match) return { base: raw, count: null }
  return { base: match[1].trim(), count: match[2] }
}

const withCount = (label, count) => (count ? `${label} (${count})` : label)

export const OPS_SEVERITY_LABELS = {
  critical: 'حرج',
  high: 'مرتفع',
  attention: 'يحتاج متابعة',
  healthy: 'سليم',
  unknown: 'غير معروف',
  approved: 'معتمد',
  applied: 'مطبق',
  active: 'نشط',
  pending: 'قيد الانتظار',
  draft: 'مسودة',
  rejected: 'مرفوض',
  retired: 'متقاعد',
  expired: 'منتهي',
  inactive: 'معطل',
}

export const OPS_KIND_LABELS = {
  approval_runtime_attention: 'تنبيه دورة الموافقات',
  attachment_runtime_attention: 'تنبيه دورة المرفقات',
  outbox_dead_letter_attention: 'تنبيه صندوق الإرسال',
  release_health_warning: 'تحذير صحة الإصدار',
  offline_sync_attention: 'تنبيه المزامنة دون اتصال',
  approval_overdue: 'طلب متجاوز للمهلة',
  sector_final_attention: 'تدخل قطاعي نهائي',
  farm_finance_volume_attention: 'ضغط مالية المزرعة',
  remote_review_blocked: 'تعطيل المراجعة البعيدة',
  attachment_runtime_block: 'تعطيل تشغيل المرفقات',
}

export const LANE_HEALTH_LABELS = {
  blocked: 'معطل',
  attention: 'يحتاج متابعة',
  healthy: 'سليم',
}

export const BLOCKER_LABELS = {
  overdue: 'متجاوز للمهلة',
  strict_finance_final_required: 'يتطلب اعتمادًا ماليًا قطاعيًا نهائيًا',
  strict_finance_required: 'يتطلب مسارًا ماليًا صارمًا',
  remote_review_blocked: 'موقوف بسبب المراجعة البعيدة',
  attachment_scan_blocked: 'موقوف بسبب فحص المرفقات',
  sector_final_attention: 'يتطلب تدخلًا قطاعيًا نهائيًا',
  approval_overdue: 'طلب اعتماد متجاوز للمهلة',
  farm_finance_volume_attention: 'حمولة مالية محلية مرتفعة',
  attachment_runtime_block: 'تعطيل تشغيلي في المرفقات',
  blocked_by_policy: 'موقوف بفعل السياسة',
  policy_blocked: 'موقوف بفعل السياسة',
  offline_sync_quarantine_pending: 'حمولات مزامنة معزولة بانتظار المعالجة',
  sync_conflict_dlq_pending: 'تعارضات مزامنة في قائمة الإخفاقات',
  no_blockers: 'لا توجد عوائق',
}

export const POLICY_SOURCE_LABELS = {
  farm_settings: 'إعدادات المزرعة',
  farm_settings_legacy_invalid: 'إعدادات المزرعة مع تعارض تراثي',
  active_binding: 'ربط سياسة نشط',
  policy_binding: 'ربط سياسة',
  package_binding: 'ربط حزمة',
  policy_package_binding: 'ربط حزمة سياسة',
  approved_exception: 'استثناء معتمد',
  exception_binding: 'ربط استثناء',
  invariant: 'قيد حاكم',
  default: 'القيمة الافتراضية',
  legacy: 'إرث سابق',
}

export const POLICY_SECTION_LABELS = {
  dual_mode_policy: 'سياسة النمط التشغيلي',
  finance_threshold_policy: 'سياسة الحدود المالية',
  attachment_policy: 'سياسة المرفقات',
  contract_policy: 'سياسة العقود',
  agronomy_execution_policy: 'سياسة التنفيذ الزراعي',
  remote_review_policy: 'سياسة المراجعة البعيدة',
  unclassified: 'حقول غير مصنفة',
}

export const POLICY_FIELD_LABELS = {
  mode: 'الوضع',
  variance_behavior: 'سلوك التباين',
  cost_visibility: 'إظهار التكاليف',
  approval_profile: 'ملف الاعتماد',
  contract_mode: 'نمط العقود',
  treasury_visibility: 'إظهار الخزينة',
  fixed_asset_mode: 'نمط الأصول الثابتة',
  show_daily_log_smart_card: 'إظهار البطاقة الذكية في السجل اليومي',
  procurement_committee_threshold: 'حد لجنة المشتريات',
  single_finance_officer_allowed: 'السماح بمسؤول مالي واحد',
  local_finance_threshold: 'حد المالية المحلي',
  sector_review_threshold: 'حد المراجعة القطاعية',
  sales_tax_percentage: 'نسبة ضريبة المبيعات',
  mandatory_attachment_for_cash: 'إلزام المرفقات للنقد',
  attachment_transient_ttl_days: 'مدة بقاء المرفقات المؤقتة بالأيام',
  approved_attachment_archive_after_days: 'أرشفة المرفقات المعتمدة بعد عدد الأيام',
  attachment_max_upload_size_mb: 'الحد الأقصى لرفع المرفقات بالميغابايت',
  attachment_scan_mode: 'نمط فحص المرفقات',
  attachment_require_clean_scan_for_strict: 'اشتراط فحص نظيف في الوضع الصارم',
  attachment_enable_cdr: 'تفعيل التنقية الآمنة للمرفقات',
  enable_sharecropping: 'تفعيل عقود المشاركة',
  sharecropping_mode: 'نمط المشاركة',
  enable_petty_cash: 'تفعيل العهدة النقدية',
  enable_zakat: 'تفعيل الزكاة',
  enable_depreciation: 'تفعيل الإهلاك',
  allow_overlapping_crop_plans: 'السماح بتداخل الخطط الزراعية',
  allow_multi_location_activities: 'السماح بالأنشطة متعددة المواقع',
  allow_cross_plan_activities: 'السماح بالأنشطة العابرة للخطط',
  allow_creator_self_variance_approval: 'السماح لمنشئ السجل باعتماد التباين',
  remote_site: 'موقع بعيد',
  weekly_remote_review_required: 'إلزام المراجعة الأسبوعية البعيدة',
}

export const POLICY_VALUE_LABELS = {
  strict: 'صارم',
  simple: 'مبسط',
  block: 'حظر',
  full_amounts: 'إظهار المبالغ الكاملة',
  tiered: 'متدرج',
  full_erp: 'نظام ERP كامل',
  visible: 'مرئي',
  full_capitalization: 'رسملة كاملة',
  heuristic: 'استدلالي',
  financial: 'مالي',
  farm_readable: 'قابل للعرض على المزرعة',
  operations_only: 'تشغيلي فقط',
  sector: 'القطاع',
  farm: 'المزرعة',
}

export function formatOpsSeverity(value) {
  const key = normalizeKey(value)
  return OPS_SEVERITY_LABELS[key] || value || OPS_SEVERITY_LABELS.unknown
}

export function formatOpsKind(value) {
  const key = normalizeKey(value)
  return OPS_KIND_LABELS[key] || value || 'تنبيه تشغيلي'
}

export function formatLaneHealth(value) {
  const key = normalizeKey(value)
  return LANE_HEALTH_LABELS[key] || formatOpsSeverity(value)
}

export function formatBlocker(value) {
  const { base, count } = splitCountSuffix(value)
  const key = normalizeKey(base)
  const label = BLOCKER_LABELS[key] || base || BLOCKER_LABELS.no_blockers
  return withCount(label, count)
}

export function formatPolicySource(value) {
  const key = normalizeKey(value)
  return POLICY_SOURCE_LABELS[key] || value || 'غير محدد'
}

export function formatPolicySection(value) {
  if (hasArabic(value)) return value
  const key = normalizeKey(value)
  return POLICY_SECTION_LABELS[key] || String(value || '').replaceAll('_', ' ') || 'غير مصنف'
}

export function formatPolicyFieldLabel(value) {
  if (hasArabic(value)) return value
  const key = normalizeKey(value)
  return POLICY_FIELD_LABELS[key] || String(value || '').replaceAll('_', ' ') || 'حقل سياسة'
}

export function formatPolicyValue(value) {
  if (typeof value === 'boolean') return value ? 'نعم' : 'لا'
  if (value === null || value === undefined || value === '') return 'غير محدد'
  if (typeof value === 'number') return String(value)
  if (hasArabic(value)) return value
  const key = normalizeKey(value)
  return POLICY_VALUE_LABELS[key] || String(value)
}

export function formatOpsReason(value) {
  const raw = String(value || '').trim()
  if (!raw) return 'غير محدد'
  const { base, count } = splitCountSuffix(raw)
  const key = normalizeKey(base)
  if (BLOCKER_LABELS[key]) return withCount(BLOCKER_LABELS[key], count)
  if (OPS_KIND_LABELS[key]) return withCount(OPS_KIND_LABELS[key], count)
  if (key.includes('offline_quarantine')) return withCount('حمولات دون اتصال معزولة بانتظار المعالجة', count)
  if (key.includes('pending_scan_or_quarantined')) return withCount('الدليل المعتمد ما زال بانتظار الفحص أو في العزل', count)
  if (key.includes('authoritative_evidence_is_pending_scan_or_quarantined')) {
    return withCount('الدليل المعتمد ما زال بانتظار الفحص أو في العزل', count)
  }
  return raw
}

export function formatBooleanArabic(value) {
  return value ? 'نعم' : 'لا'
}

export function formatPolicyValidationMessage(value) {
  const raw = String(value || '').trim()
  const key = normalizeKey(raw)
  if (!raw) return 'غير محدد'
  if (key === 'full_erp_contract_mode_is_forbidden_in_simple_mode.') {
    return 'نمط العقود الكامل غير مسموح في الوضع المبسط.'
  }
  if (key === 'full_erp_contract_mode_is_forbidden_in_simple_mode') {
    return 'نمط العقود الكامل غير مسموح في الوضع المبسط.'
  }
  return raw
}
