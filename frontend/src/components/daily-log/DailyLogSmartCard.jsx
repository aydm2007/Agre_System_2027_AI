import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { ServiceCards } from '../../api/client'
import { useFarmContext } from '../../api/farmContext'
import { useSettings } from '../../contexts/SettingsContext'
import { extractApiError } from '../../utils/errorUtils'
import { getLookupCache, seedLookupCache } from '../../offline/dexie_db'

import {
  FLAG_LABELS,
  SmartCardStack,
  STATUS_LABELS,
  getSmartCardByKey,
  sortSmartCardStack,
} from './SmartCardStack'

const parseAmount = (value) => {
  const parsed = Number(value ?? 0)
  return Number.isFinite(parsed) ? parsed : 0
}

const computeBurnRate = (executionMetrics) => {
  const budget = parseAmount(executionMetrics?.budget_total)
  const actual = parseAmount(executionMetrics?.actual_total)
  if (budget <= 0) {
    return 0
  }
  return Math.round((actual / budget) * 10000) / 100
}

function StatTile({ label, value, tone = 'default', testId }) {
  const toneClass =
    tone === 'danger'
      ? 'text-rose-700 dark:text-rose-300'
      : tone === 'warning'
        ? 'text-amber-700 dark:text-amber-300'
        : 'text-gray-900 dark:text-white'

  return (
    <div data-testid={testId} className="rounded-xl bg-white/70 px-3 py-3 dark:bg-slate-950/40">
      <div className="text-[11px] text-gray-500 dark:text-slate-400">{label}</div>
      <div className={`mt-1 text-lg font-bold ${toneClass}`}>{value}</div>
    </div>
  )
}

StatTile.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  tone: PropTypes.oneOf(['default', 'warning', 'danger']),
  testId: PropTypes.string.isRequired,
}

const buildMergedFlags = (smartCardStack) =>
  Array.from(
    new Set(
      smartCardStack.flatMap((entry) => (Array.isArray(entry?.flags) ? entry.flags : [])),
    ),
  )

const getExecutionMetrics = (card, smartCardStack) => {
  const executionCard = getSmartCardByKey(smartCardStack, 'execution')
  if (executionCard?.metrics) {
    return executionCard.metrics
  }
  return {}
}

