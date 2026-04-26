import { useState, useCallback, useMemo, useEffect } from 'react'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { formatMoney } from '../../utils/decimal'
import { logRuntimeError } from '../../utils/runtimeLogger'
import { BarChart2, AlertCircle, RefreshCw, Search, ChevronDown, FileText } from 'lucide-react'

const LoadingSkeleton = () => (
  <div className="animate-pulse space-y-6 max-w-7xl mx-auto">
    <div className="h-24 bg-gray-200 dark:bg-white/5 rounded-2xl" />
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-32 bg-gray-200 dark:bg-white/5 rounded-2xl" />
      ))}
    </div>
    <div className="h-96 bg-gray-200 dark:bg-white/5 rounded-xl" />
  </div>
)

export default function VarianceAnalysis() {
  const { selectedFarmId } = useFarmContext()
  const [selectedCropPlan, setSelectedCropPlan] = useState('')
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)

  // Fetch active crop plans for the farm
  const [cropPlansData, setCropPlansData] = useState(null)
  const [loadingPlans, setLoadingPlans] = useState(false)

  useEffect(() => {
    if (!selectedFarmId) return
    let cancelled = false
    setLoadingPlans(true)
    api
      .get(`/core/crop-plans/?farm=${selectedFarmId}&status=active,draft`)
      .then((res) => {
        if (!cancelled) setCropPlansData(res.data)
      })
      .catch((err) => {
        logRuntimeError('VARIANCE_CROP_PLANS_LOAD_FAILED', err, { farm_id: selectedFarmId })
        toast.error('تعذر تحميل الخطط الزراعية لهذه المزرعة.')
      })
      .finally(() => {
        if (!cancelled) setLoadingPlans(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedFarmId])

  const cropPlans = useMemo(() => cropPlansData?.results || cropPlansData || [], [cropPlansData])

  const fetchVarianceAnalysis = useCallback(async () => {
    if (!selectedCropPlan) {
      toast.error('الرجاء اختيار الخطة الزراعية')
      return
    }

    try {
      setLoadingAnalysis(true)
      const res = await api.get('/finance/ledger/material-variance-analysis/', {
        params: { crop_plan_id: selectedCropPlan },
      })
      setAnalysisData(res.data)
    } catch (err) {
      logRuntimeError('VARIANCE_ANALYSIS_FETCH_FAILED', err, {
        crop_plan_id: selectedCropPlan,
        farm_id: selectedFarmId,
      })
      toast.error(err.response?.data?.error || 'فشل في جلب تحليل الانحراف')
      setAnalysisData(null)
    } finally {
      setLoadingAnalysis(false)
    }
  }, [selectedCropPlan, selectedFarmId])

  if (!selectedFarmId) {
    return (
      <div dir="rtl" className="app-page">
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-8 text-center max-w-lg mx-auto mt-20">
          <AlertCircle className="w-16 h-16 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-amber-900 dark:text-white mb-2">اختر مزرعة</h2>
          <p className="text-slate-700 dark:text-white/60">
            يرجى اختيار مزرعة من الشريط العلوي لاستعراض تحليل الانحراف
          </p>
        </div>
      </div>
    )
  }

  const renderVarianceColor = (valueStr) => {
    if (!valueStr) return 'text-slate-500'
    const val = Number(valueStr)
    // Positive variance means Actual < Standard (Favorable -> Green)
    // Negative variance means Actual > Standard (Unfavorable -> Red)
    // Wait, Standard - Actual = Positive (Favorable), Negative (Unfavorable)
    return val > 0 ? 'text-emerald-500' : val < 0 ? 'text-rose-500' : 'text-slate-500'
  }

  return (
    <div data-testid="variance-analysis-page" dir="rtl" className="app-page space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-white flex items-center gap-3">
            <BarChart2 className="w-8 h-8 text-indigo-500" />
            تحليل الانحراف العميق للمواد
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            مقارنة الكميات المعيارية والتكاليف بالاستهلاك الفعلي مفصّلة كـ (Price Var vs Qty Var)
          </p>
        </div>
      </div>

      <div className="app-panel p-4 flex flex-col md:flex-row items-center gap-4">
        <div className="w-full md:w-1/3 relative">
          <label className="block text-xs font-bold text-slate-500 dark:text-white/50 mb-1 mx-1">
            الخطة الزراعية
          </label>
          <div className="relative">
            <select
              value={selectedCropPlan}
              onChange={(e) => setSelectedCropPlan(e.target.value)}
              className="appearance-none w-full pl-10 pr-4 py-3 bg-white/90 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-800 dark:text-white focus:border-indigo-500/50 focus:outline-none"
              disabled={loadingPlans}
            >
              <option value="">-- اختر الخطة الزراعية --</option>
              {cropPlans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name} - {plan.variety_name || ''}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute left-3 top-3.5 w-4 h-4 text-slate-400 dark:text-white/30 pointer-events-none" />
          </div>
        </div>

        <button
          onClick={fetchVarianceAnalysis}
          disabled={!selectedCropPlan || loadingAnalysis}
          className="mt-5 flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm w-full md:w-auto justify-center"
        >
          {loadingAnalysis ? (
            <RefreshCw className="w-5 h-5 animate-spin" />
          ) : (
            <Search className="w-5 h-5" />
          )}
          تحليل الخطة
        </button>
      </div>

      {loadingAnalysis && <LoadingSkeleton />}

      {!loadingAnalysis && analysisData && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-3xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 to-transparent p-6">
              <p className="text-indigo-500/80 text-sm font-bold mb-1">
                إجمالي انحراف الكمية (Qty Var)
              </p>
              <h2
                className={`text-3xl font-black ${renderVarianceColor(analysisData.overall_summary.total_quantity_variance)}`}
                dir="ltr"
              >
                {formatMoney(analysisData.overall_summary.total_quantity_variance)}
              </h2>
            </div>
            <div className="rounded-3xl border border-blue-500/30 bg-gradient-to-br from-blue-500/10 to-transparent p-6">
              <p className="text-blue-500/80 text-sm font-bold mb-1">
                إجمالي انحراف السعر (Price Var)
              </p>
              <h2
                className={`text-3xl font-black ${renderVarianceColor(analysisData.overall_summary.total_price_variance)}`}
                dir="ltr"
              >
                {formatMoney(analysisData.overall_summary.total_price_variance)}
              </h2>
            </div>
            <div className="rounded-3xl border border-purple-500/30 bg-gradient-to-br from-purple-500/10 to-transparent p-6">
              <p className="text-purple-500/80 text-sm font-bold mb-1">
                صافي الانحراف للمواد (Net Var)
              </p>
              <h2
                className={`text-3xl font-black ${renderVarianceColor(analysisData.overall_summary.net_variance)}`}
                dir="ltr"
              >
                {formatMoney(analysisData.overall_summary.net_variance)}
              </h2>
            </div>
          </div>

          <div className="app-panel overflow-hidden">
            <div className="p-4 border-b border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/5">
              <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-500" />
                تفاصيل انحراف المواد المباشرة
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-end">
                <thead className="bg-slate-100/50 dark:bg-white/5 text-slate-500 dark:text-white/40 font-bold">
                  <tr>
                    <th className="px-6 py-4">المادة (الصنف)</th>
                    <th className="px-6 py-4">الكمية المعيارية (SQ)</th>
                    <th className="px-6 py-4">الكمية الفعلية (AQ)</th>
                    <th className="px-6 py-4">السعر المعياري (SP)</th>
                    <th className="px-6 py-4">السعر الفعلي (AP)</th>
                    <th className="px-6 py-4">انحراف الكمية</th>
                    <th className="px-6 py-4">انحراف السعر</th>
                    <th className="px-6 py-4">الإجمالي</th>
                  </tr>
                </thead>
                <tbody>
                  {analysisData.detailed_materials.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="py-12 text-center text-slate-500">
                        لا توجد داتا مواد مسجلة.
                      </td>
                    </tr>
                  ) : (
                    analysisData.detailed_materials.map((mat, idx) => (
                      <tr
                        key={idx}
                        className="border-t border-slate-200/50 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5"
                      >
                        <td className="px-6 py-4 font-bold text-slate-800 dark:text-white">
                          {mat.item_name}
                        </td>
                        <td className="px-6 py-4 text-emerald-600 dark:text-emerald-400">
                          {Number(mat.standard_qty)}
                        </td>
                        <td className="px-6 py-4 text-rose-600 dark:text-rose-400">
                          {Number(mat.actual_qty)}
                        </td>
                        <td className="px-6 py-4 text-slate-600 dark:text-slate-300" dir="ltr">
                          {formatMoney(mat.standard_cost_per_unit)}
                        </td>
                        <td className="px-6 py-4 text-slate-600 dark:text-slate-300" dir="ltr">
                          {formatMoney(mat.actual_cost_per_unit)}
                        </td>
                        <td
                          className={`px-6 py-4 font-bold ${renderVarianceColor(mat.quantity_variance)}`}
                          dir="ltr"
                        >
                          {formatMoney(mat.quantity_variance)}
                        </td>
                        <td
                          className={`px-6 py-4 font-bold ${renderVarianceColor(mat.price_variance)}`}
                          dir="ltr"
                        >
                          {formatMoney(mat.price_variance)}
                        </td>
                        <td
                          className={`px-6 py-4 font-bold ${renderVarianceColor(mat.total_variance)}`}
                          dir="ltr"
                        >
                          {formatMoney(mat.total_variance)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
// Note: FileText import is missing, so fixing it.
