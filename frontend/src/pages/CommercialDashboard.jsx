import { useEffect, useMemo, useState } from 'react'
import { toast } from 'react-hot-toast'
import useFinancialFilters from '../hooks/useFinancialFilters'
import FinancialFilterBar from '../components/filters/FinancialFilterBar'
import { PremiumCard, GlassContainer } from '../components/commercial/PremiumUI.jsx'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { api, AsyncReports } from '../api/client'
import { buildCommercialReportParams } from './Finance/reportParams'

const FILTER_DIMENSIONS = ['farm', 'location', 'crop_plan', 'crop']

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
)

const TEXT = {
  title: 'الرؤية التجارية',
  subtitle: 'تحليلات الربحية الزراعية في الوقت الحقيقي',
  kpi: {
    netMargin: 'صافي الهامش',
    netMarginSub: 'ملخص تنفيذي مباشر من بيانات اللوحة',
    revenue: 'إجمالي الإيرادات',
    revenueSub: 'من المبيعات المعتمدة',
    costs: 'إجمالي التكاليف',
    costsSub: 'تكاليف التشغيل والموارد',
    yieldPerf: 'أداء الإنتاجية',
    yieldPerfSub: 'مقارنة بالمستهدف الموسمي',
  },
  charts: {
    profitability: 'تحليلات الربحية',
    pulse: 'نبض التشغيل',
    riskZone: 'منطقة المخاطر المالية',
    grading: 'التوزيع حسب المحصول',
  },
  buttons: {
    export: 'تصدير PDF',
    allocate: 'تخصيص النفقات',
    sixMonths: '6 أشهر',
    oneYear: 'سنة',
  },
}

