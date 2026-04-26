import { useEffect, useMemo, useState } from 'react'

import {
  Units,
  UnitConversions,
  Items,
  Crops,
  CropTemplates,
  CropTemplateMaterials,
  CropTemplateTasks,
} from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ToastProvider'

const UNIT_CONVERSION_TEXT = {
  title: 'تحويلات الوحدات',
  fromLabel: 'من وحدة',
  toLabel: 'إلى وحدة',
  multiplierLabel: 'المعامل',
  submit: 'حفظ التحويل',
  success: 'تم حفظ التحويل بنجاح.',
  removeSuccess: 'تم حذف التحويل.',
  missingFields: 'يرجى اختيار الوحدات وإدخال المعامل.',
}

const TEMPLATE_TEXT = {
  title: 'قوالب الخامات والأنشطة',
  createTitle: 'إنشاء قالب جديد',
  nameLabel: 'اسم القالب',
  categoryLabel: 'نوع القالب',
  descriptionLabel: 'الوصف',
  submit: 'إنشاء القالب',
  success: 'تم إنشاء القالب بنجاح.',
}

const TEMPLATE_MATERIAL_TEXT = {
  title: 'خامات القالب',
  itemLabel: 'الخامة',
  qtyLabel: 'الكمية',
  unitLabel: 'الوحدة',
  submit: 'إضافة الخامة',
  success: 'تم إضافة الخامة إلى القالب.',
  removeSuccess: 'تم إزالة الخامة من القالب.',
}

const TEMPLATE_TASK_TEXT = {
  title: 'أنشطة القالب',
  nameLabel: 'اسم النشاط',
  stageLabel: 'المرحلة',
  hoursLabel: 'الساعات المتوقعة',
  offsetLabel: 'بداية مطلع اليوم (Offset)',
  durationLabel: 'المدة بالأيام (Duration)',
  submit: 'إضافة النشاط',
  success: 'تم إضافة النشاط إلى القالب.',
  removeSuccess: 'تم إزالة النشاط من القالب.',
}

const TEMPLATE_CATEGORY_OPTIONS = [
  { value: 'bundle', label: 'حزمة متكاملة' },
  { value: 'service', label: 'خدمات' },
  { value: 'material', label: 'خامات' },
]

const initialConversionForm = {
  from_unit: '',
  to_unit: '',
  multiplier: '',
}

const initialTemplateForm = {
  crop: '',
  name: '',
  category: 'bundle',
  description: '',
}

const initialTemplateMaterialForm = {
  template: '',
  item: '',
  qty: '',
  unit: '',
}

const initialTemplateTaskForm = {
  template: '',
  name: '',
  stage: '',
  estimated_hours: '',
  days_offset: 0,
  duration_days: 1,
}

const describeUnit = (unit) => {
  if (!unit) return ''
  const symbol = unit.symbol || unit.code
  return symbol ? `${unit.name} (${symbol})` : unit.name
}

