import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { format, subDays, startOfMonth } from 'date-fns'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
} from 'chart.js'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import { api, fetchDashboardStats } from '../api/client'
import { toDecimal, formatCurrency, formatMoney } from '../utils/decimal'
import { useAuth } from '../auth/AuthContext'
import { canRegisterFinancialRoutes } from '../auth/modeAccess'
import { useOpsRuntime } from '../contexts/OpsRuntimeContext.jsx'
import { useSettings } from '../contexts/SettingsContext.jsx'
import BurnRateWidget from '../components/dashboard/BurnRateWidget'
import SectorKPIBar from '../components/dashboard/SectorKPIBar'
import { formatOpsKind, formatOpsReason, formatOpsSeverity } from '../utils/opsArabic'
import { readScopedValue, writeScopedValue } from '../api/offlineQueueStore.js'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
)

// Premium design system

const PREMIUM_COLORS = {
  primary: {
    gradient: 'from-indigo-600 via-purple-600 to-pink-500',
    solid: '#6366f1',
  },
  success: {
    gradient: 'from-emerald-500 to-teal-600',
    solid: '#10b981',
  },
  warning: {
    gradient: 'from-amber-400 to-orange-500',
    solid: '#f59e0b',
  },
  danger: {
    gradient: 'from-rose-500 to-red-600',
    solid: '#ef4444',
  },
  info: {
    gradient: 'from-sky-400 to-blue-600',
    solid: '#0ea5e9',
  },
}

const CHART_COLORS = {
  primary: 'rgba(99, 102, 241, 0.8)',
  secondary: 'rgba(16, 185, 129, 0.8)',
  accent: 'rgba(245, 158, 11, 0.8)',
  background: 'rgba(99, 102, 241, 0.1)',
}

// Premium components

function GlassCard({ children, className = '', hover = true }) {
  return (
    <div
      className={`
      relative overflow-hidden rounded-2xl
      bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl
      border border-white/20 dark:border-slate-700/50
      shadow-xl shadow-gray-200/50 dark:shadow-black/20
      ${hover ? 'transition-all duration-300 hover:shadow-2xl hover:-translate-y-1' : ''}
      ${className}
    `}
    >
      {children}
    </div>
  )
}

