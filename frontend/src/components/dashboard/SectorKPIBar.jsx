/**
 * [AGRI-GUARDIAN Phase 4] SectorKPIBar
 *
 * Executive-level KPI summary bar for the Sector Governance Dashboard.
 * Appears in STRICT mode only, for users with canObserveOps permission.
 * Fetches from /approval-requests/sector-dashboard/ (already backed by ApprovalGovernanceService).
 *
 * Usage: <SectorKPIBar />
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Clock, ShieldAlert, Users, ArrowLeft, TrendingUp } from 'lucide-react'
import { ApprovalRequests } from '../../api/client'
import { useOpsRuntime } from '../../contexts/OpsRuntimeContext'
import { useSettings } from '../../contexts/SettingsContext.jsx'

const fmtFarm = (name) => (name?.length > 18 ? `${name.slice(0, 16)}…` : name || '—')

function KPIItem({ icon: Icon, label, value, tone = 'text-slate-700 dark:text-slate-200', urgent }) {
  return (
    <div className={`flex items-center gap-2 px-3 ${urgent ? 'animate-pulse' : ''}`}>
      <Icon className={`h-4 w-4 shrink-0 ${urgent ? 'text-rose-500' : 'text-slate-400 dark:text-slate-500'}`} />
      <div>
        <div className={`text-xl font-bold leading-none ${urgent ? 'text-rose-600 dark:text-rose-400' : tone}`}>
          {value}
        </div>
        <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{label}</div>
      </div>
    </div>
  )
}

export default function SectorKPIBar() {
  const navigate = useNavigate()
  const { isStrictMode } = useSettings()
  const { canObserveOps } = useOpsRuntime()
  const [kpi, setKpi] = useState(null)
  const [topFarm, setTopFarm] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isStrictMode || !canObserveOps) {
      setLoading(false)
      return
    }
    ApprovalRequests.sectorDashboard()
      .then((res) => {
        const data = res.data || {}
        setKpi(data.kpis || {})
        const farms = data.top_farms || []
        setTopFarm(farms[0] || null)
      })
      .catch(() => {}) // Non-blocking — bar just stays hidden
      .finally(() => setLoading(false))
  }, [canObserveOps, isStrictMode])

  if (!isStrictMode || !canObserveOps || loading || !kpi) return null

  const hasCritical = (kpi.blocked_requests || 0) > 0 || (kpi.director_attention_count || 0) > 0

  return (
    <div
      className={`mb-6 flex flex-col gap-3 rounded-2xl border px-5 py-4 shadow-sm transition-all lg:flex-row lg:items-center lg:justify-between ${
        hasCritical
          ? 'border-rose-200 bg-rose-50/60 dark:border-rose-900/50 dark:bg-rose-950/30'
          : 'border-slate-200 bg-white/70 backdrop-blur dark:border-slate-700 dark:bg-slate-800/70'
      }`}
      dir="rtl"
      role="region"
      aria-label="مؤشرات الحوكمة القطاعية"
    >
      {/* Label */}
      <div className="flex items-center gap-2 shrink-0">
        <ShieldAlert className={`h-5 w-5 ${hasCritical ? 'text-rose-500' : 'text-primary'}`} />
        <span className="text-sm font-bold text-slate-700 dark:text-slate-200">الحوكمة القطاعية</span>
      </div>

      {/* KPI Pills */}
      <div className="flex flex-wrap items-center gap-1 divide-x divide-slate-200 dark:divide-slate-700 rtl:divide-x-reverse">
        <KPIItem icon={Clock} label="معلّق" value={kpi.pending_requests || 0} />
        <KPIItem icon={AlertTriangle} label="متأخر" value={kpi.overdue_requests || 0} urgent={(kpi.overdue_requests || 0) > 0} />
        <KPIItem icon={ShieldAlert} label="معطّل" value={kpi.blocked_requests || 0} urgent={(kpi.blocked_requests || 0) > 0} />
        <KPIItem icon={Users} label="تدخل مدير" value={kpi.director_attention_count || 0} urgent={(kpi.director_attention_count || 0) > 0} />
        {kpi.strict_finance_pending > 0 && (
          <KPIItem icon={TrendingUp} label="مالية صارمة" value={kpi.strict_finance_pending} />
        )}
        {topFarm && (
          <div className="flex items-center gap-2 px-3">
            <div className="h-4 w-px bg-slate-200 dark:bg-slate-700" />
            <div>
              <div className="text-xs font-semibold text-slate-800 dark:text-white">{fmtFarm(topFarm.farm_name)}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">{topFarm.pending_count} معلّق</div>
            </div>
          </div>
        )}
      </div>

      {/* CTA */}
      <button
        type="button"
        onClick={() => navigate('/approvals?tab=overview')}
        className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white shadow hover:bg-primary/90 transition-colors"
      >
        لوحة القطاع
        <ArrowLeft className="h-3 w-3" />
      </button>
    </div>
  )
}