export default function TemplateManagerPage() {
  const auth = useAuth()
  const addToast = useToast()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [units, setUnits] = useState([])
  const [conversions, setConversions] = useState([])
  const [items, setItems] = useState([])
  const [crops, setCrops] = useState([])
  const [templates, setTemplates] = useState([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [selectedTemplateDetail, setSelectedTemplateDetail] = useState(null)

  const [conversionForm, setConversionForm] = useState(initialConversionForm)
  const [templateForm, setTemplateForm] = useState(initialTemplateForm)
  const [templateMaterialForm, setTemplateMaterialForm] = useState(initialTemplateMaterialForm)
  const [templateTaskForm, setTemplateTaskForm] = useState(initialTemplateTaskForm)

  useEffect(() => {
    let isMounted = true
      ; (async () => {
        setLoading(true)
        setError('')
        try {
          const [
            unitsResponse,
            conversionsResponse,
            itemsResponse,
            cropsResponse,
            templatesResponse,
          ] = await Promise.all([
            Units.list(),
            UnitConversions.list(),
            Items.list(),
            Crops.list(),
            CropTemplates.list(),
          ])

          if (!isMounted) return

          setUnits(unitsResponse.data?.results ?? unitsResponse.data ?? [])
          setConversions(conversionsResponse.data?.results ?? conversionsResponse.data ?? [])
          setItems(itemsResponse.data?.results ?? itemsResponse.data ?? [])

          const cropResults = cropsResponse.data?.results ?? cropsResponse.data ?? []
          const accessibleCrops = cropResults.filter(
            (crop) => auth.isSuperuser || auth.isAdmin || auth.hasFarmAccess?.(crop.id),
          )
          setCrops(accessibleCrops)

          const templateResults = templatesResponse.data?.results ?? templatesResponse.data ?? []
          setTemplates(templateResults)

          if (accessibleCrops.length && !templateForm.crop) {
            setTemplateForm((prev) => ({ ...prev, crop: String(accessibleCrops[0].id) }))
          }

          if (templateResults.length) {
            const firstTemplateId = String(templateResults[0].id)
            setSelectedTemplateId(firstTemplateId)
            setTemplateMaterialForm((prev) => ({ ...prev, template: firstTemplateId }))
            setTemplateTaskForm((prev) => ({ ...prev, template: firstTemplateId }))
          }
        } catch (err) {
          console.error('Failed to load template manager data', err)
          if (isMounted) setError('تعذر تحميل بيانات القوالب. حاول مرة أخرى.')
        } finally {
          if (isMounted) setLoading(false)
        }
      })()
    return () => {
      isMounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth])

  useEffect(() => {
    if (units.length >= 2) {
      setConversionForm((prev) => ({
        ...prev,
        from_unit: prev.from_unit || String(units[0].id),
        to_unit: prev.to_unit || String(units[1].id),
      }))
      setTemplateMaterialForm((prev) => ({ ...prev, unit: prev.unit || String(units[0].id) }))
    }
  }, [units])

  useEffect(() => {
    if (!selectedTemplateId) {
      setSelectedTemplateDetail(null)
      return
    }
    let isMounted = true
      ; (async () => {
        try {
          const response = await CropTemplates.retrieve(selectedTemplateId)
          if (isMounted) {
            setSelectedTemplateDetail(response.data ?? response)
          }
        } catch (err) {
          console.error('Failed to load template detail', err)
          if (isMounted) setSelectedTemplateDetail(null)
        }
      })()
    setTemplateMaterialForm((prev) => ({ ...prev, template: String(selectedTemplateId) }))
    setTemplateTaskForm((prev) => ({ ...prev, template: String(selectedTemplateId) }))
    return () => {
      isMounted = false
    }
  }, [selectedTemplateId])

  const unitOptions = useMemo(
    () => units.map((unit) => ({ id: String(unit.id), label: describeUnit(unit) })),
    [units],
  )

  const cropOptions = useMemo(
    () => crops.map((crop) => ({ id: String(crop.id), name: crop.name })),
    [crops],
  )

  const materialItems = useMemo(
    () => items.filter((item) => item.group !== 'Harvested Product'),
    [items],
  )

  const materialOptions = useMemo(
    () => materialItems.map((item) => ({ id: String(item.id), name: item.name })),
    [materialItems],
  )

  const templateMaterials = selectedTemplateDetail?.materials ?? []
  const templateTasks = selectedTemplateDetail?.tasks ?? []

  const handleConversionSubmit = async (event) => {
    event.preventDefault()
    if (
      !conversionForm.from_unit ||
      !conversionForm.to_unit ||
      !conversionForm.multiplier ||
      conversionForm.from_unit === conversionForm.to_unit
    ) {
      addToast({ intent: 'error', message: UNIT_CONVERSION_TEXT.missingFields })
      return
    }
    try {
      const response = await UnitConversions.create({
        from_unit: conversionForm.from_unit,
        to_unit: conversionForm.to_unit,
        multiplier: conversionForm.multiplier,
      })
      const created = response.data ?? response
      setConversions((prev) => [...prev, created])
      setConversionForm(initialConversionForm)
      addToast({ intent: 'success', message: UNIT_CONVERSION_TEXT.success })
    } catch (err) {
      console.error('Failed to create conversion', err)
      addToast({ intent: 'error', message: UNIT_CONVERSION_TEXT.missingFields })
    }
  }

  const handleConversionDelete = async (id) => {
    try {
      await UnitConversions.remove(id)
      setConversions((prev) => prev.filter((conversion) => conversion.id !== id))
      addToast({ intent: 'success', message: UNIT_CONVERSION_TEXT.removeSuccess })
    } catch (err) {
      console.error('Failed to delete conversion', err)
      addToast({ intent: 'error', message: UNIT_CONVERSION_TEXT.missingFields })
    }
  }

  const handleTemplateSubmit = async (event) => {
    event.preventDefault()
    if (!templateForm.crop || !templateForm.name.trim()) {
      addToast({ intent: 'error', message: TEMPLATE_TEXT.title })
      return
    }
    try {
      const response = await CropTemplates.create({
        crop: templateForm.crop,
        name: templateForm.name.trim(),
        category: templateForm.category,
        description: templateForm.description.trim(),
      })
      const created = response.data ?? response
      setTemplates((prev) => [...prev, created])
      setTemplateForm((prev) => ({ ...initialTemplateForm, crop: prev.crop }))
      setSelectedTemplateId(String(created.id))
      addToast({ intent: 'success', message: TEMPLATE_TEXT.success })
    } catch (err) {
      console.error('Failed to create template', err)
      addToast({ intent: 'error', message: TEMPLATE_TEXT.title })
    }
  }

  const handleTemplateMaterialSubmit = async (event) => {
    event.preventDefault()
    const templateId = templateMaterialForm.template || selectedTemplateId
    if (!templateId || !templateMaterialForm.item || !templateMaterialForm.qty) {
      addToast({ intent: 'error', message: TEMPLATE_MATERIAL_TEXT.title })
      return
    }
    try {
      await CropTemplateMaterials.create({
        template: templateId,
        item: templateMaterialForm.item,
        qty: templateMaterialForm.qty,
        unit: templateMaterialForm.unit || null,
      })
      const detail = await CropTemplates.retrieve(templateId)
      setSelectedTemplateDetail(detail.data ?? detail)
      setTemplateMaterialForm((prev) => ({
        ...initialTemplateMaterialForm,
        template: templateId,
        unit: prev.unit,
      }))
      addToast({ intent: 'success', message: TEMPLATE_MATERIAL_TEXT.success })
    } catch (err) {
      console.error('Failed to create template material', err)
      addToast({ intent: 'error', message: TEMPLATE_MATERIAL_TEXT.title })
    }
  }

  const handleTemplateMaterialDelete = async (id) => {
    if (!selectedTemplateId) return
    try {
      await CropTemplateMaterials.remove(id)
      const detail = await CropTemplates.retrieve(selectedTemplateId)
      setSelectedTemplateDetail(detail.data ?? detail)
      addToast({ intent: 'success', message: TEMPLATE_MATERIAL_TEXT.removeSuccess })
    } catch (err) {
      console.error('Failed to delete template material', err)
      addToast({ intent: 'error', message: TEMPLATE_MATERIAL_TEXT.title })
    }
  }

  const handleTemplateTaskSubmit = async (event) => {
    event.preventDefault()
    const templateId = templateTaskForm.template || selectedTemplateId
    if (!templateId || !templateTaskForm.name.trim()) {
      addToast({ intent: 'error', message: TEMPLATE_TASK_TEXT.title })
      return
    }
    try {
      await CropTemplateTasks.create({
        template: templateId,
        name: templateTaskForm.name.trim(),
        stage: templateTaskForm.stage.trim(),
        estimated_hours: templateTaskForm.estimated_hours
          ? Number(templateTaskForm.estimated_hours)
          : null,
        days_offset: Number(templateTaskForm.days_offset) || 0,
        duration_days: Number(templateTaskForm.duration_days) || 1,
      })
      const detail = await CropTemplates.retrieve(templateId)
      setSelectedTemplateDetail(detail.data ?? detail)
      setTemplateTaskForm(() => ({ ...initialTemplateTaskForm, template: templateId }))
      addToast({ intent: 'success', message: TEMPLATE_TASK_TEXT.success })
    } catch (err) {
      console.error('Failed to create template task', err)
      addToast({ intent: 'error', message: TEMPLATE_TASK_TEXT.title })
    }
  }

  const handleTemplateTaskDelete = async (id) => {
    if (!selectedTemplateId) return
    try {
      await CropTemplateTasks.remove(id)
      const detail = await CropTemplates.retrieve(selectedTemplateId)
      setSelectedTemplateDetail(detail.data ?? detail)
      addToast({ intent: 'success', message: TEMPLATE_TASK_TEXT.removeSuccess })
    } catch (err) {
      console.error('Failed to delete template task', err)
      addToast({ intent: 'error', message: TEMPLATE_TASK_TEXT.title })
    }
  }

  if (loading) {
    return (
      <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-primary-700">
        جارٍ تحميل بيانات القوالب...
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
          {UNIT_CONVERSION_TEXT.title}
        </h2>
        <form className="grid gap-4 md:grid-cols-4" onSubmit={handleConversionSubmit}>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-400">
              {UNIT_CONVERSION_TEXT.fromLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={conversionForm.from_unit}
              onChange={(event) =>
                setConversionForm((prev) => ({ ...prev, from_unit: event.target.value }))
              }
              required
            >
              <option value="">اختر الوحدة</option>
              {unitOptions.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">{UNIT_CONVERSION_TEXT.toLabel}</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={conversionForm.to_unit}
              onChange={(event) =>
                setConversionForm((prev) => ({ ...prev, to_unit: event.target.value }))
              }
              required
            >
              <option value="">اختر الوحدة</option>
              {unitOptions.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">
              {UNIT_CONVERSION_TEXT.multiplierLabel}
            </label>
            <input
              type="number"
              min="0"
              step="0.0001"
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={conversionForm.multiplier}
              onChange={(event) =>
                setConversionForm((prev) => ({ ...prev, multiplier: event.target.value }))
              }
              required
            />
          </div>
          <div className="md:flex md:items-end">
            <button
              type="submit"
              className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {UNIT_CONVERSION_TEXT.submit}
            </button>
          </div>
        </form>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 dark:bg-slate-700 text-gray-600 dark:text-slate-300">
              <tr>
                <th className="px-3 py-2 text-end font-medium">{UNIT_CONVERSION_TEXT.fromLabel}</th>
                <th className="px-3 py-2 text-end font-medium">{UNIT_CONVERSION_TEXT.toLabel}</th>
                <th className="px-3 py-2 text-end font-medium">
                  {UNIT_CONVERSION_TEXT.multiplierLabel}
                </th>
                <th className="px-3 py-2 text-end font-medium">خيارات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {conversions.map((conversion) => (
                <tr key={conversion.id} className="hover:bg-gray-50 dark:hover:bg-slate-700">
                  <td className="px-3 py-2 text-gray-700 dark:text-slate-200">
                    {describeUnit(conversion.from_unit_detail)}
                  </td>
                  <td className="px-3 py-2 text-gray-700 dark:text-slate-200">
                    {describeUnit(conversion.to_unit_detail)}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    {conversion.multiplier}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    <button
                      type="button"
                      onClick={() => handleConversionDelete(conversion.id)}
                      className="rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-50"
                    >
                      حذف
                    </button>
                  </td>
                </tr>
              ))}
              {!conversions.length && (
                <tr>
                  <td
                    className="px-3 py-3 text-center text-gray-500 dark:text-slate-400"
                    colSpan={4}
                  >
                    لا توجد تحويلات مسجلة حالياً.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
            {TEMPLATE_TEXT.title}
          </h2>
          <select
            className="rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            value={selectedTemplateId}
            onChange={(event) => setSelectedTemplateId(event.target.value)}
          >
            <option value="">اختر قالباً</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
        </div>

        <form
          className="grid gap-4 md:grid-cols-3 rounded-xl border border-gray-200 dark:border-slate-700 p-4 bg-gray-50 dark:bg-slate-900"
          onSubmit={handleTemplateSubmit}
        >
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-400">
              {TEMPLATE_TEXT.nameLabel}
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={templateForm.name}
              onChange={(event) =>
                setTemplateForm((prev) => ({ ...prev, name: event.target.value }))
              }
              required
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">{TEMPLATE_TEXT.categoryLabel}</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={templateForm.category}
              onChange={(event) =>
                setTemplateForm((prev) => ({ ...prev, category: event.target.value }))
              }
            >
              {TEMPLATE_CATEGORY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">{TEMPLATE_TEXT.descriptionLabel}</label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={templateForm.description}
              onChange={(event) =>
                setTemplateForm((prev) => ({ ...prev, description: event.target.value }))
              }
            />
          </div>
          <div className="space-y-1 md:col-span-3">
            <label className="block text-sm text-gray-600">المحصول</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={templateForm.crop}
              onChange={(event) =>
                setTemplateForm((prev) => ({ ...prev, crop: event.target.value }))
              }
              required
            >
              <option value="">اختر المحصول</option>
              {cropOptions.map((crop) => (
                <option key={crop.id} value={crop.id}>
                  {crop.name}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-3">
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {TEMPLATE_TEXT.submit}
            </button>
          </div>
        </form>

        <div className="grid gap-4 md:grid-cols-2">
          <form
            className="space-y-3 rounded-xl border border-gray-200 dark:border-slate-700 p-4"
            onSubmit={handleTemplateMaterialSubmit}
          >
            <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
              {TEMPLATE_MATERIAL_TEXT.title}
            </h3>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={templateMaterialForm.item}
              onChange={(event) =>
                setTemplateMaterialForm((prev) => ({ ...prev, item: event.target.value }))
              }
            >
              <option value="">اختر الخامة</option>
              {materialOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                type="number"
                min="0"
                step="0.01"
                className="rounded-lg border border-gray-300 px-3 py-2"
                placeholder={TEMPLATE_MATERIAL_TEXT.qtyLabel}
                value={templateMaterialForm.qty}
                onChange={(event) =>
                  setTemplateMaterialForm((prev) => ({ ...prev, qty: event.target.value }))
                }
              />
              <select
                className="rounded-lg border border-gray-300 px-3 py-2"
                value={templateMaterialForm.unit}
                onChange={(event) =>
                  setTemplateMaterialForm((prev) => ({ ...prev, unit: event.target.value }))
                }
              >
                <option value="">بدون تحديد</option>
                {unitOptions.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {TEMPLATE_MATERIAL_TEXT.submit}
            </button>
          </form>

          <form
            className="space-y-3 rounded-xl border border-gray-200 dark:border-slate-700 p-4"
            onSubmit={handleTemplateTaskSubmit}
          >
            <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
              {TEMPLATE_TASK_TEXT.title}
            </h3>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              placeholder={TEMPLATE_TASK_TEXT.nameLabel}
              value={templateTaskForm.name}
              onChange={(event) =>
                setTemplateTaskForm((prev) => ({ ...prev, name: event.target.value }))
              }
            />
            <div className="grid gap-3 md:grid-cols-2">
              <input
                type="text"
                className="rounded-lg border border-gray-300 px-3 py-2"
                placeholder={TEMPLATE_TASK_TEXT.stageLabel}
                value={templateTaskForm.stage}
                onChange={(event) =>
                  setTemplateTaskForm((prev) => ({ ...prev, stage: event.target.value }))
                }
              />
              <input
                type="number"
                min="0"
                step="0.25"
                className="rounded-lg border border-gray-300 px-3 py-2"
                placeholder={TEMPLATE_TASK_TEXT.hoursLabel}
                value={templateTaskForm.estimated_hours}
                onChange={(event) =>
                  setTemplateTaskForm((prev) => ({ ...prev, estimated_hours: event.target.value }))
                }
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label className="text-[10px] text-gray-500 font-medium">{TEMPLATE_TASK_TEXT.offsetLabel}</label>
                <input
                  type="number"
                  min="0"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  value={templateTaskForm.days_offset}
                  onChange={(event) =>
                    setTemplateTaskForm((prev) => ({ ...prev, days_offset: event.target.value }))
                  }
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-gray-500 font-medium">{TEMPLATE_TASK_TEXT.durationLabel}</label>
                <input
                  type="number"
                  min="1"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  value={templateTaskForm.duration_days}
                  onChange={(event) =>
                    setTemplateTaskForm((prev) => ({ ...prev, duration_days: event.target.value }))
                  }
                />
              </div>
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {TEMPLATE_TASK_TEXT.submit}
            </button>
          </form>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
              {TEMPLATE_MATERIAL_TEXT.title}
            </h3>
            {templateMaterials.map((material) => (
              <div
                key={material.id}
                className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-slate-700 p-3"
              >
                <div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-slate-100">
                    {material.item_detail?.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {material.qty} {describeUnit(material.unit_detail) || material.uom || ''}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleTemplateMaterialDelete(material.id)}
                  className="rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-50"
                >
                  حذف
                </button>
              </div>
            ))}
            {!templateMaterials.length && (
              <div className="rounded-xl border border-dashed border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 px-4 py-3 text-sm text-gray-500 dark:text-slate-400">
                لا توجد خامات مرتبطة بالقالب.
              </div>
            )}
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
              {TEMPLATE_TASK_TEXT.title}
            </h3>
            {templateTasks.map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-slate-700 p-3"
              >
                <div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-slate-100">
                    {task.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {task.stage || TEMPLATE_TASK_TEXT.stageLabel} • 
                    بداية: اليوم {task.days_offset} • 
                    المدة: {task.duration_days} يوم
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleTemplateTaskDelete(task.id)}
                  className="rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-50"
                >
                  حذف
                </button>
              </div>
            ))}
            {!templateTasks.length && (
              <div className="rounded-xl border border-dashed border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 px-4 py-3 text-sm text-gray-500 dark:text-slate-400">
                لا توجد أنشطة مرتبطة بالقالب.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
