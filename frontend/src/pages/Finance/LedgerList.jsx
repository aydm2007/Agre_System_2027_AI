import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, Seasons } from '../../api/client'
import { toast } from 'react-hot-toast'
import {
  AlertCircle,
  Book,
  Calendar,
  ChevronLeft,
  ChevronRight,
  FileText,
  RefreshCw,
  Search,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useFarmContext } from '../../api/farmContext.jsx'
import { ACCOUNT_LABELS } from './constants'
import { formatMoney } from '../../utils/decimal'
import useFinancialFilters from '../../hooks/useFinancialFilters'
import FinancialFilterBar from '../../components/filters/FinancialFilterBar'

const PAGE_SIZE = 50

const EMPTY_SUMMARY = {
  totals: {
    debit: 0,
    credit: 0,
    balance: 0,
    entry_count: 0,
  },
  by_account: [],
}

const DATE_PRESETS = [
  { key: 'today', label: 'اليوم' },
  { key: 'last_7_days', label: 'آخر 7 أيام' },
  { key: 'last_30_days', label: 'آخر 30 يومًا' },
  { key: 'this_season', label: 'هذا الموسم' },
]

const formatDateInput = (date) => {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const createRangeFromPreset = (preset, seasonWindow = null) => {
  const today = new Date()
  const to = formatDateInput(today)

  if (preset === 'today') {
    return { from: to, to }
  }

  if (preset === 'last_7_days') {
    const fromDate = new Date(today)
    fromDate.setDate(fromDate.getDate() - 6)
    return { from: formatDateInput(fromDate), to }
  }

  if (preset === 'this_season' && seasonWindow?.from && seasonWindow?.to) {
    return seasonWindow
  }

  const fromDate = new Date(today)
  fromDate.setDate(fromDate.getDate() - 29)
  return { from: formatDateInput(fromDate), to }
}

const buildSummaryEndpoint = (endpoint) => {
  const normalized = endpoint.endsWith('/') ? endpoint : `${endpoint}/`
  return `${normalized}summary/`
}

const buildLedgerRequestConfig = ({ endpoint, params, signal }) => {
  const config = {
    params: { ...params },
    signal,
  }

  if (endpoint === '/shadow-ledger/') {
    config.params._ts = Date.now()
    config.headers = {
      'Cache-Control': 'no-cache, no-store, max-age=0',
      Pragma: 'no-cache',
      Expires: '0',
    }
  }

  return config
}

const normalizeRows = (data) => {
  if (Array.isArray(data)) {
    return {
      rows: data,
      count: data.length,
      next: null,
      previous: null,
    }
  }

  return {
    rows: data?.results || [],
    count: Number(data?.count || 0),
    next: data?.next || null,
    previous: data?.previous || null,
  }
}

const classifyLedgerError = (error, endpoint) => {
  const status = error?.response?.status

  if (status === 404 && endpoint === '/shadow-ledger/') {
    return {
      type: 'integration',
      message:
        'سطح القيود للقراءة متاح في هذا الإصدار من الواجهة، لكن backend المنشور لا يحتوي endpoint المطلوب بعد.',
    }
  }

  if (status === 403) {
    return {
      type: 'permission',
      message: 'لا تملك صلاحية الوصول إلى القيود المطلوبة لهذه المزرعة أو الفترة.',
    }
  }

  if (status >= 500) {
    return {
      type: 'server',
      message: 'تعذر تجهيز القيود حاليًا بسبب خطأ في الخادم. أعد المحاولة بعد قليل.',
    }
  }

  return {
    type: 'network',
    message: 'تعذر الاتصال بسطح القيود حاليًا. تحقق من الاتصال ثم أعد المحاولة.',
  }
}

const getAccountLabel = (code) => ACCOUNT_LABELS[code]?.name || code

const getAccountBadgeClass = (code) => {
  if (!code) {
    return 'border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-500/40 dark:bg-slate-500/20 dark:text-slate-200'
  }
  const prefix = String(code).slice(0, 1)
  switch (prefix) {
    case '1':
      return 'border-emerald-300 bg-emerald-100 text-emerald-900 dark:border-emerald-400/40 dark:bg-emerald-500/20 dark:text-emerald-300'
    case '2':
      return 'border-rose-300 bg-rose-100 text-rose-900 dark:border-rose-400/40 dark:bg-rose-500/20 dark:text-rose-300'
    case '3':
      return 'border-blue-300 bg-blue-100 text-blue-900 dark:border-blue-400/40 dark:bg-blue-500/20 dark:text-blue-300'
    case '4':
      return 'border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-400/40 dark:bg-amber-500/20 dark:text-amber-300'
    case '5':
      return 'border-violet-300 bg-violet-100 text-violet-900 dark:border-violet-400/40 dark:bg-violet-500/20 dark:text-violet-300'
    default:
      return 'border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-500/40 dark:bg-slate-500/20 dark:text-slate-200'
  }
}

const formatLedgerDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('ar-SA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function SummaryCard({ title, value, subValue, tone = 'slate', icon: Icon, loading = false }) {
  const toneClasses = {
    emerald:
      'border-emerald-200/80 bg-emerald-50/90 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100',
    blue: 'border-blue-200/80 bg-blue-50/90 text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-100',
    rose: 'border-rose-200/80 bg-rose-50/90 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100',
    violet:
      'border-violet-200/80 bg-violet-50/90 text-violet-900 dark:border-violet-500/30 dark:bg-violet-500/10 dark:text-violet-100',
    slate:
      'border-slate-200/80 bg-white/90 text-slate-900 dark:border-slate-700/60 dark:bg-slate-800/80 dark:text-white',
  }

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${toneClasses[tone] || toneClasses.slate}`}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm font-medium opacity-75">{title}</div>
          {loading ? (
            <div className="mt-3 h-8 w-28 animate-pulse rounded-lg bg-slate-200 dark:bg-white/10" />
          ) : (
            <div className="mt-2 text-2xl font-black" dir="ltr">
              {typeof value === 'number' || typeof value === 'string' ? formatMoney(value) : value}
              {subValue ? <span className="me-2 text-sm font-medium opacity-70">{subValue}</span> : null}
            </div>
          )}
        </div>
        <div className="rounded-2xl border border-current/10 bg-white/60 p-3 dark:bg-white/5">
          <Icon className="h-7 w-7 opacity-80" />
        </div>
      </div>
    </div>
  )
}

function InlineBanner({ errorInfo, onRetry, rowsLoading = false }) {
  if (!errorInfo && !rowsLoading) return null

  if (rowsLoading && !errorInfo) {
    return (
      <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-100">
        جارٍ تجهيز القيود المحددة...
      </div>
    )
  }

  const toneClasses = {
    integration:
      'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100',
    permission:
      'border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100',
    server:
      'border-orange-300 bg-orange-50 text-orange-900 dark:border-orange-500/30 dark:bg-orange-500/10 dark:text-orange-100',
    network:
      'border-blue-300 bg-blue-50 text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-100',
  }

  return (
    <div
      className={`flex flex-wrap items-start justify-between gap-3 rounded-2xl border px-4 py-3 text-sm ${toneClasses[errorInfo?.type] || toneClasses.network}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
        <div>{errorInfo?.message}</div>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-xl border border-current/20 px-3 py-1.5 font-medium hover:bg-white/50 dark:hover:bg-white/10"
        >
          إعادة المحاولة
        </button>
      ) : null}
    </div>
  )
}

