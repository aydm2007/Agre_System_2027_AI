import { useState, useEffect, useCallback } from 'react'
import { toast } from 'react-hot-toast'
import { v4 as uuidv4 } from 'uuid'
import { api } from '../../../api/client'
import {
  TEXT,
  createUnitRow,
  ensureDefaultUnitSelection,
  prepareProductPayload,
} from '../constants'

const asList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  if (Array.isArray(payload?.data?.results)) return payload.data.results
  if (Array.isArray(payload?.data)) return payload.data
  return []
}

const parseApiErrorMessage = (error, fallback = 'فشل تنفيذ العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback

  if (typeof payload?.detail === 'string' && payload.detail.trim()) return payload.detail
  if (Array.isArray(payload?.detail)) return payload.detail.join(' - ')
  if (typeof payload === 'string' && payload.trim()) return payload

  if (typeof payload === 'object') {
    const messages = []
    Object.entries(payload).forEach(([field, value]) => {
      if (field === 'detail') return
      if (Array.isArray(value)) messages.push(`${field}: ${value.join(', ')}`)
      else if (typeof value === 'string') messages.push(`${field}: ${value}`)
    })
    if (messages.length) return messages.join(' - ')
  }

  return fallback
}

export const useHarvestCatalog = (selectedFarmId) => {
  const [catalog, setCatalog] = useState([])
  const [loadingCatalog, setLoadingCatalog] = useState(false)

  const [crops, setCrops] = useState([])
  const [loadingCrops, setLoadingCrops] = useState(false)
  // Options for dropdowns
  const [cropOptions, setCropOptions] = useState([])
  const [farmOptions, setFarmOptions] = useState([])
  const [itemOptions, setItemOptions] = useState([])
  const [units, setUnits] = useState([])

  // Filters
  const [selectedFarm, setSelectedFarm] = useState('')
  const [selectedCrop, setSelectedCrop] = useState('')

  // Form State
  const initialFormState = {
    farm: '',
    crop: '',
    item: '',
    is_primary: false,
    notes: '',
    quality_grade: '',
    packing_type: '',
    reference_price: '',
    pack_size: '',
    pack_uom: '',
    units: [createUnitRow({ is_default: true, multiplier: '1' })],
  }
  const [form, setForm] = useState(initialFormState)
  const [submitting, setSubmitting] = useState(false)

  // Edit State
  const [editingProduct, setEditingProduct] = useState(null)
  const [editingProductSaving, setEditingProductSaving] = useState(false)

  // 1. Load Static Data (Units, Items)
  const loadStaticData = useCallback(async () => {
    try {
      try {
        const unitsRes = await api.get('/units/')
        setUnits(asList(unitsRes.data))
      } catch (e) {
        console.error('Error loading units', e)
        toast.error('فشل تحميل وحدات القياس')
      }

      try {
        const itemsRes = await api.get('/items/?group=Yield')
        setItemOptions(asList(itemsRes.data))
      } catch (e) {
        console.error('Error loading items', e)
        toast.error('فشل تحميل الأصناف')
      }
    } catch (error) {
      console.error('Error loading static data', error)
      toast.error('فشل تحميل البيانات الأساسية')
    }
  }, [])

  // 2. Load Crops
  const loadCrops = useCallback(async () => {
    try {
      setLoadingCrops(true)
      const cached = localStorage.getItem('harvestCrops')
      if (cached) {
        const parsed = JSON.parse(cached)
        const cachedList = asList(parsed)
        setCrops(cachedList)
        setCropOptions(cachedList) // Initially all
      }

      const response = await api.get('/crops/')
      const data = asList(response.data)
      setCrops(data)
      setCropOptions(data)
      localStorage.setItem('harvestCrops', JSON.stringify(data))
    } catch (error) {
      console.error('Error loading crops:', error)
      toast.error('تعذر تحميل قائمة المحاصيل، يرجى التحديث والمحاولة.')
    } finally {
      setLoadingCrops(false)
    }
  }, [])

  // 3. Load Catalog
  const loadCatalog = useCallback(async () => {
    try {
      setLoadingCatalog(true)
      let query = []
      if (selectedFarm) query.push(`farm_id=${selectedFarm}`)
      if (selectedCrop) query.push(`crop_id=${selectedCrop}`)

      // [Agri-Guardian] Default to selectedFarmId from context if no manual filter
      if (!selectedFarm && selectedFarmId) {
        query.push(`farm_id=${selectedFarmId}`)
      }

      const queryString = query.length ? `?${query.join('&')}` : ''
      const res = await api.get(`/harvest-product-catalog/${queryString}`)

      const data = asList(res.data)
      setCatalog(data)

      // Extract unique farms for filter
      const uniqueFarms = {}
      data.forEach((p) => {
        if (p?.farm_id) {
          uniqueFarms[p.farm_id] = { id: p.farm_id, name: p.farm_name || `مزرعة #${p.farm_id}` }
        }
      })
      setFarmOptions(Object.values(uniqueFarms))
    } catch (error) {
      console.error('Error loading catalog:', error)
      toast.error('تعذر جلب بيانات المنتجات، تأكد من الاتصال بالشبكة.')
    } finally {
      setLoadingCatalog(false)
    }
  }, [selectedFarm, selectedCrop, selectedFarmId])

  // 4. Initial Load
  useEffect(() => {
    loadStaticData()
    loadCrops()
  }, [loadStaticData, loadCrops])

  useEffect(() => {
    loadCatalog()
  }, [loadCatalog])

  // Set default farm in form when context changes
  useEffect(() => {
    if (selectedFarmId) {
      setForm((prev) => ({ ...prev, farm: selectedFarmId }))
      setSelectedFarm(selectedFarmId) // Auto-filter by current farm
    }
  }, [selectedFarmId])

  // Form Handlers
  const addFormUnit = () => {
    setForm((prev) => ({
      ...prev,
      units: [...prev.units, createUnitRow()],
    }))
  }

  const removeFormUnit = (index) => {
    setForm((prev) => {
      const next = prev.units.filter((_, i) => i !== index)
      return { ...prev, units: ensureDefaultUnitSelection(next) }
    })
  }

  const updateFormUnit = (index, field, value) => {
    setForm((prev) => {
      const next = [...prev.units]
      next[index] = { ...next[index], [field]: value }
      return { ...prev, units: next }
    })
  }

  const markFormDefaultUnit = (index) => {
    setForm((prev) => {
      const next = prev.units.map((u, i) => ({ ...u, is_default: i === index }))
      return { ...prev, units: next }
    })
  }

  const resetForm = () => {
    setForm({
      ...initialFormState,
      farm: selectedFarmId || '',
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.crop || !form.item || !form.farm) {
      toast.error('يرجى اختيار المزرعة، المحصول، والمنتج قبل الإرسال.')
      return
    }
    if (!itemOptions.length) {
      toast.error('لا توجد أصناف Yield متاحة للربط حالياً.')
      return
    }
    const selectedItem = itemOptions.find((item) => String(item.id) === String(form.item))
    if (!selectedItem) {
      toast.error('الصنف المحدد غير متاح. يرجى تحديث الصفحة وإعادة المحاولة.')
      return
    }
    setSubmitting(true)
    try {
      const payload = prepareProductPayload(form, { includeIdentifiers: true })
      const idempotencyKey = uuidv4()
      await api.post('/crop-products/', payload, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      })

      const itemName = selectedItem.name || ''
      toast.success(TEXT.successCreate(itemName))
      resetForm()
      loadCatalog()
    } catch (error) {
      console.error('Submit error', error)
      const message = parseApiErrorMessage(error, 'فشل إضافة منتج الحصاد.')
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  // Delete
  const handleDelete = async (record) => {
    if (!window.confirm(TEXT.deleteConfirmMessage(record.item_name))) return
    try {
      await api.delete(`/crop-products/${record.product_id}/`)
      toast.success(TEXT.successDelete(record.item_name))
      loadCatalog()
    } catch (error) {
      toast.error('فشل الحذف')
    }
  }

  // Edit Logic
  const startEditingProduct = (record) => {
    setEditingProduct({
      id: record.product_id,
      is_primary: record.is_primary,
      notes: record.notes || '',
      quality_grade: record.quality_grade || '',
      packing_type: record.packing_type || '',
      reference_price: record.reference_price || '',
      pack_size: record.pack_size || '',
      pack_uom: record.pack_uom || '',
      units: (record.units || []).map((u) => ({
        id: u.id,
        unit: u.unit,
        multiplier: u.multiplier,
        uom: u.uom || '',
        is_default: u.is_default,
      })),
    })
  }

  const cancelEditingProduct = () => {
    setEditingProduct(null)
  }

  const handleEditingProductChange = (field, value) => {
    setEditingProduct((prev) => ({ ...prev, [field]: value }))
  }

  // Edit Unit Handlers
  const addEditingUnit = () => {
    setEditingProduct((prev) => ({
      ...prev,
      units: [...prev.units, createUnitRow()],
    }))
  }

  const removeEditingUnit = (index) => {
    setEditingProduct((prev) => {
      const next = prev.units.filter((_, i) => i !== index)
      return { ...prev, units: ensureDefaultUnitSelection(next) }
    })
  }

  const updateEditingUnit = (index, field, value) => {
    setEditingProduct((prev) => {
      const next = [...prev.units]
      next[index] = { ...next[index], [field]: value }
      return { ...prev, units: next }
    })
  }

  const markEditingDefaultUnit = (index) => {
    setEditingProduct((prev) => {
      const next = prev.units.map((u, i) => ({ ...u, is_default: i === index }))
      return { ...prev, units: next }
    })
  }

  const saveEditingProduct = async () => {
    if (!editingProduct) return
    setEditingProductSaving(true)
    try {
      const payload = prepareProductPayload(editingProduct, { includeIdentifiers: false })
      const idempotencyKey = uuidv4()
      await api.patch(`/crop-products/${editingProduct.id}/`, payload, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      })
      toast.success('تم التحديث بنجاح')
      setEditingProduct(null)
      loadCatalog()
    } catch (error) {
      console.error(error)
      const message = parseApiErrorMessage(error, 'فشل تحديث منتج الحصاد.')
      toast.error(`فشل التحديث: ${message}`)
    } finally {
      setEditingProductSaving(false)
    }
  }

  return {
    catalog,
    loadingCatalog,
    crops,
    loadingCrops,
    cropOptions,
    farmOptions,
    itemOptions,
    units,
    selectedFarm,
    setSelectedFarm,
    selectedCrop,
    setSelectedCrop,
    form,
    setForm,
    submitting,
    handleSubmit,
    resetForm,
    handleDelete,
    // Helpers
    addFormUnit,
    removeFormUnit,
    updateFormUnit,
    markFormDefaultUnit,
    // Edit
    editingProduct,
    startEditingProduct,
    cancelEditingProduct,
    handleEditingProductChange,
    saveEditingProduct,
    editingProductSaving,
    addEditingUnit,
    removeEditingUnit,
    updateEditingUnit,
    markEditingDefaultUnit,
  }
}
