import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import {
  CropPlans,
  CropPlanBudgetLines,
  Activities,
  Tasks,
  PlanImportLogs,
  HarvestLogs,
  CropMaterials,
} from '../api/client'
import RiskDashboard from '../components/RiskDashboard.jsx'
import { useToast } from '../components/ToastProvider'
// Unused: import { useAuth } from '../auth/AuthContext'
import BudgetImportModal from '../components/BudgetImportModal.jsx'
import { extractApiError } from '../utils/errorUtils.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

const CANONICAL_UOM_ALIASES = {
  liter: 'L',
  litre: 'L',
  l: 'L',
  'لتر': 'L',
  kg: 'kg',
  'كجم': 'kg',
  kilogram: 'kg',
  ton: 'ton',
  'طن': 'ton',
  surra: 'surra',
  hour: 'hour',
  hr: 'hour',
  'ساعة': 'hour',
  lot: 'lot',
  'مقطوعية': 'lot',
  pcs: 'pcs',
  piece: 'pcs',
  pack: 'pack',
  unit: 'Unit',
}

const normalizeBudgetUom = (value) => {
  if (value === null || value === undefined) return ''
  const trimmed = String(value).trim()
  if (!trimmed) return ''
  return CANONICAL_UOM_ALIASES[trimmed.toLowerCase()] || trimmed
}

const numberFormat = (value, currency = '') => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return String(value)
  return `${num.toLocaleString(undefined, { maximumFractionDigits: 2 })}${currency ? ` ${currency}` : ''}`
}