export default function LedgerList({ endpoint = '/finance/ledger/' }) {
  const { selectedFarmId, farms } = useFarmContext()
  const [entries, setEntries] = useState([])
  const [summary, setSummary] = useState(EMPTY_SUMMARY)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [rowsLoading, setRowsLoading] = useState(false)
  const [errorInfo, setErrorInfo] = useState(null)
  const [searchText, setSearchText] = useState('')
  const [accountFilter, setAccountFilter] = useState('')
  const initialRange = useMemo(() => createRangeFromPreset('last_30_days'), [])
  const [dateFrom, setDateFrom] = useState(initialRange.from)
  const [dateTo, setDateTo] = useState(initialRange.to)
  const [periodPreset, setPeriodPreset] = useState('last_30_days')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({
    count: 0,
    next: null,
    previous: null,
  })
  const [hasAttemptedLoad, setHasAttemptedLoad] = useState(false)
  const [lastAppliedSignature, setLastAppliedSignature] = useState('')
  const [autoLoadedFarm, setAutoLoadedFarm] = useState(null)
  const summaryAbortRef = useRef(null)
  const rowsAbortRef = useRef(null)

  const {
    filters: financialFilters,
    options: filterOptions,
    loading: filterLoading,
    setFilter: setFinancialFilter,
    resetFilters,
    filterParams,
  } = useFinancialFilters({ dimensions: ['farm', 'location', 'costCenter', 'crop_plan', 'activity'] })

  const activeFarmId = financialFilters.farm || selectedFarmId || ''

  const selectedFarm = useMemo(
    () => farms?.find((farm) => String(farm.id) === String(activeFarmId)),
    [farms, activeFarmId],
  )

  const baseRequestParams = useMemo(() => {
    const params = {
      ...filterParams,
      ordering: '-created_at',
    }
    if (activeFarmId && !params.farm) {
      params.farm = activeFarmId
    }
    if (accountFilter) params.account_code = accountFilter
    if (dateFrom) params.created_at__gte = dateFrom
    if (dateTo) params.created_at__lte = dateTo
    return params
  }, [filterParams, activeFarmId, accountFilter, dateFrom, dateTo])

  const requestSignature = useMemo(
    () => JSON.stringify(baseRequestParams),
    [baseRequestParams],
  )

  const hasDirtyFilters = Boolean(lastAppliedSignature && lastAppliedSignature !== requestSignature)

  const cancelPendingRequests = useCallback(() => {
    summaryAbortRef.current?.abort()
    rowsAbortRef.current?.abort()
  }, [])

  useEffect(() => () => cancelPendingRequests(), [cancelPendingRequests])

  const applyPreset = useCallback(
    async (preset) => {
      if (preset === 'this_season' && activeFarmId) {
        try {
          const response = await Seasons.list({
            farm_id: activeFarmId,
            is_active: true,
            page_size: 1,
          })
          const payload = response?.data?.results || response?.data || []
          const season = Array.isArray(payload) ? payload[0] : payload
          const seasonWindow =
            season?.start_date && season?.end_date
              ? {
                  from: String(season.start_date).slice(0, 10),
                  to: String(season.end_date).slice(0, 10),
                }
              : null
          const range = createRangeFromPreset('this_season', seasonWindow)
          setPeriodPreset('this_season')
          setDateFrom(range.from)
          setDateTo(range.to)
          return
        } catch {
          toast.error('تعذر تحديد حدود الموسم النشط، وتم استخدام آخر 30 يومًا بدلًا من ذلك.')
        }
      }

      const range = createRangeFromPreset(preset)
      setPeriodPreset(preset)
      setDateFrom(range.from)
      setDateTo(range.to)
    },
    [activeFarmId],
  )

  const loadLedger = useCallback(
    async ({ nextPage = 1 } = {}) => {
      if (!activeFarmId) return

      cancelPendingRequests()
      const summaryController = new AbortController()
      const rowsController = new AbortController()
      summaryAbortRef.current = summaryController
      rowsAbortRef.current = rowsController

      setHasAttemptedLoad(true)
      setSummaryLoading(true)
      setRowsLoading(true)
      setErrorInfo(null)

      try {
        const summaryResponse = await api.get(
          buildSummaryEndpoint(endpoint),
          buildLedgerRequestConfig({
            endpoint,
            params: baseRequestParams,
            signal: summaryController.signal,
          }),
        )

        startTransition(() => {
          setSummary(summaryResponse?.data || EMPTY_SUMMARY)
        })

        const rowsResponse = await api.get(
          endpoint,
          buildLedgerRequestConfig({
            endpoint,
            params: {
              ...baseRequestParams,
              page: nextPage,
              page_size: PAGE_SIZE,
            },
            signal: rowsController.signal,
          }),
        )

        const normalized = normalizeRows(rowsResponse?.data)
        startTransition(() => {
          setEntries(normalized.rows)
          setPagination({
            count: normalized.count,
            next: normalized.next,
            previous: normalized.previous,
          })
          setPage(nextPage)
          setLastAppliedSignature(requestSignature)
        })
      } catch (error) {
        if (error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
          return
        }
        const nextError = classifyLedgerError(error, endpoint)
        setErrorInfo(nextError)
        toast.error(nextError.message)
      } finally {
        setSummaryLoading(false)
        setRowsLoading(false)
      }
    },
    [activeFarmId, baseRequestParams, cancelPendingRequests, endpoint, requestSignature],
  )

  useEffect(() => {
    if (!activeFarmId) {
      setAutoLoadedFarm(null)
      setEntries([])
      setSummary(EMPTY_SUMMARY)
      setPagination({ count: 0, next: null, previous: null })
      setLastAppliedSignature('')
      setHasAttemptedLoad(false)
      setErrorInfo(null)
      return
    }

    if (autoLoadedFarm === activeFarmId) return
    setAutoLoadedFarm(activeFarmId)
    void loadLedger({ nextPage: 1 })
  }, [activeFarmId, autoLoadedFarm, loadLedger])

  const handleShowLedger = useCallback(() => {
    void loadLedger({ nextPage: 1 })
  }, [loadLedger])

  const handleRefresh = useCallback(() => {
    void loadLedger({ nextPage: page })
  }, [loadLedger, page])

  const handleReset = useCallback(() => {
    resetFilters()
    setAccountFilter('')
    setSearchText('')
    const range = createRangeFromPreset('last_30_days')
    setPeriodPreset('last_30_days')
    setDateFrom(range.from)
    setDateTo(range.to)
    setPage(1)
    setErrorInfo(null)
  }, [resetFilters])

  const handlePageChange = useCallback(
    (nextPage) => {
      if (nextPage < 1) return
      void loadLedger({ nextPage })
    },
    [loadLedger],
  )

  const filteredEntries = useMemo(() => {
    if (!searchText) return entries
    const loweredSearch = searchText.toLowerCase()
    return entries.filter((entry) => {
      const haystack = [
        entry.localized_description || entry.description || '',
        entry.account_code_name || '',
        entry.account_code || '',
        entry.id,
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(loweredSearch)
    })
  }, [entries, searchText])

  const totalPages = Math.max(1, Math.ceil((pagination.count || 0) / PAGE_SIZE))
  const totals = summary?.totals || EMPTY_SUMMARY.totals

  return (
    <div data-testid="finance-ledger-page" dir="rtl" className="app-page space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="bg-gradient-to-r from-indigo-600 to-purple-500 bg-clip-text text-4xl font-black tracking-tight text-transparent dark:from-indigo-400 dark:to-purple-200">
            دفتر الأستاذ المالي
          </h1>
          <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">
            سجل يومي للقراءة فقط مع تحميل تدريجي وفلاتر تشغيلية واضحة.
          </p>
        </div>
        <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
          للقراءة فقط
        </div>
      </div>

      <div className="space-y-3 rounded-3xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700/60 dark:bg-slate-800/80">
        <FinancialFilterBar
          filters={financialFilters}
          options={filterOptions}
          loading={filterLoading}
          setFilter={setFinancialFilter}
          dimensions={['farm', 'location', 'costCenter', 'crop_plan', 'activity']}
          className="!border-0 !bg-transparent !px-0 !py-0 !shadow-none"
        />

        <div className="flex flex-wrap items-center gap-2">
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              onClick={() => void applyPreset(preset.key)}
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
                periodPreset === preset.key
                  ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:border-indigo-400/40 dark:bg-indigo-500/10 dark:text-indigo-200'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-indigo-300 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200 dark:hover:border-indigo-400/30'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
          <label className="space-y-1 text-sm font-medium text-slate-700 dark:text-slate-200">
            <span>من تاريخ</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setPeriodPreset('custom')
                setDateFrom(event.target.value)
              }}
              className="app-input"
            />
          </label>
          <label className="space-y-1 text-sm font-medium text-slate-700 dark:text-slate-200">
            <span>إلى تاريخ</span>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => {
                setPeriodPreset('custom')
                setDateTo(event.target.value)
              }}
              className="app-input"
            />
          </label>
          <label className="space-y-1 text-sm font-medium text-slate-700 dark:text-slate-200">
            <span>الحساب</span>
            <select
              value={accountFilter}
              onChange={(event) => setAccountFilter(event.target.value)}
              className="app-input"
            >
              <option value="">جميع الحسابات</option>
              {Object.entries(ACCOUNT_LABELS).map(([code, { name }]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium text-slate-700 dark:text-slate-200">
            <span>بحث داخل النتائج الحالية</span>
            <div className="relative">
              <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="الوصف أو الحساب أو رقم القيد"
                className="app-input pr-10"
              />
            </div>
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm text-slate-500 dark:text-slate-400">
            {selectedFarm?.name ? `المزرعة الحالية: ${selectedFarm.name}` : 'اختر مزرعة لعرض القيود'}
            {hasDirtyFilters ? (
              <span className="me-3 inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
                توجد فلاتر غير مطبقة
              </span>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleShowLedger}
              disabled={!activeFarmId || summaryLoading || rowsLoading}
              className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              عرض القيود
            </button>
            <button
              type="button"
              onClick={handleRefresh}
              disabled={!activeFarmId || (!hasAttemptedLoad && !lastAppliedSignature) || summaryLoading || rowsLoading}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className="h-4 w-4" />
              تحديث
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200"
            >
              مسح
            </button>
          </div>
        </div>
      </div>

      {!activeFarmId ? (
        <InlineBanner
          errorInfo={{
            type: 'network',
            message: 'يرجى اختيار مزرعة أولًا حتى يتمكن النظام من تجهيز القيود اليومية للقراءة.',
          }}
        />
      ) : null}

      <InlineBanner errorInfo={errorInfo} onRetry={activeFarmId ? handleShowLedger : null} rowsLoading={rowsLoading && hasAttemptedLoad} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
        <SummaryCard
          title="إجمالي المدين"
          value={totals.debit}
          subValue="ريال"
          tone="emerald"
          icon={TrendingUp}
          loading={summaryLoading}
        />
        <SummaryCard
          title="إجمالي الدائن"
          value={totals.credit}
          subValue="ريال"
          tone="blue"
          icon={TrendingDown}
          loading={summaryLoading}
        />
        <SummaryCard
          title="الرصيد"
          value={totals.balance}
          subValue="ريال"
          tone={Number(totals.balance) >= 0 ? 'emerald' : 'rose'}
          icon={Calendar}
          loading={summaryLoading}
        />
        <SummaryCard
          title="عدد القيود"
          value={summaryLoading ? 0 : totals.entry_count}
          tone="violet"
          icon={FileText}
          loading={summaryLoading}
        />
      </div>

      <div className="app-panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 dark:border-white/10">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">القيود اليومية</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              يتم عرض {filteredEntries.length} من أصل {pagination.count || 0} قيدًا في الصفحة الحالية.
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <span>ترتيب افتراضي: الأحدث أولًا</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium dark:bg-white/10">
              {PAGE_SIZE} قيد/صفحة
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-right">
            <thead className="bg-slate-100/90 text-slate-600 dark:bg-white/5 dark:text-white/40">
              <tr>
                <th className="px-5 py-4 font-bold">التاريخ</th>
                <th className="px-5 py-4 font-bold">الحساب</th>
                <th className="px-5 py-4 font-bold">الوصف</th>
                <th className="px-5 py-4 font-bold">مدين</th>
                <th className="px-5 py-4 font-bold">دائن</th>
                <th className="px-5 py-4 font-bold">العملة</th>
              </tr>
            </thead>
            <tbody>
              {!activeFarmId ? (
                <tr>
                  <td colSpan="6" className="px-6 py-16 text-center text-slate-500 dark:text-slate-400">
                    اختر مزرعة ثم اضغط &quot;عرض القيود&quot;.
                  </td>
                </tr>
              ) : rowsLoading && !entries.length ? (
                Array.from({ length: 6 }).map((_, index) => (
                  <tr key={`skeleton-${index}`} className="border-t border-slate-200/70 dark:border-white/5">
                    <td colSpan="6" className="px-5 py-4">
                      <div className="h-10 animate-pulse rounded-xl bg-slate-100 dark:bg-white/5" />
                    </td>
                  </tr>
                ))
              ) : filteredEntries.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-16 text-center text-slate-500 dark:text-slate-400">
                    <Book className="mx-auto mb-4 h-12 w-12 opacity-30" />
                    {hasAttemptedLoad
                      ? 'لا توجد قيود مطابقة للفلاتر الحالية ضمن النطاق المحدد.'
                      : 'اضغط «عرض القيود» لبدء تحميل السجل اليومي.'}
                  </td>
                </tr>
              ) : (
                filteredEntries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-t border-slate-200/70 hover:bg-slate-100/70 dark:border-white/5 dark:hover:bg-white/5"
                  >
                    <td className="px-5 py-4 text-slate-600 dark:text-white/60">
                      {formatLedgerDate(entry.created_at)}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-lg border px-3 py-1.5 text-xs font-bold ${getAccountBadgeClass(entry.account_code)}`}
                      >
                        {entry.account_code_name || getAccountLabel(entry.account_code)}
                      </span>
                    </td>
                    <td className="max-w-xl px-5 py-4 font-medium text-slate-900 dark:text-white">
                      <div className="truncate">{entry.localized_description || entry.description || '-'}</div>
                    </td>
                    <td className="px-5 py-4 font-bold text-emerald-600 dark:text-emerald-300" dir="ltr">
                      {Number(entry.debit) > 0 ? formatMoney(entry.debit) : '-'}
                    </td>
                    <td className="px-5 py-4 font-bold text-blue-600 dark:text-blue-300" dir="ltr">
                      {Number(entry.credit) > 0 ? formatMoney(entry.credit) : '-'}
                    </td>
                    <td className="px-5 py-4 text-slate-500 dark:text-white/40">{entry.currency || 'YER'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm dark:border-white/10">
          <div className="text-slate-500 dark:text-slate-400">
            صفحة {page} من {totalPages}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handlePageChange(page - 1)}
              disabled={!pagination.previous || rowsLoading}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-slate-700 transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <ChevronRight className="h-4 w-4" />
              السابقة
            </button>
            <button
              type="button"
              onClick={() => handlePageChange(page + 1)}
              disabled={!pagination.next || rowsLoading}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-slate-700 transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              التالية
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-amber-300 bg-amber-50/70 p-5 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
        القيود المعروضة هنا للقراءة فقط. أي تصحيح مالي يجب أن يتم عبر قيود عكسية وخدمات الحوكمة المعتمدة، وليس عبر تعديل مباشر على السجل.
      </div>
    </div>
  )
}
