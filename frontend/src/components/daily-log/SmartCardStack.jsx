import PropTypes from 'prop-types'

export const STATUS_LABELS = {
  no_plan: 'بدون خطة',
  planned: 'ضمن الخطة',
  due_today: 'مجدول اليوم',
  late: 'متاخر عن الخطة',
  ahead_of_plan: 'مبكر على الخطة',
  unplanned: 'غير مجدول',
}

export const FLAG_LABELS = {
  missing_active_plan: 'لا توجد خطة فعالة',
  budget_overrun: 'تجاوز ميزانية',
  open_variance: 'انحراف مفتوح',
  critical_control: 'ملاحظة رقابية حرجة',
  task_late: 'المهمة متاخرة',
  task_unplanned: 'المهمة غير مجدولة',
}

const CARD_STATUS_LABELS = {
  idle: 'غير نشط',
  ready: 'جاهز',
  attention: 'يحتاج متابعة',
  critical: 'حرج',
}

const POLICY_LABELS = {
  backend_costing_only: 'الحسابات في الخلفية فقط',
  cost_display_mode: 'سياسة العرض المالي',
  full_cost_allowed: 'تفاصيل المواد الكاملة',
  per_card_classification: 'تصنيف الانحراف حسب البطاقة',
  read_only: 'قراءة فقط',
  shadow_accounting: 'القيد الظلي محفوظ',
  strict_detail_only: 'التفصيل الصارم فقط',
  surra_law: 'قانون الصرة',
  variance_surface: 'سطح رقابي للانحراف',
  visibility_level: 'مستوى الرؤية',
}

const CARD_METRIC_LABELS = {
  actual_cost: 'التكلفة الفعلية',
  actual_qty: 'الكمية الفعلية',
  cost_ratio_pct: 'نسبة الصرف',
  cost_variance: 'انحراف التكلفة',
  credit_total: 'اجمالي الدائن',
  debit_total: 'اجمالي المدين',
  entries_count: 'القيود',
  executed_count: 'المنفذ',
  failed_retryable: 'المحاولات القابلة لإعادة المحاولة',
  fuel_consumed: 'الوقود المستهلك',
  harvest_quantity: 'كمية الحصاد',
  inventory_linked: 'مرتبط بالمخزون',
  machine_hours: 'ساعات الالة',
  open_alerts: 'الانحرافات المفتوحة',
  plan_progress_pct: 'تقدم الخطة',
  planned_cost: 'التكلفة المخططة',
  planned_count: 'المجدول',
  planned_qty: 'الكمية المخططة',
  qty_variance: 'انحراف الكمية',
  reconciliation_posture: 'وضع المطابقة',
  schedule_status: 'الحالة الجدولية',
  is_solar_powered: 'طاقة شمسية',
  diesel_qty: 'كمية الديزل (لتر)',
  stage: 'المرحلة',
  submitted_logs: 'اليوميات المرسلة',
  surrah_share: 'حصة الصرة',
  task_name: 'المهمة',
  total_alerts: 'اجمالي الانحرافات',
  total_logs: 'اجمالي اليوميات',
  total_variance: 'اجمالي الانحراف',
  uom: 'الوحدة',
  warning_logs: 'اليوميات التحذيرية',
  water_volume: 'حجم المياه',
  well_reading: 'قراءة البئر',
  workers_count: 'عدد العمال',
}

export const sortSmartCardStack = (stack = []) =>
  [...stack].sort((left, right) => (left.order || 0) - (right.order || 0))

export const getSmartCardByKey = (stack = [], cardKey) =>
  sortSmartCardStack(Array.isArray(stack) ? stack : []).find((entry) => entry?.card_key === cardKey) || null

export const getSmartCardMetric = (stack = [], cardKey, metricKey, fallback = null) =>
  getSmartCardByKey(stack, cardKey)?.metrics?.[metricKey] ?? fallback

const titleizeMetricKey = (key) =>
  CARD_METRIC_LABELS[key] ||
  key
    .split('_')
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(' ')

const formatMetricValue = (value, key) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  if (typeof value === 'boolean') {
    if (key === 'is_solar_powered') return value ? 'نعم (☀️)' : 'لا'
    return value ? 'نعم' : 'لا'
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (item && typeof item === 'object') {
          return item.label || item.title || item.name || JSON.stringify(item)
        }
        return String(item)
      })
      .join('، ')
  }
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([nestedKey, nestedValue]) => `${titleizeMetricKey(nestedKey)}: ${nestedValue}`)
      .join('، ')
  }
  if (key === 'schedule_status') {
    return STATUS_LABELS[value] || value
  }
  if (typeof value === 'number' && key.endsWith('_pct')) {
    return `${value}%`
  }
  return String(value)
}

const formatPolicyEntries = (policy = {}) =>
  Object.entries(policy).filter(([, value]) => value !== undefined && value !== null && value !== false && value !== '')