function PremiumKPICard({ title, value, subValue, icon, gradient, trend }) {
  const isPositive = trend >= 0

  return (
    <GlassCard>
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-500 dark:text-slate-400 mb-2">{title}</p>
            <h3
              className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent"
              dir="ltr"
            >
              {value}
            </h3>
            {subValue && (
              <p className="text-sm text-gray-400 mt-2 flex items-center gap-1">
                {trend !== undefined && (
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      isPositive ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                    }`}
                  >
                    {isPositive ? '↑' : '↓'} {Math.abs(trend)}%
                  </span>
                )}
                {subValue}
              </p>
            )}
          </div>
          <div className={`p-4 rounded-2xl bg-gradient-to-br ${gradient} shadow-lg`}>
            <span className="text-3xl filter drop-shadow-md">{icon}</span>
          </div>
        </div>
      </div>
      {/* Decorative gradient bar */}
      <div className={`h-1 bg-gradient-to-r ${gradient}`} />
    </GlassCard>
  )
}

function ChartContainer({ title, subtitle, children, className = '' }) {
  return (
    <GlassCard className={className}>
      <div className="p-6">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-gray-800 dark:text-slate-100">{title}</h2>
          {subtitle && <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className="relative">{children}</div>
      </div>
    </GlassCard>
  )
}

function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-6">
      <div className="animate-pulse space-y-6">
        <div className="h-12 bg-gray-200 rounded-xl w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded-2xl" />
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 bg-gray-200 rounded-2xl" />
          ))}
        </div>
      </div>
    </div>
  )
}

function ErrorState({ error, onRetry }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-rose-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex items-center justify-center p-6">
      <GlassCard className="max-w-md w-full text-center">
        <div className="p-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-rose-500 to-red-600 flex items-center justify-center">
            <span className="text-3xl">!</span>
          </div>
          <h2 className="text-xl font-bold text-gray-800 dark:text-slate-100 mb-2">
            فشل تحميل لوحة المعلومات
          </h2>
          <p className="text-gray-500 dark:text-slate-400 text-sm mb-6 bg-gray-50 dark:bg-slate-800/70 p-3 rounded-lg">
            {error}
          </p>
          <button
            onClick={onRetry}
            className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-medium
                       shadow-lg shadow-indigo-500/30 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
          >
            إعادة المحاولة
          </button>
        </div>
      </GlassCard>
    </div>
  )
}


// Main dashboard

export default function Dashboard() {
  const navigate = useNavigate()
  const { isAdmin, is_superuser, hasFarmRole } = useAuth()
  const { isStrictMode, costVisibility } = useSettings()
  const { topAlerts, canObserveOps } = useOpsRuntime()
  const financialRoutesEnabled = canRegisterFinancialRoutes({
    strictErpMode: isStrictMode,
    isAdmin,
    isSuperuser: is_superuser,
    hasFarmRole,
  })

  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalFarms: 0,
    activePlans: 0,
    todayActivities: 0,
    weekActivities: 0,
    monthCost: 0,
    monthBudget: 0,
    financials: { revenue: 0, cost: 0, netProfit: 0, currency: 'YER' },
    yields: { expected: 0, actual: 0 },
  })
  const [planStatus, setPlanStatus] = useState([])
  const [topMaterials, setTopMaterials] = useState([])
  const [costTrend, setCostTrend] = useState([])
  const [error, setError] = useState(null)
  const [reportLoading, setReportLoading] = useState(true)
  const [opsHealth, setOpsHealth] = useState({ release: {}, outbox: {}, attachment: {} })

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true)
      setError(null)
      try {
        const [dashboardStats, farmsRes, plansRes, healthRes] = await Promise.all([
          fetchDashboardStats(),
          api.get('/farms/'),
          api.get('/crop-plans/'),
          api.get('/dashboard/aggregated-health/').catch(() => ({ data: {} })),
        ])
        setOpsHealth({
          release: healthRes.data?.release || {},
          outbox: healthRes.data?.outbox || {},
          attachment: healthRes.data?.attachment || {},
        })

        const allPlans = Array.isArray(plansRes.data) ? plansRes.data : plansRes.data?.results || []
        const activePlans = allPlans.filter((p) => !p.deleted_at)

        const statusCounts = { active: 0, completed: 0, planned: 0 }
        activePlans.forEach((plan) => {
          if (plan.status === 'active') statusCounts.active++
          else if (plan.status === 'completed') statusCounts.completed++
          else statusCounts.planned++
        })

        setPlanStatus([
          { label: 'نشطة', value: statusCounts.active, color: CHART_COLORS.secondary },
          { label: 'مكتملة', value: statusCounts.completed, color: CHART_COLORS.primary },
          { label: 'مخططة', value: statusCounts.planned, color: CHART_COLORS.accent },
        ])

        const today = format(new Date(), 'yyyy-MM-dd')
        const weekStart = format(subDays(new Date(), 7), 'yyyy-MM-dd')
        const monthStart = format(startOfMonth(new Date()), 'yyyy-MM-dd')

        // Async Advanced Report Fetch (Non-blocking)
        const applyReportData = (data) => {
          const todayActs = data.activities?.filter((a) => a.log_date === today) || []
          const weekActs = data.activities?.filter((a) => a.log_date >= weekStart) || []

          const materials = data.materials || []
          const sortedMaterials = materials
            .sort((a, b) => toDecimal(b.total_qty) - toDecimal(a.total_qty))
            .slice(0, 5)
          setTopMaterials(sortedMaterials)

          const last7Days = Array.from({ length: 7 }, (_, i) => {
            const date = format(subDays(new Date(), 6 - i), 'yyyy-MM-dd')
            const dayCost =
              data.activities
                ?.filter((a) => a.log_date === date)
                .reduce((sum, a) => sum + toDecimal(a.cost_total), 0) || 0
            return { date, cost: dayCost }
          })
          setCostTrend(last7Days)

          setStats((prev) => ({
            ...prev,
            todayActivities: todayActs.length,
            weekActivities: weekActs.length,
            monthCost: toDecimal(data.summary?.total_cost),
          }))
        }

        const fetchAdvancedReport = async () => {
          setReportLoading(true)
          try {
            if (!navigator.onLine) {
              const cachedReport = await readScopedValue('dashboard-adv-report-cache')
              if (cachedReport) applyReportData(cachedReport)
              return
            }

            const allFarmsList = Array.isArray(farmsRes.data)
              ? farmsRes.data
              : farmsRes.data?.results || []
            const firstFarmId = allFarmsList[0]?.id
            if (!firstFarmId) {
              console.warn('No farms available for advanced report')
              setReportLoading(false)
              return
            }
            const reportJobRes = await api.post('/advanced-report/requests/', {
              farm_id: firstFarmId,
              start: monthStart,
              end: today,
              include_details: 'false',
            })
            const jobId = reportJobRes.data?.job_id || reportJobRes.data?.request_id

            if (jobId) {
              let reportRes = null
              let attempts = 0
              while (attempts < 10) {
                const statusRes = await api.get(`/advanced-report/requests/${jobId}/`)
                if (statusRes.data?.status === 'COMPLETED' && statusRes.data?.result_url) {
                  reportRes = await api.get(statusRes.data.result_url)
                  break
                } else if (statusRes.data?.status === 'FAILED') {
                  console.error('Async report failed')
                  break
                }
                await new Promise((r) => setTimeout(r, 1500))
                attempts++
              }

              if (reportRes?.data) {
                await writeScopedValue('dashboard-adv-report-cache', reportRes.data)
                applyReportData(reportRes.data)
              }
            }
          } catch (err) {
            console.error('Failed to fetch advanced report async', err)
            if (!navigator.onLine) {
              const cachedReport = await readScopedValue('dashboard-adv-report-cache')
              if (cachedReport) applyReportData(cachedReport)
            }
          } finally {
            setReportLoading(false)
          }
        }

        // Execute background fetch natively
        fetchAdvancedReport()

        setStats({
          totalFarms: farmsRes.data?.length || 0,
          activePlans: dashboardStats.active_plans,
          todayActivities: 0,
          weekActivities: 0,
          monthCost: 0,
          monthBudget: activePlans.reduce((sum, p) => sum + toDecimal(p.budget_total), 0),
          financials: {
            revenue: dashboardStats.financials.revenue,
            cost: dashboardStats.financials.cost,
            netProfit: dashboardStats.financials.net_profit,
            currency: dashboardStats.financials.currency,
          },
          yields: {
            expected: dashboardStats.yields.expected,
            actual: dashboardStats.yields.actual,
          },
        })
      } catch (err) {
        console.error('خطأ في تحميل بيانات لوحة المعلومات:', err)
        let msg = err.response?.data?.error || err.response?.data?.detail || 'حدث خطأ غير متوقع'
        if (typeof msg === 'object') {
          msg = msg.message || JSON.stringify(msg)
        }
        setError(msg)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState error={error} onRetry={() => window.location.reload()} />

  const costVariance =
    stats.monthBudget && stats.monthBudget > 0
      ? ((stats.monthCost - stats.monthBudget) / stats.monthBudget) * 100
      : 0

  const yieldProgress =
    stats.yields?.expected && stats.yields.expected > 0
      ? (stats.yields.actual / stats.yields.expected) * 100
      : 0

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-6">
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row md:justify-between md:items-end gap-4">
        <div>
          <h1
            data-testid="dashboard-title"
            className="text-4xl font-extrabold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 bg-clip-text text-transparent"
          >
            لوحة المعلومات التنفيذية
          </h1>
          <p className="text-gray-500 dark:text-slate-400 mt-2">
            نظرة شاملة على أداء العمليات الزراعية
          </p>
          {/* [AGRI-GUARDIAN FIX] Visual Mode Indicator Badge */}
          <span
            className={`inline-flex items-center gap-1.5 mt-2 px-3 py-1 rounded-full text-xs font-bold ${
              isStrictMode
                ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${isStrictMode ? 'bg-blue-500' : 'bg-emerald-500'}`}
            />
            {isStrictMode ? 'وضع صارم' : 'وضع مبسط'}
          </span>
        </div>
        {!isStrictMode && (
          <button
            onClick={() => navigate('/daily-log')}
            className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300 font-bold flex items-center justify-center gap-2"
          >
            <span className="text-xl">+</span> إضافة سجل يومي
          </button>
        )}
      </div>
      <SectorKPIBar />
      {isStrictMode && canObserveOps && topAlerts.length ? (
        <GlassCard className="mb-8 p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-white">التنبيهات التشغيلية</div>
              <div className="mt-1 text-xs text-gray-500 dark:text-slate-400">أهم الإشارات التشغيلية التي تستدعي مراجعة فورية من أسطح الحوكمة والتشغيل.</div>
            </div>
            <div className="rounded-2xl bg-rose-100 px-3 py-2 text-xs font-bold text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
              {topAlerts.length} تنبيه
            </div>
          </div>
          <div className="grid gap-3 lg:grid-cols-3">
            {topAlerts.map((alert) => {
              const reasonLabel = formatOpsReason(alert.canonical_reason || alert.title || alert.kind)
              const kindLabel = formatOpsKind(alert.kind)
              return (
                <button key={alert.fingerprint} type="button" onClick={() => navigate(alert.deep_link || '/approvals?tab=runtime')} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-right transition hover:border-primary dark:border-slate-700 dark:bg-slate-900/30">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${alert.severity === 'critical' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}`}>{formatOpsSeverity(alert.severity)}</span>
                    <span className="rounded-full bg-sky-100 px-2 py-1 text-xs font-semibold text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{kindLabel}</span>
                  </div>
                  <div className="mt-3 text-sm font-semibold text-slate-900 dark:text-white">{reasonLabel}</div>
                  <div className="mt-1 text-xs text-gray-500 dark:text-slate-400">{kindLabel}</div>
                </button>
              )
            })}
          </div>
        </GlassCard>
      ) : null}
      {isStrictMode && (
      <div className="mb-8 grid gap-4 md:grid-cols-3">
        <GlassCard className="p-5">
          <button type="button" onClick={() => navigate('/settings')} className="w-full text-right">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm text-gray-500 dark:text-slate-400">صحة الإصدار</div>
              <div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{formatOpsSeverity(opsHealth.release?.severity || 'unknown')}</div>
              <div className="mt-1 text-xs text-gray-500 dark:text-slate-400">تحذيرات التقادم: {opsHealth.release?.stale_warning_count || 0}</div>
            </div>
            <div className={`rounded-2xl px-3 py-2 text-xs font-bold ${opsHealth.release?.severity === 'critical' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' : opsHealth.release?.severity === 'attention' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'}`}>
              دليل رسمي
            </div>
          </div>
          </button>
        </GlassCard>
        <GlassCard className="p-5">
          <button type="button" onClick={() => navigate('/approvals')} className="w-full text-right">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm text-gray-500 dark:text-slate-400">صحة صندوق الإرسال</div>
              <div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{formatOpsSeverity(opsHealth.outbox?.severity || 'unknown')}</div>
              <div className="mt-1 text-xs text-gray-500 dark:text-slate-400">الرسائل الميتة: {opsHealth.outbox?.dead_letter_count || 0} · جاهزة لإعادة المحاولة: {opsHealth.outbox?.retry_ready_count || 0}</div>
            </div>
            <div className="rounded-2xl bg-sky-100 px-3 py-2 text-xs font-bold text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">
              صندوق الإرسال
            </div>
          </div>
          </button>
        </GlassCard>
        <GlassCard className="p-5">
          <button type="button" onClick={() => navigate('/approvals')} className="w-full text-right">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm text-gray-500 dark:text-slate-400">تشغيل المرفقات</div>
              <div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{formatOpsSeverity(opsHealth.attachment?.severity || 'unknown')}</div>
              <div className="mt-1 text-xs text-gray-500 dark:text-slate-400">الفحص المعلق: {opsHealth.attachment?.pending_scan || 0} · المعزول: {opsHealth.attachment?.quarantined || 0}</div>
            </div>
            <div className="rounded-2xl bg-amber-100 px-3 py-2 text-xs font-bold text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
              المرفقات
            </div>
          </div>
          </button>
        </GlassCard>
      </div>
      )}
      {/* Top KPIs */}
      <div className="mb-8 grid gap-5 md:grid-cols-2 lg:grid-cols-5">
        <PremiumKPICard
          title="المزارع والخطط"
          value={`${stats.totalFarms} / ${stats.activePlans}`}
          subValue="مزارع / خطط نشطة"
          icon="🚜"
          gradient={PREMIUM_COLORS.info.gradient}
        />
        {financialRoutesEnabled ? (
          <>
            <PremiumKPICard
              title="الإيرادات"
              value={`${formatMoney(stats.financials.revenue)}`}
              subValue={stats.financials.currency}
              icon="💰"
              gradient={PREMIUM_COLORS.success.gradient}
              trend={12}
            />
            <PremiumKPICard
              title="صافي الربح"
              value={`${formatMoney(stats.financials.netProfit)}`}
              subValue={stats.financials.currency}
              icon={stats.financials.netProfit >= 0 ? '📈' : '📉'}
              gradient={
                stats.financials.netProfit >= 0
                  ? PREMIUM_COLORS.success.gradient
                  : PREMIUM_COLORS.danger.gradient
              }
              trend={stats.financials.netProfit >= 0 ? 8 : -5}
            />
          </>
        ) : (
          <>
            <PremiumKPICard
              title="تنبيهات الجدول"
              value="متابعة"
              subValue="لا يوجد تأخير حرج"
              icon="⏱️"
              gradient={PREMIUM_COLORS.success.gradient}
            />
            <PremiumKPICard
              title="كفاءة الموارد"
              value={`${stats.monthBudget > 0 ? (100 - (stats.monthCost / stats.monthBudget) * 100).toFixed(0) : 100}%`}
              subValue="معدل استهلاك الخطة"
              icon="🔥"
              gradient={PREMIUM_COLORS.warning.gradient}
            />
          </>
        )}
        <PremiumKPICard
          title="تقدم الحصاد"
          value={`${yieldProgress.toFixed(0)}%`}
          subValue={`${formatCurrency(stats.yields.actual, 1)} / ${formatCurrency(stats.yields.expected, 1)}`}
          icon="🌾"
          gradient={PREMIUM_COLORS.warning.gradient}
        />

        {/* [Agri-Guardian] New Tree Intel Card */}
        <PremiumKPICard
          title="الثروة الشجرية"
          value={`${formatCurrency(stats.trees?.total_count || 0, 0)}`}
          subValue={`في ${stats.trees?.active_locations || 0} موقع نشط`}
          icon="🌳"
          gradient={PREMIUM_COLORS.success.gradient}
          trend={1}
        />
      </div>

      {/* Financial Health Row - Only for Fin Leaders */}
      <div className="mb-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {/* Monthly Cost Tracking (Micro-Dashboard Style if not financialRoutesEnabled) */}
        {financialRoutesEnabled ? (
          <ChartContainer title="التكاليف الشهرية" subtitle="مقارنة الموازنة بالمنصرف الفعلي">
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <div>
                  <div className="text-sm text-gray-500 dark:text-slate-400">المنصرف</div>
                  <div className="text-3xl font-bold text-gray-800 dark:text-slate-100">
                    {formatMoney(stats.monthCost)}
                  </div>
                </div>
                <div className="text-end">
                  <div className="text-sm text-gray-500 dark:text-slate-400">الموازنة</div>
                  <div className="text-xl text-gray-600 dark:text-slate-300">
                    {formatMoney(stats.monthBudget)}
                  </div>
                </div>
              </div>
              <div className="relative h-3 rounded-full bg-gray-100 dark:bg-slate-700 overflow-hidden">
                <div
                  style={{
                    width: `${stats.monthBudget > 0 ? Math.min((stats.monthCost / stats.monthBudget) * 100, 100) : 0}%`,
                  }}
                  className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${
                    costVariance > 0
                      ? 'bg-gradient-to-r from-rose-400 to-red-500'
                      : 'bg-gradient-to-r from-emerald-400 to-teal-500'
                  }`}
                />
              </div>
              {reportLoading ? (
                <div className="animate-pulse flex space-x-4 h-6 bg-gray-200 dark:bg-slate-700 rounded-full w-3/4"></div>
              ) : (
                <div
                  className={`text-sm font-medium ${costVariance > 0 ? 'text-rose-600' : 'text-emerald-600'}`}
                >
                  {costVariance > 0
                    ? `تجاوز ${costVariance.toFixed(1)}%`
                    : `وفر ${Math.abs(costVariance).toFixed(1)}%`}
                </div>
              )}
            </div>
          </ChartContainer>
        ) : (
          <BurnRateWidget />
        )}

        {/* Plan Status */}
        <ChartContainer title="توزيع الخطط" subtitle="حسب الحالة">
          <div className="h-48">
            <Doughnut
              data={{
                labels: planStatus.map((s) => s.label),
                datasets: [
                  {
                    data: planStatus.map((s) => s.value),
                    backgroundColor: planStatus.map((s) => s.color),
                    borderWidth: 0,
                    borderRadius: 4,
                  },
                ],
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                  legend: { position: 'right', labels: { font: { family: 'inherit' } } },
                },
              }}
            />
          </div>
        </ChartContainer>

        {/* Activity Volume */}
        <ChartContainer title="حجم العمليات" subtitle="اليوم والأسبوع">
          {reportLoading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-20 bg-gray-200 dark:bg-slate-700 rounded-2xl w-full" />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-50 to-purple-50 text-center">
                <div className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  {stats.todayActivities}
                </div>
                <div className="text-sm text-gray-500 dark:text-slate-400 mt-1">أنشطة اليوم</div>
              </div>
              <div className="p-5 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 text-center">
                <div className="text-4xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
                  {stats.weekActivities}
                </div>
                <div className="text-sm text-gray-500 dark:text-slate-400 mt-1">أنشطة الأسبوع</div>
              </div>
            </div>
          )}
        </ChartContainer>
      </div>

      {/* Charts Row */}
      <div className="grid gap-5 md:grid-cols-2">
        {/* Cost Trend */}
        {(isStrictMode || costVisibility === 'summarized_amounts') ? (
          <ChartContainer title="اتجاه التكاليف اليومية" subtitle="آخر 7 أيام">
            <div className="h-72">
              {reportLoading ? (
                <div className="animate-pulse h-full bg-gray-100 dark:bg-slate-700 rounded-lg"></div>
              ) : (
                <Line
                  data={{
                    labels: costTrend.map((d) => format(new Date(d.date), 'MM/dd')),
                    datasets: [
                      {
                        label: 'التكلفة',
                        data: costTrend.map((d) => d.cost),
                        borderColor: CHART_COLORS.primary,
                        backgroundColor: CHART_COLORS.background,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: CHART_COLORS.primary,
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                      },
                    ],
                  }}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                      y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                      x: { grid: { display: false } },
                    },
                    plugins: { legend: { display: false } },
                  }}
                />
              )}
            </div>
          </ChartContainer>
        ) : (
          <GlassCard className="flex items-center justify-center h-full p-8 text-center text-gray-500 dark:text-slate-400">
            <div>
              <div className="text-4xl mb-3">🔒</div>
              <p>منحنى التكاليف محجوب (وضع التشغيل المبسط)</p>
            </div>
          </GlassCard>
        )}

        {/* Top Materials */}
        <ChartContainer title="أكثر المواد استهلاكًا" subtitle="أعلى 5 مواد">
          <div className="h-72">
            {reportLoading ? (
              <div className="animate-pulse h-full bg-gray-100 dark:bg-slate-700 rounded-lg"></div>
            ) : (
              <Bar
                data={{
                  labels: topMaterials.map((m) => m.item_name?.slice(0, 15) || '-'),
                  datasets: [
                    {
                      label: 'الكمية',
                      data: topMaterials.map((m) => m.total_quantity || 0),
                      backgroundColor: 'rgba(99, 102, 241, 0.8)',
                      borderRadius: 4,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  indexAxis: 'y',
                  scales: {
                    x: { grid: { color: 'rgba(0,0,0,0.05)' } },
                    y: { grid: { display: false } },
                  },
                  plugins: { legend: { display: false } },
                }}
              />
            )}
          </div>
        </ChartContainer>
      </div>
    </div>
  )
}

