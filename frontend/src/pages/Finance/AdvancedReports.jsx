import React, { useState, useEffect } from 'react'
import { useFarmContext } from '../../api/farmContext'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import {
  FileText,
  Download,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  CheckCircle,
  FileBarChart,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  Eye,
  Scale,
} from 'lucide-react'
import useFinancialFilters from '../../hooks/useFinancialFilters'
import FinancialFilterBar from '../../components/filters/FinancialFilterBar'

// ─────────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM
// ─────────────────────────────────────────────────────────────────────────────
const KPI_GRADIENTS = {
  revenue: 'from-emerald-500 to-teal-600',
  expense: 'from-rose-500 to-red-600',
  profit: 'from-blue-600 to-indigo-600',
  balance: 'from-amber-400 to-orange-500',
}

function GlassCard({ children, className = '' }) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl border border-white/20 dark:border-slate-700/50 shadow-xl ${className}`}
    >
      {children}
    </div>
  )
}

function KPICard({ title, value, icon: Icon, gradient, trend, suffix = '' }) {
  const isPositive = parseFloat(value) >= 0
  return (
    <GlassCard>
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-500 dark:text-slate-400 mb-1">{title}</p>
            <h3
              className="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent"
              dir="ltr"
            >
              {value}{' '}
              {suffix && <span className="text-sm font-normal text-gray-400">{suffix}</span>}
            </h3>
            {trend !== undefined && (
              <div
                className={`flex items-center gap-1 mt-1 text-xs font-medium ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}
              >
                {isPositive ? (
                  <ArrowUpRight className="w-3 h-3" />
                ) : (
                  <ArrowDownRight className="w-3 h-3" />
                )}
                {trend}
              </div>
            )}
          </div>
          <div className={`p-3 rounded-xl bg-gradient-to-br ${gradient} shadow-lg`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>
      </div>
      <div className={`h-1 bg-gradient-to-r ${gradient}`} />
    </GlassCard>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function formatDecimal(val) {
  const num = parseFloat(val || '0')
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function AdvancedReports() {
  const { selectedFarmId } = useFarmContext()
  const [reportType, setReportType] = useState('profitability_pdf')

  // PDF Generation
  const [isGenerating, setIsGenerating] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState('')
  const [_jobId, setJobId] = useState(null)

  // On-Screen Preview Data
  const [previewData, setPreviewData] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Trial Balance Data
  const [trialData, setTrialData] = useState(null)
  const [trialLoading, setTrialLoading] = useState(false)

  // Date Range
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  // Dimensions (farm → costCenter → cropPlan cascade)
  const {
    filters: financialFilters,
    options: filterOptions,
    loading: filterLoading,
    setFilter: setFinancialFilter,
    resetFilters,
  } = useFinancialFilters({ dimensions: ['farm', 'costCenter', 'crop_plan'] })

  // [AGRI-GUARDIAN §Axis-6] Active farm: prefer in-page filter, fallback to top-bar
  const activeFarmId = financialFilters.farm || selectedFarmId

  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

  // ─── FETCH ON-SCREEN PREVIEW ────────────────────────────────────
  const fetchPreview = async () => {
    if (!activeFarmId) return
    setPreviewLoading(true)
    setPreviewData(null)
    try {
      const params = { farm_id: activeFarmId }
      if (financialFilters.costCenter) params.cost_center_id = financialFilters.costCenter
      if (financialFilters.crop_plan) params.crop_plan_id = financialFilters.crop_plan
      if (dateFrom) params.start = dateFrom
      if (dateTo) params.end = dateTo

      if (reportType === 'profitability_pdf') {
        const { data } = await api.get('/finance/profitability-summary/', { params })
        setPreviewData({ type: 'profitability', ...data })
      }
    } catch (err) {
      console.error('Preview fetch failed:', err)
      toast.error('تعذر تحميل بيانات المعاينة')
    } finally {
      setPreviewLoading(false)
    }
  }

  // ─── FETCH TRIAL BALANCE ────────────────────────────────────────
  const fetchTrialBalance = async () => {
    if (!activeFarmId) return
    setTrialLoading(true)
    setTrialData(null)
    try {
      const params = { farm_id: activeFarmId }
      if (financialFilters.costCenter) params.cost_center_id = financialFilters.costCenter
      if (financialFilters.crop_plan) params.crop_plan_id = financialFilters.crop_plan
      if (dateFrom) params.start = dateFrom
      if (dateTo) params.end = dateTo

      const { data } = await api.get('/finance/trial-balance/', { params })
      setTrialData(data)
    } catch (err) {
      console.error('Trial Balance fetch failed:', err)
      toast.error('تعذر تحميل ميزان المراجعة')
    } finally {
      setTrialLoading(false)
    }
  }

  // Auto-fetch on initial render + type change
  useEffect(() => {
    if (reportType === 'profitability_pdf') {
      fetchPreview()
    } else if (reportType === 'trial_balance') {
      fetchTrialBalance()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeFarmId, reportType])

  // ─── PDF GENERATION (existing logic) ────────────────────────────
  const pollAdvancedReport = async (targetJobId) => {
    const maxAttempts = 20
    const delayMs = 1500
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const { data } = await api.get(`/advanced-report/requests/${targetJobId}/`)
      if (data.status === 'completed') return data
      if (data.status === 'failed') throw new Error(data.error_message || 'فشل توليد التقرير')
      await wait(delayMs)
    }
    throw new Error('انتهت مهلة توليد التقرير')
  }

  const downloadReportFile = async (resultUrl, filename) => {
    const downloadOriginUrl = `${window.location.origin}${resultUrl}`
    const response = await fetch(downloadOriginUrl, { credentials: 'include' })
    if (!response.ok) throw new Error('فشل تحميل الملف')
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  const handleGenerateReport = async () => {
    if (!activeFarmId) {
      toast.error('الرجاء اختيار مزرعة أولاً')
      return
    }
    setIsGenerating(true)
    setDownloadUrl('')
    setJobId(null)
    const toastId = toast.loading('يتم إعداد وتحليل التقرير المالي...')
    try {
      const params = {
        farm_id: activeFarmId,
        report_type: reportType,
        format: 'pdf',
      }
      if (financialFilters.costCenter) params.cost_center_id = financialFilters.costCenter
      if (financialFilters.crop_plan) params.crop_plan_id = financialFilters.crop_plan
      if (dateFrom) params.start_date = dateFrom
      if (dateTo) params.end_date = dateTo

      const response = await api.post('/advanced-report/requests/', params)
      const job = response.data
      setJobId(job.id)
      const readyReport = await pollAdvancedReport(job.id)
      setDownloadUrl(readyReport.result_url)
      toast.success('تم إصدار التقرير بنجاح!', { id: toastId })
    } catch (error) {
      console.error(error)
      const message = error?.message || 'تعذر إصدار التقرير المالي'
      toast.error(message, { id: toastId })
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownload = async () => {
    if (!downloadUrl) return
    try {
      const filename = `financial-report-${activeFarmId}-${new Date().getTime()}.pdf`
      await downloadReportFile(downloadUrl, filename)
    } catch (err) {
      toast.error('حدث خطأ أثناء تنزيل الملف')
    }
  }

  const handleApplyFilters = () => {
    if (reportType === 'profitability_pdf') {
      fetchPreview()
    } else if (reportType === 'trial_balance') {
      fetchTrialBalance()
    }
  }

  // ─── RENDER ─────────────────────────────────────────────────────
  return (
    <div
      data-testid="advanced-reports-page"
      dir="rtl"
      className="app-page space-y-8 max-w-7xl mx-auto"
    >
      {/* ─── HEADER ─── */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-blue-600 dark:from-blue-400 to-indigo-500 dark:to-indigo-200 bg-clip-text text-transparent">
            التقارير المالية المتقدمة
          </h1>
          <p className="text-gray-500 dark:text-zinc-500 font-medium mt-2 max-w-2xl leading-relaxed">
            محرك تقارير P&L (الأرباح والخسائر) وموازين المراجعة المفلترة متصل بـ Agri-Guardian
            لتشكيل تحليلات مقفلة محاسبياً (Tenant Isolated).
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-500">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <div className="text-sm font-bold flex flex-col">
            <span>بيانات موثقة مالياً</span>
            <span className="text-amber-500/70 font-medium text-xs">لا يمكن التلاعب بالأرصدة</span>
          </div>
        </div>
      </div>

      {!activeFarmId ? (
        <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-12 text-center">
          <FileBarChart className="w-16 h-16 text-blue-400 mx-auto mb-4 opacity-50" />
          <h2 className="text-2xl font-bold text-blue-900 dark:text-white mb-2">
            اختر بيئة التشغيل
          </h2>
          <p className="text-slate-700 dark:text-white/60">
            يرجى اختيار المزرعة من القائمة أعلاه أو الشريط العلوي لعرض التقارير.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* ─── CONFIGURATION PANEL ─── */}
          <div className="lg:col-span-8 space-y-6">
            <div className="app-panel p-6 space-y-6 border-t-4 border-t-blue-500">
              <h2 className="text-xl font-bold flex items-center gap-2 text-slate-800 dark:text-white">
                <FileText className="w-6 h-6 text-blue-500" />
                معايير التقرير
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Report Type Selector */}
                <div className="space-y-2 col-span-1 md:col-span-2">
                  <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                    نوع التقرير
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* P&L Button */}
                    <button
                      onClick={() => setReportType('profitability_pdf')}
                      className={`relative p-4 rounded-xl border-2 text-start transition-all ${
                        reportType === 'profitability_pdf'
                          ? 'border-blue-500 bg-blue-500/5 ring-4 ring-blue-500/10'
                          : 'border-slate-200 dark:border-white/10 hover:border-blue-300'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <TrendingUp
                          className={`w-6 h-6 ${reportType === 'profitability_pdf' ? 'text-blue-500' : 'text-slate-400'}`}
                        />
                        {reportType === 'profitability_pdf' && (
                          <CheckCircle className="w-5 h-5 text-blue-500" />
                        )}
                      </div>
                      <h3 className="font-bold text-slate-900 dark:text-white">
                        تحليل الربحية P&L
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        تجميع حركات الدخل والمصروفات لاستخراج صافي الدخل.
                      </p>
                    </button>

                    {/* Trial Balance Button — NOW ACTIVE */}
                    <button
                      onClick={() => setReportType('trial_balance')}
                      className={`relative p-4 rounded-xl border-2 text-start transition-all ${
                        reportType === 'trial_balance'
                          ? 'border-emerald-500 bg-emerald-500/5 ring-4 ring-emerald-500/10'
                          : 'border-slate-200 dark:border-white/10 hover:border-emerald-300'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <Scale
                          className={`w-6 h-6 ${reportType === 'trial_balance' ? 'text-emerald-500' : 'text-slate-400'}`}
                        />
                        {reportType === 'trial_balance' && (
                          <CheckCircle className="w-5 h-5 text-emerald-500" />
                        )}
                      </div>
                      <h3 className="font-bold text-slate-900 dark:text-white">ميزان المراجعة</h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        أرصدة المدين والدائن مع فحص التوازن (Pre-Close Gate).
                      </p>
                    </button>
                  </div>
                </div>

                {/* Date Range */}
                <div className="space-y-2">
                  <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                    من تاريخ
                  </label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="app-input w-full"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                    إلى تاريخ
                  </label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="app-input w-full"
                  />
                </div>
              </div>
            </div>

            {/* Smart Filters */}
            <div className="app-panel p-6">
              <h3 className="text-lg font-bold mb-4 text-slate-800 dark:text-white flex items-center justify-between">
                <span>الأبعاد التحليلية (Cost Centers)</span>
                <span className="text-xs font-normal px-2 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded">
                  Tenant Isolated
                </span>
              </h3>
              <FinancialFilterBar
                filters={financialFilters}
                options={filterOptions}
                loading={filterLoading}
                setFilter={setFinancialFilter}
                onReset={resetFilters}
                dimensions={['farm', 'costCenter', 'crop_plan']}
                layout="grid"
              />
              {/* Apply Filters Button */}
              <div className="mt-4 flex justify-end">
                <button
                  onClick={handleApplyFilters}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-sm hover:from-blue-500 hover:to-indigo-500 shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2"
                >
                  <Eye className="w-4 h-4" />
                  عرض التقرير
                </button>
              </div>
            </div>

            {/* ─── ON-SCREEN PREVIEW ─── */}
            {reportType === 'profitability_pdf' && (previewData || previewLoading) && (
              <div className="space-y-6">
                {/* KPI Summary Cards */}
                {previewData && !previewLoading && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KPICard
                      title="إجمالي الإيرادات"
                      value={formatDecimal(previewData.totals?.total_revenue)}
                      icon={TrendingUp}
                      gradient={KPI_GRADIENTS.revenue}
                      suffix={previewData.currency}
                      trend="Credit Normal"
                    />
                    <KPICard
                      title="إجمالي المصروفات"
                      value={formatDecimal(previewData.totals?.total_expense)}
                      icon={TrendingDown}
                      gradient={KPI_GRADIENTS.expense}
                      suffix={previewData.currency}
                      trend="Debit Normal"
                    />
                    <KPICard
                      title="صافي الربح / (الخسارة)"
                      value={formatDecimal(previewData.totals?.net_income)}
                      icon={DollarSign}
                      gradient={
                        parseFloat(previewData.totals?.net_income || 0) >= 0
                          ? KPI_GRADIENTS.profit
                          : KPI_GRADIENTS.expense
                      }
                      suffix={previewData.currency}
                    />
                  </div>
                )}

                {/* P&L Table */}
                <GlassCard>
                  <div className="border-t-4 border-t-blue-500">
                    <div className="p-6">
                      <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                        <BarChart3 className="w-5 h-5 text-blue-500" />
                        قائمة الدخل (Income Statement)
                      </h3>

                      {previewLoading ? (
                        <div className="animate-pulse space-y-3">
                          {[1, 2, 3, 4, 5].map((i) => (
                            <div
                              key={i}
                              className="h-10 bg-gray-200 dark:bg-slate-700 rounded-lg"
                            />
                          ))}
                        </div>
                      ) : previewData ? (
                        <div className="space-y-6">
                          {/* Revenue Section */}
                          {previewData.revenue_accounts?.length > 0 && (
                            <div>
                              <h4 className="text-sm font-bold text-emerald-600 dark:text-emerald-400 mb-3 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                الإيرادات
                              </h4>
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead>
                                    <tr className="text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                                      <th className="text-start py-2 px-3 font-medium">الحساب</th>
                                      <th className="text-start py-2 px-3 font-medium">
                                        رقم الحساب
                                      </th>
                                      <th className="text-end py-2 px-3 font-medium">المدين</th>
                                      <th className="text-end py-2 px-3 font-medium">الدائن</th>
                                      <th className="text-end py-2 px-3 font-medium">الصافي</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {previewData.revenue_accounts.map((acc) => (
                                      <tr
                                        key={acc.code}
                                        className="border-b border-slate-100 dark:border-slate-800 hover:bg-emerald-50/50 dark:hover:bg-emerald-900/10 transition-colors"
                                      >
                                        <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                                          {acc.name}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-slate-500 dark:text-slate-400 font-mono text-xs"
                                          dir="ltr"
                                        >
                                          {acc.code}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-end text-slate-600 dark:text-slate-300"
                                          dir="ltr"
                                        >
                                          {formatDecimal(acc.total_debit)}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-end text-emerald-600 dark:text-emerald-400 font-bold"
                                          dir="ltr"
                                        >
                                          {formatDecimal(acc.total_credit)}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-end text-emerald-700 dark:text-emerald-300 font-bold"
                                          dir="ltr"
                                        >
                                          {formatDecimal(acc.net)}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* Expense Section */}
                          {previewData.expense_accounts?.length > 0 && (
                            <div>
                              <h4 className="text-sm font-bold text-rose-600 dark:text-rose-400 mb-3 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-rose-500" />
                                المصروفات
                              </h4>
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead>
                                    <tr className="text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                                      <th className="text-start py-2 px-3 font-medium">الحساب</th>
                                      <th className="text-start py-2 px-3 font-medium">
                                        رقم الحساب
                                      </th>
                                      <th className="text-end py-2 px-3 font-medium">المدين</th>
                                      <th className="text-end py-2 px-3 font-medium">الدائن</th>
                                      <th className="text-end py-2 px-3 font-medium">الصافي</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {previewData.expense_accounts.map((acc) => (
                                      <tr
                                        key={acc.code}
                                        className="border-b border-slate-100 dark:border-slate-800 hover:bg-rose-50/50 dark:hover:bg-rose-900/10 transition-colors"
                                      >
                                        <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                                          {acc.name}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-slate-500 dark:text-slate-400 font-mono text-xs"
                                          dir="ltr"
                                        >
                                          {acc.code}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-end text-rose-600 dark:text-rose-400 font-bold"
                                          dir="ltr"
                                        >
                                          {formatDecimal(acc.total_debit)}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-end text-slate-600 dark:text-slate-300"
                                          dir="ltr"
                                        >
                                          {formatDecimal(acc.total_credit)}
                                        </td>
                                        <td
                                          className="py-2.5 px-3 text-end text-rose-700 dark:text-rose-300 font-bold"
                                          dir="ltr"
                                        >
                                          {formatDecimal(acc.net)}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* Net Income Summary Bar */}
                          <div
                            className={`p-4 rounded-xl border-2 ${
                              parseFloat(previewData.totals?.net_income || 0) >= 0
                                ? 'border-emerald-500/30 bg-emerald-500/5'
                                : 'border-rose-500/30 bg-rose-500/5'
                            }`}
                          >
                            <div className="flex justify-between items-center">
                              <span className="font-bold text-lg text-slate-800 dark:text-white">
                                صافي الربح / (الخسارة) التشغيلية
                              </span>
                              <span
                                className={`text-2xl font-black ${
                                  parseFloat(previewData.totals?.net_income || 0) >= 0
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : 'text-rose-600 dark:text-rose-400'
                                }`}
                                dir="ltr"
                              >
                                {formatDecimal(previewData.totals?.net_income)}{' '}
                                {previewData.currency}
                              </span>
                            </div>
                          </div>

                          {/* No data message */}
                          {!previewData.revenue_accounts?.length &&
                            !previewData.expense_accounts?.length && (
                              <div className="text-center py-12 text-slate-400">
                                <FileBarChart className="w-12 h-12 mx-auto mb-3 opacity-40" />
                                <p className="font-medium">لا توجد قيود مالية مسجلة لهذه الفلاتر</p>
                                <p className="text-sm mt-1">
                                  حاول تعديل نطاق التاريخ أو الأبعاد التحليلية
                                </p>
                              </div>
                            )}
                        </div>
                      ) : null}
                    </div>
                  </div>
                </GlassCard>
              </div>
            )}

            {/* ─── TRIAL BALANCE PREVIEW ─── */}
            {reportType === 'trial_balance' && (trialData || trialLoading) && (
              <div className="space-y-6">
                {/* Balance Status Badge */}
                {trialData && !trialLoading && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KPICard
                      title="إجمالي المدين"
                      value={formatDecimal(trialData.totals?.total_debit)}
                      icon={ArrowUpRight}
                      gradient={KPI_GRADIENTS.expense}
                      suffix={trialData.currency}
                    />
                    <KPICard
                      title="إجمالي الدائن"
                      value={formatDecimal(trialData.totals?.total_credit)}
                      icon={ArrowDownRight}
                      gradient={KPI_GRADIENTS.revenue}
                      suffix={trialData.currency}
                    />
                    <KPICard
                      title="حالة التوازن"
                      value={trialData.totals?.is_balanced ? '✅ متوازن' : '⚠️ غير متوازن'}
                      icon={Scale}
                      gradient={
                        trialData.totals?.is_balanced ? KPI_GRADIENTS.profit : KPI_GRADIENTS.expense
                      }
                      trend={
                        trialData.totals?.is_balanced
                          ? 'Pre-Close Gate: PASS'
                          : `فرق: ${formatDecimal(trialData.totals?.difference)}`
                      }
                    />
                  </div>
                )}

                <GlassCard>
                  <div className="border-t-4 border-t-emerald-500">
                    <div className="p-6">
                      <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                        <Scale className="w-5 h-5 text-emerald-500" />
                        ميزان المراجعة (Trial Balance)
                      </h3>

                      {trialLoading ? (
                        <div className="animate-pulse space-y-3">
                          {[1, 2, 3, 4, 5].map((i) => (
                            <div
                              key={i}
                              className="h-10 bg-gray-200 dark:bg-slate-700 rounded-lg"
                            />
                          ))}
                        </div>
                      ) : trialData?.accounts?.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="text-slate-500 dark:text-slate-400 border-b-2 border-slate-200 dark:border-slate-700">
                                <th className="text-start py-3 px-3 font-bold">الحساب</th>
                                <th className="text-start py-3 px-3 font-bold">رقم الحساب</th>
                                <th className="text-end py-3 px-3 font-bold">المدين</th>
                                <th className="text-end py-3 px-3 font-bold">الدائن</th>
                                <th className="text-end py-3 px-3 font-bold">الرصيد</th>
                              </tr>
                            </thead>
                            <tbody>
                              {trialData.accounts.map((acc) => {
                                const balance = parseFloat(acc.balance || 0)
                                return (
                                  <tr
                                    key={acc.code}
                                    className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                                  >
                                    <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                                      {acc.name}
                                    </td>
                                    <td
                                      className="py-2.5 px-3 text-slate-500 dark:text-slate-400 font-mono text-xs"
                                      dir="ltr"
                                    >
                                      {acc.code}
                                    </td>
                                    <td className="py-2.5 px-3 text-end font-medium" dir="ltr">
                                      {formatDecimal(acc.total_debit)}
                                    </td>
                                    <td className="py-2.5 px-3 text-end font-medium" dir="ltr">
                                      {formatDecimal(acc.total_credit)}
                                    </td>
                                    <td
                                      className={`py-2.5 px-3 text-end font-bold ${balance > 0 ? 'text-rose-600' : balance < 0 ? 'text-emerald-600' : 'text-slate-500'}`}
                                      dir="ltr"
                                    >
                                      {formatDecimal(acc.balance)}
                                    </td>
                                  </tr>
                                )
                              })}
                            </tbody>
                            <tfoot>
                              <tr className="border-t-2 border-slate-300 dark:border-slate-600 bg-slate-50/50 dark:bg-slate-800/50 font-bold">
                                <td
                                  className="py-3 px-3 text-slate-800 dark:text-white"
                                  colSpan={2}
                                >
                                  الإجمالي
                                </td>
                                <td
                                  className="py-3 px-3 text-end text-slate-800 dark:text-white"
                                  dir="ltr"
                                >
                                  {formatDecimal(trialData.totals?.total_debit)}
                                </td>
                                <td
                                  className="py-3 px-3 text-end text-slate-800 dark:text-white"
                                  dir="ltr"
                                >
                                  {formatDecimal(trialData.totals?.total_credit)}
                                </td>
                                <td
                                  className={`py-3 px-3 text-end font-black ${trialData.totals?.is_balanced ? 'text-emerald-600' : 'text-rose-600'}`}
                                  dir="ltr"
                                >
                                  {formatDecimal(trialData.totals?.difference)}
                                </td>
                              </tr>
                            </tfoot>
                          </table>
                        </div>
                      ) : (
                        <div className="text-center py-12 text-slate-400">
                          <Scale className="w-12 h-12 mx-auto mb-3 opacity-40" />
                          <p className="font-medium">لا توجد قيود مالية مسجلة لهذه الفلاتر</p>
                        </div>
                      )}
                    </div>
                  </div>
                </GlassCard>
              </div>
            )}
          </div>

          {/* ─── ACTION PANEL (Sidebar) ─── */}
          <div className="lg:col-span-4 space-y-6">
            <div className="app-panel p-6 sticky top-24 border-t-4 border-t-indigo-500">
              <h2 className="font-bold text-lg mb-4 text-slate-800 dark:text-white">
                إجراءات التقرير
              </h2>

              <div className="space-y-4">
                <button
                  onClick={handleGenerateReport}
                  disabled={isGenerating}
                  className="w-full py-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-lg hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/30 transition-all flex items-center justify-center gap-2"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      جاري المعالجة...
                    </>
                  ) : (
                    <>
                      <FileText className="w-5 h-5" />
                      إنشاء تقرير PDF
                    </>
                  )}
                </button>

                {downloadUrl && !isGenerating && (
                  <div className="pt-6 border-t border-slate-200 dark:border-white/10 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 text-center">
                      <div className="w-12 h-12 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                        <CheckCircle className="w-6 h-6 text-emerald-500" />
                      </div>
                      <h3 className="font-bold text-emerald-700 dark:text-emerald-400 mb-1">
                        التقرير جاهز!
                      </h3>
                      <p className="text-sm text-emerald-600/70 dark:text-emerald-400/70 mb-4">
                        تم تجميع بيانات الدفتر المالي بنجاح.
                      </p>
                      <button
                        onClick={handleDownload}
                        className="w-full py-3 rounded-lg bg-emerald-500 text-white font-bold hover:bg-emerald-400 transition-colors flex items-center justify-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        تنزيل المستند (PDF)
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
