import { useEffect, useMemo, useState, useCallback } from 'react'
// Unused: import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import {
  CropPlans,
  CropPlanBudgetLines,
  Activities,
  Tasks,
  Sales,
  Locations,
} from '../api/client'
import { useToast } from '../components/ToastProvider'
import CreatePlanWizard from '../components/CreatePlanWizard'
import BudgetImportModal from '../components/BudgetImportModal'
import CropPlanStructureImportModal from '../components/CropPlanStructureImportModal'
import MasterPlanImportModal from '../components/MasterPlanImportModal'

import SaleModal from '../components/SaleModal.jsx'
import PlanTimeline from '../components/PlanTimeline.jsx'
import { toDecimal } from '../utils/decimal'
// Unused: import ErrorState from '../components/ui/ErrorState.jsx'
import LoadingSkeleton from '../components/ui/LoadingSkeleton.jsx'
import { usePageFarmFilter } from '../hooks/usePageFarmFilter'
import PageFarmFilter from '../components/filters/PageFarmFilter'

const numberFormat = (value) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return String(value)
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

export default function CropPlansPage() {
  const toast = useToast()

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

  const [rawPlans, setRawPlans] = useState([])
  const [selectedPlanId, setSelectedPlanId] = useState(null)
  const {
    farmId: selectedFarmId,
    setFarmId: setSelectedFarmId,
    farmOptions: farms,
    canUseAll,
  } = usePageFarmFilter({
    storageKey: 'page_farm.crop_plans',
    allowAllForAdmin: true,
    defaultPolicy: 'first',
  })
  const effectiveFarmId = selectedFarmId === 'all' ? '' : selectedFarmId

  const [variance, setVariance] = useState(null)
  const [budgetLines, setBudgetLines] = useState([])
  const [planActivities, setPlanActivities] = useState([])
  const [planSales, setPlanSales] = useState([])
  const [tasks, setTasks] = useState([])

  const [selectedActivityIds, setSelectedActivityIds] = useState([])
  const [selectedTaskIds, setSelectedTaskIds] = useState([])

  const [loading, setLoading] = useState(false)
  const [varianceLoading, setVarianceLoading] = useState(false)
  const [approving, setApproving] = useState(false)

  const [showBudgetImportModal, setShowBudgetImportModal] = useState(false)
  const [showStructureImportModal, setShowStructureImportModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showMasterImportModal, setShowMasterImportModal] = useState(false)

  const [showSaleModal, setShowSaleModal] = useState(false)
  const [viewMode, setViewMode] = useState('list') // list | timeline
  const [allLocations, setAllLocations] = useState([])

  // Load locations when farm changes
  useEffect(() => {
    if (!effectiveFarmId) {
      setAllLocations([])
      return
    }
    const loadLocs = async () => {
      try {
        const res = await Locations.list({ farm_id: effectiveFarmId, page_size: 200 })
        setAllLocations(Array.isArray(res.data?.results) ? res.data.results : res.data || [])
      } catch (e) {
        console.error(e)
      }
    }
    loadLocs()
  }, [effectiveFarmId])

  // Enrich plans reactively when lookup data becomes available
  const plans = useMemo(() => {
    if (!rawPlans.length) return []
    return rawPlans.map((plan) => {
      const farmId = typeof plan.farm === 'object' ? plan.farm?.id : plan.farm
      // Fallback for transition: if the backend sends 'locations' array of IDs
      const locIds = Array.isArray(plan.locations) ? plan.locations : []
      const cropId = typeof plan.crop === 'object' ? plan.crop?.id : plan.crop

      const farmObj = farms.find((f) => String(f.id) === String(farmId))
      const locObjs = locIds
        .map((id) => allLocations.find((l) => String(l.id) === String(id)))
        .filter(Boolean)
      return {
        ...plan,
        currency: plan.currency || 'YER',
        farm:
          typeof plan.farm === 'object' && plan.farm?.name
            ? plan.farm
            : farmObj
              ? { id: farmId, name: farmObj.name }
              : { id: farmId },
        locations: locObjs.length > 0 ? locObjs : locIds.map((id) => ({ id })),
        crop:
          typeof plan.crop === 'object' && plan.crop?.name
            ? plan.crop
            : { id: cropId },
      }
    })
  }, [rawPlans, farms, allLocations])

  const loadPlans = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page_size: 100 }
      if (effectiveFarmId) {
        params.farm = effectiveFarmId
      } else if (!canUseAll) {
        setRawPlans([])
        setLoading(false)
        return
      }
      const res = await CropPlans.list(params)
      const results = Array.isArray(res.data?.results) ? res.data.results : res.data || []
      setRawPlans(results)
    } catch (error) {
      console.error(error)
      toast.error('فشل تحميل الخطط')
    } finally {
      setLoading(false)
    }
  }, [toast, effectiveFarmId, canUseAll])

  useEffect(() => {
    loadPlans()
  }, [loadPlans])

  // loadDetails
  useEffect(() => {
    const planId = selectedPlanId
    if (!planId) return

    const loadDetails = async () => {
      setVarianceLoading(true)
      try {
        const [varRes, linesRes, actsRes, salesRes] = await Promise.all([
          CropPlans.variance(planId),
          CropPlanBudgetLines.list({ crop_plan: planId, page_size: 500 }),
          Activities.list({ crop_plan: planId, page_size: 200 }),
          Sales.list({ crop_plan: planId, page_size: 200 }),
        ])
        setVariance(varRes.data)
        const lines = Array.isArray(linesRes.data?.results) ? linesRes.data.results : linesRes.data
        setBudgetLines(lines || [])
        const acts = Array.isArray(actsRes.data?.results) ? actsRes.data.results : actsRes.data
        setPlanActivities(acts || [])
        setSelectedActivityIds((acts || []).map((a) => a.id))

        const sales = Array.isArray(salesRes.data?.results) ? salesRes.data.results : salesRes.data
        setPlanSales(sales || [])

        const planObj = (plans || []).find((p) => p.id === planId)
        const cropId = planObj?.crop?.id
        if (cropId) {
          const tasksRes = await Tasks.list({ crop: cropId, page_size: 500 })
          const taskResults = Array.isArray(tasksRes.data?.results)
            ? tasksRes.data.results
            : tasksRes.data
          setTasks(taskResults || [])
          setSelectedTaskIds((taskResults || []).map((t) => t.id))
        }
      } catch (error) {
        console.error(error)
        toast.error('فشل تحميل بيانات الخطة')
      } finally {
        setVarianceLoading(false)
      }
    }

    loadDetails()
  }, [selectedPlanId, plans, toast])

  const selectedPlan = useMemo(
    () => plans.find((p) => p.id === selectedPlanId),
    [plans, selectedPlanId],
  )

  const approvePlan = async () => {
    if (!selectedPlan) return
    setApproving(true)
    try {
      await CropPlans.approve(selectedPlan.id)
      toast.success('تم اعتماد الخطة')
      const refreshed = await CropPlans.retrieve(selectedPlan.id)
      setRawPlans((prev) => prev.map((p) => (p.id === selectedPlan.id ? refreshed.data : p)))
    } catch (error) {
      console.error(error)
      toast.error('فشل اعتماد الخطة')
    } finally {
      setApproving(false)
    }
  }

  const budgetCards = useMemo(() => {
    const v = variance
    if (!v) return []
    const currency = v.currency || selectedPlan?.currency || ''
    const remaining = (v.budget?.total || 0) - (v.actual?.total || 0)
    const pct = v.budget?.total ? ((v.actual?.total || 0) / v.budget.total) * 100 : null
    const unitCost = selectedPlan?.cost_per_unit
      ? `${numberFormat(selectedPlan.cost_per_unit)} ${currency}/${selectedPlan.yield_unit || 'وحدة'}`
      : '-'

    // [AGRI-GUARDIAN §1.II] Use decimal utilities for financial precision
    const totalSales = planSales.reduce((sum, sale) => sum + toDecimal(sale.total_amount), 0)
    const profit = totalSales - (v.actual?.total || 0)

    return [
      { label: 'إجمالي الميزانية', value: v.budget?.total, currency },
      { label: 'إجمالي المنصرف', value: v.actual?.total, currency },
      { label: 'المتبقي', value: remaining, currency },
      { label: 'نسبة الصرف', value: pct !== null ? `${pct.toFixed(1)}%` : '-' },
      { label: 'تكلفة الوحدة (فعلي)', value: unitCost },
      { label: 'المبيعات (الإيرادات)', value: totalSales, currency },
      {
        label: 'الربح / الخسارة',
        value: profit,
        currency,
        color: profit >= 0 ? 'text-green-600' : 'text-red-600',
      },
    ]
  }, [variance, selectedPlan, planSales])

  const budgetTotals = useMemo(() => {
    const totals = { materials: 0, labor: 0, machinery: 0, other: 0, grand: 0 }
    budgetLines.forEach((l) => {
      const amt = Number(l.total_budget) || 0
      const cat = l.category || 'other'
      if (totals[cat] !== undefined) {
        totals[cat] += amt
      } else {
        totals.other += amt
      }
      totals.grand += amt
    })
    return totals
  }, [budgetLines])

  const categoryBadges = {
    materials: { label: '📦 مواد', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800' },
    labor: { label: '👷 عمالة', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 border border-amber-200 dark:border-amber-800' },
    machinery: { label: '🔧 معدات', cls: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-400 border border-purple-200 dark:border-purple-800' },
    other: { label: '📋 أخرى', cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600' },
  }

  return (
    <>
      {showSaleModal && (
        <SaleModal
          planId={selectedPlanId}
          onClose={() => setShowSaleModal(false)}
          onSuccess={async () => {
            // [AGRI-GUARDIAN 102] State refresh بدل window.location.reload()
            setShowSaleModal(false)
            await loadPlans()
            // Force re-trigger loadDetails by toggling plan ID
            setSelectedPlanId((prev) => {
              const id = prev
              setSelectedPlanId(null)
              setTimeout(() => setSelectedPlanId(id), 50)
              return prev
            })
            toast.success('تم تسجيل البيع بنجاح')
          }}
        />
      )}

      {showCreateModal && (
        <CreatePlanWizard
          onClose={() => setShowCreateModal(false)}
          onSuccess={async (newPlan) => {
            setShowCreateModal(false)
            await loadPlans()
            if (newPlan?.id) {
              setSelectedPlanId(newPlan.id)
              toast.success(`تم إنشاء الخطة: ${newPlan.name}`)
            }
          }}
        />
      )}

      {showMasterImportModal && (
        <MasterPlanImportModal
          farmId={effectiveFarmId}
          onClose={() => setShowMasterImportModal(false)}
          onSuccess={async () => {
            setShowMasterImportModal(false)
            toast.success('تمت جدولة الخطط بنجاح')
            // [AGRI-GUARDIAN 102] State refresh بدل window.location.reload()
            await loadPlans()
          }}
        />
      )}

      {showStructureImportModal && (
        <CropPlanStructureImportModal
          planId={selectedPlanId}
          plan={selectedPlan}
          onClose={() => setShowStructureImportModal(false)}
          onSuccess={async () => {
            setShowStructureImportModal(false)
            toast.success('تم تحديث الهيكل التشغيلي للخطة بنجاح')
            await loadPlans()
          }}
        />
      )}

      {showBudgetImportModal && (
        <BudgetImportModal
          planId={selectedPlanId}
          plan={selectedPlan}
          onClose={() => {
            setShowBudgetImportModal(false)
          }}
          onSuccess={async () => {
            setShowBudgetImportModal(false)
            toast.success('تم تحديث البيانات بنجاح')
            await loadPlans()
          }}
        />
      )}

      <div dir="rtl" className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-emerald-600 dark:from-emerald-400 to-amber-500 dark:to-amber-200 bg-clip-text text-transparent">
              خطط المحاصيل والميزانية
            </h1>
            <p className="text-gray-500 dark:text-zinc-500 font-medium mt-1">
              إدارة الخطط، الميزانية، المبيعات
            </p>
          </div>
          <div className="flex gap-3 items-center">
            <div className="bg-gray-100 dark:bg-white/5 p-1 rounded-xl flex border border-gray-200 dark:border-white/10">
              <button
                onClick={() => setViewMode('list')}
                className={`px-4 py-2 text-sm rounded-lg transition-all ${viewMode === 'list' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 font-bold' : 'text-gray-500 dark:text-white/50 hover:text-gray-700 dark:hover:text-white/70'}`}
              >
                قائمة
              </button>
              <button
                onClick={() => setViewMode('timeline')}
                className={`px-4 py-2 text-sm rounded-lg transition-all ${viewMode === 'timeline' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 font-bold' : 'text-gray-500 dark:text-white/50 hover:text-gray-700 dark:hover:text-white/70'}`}
                aria-label="عرض الجدول الزمني"
              >
                جدول زمني
              </button>
            </div>
            <button
              type="button"
              className="px-4 py-2.5 rounded-xl bg-purple-500/20 text-purple-400 text-sm font-bold hover:bg-purple-500/30 border border-purple-500/30 transition-colors flex items-center gap-2"
              onClick={() => {
                if (!selectedPlanId) return toast.warning('اختر خطة أولاً')
                setShowSaleModal(true)
              }}
              aria-label="تسجيل عملية بيع جديدة"
            >
              <span className="text-lg">💰</span>
              تسجيل بيع
            </button>
            <button
              type="button"
              className="px-4 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-bold hover:bg-emerald-500 shadow-lg shadow-emerald-500/20 transition-colors flex items-center gap-2"
              onClick={() => setShowCreateModal(true)}
              aria-label="إنشاء خطة زراعية جديدة"
            >
              <span className="text-lg">+</span>
              خطة جديدة
            </button>
            <button
              type="button"
              className="px-3 py-2 rounded bg-indigo-600 text-white text-sm hover:bg-indigo-700 flex items-center gap-1"
              onClick={() => setShowMasterImportModal(true)}
              title="استيراد جدول زمني كامل من Excel"
              aria-label="استيراد جدول زمني من ملف إكسل"
            >
              <span className="text-lg">📑</span>
              استيراد جدولة
            </button>
            <div className="h-6 w-px bg-gray-300 mx-2"></div>
            <select
              className="border rounded px-3 py-2 text-sm"
              value={selectedPlanId || ''}
              onChange={(e) => setSelectedPlanId(Number(e.target.value) || null)}
              disabled={loading}
              aria-label="اختر الخطة الزراعية"
            >
              {!selectedPlanId && <option value="">اختر خطة</option>}
              {plans.map((plan) => (
                <option key={plan.id} value={plan.id} data-testid={`crop-plan-${plan.id}`}>
                  {plan.name} — {plan.farm?.name || ''} ({plan.currency || 'YER'})
                </option>
              ))}
            </select>
            {!loading && plans.length === 0 && (
              <span data-testid="empty-state" className="text-sm text-gray-500 dark:text-white/70">
                لا توجد خطط زراعية متاحة للمزرعة المحددة.
              </span>
            )}
            <button
              type="button"
              className="px-3 py-2 rounded bg-blue-600 text-white text-sm disabled:opacity-50"
              onClick={approvePlan}
              disabled={!selectedPlan || approving}
              aria-label="اعتماد الخطة المختارة"
            >
              {approving ? 'جاري الاعتماد...' : 'اعتماد الخطة'}
            </button>
          </div>
        </div>

        {viewMode === 'timeline' ? (
          <PlanTimeline plans={plans} />
        ) : (
          <>
            <div className="flex flex-wrap gap-3 items-center">
              <PageFarmFilter
                value={selectedFarmId}
                onChange={(value) => {
                  setSelectedFarmId(value)
                }}
                options={farms}
                canUseAll={canUseAll}
                testId="crop-plans-farm-filter"
                className="min-w-[220px]"
              />

              <button
                type="button"
                className="px-3 py-2 rounded bg-indigo-600 text-white text-sm disabled:opacity-50 hover:bg-indigo-700"
                onClick={() => {
                  if (!effectiveFarmId) {
                    toast.warning('يرجى تحديد المزرعة أولًا قبل استيراد الخطة الرئيسية')
                    return
                  }
                  setShowMasterImportModal(true)
                }}
                disabled={!effectiveFarmId}
                aria-label="استيراد الخطة الرئيسية"
              >
                استيراد الخطة الرئيسية
              </button>

              <button
                type="button"
                className="px-3 py-2 rounded bg-sky-600 text-white text-sm disabled:opacity-50 hover:bg-sky-700 flex items-center gap-2"
                onClick={() => {
                  if (!selectedPlanId) {
                    toast.warning('يرجى اختيار خطة زراعية أولًا لتفعيل استيراد الهيكل التشغيلي')
                    return
                  }
                  setShowStructureImportModal(true)
                }}
                title={!selectedPlanId ? 'اختر خطة لتفعيل الاستيراد' : 'استيراد الهيكل التشغيلي من Excel'}
                aria-label="استيراد الهيكل التشغيلي للخطة من ملف إكسل"
              >
                <span className="text-lg">📥</span>
                استيراد الهيكل التشغيلي
              </button>

              <button
                type="button"
                className="px-3 py-2 rounded bg-emerald-600 text-white text-sm disabled:opacity-50 hover:bg-emerald-700 flex items-center gap-2"
                onClick={() => {
                  if (!selectedPlanId) {
                    toast.warning('يرجى اختيار خطة زراعية أولًا لتفعيل استيراد الميزانية')
                    return
                  }
                  setShowBudgetImportModal(true)
                }}
                title={!selectedPlanId ? 'اختر خطة لتفعيل الاستيراد' : 'استيراد الميزانية من Excel'}
                aria-label="استيراد بيانات الميزانية من ملف إكسل"
              >
                <span className="text-lg">💼</span>
                استيراد الميزانية
              </button>
            </div>

            {varianceLoading || loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <LoadingSkeleton key={i} className="h-24 rounded-2xl" />
                ))}
              </div>
            ) : selectedPlan ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600 dark:text-white/60">
                    <div>المزرعة: {selectedPlan.farm?.name || '---'}</div>
                    <div>
                      الموقع:{' '}
                      <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                        {selectedPlan.locations?.length > 0
                          ? selectedPlan.locations.map((l) => l.name).join('، ')
                          : '---'}
                      </span>
                    </div>
                    <div>المحصول: {selectedPlan.crop?.name || '---'}</div>
                    <div>العملة: {selectedPlan.currency || '---'}</div>
                  </div>
                  <Link
                    to={`/crop-plans/${selectedPlan.id}`}
                    className="text-emerald-600 dark:text-emerald-400 text-sm hover:text-emerald-500 dark:hover:text-emerald-300 transition-colors"
                    aria-label={`عرض تفاصيل الخطة ${selectedPlan.name}`}
                  >
                    عرض تفاصيل الخطة
                  </Link>
                </div>

                {/* [AGRI-GUARDIAN 102] Budget=0 Alert */}
                {variance &&
                  (variance.budget?.total === 0 || variance.budget?.total === null) &&
                  budgetLines.length === 0 && (
                    <div className="rounded-xl border border-amber-300 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 backdrop-blur-xl p-4 flex items-center gap-3">
                      <span className="text-2xl">⚠️</span>
                      <div>
                        <div className="text-amber-700 dark:text-amber-300 font-bold text-sm">
                          لم تُحدد ميزانية لهذه الخطة بعد
                        </div>
                        <div className="text-amber-600/70 dark:text-amber-400/60 text-xs mt-1">
                          الانحرافات لن تُحسب بدقة. يُرجى تعيين الميزانية من صفحة التفاصيل.
                        </div>
                      </div>
                      <Link
                        to={`/crop-plans/${selectedPlan.id}`}
                        className="mr-auto px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 text-xs font-bold hover:bg-amber-200 dark:hover:bg-amber-500/30 border border-amber-300 dark:border-amber-500/30 transition-colors whitespace-nowrap"
                      >
                        تعيين الميزانية →
                      </Link>
                    </div>
                  )}

                <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                  {budgetCards.map((card) => (
                    <div
                      key={card.label}
                      className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-800/80 shadow-sm dark:shadow-none backdrop-blur-xl p-4 hover:border-emerald-400 dark:hover:border-emerald-500/30 transition-all"
                    >
                      <div className="text-[10px] uppercase font-bold text-gray-400 dark:text-white/40 tracking-wider">
                        {card.label}
                      </div>
                      <div
                        className={`text-xl font-black mt-2 ${card.color || 'text-gray-800 dark:text-white'}`}
                      >
                        {typeof card.value === 'string'
                          ? card.value
                          : `${numberFormat(card.value)} ${card.currency || ''}`}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-zinc-900/80 shadow-sm dark:shadow-none backdrop-blur-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-bold text-sm text-gray-800 dark:text-white">
                      اختر الأنشطة لتضمينها في القالب
                    </h3>
                    <div className="flex gap-2 text-xs">
                      <button
                        type="button"
                        className="px-3 py-1.5 rounded-lg border border-gray-200 dark:border-white/10 text-gray-500 dark:text-white/60 hover:bg-gray-100 dark:hover:bg-white/5"
                        onClick={() => setSelectedActivityIds(planActivities.map((a) => a.id))}
                        aria-label="تحديد جميع الأنشطة"
                      >
                        تحديد الكل
                      </button>
                      <button
                        type="button"
                        className="px-3 py-1.5 rounded-lg border border-gray-200 dark:border-white/10 text-gray-500 dark:text-white/60 hover:bg-gray-100 dark:hover:bg-white/5"
                        onClick={() => setSelectedActivityIds([])}
                        aria-label="إلغاء تحديد جميع الأنشطة"
                      >
                        إلغاء التحديد
                      </button>
                    </div>
                  </div>
                  {planActivities.length === 0 ? (
                    <div className="text-sm text-gray-400 dark:text-white/30">
                      لا توجد أنشطة مرتبطة بالخطة حالياً.
                    </div>
                  ) : (
                    <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {planActivities.map((act) => (
                        <label
                          key={act.id}
                          className="flex items-center gap-2 border border-gray-200 dark:border-white/10 rounded-xl px-3 py-2 text-sm text-gray-600 dark:text-white/70 hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={selectedActivityIds.includes(act.id)}
                            onChange={(e) => {
                              const checked = e.target.checked
                              setSelectedActivityIds((prev) =>
                                checked ? [...prev, act.id] : prev.filter((id) => id !== act.id),
                              )
                            }}
                            className="accent-emerald-500"
                          />
                          <span className="flex-1">
                            {act.task?.name || 'نشاط'} —{' '}
                            {act.log_date || act.created_at?.slice(0, 10) || '---'}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-zinc-900/80 shadow-sm dark:shadow-none backdrop-blur-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-bold text-sm text-gray-800 dark:text-white">
                      اختر المهام لتضمينها في القالب
                    </h3>
                    <div className="flex gap-2 text-xs">
                      <button
                        type="button"
                        className="px-3 py-1.5 rounded-lg border border-gray-200 dark:border-white/10 text-gray-500 dark:text-white/60 hover:bg-gray-100 dark:hover:bg-white/5"
                        onClick={() => setSelectedTaskIds(tasks.map((t) => t.id))}
                        aria-label="تحديد جميع المهام"
                      >
                        تحديد الكل
                      </button>
                      <button
                        type="button"
                        className="px-3 py-1.5 rounded-lg border border-gray-200 dark:border-white/10 text-gray-500 dark:text-white/60 hover:bg-gray-100 dark:hover:bg-white/5"
                        onClick={() => setSelectedTaskIds([])}
                        aria-label="إلغاء تحديد جميع المهام"
                      >
                        إلغاء التحديد
                      </button>
                    </div>
                  </div>
                  {tasks.length === 0 ? (
                    <div className="text-sm text-gray-400 dark:text-white/30">
                      لا توجد مهام للمحصول حالياً.
                    </div>
                  ) : (
                    <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {tasks.map((task) => (
                        <label
                          key={task.id}
                          className="flex items-center gap-2 border border-gray-200 dark:border-white/10 rounded-xl px-3 py-2 text-sm text-gray-600 dark:text-white/70 hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={selectedTaskIds.includes(task.id)}
                            onChange={(e) => {
                              const checked = e.target.checked
                              setSelectedTaskIds((prev) =>
                                checked ? [...prev, task.id] : prev.filter((id) => id !== task.id),
                              )
                            }}
                            className="accent-emerald-500"
                          />
                          <span className="flex-1">{task.name || 'مهمة'}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-6">
                  <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-zinc-900/80 shadow-sm dark:shadow-none backdrop-blur-xl p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-bold text-lg text-gray-800 dark:text-white">
                        بنود الميزانية
                      </h3>
                      <span className="text-xs text-gray-400 dark:text-white/40">
                        {budgetLines.length} بند
                      </span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 dark:bg-white/5 text-gray-500 dark:text-white/40 font-bold">
                          <tr>
                            <th className="text-end px-3 py-2">المهمة</th>
                            <th className="text-end px-3 py-2">الفئة</th>
                            <th className="text-end px-3 py-2">الكمية</th>
                            <th className="text-end px-3 py-2">الوحدة</th>
                            <th className="text-end px-3 py-2">السعر</th>
                            <th className="text-end px-3 py-2">الإجمالي</th>
                          </tr>
                        </thead>
                        <tbody>
                          {budgetLines.map((line) => (
                            <tr
                              key={line.id}
                              className="border-t border-gray-100 dark:border-white/5 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                            >
                              <td
                                className="px-3 py-2 text-gray-700 dark:text-white/70 truncate max-w-[150px]"
                                title={
                                  line.task_name ||
                                  (typeof line.task === 'object' && line.task?.name
                                    ? line.task.name
                                    : tasks.find(
                                      (t) =>
                                        String(t.id) ===
                                        String(
                                          typeof line.task === 'object'
                                            ? line.task?.id
                                            : line.task,
                                        ),
                                    )?.name ||
                                    line.task?.id ||
                                    line.task ||
                                    '---')
                                }
                              >
                                {line.task_name ||
                                  (typeof line.task === 'object' && line.task?.name
                                    ? line.task.name
                                    : tasks.find(
                                      (t) =>
                                        String(t.id) ===
                                        String(
                                          typeof line.task === 'object'
                                            ? line.task?.id
                                            : line.task,
                                        ),
                                    )?.name ||
                                    line.task?.id ||
                                    line.task ||
                                    '---')}
                              </td>
                              <td className="px-3 py-2 text-gray-500 dark:text-white/50">
                                {(() => {
                                  const c = line.category || 'other'
                                  const badge = categoryBadges[c] || categoryBadges.other
                                  return (
                                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap shadow-sm ${badge.cls}`}>
                                      {badge.label}
                                    </span>
                                  )
                                })()}
                              </td>
                              <td className="px-3 py-2 text-gray-600 dark:text-white/60">
                                {numberFormat(line.qty_budget)}
                              </td>
                              <td className="px-3 py-2 text-gray-600 dark:text-white/60">
                                {translateUnit(line.uom)}
                              </td>
                              <td className="px-3 py-2 text-gray-600 dark:text-white/60">
                                {numberFormat(line.rate_budget)} {line.currency}
                              </td>
                              <td className="px-3 py-2 font-bold text-emerald-600 dark:text-emerald-400">
                                {numberFormat(line.total_budget)} {line.currency}
                              </td>
                            </tr>
                          ))}
                          {budgetLines.length === 0 && (
                            <tr>
                              <td
                                className="px-3 py-6 text-center text-gray-400 dark:text-white/30"
                                colSpan="6"
                              >
                                لا توجد بنود ميزانية بعد.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-gray-200 dark:border-white/10">
                      <div className="bg-blue-50 dark:bg-blue-900/20 px-4 py-3 rounded-xl border border-blue-100 dark:border-blue-800">
                        <div className="text-xs text-blue-600 dark:text-blue-400 font-bold mb-1">📦 المواد</div>
                        <div className="text-lg font-black text-blue-900 dark:text-blue-200">{numberFormat(budgetTotals.materials)}</div>
                      </div>
                      <div className="bg-amber-50 dark:bg-amber-900/20 px-4 py-3 rounded-xl border border-amber-100 dark:border-amber-800">
                        <div className="text-xs text-amber-600 dark:text-amber-400 font-bold mb-1">👷 العمالة</div>
                        <div className="text-lg font-black text-amber-900 dark:text-amber-200">{numberFormat(budgetTotals.labor)}</div>
                      </div>
                      <div className="bg-purple-50 dark:bg-purple-900/20 px-4 py-3 rounded-xl border border-purple-100 dark:border-purple-800">
                        <div className="text-xs text-purple-600 dark:text-purple-400 font-bold mb-1">🔧 المعدات</div>
                        <div className="text-lg font-black text-purple-900 dark:text-purple-200">{numberFormat(budgetTotals.machinery)}</div>
                      </div>
                      <div className="bg-emerald-50 dark:bg-emerald-900/20 px-4 py-3 rounded-xl border border-emerald-100 dark:border-emerald-800 flex flex-col justify-center shadow-sm">
                        <div className="text-xs text-emerald-600 dark:text-emerald-400 font-bold mb-1">إجمالي الميزانية</div>
                        <div className="text-lg font-black text-emerald-900 dark:text-emerald-200">{numberFormat(budgetTotals.grand)} {selectedPlan?.currency || 'YER'}</div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-zinc-900/80 shadow-sm dark:shadow-none backdrop-blur-xl p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-bold text-lg text-gray-800 dark:text-white">
                        انحراف التكاليف
                      </h3>
                      <span className="text-xs text-gray-400 dark:text-white/40">
                        {variance?.tasks?.length || 0} مهمة
                      </span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 dark:bg-white/5 text-gray-500 dark:text-white/40 font-bold">
                          <tr>
                            <th className="text-end px-3 py-2">المهمة</th>
                            <th className="text-end px-3 py-2">الميزانية</th>
                            <th className="text-end px-3 py-2">الفعلي</th>
                            <th className="text-end px-3 py-2">% الاستهلاك</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(variance?.tasks || []).map((taskRow) => {
                            const budgetTotal = taskRow.budget_total || 0
                            const actualTotal = taskRow.actual_total || 0
                            const pct = budgetTotal
                              ? ((actualTotal / budgetTotal) * 100).toFixed(1)
                              : '---'
                            const isOver = budgetTotal && actualTotal > budgetTotal
                            return (
                              <tr
                                key={taskRow.task_id}
                                className="border-t border-gray-100 dark:border-white/5 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                              >
                                <td
                                  className="px-3 py-2 text-gray-700 dark:text-white/70 truncate max-w-[150px]"
                                  title={
                                    taskRow.task_name ||
                                    tasks.find((t) => String(t.id) === String(taskRow.task_id))
                                      ?.name ||
                                    taskRow.task_id ||
                                    '---'
                                  }
                                >
                                  {taskRow.task_name ||
                                    tasks.find((t) => String(t.id) === String(taskRow.task_id))
                                      ?.name ||
                                    taskRow.task_id ||
                                    '---'}
                                </td>
                                <td className="px-3 py-2 text-gray-600 dark:text-white/60">
                                  {numberFormat(budgetTotal)}
                                </td>
                                <td className="px-3 py-2 text-gray-600 dark:text-white/60">
                                  {numberFormat(actualTotal)}
                                </td>
                                <td
                                  className={`px-3 py-2 font-bold ${isOver ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}
                                >
                                  {budgetTotal ? `${pct}%` : '---'}
                                </td>
                              </tr>
                            )
                          })}
                          {(!variance?.tasks || variance.tasks.length === 0) && (
                            <tr>
                              <td
                                className="px-3 py-6 text-center text-gray-400 dark:text-white/30"
                                colSpan="4"
                              >
                                لا توجد بيانات انحراف لعرضها.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </>
            ) : plans.length > 0 ? (
              /* [AGRI-GUARDIAN 102] Plans Grid — شبكة بطاقات كل الخطط النشطة */
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-gray-800 dark:text-white">
                    جميع الخطط ({plans.length})
                  </h3>
                  <span className="text-xs text-gray-400 dark:text-white/40">
                    اضغط على أي خطة لعرض تفاصيلها
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {plans.map((plan) => {
                    const statusColors = {
                      active:
                        'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border-emerald-300 dark:border-emerald-500/30',
                      draft:
                        'bg-gray-100 dark:bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-500/30',
                      completed:
                        'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-300 dark:border-blue-500/30',
                      closed:
                        'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border-rose-300 dark:border-rose-500/30',
                    }
                    const statusLabels = {
                      active: 'نشطة',
                      draft: 'مسودة',
                      completed: 'مكتملة',
                      closed: 'مُقفلة',
                    }
                    const statusKey = (plan.status || 'active').toLowerCase()
                    return (
                      <button
                        key={plan.id}
                        type="button"
                        onClick={() => setSelectedPlanId(plan.id)}
                        className="rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-800/80 shadow-sm dark:shadow-none backdrop-blur-xl p-5 text-start hover:border-emerald-400 dark:hover:border-emerald-500/40 hover:shadow-lg hover:shadow-emerald-500/10 dark:hover:shadow-emerald-500/5 transition-all group cursor-pointer"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <h4 className="text-sm font-bold text-gray-800 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors truncate max-w-[200px]">
                            {plan.name}
                          </h4>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full border font-bold whitespace-nowrap ${statusColors[statusKey] || statusColors.active}`}
                          >
                            {statusLabels[statusKey] || statusKey}
                          </span>
                        </div>
                        <div className="space-y-1 text-xs text-gray-500 dark:text-white/50">
                          <div className="flex justify-between">
                            <span>المزرعة</span>
                            <span className="text-gray-700 dark:text-white/70">
                              {plan.farm?.name || '---'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>الموقع</span>
                            <span
                              className="text-emerald-600 dark:text-emerald-400/80 font-medium"
                              title={
                                plan.locations?.length > 1
                                  ? plan.locations.map((l) => l.name).join('، ')
                                  : ''
                              }
                            >
                              {plan.locations?.length > 0
                                ? plan.locations.length === 1
                                  ? plan.locations[0].name
                                  : `${plan.locations.length} مواقع`
                                : '---'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>المحصول</span>
                            <span className="text-gray-700 dark:text-white/70">
                              {plan.crop?.name || '---'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>الفترة</span>
                            <span className="text-gray-700 dark:text-white/70">
                              {plan.start_date || '—'} → {plan.end_date || '—'}
                            </span>
                          </div>
                        </div>
                        {plan.budget_total > 0 && (
                          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-white/5">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="text-gray-400 dark:text-white/40">الميزانية</span>
                              <span className="text-gray-600 dark:text-white/60 font-medium">
                                {numberFormat(plan.budget_total)} {plan.currency || 'YER'}
                              </span>
                            </div>
                          </div>
                        )}
                        {(!plan.budget_total || plan.budget_total === 0) && (
                          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-white/5">
                            <div className="text-xs text-amber-600 dark:text-amber-400/60 flex items-center gap-1">
                              <span>⚠️</span> لم تُحدد الميزانية
                            </div>
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="rounded-3xl border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-800/80 shadow-sm dark:shadow-none backdrop-blur-xl p-12 text-center">
                <div className="text-6xl mb-4 opacity-30">📋</div>
                <h3 className="text-xl font-bold text-gray-800 dark:text-white">
                  لا توجد خطط زراعية
                </h3>
                <p className="text-gray-400 dark:text-white/40 mt-2">
                  أنشئ خطة جديدة لبدء إدارة المهام، الموارد، والميزانية.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
