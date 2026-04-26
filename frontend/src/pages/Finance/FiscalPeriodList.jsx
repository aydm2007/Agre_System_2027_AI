/**
 * [AGRI-GUARDIAN] Fiscal Period Management Page
 * Strict Mode only — full ERP fiscal lifecycle management.
 *
 * Compliance:
 * - Axis 3: Fiscal Lifecycle (open → soft-close → hard-close)
 * - Axis 6: Farm-scoped periods
 * - AGENTS.md §94-102: Period closing rules
 *
 * data-testid: finance-fiscal-periods-page
 */
import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { useAuth } from '../../auth/AuthContext'
import {
  Calendar,
  Lock,
  Unlock,
  AlertTriangle,
  CheckCircle,
  Clock,
  ChevronRight,
  Shield,
  RefreshCw,
} from 'lucide-react'
import ClosingWizard from './components/ClosingWizard'

// ─────────────────────────────────────────────────────────────────
// STATUS DESIGN TOKENS
// ─────────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  open: {
    label: 'مفتوحة',
    icon: Unlock,
    color: 'emerald',
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    text: 'text-emerald-700 dark:text-emerald-400',
    border: 'border-emerald-200 dark:border-emerald-800',
    badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    glow: 'shadow-emerald-200/50 dark:shadow-emerald-900/30',
  },
  'soft-close': {
    label: 'إغلاق مبدئي',
    icon: Clock,
    color: 'amber',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    text: 'text-amber-700 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800',
    badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    glow: 'shadow-amber-200/50 dark:shadow-amber-900/30',
  },
  'hard-close': {
    label: 'مغلقة نهائياً',
    icon: Lock,
    color: 'slate',
    bg: 'bg-slate-100 dark:bg-slate-800/40',
    text: 'text-slate-600 dark:text-slate-400',
    border: 'border-slate-200 dark:border-slate-700',
    badge: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
    glow: 'shadow-slate-200/30 dark:shadow-slate-900/20',
  },
}

// ─────────────────────────────────────────────────────────────────
// SKELETON LOADER
// ─────────────────────────────────────────────────────────────────

function PeriodSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="h-24 bg-gray-200 dark:bg-slate-700 rounded-2xl" />
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// PERIOD CARD COMPONENT
// ─────────────────────────────────────────────────────────────────

