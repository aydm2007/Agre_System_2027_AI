import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { useAuth } from '../../auth/AuthContext'
import {
  Calendar,
  CheckCircle,
  Clock,
  Lock,
  RefreshCw,
  RotateCcw,
  Shield,
  Unlock,
} from 'lucide-react'
import ClosingWizard from './components/ClosingWizard'

const normalizePeriodStatus = (status) => String(status || 'open').toLowerCase().replace(/-/g, '_')

const STATUS_CONFIG = {
  open: {
    label: 'مفتوحة',
    icon: Unlock,
    badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
    panel: 'bg-emerald-50 dark:bg-emerald-900/10',
  },
  soft_close: {
    label: 'إغلاق مبدئي',
    icon: Clock,
    badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    border: 'border-amber-200 dark:border-amber-800',
    panel: 'bg-amber-50 dark:bg-amber-900/10',
  },
  hard_close: {
    label: 'مغلقة نهائياً',
    icon: Lock,
    badge: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
    border: 'border-slate-200 dark:border-slate-700',
    panel: 'bg-slate-100 dark:bg-slate-800/40',
  },
}

const parseApiErrorMessage = (error, fallback = 'تعذر إتمام العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback
  if (typeof payload === 'string' && payload.trim()) return payload
  if (typeof payload?.detail === 'string' && payload.detail.trim()) return payload.detail
  if (typeof payload?.error === 'string' && payload.error.trim()) return payload.error
  return fallback
}

