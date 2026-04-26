import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Crops, Items, MaterialCatalog, Units, Farms, CropMaterials } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useSettings } from '../contexts/SettingsContext.jsx'
import { useToast } from '../components/ToastProvider'
import { MATERIAL_TYPES } from './daily-log/constants.js'

const TEXT = {
  title: 'كتالوج المواد والخامات',
  farmLabel: 'المزرعة',
  cropLabel: 'المحصول',
  itemLabel: 'المادة',
  recommendations: 'الكمية الموصى بها',
  onHand: 'المتوفر حاليًا',
  reorderLevel: 'حد إعادة الطلب',
  lowStock: 'حالة المادة',
  unit: 'الوحدة',
  refresh: 'تحديث القائمة',
  low: 'منخفض',
  ok: 'كافٍ',
  noResults: 'لا توجد بيانات مواد وفق عوامل التصفية الحالية.',
  loading: 'جاري تحميل كتالوج المواد...',
  error: 'تعذر تحميل كتالوج المواد.',
  actions: 'إجراءات',
  edit: 'تعديل',
  delete: 'حذف',
  save: 'حفظ',
  cancel: 'إلغاء',
  editNameLabel: 'اسم المادة',
  editReorderLabel: 'حد إعادة الطلب',
  deleteConfirm: (name) => `هل تريد حذف المادة "${name}"؟`,
  createSuccess: (name) => `تم إضافة المادة "${name}" إلى الكتالوج.`,
  updateSuccess: (name) => `تم تحديث بيانات المادة "${name}" بنجاح.`,
  deleteSuccess: (name) => `تم حذف المادة "${name}" من الكتالوج.`,
  showLocations: 'عرض تفاصيل المخازن',
  locationLevels: 'توزيع المخزون:',
}

const initialFilters = {
  farm: '',
  crop: '',
  item: '',
}

const initialItemForm = {
  name: '',
  group: '',
  material_type: '',
  unit: '',
  uom: '',
  currency: 'YER',
  unit_price: '',
  reorder_level: '',
}

