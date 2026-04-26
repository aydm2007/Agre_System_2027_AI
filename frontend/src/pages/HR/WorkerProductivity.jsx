/**
 * WorkerProductivity — لوحة مؤشرات أداء العمال
 *
 * AGENTS.md Compliance:
 * - §297-301: Required KPI Outputs (Daily labor cost variance)
 * - §139-144: HR Admin Segregation (OFFICIAL/CASUAL)
 * - Axis 5: Surra financial unit display
 * - Axis 6: Farm-scoped
 * - §29: RTL + dark: classes
 * - §32: data-testid contracts
 */
import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import { useFarmContext } from '../../api/farmContext.jsx'
import { formatMoney, toDecimal } from '../../utils/decimal'
import {
  BarChart3,
  Users,
  Clock,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

export default function WorkerProductivity() {
  const { selectedFarmId } = useFarmContext()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(true)

  const fetchKPI = useCallback(async () => {
    if (!selectedFarmId) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/worker-kpi/', {
        params: { farm: selectedFarmId },
      })
      setData(res.data)
    } catch (err) {
      console.error('Failed to load worker KPI:', err)
      setError('فشل تحميل مؤشرات الأداء')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    fetchKPI()
  }, [fetchKPI])

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

  const s = data?.summary || {}
  const as_ = data?.activity_stats || {}

  return (
    <div data-testid="worker-kpi-page" className="space-y-6 p-4 md:p-6" dir="rtl">
      {/* ─── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-violet-400" />
            إنتاجية العمال
          </h1>
          <p className="text-sm text-gray-400 mt-1">مؤشرات أداء الموارد البشرية — نظام الصُرّة</p>
        </div>
        <button
          onClick={fetchKPI}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-violet-600/20 text-violet-300 rounded-xl border border-violet-500/30 hover:bg-violet-600/30 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          تحديث
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-300 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" /> {error}
        </div>
      )}

      {loading && !data && (
        <div className="text-center py-16 text-gray-500">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3" />
          جار تحميل المؤشرات...
        </div>
      )}

      {data && (
        <>
          {/* ─── Top KPI Cards ─────────────────────────────────────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              icon={<Users className="w-5 h-5" />}
              label="موظفون نشطون"
              value={s.unique_employees || 0}
              color="emerald"
              testId="kpi-employees"
            />
            <KPICard
              icon={<Clock className="w-5 h-5" />}
              label="إجمالي الصُرّة"
              value={toDecimal(s.total_surrah, 1).toFixed(1)}
              color="blue"
              testId="kpi-surrah"
            />
            <KPICard
              icon={<TrendingUp className="w-5 h-5" />}
              label="متوسط الصُرّة / يوم"
              value={toDecimal(s.avg_surrah_per_day, 2).toFixed(2)}
              color="violet"
              testId="kpi-avg-surrah"
            />
            <KPICard
              icon={<BarChart3 className="w-5 h-5" />}
              label="نسبة الاعتماد"
              value={`${s.approval_rate || '0.0'}%`}
              color="amber"
              testId="kpi-approval"
            />
          </div>

          {/* ─── Activity Stats ────────────────────────────────────────── */}
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-5">
            <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-gray-400" />
              إحصائيات الأنشطة
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatItem label="تعيينات رسمية" value={as_.registered_assignments || 0} />
              <StatItem label="دفعات مؤقتة" value={as_.casual_batches || 0} />
              <StatItem
                label="عمال مؤقتون"
                value={toDecimal(as_.casual_workers_total, 0).toString()}
              />
              <StatItem
                label="تكلفة الأجور"
                value={`${formatMoney(as_.total_wage_cost)} ر.ي`}
                highlight
              />
            </div>
          </div>

          {/* ─── Worker Table ──────────────────────────────────────────── */}
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
            <button
              onClick={() => setExpanded(!expanded)}
              className="w-full flex items-center justify-between px-5 py-4 text-white font-semibold hover:bg-gray-700/20 transition-colors"
            >
              <span className="flex items-center gap-2">
                <Users className="w-4 h-4 text-gray-400" />
                تفاصيل الموظفين ({(data.workers || []).length})
              </span>
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {expanded && (
              <div className="overflow-x-auto">
                <table data-testid="worker-kpi-table" className="w-full text-sm">
                  <thead>
                    <tr className="border-t border-b border-gray-700/50 bg-gray-800/60">
                      <th className="px-4 py-3 text-right text-gray-400 font-medium">الاسم</th>
                      <th className="px-4 py-3 text-center text-gray-400 font-medium">الفئة</th>
                      <th className="px-4 py-3 text-center text-gray-400 font-medium">الأيام</th>
                      <th className="px-4 py-3 text-center text-gray-400 font-medium">الصُرّة</th>
                      <th className="px-4 py-3 text-center text-gray-400 font-medium">الإضافي</th>
                      <th className="px-4 py-3 text-center text-gray-400 font-medium">الأداء</th>
                      <th className="px-4 py-3 text-left text-gray-400 font-medium">التكلفة</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.workers || []).map((w) => (
                      <tr
                        key={w.employee_id}
                        className="border-b border-gray-700/30 hover:bg-gray-700/20 transition-colors"
                      >
                        <td className="px-4 py-3 text-white font-medium">{w.name}</td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-xs border ${
                              w.category === 'OFFICIAL'
                                ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                            }`}
                          >
                            {w.category === 'OFFICIAL' ? 'رسمي' : 'يومي'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center text-gray-200">{w.days}</td>
                        <td className="px-4 py-3 text-center text-white font-semibold">
                          {toDecimal(w.total_surrah, 1).toFixed(1)}
                        </td>
                        <td className="px-4 py-3 text-center text-amber-300">
                          {toDecimal(w.total_overtime, 2) > 0
                            ? `+${toDecimal(w.total_overtime, 2).toFixed(2)}`
                            : '—'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={`text-xs font-medium ${
                              w.productivity_rank === 'عالية'
                                ? 'text-emerald-400'
                                : w.productivity_rank === 'متوسطة'
                                  ? 'text-amber-400'
                                  : w.productivity_rank === 'N/A'
                                    ? 'text-gray-500'
                                    : 'text-red-400'
                            }`}
                          >
                            {w.productivity_rank}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-left">
                          {w.category === 'OFFICIAL' ? (
                            <span className="text-gray-500 text-xs">—</span>
                          ) : (
                            <span className="text-emerald-300 font-semibold">
                              {formatMoney(w.estimated_cost)}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* ─── Legend ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500 px-2">
        <span>🟢 عالية: ≥20 صرّة/شهر</span>
        <span>🟡 متوسطة: 10-19 صرّة/شهر</span>
        <span>🔴 منخفضة: &lt;10 صرّة/شهر</span>
        <span>— رسمي: مؤشرات حضور فقط (§139)</span>
      </div>
    </div>
  )
}

function KPICard({ icon, label, value, color, testId }) {
  const colors = {
    emerald: 'from-emerald-500/10 border-emerald-500/20 text-emerald-400',
    blue: 'from-blue-500/10 border-blue-500/20 text-blue-400',
    violet: 'from-violet-500/10 border-violet-500/20 text-violet-400',
    amber: 'from-amber-500/10 border-amber-500/20 text-amber-400',
  }
  const c = colors[color] || colors.emerald
  return (
    <div
      data-testid={testId}
      className={`bg-gradient-to-br ${c.split(' ')[0]} to-transparent border ${c.split(' ')[1]} rounded-xl p-4`}
    >
      <div className="flex items-center gap-3">
        <div className={`bg-${color}-500/20 p-2.5 rounded-lg ${c.split(' ')[2]}`}>{icon}</div>
        <div>
          <p className="text-gray-400 text-xs">{label}</p>
          <p className="text-xl font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  )
}

function StatItem({ label, value, highlight }) {
  return (
    <div className="text-center">
      <p className="text-gray-500 text-xs mb-1">{label}</p>
      <p className={`text-lg font-bold ${highlight ? 'text-emerald-300' : 'text-white'}`}>
        {value}
      </p>
    </div>
  )
}
