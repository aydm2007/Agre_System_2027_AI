/**
 * TimesheetPage — صفحة تسجيل واعتماد الدوام
 *
 * AGENTS.md Compliance:
 * - §139-144: HR Admin Segregation (OFFICIAL=attendance, CASUAL=crop-cost)
 * - Axis 5: Surra is the financial labor unit
 * - Axis 6: Farm-scoped data
 * - Axis 7: Maker-Checker approval
 * - §29: RTL + dark: classes
 * - §32: data-testid contracts
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '../../api/client'
import { useFarmContext } from '../../api/farmContext.jsx'
import { formatMoney, toDecimal } from '../../utils/decimal'
import {
  Calendar,
  CheckCircle,
  Users,
  Clock,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'

// ─── Month navigation ───────────────────────────────────────────────────────
const MONTH_NAMES_AR = [
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

export default function TimesheetPage() {
  const { selectedFarmId } = useFarmContext()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [summary, setSummary] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // ─── Fetch monthly summary ──────────────────────────────────────────────
  const fetchSummary = useCallback(async () => {
    if (!selectedFarmId) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/core/timesheets/monthly-summary/', {
        params: { farm: selectedFarmId, year, month },
      })
      setSummary(res.data || [])
    } catch (err) {
      console.error('Failed to load timesheet summary:', err)
      setError('فشل تحميل ملخص الدوام')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId, year, month])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  // ─── Navigation helpers ──────────────────────────────────────────────────
  const goPrev = () => {
    if (month === 1) {
      setMonth(12)
      setYear((y) => y - 1)
    } else setMonth((m) => m - 1)
  }
  const goNext = () => {
    if (month === 12) {
      setMonth(1)
      setYear((y) => y + 1)
    } else setMonth((m) => m + 1)
  }

  // ─── Totals ──────────────────────────────────────────────────────────────
  const totals = useMemo(() => {
    let totalSurrah = 0,
      totalCost = 0,
      totalDays = 0
    for (const row of summary) {
      totalSurrah += toDecimal(row.total_surrah, 1)
      totalCost += toDecimal(row.estimated_cost, 2)
      totalDays += row.days_count || 0
    }
    return { totalSurrah, totalCost, totalDays }
  }, [summary])

  // ─── Category label ──────────────────────────────────────────────────────
  const catLabel = (cat) => (cat === 'OFFICIAL' ? 'رسمي (مركزي)' : 'أجر يومي (ذاتي)')

  const catBadge = (cat) =>
    cat === 'OFFICIAL'
      ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'

  if (!selectedFarmId) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center text-gray-400">
          <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>الرجاء اختيار مزرعة أولاً</p>
        </div>
      </div>
    )
  }

  return (
    <div data-testid="timesheet-page" className="space-y-6 p-4 md:p-6" dir="rtl">
      {/* ─── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Calendar className="w-7 h-7 text-emerald-400" />
            سجل الدوام الشهري
          </h1>
          <p className="text-sm text-gray-400 mt-1">نظام الصُرّة — تسجيل ومتابعة حضور الموظفين</p>
        </div>

        {/* Month nav */}
        <div className="flex items-center gap-2 bg-gray-800/60 rounded-xl px-3 py-2 border border-gray-700/50">
          <button onClick={goNext} className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors">
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </button>
          <span
            data-testid="timesheet-month-label"
            className="text-white font-semibold min-w-[140px] text-center"
          >
            {MONTH_NAMES_AR[month - 1]} {year}
          </span>
          <button onClick={goPrev} className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors">
            <ChevronLeft className="w-5 h-5 text-gray-400" />
          </button>
          <button
            onClick={fetchSummary}
            className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors mr-2"
          >
            <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ─── Stats Cards ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-emerald-500/10 to-transparent border border-emerald-500/20 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/20 p-2.5 rounded-lg">
              <Users className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-gray-400 text-xs">عدد الموظفين</p>
              <p data-testid="timesheet-employee-count" className="text-xl font-bold text-white">
                {summary.length}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-gradient-to-br from-blue-500/10 to-transparent border border-blue-500/20 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/20 p-2.5 rounded-lg">
              <Clock className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-gray-400 text-xs">إجمالي الصُرّة</p>
              <p data-testid="timesheet-total-surrah" className="text-xl font-bold text-white">
                {totals.totalSurrah.toLocaleString('en-US', { minimumFractionDigits: 1 })}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/20 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="bg-amber-500/20 p-2.5 rounded-lg">
              <CheckCircle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-gray-400 text-xs">التكلفة التقديرية</p>
              <p data-testid="timesheet-total-cost" className="text-xl font-bold text-white">
                {formatMoney
                  ? formatMoney(totals.totalCost)
                  : totals.totalCost.toLocaleString('en-US', { minimumFractionDigits: 2 })}{' '}
                ر.ي
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Summary Table ──────────────────────────────────────────────── */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-300 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table data-testid="timesheet-table" className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/50 bg-gray-800/60">
                <th className="px-4 py-3 text-right text-gray-400 font-medium">الموظف</th>
                <th className="px-4 py-3 text-right text-gray-400 font-medium">الرقم الوظيفي</th>
                <th className="px-4 py-3 text-center text-gray-400 font-medium">الفئة</th>
                <th className="px-4 py-3 text-center text-gray-400 font-medium">أيام العمل</th>
                <th className="px-4 py-3 text-center text-gray-400 font-medium">إجمالي الصُرّة</th>
                <th className="px-4 py-3 text-center text-gray-400 font-medium">الإضافي</th>
                <th className="px-4 py-3 text-center text-gray-400 font-medium">المعتمد</th>
                <th className="px-4 py-3 text-left text-gray-400 font-medium">التكلفة (ر.ي)</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    جار التحميل...
                  </td>
                </tr>
              ) : summary.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                    <Calendar className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    لا توجد سجلات دوام لهذا الشهر
                  </td>
                </tr>
              ) : (
                summary.map((row) => (
                  <tr
                    key={row.employee_id}
                    className="border-b border-gray-700/30 hover:bg-gray-700/20 transition-colors"
                  >
                    <td className="px-4 py-3 text-white font-medium">{row.employee_name}</td>
                    <td className="px-4 py-3 text-gray-300 font-mono text-xs">{row.badge}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs border ${catBadge(row.category)}`}
                      >
                        {catLabel(row.category)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-200">{row.days_count}</td>
                    <td className="px-4 py-3 text-center text-white font-semibold">
                      {toDecimal(row.total_surrah, 1).toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-center text-amber-300">
                      {toDecimal(row.total_overtime, 2) > 0
                        ? `+${toDecimal(row.total_overtime, 2).toFixed(2)}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`text-xs ${row.approved_count === row.days_count ? 'text-emerald-400' : 'text-amber-400'}`}
                      >
                        {row.approved_count}/{row.days_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-left">
                      {row.category === 'OFFICIAL' ? (
                        <span className="text-gray-500 text-xs">حضور فقط</span>
                      ) : (
                        <span className="text-emerald-300 font-semibold">
                          {formatMoney(row.estimated_cost)}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            {summary.length > 0 && (
              <tfoot>
                <tr className="bg-gray-800/60 border-t border-gray-600/50">
                  <td colSpan={3} className="px-4 py-3 text-white font-bold">
                    الإجمالي
                  </td>
                  <td className="px-4 py-3 text-center text-white font-bold">{totals.totalDays}</td>
                  <td className="px-4 py-3 text-center text-white font-bold">
                    {totals.totalSurrah.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-center">—</td>
                  <td className="px-4 py-3 text-center">—</td>
                  <td className="px-4 py-3 text-left text-emerald-300 font-bold">
                    {formatMoney
                      ? formatMoney(totals.totalCost)
                      : totals.totalCost.toLocaleString('en-US', { minimumFractionDigits: 2 })}{' '}
                    ر.ي
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* ─── Legend ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500 px-2">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
          رسمي = حضور فقط (§139 AGENTS.md)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
          أجر يومي = تكلفة محصول
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
          الوحدة المالية: الصُرّة (Axis 5)
        </span>
      </div>
    </div>
  )
}