function PeriodCard({ period, canManage, canReopen, onManage }) {
  const status = normalizePeriodStatus(period.status)
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.open
  const Icon = config.icon

  let actionLabel = ''
  if (status === 'open' && canManage) actionLabel = 'بدء الإغلاق'
  if (status === 'soft_close' && canManage) actionLabel = 'إدارة الإغلاق'
  if (status === 'hard_close' && canReopen) actionLabel = 'إعادة فتح'

  return (
    <div
      className={`rounded-2xl border p-5 shadow-sm transition-all ${config.border} ${config.panel}`}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className={`rounded-xl p-3 ${config.badge}`}>
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                {period.name || `الفترة ${period.month}`}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                <Calendar className="h-4 w-4" />
                <span>{period.start_date}</span>
                <span>حتى</span>
                <span>{period.end_date}</span>
              </div>
            </div>
          </div>

          {status === 'soft_close' ? (
            <p className="text-sm text-amber-800 dark:text-amber-300">
              الفترة في وضع مراجعة. يمكن الإغلاق النهائي أو إعادة الفتح المحكومة حسب الصلاحيات.
            </p>
          ) : null}
          {status === 'hard_close' ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">
              الفترة مغلقة نهائياً. إعادة الفتح تترك أثراً تدقيقياً وتتطلب اعتماداً قطاعياً.
            </p>
          ) : null}
        </div>

        <div className="flex flex-col items-start gap-3 md:items-end">
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-bold ${config.badge}`}>
            <Icon className="h-3.5 w-3.5" />
            {config.label}
          </span>

          {actionLabel ? (
            <button
              type="button"
              onClick={() => onManage(period)}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
            >
              {actionLabel}
            </button>
          ) : (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              لا توجد إجراءات متاحة لهذا المستخدم
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default function FiscalPeriodList() {
  const { selectedFarmId, farms } = useFarmContext()
  const { hasPermission, hasFarmRole, isAdmin, isSuperuser } = useAuth()
  const [loading, setLoading] = useState(true)
  const [fiscalYears, setFiscalYears] = useState([])
  const [periods, setPeriods] = useState([])
  const [selectedYear, setSelectedYear] = useState('')
  const [activePeriod, setActivePeriod] = useState(null)

  const canSoftClosePeriod =
    isAdmin || isSuperuser || hasFarmRole('manager') || hasFarmRole('admin')
  const canHardClosePeriod =
    isAdmin || isSuperuser || hasPermission('can_hard_close_period')
  const canReopenPeriod = canHardClosePeriod

  const selectedFarm = useMemo(
    () => farms?.find((farm) => String(farm.id) === String(selectedFarmId)) || null,
    [farms, selectedFarmId],
  )

  const fetchFiscalYears = useCallback(async () => {
    if (!selectedFarmId) {
      setFiscalYears([])
      setSelectedYear('')
      return
    }

    try {
      const response = await api.get('/finance/fiscal-years/', {
        params: { farm: selectedFarmId },
      })
      const years = Array.isArray(response.data) ? response.data : response.data?.results || []
      setFiscalYears(years)
      setSelectedYear((current) =>
        current && years.some((year) => String(year.id) === String(current))
          ? current
          : years[0]?.id || '',
      )
    } catch (error) {
      toast.error(parseApiErrorMessage(error, 'فشل تحميل السنوات المالية'))
    }
  }, [selectedFarmId])

  const fetchPeriods = useCallback(async () => {
    if (!selectedYear || !selectedFarmId) {
      setPeriods([])
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const response = await api.get('/finance/fiscal-periods/', {
        params: { fiscal_year: selectedYear, farm: selectedFarmId },
      })
      const records = Array.isArray(response.data) ? response.data : response.data?.results || []
      setPeriods(records)
    } catch (error) {
      toast.error(parseApiErrorMessage(error, 'فشل تحميل الفترات المالية'))
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId, selectedYear])

  useEffect(() => {
    setLoading(true)
    fetchFiscalYears().finally(() => setLoading(false))
  }, [fetchFiscalYears])

  useEffect(() => {
    fetchPeriods()
  }, [fetchPeriods])

  const normalizedPeriods = useMemo(
    () =>
      periods.map((period) => ({
        ...period,
        normalizedStatus: normalizePeriodStatus(period.status),
      })),
    [periods],
  )

  const stats = useMemo(() => {
    const open = normalizedPeriods.filter((period) => period.normalizedStatus === 'open').length
    const softClosed = normalizedPeriods.filter(
      (period) => period.normalizedStatus === 'soft_close',
    ).length
    const hardClosed = normalizedPeriods.filter(
      (period) => period.normalizedStatus === 'hard_close',
    ).length
    return { open, softClosed, hardClosed }
  }, [normalizedPeriods])

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 p-6 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950"
      data-testid="finance-fiscal-periods-page"
      dir="rtl"
    >
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="bg-gradient-to-r from-indigo-600 to-cyan-500 bg-clip-text text-3xl font-extrabold text-transparent">
            الفترات المالية
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            إدارة دورة الفترة المالية من واجهة موحدة للمزرعة المحددة.
          </p>
          {selectedFarm ? (
            <p className="mt-1 text-sm font-medium text-slate-700 dark:text-slate-200">
              المزرعة الحالية: {selectedFarm.name}
            </p>
          ) : null}
        </div>

        <button
          type="button"
          onClick={() => {
            fetchFiscalYears()
            fetchPeriods()
          }}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
        >
          <RefreshCw className="h-4 w-4" />
          تحديث
        </button>
      </div>

      {!selectedFarmId ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-amber-900 dark:border-amber-800 dark:bg-amber-900/10 dark:text-amber-200">
          اختر مزرعة من الشريط العلوي لعرض السنوات والفترات المالية الخاصة بها.
        </div>
      ) : (
        <>
          <div className="mb-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-900/10">
              <div className="flex items-center gap-2 text-sm font-bold text-emerald-700 dark:text-emerald-300">
                <Unlock className="h-4 w-4" />
                فترات مفتوحة
              </div>
              <div className="mt-2 text-2xl font-black text-emerald-900 dark:text-emerald-100">
                {stats.open}
              </div>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/10">
              <div className="flex items-center gap-2 text-sm font-bold text-amber-700 dark:text-amber-300">
                <Clock className="h-4 w-4" />
                إغلاق مبدئي
              </div>
              <div className="mt-2 text-2xl font-black text-amber-900 dark:text-amber-100">
                {stats.softClosed}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-100 p-4 dark:border-slate-700 dark:bg-slate-800/40">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                <Lock className="h-4 w-4" />
                مغلقة نهائياً
              </div>
              <div className="mt-2 text-2xl font-black text-slate-900 dark:text-slate-100">
                {stats.hardClosed}
              </div>
            </div>
          </div>

          <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <label className="mb-2 block text-sm font-bold text-slate-700 dark:text-slate-200">
              السنة المالية
            </label>
            <select
              value={selectedYear}
              onChange={(event) => setSelectedYear(event.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
            >
              {fiscalYears.length === 0 ? (
                <option value="">لا توجد سنوات مالية</option>
              ) : (
                fiscalYears.map((year) => (
                  <option key={year.id} value={year.id}>
                    {year.name || year.year || year.id}
                  </option>
                ))
              )}
            </select>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
              جاري تحميل الفترات المالية...
            </div>
          ) : normalizedPeriods.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
              لا توجد فترات مالية لهذه السنة.
            </div>
          ) : (
            <div className="space-y-4">
              {normalizedPeriods.map((period) => (
                <PeriodCard
                  key={period.id}
                  period={period}
                  canManage={canSoftClosePeriod}
                  canReopen={canReopenPeriod}
                  onManage={setActivePeriod}
                />
              ))}
            </div>
          )}
        </>
      )}

      {activePeriod ? (
        <ClosingWizard
          period={activePeriod}
          canHardClose={canHardClosePeriod}
          canReopen={canReopenPeriod}
          onClose={() => setActivePeriod(null)}
          onComplete={() => {
            fetchFiscalYears()
            fetchPeriods()
          }}
        />
      ) : null}
    </div>
  )
}
