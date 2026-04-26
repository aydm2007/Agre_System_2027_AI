import { useEffect, useMemo, useState } from 'react'
import { Crops, Farms, Tasks, CropVarieties } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ToastProvider'
import TaskContractForm from '../components/TaskContractForm'

const CROP_TEXT = {
  title: 'إضافة محصول جديد',
  nameLabel: 'اسم المحصول',
  modeLabel: 'نوع الزراعة',
  modeOpen: 'مكشوف',
  modeProtected: 'محمي',
  perennialLabel: 'محصول دائم',
  farmLabel: 'المزرعة',
  submit: 'حفظ المحصول',
}

const SERVICE_TEXT = {
  title: 'إضافة خدمة/مهمة جديدة',
  cropLabel: 'المحصول',
  stageLabel: 'المرحلة',
  nameLabel: 'اسم الخدمة',
  requiresMachinery: 'يحتاج آليات',
  requiresWell: 'يحتاج بئر/ري',
  requiresArea: 'يحتاج مساحة',
  requiresTreeCount: 'يحتاج عدد أشجار',
  harvestTask: 'مهمة حصاد',
  assetTask: 'مهمة مرتبطة بالأصول',
  assetTypeLabel: 'نوع الأصل',
  submit: 'حفظ الخدمة',
}

const VARIETY_TEXT = {
  title: 'إضافة صنف محصول (مثل المانجو/الموز)',
  cropLabel: 'المحصول الأساسي',
  nameLabel: 'اسم الصنف',
  submit: 'حفظ الصنف',
}

// Removed MATERIAL_TEXT completely

const initialCropForm = {
  name: '',
  mode: 'Open',
  is_perennial: false,
  farm: '',
}

const initialVarietyForm = {
  crop: '',
  name: '',
}

// Removed initialMaterialForm