const formatNumber = (value) => {
  if (value === null || value === undefined) return '-'
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  return number.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function MaterialsCatalogPage() {
  const auth = useAuth()
  const { isAdmin, isSuperuser } = auth
  const { isStrictMode } = useSettings()
  const addToast = useToast()
  const navigate = useNavigate()

  const canManageCatalog = isAdmin || isSuperuser || isStrictMode

  const [filters, setFilters] = useState(initialFilters)
  const [showLocations, setShowLocations] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [records, setRecords] = useState([])
  const [farms, setFarms] = useState([])
  const [crops, setCrops] = useState([])
  const [items, setItems] = useState([])
  const [units, setUnits] = useState([])
  const [itemForm, setItemForm] = useState(initialItemForm)
  const [itemSubmitting, setItemSubmitting] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [editingItemSaving, setEditingItemSaving] = useState(false)
  const [linkForm, setLinkForm] = useState({
    crop: '',
    item: '',
    recommended_qty: '',
    recommended_unit: '',
  })
  const [linkSubmitting, setLinkSubmitting] = useState(false)

  useEffect(() => {
    let isMounted = true
    ;(async () => {
        try {
          setLoading(true)
          setError('')
          const [cropsResponse, itemsResponse, unitsResponse, farmResponse] = await Promise.all([
            Crops.list({ global: '1' }),
            Items.list(),
            Units.list(),
            Farms.list()
          ])
          if (!isMounted) return
          const cropResults = cropsResponse.data?.results ?? cropsResponse.data ?? []

          const allFarms = farmResponse.data?.results ?? farmResponse.data ?? []
          const accessible = allFarms.filter(
            (farm) => auth.isSuperuser || auth.isAdmin || auth.hasFarmAccess(farm.id),
          )
          setFarms(accessible)

          setCrops(cropResults)
          setItems(itemsResponse.data?.results ?? itemsResponse.data ?? [])
          setUnits(unitsResponse.data?.results ?? unitsResponse.data ?? [])

          if (accessible.length) {
            setFilters((prev) => ({ ...prev, farm: String(accessible[0].id) }))
          }
        } catch (err) {
          console.error('Failed to load catalog filters', err)
          if (isMounted) setError(TEXT.error)
        } finally {
          if (isMounted) setLoading(false)
        }
      })()
    return () => {
      isMounted = false
    }
  }, [auth])

  const loadCatalog = useCallback(async (appliedFilters) => {
    try {
      setLoading(true)
      setError('')
      const params = {}
      if (appliedFilters.farm) params.farm_id = appliedFilters.farm
      if (appliedFilters.crop) params.crop = appliedFilters.crop
      if (appliedFilters.item) params.item = appliedFilters.item
      if (showLocations) params.include_locations = 'true'
      const response = await MaterialCatalog.list(params)
      setRecords(response.data ?? [])
    } catch (err) {
      console.error('Failed to load material catalog', err)
      setError(TEXT.error)
      addToast({ intent: 'error', message: TEXT.error })
    } finally {
      setLoading(false)
    }
  }, [addToast, showLocations])

  useEffect(() => {
    if (filters.farm) {
      loadCatalog(filters).catch(() => { })
    }
  }, [filters, loadCatalog, showLocations])

  const cropOptions = useMemo(
    () => crops.map((crop) => ({ id: String(crop.id), name: crop.name })),
    [crops],
  )

  const farmOptions = useMemo(
    () => farms.map((farm) => ({ id: String(farm.id), name: farm.name })),
    [farms],
  )

  const itemOptions = useMemo(
    () => items.map((item) => ({ id: String(item.id), name: item.name })),
    [items],
  )

  const handleSubmit = (event) => {
    event.preventDefault()
    loadCatalog(filters).catch(() => { })
  }

  const handleCreateItem = async (event) => {
    event.preventDefault()
    if (!itemForm.name.trim() || !itemForm.group.trim()) {
      addToast({ intent: 'error', message: 'يرجى إدخال اسم المادة وتصنيفها.' })
      return
    }
    try {
      setItemSubmitting(true)
      const payload = {
        name: itemForm.name.trim(),
        group: itemForm.material_type ? MATERIAL_TYPES[itemForm.material_type] : (itemForm.group.trim() || 'أخرى'),
        material_type: itemForm.material_type || undefined,
        unit: itemForm.unit || undefined,
        uom: itemForm.uom || undefined,
        currency: itemForm.currency || 'YER',
        unit_price: itemForm.unit_price ? Number(itemForm.unit_price) : undefined,
        reorder_level: itemForm.reorder_level || undefined,
      }
      await Items.create(payload)
      addToast({ intent: 'success', message: TEXT.createSuccess(payload.name) })
      setItemForm(initialItemForm)
      await Promise.all([
        loadCatalog(filters),
        Items.list().then((response) => {
          setItems(response.data?.results ?? response.data ?? [])
        }),
      ])
    } catch (err) {
      console.error('Failed to create catalog item', err)
      addToast({ intent: 'error', message: TEXT.error })
    } finally {
      setItemSubmitting(false)
    }
  }

  const handleLinkMaterial = async (event) => {
    event.preventDefault()
    if (!linkForm.crop || !linkForm.item) {
      addToast({ intent: 'error', message: 'يرجى اختيار المحصول والمادة.' })
      return
    }
    try {
      setLinkSubmitting(true)
      await CropMaterials.create({
        crop: Number(linkForm.crop),
        item: Number(linkForm.item),
        recommended_qty: linkForm.recommended_qty ? Number(linkForm.recommended_qty) : null,
        recommended_unit: linkForm.recommended_unit ? Number(linkForm.recommended_unit) : null,
      })
      addToast({ intent: 'success', message: 'تم ربط المادة بالمحصول بنجاح. ستظهر الآن في الخطط والإنجاز.' })
      setLinkForm({ crop: '', item: '', recommended_qty: '', recommended_unit: '' })
      await Promise.all([loadCatalog(filters)])
    } catch (err) {
      console.error('Failed to link material to crop', err)
      let msg = 'فشل ربط المادة بالمحصول، ربما تكون مربوطة بالفعل.'
      if (err?.response?.status === 409) msg = 'المادة مربوطة مسبقًا بهذا المحصول'
      addToast({ intent: 'error', message: msg })
    } finally {
      setLinkSubmitting(false)
    }
  }

  const startEditingItem = (record) => {
    const sourceItem = items.find((item) => String(item.id) === String(record.item_id))
    setEditingItem({
      id: record.item_id,
      name: sourceItem?.name ?? record.item_name,
      group: sourceItem?.group ?? record.item_group ?? '',
      unit: sourceItem?.unit ?? record.item_unit_id ?? '',
      uom:
        sourceItem?.unit_detail?.symbol ??
        sourceItem?.uom ??
        record.recommended_unit?.symbol ??
        record.on_hand_unit?.symbol ??
        '',
      currency: sourceItem?.currency ?? record.item_currency ?? 'YER',
      unit_price: sourceItem?.unit_price ?? record.item_unit_price ?? '',
      material_type: sourceItem?.material_type ?? record.item_material_type ?? '',
      reorder_level: sourceItem?.reorder_level ?? record.reorder_level ?? '',
      crop_material_id: record.crop_material_id ?? null,
      crop: record.crop_id ? String(record.crop_id) : '',
      recommended_qty: record.recommended_qty ?? '',
      recommended_unit: record.recommended_unit_id ?? '',
    })
  }

  const cancelEditingItem = () => {
    setEditingItem(null)
    setEditingItemSaving(false)
  }

  const handleEditingItemChange = (field, value) => {
    setEditingItem((prev) => ({ ...prev, [field]: value }))
  }

  const refreshItemsList = async () => {
    const response = await Items.list()
    setItems(response.data?.results ?? response.data ?? [])
  }

  const saveEditingItem = async () => {
    if (!editingItem || !editingItem.name.trim()) {
      addToast({ intent: 'error', message: 'يرجى إدخال اسم صالح للمادة.' })
      return
    }
    try {
      setEditingItemSaving(true)
      await Items.update(editingItem.id, {
        name: editingItem.name.trim(),
        group: editingItem.group?.trim() || '',
        unit: editingItem.unit || null,
        uom: editingItem.uom || '',
        currency: editingItem.currency || 'YER',
        unit_price:
          editingItem.unit_price === '' || editingItem.unit_price === null
            ? null
            : Number(editingItem.unit_price),
        material_type: editingItem.material_type || '',
        reorder_level:
          editingItem.reorder_level === '' || editingItem.reorder_level === null
            ? null
            : Number(editingItem.reorder_level),
      })
      if (editingItem.crop_material_id) {
        await CropMaterials.update(editingItem.crop_material_id, {
          crop: editingItem.crop ? Number(editingItem.crop) : null,
          item: editingItem.id,
          recommended_qty:
            editingItem.recommended_qty === '' || editingItem.recommended_qty === null
              ? null
              : Number(editingItem.recommended_qty),
          recommended_unit: editingItem.recommended_unit
            ? Number(editingItem.recommended_unit)
            : null,
        })
      }
      addToast({ intent: 'success', message: TEXT.updateSuccess(editingItem.name.trim()) })
      setEditingItem(null)
      await Promise.all([loadCatalog(filters), refreshItemsList()])
    } catch (err) {
      console.error('Failed to update item', err)
      addToast({ intent: 'error', message: 'تعذر تحديث بيانات المادة.' })
    } finally {
      setEditingItemSaving(false)
    }
  }

  const deleteItem = async (record) => {
    const confirmed = window.confirm(TEXT.deleteConfirm(record.item_name))
    if (!confirmed) return
    try {
      await Items.remove(record.item_id)
      addToast({ intent: 'success', message: TEXT.deleteSuccess(record.item_name) })
      await Promise.all([loadCatalog(filters), refreshItemsList()])
    } catch (err) {
      console.error('Failed to delete item', err)
      addToast({ intent: 'error', message: 'تعذر حذف المادة.' })
    }
  }

  if (loading && !records.length) {
    return (
      <div className="rounded-xl border border-primary/20 bg-primary/5 dark:bg-primary/10 px-4 py-3 text-primary-700 dark:text-primary-400">
        {TEXT.loading}
      </div>
    )
  }

  if (error && !records.length) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 px-4 py-3 text-red-700 dark:text-red-400">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section
        data-testid="materials-catalog-page"
        className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm space-y-4"
      >
        <h1 data-testid="materials-catalog-title" className="text-xl font-semibold text-gray-800 dark:text-white">{TEXT.title}</h1>
        {canManageCatalog && (
          <form className="grid gap-3 md:grid-cols-4" onSubmit={handleCreateItem}>
            <div className="md:col-span-4 text-sm font-semibold text-primary-700 dark:text-primary-400">
              إضافة مادة أو خامة جديدة
            </div>
            <div className="space-y-1">
              <label className="block text-sm text-gray-600 dark:text-slate-300">اسم المادة</label>
              <input
                type="text"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={itemForm.name}
                onChange={(event) => setItemForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="مثال: سماد نيتروجيني"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm text-gray-600 dark:text-slate-300">تصنيف المادة (النوع)</label>
              <select
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={itemForm.material_type}
                onChange={(event) => setItemForm((prev) => ({ 
                  ...prev, 
                  material_type: event.target.value,
                  group: event.target.value ? MATERIAL_TYPES[event.target.value] : prev.group 
                }))}
                required
              >
                <option value="">اختر التصنيف...</option>
                {Object.entries(MATERIAL_TYPES).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="block text-sm text-gray-600 dark:text-slate-300">
                الوحدة الافتراضية
              </label>
              <select
                data-testid="materials-catalog-unit-select"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={itemForm.unit}
                onChange={(event) => {
                  const selectedUnitId = event.target.value;
                  const selectedUnit = units.find((u) => String(u.id) === String(selectedUnitId));
                  setItemForm((prev) => ({ 
                    ...prev, 
                    unit: selectedUnitId,
                    uom: selectedUnit ? (selectedUnit.symbol || selectedUnit.code) : prev.uom
                  }));
                }}
              >
                <option value="">اختر الوحدة</option>
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.name} ({unit.symbol || unit.code})
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="block text-sm text-gray-600 dark:text-slate-300">رمز الوحدة</label>
              <input
                type="text"
                data-testid="materials-catalog-uom-input"
                className="w-full rounded-lg border border-gray-200 dark:border-slate-700 px-3 py-2 bg-gray-50 dark:bg-slate-800/70 dark:text-slate-300"
                value={itemForm.uom}
                readOnly
                placeholder="مثال: كجم"
              />
              <p className="text-[11px] text-gray-500 dark:text-slate-400">
                يتم اشتقاق رمز الوحدة من الوحدة القياسية المختارة لمنع اختلافات الإدخال بين
                المخازن والإنجاز اليومي والتقارير.
              </p>
            </div>
            <div className="space-y-1">
              <label className="block text-sm text-gray-600 dark:text-slate-300">السعر المعياري</label>
              <div className="relative">
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 pl-12 bg-white dark:bg-slate-700 dark:text-white"
                  value={itemForm.unit_price}
                  onChange={(event) => setItemForm((prev) => ({ ...prev, unit_price: event.target.value }))}
                  placeholder="0.00"
                />
                <span className="absolute left-3 top-2 text-sm text-gray-500">ر.ي</span>
              </div>
            </div>
            <div className="space-y-1">
              <label className="block text-sm text-gray-600 dark:text-slate-300">
                حد إعادة الطلب
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={itemForm.reorder_level}
                onChange={(event) =>
                  setItemForm((prev) => ({ ...prev, reorder_level: event.target.value }))
                }
                placeholder="مثال: 25"
              />
            </div>
            <div className="flex items-end gap-3 md:col-span-4 mt-2">
              <button
                type="submit"
                disabled={itemSubmitting}
                className="rounded-lg bg-emerald-600 px-6 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-70"
              >
                إضافة مادة جديدة في الكتالوج
              </button>
            </div>
          </form>
        )}

        <form className="grid gap-3 md:grid-cols-5 pt-4 border-t border-gray-200 dark:border-slate-700" onSubmit={handleLinkMaterial}>
          <div className="md:col-span-4 text-sm font-semibold text-indigo-700 dark:text-indigo-400">
            ربط مادة بمحصول (لتظهر في الإنجاز اليومي والخطط)
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">المحصول</label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={linkForm.crop}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, crop: e.target.value }))}
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
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">المادة</label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={linkForm.item}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, item: e.target.value }))}
              required
            >
              <option value="">اختر المادة</option>
              {itemOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">كمية التوصية (اختياري)</label>
            <input
              type="number"
              min="0"
              step="any"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={linkForm.recommended_qty}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, recommended_qty: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">الوحدة الموصى بها</label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={linkForm.recommended_unit}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, recommended_unit: e.target.value }))}
            >
              <option value="">اختر الوحدة</option>
              {units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.name} ({unit.symbol || unit.code})
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-3 md:pt-6">
            <button
              type="submit"
              disabled={linkSubmitting}
              className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-70"
            >
              ربط المادة بالمحصول
            </button>
          </div>
        </form>
        <form className="grid gap-3 md:grid-cols-4" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.farmLabel}
            </label>
            <select
              data-testid="materials-catalog-farm-filter"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.farm}
              onChange={(event) => setFilters((prev) => ({ ...prev, farm: event.target.value }))}
              required
            >
              <option value="">اختر المزرعة</option>
              {farmOptions.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.cropLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.crop}
              onChange={(event) => setFilters((prev) => ({ ...prev, crop: event.target.value }))}
            >
              <option value="">جميع المحاصيل</option>
              {cropOptions.map((crop) => (
                <option key={crop.id} value={crop.id}>
                  {crop.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.itemLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.item}
              onChange={(event) => setFilters((prev) => ({ ...prev, item: event.target.value }))}
            >
              <option value="">جميع المواد</option>
              {itemOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
          <div className="md:flex md:items-center md:gap-4 md:pt-4 md:col-span-1">
             <label className="flex items-center gap-2 cursor-pointer select-none">
                <input 
                  type="checkbox"
                  className="w-4 h-4 rounded text-primary border-gray-300 focus:ring-primary"
                  checked={showLocations}
                  onChange={(e) => setShowLocations(e.target.checked)}
                />
                <span className="text-sm text-gray-700 dark:text-slate-300">{TEXT.showLocations}</span>
             </label>
          </div>
          <div className="md:flex md:items-end">
            <button
              type="submit"
              className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {TEXT.refresh}
            </button>
          </div>
        </form>
      </section>

      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 px-4 py-3 text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm space-y-4">
        {loading && (
          <div className="rounded-lg border border-primary/20 bg-primary/5 dark:bg-primary/10 px-3 py-2 text-sm text-primary-700 dark:text-primary-400">
            {TEXT.loading}
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 dark:bg-slate-700 text-gray-600 dark:text-slate-300">
              <tr>
                <th className="px-3 py-2 text-end font-medium">{TEXT.cropLabel}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.itemLabel}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.recommendations}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.onHand}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.reorderLevel}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.unit}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.lowStock}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.actions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {records.map((record) => (
                <tr
                  key={`${record.crop_id}-${record.item_id}`}
                  className="hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  <td className="px-3 py-2 text-gray-800 dark:text-slate-200">
                    {record.crop_name}
                  </td>
                  <td className="px-3 py-2 text-gray-800 dark:text-slate-200">
                    {editingItem?.id === record.item_id ? (
                      <input
                        type="text"
                        className="w-full rounded border border-gray-300 dark:border-slate-600 px-2 py-1 text-sm bg-white dark:bg-slate-700 dark:text-white"
                        value={editingItem.name}
                        onChange={(event) => handleEditingItemChange('name', event.target.value)}
                      />
                    ) : (
                      record.item_name
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    {formatNumber(record.recommended_qty)}{' '}
                    {record.recommended_unit?.symbol || record.recommended_uom || ''}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    <div>
                        {formatNumber(record.on_hand_qty)}{' '}
                        {record.on_hand_unit?.symbol || record.on_hand_uom || ''}
                    </div>
                    {showLocations && record.locations && record.locations.length > 0 && (
                        <div className="mt-2 text-[11px] bg-gray-50 dark:bg-slate-700/50 p-2 rounded-lg border border-gray-100 dark:border-slate-600">
                            <div className="font-semibold text-gray-400 mb-1">{TEXT.locationLevels}</div>
                            <div className="space-y-1">
                                {record.locations.map(loc => (
                                    <div key={loc.location_id} className="flex justify-between gap-4 border-b border-gray-100 dark:border-slate-600 last:border-0 pb-1">
                                        <span className="text-gray-500">{loc.location_name}</span>
                                        <span className="font-medium text-primary-600">{formatNumber(loc.qty)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    {editingItem?.id === record.item_id ? (
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        className="w-full rounded border border-gray-300 dark:border-slate-600 px-2 py-1 text-sm bg-white dark:bg-slate-700 dark:text-white"
                        value={editingItem.reorder_level}
                        onChange={(event) =>
                          handleEditingItemChange('reorder_level', event.target.value)
                        }
                      />
                    ) : record.reorder_level ? (
                      `${formatNumber(record.reorder_level)} ${record.on_hand_unit?.symbol || record.on_hand_uom || ''}`
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-500 dark:text-slate-400">
                    {record.on_hand_unit?.name || record.recommended_unit?.name || '-'}
                  </td>
                  <td className="px-3 py-2">
                    {record.low_stock ? (
                      <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
                        {TEXT.low}
                      </span>
                    ) : (
                      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                        {TEXT.ok}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-end">
                    {editingItem?.id === record.item_id ? (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="rounded-lg bg-primary px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-primary/90 disabled:opacity-70"
                          onClick={saveEditingItem}
                          disabled={editingItemSaving}
                        >
                          {TEXT.save}
                        </button>
                        <button
                          type="button"
                          className="rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-1 text-xs font-semibold text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-600"
                          onClick={cancelEditingItem}
                          disabled={editingItemSaving}
                        >
                          {TEXT.cancel}
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        {canManageCatalog && (
                          <button
                            type="button"
                            className="rounded-lg border border-emerald-200 px-3 py-1 text-xs font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:border-emerald-800 dark:text-emerald-400"
                            title="الانتقال إلى شاشة إدارة المخزون لتوريد كمية جديدة"
                            onClick={() => navigate('/stock-management')}
                          >
                            توريد للمخزن
                          </button>
                        )}
                        {canManageCatalog && (
                          <button
                            type="button"
                            className="rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-1 text-xs font-semibold text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-600"
                            onClick={() => startEditingItem(record)}
                          >
                            {TEXT.edit}
                          </button>
                        )}
                        {canManageCatalog && (
                          <button
                            type="button"
                            className="rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-50"
                            onClick={() => deleteItem(record)}
                          >
                            {TEXT.delete}
                          </button>
                        )}
                        {!canManageCatalog && (
                           <span className="text-[11px] italic text-gray-400">للقراءة فقط</span>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {!records.length && !loading && (
                <tr>
                  <td
                    className="px-3 py-3 text-center text-gray-500 dark:text-slate-400"
                    colSpan={8}
                  >
                    {TEXT.noResults}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
