import { useState, useEffect, useMemo } from 'react'
import PropTypes from 'prop-types'
import { useCallback } from 'react'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { useAuth } from '../../auth/AuthContext'
import {
  Calendar,
  Lock,
  Unlock,
  ChevronDown,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react'
import ClosingWizard from '../Finance/components/ClosingWizard'

const parseApiErrorMessage = (error, fallback = 'تعذر إتمام العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback
  if (typeof payload === 'string' && payload.trim()) return payload
  const detail = payload?.detail
  if (Array.isArray(detail)) return detail.join(' - ')
  if (typeof detail === 'string' && detail.trim()) return detail
  return fallback
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// LOADING SKELETON
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const LoadingSkeleton = () => (
  <div className="animate-pulse space-y-6">
    <div className="h-16 bg-white/5 rounded-2xl" />
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-32 bg-white/5 rounded-2xl" />
      ))}
    </div>
    <div className="h-64 bg-white/5 rounded-xl" />
  </div>
)

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// STAT CARD
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const StatCard = ({ title, value, icon: Icon, color }) => (
  <div
    className={`rounded-2xl border border-${color}-500/30 bg-gradient-to-br from-${color}-500/10 to-transparent p-5`}
  >
    <div className="flex items-center gap-3">
      <div className={`p-2.5 bg-${color}-500/20 rounded-xl`}>
        <Icon className={`w-6 h-6 text-${color}-400`} />
      </div>
      <div>
        <p className="text-white/50 text-sm">{title}</p>
        <h3 className="text-2xl font-bold text-white">{value}</h3>
      </div>
    </div>
  </div>
)

StatCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  icon: PropTypes.elementType.isRequired,
  color: PropTypes.string.isRequired,
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// MAIN COMPONENT
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function FiscalPeriods() {
  const { selectedFarmId, farms } = useFarmContext()
  const { hasPermission, hasFarmRole, isAdmin, isSuperuser } = useAuth()
  const [fiscalYears, setFiscalYears] = useState([])
  const [periods, setPeriods] = useState([])
  const [selectedYear, setSelectedYear] = useState(null)
  const [wizardPeriod, setWizardPeriod] = useState(null)
  const [loading, setLoading] = useState(true)
  const canSoftClosePeriod =
    isAdmin || isSuperuser || hasFarmRole('manager') || hasFarmRole('admin')
  const canHardClosePeriod = isAdmin || isSuperuser || hasPermission('can_hard_close_period')

  // Fetch fiscal years for selected farm
  const fetchFiscalYears = useCallback(async () => {
    if (!selectedFarmId) return
    try {
      setLoading(true)
      const res = await api.get('/finance/fiscal-years/', {
        params: { farm: selectedFarmId },
      })
      const years = res.data.results || res.data || []
      setFiscalYears(years)
      if (years.length > 0 && !selectedYear) {
        setSelectedYear(years[0].id)
      }
    } catch (err) {
      toast.error(
        `فشل تحميل السنوات المالية: ${parseApiErrorMessage(err, 'تعذر تحميل السنوات المالية.')}`,
      )
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId, selectedYear])

  // Fetch periods for selected year
  const fetchPeriods = useCallback(async () => {
    if (!selectedYear) return
    try {
      const res = await api.get('/finance/fiscal-periods/', {
        params: { fiscal_year: selectedYear },
      })
      setPeriods(res.data.results || res.data || [])
    } catch (err) {
      toast.error(
        `فشل تحميل الفترات المالية: ${parseApiErrorMessage(err, 'تعذر تحميل الفترات المالية.')}`,
      )
    }
  }, [selectedYear])

  useEffect(() => {
    fetchFiscalYears()
  }, [fetchFiscalYears])

  useEffect(() => {
    fetchPeriods()
  }, [fetchPeriods])

  // Triple-close wizard launcher
  const openClosingWizard = (period) => {
    if (!canSoftClosePeriod) {
      toast.error('لا تملك صلاحية تنفيذ الإغلاق المالي.')
      return
    }
    setWizardPeriod(period)
  }

  // Stats
  const stats = useMemo(() => {
    const open = periods.filter((p) => !p.is_closed).length
    const closed = periods.filter((p) => p.is_closed).length
    return { open, closed, total: periods.length }
  }, [periods])

  // Month names in Arabic
  const monthNames = [
    'يناير',
    'فبراير',
    'مارس',
    'أبريل',
    'مايو',
    'يونيو',
    'يوليو',
    'أغسطس',
    'سبتمبر',
    'أكتوبر',
    'نوفمبر',
    'ديسمبر',
  ]

  const selectedFarm = farms?.find((f) => f.id === selectedFarmId)

  return (
    <div
      data-testid="finance-fiscal-periods-page"
      dir="rtl"
      className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8 space-y-8"
    >
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-purple-600 dark:from-purple-400 to-pink-500 bg-clip-text text-transparent">
            الفترات المالية
          </h1>
          <p className="text-gray-500 dark:text-zinc-500 font-medium mt-1">
            إدارة السنوات والفترات المالية - {selectedFarm?.name || 'اختر مزرعة'}
          </p>
        </div>
        <button
          onClick={() => {
            fetchFiscalYears()
            fetchPeriods()
          }}
          className="p-3 rounded-xl bg-white/5 border border-white/10 text-white/60 hover:text-white hover:bg-white/10 transition-all"
          aria-label="تحديث البيانات"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {!selectedFarmId ? (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6 text-center">
          <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
          <p className="text-white/70">يرجى اختيار مزرعة من الشريط العلوي لعرض الفترات المالية</p>
        </div>
      ) : loading ? (
        <LoadingSkeleton />
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard title="فترات مفتوحة" value={stats.open} icon={Unlock} color="emerald" />
            <StatCard title="فترات مغلقة" value={stats.closed} icon={Lock} color="rose" />
            <StatCard title="إجمالي الفترات" value={stats.total} icon={Calendar} color="blue" />
          </div>

          {/* Year Selector */}
          <div className="rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl p-4 flex items-center gap-4">
            <Calendar className="w-5 h-5 text-white/40" />
            <span className="text-white/60">السنة المالية:</span>
            <div className="relative">
              <select
                value={selectedYear || ''}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="appearance-none pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white focus:border-purple-500/50 focus:outline-none min-w-[150px]"
                aria-label="اختر السنة المالية"
              >
                {fiscalYears.length === 0 ? (
                  <option value="">لا توجد سنوات مالية</option>
                ) : (
                  fiscalYears.map((fy) => (
                    <option key={fy.id} value={fy.id}>
                      {fy.year} {fy.is_closed ? '(مغلقة)' : ''}
                    </option>
                  ))
                )}
              </select>
              <ChevronDown className="absolute left-3 top-2.5 w-4 h-4 text-white/30 pointer-events-none" />
            </div>
          </div>

          {/* Periods Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {periods.length === 0 ? (
              <div className="col-span-full rounded-2xl border border-white/10 bg-white/5 p-8 text-center">
                <Clock className="w-12 h-12 text-white/20 mx-auto mb-3" />
                <p className="text-white/40">لا توجد فترات لهذه السنة</p>
              </div>
            ) : (
              periods.map((period) => (
                <div
                  key={period.id}
                  className={`rounded-2xl border p-4 transition-all ${
                    period.is_closed
                      ? 'border-rose-500/30 bg-rose-500/5'
                      : 'border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-lg font-bold text-white">
                      {monthNames[period.month - 1] || `شهر ${period.month}`}
                    </span>
                    {period.is_closed ? (
                      <Lock className="w-4 h-4 text-rose-400" />
                    ) : (
                      <Unlock className="w-4 h-4 text-emerald-400" />
                    )}
                  </div>

                  <div className="text-xs text-white/40 mb-3">
                    {new Date(period.start_date).toLocaleDateString('ar-SA')} -{' '}
                    {new Date(period.end_date).toLocaleDateString('ar-SA')}
                  </div>

                  {period.is_closed ? (
                    <div className="flex items-center gap-1 text-xs text-rose-400">
                      <CheckCircle className="w-3 h-3" />
                      مغلقة
                    </div>
                  ) : canSoftClosePeriod ? (
                    <button
                      onClick={() => openClosingWizard(period)}
                      className="w-full py-2 rounded-xl bg-rose-500/20 text-rose-400 text-xs font-bold hover:bg-rose-500/30 transition-colors"
                      aria-label={`معالج الإغلاق ${monthNames[period.month - 1]}`}
                    >
                      معالج الإغلاق
                    </button>
                  ) : (
                    <div className="flex items-center gap-1 text-xs text-amber-400">
                      <AlertCircle className="w-3 h-3" />
                      لا تملك صلاحية الإغلاق
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Info Notice */}
          <div className="rounded-2xl border border-purple-500/20 bg-purple-500/5 p-5">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-purple-400 mt-0.5" />
              <div className="text-sm text-white/60">
                <strong className="text-purple-400">ملاحظة:</strong> معالج الإغلاق المالي يمنع إضافة
                أي معاملات جديدة بتاريخ ضمن تلك الفترة. أي تصحيحات يجب أن تتم في فترة مفتوحة عبر
                قيود عكسية.
              </div>
            </div>
          </div>
        </>
      )}

      {wizardPeriod && (
        <ClosingWizard
          period={wizardPeriod}
          canHardClose={canHardClosePeriod}
          onClose={() => setWizardPeriod(null)}
          onComplete={() => {
            fetchPeriods()
          }}
        />
      )}
    </div>
  )
}