export default function ManageCatalogPage() {
  const auth = useAuth()
  const toast = useToast()

  const [farms, setFarms] = useState([])
  const [crops, setCrops] = useState([])
  const [cropForm, setCropForm] = useState(initialCropForm)
  const [varietyForm, setVarietyForm] = useState(initialVarietyForm)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError('')
      try {
        const [farmsResponse, cropsResponse] = await Promise.all([Farms.list(), Crops.list()])
        const allFarms = farmsResponse.data?.results ?? farmsResponse.data ?? []
        const accessible = allFarms.filter(
          (farm) => auth.hasFarmAccess(farm.id) || auth.isAdmin || auth.isSuperuser,
        )
        setFarms(accessible)
        const cropResults = cropsResponse.data?.results ?? cropsResponse.data ?? []
        setCrops(cropResults)
        if (accessible.length > 0) {
          setCropForm((prev) => ({ ...prev, farm: String(accessible[0].id) }))
        }
        if (cropResults.length > 0) {
          setVarietyForm((prev) => ({ ...prev, crop: String(cropResults[0].id) }))
        }
      } catch (err) {
        console.error('Failed to load catalog data', err)
        setError('تعذر تحميل بيانات المزارع أو المحاصيل.')
      } finally {
        setLoading(false)
      }
    })()
  }, [auth])

  const cropOptions = useMemo(
    () => crops.map((crop) => ({ id: crop.id, name: crop.name })),
    [crops],
  )

  const handleCropSubmit = async (event) => {
    event.preventDefault()
    if (!cropForm.name.trim() || !cropForm.farm) {
      toast.error('يرجى إدخال اسم المحصول والمزرعة.')
      return
    }
    try {
      const payload = {
        name: cropForm.name.trim(),
        mode: cropForm.mode,
        is_perennial: cropForm.is_perennial,
        farm: cropForm.farm,
      }
      const response = await Crops.create(payload)
      const newCrop = response.data ?? response
      setCrops((prev) => [...prev, newCrop])
      setCropForm((prev) => ({ ...initialCropForm, farm: prev.farm }))
      if (!varietyForm.crop) {
        setVarietyForm((prev) => ({ ...prev, crop: String(newCrop.id) }))
      }
      toast.success('تم إضافة المحصول بنجاح.')
    } catch (err) {
      console.error('Failed to create crop', err)
      toast.error('تعذر حفظ المحصول. تحقق من البيانات.')
    }
  }

  const handleServiceSubmit = async (formData, payload) => {
    try {
      await Tasks.create(payload)
      toast.success('تم إضافة العقد الذكي للخدمة بنجاح.')
      // Force reload crops to refresh cache if needed, or clear initial data explicitly if we bound it
    } catch (err) {
      console.error('Failed to create service', err)
      toast.error('تعذر حفظ الخدمة. تأكد من الصلاحيات والبيانات.')
    }
  }

  const handleVarietySubmit = async (event) => {
    event.preventDefault()
    if (!varietyForm.crop || !varietyForm.name.trim()) {
      toast.error('يرجى اختيار المحصول وإدخال اسم الصنف.')
      return
    }
    try {
      const payload = {
        crop: varietyForm.crop,
        name: varietyForm.name.trim(),
      }
      await CropVarieties.create(payload)
      setVarietyForm((prev) => ({ ...initialVarietyForm, crop: prev.crop }))
      toast.success('تم إضافة الصنف بنجاح.')
    } catch (err) {
      console.error('Failed to create variety', err)
      toast.error('تعذر حفظ الصنف. قد يكون الاسم مكرراً.')
    }
  }

  if (loading) {
    return (
      <div className="rounded-xl border border-primary/20 bg-primary/5 dark:bg-primary/10 px-4 py-3 text-primary-700 dark:text-primary-300">
        جاري التحميل...
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-red-700 dark:text-red-400"
        role="alert"
        aria-live="assertive"
      >
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white">{CROP_TEXT.title}</h2>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCropSubmit}>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {CROP_TEXT.nameLabel}
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2"
              value={cropForm.name}
              onChange={(event) => setCropForm((prev) => ({ ...prev, name: event.target.value }))}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {CROP_TEXT.farmLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2"
              value={cropForm.farm}
              onChange={(event) => setCropForm((prev) => ({ ...prev, farm: event.target.value }))}
              required
            >
              <option value="">اختر</option>
              {farms.map((farm) => (
                <option key={farm.id} value={String(farm.id)}>
                  {farm.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {CROP_TEXT.modeLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2"
              value={cropForm.mode}
              onChange={(event) => setCropForm((prev) => ({ ...prev, mode: event.target.value }))}
            >
              <option value="Open">{CROP_TEXT.modeOpen}</option>
              <option value="Protected">{CROP_TEXT.modeProtected}</option>
            </select>
          </div>
          <div className="md:col-span-2 space-y-3 mt-2">
            <label className="block text-sm font-bold text-gray-700 dark:text-slate-300">
              طبيعة المحصول (نظام التتبع المالي)
            </label>
            <div className="grid grid-cols-2 gap-4">
              <label
                className={`cursor-pointer rounded-2xl border-2 p-4 flex gap-3 transition-all ${!cropForm.is_perennial
                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                    : 'border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 hover:border-emerald-300'
                  }`}
              >
                <input
                  type="radio"
                  name="crop_type"
                  className="hidden"
                  checked={!cropForm.is_perennial}
                  onChange={() => setCropForm((prev) => ({ ...prev, is_perennial: false }))}
                />
                <div className="text-3xl">🌱</div>
                <div>
                  <h4
                    className={`font-bold ${!cropForm.is_perennial ? 'text-emerald-700 dark:text-emerald-300' : 'text-gray-700 dark:text-slate-300'}`}
                  >
                    محصول موسمي
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                    يحسب التكاليف كبضاعة تحت التشغيل (WIP) حتى الحصاد.
                  </p>
                </div>
              </label>

              <label
                className={`cursor-pointer rounded-2xl border-2 p-4 flex gap-3 transition-all ${cropForm.is_perennial
                    ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/20'
                    : 'border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 hover:border-amber-300'
                  }`}
              >
                <input
                  type="radio"
                  name="crop_type"
                  className="hidden"
                  checked={cropForm.is_perennial}
                  onChange={() => setCropForm((prev) => ({ ...prev, is_perennial: true }))}
                />
                <div className="text-3xl">🌳</div>
                <div>
                  <h4
                    className={`font-bold ${cropForm.is_perennial ? 'text-amber-700 dark:text-amber-300' : 'text-gray-700 dark:text-slate-300'}`}
                  >
                    أشجار معمرة (أصل بيولوجي)
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                    ترسمل تكاليف التأسيس وتخضع لتقييم جرد الثروة الشجرية.
                  </p>
                </div>
              </label>
            </div>
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {CROP_TEXT.submit}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
          {SERVICE_TEXT.title}
        </h2>
        <TaskContractForm
          showCropSelector={true}
          crops={crops}
          initialData={crops.length > 0 ? { cropId: String(crops[0].id) } : {}}
          onSubmit={handleServiceSubmit}
        />
      </section>

      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
          {VARIETY_TEXT.title}
        </h2>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleVarietySubmit}>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {VARIETY_TEXT.cropLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2"
              value={varietyForm.crop}
              onChange={(event) =>
                setVarietyForm((prev) => ({ ...prev, crop: event.target.value }))
              }
              required
            >
              <option value="">اختر</option>
              {cropOptions.map((crop) => (
                <option key={crop.id} value={String(crop.id)}>
                  {crop.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {VARIETY_TEXT.nameLabel}
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2"
              value={varietyForm.name}
              onChange={(event) =>
                setVarietyForm((prev) => ({ ...prev, name: event.target.value }))
              }
              required
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {VARIETY_TEXT.submit}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
