import { useState, useEffect } from 'react'
import { CropPlans, Farms, Crops, Locations, CropTemplates, Seasons, CropRecipes } from '../api/client'
import { useToast } from './ToastProvider'

// ─── Step Indicator ────────────────────────────────────────────────────────────
function StepBadge({ current, total }) {
  const labels = ['الإعداد', 'التوعية الزراعية', 'القالب والموارد', 'المراجعة']
  return (
    <div className="flex items-center gap-1 mt-2 text-sm opacity-90 flex-wrap">
      {labels.slice(0, total).map((label, i) => (
        <span key={i} className="flex items-center gap-1">
          <span
            className={`px-2 py-1 rounded text-xs font-medium transition-all ${
              current === i + 1
                ? 'bg-white text-green-700 font-bold shadow'
                : current > i + 1
                ? 'bg-green-400/40 text-white'
                : 'text-white/60'
            }`}
          >
            {i + 1}. {label}
          </span>
          {i < total - 1 && <span className="text-white/40">→</span>}
        </span>
      ))}
    </div>
  )
}

const PLAN_TYPE_OPTIONS = [
  { value: 'maintenance', label: '🔧 صيانة (تقليم، تسميد، ري)' },
  { value: 'harvest', label: '🌾 حصاد (جني، تعبئة)' },
  { value: 'rehabilitation', label: '🌱 تأهيل (إعادة تشكيل، استبدال)' },
  { value: 'general', label: '📋 عام (متعدد الأغراض)' },
]

const YIELD_UNIT_OPTIONS = [
  { value: 'kg', label: 'كيلوجرام (kg)' },
  { value: 'ton', label: 'طن' },
  { value: 'قنطار', label: 'قنطار' },
  { value: 'صندوق', label: 'صندوق' },
  { value: 'كيس', label: 'كيس' },
  { value: 'لتر', label: 'لتر' },
  { value: 'وحدة', label: 'وحدة' },
]