function PeriodCard({ period, onClose, isAdmin }) {
  const config = STATUS_CONFIG[period.status] || STATUS_CONFIG.open
  const Icon = config.icon
  const isLocked = period.status === 'hard-close'

  return (
    <div
      className={`
        relative overflow-hidden rounded-2xl border
        ${config.border} ${config.bg}
        shadow-lg ${config.glow}
        transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5
      `}
    >
      {/* Top gradient bar */}
      <div
        className={`h-1 bg-gradient-to-r ${
          period.status === 'open'
            ? 'from-emerald-400 to-teal-500'
            : period.status === 'soft-close'
              ? 'from-amber-400 to-orange-500'
              : 'from-slate-400 to-slate-500'
        }`}
      />

      <div className="p-5">
        <div className="flex items-center justify-between">
          {/* Left: Period info */}
          <div className="flex items-center gap-4">
            <div
              className={`p-3 rounded-xl ${config.badge} transition-transform duration-200 hover:scale-105`}
            >
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-slate-100">
                {period.name || `الفترة ${period.period_number || period.id}`}
              </h3>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-slate-400">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  {period.start_date}
                </span>
                <ChevronRight className="w-3 h-3" />
                <span>{period.end_date}</span>
              </div>
            </div>
          </div>

          {/* Right: Status badge + Actions */}
          <div className="flex items-center gap-3">
            <span
              className={`
                inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold
                ${config.badge}
                transition-all duration-200
              `}
            >
              <Icon className="w-3 h-3" />
              {config.label}
            </span>

            {!isLocked && isAdmin && (
              <button
                onClick={() => onClose(period)}
                className={`
                  inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                  transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5
                  ${
                    period.status === 'open'
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-amber-300/30'
                      : 'bg-gradient-to-r from-slate-600 to-slate-700 text-white shadow-slate-400/30'
                  }
                `}
              >
                <Shield className="w-4 h-4" />
                {period.status === 'open' ? 'إغلاق مبدئي' : 'إغلاق نهائي'}
              </button>
            )}

            {isLocked && (
              <div className="flex items-center gap-1.5 text-slate-400">
                <Lock className="w-4 h-4" />
                <span className="text-xs">غير قابلة للتعديل</span>
              </div>
            )}
          </div>
        </div>

        {/* Warning for soft-close */}
        {period.status === 'soft-close' && (
          <div className="mt-3 flex items-start gap-2 p-3 rounded-xl bg-amber-100/50 dark:bg-amber-900/10 border border-amber-200/50 dark:border-amber-800/30">
            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-700 dark:text-amber-400">
              الفترة في وضع الإغلاق المبدئي — يُسمح فقط بقيود التسوية. الإغلاق النهائي لا رجعة فيه.
            </p>
          </div>
        )}

        {/* Hard-close stamp */}
        {isLocked && (
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-500">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>تم الإغلاق النهائي — التصحيح يتطلب قيد عكسي في الفترة التالية</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────

export default function FiscalPeriodList() {
  const [loading, setLoading] = useState(true)
  const [periods, setPeriods] = useState([])
  const [fiscalYears, setFiscalYears] = useState([])
  const [selectedYear, setSelectedYear] = useState(null)
  const [closingTarget, setClosingTarget] = useState(null)
  const { farmId } = useFarmContext()
  const { isAdmin, is_superuser } = useAuth()
  const canManage = isAdmin || is_superuser

  const fetchFiscalYears = useCallback(async () => {
    if (!farmId) return
    try {
      const res = await api.get('/fiscal-years/', { params: { farm_id: farmId } })
      const years = Array.isArray(res.data) ? res.data : res.data?.results || []
      setFiscalYears(years)
      setSelectedYear((current) => current || years[0]?.id || null)
    } catch (err) {
      toast.error('فشل تحميل السنوات المالية')
    }
  }, [farmId])

  const fetchPeriods = useCallback(async () => {
    if (!selectedYear) return
    setLoading(true)
    try {
      const res = await api.get('/fiscal-periods/', {
        params: { fiscal_year: selectedYear, farm_id: farmId },
      })
      setPeriods(Array.isArray(res.data) ? res.data : res.data?.results || [])
    } catch (err) {
      toast.error('فشل تحميل الفترات المالية')
    } finally {
      setLoading(false)
    }
  }, [selectedYear, farmId])

  useEffect(() => {
    fetchFiscalYears()
  }, [fetchFiscalYears])
  useEffect(() => {
    fetchPeriods()
  }, [fetchPeriods])

  const openCount = periods.filter((p) => p.status === 'open').length
  const softCloseCount = periods.filter((p) => p.status === 'soft-close').length
  const hardCloseCount = periods.filter((p) => p.status === 'hard-close').length

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-6"
      data-testid="finance-fiscal-periods-page"
    >
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent">
            الفترات المالية
          </h1>
          <p className="text-gray-500 dark:text-slate-400 mt-1">
            إدارة دورة الحياة المالية — مفتوح → إغلاق مبدئي → إغلاق نهائي
          </p>
        </div>
        <button
          onClick={() => {
            fetchFiscalYears()
            fetchPeriods()
          }}
          className="p-3 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all duration-200"
          title="تحديث"
        >
          <RefreshCw className="w-5 h-5 text-gray-500 dark:text-slate-400" />
        </button>
      </div>

      {/* Year Selector */}
      {fiscalYears.length > 0 && (
        <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
          {fiscalYears.map((year) => (
            <button
              key={year.id}
              onClick={() => setSelectedYear(year.id)}
              className={`
                px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                ${
                  selectedYear === year.id
                    ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/30'
                    : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700 hover:shadow-md'
                }
              `}
            >
              {year.name || year.year || year.id}
            </button>
          ))}
        </div>
      )}

      {/* Status Summary Cards */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200/50 dark:border-emerald-800/30 text-center">
          <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-400">
            {openCount}
          </div>
          <div className="text-xs text-emerald-600 dark:text-emerald-500 mt-1">مفتوحة</div>
        </div>
        <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200/50 dark:border-amber-800/30 text-center">
          <div className="text-2xl font-bold text-amber-700 dark:text-amber-400">
            {softCloseCount}
          </div>
          <div className="text-xs text-amber-600 dark:text-amber-500 mt-1">إغلاق مبدئي</div>
        </div>
        <div className="p-4 rounded-2xl bg-slate-100 dark:bg-slate-800/30 border border-slate-200/50 dark:border-slate-700/30 text-center">
          <div className="text-2xl font-bold text-slate-700 dark:text-slate-400">
            {hardCloseCount}
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-500 mt-1">مغلقة نهائياً</div>
        </div>
      </div>

      {/* Periods List */}
      {loading ? (
        <PeriodSkeleton />
      ) : periods.length === 0 ? (
        <div className="text-center py-16">
          <Calendar className="w-16 h-16 mx-auto text-gray-300 dark:text-slate-600 mb-4" />
          <h3 className="text-lg font-medium text-gray-500 dark:text-slate-400">
            لا توجد فترات مالية
          </h3>
          <p className="text-sm text-gray-400 dark:text-slate-500 mt-1">
            قم بإنشاء سنة مالية أولاً من الإعدادات
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {periods.map((period) => (
            <PeriodCard
              key={period.id}
              period={period}
              onClose={(p) => setClosingTarget(p)}
              isAdmin={canManage}
            />
          ))}
        </div>
      )}

      {/* Closing Wizard Modal */}
      {closingTarget && (
        <ClosingWizard
          period={closingTarget}
          onClose={() => {
            setClosingTarget(null)
            fetchPeriods()
          }}
        />
      )}
    </div>
  )
}
