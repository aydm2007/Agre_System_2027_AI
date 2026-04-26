import { useEffect, useMemo, useState } from 'react'
import { Farms, ServiceCards as ServiceCardsApi } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ToastProvider'
import {
  SmartCardStack,
  getSmartCardByKey,
  sortSmartCardStack,
} from '../components/daily-log/SmartCardStack'
import { Header } from '../stories/Header'

function normalizeResults(response) {
  return response?.data?.results ?? response?.data ?? response?.results ?? response ?? []
}

function SummaryCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <p className="text-xs text-gray-500 dark:text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function MetricTile({ label, value, tone = 'default' }) {
  const toneClass =
    tone === 'danger'
      ? 'text-rose-700 dark:text-rose-300'
      : tone === 'warning'
        ? 'text-amber-700 dark:text-amber-300'
        : 'text-gray-900 dark:text-white'

  return (
    <div className="rounded-xl bg-slate-50 px-3 py-3 dark:bg-slate-900/40">
      <p className="text-xs text-gray-500 dark:text-slate-400">{label}</p>
      <p className={`mt-1 text-xl font-bold ${toneClass}`}>{value}</p>
    </div>
  )
}

const countEnabledCards = (stack) => sortSmartCardStack(Array.isArray(stack) ? stack : []).length

const parseAmount = (value) => {
  const parsed = Number(value ?? 0)
  return Number.isFinite(parsed) ? parsed : 0
}

const buildMergedFlags = (stack) =>
  Array.from(
    new Set(
      sortSmartCardStack(Array.isArray(stack) ? stack : []).flatMap((entry) =>
        Array.isArray(entry?.flags) ? entry.flags : [],
      ),
    ),
  )

const getExecutionMetrics = (card, stack) => {
  const executionCard = getSmartCardByKey(stack, 'execution')
  if (executionCard?.metrics) {
    return executionCard.metrics
  }
  return {}
}

