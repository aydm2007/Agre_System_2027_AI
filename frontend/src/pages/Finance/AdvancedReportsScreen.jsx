import React, { useEffect, useMemo, useState } from 'react'
import { toast } from 'react-hot-toast'
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Eye,
  FileBarChart,
  FileText,
  RefreshCw,
  Scale,
  TrendingUp,
} from 'lucide-react'

import { useFarmContext } from '../../api/farmContext'
import { api, AsyncReports } from '../../api/client'
import useFinancialFilters from '../../hooks/useFinancialFilters'
import FinancialFilterBar from '../../components/filters/FinancialFilterBar'
import { buildAdvancedFinancialReportParams } from './reportParams'

function formatDecimal(value) {
  const num = Number(value || 0)
  return num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function StatusBadge({ status, errorMessage }) {
  const styles = {
    idle: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    pending: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300',
    failed: 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300',
  }

  const labels = {
    idle: 'جاهز',
    pending: 'جارٍ التوليد',
    completed: 'جاهز للتنزيل',
    failed: errorMessage || 'فشل التوليد',
  }

  return (
    <div className={`rounded-xl px-3 py-2 text-sm font-semibold ${styles[status] || styles.idle}`}>
      {labels[status] || labels.idle}
    </div>
  )
}

function SummaryCard({ title, value, icon: Icon, accent }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">{title}</span>
        <div className={`rounded-xl p-2 ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="text-2xl font-black text-slate-900 dark:text-white" dir="ltr">
        {value}
      </div>
    </div>
  )
}

async function pollAsyncReport(jobId) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const { data } = await AsyncReports.status(jobId)
    if (data.status === 'completed') {
      return data
    }
    if (data.status === 'failed') {
      throw new Error(data.error_message || 'فشل توليد التقرير')
    }
    await new Promise((resolve) => setTimeout(resolve, 1500))
  }
  throw new Error('انتهت مهلة توليد التقرير')
}

export default function AdvancedReportsScreen() {
  const { selectedFarmId } = useFarmContext()
  const [reportType, setReportType] = useState('profitability_pdf')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [trialData, setTrialData] = useState(null)
  const [jobState, setJobState] = useState({
    status: 'idle',
    id: null,
    resultUrl: '',
    errorMessage: '',
  })

  const { filters, options, loading, setFilter, resetFilters } = useFinancialFilters({
    dimensions: ['farm', 'costCenter', 'crop_plan'],
  })

  const activeFarmId = filters.farm || selectedFarmId

  const previewParams = useMemo(() => {
    const params = { farm_id: activeFarmId }
    if (filters.costCenter) params.cost_center_id = filters.costCenter
    if (filters.crop_plan) params.crop_plan_id = filters.crop_plan
    if (dateFrom) params.start = dateFrom
    if (dateTo) params.end = dateTo
    return params
  }, [activeFarmId, filters.costCenter, filters.crop_plan, dateFrom, dateTo])

  const fetchPreview = async () => {
    if (!activeFarmId) return
    setPreviewLoading(true)
    try {
      if (reportType === 'trial_balance') {
        const { data } = await api.get('/finance/trial-balance/', { params: previewParams })
        setTrialData(data)
        setPreviewData(null)
      } else {
        const { data } = await api.get('/finance/profitability-summary/', { params: previewParams })
        setPreviewData(data)
        setTrialData(null)
      }
    } catch (error) {
      console.error('advanced reports preview failed', error)
      setPreviewData(null)
      setTrialData(null)
      toast.error('تعذر تحميل المعاينة المالية')
    } finally {
      setPreviewLoading(false)
    }
  }

  useEffect(() => {
    if (activeFarmId) {
      fetchPreview()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeFarmId, reportType])

  const handleGenerateReport = async () => {
    if (!activeFarmId) {
      toast.error('الرجاء اختيار مزرعة أولاً')
      return
    }
    if (reportType !== 'profitability_pdf') {
      toast.error('توليد PDF متاح حالياً لتقرير الربحية فقط')
      return
    }

    setJobState({ status: 'pending', id: null, resultUrl: '', errorMessage: '' })
    const toastId = toast.loading('جارٍ إنشاء تقرير PDF المالي...')
    try {
      const payload = buildAdvancedFinancialReportParams({
        farmId: activeFarmId,
        reportType,
        costCenterId: filters.costCenter,
        cropPlanId: filters.crop_plan,
        start: dateFrom,
        end: dateTo,
      })
      const { data } = await AsyncReports.request(payload)
      setJobState({ status: 'pending', id: data.id, resultUrl: '', errorMessage: '' })

      const ready = await pollAsyncReport(data.id)
      setJobState({
        status: 'completed',
        id: ready.id,
        resultUrl: ready.result_url,
        errorMessage: '',
      })
      toast.success('أصبح ملف PDF جاهزاً للتنزيل', { id: toastId })
    } catch (error) {
      const message = error?.message || 'تعذر توليد تقرير PDF'
      setJobState({ status: 'failed', id: null, resultUrl: '', errorMessage: message })
      toast.error(message, { id: toastId })
    }
  }

  const handleDownload = async () => {
    if (!jobState.resultUrl) return
    try {
      await AsyncReports.download(
        jobState.resultUrl,
        `financial-report-${activeFarmId}-${Date.now()}.pdf`,
      )
    } catch (error) {
      toast.error(error?.message || 'فشل تنزيل الملف')
    }
  }

  return (
    <div
      className="app-page mx-auto max-w-7xl space-y-8"
      dir="rtl"
      data-testid="advanced-reports-page"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900 dark:text-white">
            التقارير المالية المتقدمة
          </h1>
          <p className="mt-2 max-w-2xl text-sm font-medium text-slate-500 dark:text-slate-400">
            معاينة مالية مباشرة مع مسار PDF موحد يعتمد نفس الفلاتر ونفس عقد الطلبات الخلفي.
          </p>
        </div>
        <StatusBadge status={jobState.status} errorMessage={jobState.errorMessage} />
      </div>

      {!activeFarmId ? (
        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-10 text-center dark:border-blue-500/20 dark:bg-blue-500/5">
          <FileBarChart className="mx-auto mb-4 h-12 w-12 text-blue-500" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">اختر المزرعة أولاً</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            لن يتم إنشاء أو تنزيل أي تقرير قبل تحديد نطاق المزرعة المعتمدة.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
            <div className="app-panel space-y-6 p-6">
              <div className="grid gap-4 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setReportType('profitability_pdf')}
                  className={`rounded-2xl border p-4 text-start transition ${
                    reportType === 'profitability_pdf'
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-500/10'
                      : 'border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <TrendingUp className="h-5 w-5 text-blue-500" />
                    {reportType === 'profitability_pdf' && (
                      <CheckCircle2 className="h-5 w-5 text-blue-500" />
                    )}
                  </div>
                  <div className="font-bold text-slate-900 dark:text-white">تقرير الربحية PDF</div>
                  <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    يولد ملف PDF مالي رسمي بنفس نطاق الفلاتر الظاهر.
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setReportType('trial_balance')}
                  className={`rounded-2xl border p-4 text-start transition ${
                    reportType === 'trial_balance'
                      ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10'
                      : 'border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <Scale className="h-5 w-5 text-emerald-500" />
                    {reportType === 'trial_balance' && (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    )}
                  </div>
                  <div className="font-bold text-slate-900 dark:text-white">ميزان المراجعة</div>
                  <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    معاينة تفاعلية للحسابات. التصدير PDF غير مفعل لهذا النوع بعد.
                  </div>
                </button>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                  <span>من تاريخ</span>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="app-input w-full"
                  />
                </label>
                <label className="space-y-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                  <span>إلى تاريخ</span>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="app-input w-full"
                  />
                </label>
              </div>

              <FinancialFilterBar
                filters={filters}
                options={options}
                loading={loading}
                setFilter={setFilter}
                onReset={resetFilters}
                dimensions={['farm', 'costCenter', 'crop_plan']}
                layout="grid"
              />

              <div className="flex flex-wrap justify-end gap-3">
                <button
                  type="button"
                  onClick={fetchPreview}
                  className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <span className="inline-flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    عرض المعاينة
                  </span>
                </button>
                <button
                  type="button"
                  data-testid="generate-report-button"
                  onClick={handleGenerateReport}
                  disabled={jobState.status === 'pending'}
                  className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <span className="inline-flex items-center gap-2">
                    {jobState.status === 'pending' ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <FileText className="h-4 w-4" />
                    )}
                    إنشاء تقرير PDF
                  </span>
                </button>
              </div>
            </div>

            <div className="app-panel space-y-4 p-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">حالة التصدير</h2>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <div>
                  نوع التقرير:{' '}
                  {reportType === 'profitability_pdf' ? 'PDF الربحية' : 'ميزان المراجعة'}
                </div>
                <div>المزرعة: {activeFarmId}</div>
                <div>الحالة: {jobState.status}</div>
                {jobState.id && <div>رقم الطلب: {jobState.id}</div>}
              </div>
              <button
                type="button"
                data-testid="download-report-button"
                onClick={handleDownload}
                disabled={jobState.status !== 'completed' || !jobState.resultUrl}
                className="w-full rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="inline-flex items-center gap-2">
                  <Download className="h-4 w-4" />
                  تنزيل التقرير
                </span>
              </button>
              {reportType === 'trial_balance' && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
                  تصدير PDF لهذا النوع غير مفعل بعد. المعاينة على الشاشة فقط.
                </div>
              )}
            </div>
          </div>

          {jobState.status === 'failed' && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300">
              <div className="inline-flex items-center gap-2 font-semibold">
                <AlertCircle className="h-4 w-4" />
                {jobState.errorMessage || 'فشل توليد التقرير'}
              </div>
            </div>
          )}

          {previewLoading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
              جارٍ تحميل المعاينة...
            </div>
          ) : reportType === 'profitability_pdf' && previewData ? (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <SummaryCard
                  title="إجمالي الإيرادات"
                  value={formatDecimal(previewData.totals?.total_revenue)}
                  icon={TrendingUp}
                  accent="bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-300"
                />
                <SummaryCard
                  title="إجمالي المصروفات"
                  value={formatDecimal(previewData.totals?.total_expense)}
                  icon={AlertCircle}
                  accent="bg-rose-100 text-rose-600 dark:bg-rose-500/10 dark:text-rose-300"
                />
                <SummaryCard
                  title="صافي الربح"
                  value={formatDecimal(previewData.totals?.net_income)}
                  icon={FileBarChart}
                  accent="bg-blue-100 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300"
                />
              </div>

              <div className="app-panel overflow-x-auto p-6">
                <h2 className="mb-4 text-lg font-bold text-slate-900 dark:text-white">
                  تفاصيل قائمة الدخل
                </h2>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-start text-slate-500 dark:border-slate-800 dark:text-slate-400">
                      <th className="px-3 py-2 text-start">الحساب</th>
                      <th className="px-3 py-2 text-start">الرمز</th>
                      <th className="px-3 py-2 text-end">المدين</th>
                      <th className="px-3 py-2 text-end">الدائن</th>
                      <th className="px-3 py-2 text-end">الصافي</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ...(previewData.revenue_accounts || []),
                      ...(previewData.expense_accounts || []),
                    ].map((row) => (
                      <tr
                        key={`${row.code}-${row.name}`}
                        className="border-b border-slate-100 dark:border-slate-900"
                      >
                        <td className="px-3 py-2">{row.name}</td>
                        <td className="px-3 py-2" dir="ltr">
                          {row.code}
                        </td>
                        <td className="px-3 py-2 text-end" dir="ltr">
                          {formatDecimal(row.total_debit)}
                        </td>
                        <td className="px-3 py-2 text-end" dir="ltr">
                          {formatDecimal(row.total_credit)}
                        </td>
                        <td className="px-3 py-2 text-end" dir="ltr">
                          {formatDecimal(row.net)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : reportType === 'trial_balance' && trialData ? (
            <div className="app-panel overflow-x-auto p-6">
              <h2 className="mb-4 text-lg font-bold text-slate-900 dark:text-white">
                ميزان المراجعة
              </h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-start text-slate-500 dark:border-slate-800 dark:text-slate-400">
                    <th className="px-3 py-2 text-start">الحساب</th>
                    <th className="px-3 py-2 text-start">الرمز</th>
                    <th className="px-3 py-2 text-end">المدين</th>
                    <th className="px-3 py-2 text-end">الدائن</th>
                    <th className="px-3 py-2 text-end">الرصيد</th>
                  </tr>
                </thead>
                <tbody>
                  {(trialData.accounts || []).map((row) => (
                    <tr
                      key={`${row.code}-${row.name}`}
                      className="border-b border-slate-100 dark:border-slate-900"
                    >
                      <td className="px-3 py-2">{row.name}</td>
                      <td className="px-3 py-2" dir="ltr">
                        {row.code}
                      </td>
                      <td className="px-3 py-2 text-end" dir="ltr">
                        {formatDecimal(row.total_debit)}
                      </td>
                      <td className="px-3 py-2 text-end" dir="ltr">
                        {formatDecimal(row.total_credit)}
                      </td>
                      <td className="px-3 py-2 text-end" dir="ltr">
                        {formatDecimal(row.balance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}