export function SmartStackCard({ cardEntry, testPrefix = 'smart-card-stack' }) {
  const statusLabel = CARD_STATUS_LABELS[cardEntry.status] || cardEntry.status
  const statusToneClass =
    cardEntry.status === 'critical'
      ? 'border-rose-200 bg-rose-100 text-rose-800 dark:border-rose-900/40 dark:bg-rose-900/30 dark:text-rose-200'
      : cardEntry.status === 'attention'
        ? 'border-amber-200 bg-amber-100 text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/30 dark:text-amber-200'
        : 'border-emerald-200 bg-emerald-100 text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-900/30 dark:text-emerald-200'

  const metricEntries = Object.entries(cardEntry.metrics || {}).filter(([, value]) => !Array.isArray(value))
  const lineItems = Array.isArray(cardEntry.metrics?.line_items) ? cardEntry.metrics.line_items : []
  const flags = Array.isArray(cardEntry.flags) ? cardEntry.flags : []
  const sourceRefs = Array.isArray(cardEntry.source_refs) ? cardEntry.source_refs : []
  const policyEntries = formatPolicyEntries(cardEntry.policy)

  return (
    <article
      data-testid={`${testPrefix}-card-${cardEntry.card_key}`}
      className="rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-950/30"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3
            data-testid={`${testPrefix}-card-title-${cardEntry.card_key}`}
            className="text-sm font-semibold text-gray-900 dark:text-white"
          >
            {cardEntry.title}
          </h3>
          <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">
            {cardEntry.data_source} | {cardEntry.mode_visibility}
          </p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusToneClass}`}>
          {statusLabel}
        </span>
      </div>

      {flags.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {flags.map((flag) => (
            <span
              key={`${cardEntry.card_key}-${flag}`}
              data-testid={`${testPrefix}-card-flag-${cardEntry.card_key}-${flag}`}
              className="rounded-full border border-amber-200 bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/30 dark:text-amber-200"
            >
              {FLAG_LABELS[flag] || flag}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {metricEntries.map(([key, value]) => (
          <div
            key={`${cardEntry.card_key}-${key}`}
            data-testid={`${testPrefix}-card-metric-${cardEntry.card_key}-${key}`}
            className="rounded-xl bg-slate-50 px-3 py-3 text-sm dark:bg-slate-900/40"
          >
            <div className="text-[11px] text-gray-500 dark:text-slate-400">{titleizeMetricKey(key)}</div>
            <div className="mt-1 font-semibold text-gray-900 dark:text-white">
              {formatMetricValue(value, key)}
            </div>
          </div>
        ))}
      </div>

      {lineItems.length > 0 ? (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-900/40">
          <div className="text-xs font-semibold text-gray-700 dark:text-slate-300">تفصيل المواد</div>
          <div className="mt-2 space-y-2">
            {lineItems.map((item) => (
              <div
                key={`${cardEntry.card_key}-${item.item_id}`}
                data-testid={`${testPrefix}-card-line-item-${cardEntry.card_key}-${item.item_id}`}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-700 dark:bg-slate-950/30 dark:text-slate-300"
              >
                <div className="font-semibold">{item.item_name}</div>
                <div className="mt-1">
                  رصيد {item.on_hand_qty || '0'} | مخطط {item.planned_qty} | فعلي {item.actual_qty} | انحراف {item.qty_variance}
                </div>
                <div className="mt-1">
                  تكلفة مخططة {item.planned_cost} | فعلية {item.actual_cost} | انحراف {item.cost_variance}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {policyEntries.length > 0 ? (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-900/40">
          <div className="text-xs font-semibold text-gray-700 dark:text-slate-300">سياسة العرض</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {policyEntries.map(([key, value]) => (
              <span
                key={`${cardEntry.card_key}-policy-${key}`}
                data-testid={`${testPrefix}-card-policy-${cardEntry.card_key}-${key}`}
                className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] text-slate-700 dark:border-slate-700 dark:bg-slate-950/30 dark:text-slate-300"
              >
                {POLICY_LABELS[key] || key}: {formatMetricValue(value, key)}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {sourceRefs.length > 0 ? (
        <div className="mt-4 text-[11px] text-gray-500 dark:text-slate-400">
          المصادر: {sourceRefs.join('، ')}
        </div>
      ) : null}
    </article>
  )
}

SmartStackCard.propTypes = {
  cardEntry: PropTypes.shape({
    card_key: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    mode_visibility: PropTypes.string,
    status: PropTypes.string,
    metrics: PropTypes.object,
    flags: PropTypes.arrayOf(PropTypes.string),
    data_source: PropTypes.string,
    source_refs: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  testPrefix: PropTypes.string,
}

export function SmartCardStack({ stack, testPrefix = 'smart-card-stack', className = 'grid gap-4 md:grid-cols-2' }) {
  const sortedStack = sortSmartCardStack(stack)
  if (!sortedStack.length) {
    return null
  }

  return (
    <div data-testid={`${testPrefix}`} className={className}>
      {sortedStack.map((cardEntry) => (
        <SmartStackCard
          key={`${cardEntry.card_key}-${cardEntry.order ?? 0}`}
          cardEntry={cardEntry}
          testPrefix={testPrefix}
        />
      ))}
    </div>
  )
}

SmartCardStack.propTypes = {
  stack: PropTypes.arrayOf(PropTypes.object),
  testPrefix: PropTypes.string,
  className: PropTypes.string,
}