export default function ServiceCards() {
  const { user } = useAuth()
  const toast = useToast()
  const [farms, setFarms] = useState([])
  const [cards, setCards] = useState([])
  const [selectedFarm, setSelectedFarm] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isMounted = true

    const loadFarms = async () => {
      setLoading(true)
      try {
        const results = normalizeResults(await Farms.list())
        if (!isMounted) {
          return
        }
        const normalized = Array.isArray(results) ? results : []
        setFarms(normalized)
        setSelectedFarm((current) => current || String(normalized[0]?.id || ''))
        setError(normalized.length ? '' : 'لا توجد مزارع متاحة لعرض الكروت.')
      } catch {
        if (!isMounted) {
          return
        }
        setFarms([])
        setError('تعذر تحميل قائمة المزارع.')
        toast.error('تعذر تحميل قائمة المزارع.')
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadFarms()
    return () => {
      isMounted = false
    }
  }, [toast])

  useEffect(() => {
    if (!selectedFarm) {
      setCards([])
      return
    }

    let isMounted = true

    const loadCards = async () => {
      setLoading(true)
      try {
        const results = normalizeResults(await ServiceCardsApi.list({ farm_id: selectedFarm }))
        if (!isMounted) {
          return
        }
        setCards(Array.isArray(results) ? results : [])
        setError('')
      } catch {
        if (!isMounted) {
          return
        }
        setCards([])
        setError('تعذر تحميل الكروت الذكية لهذه المزرعة.')
        toast.error('تعذر تحميل الكروت الذكية لهذه المزرعة.')
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadCards()
    return () => {
      isMounted = false
    }
  }, [selectedFarm, toast])

  const summary = useMemo(
    () =>
      cards.reduce(
        (acc, card) => {
          const stack = sortSmartCardStack(Array.isArray(card?.smart_card_stack) ? card.smart_card_stack : [])
          acc.crops += 1
          acc.total += Number(card?.metrics?.total || 0)
          acc.treeCount += Number(card?.metrics?.tree_count || 0)
          acc.machinery += Number(card?.metrics?.machinery || 0)
          acc.openVariances += Number(
            getSmartCardByKey(stack, 'variance')?.metrics?.open_alerts ?? 0,
          )
          acc.ledgerEntries += Number(
            getSmartCardByKey(stack, 'financial_trace')?.metrics?.entries_count ?? 0,
          )
          acc.stackCards += countEnabledCards(stack)
          return acc
        },
        { crops: 0, total: 0, treeCount: 0, machinery: 0, openVariances: 0, ledgerEntries: 0, stackCards: 0 },
      ),
    [cards],
  )

  return (
    <div className="min-h-screen bg-gray-50 pb-20 dark:bg-slate-900" dir="rtl">
      <Header
        user={user ? { ...user, name: user.name || user.username || 'User' } : { name: 'User' }}
        onLogin={() => {}}
        onLogout={() => {}}
        onCreateAccount={() => {}}
      />

      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-white">الكروت الذكية للخدمات الزراعية</h1>
            <p className="text-sm text-gray-500 dark:text-slate-400">
              مدمجة مع الإنجاز اليومي والرقابة والانحرافات والقيود المالية.
            </p>
          </div>

          <label className="flex flex-col gap-2 text-sm font-medium text-gray-700 dark:text-slate-300">
            المزرعة
            <select
              value={selectedFarm}
              onChange={(event) => setSelectedFarm(event.target.value)}
              className="min-w-56 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            >
              {farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          <SummaryCard label="المحاصيل" value={summary.crops} />
          <SummaryCard label="إجمالي الخدمات" value={summary.total} />
          <SummaryCard label="خدمات الأشجار" value={summary.treeCount} />
          <SummaryCard label="الخدمات الآلية" value={summary.machinery} />
          <SummaryCard label="انحرافات مفتوحة" value={summary.openVariances} />
          <SummaryCard label="قيود دفترية" value={summary.ledgerEntries} />
          <SummaryCard label="بطاقات ذكية مفعلة" value={summary.stackCards} />
        </div>

        {loading ? (
          <div className="py-10 text-center dark:text-slate-300">جاري تحميل الكروت...</div>
        ) : error ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-6 text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100">
            {error}
          </div>
        ) : cards.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-gray-300 bg-white px-4 py-10 text-center text-gray-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
            لا توجد كروت خدمات لهذه المزرعة.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {cards.map((card) => {
              const stack = sortSmartCardStack(Array.isArray(card.smart_card_stack) ? card.smart_card_stack : [])
              const executionMetrics = getExecutionMetrics(card, stack)
              const controlCard = getSmartCardByKey(stack, 'control')
              const varianceCard = getSmartCardByKey(stack, 'variance')
              const financialTraceCard = getSmartCardByKey(stack, 'financial_trace')
              const mergedFlags = buildMergedFlags(stack)
              const displayMode = card.cost_display_mode || 'summarized_amounts'
              const showFullAmounts = displayMode === 'full_amounts'
              const showSummaryAmounts = displayMode === 'summarized_amounts' || showFullAmounts
              const budget = parseAmount(executionMetrics.budget_total)
              const actual = parseAmount(executionMetrics.actual_total)
              const burnRate = budget > 0 ? Math.round((actual / budget) * 10000) / 100 : 0
              const openAlerts = Number(varianceCard?.metrics?.open_alerts ?? 0)
              const totalAlerts = Number(varianceCard?.metrics?.total_alerts ?? 0)
              const totalVariance = varianceCard?.metrics?.total_variance ?? '0.0000'
              const entriesCount = Number(financialTraceCard?.metrics?.entries_count ?? 0)
              const debitTotal = financialTraceCard?.metrics?.debit_total ?? '0.0000'
              const creditTotal = financialTraceCard?.metrics?.credit_total ?? '0.0000'
              const criticalLogs = Number(controlCard?.metrics?.critical_logs ?? 0)
              const totalLogs = Number(controlCard?.metrics?.total_logs ?? 0)
              const rejectedLogs = Number(controlCard?.metrics?.rejected_logs ?? 0)
              const costLabel = displayMode === 'ratios_only' ? 'معدل الصرف' : 'تكلفة الإنجاز'
              const costValue = displayMode === 'ratios_only' ? `${burnRate}%` : (executionMetrics.actual_total || '0.0000')
              const ledgerSummaryText = showFullAmounts
                ? `القيود: مدين ${debitTotal}، دائن ${creditTotal}`
                : displayMode === 'summarized_amounts'
                  ? `القيود: ${entriesCount} قيد ملخص وفق سياسة المزرعة`
                  : 'القيود تعمل في الخلفية حسب السياسة التشغيلية'

              return (
                <article
                  key={card.crop.id}
                  className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-bold text-gray-900 dark:text-white">{card.crop.name}</h2>
                      <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">
                        {card.metrics.total} خدمة عبر {card.stage_groups.length} مراحل
                        {executionMetrics.task_name ? ` • ${executionMetrics.task_name}` : ''}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <div className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
                        {card.metrics.tree_count} أشجار
                      </div>
                      <div
                        data-testid={`service-cards-stack-count-${card.crop.id}`}
                        className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
                      >
                        {countEnabledCards(stack)} بطاقات
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <MetricTile label="الخدمات الآلية" value={card.metrics.machinery} />
                    <MetricTile label="الآبار + المساحة" value={card.metrics.well + card.metrics.area} />
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <MetricTile label="الإنجاز اليومي" value={`${executionMetrics.plan_progress_pct || 0}%`} />
                    <MetricTile label={costLabel} value={costValue} />
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <MetricTile
                      label="انحرافات مفتوحة"
                      value={openAlerts}
                      tone={openAlerts > 0 ? 'warning' : 'default'}
                    />
                    <MetricTile label="قيود دفترية" value={entriesCount} />
                  </div>

                  <div className="mt-4 rounded-2xl border border-gray-100 px-4 py-4 dark:border-slate-700">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                      الرقابة والانحرافات والقيود
                    </h3>
                    <div className="mt-3 space-y-2 text-xs text-gray-600 dark:text-slate-300">
                      <p>
                        الإنجاز: {executionMetrics.executed_count || 0} نشاط، آخر يومية -
                      </p>
                      <p>
                        الرقابة: {totalLogs} يومية، {rejectedLogs} مرفوضة، {criticalLogs} حرجة
                      </p>
                      <p>
                        الانحرافات: {totalAlerts} إجماليًا،{' '}
                        {showSummaryAmounts ? `${totalVariance} قيمة تراكمية` : `${burnRate}% معدل صرف مقابل الخطة`}
                      </p>
                      <p>{ledgerSummaryText}</p>
                      {mergedFlags.length > 0 ? <p>الأعلام: {mergedFlags.join('، ')}</p> : null}
                    </div>
                  </div>

                  <div className="mt-4 border-t border-gray-100 pt-4 dark:border-slate-700">
                    <p className="mb-3 text-xs font-semibold text-gray-500 dark:text-slate-400">التوزيع المرحلي</p>
                    <div className="space-y-2">
                      {card.stage_groups.map((stageGroup) => (
                        <div
                          key={`${card.crop.id}-${stageGroup.stage}`}
                          className="rounded-xl border border-gray-100 px-3 py-3 dark:border-slate-700"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-gray-900 dark:text-white">{stageGroup.stage}</p>
                            <span className="text-xs text-gray-500 dark:text-slate-400">{stageGroup.count}</span>
                          </div>
                          <p className="mt-2 text-xs text-gray-600 dark:text-slate-300">
                            {stageGroup.services.map((service) => service.name).join('، ')}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {countEnabledCards(stack) > 0 ? (
                    <div className="mt-4 border-t border-gray-100 pt-4 dark:border-slate-700">
                      <p className="mb-3 text-xs font-semibold text-gray-500 dark:text-slate-400">
                        معاينة Smart Card Stack
                      </p>
                      <SmartCardStack
                        stack={stack}
                        testPrefix={`service-cards-stack-${card.crop.id}`}
                        className="grid gap-3"
                      />
                    </div>
                  ) : null}
                </article>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