export function DailyLogSmartCard({ form, linkedCropPlan = null, offlineDrafts = [] }) {
  const { selectedFarmId } = useFarmContext()
  const { costVisibility, showDailyLogSmartCard } = useSettings()
  const [card, setCard] = useState(null)
  const [loading, setLoading] = useState(false)
  const [isFromCache, setIsFromCache] = useState(false)
  const [error, setError] = useState('')

  const formFarmId = String(form.farm || '')
  const followsSelectedFarmPolicy = formFarmId && String(selectedFarmId || '') === formFarmId
  const shouldHideFromSelectedFarmPolicy = followsSelectedFarmPolicy && !showDailyLogSmartCard

  useEffect(() => {
    if (!form.farm || !form.crop || shouldHideFromSelectedFarmPolicy) {
      setCard(null)
      setError('')
      return
    }

    let isMounted = true

    const loadCard = async () => {
      setLoading(true)
      setError('')
      try {
        const params = {
          farm_id: form.farm,
          crop_id: form.crop,
          date: form.date,
        }
        if (form.task) {
          params.task_id = form.task
        }
        if (linkedCropPlan?.id) {
          params.crop_plan_id = linkedCropPlan.id
        }
        if (Array.isArray(form.locations) && form.locations.length > 0) {
          params.location_ids = form.locations.join(',')
        }

        const response = await ServiceCards.list(params)
        const results = response?.data?.results ?? response?.data ?? []
        if (!isMounted) {
          return
        }
        setIsFromCache(false)
        const data = Array.isArray(results) ? results[0] || null : null
        setCard(data)
        if (data) {
          const cacheKey = `smart_card:${form.farm}:${form.crop}${form.task ? `:${form.task}` : ''}`
          await seedLookupCache(cacheKey, data)
        }
      } catch (err) {
        if (!isMounted) {
          return
        }
        const cacheKey = `smart_card:${form.farm}:${form.crop}${form.task ? `:${form.task}` : ''}`
        const cached = await getLookupCache(cacheKey)
        if (cached) {
          setCard(cached)
          setIsFromCache(true)
          setLoading(false)
          setError('')
          return
        }
        setCard(null)
        setError(extractApiError(err, 'تعذر تحميل الكرت الذكي لهذه اليومية.'))
      } finally {

        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadCard()
    return () => {
      isMounted = false
    }
  }, [
    form.crop,
    form.date,
    form.farm,
    form.locations,
    form.task,
    linkedCropPlan?.id,
    shouldHideFromSelectedFarmPolicy,
  ])

  if (!form.farm || !form.crop || shouldHideFromSelectedFarmPolicy) {
    return null
  }

  if (loading) {
    return (
      <div
        data-testid="daily-log-smart-card-loading"
        className="max-w-4xl mx-auto mb-4 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4 text-sm text-sky-800 dark:border-sky-900/40 dark:bg-sky-950/20 dark:text-sky-200"
      >
        جاري تحليل الخطة والإنجاز والرقابة والقيود لهذا النشاط...
      </div>
    )
  }

  if (error) {
    return (
      <div
        data-testid="daily-log-smart-card-error"
        className="max-w-4xl mx-auto mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200"
      >
        {error}
      </div>
    )
  }

  if (!card) {
    return null
  }

  const resolvedShowDailyLogSmartCard =
    card?.policy_snapshot?.show_daily_log_smart_card ?? showDailyLogSmartCard
  if (!resolvedShowDailyLogSmartCard) {
    return null
  }

  const smartCardStack = sortSmartCardStack(Array.isArray(card.smart_card_stack) ? card.smart_card_stack : [])
  const executionMetrics = getExecutionMetrics(card, smartCardStack)
  const controlCard = getSmartCardByKey(smartCardStack, 'control')
  const varianceCard = getSmartCardByKey(smartCardStack, 'variance')
  const financialTraceCard = getSmartCardByKey(smartCardStack, 'financial_trace')
  const flags = buildMergedFlags(smartCardStack)
  const titleTaskName = executionMetrics.task_name
  const scheduleStatus = executionMetrics.schedule_status
  const scheduleLabel = STATUS_LABELS[scheduleStatus] || 'غير معروف'
  const criticalLogs = Number(controlCard?.metrics?.critical_logs ?? 0)
  const totalLogs = Number(controlCard?.metrics?.total_logs ?? 0)
  const rejectedLogs = Number(controlCard?.metrics?.rejected_logs ?? 0)
  const openAlerts = Number(varianceCard?.metrics?.open_alerts ?? 0)
  const latestAlertAt = varianceCard?.metrics?.latest_alert_at ?? '-'
  const entriesCount = Number(financialTraceCard?.metrics?.entries_count ?? 0)
  const debitTotal = financialTraceCard?.metrics?.debit_total ?? '0.0000'
  const creditTotal = financialTraceCard?.metrics?.credit_total ?? '0.0000'
  const displayMode = card.cost_display_mode || costVisibility || 'summarized_amounts'
  const showFullAmounts = displayMode === 'full_amounts'
  const showSummaryAmounts = displayMode === 'summarized_amounts' || showFullAmounts
  const burnRate = computeBurnRate(executionMetrics)
  
  // [AGRI-GUARDIAN] Local Draft Achievement Logic (Live Mirroring)
  const formTotalServiced = (form.serviceRows || []).reduce((acc, r) => acc + (Number(r.serviceCount) || 0), 0)
  const formFuelConsumed = Number(form.fuel_consumed || 0) + Number(form.diesel_qty || 0)
  const formWaterVolume = Number(form.water_volume || 0)
  const formTotalArea = Number(form.planted_area || 0)
  const formTotalTrees = Number(form.activity_tree_count || 0) + Number(form.tree_count_delta || 0)
  const formGenericAch = Number(form.achievement_qty || 0)

  // Factor in offline queued achievements
  const queuedDrafts = offlineDrafts.filter(d => d.status === 'queued' || d.status === 'pending')
  const queueTotalServiced = queuedDrafts.reduce((acc, draft) => {
    return acc + (draft.data?.serviceRows || []).reduce((sum, r) => sum + (Number(r.serviceCount) || 0), 0)
  }, 0)
  const queueFuelConsumed = queuedDrafts.reduce((acc, draft) => {
    return acc + Number(draft.data?.fuel_consumed || 0) + Number(draft.data?.diesel_qty || 0)
  }, 0)
  const queueWaterVolume = queuedDrafts.reduce((acc, draft) => {
    return acc + Number(draft.data?.water_volume || 0)
  }, 0)
  const queueTotalArea = queuedDrafts.reduce((acc, draft) => acc + Number(draft.data?.planted_area || 0), 0)
  const queueTotalTrees = queuedDrafts.reduce((acc, draft) => {
    return acc + Number(draft.data?.activity_tree_count || 0) + Number(draft.data?.tree_count_delta || 0)
  }, 0)
  const queueGenericAch = queuedDrafts.reduce((acc, draft) => acc + Number(draft.data?.achievement_qty || 0), 0)

  const draftTotalServiced = formTotalServiced + queueTotalServiced
  const draftFuelConsumed = formFuelConsumed + queueFuelConsumed
  const draftWaterVolume = formWaterVolume + queueWaterVolume
  const draftTotalArea = formTotalArea + queueTotalArea
  const draftTotalTrees = formTotalTrees + queueTotalTrees
  const draftGenericAch = formGenericAch + queueGenericAch
  
  const isDraftActive = draftTotalServiced > 0 || draftFuelConsumed > 0 || draftWaterVolume > 0 || draftTotalArea > 0 || draftTotalTrees > 0 || draftGenericAch > 0 || queuedDrafts.length > 0

  const completionPct = executionMetrics.plan_progress_pct || 0
  const completionTone = isDraftActive ? 'emerald' : (openAlerts > 0 ? 'warning' : 'default')
  
  let draftLabelStr = ''
  if (draftTotalArea > 0) draftLabelStr += ` مساحة ${draftTotalArea}`
  if (draftTotalTrees > 0) draftLabelStr += ` أشجار ${draftTotalTrees}`
  if (draftTotalServiced > 0) draftLabelStr += ` خدمة ${draftTotalServiced}`
  if (draftGenericAch > 0) draftLabelStr += ` كمية ${draftGenericAch}`
  if (!draftLabelStr && queuedDrafts.length > 0) draftLabelStr = ` (${queuedDrafts.length} مسودة)`

  const completionLabel = isDraftActive ? `الإنجاز (مسودة:${draftLabelStr})` : 'الإنجاز المعتمد'
  const completionValue = isDraftActive ? `${completionPct}% +` : `${completionPct}%`
  const costStatLabel = displayMode === 'ratios_only' ? 'معدل الصرف' : 'تكلفة منفذة'
  const costStatValue =
    displayMode === 'ratios_only'
      ? `${burnRate}%`
      : executionMetrics.actual_total || '0.0000'
  const ledgerSummaryText = showFullAmounts
    ? `القيود: مدين ${debitTotal} | دائن ${creditTotal}`
    : displayMode === 'summarized_amounts'
      ? `القيود: ${entriesCount} قيد ملخص وفق سياسة المزرعة`
      : 'القيود تعمل في الخلفية حسب السياسة التشغيلية'

  return (
    <section
      data-testid="daily-log-smart-card"
      className="max-w-4xl mx-auto mb-6 rounded-3xl border border-slate-200 bg-gradient-to-l from-white via-slate-50 to-emerald-50 px-5 py-5 shadow-sm dark:border-slate-800 dark:from-slate-900 dark:via-slate-900 dark:to-emerald-950/30"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div
            data-testid="daily-log-smart-card-kicker"
            className="text-xs font-semibold tracking-wide text-emerald-700 dark:text-emerald-300"
          >
            الكرت الذكي لليومية
            {isFromCache && (
              <span className="ms-2 inline-flex items-center rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 ring-1 ring-inset ring-slate-500/10 dark:bg-slate-400/10 dark:text-slate-400 dark:ring-slate-400/20">
                بيانات مخزنة (Offline)
              </span>
            )}
          </div>

          <h2
            data-testid="daily-log-smart-card-title"
            className="mt-1 text-xl font-bold text-gray-900 dark:text-white"
          >
            {card.crop?.name || 'المحصول'} {titleTaskName ? `• ${titleTaskName}` : ''}
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {flags.length > 0 ? (
            flags.map((flag) => (
              <span
                key={flag}
                data-testid={`daily-log-smart-card-flag-${flag}`}
                className="rounded-full border border-amber-200 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/30 dark:text-amber-200"
              >
                {FLAG_LABELS[flag] || flag}
              </span>
            ))
          ) : (
            <span
              data-testid="daily-log-smart-card-flag-healthy"
              className="rounded-full border border-emerald-200 bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-900/30 dark:text-emerald-200"
            >
              متوافق تشغيليًا
            </span>
          )}
        </div>
      </div>

      <div data-testid="daily-log-smart-card-stats" className="mt-4 grid gap-3 md:grid-cols-4">
        <StatTile
          label={completionLabel}
          testId="daily-log-smart-card-stat-completion"
          value={completionValue}
          tone={completionTone}
        />
        <StatTile
          label="قيود دفترية"
          testId="daily-log-smart-card-stat-ledger"
          value={entriesCount}
          tone={criticalLogs > 0 ? 'warning' : 'default'}
        />
        <StatTile
          label="انحرافات مفتوحة"
          testId="daily-log-smart-card-stat-open-variances"
          value={openAlerts}
          tone={openAlerts > 0 ? 'danger' : 'default'}
        />
        <StatTile
          label={costStatLabel}
          testId="daily-log-smart-card-stat-cost"
          value={costStatValue}
          tone={flags.includes('budget_overrun') ? 'danger' : 'default'}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div
          data-testid="daily-log-smart-card-plan"
          className="rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-950/30"
        >
          <h3
            data-testid="daily-log-smart-card-plan-heading"
            className="text-sm font-semibold text-gray-900 dark:text-white"
          >
            الخطة والميزانية
          </h3>
          {executionMetrics.plan_name ? (
            <div
              data-testid="daily-log-smart-card-plan-body"
              className="mt-3 space-y-2 text-sm text-gray-700 dark:text-slate-300"
            >
              <p data-testid="daily-log-smart-card-plan-name">
                الخطة: <strong>{executionMetrics.plan_name}</strong> ({executionMetrics.plan_status || '-'})
              </p>
              <p data-testid="daily-log-smart-card-plan-progress">
                التقدم المرحلي: {executionMetrics.completed_tasks || 0}/{executionMetrics.planned_tasks || 0} مهمة (
                {executionMetrics.plan_progress_pct || 0}%)
              </p>
              {showSummaryAmounts ? (
                <p data-testid="daily-log-smart-card-plan-budget">
                  الميزانية: {executionMetrics.budget_total || '0.0000'} | الفعلي: {executionMetrics.actual_total || '0.0000'}
                </p>
              ) : (
                <p data-testid="daily-log-smart-card-plan-budget-policy">معدل الصرف مقابل الخطة: {burnRate}%</p>
              )}
              <p data-testid="daily-log-smart-card-plan-variance">
                انحراف الخطة: {executionMetrics.variance_total || '0.0000'} ({executionMetrics.variance_pct || 0}%)
              </p>
              <p data-testid="daily-log-smart-card-plan-locations">
                تغطية المواقع: {executionMetrics.matched_locations || 0}/{executionMetrics.planned_locations || 0}
              </p>
            </div>
          ) : (
            <p
              data-testid="daily-log-smart-card-plan-missing"
              className="mt-3 text-sm text-amber-700 dark:text-amber-300"
            >
              لا توجد خطة فعالة مرتبطة بهذه اليومية حتى الآن.
            </p>
          )}
        </div>

        <div
          data-testid="daily-log-smart-card-task"
          className="rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-950/30"
        >
          <h3
            data-testid="daily-log-smart-card-task-heading"
            className="text-sm font-semibold text-gray-900 dark:text-white"
          >
            تركيز المهمة والرقابة
          </h3>
          {titleTaskName || !smartCardStack.length ? (
            <div
              data-testid="daily-log-smart-card-task-body"
              className="mt-3 space-y-2 text-sm text-gray-700 dark:text-slate-300"
            >
              <p data-testid="daily-log-smart-card-task-name">
                المهمة الحالية: <strong>{titleTaskName || 'بدون مهمة محددة'}</strong> / {executionMetrics.stage || 'غير معروفة'}
              </p>
              <p data-testid="daily-log-smart-card-schedule-status">الحالة الجدولية: {scheduleLabel}</p>
              <p data-testid="daily-log-smart-card-task-counts">
                المجدول/المنفذ: {executionMetrics.planned_count ?? 0}/{executionMetrics.executed_count ?? 0}
              </p>
              {showSummaryAmounts ? (
                <p data-testid="daily-log-smart-card-task-budget">
                  ميزانية المهمة: {executionMetrics.budget_total || '0.0000'} | الفعلي: {executionMetrics.actual_total || '0.0000'}
                </p>
              ) : (
                <p data-testid="daily-log-smart-card-task-budget-policy">
                  المالية التفصيلية للمهمة مخفية، والمتاح هو الحالة والانحراف.
                </p>
              )}
              <p data-testid="daily-log-smart-card-task-variances">
                انحرافات المهمة المفتوحة: {executionMetrics.open_variances ?? openAlerts}
              </p>
            </div>
          ) : (
            <p
              data-testid="daily-log-smart-card-task-empty"
              className="mt-3 text-sm text-gray-600 dark:text-slate-400"
            >
              اختر مهمة لعرض المقارنة المباشرة مع الجدولة والميزانية والانحرافات.
            </p>
          )}
        </div>
      </div>

      {smartCardStack.length > 0 ? (
        <SmartCardStack
          stack={smartCardStack}
          testPrefix="daily-log-smart-card-stack"
          className="mt-4 grid gap-4 md:grid-cols-2"
        />
      ) : null}

      <div
        data-testid="daily-log-smart-card-audit"
        className="mt-4 rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-gray-700 dark:border-slate-800 dark:bg-slate-950/30 dark:text-slate-300"
      >
        <div className="grid gap-2 md:grid-cols-3">
          <p data-testid="daily-log-smart-card-control-summary">
            اليوميات: {totalLogs} | مرفوضة: {rejectedLogs} | حرجة: {criticalLogs}
          </p>
          <p data-testid="daily-log-smart-card-ledger-summary">{ledgerSummaryText}</p>
          <p data-testid="daily-log-smart-card-variance-summary">
            اخر إنجاز: - | اخر انحراف: {latestAlertAt}
          </p>
        </div>
      </div>
    </section>
  )
}

DailyLogSmartCard.propTypes = {
  form: PropTypes.shape({
    farm: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    crop: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    task: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    date: PropTypes.string,
    locations: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.number])),
  }).isRequired,
  linkedCropPlan: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  }),
  offlineDrafts: PropTypes.array,
}
