import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { useFarmContext } from '../../api/farmContext'
import { logRuntimeError } from '../../utils/runtimeLogger'

/**
 * BurnRateWidget — لوحة معدل الحرق المصغّرة
 *
 * [AGRI-GUARDIAN Axis 8+15] Micro-Dashboard for Simple Mode users.
 * Shows proportional completion rates (burn rate %) WITHOUT leaking
 * explicit absolute financial unit values.
 *
 * Designed to match existing GlassCard design pattern from Dashboard.jsx.
 */

const STATUS_CONFIG = {
  GREEN: {
    label: 'طبيعي',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
    border: 'border-emerald-500/30',
    icon: '✅',
  },
  YELLOW: {
    label: 'تنبيه',
    color: 'text-amber-400',
    bg: 'bg-amber-500/20',
    border: 'border-amber-500/30',
    icon: '⚠️',
  },
  RED: {
    label: 'حرج',
    color: 'text-red-400',
    bg: 'bg-red-500/20',
    border: 'border-red-500/30',
    icon: '🔴',
  },
}

function ProgressBar({ label, pct, status }) {
  const pctNum = parseFloat(pct) || 0
  const clampedPct = Math.min(pctNum, 100)
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.GREEN

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-gray-400">{label}</span>
        <span className={`text-xs font-bold ${config.color}`}>{pctNum.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-gray-700/50 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-700 ease-out ${
            status === 'RED'
              ? 'bg-gradient-to-r from-red-500 to-red-600'
              : status === 'YELLOW'
                ? 'bg-gradient-to-r from-amber-400 to-amber-500'
                : 'bg-gradient-to-r from-emerald-400 to-teal-500'
          }`}
          style={{ width: `${clampedPct}%` }}
        />
      </div>
    </div>
  )
}

function CropPlanCard({ plan }) {
  const config = STATUS_CONFIG[plan.status] || STATUS_CONFIG.GREEN

  return (
    <div
      className={`backdrop-blur-lg bg-white/5 border ${config.border} rounded-xl p-4 
                  hover:bg-white/10 transition-all duration-300`}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white truncate">
            {plan.crop_plan_name || `خطة #${plan.crop_plan_id}`}
          </h4>
        </div>
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.color}`}
        >
          {config.icon} {config.label}
        </span>
      </div>

      {/* Main Budget Burn */}
      <ProgressBar label="معدل الحرق الإجمالي" pct={plan.budget_pct_used} status={plan.status} />

      {/* Sub-categories */}
      <div className="grid grid-cols-3 gap-2 mt-2">
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-1">عمالة</div>
          <div className="text-sm font-bold text-indigo-400">
            {parseFloat(plan.labor_burn_pct || 0).toFixed(0)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-1">مواد</div>
          <div className="text-sm font-bold text-purple-400">
            {parseFloat(plan.material_burn_pct || 0).toFixed(0)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-1">معدات</div>
          <div className="text-sm font-bold text-pink-400">
            {parseFloat(plan.machinery_burn_pct || 0).toFixed(0)}%
          </div>
        </div>
      </div>
    </div>
  )
}

export default function BurnRateWidget() {
  const { selectedFarmId } = useFarmContext()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!selectedFarmId) return

    let cancelled = false
    setLoading(true)
    setError(null)

    api
      .get(`/burn-rate-summary/?farm=${selectedFarmId}`)
      .then(({ data: result }) => {
        if (!cancelled) setData(result || [])
      })
      .catch((err) => {
        if (!cancelled) {
          logRuntimeError('BURN_RATE_FETCH_FAILED', err, { farm_id: selectedFarmId })
          setError('تعذر تحميل معدلات الحرق.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [selectedFarmId])

  if (loading) {
    return (
      <div className="backdrop-blur-lg bg-white/5 border border-white/10 rounded-2xl p-6">
        <div className="animate-pulse">
          <div className="h-5 bg-gray-700 rounded w-1/3 mb-4" />
          <div className="space-y-3">
            <div className="h-16 bg-gray-700/50 rounded-xl" />
            <div className="h-16 bg-gray-700/50 rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="backdrop-blur-lg bg-red-500/10 border border-red-500/20 rounded-2xl p-4">
        <p className="text-red-400 text-sm text-center">{error}</p>
      </div>
    )
  }

  if (!data.length) return null

  // Count statuses for summary
  const statusCounts = data.reduce(
    (acc, p) => {
      acc[p.status] = (acc[p.status] || 0) + 1
      return acc
    },
    { GREEN: 0, YELLOW: 0, RED: 0 },
  )

  return (
    <div className="backdrop-blur-lg bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/[0.07] transition-all duration-300">
      {/* Widget Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            📊 معدل الحرق — الخطط الزراعية
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">نسب الاستهلاك مقارنة بالموازنة المعتمدة</p>
        </div>

        {/* Status Summary Badges */}
        <div className="flex gap-2">
          {statusCounts.RED > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-500/20 text-red-400">
              🔴 {statusCounts.RED}
            </span>
          )}
          {statusCounts.YELLOW > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-400">
              ⚠️ {statusCounts.YELLOW}
            </span>
          )}
          {statusCounts.GREEN > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-emerald-500/20 text-emerald-400">
              ✅ {statusCounts.GREEN}
            </span>
          )}
        </div>
      </div>

      {/* Crop Plan Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {data.map((plan) => (
          <CropPlanCard key={plan.crop_plan_id} plan={plan} />
        ))}
      </div>
    </div>
  )
}