export default function CropPlanDetailPage() {
  const { id } = useParams()
  const toast = useToast()
  // Removed unused useAuth and canEdit here
  const [plan, setPlan] = useState(null)
  const [budgetLines, setBudgetLines] = useState([])
  const [variance, setVariance] = useState(null)
  const [financialSummary, setFinancialSummary] = useState(null)
  const [activities, setActivities] = useState([])
  const [harvestLogs, setHarvestLogs] = useState([])
  const [overrunWarning, setOverrunWarning] = useState(false)
  const [importLogs, setImportLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)
  const [savingLineId, setSavingLineId] = useState(null)
  const [tasks, setTasks] = useState([])
  const [materialRecommendations, setMaterialRecommendations] = useState([])
  const [newLine, setNewLine] = useState({
    task_id: '',
    category: 'materials',
    qty_budget: '',
    uom: '',
    rate_budget: '',
    total_budget: '',
    currency: '',
  })

  const translateUnit = (u) => {
    const term = String(u || '')
      .toLowerCase()
      .trim()
    const map = {
      surra: 'فترة',
      lot: 'مقطوعية',
      hour: 'ساعة',
      hr: 'ساعة',
      kg: 'كجم',
      ton: 'طن',
    }
    return map[term] || term
  }

  const materialUnitSuggestions = useMemo(() => {
    const values = materialRecommendations
      .map(
        (entry) =>
          entry?.recommended_unit_detail?.symbol ||
          entry?.recommended_uom ||
          entry?.item_unit?.symbol ||
          entry?.item_uom ||
          '',
      )
      .map((value) => normalizeBudgetUom(value))
      .filter(Boolean)
    return [...new Set(values)]
  }, [materialRecommendations])

  const defaultMaterialUom = materialUnitSuggestions[0] || ''

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [planRes, varianceRes, finSumRes, budgetRes, actRes, logsRes, harvestRes] =
          await Promise.all([
            CropPlans.retrieve(id),
            CropPlans.variance(id),
            CropPlans.financialSummary(id).catch(() => ({ data: null })), // [AGRI-GUARDIAN P&L]
            CropPlanBudgetLines.list({ crop_plan: id, page_size: 500 }),
            Activities.list
              ? Activities.list({ crop_plan: id, page_size: 100 })
              : Promise.resolve({ data: { results: [] } }),
            PlanImportLogs.list({ crop_plan: id, page_size: 10 }),
            HarvestLogs.list({ crop_plan: id, page_size: 100 }),
          ])

        const fetchedPlan = {
          ...planRes.data,
          currency: planRes.data?.currency || 'YER',
        }
        setPlan(fetchedPlan)
        setVariance(varianceRes.data)
        setFinancialSummary(finSumRes?.data || null)

        // Fetch tasks conditionally based on the plan's crop ID (Best Practice: Contextual Filter)
        const cropId = fetchedPlan?.crop?.id || fetchedPlan?.crop
        if (cropId && Tasks.list) {
          const tasksRes = await Tasks.list({ crop: cropId, page_size: 500 })
          const taskResults = Array.isArray(tasksRes.data?.results)
            ? tasksRes.data.results
            : tasksRes.data
          setTasks(taskResults || [])
          const materialsRes = await CropMaterials.list({
            crop_id: cropId,
            ...(fetchedPlan?.farm?.id || fetchedPlan?.farm
              ? { farm_id: fetchedPlan?.farm?.id || fetchedPlan?.farm }
              : {}),
          })
          setMaterialRecommendations(materialsRes.data?.results ?? materialsRes.data ?? [])
        } else {
          setTasks([])
          setMaterialRecommendations([])
        }

        const budgetResults = Array.isArray(budgetRes.data?.results)
          ? budgetRes.data.results
          : budgetRes.data
        setBudgetLines(budgetResults || [])

        const actResults = Array.isArray(actRes.data?.results) ? actRes.data.results : actRes.data
        setActivities(actResults || [])

        const logResults = Array.isArray(logsRes.data?.results)
          ? logsRes.data.results
          : logsRes.data
        setImportLogs(logResults || [])
        const harvestResults = Array.isArray(harvestRes.data?.results)
          ? harvestRes.data.results
          : harvestRes.data
        setHarvestLogs(harvestResults || [])
      } catch (error) {
        console.error(error)
        toast.error('فشل تحميل تفاصيل الخطة')
      } finally {
        setLoading(false)
      }
    }
    if (id) {
      load()
    }
  }, [id, toast, reloadToken])

  const budgetTotals = useMemo(() => {
    const tot = { materials: 0, labor: 0, machinery: 0, total: 0 }
    budgetLines.forEach((b) => {
      const cat = b.category || 'other'
      const amount = Number(b.total_budget || 0)
      if (cat === 'materials') tot.materials += amount
      if (cat === 'labor') tot.labor += amount
      if (cat === 'machinery') tot.machinery += amount
      tot.total += amount
    })
    return tot
  }, [budgetLines])

  const varianceCards = useMemo(() => {
    if (!variance) return []
    const currency = variance.currency || plan?.currency || ''
    const remaining = (variance.budget?.total || 0) - (variance.actual?.total || 0)
    const pct = variance.budget?.total
      ? ((variance.actual?.total || 0) / variance.budget.total) * 100
      : null
    return [
      { label: 'إجمالي الميزانية', value: variance.budget?.total, currency },
      { label: 'الإجمالي الفعلي', value: variance.actual?.total, currency },
      {
        label: 'المتبقي',
        value: remaining,
        currency,
        highlight:
          remaining < 0
            ? 'red'
            : remaining < (variance.budget?.total || 0) * 0.2
              ? 'yellow'
              : 'green',
      },
      {
        label: 'نسبة الاستهلاك',
        value: pct !== null ? `${pct.toFixed(1)}%` : '-',
        highlight: pct !== null ? (pct > 100 ? 'red' : pct > 90 ? 'yellow' : 'green') : undefined,
      },
      { label: 'الانحراف المعياري', value: variance.std_dev_total, currency },
    ]
  }, [variance, plan])

  const handleLineChange = (id, field, value, isNew = false) => {
    const applyAutoTotal = (line) => {
      const normalizedValue = field === 'uom' ? normalizeBudgetUom(value) : value
      let next = { ...line, [field]: normalizedValue }

      // Auto-set UOM based on Category selection
      if (field === 'category') {
        if (value === 'labor') next.uom = 'surra'
        else if (value === 'machinery') next.uom = 'hour'
        else if (value === 'materials') next.uom = next.uom || defaultMaterialUom
      }

      const qty = Number(next.qty_budget || 0)
      const rate = Number(next.rate_budget || 0)
      if (
        !Number.isNaN(qty) &&
        !Number.isNaN(rate) &&
        (field === 'qty_budget' || field === 'rate_budget' || field === 'category')
      ) {
        next.total_budget = qty * rate
      }
      return next
    }

    if (isNew) {
      setNewLine((prev) => applyAutoTotal(prev))
      return
    }
    setBudgetLines((prev) => prev.map((line) => (line.id === id ? applyAutoTotal(line) : line)))
  }

  const persistLine = async (line, isNew = false) => {
    setSavingLineId(line.id || 'new')
    try {
      const payload = {
        crop_plan: plan.id,
        task: line.task_id
          ? Number(line.task_id)
          : line.task && typeof line.task === 'object'
            ? Number(line.task.id)
            : line.task
              ? Number(line.task)
              : null,
        category: line.category || 'other',
        qty_budget: line.qty_budget ? Number(line.qty_budget) : null,
        uom: normalizeBudgetUom(line.uom || ''),
        rate_budget: line.rate_budget ? Number(line.rate_budget) : 0,
        total_budget: line.total_budget ? Number(line.total_budget) : 0,
        currency: line.currency || plan.currency || 'YER',
      }
      let saved
      if (isNew) {
        saved = await CropPlanBudgetLines.create(payload)
        setNewLine({
          task_id: '',
          category: 'materials',
          qty_budget: '',
          uom: '',
          rate_budget: '',
          total_budget: '',
          currency: plan.currency || 'YER',
        })
        setBudgetLines((prev) => [...prev, saved.data])
      } else {
        saved = await CropPlanBudgetLines.update(line.id, payload)
        setBudgetLines((prev) => prev.map((l) => (l.id === line.id ? saved.data : l)))
      }
      toast.success('تم حفظ سطر الميزانية')
    } catch (error) {
      const errorMsg = extractApiError(error, 'فشل حفظ سطر الميزانية')
      toast.error(errorMsg)
    } finally {
      setSavingLineId(null)
    }
  }

  const handleExportActivities = async () => {
    if (!activities.length) return
    const XLSX = await import('xlsx')
    const rows = activities.map((act) => ({
      ID: act.id,
      Date: act.log_date || act.created_at?.slice(0, 10),
      Task: act.task?.name || '---',
      Hours: act.hours || 0,
      Cost: act.cost_total || 0,
      Materials: act.cost_materials || 0,
      Labor: act.cost_labor || 0,
      Machinery: act.cost_machinery || 0,
      Notes: act.notes || '',
    }))
    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Activities')
    XLSX.writeFile(wb, `Activities_Plan_${plan.id}_${new Date().toISOString().slice(0, 10)}.xlsx`)
  }

  const sCurveData = useMemo(() => {
    if (!activities.length) return null
    const byDate = {}
    activities.forEach((act) => {
      const date = act.log_date || act.created_at?.slice(0, 10)
      const total = Number(act.cost_total || 0)
      if (!byDate[date]) byDate[date] = 0
      byDate[date] += total
    })
    const sorted = Object.entries(byDate).sort((a, b) => (a[0] > b[0] ? 1 : -1))
    let cumulative = 0
    const labels = []
    const values = []
    sorted.forEach(([date, val]) => {
      cumulative += val
      labels.push(date)
      values.push(cumulative)
    })
    const budgetTotal = variance?.budget?.total || plan?.budget_total || 0
    if (budgetTotal > 0 && cumulative > budgetTotal) {
      setOverrunWarning(true)
    } else {
      setOverrunWarning(false)
    }
    return {
      labels,
      datasets: [
        {
          label: 'الصرف التراكمي',
          data: values,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.2)',
          tension: 0.25,
        },
      ],
    }
  }, [activities, variance?.budget?.total, plan?.budget_total])

  if (loading || !plan) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-1/3 animate-pulse"></div>
        <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/4 animate-pulse"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
          ))}
        </div>
        <div className="h-64 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold dark:text-white">{plan.name}</h2>
          <p className="text-sm text-gray-500 dark:text-slate-400 flex items-center gap-1 flex-wrap">
            <span>{plan.farm?.name || ''}</span> — <span>{plan.crop?.name || ''}</span> —{' '}
            <span>{plan.season || ''}</span> —{' '}
            {plan.locations?.length > 0
              ? plan.locations.map((loc, idx) => (
                  <span
                    key={loc.id || idx}
                    className="inline-block bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-xs px-2 py-0.5 rounded-full font-medium"
                  >
                    {loc.name}
                  </span>
                ))
              : '---'}
          </p>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            من {plan.start_date || '—'} إلى {plan.end_date || '—'} | عملة: {plan.currency || '—'}
          </p>
        </div>
        <Link className="text-blue-600 text-sm" to="/crop-plans">
          عودة إلى قائمة الخطط
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {varianceCards.map((card) => (
          <div
            key={card.label}
            className={`border rounded p-3 shadow-sm ${
              card.highlight === 'red'
                ? 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-400'
                : card.highlight === 'yellow'
                  ? 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-400'
                  : 'bg-white dark:bg-slate-800 dark:border-slate-700'
            }`}
          >
            <div className="text-xs text-gray-500 dark:text-slate-400">{card.label}</div>
            <div className="text-lg font-semibold dark:text-white">
              {typeof card.value === 'string'
                ? card.value
                : numberFormat(card.value, card.currency)}
            </div>
          </div>
        ))}
      </div>

      <RiskDashboard farmId={plan.farm?.id} cropId={plan.crop?.id} />

      {financialSummary && (
        <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm mt-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg dark:text-white">
              الخلاصة الماليّة (من دفتر الأستاذ الفعلي)
            </h3>
            <span className="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 rounded-full font-medium">
              البيانات الفعليّة للقيود
            </span>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-800/50">
              <div className="text-sm text-blue-600 dark:text-blue-400 font-bold mb-1">العمالة</div>
              <div className="text-xl font-black text-blue-700 dark:text-blue-300">
                {numberFormat(financialSummary.cost_breakdown?.labor, financialSummary.currency)}
              </div>
            </div>
            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/10 rounded-xl border border-emerald-100 dark:border-emerald-800/50">
              <div className="text-sm text-emerald-600 dark:text-emerald-400 font-bold mb-1">
                المواد والمخزون
              </div>
              <div className="text-xl font-black text-emerald-700 dark:text-emerald-300">
                {numberFormat(financialSummary.cost_breakdown?.material, financialSummary.currency)}
              </div>
            </div>
            <div className="p-4 bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-100 dark:border-amber-800/50">
              <div className="text-sm text-amber-600 dark:text-amber-400 font-bold mb-1">
                الآليات والمعدات
              </div>
              <div className="text-xl font-black text-amber-700 dark:text-amber-300">
                {numberFormat(
                  financialSummary.cost_breakdown?.machinery,
                  financialSummary.currency,
                )}
              </div>
            </div>
            <div className="p-4 bg-purple-50 dark:bg-purple-900/10 rounded-xl border border-purple-100 dark:border-purple-800/50">
              <div className="text-sm text-purple-600 dark:text-purple-400 font-bold mb-1">
                نفقات أخرى / عامة
              </div>
              <div className="text-xl font-black text-purple-700 dark:text-purple-300">
                {numberFormat(
                  (financialSummary.cost_breakdown?.overhead || 0) +
                    (financialSummary.cost_breakdown?.other || 0),
                  financialSummary.currency,
                )}
              </div>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap lg:flex-nowrap items-center bg-gray-50 dark:bg-slate-700/50 p-4 rounded-xl border dark:border-slate-700">
            <div className="flex-1 flex flex-col mb-4 lg:mb-0">
              <span className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                إجمالي التكاليف المُسجّلة:
              </span>
              <span className="text-xl font-black text-rose-600 dark:text-rose-400 mt-1">
                {numberFormat(financialSummary.total_expense, financialSummary.currency)}
              </span>
            </div>
            <div className="hidden lg:block w-px h-12 bg-gray-200 dark:bg-gray-600 mx-6"></div>
            <div className="flex-1 flex flex-col mb-4 lg:mb-0">
              <span className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                إجمالي الإيرادات (المبيعات):
              </span>
              <span className="text-xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
                {numberFormat(financialSummary.total_revenue, financialSummary.currency)}
              </span>
            </div>
            <div className="hidden lg:block w-px h-12 bg-gray-200 dark:bg-gray-600 mx-6"></div>
            <div className="flex-1 flex flex-col items-start lg:items-end bg-white dark:bg-slate-800 p-3 rounded-lg border dark:border-slate-600 shadow-sm">
              <span className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                صافي الربح الفعلي:
              </span>
              <span
                className={`text-2xl font-black mt-1 ${financialSummary.net_profit >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}
              >
                {numberFormat(financialSummary.net_profit, financialSummary.currency)}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-lg dark:text-white">سجل الحصاد (التتبع)</h3>
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {harvestLogs.length} عملية حصاد
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300">
              <tr>
                <th className="text-start px-2 py-2">التاريخ</th>
                <th className="text-start px-2 py-2">الكمية</th>
                <th className="text-start px-2 py-2">الوحدة</th>
                <th className="text-start px-2 py-2">رقم التشغيلة (Batch ID)</th>
                <th className="text-start px-2 py-2">إجراءات</th>
              </tr>
            </thead>
            <tbody className="dark:text-slate-200">
              {harvestLogs.map((log) => (
                <tr key={log.id} className="border-b dark:border-slate-700 last:border-0">
                  <td className="px-2 py-2">{log.date}</td>
                  <td className="px-2 py-2 font-medium">{log.qty}</td>
                  <td className="px-2 py-2">{log.unit_name || log.unit || '-'}</td>
                  <td className="px-2 py-2 font-mono text-xs bg-gray-50 dark:bg-slate-700 text-gray-800 dark:text-slate-300 rounded px-1">
                    {log.batch_number || '---'}
                  </td>
                  <td className="px-2 py-2">
                    {log.batch_number && (
                      <button
                        onClick={() => alert(`Printing QR for Batch: ${log.batch_number}`)}
                        className="text-xs bg-gray-800 text-white px-2 py-1 rounded hover:bg-gray-700 flex items-center gap-1"
                      >
                        <span>🖨️</span> QR
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {harvestLogs.length === 0 && (
                <tr>
                  <td
                    className="px-2 py-3 text-center text-gray-500 dark:text-slate-400"
                    colSpan="5"
                  >
                    لا توجد سجلات حصاد.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {variance?.tasks && variance.tasks.length > 0 && (
        <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-lg dark:text-white">انحرافات المهام</h3>
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {variance.tasks.length} مهمة
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300">
                <tr>
                  <th className="text-start px-2 py-2">المهمة</th>
                  <th className="text-start px-2 py-2">الميزانية</th>
                  <th className="text-start px-2 py-2">الفعلية</th>
                  <th className="text-start px-2 py-2">% الاستهلاك</th>
                </tr>
              </thead>
              <tbody>
                {variance.tasks.map((taskRow) => {
                  const budgetTotal = taskRow.budget_total || 0
                  const actualTotal = taskRow.actual_total || 0
                  const pct = budgetTotal ? (actualTotal / budgetTotal) * 100 : null
                  const rowClass = !budgetTotal
                    ? ''
                    : pct > 100
                      ? 'bg-red-50 dark:bg-red-900/30'
                      : pct > 90
                        ? 'bg-amber-50 dark:bg-amber-900/30'
                        : 'bg-green-50 dark:bg-green-900/30'
                  return (
                    <tr
                      key={taskRow.task_id}
                      className={`border-b dark:border-slate-700 last:border-0 ${rowClass}`}
                    >
                      <td className="px-2 py-2 dark:text-slate-200">
                        {tasks.find((t) => t.id === taskRow.task_id)?.name ||
                          taskRow.task_id ||
                          '—'}
                      </td>
                      <td className="px-2 py-2">{numberFormat(budgetTotal, plan.currency)}</td>
                      <td className="px-2 py-2">{numberFormat(actualTotal, plan.currency)}</td>
                      <td className="px-2 py-2">{pct !== null ? `${pct.toFixed(1)}%` : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {sCurveData && (
        <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm">
          <h3 className="font-semibold mb-3 dark:text-white">منحنى الصرف التراكمي</h3>
          {overrunWarning && (
            <div className="mb-2 text-sm text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded px-3 py-2">
              تحذير: الصرف التراكمي تجاوز الميزانية المحددة للخطة.
            </div>
          )}
          <Line
            data={sCurveData}
            options={{ responsive: true, plugins: { legend: { display: true } } }}
          />
        </div>
      )}

      <div className="space-y-6">
        <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-lg dark:text-white">الأنشطة المرتبطة</h3>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 dark:text-slate-400">
                {activities.length} أنشطة
              </span>
              <button
                onClick={handleExportActivities}
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 flex items-center gap-1 transition-colors"
              >
                <span>📤</span> تصدير Excel
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300">
                <tr>
                  <th className="text-start px-2 py-2">التاريخ</th>
                  <th className="text-start px-2 py-2">المهمة</th>
                  <th className="text-start px-2 py-2">الكمية/الساعات</th>
                  <th className="text-start px-2 py-2">التكلفة</th>
                </tr>
              </thead>
              <tbody className="dark:text-slate-200">
                {activities.map((act) => (
                  <tr key={act.id} className="border-b dark:border-slate-700 last:border-0">
                    <td className="px-2 py-2">{act.log_date || act.created_at?.slice(0, 10)}</td>
                    <td className="px-2 py-2">{act.task?.name || '—'}</td>
                    <td className="px-2 py-2">{act.hours ? `${act.hours} ساعة` : '—'}</td>
                    <td className="px-2 py-2 font-medium">
                      {numberFormat(act.cost_total, plan.currency)}
                    </td>
                  </tr>
                ))}
                {activities.length === 0 && (
                  <tr>
                    <td
                      className="px-2 py-3 text-center text-gray-500 dark:text-slate-400"
                      colSpan="4"
                    >
                      لا توجد أنشطة مرتبطة بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {importLogs.length > 0 && (
            <div className="mt-4">
              <h4 className="font-semibold mb-2 text-sm dark:text-slate-200">سجل الاستيراد</h4>
              <div className="max-h-48 overflow-auto border dark:border-slate-700 rounded">
                <table className="min-w-full text-xs">
                  <thead className="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300">
                    <tr>
                      <th className="px-2 py-1 text-start">التاريخ</th>
                      <th className="px-2 py-1 text-start">الحالة</th>
                      <th className="px-2 py-1 text-start">مستورد/متجاهل</th>
                      <th className="px-2 py-1 text-start">أخطاء</th>
                      <th className="px-2 py-1 text-start">وضع المحاكاة</th>
                    </tr>
                  </thead>
                  <tbody className="dark:text-slate-200">
                    {importLogs.map((log) => (
                      <tr key={log.id} className="border-b dark:border-slate-700 last:border-0">
                        <td className="px-2 py-1">
                          {log.created_at?.slice(0, 19).replace('T', ' ')}
                        </td>
                        <td
                          className={`px-2 py-1 ${log.status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-green-700 dark:text-green-400'}`}
                        >
                          {log.status}
                        </td>
                        <td className="px-2 py-1">
                          {log.imported_count}/{log.skipped_count}
                        </td>
                        <td className="px-2 py-1">{log.errors?.length || 0}</td>
                        <td className="px-2 py-1">{log.dry_run ? 'نعم' : 'لا'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-lg dark:text-white">الميزانية التفصيلية</h3>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 dark:text-slate-400">
                {budgetLines.length} بنود
              </span>
              <button
                onClick={() => setShowImportModal(true)}
                className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 flex items-center gap-1 transition-colors"
              >
                <span>📂</span> استيراد
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300">
                <tr>
                  <th className="text-start px-2 py-2">المهمة</th>
                  <th className="text-start px-2 py-2">الفئة</th>
                  <th className="text-start px-2 py-2">الكمية</th>
                  <th className="text-start px-2 py-2">السعر</th>
                  <th className="text-start px-2 py-2">الإجمالي</th>
                  <th className="text-start px-2 py-2">الإجراءات</th>
                </tr>
              </thead>
              <tbody className="dark:text-slate-200">
                <tr className="border-b dark:border-slate-700 bg-gray-50 dark:bg-slate-700">
                  <td className="px-2 py-2 min-w-[200px]">
                    <select
                      className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                      value={newLine.task_id}
                      onChange={(e) =>
                        handleLineChange(null, 'task_id', Number(e.target.value) || '', true)
                      }
                    >
                      <option value="">اختر مهمة</option>
                      {tasks.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-2 py-2">
                    <select
                      className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                      value={newLine.category}
                      onChange={(e) => handleLineChange(null, 'category', e.target.value, true)}
                    >
                      <option value="materials">مواد</option>
                      <option value="labor">عمالة</option>
                      <option value="machinery">معدات</option>
                      <option value="other">أخرى</option>
                    </select>
                  </td>
                  <td className="px-2 py-2 min-w-[150px]">
                    <div className="flex flex-col gap-1 w-full">
                      <input
                        type="number"
                        className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                        placeholder="الكمية"
                        value={newLine.qty_budget}
                        onChange={(e) => handleLineChange(null, 'qty_budget', e.target.value, true)}
                      />
                      <div className="flex text-xs items-center gap-1 text-slate-500 bg-slate-100 dark:bg-slate-800 rounded px-2 py-1">
                        <span className="opacity-50 text-[10px]">كـ/س</span>
                        <input
                          type="text"
                          className="w-full bg-transparent outline-none dark:text-white"
                          placeholder="وحدة"
                          value={newLine.uom}
                          list="uom-options"
                          onChange={(e) => handleLineChange(null, 'uom', e.target.value, true)}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-2 py-2 min-w-[180px]">
                    <div className="flex flex-col gap-1 w-full">
                      <input
                        type="number"
                        className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                        placeholder="السعر"
                        value={newLine.rate_budget}
                        onChange={(e) =>
                          handleLineChange(null, 'rate_budget', e.target.value, true)
                        }
                      />
                      <div className="flex text-xs items-center gap-1 text-slate-500 bg-slate-100 dark:bg-slate-800 rounded px-2 py-1">
                        <span className="opacity-50 text-[10px]">عملة</span>
                        <input
                          type="text"
                          className="w-full bg-transparent outline-none dark:text-white uppercase"
                          placeholder="العملة"
                          value={newLine.currency || plan?.currency || ''}
                          onChange={(e) => handleLineChange(null, 'currency', e.target.value, true)}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-2 py-2">
                    <input
                      type="number"
                      className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                      value={newLine.total_budget}
                      onChange={(e) => handleLineChange(null, 'total_budget', e.target.value, true)}
                    />
                  </td>
                  <td className="px-2 py-2">
                    <button
                      type="button"
                      className="px-3 py-1 rounded bg-blue-600 text-white text-xs disabled:opacity-50"
                      onClick={() => persistLine(newLine, true)}
                      disabled={savingLineId === 'new'}
                    >
                      {savingLineId === 'new' ? 'جاري الحفظ...' : 'إضافة'}
                    </button>
                  </td>
                </tr>
                {budgetLines.map((line) => (
                  <tr
                    key={line.id}
                    className="border-b dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                  >
                    <td className="px-2 py-2 min-w-[200px]">
                      <select
                        className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                        value={
                          line.task_id ||
                          (line.task && typeof line.task === 'object' ? line.task.id : line.task) ||
                          ''
                        }
                        onChange={(e) =>
                          handleLineChange(line.id, 'task_id', Number(e.target.value) || '')
                        }
                      >
                        <option value="">اختر مهمة</option>
                        {tasks.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-2 py-2">
                      <select
                        className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                        value={line.category || 'other'}
                        onChange={(e) => handleLineChange(line.id, 'category', e.target.value)}
                      >
                        <option value="materials">مواد</option>
                        <option value="labor">عمالة</option>
                        <option value="machinery">معدات</option>
                        <option value="other">أخرى</option>
                      </select>
                    </td>
                    <td className="px-2 py-2 min-w-[150px]">
                      <div className="flex flex-col gap-1 w-full">
                        <input
                          type="number"
                          className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                          value={line.qty_budget ?? ''}
                          onChange={(e) => handleLineChange(line.id, 'qty_budget', e.target.value)}
                        />
                        <div className="flex text-xs items-center gap-1 text-slate-500 bg-slate-50 dark:bg-slate-800 rounded px-2 py-1 border border-dashed border-slate-300 dark:border-slate-600">
                          <input
                            type="text"
                            className="w-full bg-transparent outline-none dark:text-white text-center font-medium"
                            value={line.uom || ''}
                            list="uom-options"
                            onChange={(e) => handleLineChange(line.id, 'uom', e.target.value)}
                            placeholder="الوحدة"
                          />
                          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold whitespace-nowrap">
                            {translateUnit(line.uom)}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-2 py-2 min-w-[180px]">
                      <div className="flex flex-col gap-1 w-full">
                        <div className="flex items-center gap-1 border dark:border-slate-600 rounded px-2 py-1 bg-white dark:bg-slate-700 focus-within:ring-1 focus-within:ring-emerald-500">
                          <input
                            type="number"
                            className="w-full bg-transparent outline-none dark:text-white"
                            value={line.rate_budget ?? ''}
                            onChange={(e) =>
                              handleLineChange(line.id, 'rate_budget', e.target.value)
                            }
                          />
                          {(line.currency || plan?.currency) === plan?.currency ? (
                            <span className="text-[10px] text-slate-400 font-bold uppercase select-none">
                              {plan?.currency}
                            </span>
                          ) : null}
                        </div>
                        {(line.currency || plan?.currency) !== plan?.currency && (
                          <input
                            type="text"
                            className="border dark:border-slate-600 rounded px-2 py-1 w-full text-xs text-center bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 uppercase font-bold"
                            value={line.currency || plan?.currency || ''}
                            onChange={(e) => handleLineChange(line.id, 'currency', e.target.value)}
                            title="عملة مختلفة عن عملة الخطة"
                          />
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-2 font-medium">
                      <input
                        type="number"
                        className="border dark:border-slate-600 rounded px-2 py-1 w-full bg-white dark:bg-slate-700 dark:text-white"
                        value={line.total_budget ?? ''}
                        onChange={(e) => handleLineChange(line.id, 'total_budget', e.target.value)}
                      />
                    </td>
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        className="px-3 py-1 rounded bg-blue-600 text-white text-xs disabled:opacity-50"
                        onClick={() => persistLine(line, false)}
                        disabled={savingLineId === line.id}
                      >
                        {savingLineId === line.id ? 'جاري الحفظ...' : 'حفظ'}
                      </button>
                    </td>
                  </tr>
                ))}
                {budgetLines.length === 0 && (
                  <tr>
                    <td
                      className="px-2 py-3 text-center text-gray-500 dark:text-slate-400"
                      colSpan="6"
                    >
                      لا توجد بنود ميزانية للخطة.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <datalist id="uom-options">
              <option value="kg">كجم (kg)</option>
              <option value="L">لتر (L)</option>
              <option value="ton">طن (Ton)</option>
              <option value="lot">مقطوعية (Lot)</option>
              <option value="surra">فترة (Surra)</option>
              <option value="hour">ساعة (Hour)</option>
            </datalist>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4 pt-4 border-t border-gray-200 dark:border-slate-700">
            <div className="bg-blue-50 dark:bg-blue-900/20 px-4 py-3 rounded-xl border border-blue-100 dark:border-blue-800/50">
              <div className="text-xs text-blue-600 dark:text-blue-400 font-bold mb-1">📦 المواد</div>
              <div className="text-lg font-black text-blue-900 dark:text-blue-200">{numberFormat(budgetTotals.materials, plan.currency)}</div>
            </div>
            <div className="bg-amber-50 dark:bg-amber-900/20 px-4 py-3 rounded-xl border border-amber-100 dark:border-amber-800/50">
              <div className="text-xs text-amber-600 dark:text-amber-400 font-bold mb-1">👷 العمالة</div>
              <div className="text-lg font-black text-amber-900 dark:text-amber-200">{numberFormat(budgetTotals.labor, plan.currency)}</div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 px-4 py-3 rounded-xl border border-purple-100 dark:border-purple-800/50">
              <div className="text-xs text-purple-600 dark:text-purple-400 font-bold mb-1">🔧 المعدات</div>
              <div className="text-lg font-black text-purple-900 dark:text-purple-200">{numberFormat(budgetTotals.machinery, plan.currency)}</div>
            </div>
            <div className="bg-emerald-50 dark:bg-emerald-900/20 px-4 py-3 rounded-xl border border-emerald-100 dark:border-emerald-800/50 flex flex-col justify-center shadow-sm">
              <div className="text-xs text-emerald-600 dark:text-emerald-400 font-bold mb-1">إجمالي الميزانية</div>
              <div className="text-lg font-black text-emerald-900 dark:text-emerald-200">{numberFormat(budgetTotals.total, plan.currency)}</div>
            </div>
          </div>
        </div>
      </div>

      {showImportModal && (
        <BudgetImportModal
          planId={plan?.id}
          plan={plan}
          onClose={() => setShowImportModal(false)}
          onSuccess={() => {
            setShowImportModal(false)
            setReloadToken((prev) => prev + 1)
          }}
        />
      )}
    </div>
  )
}