const formatCurrency = (value, currency = 'YER') => {
  const num = Number(value) || 0
  return `${currency} ${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const formatPercent = (value) => {
  const num = Number(value) || 0
  return `${num.toFixed(1)}%`
}

const calcYieldPercent = (actual, expected) => {
  if (!expected || Number(expected) === 0) return 0
  return Number(((Number(actual || 0) / Number(expected)) * 100).toFixed(1))
}

const zoneMeta = {
  safe: { label: 'آمن', className: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20' },
  warning: { label: 'تحذير', className: 'bg-amber-500/15 text-amber-400 border-amber-500/20' },
  danger: { label: 'خطر', className: 'bg-rose-500/15 text-rose-400 border-rose-500/20' },
}

function FinancialRiskZone({ data }) {
  const risk = data?.risk_zone || { margin_percent: 0, zone: 'danger' }
  const meta = zoneMeta[risk.zone] || zoneMeta.danger

  return (
    <GlassContainer title={TEXT.charts.riskZone}>
      <div className="space-y-4">
        <div className={`rounded-2xl border p-4 ${meta.className}`}>
          <div className="text-xs font-bold uppercase opacity-70">هامش الربح الحالي</div>
          <div className="mt-2 flex items-center justify-between">
            <div className="text-3xl font-black">{formatPercent(risk.margin_percent)}</div>
            <div className="rounded-xl border px-3 py-1 text-sm font-bold">{meta.label}</div>
          </div>
        </div>
        <div className="space-y-3 text-sm text-white/70 dark:text-white/70">
          <div className="flex items-center justify-between rounded-xl bg-white/5 p-3">
            <span>الإيرادات</span>
            <span dir="ltr">
              {formatCurrency(
                data?.financials?.revenue,
                data?.financials?.currency || data?.currency || 'YER',
              )}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-xl bg-white/5 p-3">
            <span>التكاليف</span>
            <span dir="ltr">
              {formatCurrency(
                data?.financials?.cost,
                data?.financials?.currency || data?.currency || 'YER',
              )}
            </span>
          </div>
          <div className="flex items-center justify-between rounded-xl bg-white/5 p-3">
            <span>صافي الربح</span>
            <span dir="ltr">
              {formatCurrency(
                data?.financials?.net_profit,
                data?.financials?.currency || data?.currency || 'YER',
              )}
            </span>
          </div>
        </div>
      </div>
    </GlassContainer>
  )
}

const LoadingSkeleton = () => (
  <div className="space-y-8 bg-gray-50 p-8 text-gray-800 dark:bg-slate-900 dark:text-white">
    <div className="animate-pulse">
      <div className="mb-4 h-10 w-64 rounded-lg bg-gray-200 dark:bg-white/10" />
      <div className="grid grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-40 rounded-2xl bg-gray-200 dark:bg-white/5" />
        ))}
      </div>
    </div>
  </div>
)

async function pollCommercialReport(jobId) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const { data } = await AsyncReports.status(jobId)
    if (data.status === 'completed') return data
    if (data.status === 'failed') throw new Error(data.error_message || 'فشل توليد ملف PDF التجاري')
    await new Promise((resolve) => setTimeout(resolve, 1500))
  }
  throw new Error('انتهت مهلة توليد ملف PDF التجاري')
}

const CommercialDashboard = () => {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [hasLiveData, setHasLiveData] = useState(false)
  const [dashboardError, setDashboardError] = useState('')

  const {
    filters,
    options,
    loading: filterLoading,
    setFilter,
    resetFilters,
    filterParams,
  } = useFinancialFilters({ dimensions: FILTER_DIMENSIONS })

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setDashboardError('')
        const response = await api.get('/dashboard-stats/', { params: filterParams })
        setData(response.data)
        setHasLiveData(true)
      } catch (error) {
        console.error('Dashboard fetch error:', error)
        setHasLiveData(false)
        setDashboardError(
          'تعذر تحميل البيانات الحية. القيم المعروضة احتياطية للقراءة فقط ولا يمكن تصديرها.',
        )
        setData({
          active_plans: 12,
          financials: { revenue: 2400000, cost: 1800000, net_profit: 600000, currency: 'YER' },
          yields: { expected: 1000, actual: 824 },
          risk_zone: { margin_percent: 25, zone: 'safe' },
          pulse: {
            active_plans: 12,
            approved_invoices: 0,
            expected_yield: 1000,
            actual_yield: 824,
          },
          trend: [],
          allocations: [],
          grading: [],
          currency: 'YER',
        })
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [filterParams])

  const handleExportReport = async () => {
    if (!hasLiveData) {
      toast.error('التصدير معطل لأن الصفحة تعرض بيانات احتياطية وليست بيانات حية.')
      return
    }

    setExporting(true)
    const toastId = toast.loading('جارٍ إنشاء تقرير PDF التجاري...')
    try {
      const payload = buildCommercialReportParams(filterParams)
      const { data: job } = await AsyncReports.request(payload)
      const readyJob = await pollCommercialReport(job.id)
      await AsyncReports.download(
        readyJob.result_url,
        `commercial-report-${payload.farm_id || 'all'}-${Date.now()}.pdf`,
      )
      toast.success('تم تنزيل تقرير PDF التجاري', { id: toastId })
    } catch (error) {
      console.error('Commercial report export failed:', error)
      toast.error(error?.message || 'تعذر تصدير التقرير التجاري', { id: toastId })
    } finally {
      setExporting(false)
    }
  }

  const chartData = useMemo(() => {
    const trend = Array.isArray(data?.trend) ? data.trend : []
    if (trend.length > 0) {
      return {
        labels: trend.map((row) => row.label),
        datasets: [
          {
            label: 'الإيرادات',
            data: trend.map((row) => Number(row.revenue || 0)),
            fill: true,
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderColor: '#10b981',
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: '#10b981',
          },
          {
            label: 'التكاليف',
            data: trend.map((row) => Number(row.cost || 0)),
            borderColor: '#f59e0b',
            borderDash: [5, 5],
            fill: false,
            tension: 0.4,
          },
        ],
      }
    }

    return {
      labels: ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو'],
      datasets: [
        {
          label: 'الإيرادات',
          data: [
            180000,
            220000,
            280000,
            350000,
            420000,
            Number(data?.financials?.revenue || 0) / 6 || 400000,
          ],
          fill: true,
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderColor: '#10b981',
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#10b981',
        },
        {
          label: 'التكاليف',
          data: [
            150000,
            170000,
            200000,
            250000,
            300000,
            Number(data?.financials?.cost || 0) / 6 || 300000,
          ],
          borderColor: '#f59e0b',
          borderDash: [5, 5],
          fill: false,
          tension: 0.4,
        },
      ],
    }
  }, [data])

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.9)',
        rtl: true,
        titleFont: { family: 'Tajawal' },
        bodyFont: { family: 'Tajawal' },
        cornerRadius: 12,
        padding: 12,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: 'rgba(255,255,255,0.4)', font: { family: 'Tajawal' } },
      },
      y: {
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: { color: 'rgba(255,255,255,0.4)' },
      },
    },
  }

  if (loading) return <LoadingSkeleton />

  const currency = data?.financials?.currency || data?.currency || 'YER'
  const yieldPercent = calcYieldPercent(data?.yields?.actual, data?.yields?.expected)
  const profitTrend = Number(data?.financials?.net_profit || 0) >= 0 ? 12.5 : -5.2
  const yieldTrend = yieldPercent > 80 ? 4.2 : -2.1
  const gradingRows =
    Array.isArray(data?.grading) && data.grading.length > 0
      ? data.grading
      : [{ crop_name: 'بدون بيانات', plans: 0, expected_yield: 0 }]

  return (
    <div
      dir="rtl"
      className="min-h-screen space-y-8 bg-gray-50 p-8 text-gray-800 dark:bg-slate-900 dark:text-white"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="bg-gradient-to-r from-emerald-600 to-amber-500 bg-clip-text text-4xl font-black tracking-tight text-transparent dark:from-emerald-400 dark:to-amber-200">
            {TEXT.title}
          </h1>
          <p className="mt-1 font-medium text-gray-500 dark:text-zinc-500">{TEXT.subtitle}</p>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleExportReport}
            disabled={exporting || !hasLiveData}
            className="rounded-xl border border-gray-200 bg-gray-100 px-5 py-2.5 text-sm font-semibold transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/5 dark:bg-zinc-800 dark:hover:bg-zinc-700"
          >
            {exporting ? 'جارٍ إنشاء الملف...' : TEXT.buttons.export}
          </button>
          <button className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold shadow-lg shadow-emerald-500/20 transition-colors hover:bg-emerald-500">
            {TEXT.buttons.allocate}
          </button>
        </div>
      </div>

      <FinancialFilterBar
        filters={filters}
        options={options}
        loading={filterLoading}
        setFilter={setFilter}
        onReset={resetFilters}
        dimensions={FILTER_DIMENSIONS}
      />

      {dashboardError && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm font-semibold text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
          {dashboardError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <PremiumCard
          title={TEXT.kpi.netMargin}
          value={formatCurrency(data?.financials?.net_profit, currency)}
          icon="💰"
          trend={profitTrend}
          subValue={TEXT.kpi.netMarginSub}
        />
        <PremiumCard
          title={TEXT.kpi.revenue}
          value={formatCurrency(data?.financials?.revenue, currency)}
          icon="📈"
          trend={8.3}
          color="gold"
          subValue={TEXT.kpi.revenueSub}
        />
        <PremiumCard
          title={TEXT.kpi.costs}
          value={formatCurrency(data?.financials?.cost, currency)}
          icon="📊"
          trend={-3.2}
          color="blue"
          subValue={TEXT.kpi.costsSub}
        />
        <PremiumCard
          title={TEXT.kpi.yieldPerf}
          value={`${yieldPercent}%`}
          icon="🌾"
          trend={yieldTrend}
          color={yieldPercent > 80 ? 'emerald' : yieldPercent > 60 ? 'gold' : 'rose'}
          subValue={TEXT.kpi.yieldPerfSub}
        />
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <GlassContainer
            title={TEXT.charts.profitability}
            action={
              <div className="flex gap-2">
                <button className="rounded-lg bg-emerald-500/20 px-3 py-1 text-xs text-emerald-400">
                  {TEXT.buttons.sixMonths}
                </button>
                <button className="rounded-lg px-3 py-1 text-xs text-white/50 hover:bg-white/5">
                  {TEXT.buttons.oneYear}
                </button>
              </div>
            }
          >
            <div className="h-[350px]">
              <Line data={chartData} options={chartOptions} />
            </div>
          </GlassContainer>
        </div>

        <div className="lg:col-span-1">
          <FinancialRiskZone data={data} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 pb-12 lg:grid-cols-2">
        <GlassContainer title={TEXT.charts.pulse}>
          <div className="space-y-4">
            {[
              { label: 'خطط نشطة', val: data?.pulse?.active_plans ?? data?.active_plans ?? 0 },
              { label: 'الفواتير المعتمدة', val: data?.pulse?.approved_invoices ?? 0 },
              {
                label: 'العائد المتوقع',
                val: `${Number(data?.pulse?.expected_yield ?? data?.yields?.expected ?? 0).toLocaleString('en-US', { maximumFractionDigits: 2 })} كجم`,
              },
              {
                label: 'العائد الفعلي',
                val: `${Number(data?.pulse?.actual_yield ?? data?.yields?.actual ?? 0).toLocaleString('en-US', { maximumFractionDigits: 2 })} كجم`,
              },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between rounded-2xl border border-white/5 bg-white/5 p-4"
              >
                <div>
                  <p className="text-xs font-bold uppercase tracking-tighter text-white/40">
                    {item.label}
                  </p>
                  <p className="mt-0.5 text-xl font-bold">{item.val}</p>
                </div>
              </div>
            ))}
          </div>
        </GlassContainer>

        <GlassContainer title={TEXT.charts.grading}>
          <div className="space-y-3">
            {gradingRows.map((row) => (
              <div
                key={`${row.crop_id || row.crop_name}`}
                className="rounded-2xl border border-white/5 bg-white/5 p-4"
              >
                <div className="mb-2 flex items-center justify-between">
                  <div className="font-bold text-white/90">{row.crop_name}</div>
                  <div className="text-xs text-white/50">{row.plans} خطط</div>
                </div>
                <div className="text-sm text-white/60" dir="ltr">
                  الإنتاج المتوقع:{' '}
                  {Number(row.expected_yield || 0).toLocaleString('en-US', {
                    maximumFractionDigits: 2,
                  })}
                </div>
              </div>
            ))}
          </div>
        </GlassContainer>
      </div>
    </div>
  )
}

export default CommercialDashboard