export default function CreatePlanWizard({ onClose, onSuccess }) {
  const toast = useToast()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [farms, setFarms] = useState([])
  const [crops, setCrops] = useState([])
  const [locations, setLocations] = useState([])
  const [templates, setTemplates] = useState([])
  const [seasons, setSeasons] = useState([])
  const [recipes, setRecipes] = useState([])
  const [selectedTemplateDetails, setSelectedTemplateDetails] = useState(null)
  const [useManualSeason, setUseManualSeason] = useState(false)
  const [existingPlans, setExistingPlans] = useState([])

  const [formData, setFormData] = useState({
    name: '',
    farm: '',
    crop: '',
    location_ids: [],
    template: '',
    recipe: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    currency: 'YER',
    season: '',
    season_ref: '',
    expected_yield: '',
    yield_unit: '',
    area: '',
    notes: '',
    plan_type: 'general',
  })

  // ── Derived state ───────────────────────────────────────────────────────────
  const selectedCrop = crops.find((c) => String(c.id) === String(formData.crop))
  const isPerennial = selectedCrop?.is_perennial || false

  // ── Initial loads ───────────────────────────────────────────────────────────
  useEffect(() => {
    Farms.list({ page_size: 100 })
      .then((res) => setFarms(Array.isArray(res.data?.results) ? res.data.results : res.data || []))
      .catch(console.error)
    Seasons.list({ is_active: true, page_size: 100 })
      .then((res) => setSeasons(Array.isArray(res.data?.results) ? res.data.results : res.data || []))
      .catch(console.error)
  }, [])

  // ── Farm-dependent loads ────────────────────────────────────────────────────
  useEffect(() => {
    if (formData.farm) {
      Crops.list({ farm_id: formData.farm, page_size: 100 })
        .then((res) => setCrops(Array.isArray(res.data?.results) ? res.data.results : res.data || []))
        .catch(console.error)
      Locations.list({ farm_id: formData.farm, page_size: 100 })
        .then((res) => setLocations(Array.isArray(res.data?.results) ? res.data.results : res.data || []))
        .catch(console.error)
    } else {
      setCrops([])
      setLocations([])
      setTemplates([])
      setRecipes([])
    }
  }, [formData.farm])

  // ── Crop-dependent loads ────────────────────────────────────────────────────
  useEffect(() => {
    if (formData.crop) {
      CropTemplates.list({ crop: formData.crop, page_size: 100 })
        .then((res) => setTemplates(Array.isArray(res.data?.results) ? res.data.results : res.data || []))
        .catch(console.error)
      CropRecipes.list({ crop: formData.crop, is_active: true, page_size: 50 })
        .then((res) => setRecipes(Array.isArray(res.data?.results) ? res.data.results : res.data || []))
        .catch(console.error)
    } else {
      setTemplates([])
      setRecipes([])
    }
  }, [formData.crop])

  // ── Proactive overlap check ─────────────────────────────────────────────────
  useEffect(() => {
    if (formData.farm && formData.crop) {
      CropPlans.list({ farm: formData.farm, crop: formData.crop, page_size: 20 })
        .then((res) => {
          const results = Array.isArray(res.data?.results) ? res.data.results : res.data || []
          setExistingPlans(results.filter((p) => p.status !== 'COMPLETED' && p.status !== 'ARCHIVED'))
        })
        .catch(() => setExistingPlans([]))
    } else {
      setExistingPlans([])
    }
  }, [formData.farm, formData.crop])

  // ── Template detail fetch ───────────────────────────────────────────────────
  useEffect(() => {
    if (formData.template) {
      CropTemplates.retrieve(formData.template)
        .then((res) => setSelectedTemplateDetails(res.data))
        .catch(console.error)
    } else {
      setSelectedTemplateDetails(null)
    }
  }, [formData.template])

  // ── Auto-set plan_type for seasonal crops ───────────────────────────────────
  useEffect(() => {
    if (!isPerennial) {
      setFormData((prev) => ({ ...prev, plan_type: 'general' }))
    }
  }, [isPerennial])

  // ── Validation ──────────────────────────────────────────────────────────────
  const nextStep = () => {
    if (step === 1) {
      if (
        !formData.farm ||
        !formData.crop ||
        !formData.location_ids ||
        formData.location_ids.length === 0 ||
        !formData.name ||
        !formData.start_date ||
        !formData.end_date
      ) {
        toast.error('يرجى تعبئة جميع الحقول المطلوبة')
        return
      }
      const start = new Date(formData.start_date)
      const end = new Date(formData.end_date)
      if (end < start) {
        toast.error('تاريخ الانتهاء لا يمكن أن يكون قبل تاريخ البدء')
        return
      }
    }
    setStep((s) => s + 1)
  }

  const prevStep = () => setStep((s) => s - 1)

  // ── Submit ──────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (loading) return
    setLoading(true)
    const payload = {
      ...formData,
      crop_id: formData.crop,
      location_ids: formData.location_ids,
      template: formData.template || null,
      recipe: formData.recipe || null,
      expected_yield: formData.expected_yield || null,
      yield_unit: formData.yield_unit || '',
      area: formData.area || null,
      notes: formData.notes || '',
      season_ref: formData.season_ref || null,
    }
    try {
      const res = await CropPlans.create(payload)
      toast.success('تم إنشاء الخطة بنجاح')
      onSuccess(res.data)
    } catch (error) {
      console.error(error)
      let msg = 'فشل إنشاء الخطة'
      const data = error.response?.data
      if (data) {
        if (data.error && typeof data.error === 'object') {
          msg = data.error.message || msg
          if (data.error.details && typeof data.error.details === 'object') {
            const fieldErrors = Object.entries(data.error.details)
              .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(' ') : String(val)}`)
              .join(' | ')
            if (fieldErrors) msg = `${msg} — ${fieldErrors}`
          }
        } else if (data.detail) {
          msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
        } else if (data.non_field_errors) {
          const nfe = data.non_field_errors
          msg = Array.isArray(nfe) ? nfe.join(' ') : String(nfe)
        } else {
          msg = Object.entries(data)
            .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(' ') : String(val)}`)
            .join(' | ')
        }
      }
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── Helper ──────────────────────────────────────────────────────────────────
  const set = (field, value) => setFormData((prev) => ({ ...prev, [field]: value }))

  const baseInput =
    'w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none bg-white dark:bg-slate-700 dark:text-white transition'
  const baseLabel = 'block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1'

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col overflow-hidden"
        style={{ maxHeight: '92vh' }}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-teal-600 p-5 text-white flex-shrink-0">
          <h3 className="text-xl font-bold">معالج إنشاء الخطة الزراعية</h3>
          <StepBadge current={step} total={4} />
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 dark:text-slate-200 space-y-5">

          {/* ════ STEP 1: Basic Setup ══════════════════════════════════════════ */}
          {step === 1 && (
            <div className="space-y-4 animate-fadeIn">

              {/* Farm + Locations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={baseLabel} htmlFor="wz-farm">المزرعة *</label>
                  <select
                    id="wz-farm"
                    aria-label="اختيار المزرعة"
                    className={baseInput}
                    value={formData.farm}
                    onChange={(e) =>
                      setFormData({ ...formData, farm: e.target.value, crop: '', location_ids: [], template: '', recipe: '' })
                    }
                  >
                    <option value="">اختر المزرعة</option>
                    {farms.map((f) => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={baseLabel}>المواقع (يمكن اختيار أكثر من موقع) *</label>
                  <div className="w-full border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 max-h-32 overflow-y-auto">
                    {locations.length === 0 ? (
                      <span className="text-gray-400 dark:text-slate-500 text-sm">
                        {formData.farm ? 'لا توجد مواقع' : 'اختر المزرعة أولاً'}
                      </span>
                    ) : (
                      <div className="space-y-1.5">
                        {locations.map((l) => (
                          <label
                            key={l.id}
                            className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-200 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-600 rounded px-1"
                          >
                            <input
                              type="checkbox"
                              className="rounded text-green-600 focus:ring-green-500"
                              checked={formData.location_ids.includes(l.id)}
                              onChange={(e) => {
                                const newIds = e.target.checked
                                  ? [...formData.location_ids, l.id]
                                  : formData.location_ids.filter((id) => id !== l.id)
                                set('location_ids', newIds)
                              }}
                            />
                            <span>{l.name} <span className="text-xs text-slate-400">({l.type || 'عام'})</span></span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Crop */}
              <div>
                <label className={baseLabel} htmlFor="wz-crop">المحصول *</label>
                <select
                  id="wz-crop"
                  aria-label="اختيار المحصول"
                  className={baseInput}
                  value={formData.crop}
                  onChange={(e) => setFormData({ ...formData, crop: e.target.value, template: '', recipe: '' })}
                  disabled={!formData.farm}
                >
                  <option value="">اختر المحصول</option>
                  {crops.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} {c.is_perennial ? '🌳' : '🌾'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Plan Name */}
              <div>
                <label className={baseLabel} htmlFor="wz-name">اسم الخطة *</label>
                <input
                  id="wz-name"
                  aria-label="اسم الخطة الزراعية"
                  type="text"
                  className={baseInput}
                  placeholder="مثال: خطة مانجو - صيانة 2026"
                  value={formData.name}
                  onChange={(e) => set('name', e.target.value)}
                />
              </div>

              {/* Dates */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={baseLabel} htmlFor="wz-start">تاريخ البدء *</label>
                  <input
                    id="wz-start"
                    aria-label="تاريخ بدء الخطة"
                    type="date"
                    className={baseInput}
                    value={formData.start_date}
                    onChange={(e) => set('start_date', e.target.value)}
                  />
                </div>
                <div>
                  <label className={baseLabel} htmlFor="wz-end">تاريخ الانتهاء *</label>
                  <input
                    id="wz-end"
                    aria-label="تاريخ انتهاء الخطة"
                    type="date"
                    className={baseInput}
                    value={formData.end_date}
                    onChange={(e) => set('end_date', e.target.value)}
                  />
                </div>
              </div>

              {/* Area + Yield */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={baseLabel} htmlFor="wz-area">المساحة (هكتار)</label>
                  <input
                    id="wz-area"
                    aria-label="مساحة الخطة بالهكتار"
                    type="number"
                    min="0"
                    step="0.01"
                    className={baseInput}
                    placeholder="مثال: 10.5"
                    value={formData.area}
                    onChange={(e) => set('area', e.target.value)}
                  />
                </div>
                <div>
                  <label className={baseLabel} htmlFor="wz-yield">الإنتاج المتوقع</label>
                  <div className="flex gap-2">
                    <input
                      id="wz-yield"
                      aria-label="كمية الإنتاج المتوقع"
                      type="number"
                      min="0"
                      step="0.01"
                      className={`${baseInput} flex-1`}
                      placeholder="مثال: 5000"
                      value={formData.expected_yield}
                      onChange={(e) => set('expected_yield', e.target.value)}
                    />
                    <select
                      aria-label="وحدة الإنتاج"
                      className={`${baseInput} w-28`}
                      value={formData.yield_unit}
                      onChange={(e) => set('yield_unit', e.target.value)}
                    >
                      <option value="">الوحدة</option>
                      {YIELD_UNIT_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className={baseLabel} htmlFor="wz-notes">ملاحظات</label>
                <textarea
                  id="wz-notes"
                  aria-label="ملاحظات الخطة"
                  className={baseInput}
                  rows={2}
                  placeholder="أي ملاحظات خاصة بهذه الخطة..."
                  value={formData.notes}
                  onChange={(e) => set('notes', e.target.value)}
                />
              </div>
            </div>
          )}

          {/* ════ STEP 2: Agronomic Awareness ════════════════════════════════ */}
          {step === 2 && (
            <div className="space-y-4 animate-fadeIn">
              <h4 className="font-bold text-lg text-gray-800 dark:text-white">🌿 التوعية الزراعية</h4>

              {/* Crop type banner */}
              {isPerennial ? (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl p-4">
                  <h5 className="font-bold text-amber-800 dark:text-amber-300">🌳 محصول معمر (شجري)</h5>
                  <p className="text-sm text-amber-700 dark:text-amber-400 mt-1">
                    تتعدد الخطط للمحصول المعمر وفق نوع النشاط — حدد الغرض من هذه الخطة:
                  </p>
                  <ul className="text-xs text-amber-600 dark:text-amber-500 mt-2 space-y-1 list-disc list-inside">
                    <li>صيانة سنوية: تقليم، تسميد، مكافحة، ري</li>
                    <li>حصاد: جني، تعبئة، نقل</li>
                    <li>تأهيل: إعادة تشكيل ملف النمو، استبدال أشجار</li>
                  </ul>
                </div>
              ) : (
                <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-xl p-4">
                  <h5 className="font-bold text-emerald-800 dark:text-emerald-300">🌾 محصول موسمي</h5>
                  <p className="text-sm text-emerald-700 dark:text-emerald-400 mt-1">
                    خطة واحدة تغطي دورة الإنتاج الكاملة — من زراعة الشتلة/البذرة حتى الحصاد.
                  </p>
                </div>
              )}

              {/* Plan type (perennial only) */}
              {isPerennial && (
                <div>
                  <label className={baseLabel}>نوع الخطة *</label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {PLAN_TYPE_OPTIONS.map((opt) => (
                      <label
                        key={opt.value}
                        className={`flex items-center gap-3 border rounded-xl p-3 cursor-pointer transition-all hover:border-green-400 dark:hover:border-green-500 ${
                          formData.plan_type === opt.value
                            ? 'border-green-500 bg-green-50 dark:bg-green-900/20 dark:border-green-500'
                            : 'border-slate-200 dark:border-slate-600'
                        }`}
                      >
                        <input
                          type="radio"
                          name="plan_type"
                          value={opt.value}
                          checked={formData.plan_type === opt.value}
                          onChange={() => set('plan_type', opt.value)}
                          className="text-green-600 focus:ring-green-500"
                        />
                        <span className="text-sm text-gray-700 dark:text-slate-200">{opt.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Proactive overlap warning */}
              {existingPlans.length > 0 && (
                <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-700 rounded-xl p-4">
                  <h5 className="font-bold text-rose-800 dark:text-rose-300">⚠️ خطط قائمة لنفس المحصول</h5>
                  <ul className="mt-2 space-y-1">
                    {existingPlans.slice(0, 5).map((p) => (
                      <li key={p.id} className="text-sm text-rose-700 dark:text-rose-400">
                        📋 {p.name} ({p.start_date} → {p.end_date}) — الحالة: {p.status}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs text-rose-600 dark:text-rose-500 mt-2">
                    تأكد أن الخطة الجديدة لفترة أو غرض مختلف قبل المتابعة.
                  </p>
                </div>
              )}

              {existingPlans.length === 0 && formData.crop && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-3 text-sm text-green-700 dark:text-green-400">
                  ✅ لا توجد خطط نشطة لهذا المحصول — يمكنك المتابعة بأمان.
                </div>
              )}
            </div>
          )}

          {/* ════ STEP 3: Template, Recipe, Season ═══════════════════════════ */}
          {step === 3 && (
            <div className="space-y-5 animate-fadeIn">

              {/* Template */}
              <div>
                <h4 className="font-bold text-gray-800 dark:text-white mb-1">⭐ القالب الزراعي</h4>
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
                  قالب جاهز يملأ المهام والمواد تلقائياً.
                </p>
                <select
                  aria-label="اختيار القالب الزراعي"
                  className="w-full border-2 border-indigo-100 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/30 rounded-lg px-3 py-2 text-sm text-indigo-700 dark:text-indigo-300 font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={formData.template}
                  onChange={(e) => setFormData({ ...formData, template: e.target.value })}
                >
                  <option value="">بدون قالب (خطة يدوية)</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
                {selectedTemplateDetails && (
                  <div className="bg-gray-50 dark:bg-slate-700 p-3 rounded-lg border border-gray-200 dark:border-slate-600 text-sm mt-2">
                    <span className="font-bold dark:text-white">معاينة: </span>
                    <span className="text-gray-600 dark:text-slate-300">
                      {selectedTemplateDetails.tasks?.length || 0} مهمة ·{' '}
                      {selectedTemplateDetails.materials?.length || 0} مادة
                    </span>
                  </div>
                )}
              </div>

              {/* Recipe/BOM */}
              <div>
                <h4 className="font-bold text-gray-800 dark:text-white mb-1">📐 الوصفة الزراعية (BOM)</h4>
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
                  ربط بمواصفة قياسية لحساب التكلفة المعيارية ورصد الانحراف.
                </p>
                <select
                  aria-label="اختيار الوصفة الزراعية BOM"
                  className="w-full border-2 border-teal-100 dark:border-teal-800 bg-teal-50 dark:bg-teal-900/30 rounded-lg px-3 py-2 text-sm text-teal-700 dark:text-teal-300 font-medium focus:ring-2 focus:ring-teal-500 outline-none"
                  value={formData.recipe}
                  onChange={(e) => set('recipe', e.target.value)}
                >
                  <option value="">بدون وصفة (تكلفة حرة)</option>
                  {recipes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} {r.phenological_stage ? `— ${r.phenological_stage}` : ''}
                    </option>
                  ))}
                </select>
                {recipes.length === 0 && formData.crop && (
                  <p className="text-xs text-slate-400 mt-1">لا توجد وصفات معيارية لهذا المحصول بعد.</p>
                )}
              </div>

              {/* Season + Currency */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={`${baseLabel} flex justify-between items-center`}>
                    <span>الموسم</span>
                    <button
                      type="button"
                      onClick={() => setUseManualSeason(!useManualSeason)}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-2"
                    >
                      {useManualSeason ? 'اختيار من القائمة' : 'موسم جديد / يدوي'}
                    </button>
                  </label>
                  {useManualSeason ? (
                    <input
                      aria-label="اسم الموسم يدوياً"
                      type="text"
                      className={baseInput}
                      placeholder="مثال: الموسم الصيفي 2026"
                      value={formData.season}
                      onChange={(e) => setFormData({ ...formData, season: e.target.value, season_ref: null })}
                    />
                  ) : (
                    <select
                      aria-label="اختيار الموسم من القائمة"
                      className={baseInput}
                      value={formData.season_ref || ''}
                      onChange={(e) => {
                        const val = e.target.value
                        const selected = seasons.find((s) => String(s.id) === val)
                        setFormData({
                          ...formData,
                          season_ref: val || null,
                          season: selected ? selected.name : '',
                        })
                      }}
                    >
                      <option value="">بدون موسم</option>
                      {seasons.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  )}
                </div>

                <div>
                  <label className={baseLabel}>العملة</label>
                  <select
                    aria-label="اختيار عملة الخطة"
                    className={baseInput}
                    value={formData.currency || 'YER'}
                    onChange={(e) => set('currency', e.target.value)}
                  >
                    <option value="YER">YER — ريال يمني</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* ════ STEP 4: Review ══════════════════════════════════════════════ */}
          {step === 4 && (
            <div className="space-y-4 animate-fadeIn">
              <h4 className="font-bold text-xl text-gray-800 dark:text-white border-b dark:border-slate-600 pb-2">
                ✅ ملخص الخطة — مراجعة نهائية
              </h4>

              <dl className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                {[
                  { label: 'اسم الخطة', value: formData.name },
                  {
                    label: 'المزرعة',
                    value: farms.find((f) => String(f.id) === String(formData.farm))?.name || '---',
                  },
                  {
                    label: 'المحصول',
                    value: `${selectedCrop?.name || '---'} ${isPerennial ? '🌳 معمر' : '🌾 موسمي'}`,
                  },
                  {
                    label: 'نوع الخطة',
                    value: PLAN_TYPE_OPTIONS.find((o) => o.value === formData.plan_type)?.label || '---',
                  },
                  {
                    label: 'المواقع',
                    value:
                      formData.location_ids.length > 0
                        ? formData.location_ids
                            .map((id) => locations.find((l) => l.id === id)?.name || `#${id}`)
                            .join('، ')
                        : '---',
                  },
                  { label: 'المدة', value: `${formData.start_date} ↔ ${formData.end_date}` },
                  {
                    label: 'الموسم',
                    value: formData.season || '---',
                  },
                  { label: 'العملة', value: formData.currency },
                  {
                    label: 'المساحة',
                    value: formData.area ? `${formData.area} هكتار` : 'غير محددة',
                  },
                  {
                    label: 'الإنتاج المتوقع',
                    value:
                      formData.expected_yield
                        ? `${formData.expected_yield} ${formData.yield_unit || ''}`
                        : 'غير محدد',
                  },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-gray-50 dark:bg-slate-700 p-3 rounded-lg">
                    <dt className="text-gray-500 dark:text-slate-400 text-xs">{label}</dt>
                    <dd className="font-bold text-gray-800 dark:text-white mt-0.5">{value}</dd>
                  </div>
                ))}

                {/* Template */}
                <div className="col-span-1 md:col-span-2 bg-indigo-50 dark:bg-indigo-900/30 p-3 rounded-lg border border-indigo-100 dark:border-indigo-800">
                  <dt className="text-indigo-600 dark:text-indigo-400 text-xs font-medium">القالب الزراعي</dt>
                  <dd className="font-bold text-indigo-900 dark:text-indigo-200 mt-0.5">
                    {formData.template
                      ? templates.find((t) => String(t.id) === String(formData.template))?.name || `QT#${formData.template}`
                      : 'لا يوجد (خطة يدوية)'}
                  </dd>
                </div>

                {/* Recipe */}
                <div className="col-span-1 md:col-span-2 bg-teal-50 dark:bg-teal-900/30 p-3 rounded-lg border border-teal-100 dark:border-teal-800">
                  <dt className="text-teal-600 dark:text-teal-400 text-xs font-medium">الوصفة الزراعية (BOM)</dt>
                  <dd className="font-bold text-teal-900 dark:text-teal-200 mt-0.5">
                    {formData.recipe
                      ? recipes.find((r) => String(r.id) === String(formData.recipe))?.name || `Recipe#${formData.recipe}`
                      : 'لا يوجد (تكلفة حرة)'}
                  </dd>
                </div>

                {/* Notes */}
                {formData.notes && (
                  <div className="col-span-1 md:col-span-2 bg-slate-50 dark:bg-slate-700 p-3 rounded-lg">
                    <dt className="text-gray-500 dark:text-slate-400 text-xs">الملاحظات</dt>
                    <dd className="text-gray-800 dark:text-white mt-0.5 text-sm">{formData.notes}</dd>
                  </div>
                )}
              </dl>

              {/* Overlap warning on review too */}
              {existingPlans.length > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl p-3">
                  <p className="text-sm text-amber-800 dark:text-amber-300 font-medium">
                    ⚠️ تذكير: يوجد {existingPlans.length} خطة نشطة لنفس المحصول. تأكد من عدم التكرار.
                  </p>
                </div>
              )}

              <p className="text-xs text-gray-400 dark:text-slate-500 text-center">
                سيقوم النظام بإنشاء الخطة وتوليد الأنشطة والميزانية بناءً على القالب والوصفة المختارة.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t dark:border-slate-700 bg-gray-50 dark:bg-slate-800 flex justify-between flex-shrink-0">
          <button
            type="button"
            onClick={step === 1 ? onClose : prevStep}
            className="px-5 py-2 rounded-xl border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 font-medium text-sm transition"
          >
            {step === 1 ? 'إلغاء' : '← السابق'}
          </button>

          {step < 4 ? (
            <button
              type="button"
              onClick={nextStep}
              className="px-6 py-2 rounded-xl bg-green-600 text-white hover:bg-green-700 font-bold text-sm transition shadow"
            >
              التالي →
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              aria-label="إنشاء الخطة الزراعية والتأكيد النهائي"
              className="px-8 py-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed shadow-lg transition"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
                  </svg>
                  جاري الإنشاء...
                </span>
              ) : (
                '✅ إنشاء الخطة'
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
