import { useEffect, useMemo, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'
import { api, BiologicalAssetCohorts, TreeInventorySummary } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ToastProvider'
import { useTreeCensusOffline, IDB_KEYS } from '../hooks/useTreeCensusOffline'

// [Agri-Guardian] Local format helpers
const formatNumber = (num, decimals = 0) => {
  if (num == null) return '-'
  return Number(num).toLocaleString('ar-EG', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const d = new Date(dateString)
  if (isNaN(d)) return dateString
  return new Intl.DateTimeFormat('ar-EG', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(d)
}

const STATUS_CONFIG_MAP = {
  JUVENILE: {
    ar: 'غير منتجة (نمو)',
    color: 'text-amber-600',
    bg: 'bg-amber-100 dark:bg-amber-900/30',
  },
  PRODUCTIVE: {
    ar: 'منتجة (طرح)',
    color: 'text-emerald-600',
    bg: 'bg-emerald-100 dark:bg-emerald-900/30',
  },
  SICK: {
    ar: 'مريضة / مصابة',
    color: 'text-orange-600',
    bg: 'bg-orange-100 dark:bg-orange-900/30',
  },
  RENEWING: { ar: 'خلفة (تجديد)', color: 'text-blue-600', bg: 'bg-blue-100 dark:bg-blue-900/30' },
  EXCLUDED: { ar: 'مستبعدة / ميتة', color: 'text-red-500', bg: 'bg-red-100 dark:bg-red-900/30' },
}

export default function TreeCensusPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const auth = useAuth()

  // [Agri-Guardian] Offline-First Infrastructure Hook (AGENTS.md §18)
  const {
    isOnline,
    isOffline,
    offlineQueue,
    syncing,
    onReconnect,
    queuePush,
    queueFlush,
    fetchWithCache,
  } = useTreeCensusOffline()

  const [farms, setFarms] = useState([])
  const [filterLocations, setFilterLocations] = useState([])
  const [formLocations, setFormLocations] = useState([])
  const [crops, setCrops] = useState([])
  const [filterVarieties, setFilterVarieties] = useState([])
  const [formVarieties, setFormVarieties] = useState([])

  const [cohorts, setCohorts] = useState([])
  const [locationVarietySummary, setLocationVarietySummary] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [summaryError, setSummaryError] = useState('')

  const [filters, setFilters] = useState({
    farm: '',
    location_id: '',
    crop_id: '',
    variety_id: '',
    status: '',
  })

  // Modal State for New Cohort
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState({
    farm: '',
    location: '',
    crop: '',
    variety: '',
    status: 'JUVENILE',
    quantity: '',
    batch_name: '',
    planted_date: new Date().toISOString().split('T')[0],
    source: '',
    expected_productive_date: '',
    notes: '',
    parent_cohort: '',
  })

  // Transition Modal State
  const [isTransitionModalOpen, setIsTransitionModalOpen] = useState(false)
  const [transitionCohort, setTransitionCohort] = useState(null)
  const [transitionData, setTransitionData] = useState({
    target_status: '',
    quantity: '',
    notes: '',
  })

  // [AGRI-GUARDIAN] Mass Casualty Modal State (Axis 18)
  const [isMassCasualtyModalOpen, setIsMassCasualtyModalOpen] = useState(false)
  const [massCasualtyCohort, setMassCasualtyCohort] = useState(null)
  const [massCasualtyData, setMassCasualtyData] = useState({
    cause: 'DISEASE',
    quantity_lost: '',
    estimated_fair_value_per_unit: '',
    reason: '',
  })

  // [Best-Practice] Inline Delete Confirmation Modal State
  const [confirmDeleteCohort, setConfirmDeleteCohort] = useState(null) // cohort to delete, or null
  const [deleting, setDeleting] = useState(false)

  // Add Variety Modal State
  const [isAddVarietyModalOpen, setIsAddVarietyModalOpen] = useState(false)
  const [newVarietyData, setNewVarietyData] = useState({ name: '', notes: '' })

  const filteredPotentialParents = useMemo(() => {
    return cohorts.filter(
      (c) =>
        String(c.farm) === String(formData.farm) &&
        String(c.location) === String(formData.location) &&
        String(c.crop) === String(formData.crop),
    )
  }, [cohorts, formData.farm, formData.location, formData.crop])

  const currentFarm = useMemo(() => {
    return farms.find(f => String(f.id) === String(filters.farm))
  }, [filters.farm, farms])
  const canAdjustTreeInventory =
    auth.isAdmin || auth.isSuperuser || auth.canChangeModel?.('locationtreestock')

  const enableTreeGIS = currentFarm?.settings?.enable_tree_gis_zoning === true
  const enableBulkTransition = currentFarm?.settings?.enable_bulk_cohort_transition === true
  const [viewMode, setViewMode] = useState('grid') // 'grid' | 'gis'

  // Bulk Transition State
  const [selectedCohorts, setSelectedCohorts] = useState([])
  const [isBulkTransitionModalOpen, setIsBulkTransitionModalOpen] = useState(false)
  const [bulkTransitionData, setBulkTransitionData] = useState({
    target_status: '',
    notes: '',
  })

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedCohorts(cohorts.map((c) => c.id))
    } else {
      setSelectedCohorts([])
    }
  }

  const handleSelectCohort = (id) => {
    if (selectedCohorts.includes(id)) {
      setSelectedCohorts(selectedCohorts.filter((cId) => cId !== id))
    } else {
      setSelectedCohorts([...selectedCohorts, id])
    }
  }

  const handleBulkTransitionChange = (e) => {
    const { name, value } = e.target
    setBulkTransitionData((prev) => ({ ...prev, [name]: value }))
  }

  const handleBulkTransitionSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = { ...bulkTransitionData, cohort_ids: selectedCohorts }
      await BiologicalAssetCohorts.bulkTransition(payload, uuidv4())
      toast.success(`تم نقل ${selectedCohorts.length} دفعة بنجاح`)
      setIsBulkTransitionModalOpen(false)
      setSelectedCohorts([])
      setBulkTransitionData({ target_status: '', notes: '' })
      
      // Refresh Data
      const resp = await BiologicalAssetCohorts.list(filters)
      setCohorts(resp.data?.results || resp.data || [])
      
      if (filters.location_id) {
        const aggr = await BiologicalAssetCohorts.aggregateByLocation(filters)
        setLocationVarietySummary([aggr.data])
      }
    } catch (err) {
      console.error('Failed to submit bulk transition:', err)
      const data = err?.response?.data
      let errValue = data?.detail || data?.non_field_errors?.[0] || data?.message
      if (!errValue && data && typeof data === 'object') {
        errValue = Object.values(data).flat().filter(i => typeof i === 'string').join(' | ')
      }
      toast.error(errValue || 'حدث خطأ غير متوقع أثناء الحفظ')
    } finally {
      setSaving(false)
    }
  }


  // [Offline-First] Cache base data (farms, crops) with IndexedDB fallback
  useEffect(() => {
    const fetchBaseData = async () => {
      const farmsResult = await fetchWithCache(IDB_KEYS.FARMS, async () => {
        const res = await api.get('/farms/')
        return res.data?.results || res.data || []
      })
      if (farmsResult.data) setFarms(farmsResult.data)
      if (farmsResult.fromCache && farmsResult.error)
        console.info('[TreeCensus] Farms loaded from cache')

      const cropsResult = await fetchWithCache(IDB_KEYS.CROPS, async () => {
        const res = await api.get('/crops/')
        return res.data?.results || res.data || []
      })
      if (cropsResult.data) setCrops(cropsResult.data)
      if (cropsResult.fromCache && cropsResult.error)
        console.info('[TreeCensus] Crops loaded from cache')

      if (!farmsResult.data && !cropsResult.data) {
        toast.error('تعذر تحميل البيانات الأساسية ولا توجد نسخة مخبأة')
      }
    }
    fetchBaseData()
  }, [toast, fetchWithCache])

  // [Offline-First] Load locations for filters
  useEffect(() => {
    const fetchFilterLocations = async () => {
      if (!filters.farm) {
        setFilterLocations([])
        return
      }
      const cacheKey = `${IDB_KEYS.LOCATIONS_PREFIX}filter-${filters.farm}`
      const result = await fetchWithCache(cacheKey, async () => {
        const res = await api.get('/locations/', { params: { farm_id: filters.farm } })
        return res.data?.results || res.data || []
      })
      setFilterLocations(result.data || [])
    }
    fetchFilterLocations()
  }, [filters.farm, fetchWithCache])

  // [Offline-First] Load locations for form
  useEffect(() => {
    const fetchFormLocations = async () => {
      if (!formData.farm) {
        setFormLocations([])
        return
      }
      const cacheKey = `${IDB_KEYS.LOCATIONS_PREFIX}form-${formData.farm}`
      const result = await fetchWithCache(cacheKey, async () => {
        const res = await api.get('/locations/', { params: { farm_id: formData.farm } })
        return res.data?.results || res.data || []
      })
      setFormLocations(result.data || [])
    }
    fetchFormLocations()
  }, [formData.farm, fetchWithCache])

  // [Offline-First] Load varieties for filters
  useEffect(() => {
    const fetchFilterVarieties = async () => {
      if (!filters.crop_id) {
        setFilterVarieties([])
        return
      }
      
      const cacheKey = `${IDB_KEYS.VARIETIES_PREFIX}filter-${filters.crop_id}`
      const result = await fetchWithCache(cacheKey, async () => {
        const res = await api.get('/crop-varieties/', { params: { crop_id: filters.crop_id } })
        return res.data?.results || res.data || []
      })
      
      const allCropVarieties = result.data || []
      
      // [AGRI-GUARDIAN] Dynamic location-based filtering from inventory
      if (filters.location_id) {
        const { getAvailableVarietiesForLocation } = await import('../utils/agronomyUtils.js')
        const farmContextMock = {
          tree_census: cohorts,
          varieties: allCropVarieties
        }
        const filtered = getAvailableVarietiesForLocation(filters.location_id, farmContextMock)
        setFilterVarieties(filtered)
      } else {
        setFilterVarieties(allCropVarieties)
      }
    }
    fetchFilterVarieties()
  }, [filters.crop_id, filters.location_id, cohorts, fetchWithCache])

  // [Offline-First] Load varieties for form
  useEffect(() => {
    const fetchFormVarieties = async () => {
      if (!formData.crop) {
        setFormVarieties([])
        return
      }
      const cacheKey = `${IDB_KEYS.VARIETIES_PREFIX}form-${formData.crop}`
      const result = await fetchWithCache(cacheKey, async () => {
        const res = await api.get('/crop-varieties/', { params: { crop_id: formData.crop } })
        return res.data?.results || res.data || []
      })
      setFormVarieties(result.data || [])
    }
    fetchFormVarieties()
  }, [formData.crop, fetchWithCache])

  // [Offline-First] Fetch cohorts with cache fallback + merge pending queue
  const fetchCohorts = useCallback(async () => {
    setLoading(true)
    setError('')
    setSummaryError('')
    const cacheKey = `${IDB_KEYS.COHORTS_PREFIX}${filters.farm}-${filters.location_id}-${filters.crop_id}-${filters.variety_id}-${filters.status}`

    const result = await fetchWithCache(cacheKey, async () => {
      const resp = await BiologicalAssetCohorts.list(filters)
      return resp.data?.results || resp.data || []
    })

    let serverCohorts = result.data || []

    // [Agri-Guardian] Merge offline queue items into the display
    // so field engineers see their pending entries while offline
    const pendingForCurrentView = offlineQueue.filter((item) => {
      const p = item.payload || item
      return (
        (!filters.farm || String(p.farm) === String(filters.farm)) &&
        (!filters.location_id || String(p.location) === String(filters.location_id)) &&
        (!filters.crop_id || String(p.crop) === String(filters.crop_id))
      )
    })
    const mergedCohorts = [...pendingForCurrentView, ...serverCohorts]

    setCohorts(mergedCohorts)
    if (filters.farm) {
      const selectedLocationIds = filters.location_id
        ? [String(filters.location_id)]
        : filterLocations.map((location) => String(location.id))
      if (selectedLocationIds.length > 0) {
        try {
          const summaryResp = await TreeInventorySummary.locationVarietySummary({
            farm_id: filters.farm,
            crop_id: filters.crop_id || undefined,
            variety_id: filters.variety_id || undefined,
            location_ids: selectedLocationIds.join(','),
          })
          setLocationVarietySummary(summaryResp.data?.results || [])
        } catch (_summaryErr) {
          setLocationVarietySummary([])
          setSummaryError('تعذر تحميل ملخص المطابقة بين الجرد والدفعات.')
        }
      } else {
        setLocationVarietySummary([])
      }
    } else {
      setLocationVarietySummary([])
    }
    if (result.error) setError(result.error)
    setLoading(false)
  }, [filterLocations, filters, fetchWithCache, offlineQueue])

  useEffect(() => {
    fetchCohorts()
  }, [fetchCohorts])

  // [Offline-First] Sync queue via hook (sequential FIFO per AGENTS.md Idempotency)
  const syncOfflineQueue = useCallback(async () => {
    const syncCount = await queueFlush((payload) => BiologicalAssetCohorts.create(payload))
    if (syncCount > 0) {
      toast.success(`تم مزامنة ${syncCount} دفعة غرس مع السيرفر بنجاح`)
      fetchCohorts()
    }
  }, [queueFlush, toast, fetchCohorts])

  // [Offline-First] Auto-sync when network reconnects
  useEffect(() => {
    const unsubscribe = onReconnect(() => {
      if (offlineQueue.length > 0) {
        console.info(
          '[TreeCensus] Network restored — auto-syncing',
          offlineQueue.length,
          'pending cohorts',
        )
        syncOfflineQueue()
      }
      // Also refresh data from server
      fetchCohorts()
    })
    return unsubscribe
  }, [onReconnect, offlineQueue.length, syncOfflineQueue, fetchCohorts])

  const handleFilterChange = (e) => {
    const { name, value } = e.target
    setFilters((prev) => {
      const updates = { [name]: value }
      if (name === 'farm') updates.location_id = ''
      if (name === 'crop_id') updates.variety_id = ''
      return { ...prev, ...updates }
    })
  }

  const handleFormChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => {
      const updates = { [name]: value }
      if (name === 'farm') updates.location = ''
      if (name === 'crop') updates.variety = ''
      return { ...prev, ...updates }
    })
  }

  const handleTransitionChange = (e) => {
    const { name, value } = e.target
    setTransitionData((prev) => ({ ...prev, [name]: value }))
  }

  const handleNewVarietyChange = (e) => {
    setNewVarietyData((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleAddVarietySubmit = async (e) => {
    e.preventDefault()
    if (!newVarietyData.name.trim()) return
    try {
      setSaving(true)
      const res = await api.post('/crop-varieties/', {
        crop: formData.crop,
        name: newVarietyData.name,
        notes: newVarietyData.notes || '',
      })
      const newVar = res.data
      
      setFormVarieties((prev) => {
        if (prev.find((v) => v.id === newVar.id)) return prev;
        return [...prev, newVar];
      })
      setFormData((prev) => ({ ...prev, variety: newVar.id }))
      setFilterVarieties((prev) => {
        if (prev.find((v) => v.id === newVar.id)) return prev;
        return [...prev, newVar];
      })
      
      setIsAddVarietyModalOpen(false)
      setNewVarietyData({ name: '', notes: '' })
      toast.success('تمت إضافة الصنف بنجاح')
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'حدث خطأ أثناء إضافة الصنف')
    } finally {
      setSaving(false)
    }
  }

  const handleTransitionSubmit = async (e) => {
    e.preventDefault()
    if (!isOnline) {
      toast.error(
        'عمليات تغيير الحالة الرأسمالية أو الإعدام تتطلب اتصالاً بالإنترنت لضمان سلامة السجلات المالية.',
      )
      return
    }

    setSaving(true)
    try {
      const idempotencyKey = uuidv4()
      const payload = {
        target_status: transitionData.target_status,
        quantity: transitionData.quantity,
        notes: transitionData.notes,
      }

      const res = await BiologicalAssetCohorts.transition(
        transitionCohort.id,
        payload,
        idempotencyKey,
      )
      toast.success(res.data?.detail || 'تم تنفيذ العملية بنجاح')
      setIsTransitionModalOpen(false)
      fetchCohorts()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ أثناء حفظ التغييرات')
    } finally {
      setSaving(false)
    }
  }

  const openTransitionModal = (cohort) => {
    setTransitionCohort(cohort)
    setTransitionData({
      target_status: '',
      quantity: '',
      notes: '',
    })
    setIsTransitionModalOpen(true)
  }

  // [AGRI-GUARDIAN] Launchpad Implementation (100/100 Master Plan)
  // This connects the Asset Registry directly to the Daily Log Documentary Cycle.
  const handleLaunchpadAction = (cohort, actionType) => {
    const launchpadData = {
      farm: String(cohort.farm?.id || cohort.farm || ''),
      locations: [String(cohort.location?.id || cohort.location || '')],
      crop: String(cohort.crop?.id || cohort.crop || ''),
      variety: String(cohort.variety?.id || cohort.variety || ''),
      // Metadata for DailyLog to auto-set the Task and special UI logic
      launchpadMetaData: {
        cohort_id: cohort.id,
        action: actionType,
        batch_name: cohort.batch_name,
      },
    }

    if (actionType === 'PRUNE') {
      launchpadData.requestedArchetype = 'PERENNIAL_SERVICE'
      launchpadData.requestedTaskName = 'تقليم' // Legacy fallback
      // Auto-populate the first service row for the specific cohort
      launchpadData.serviceRows = [
        {
          key: uuidv4(),
          varietyId: String(cohort.variety?.id || cohort.variety || ''),
          serviceCount: String(cohort.quantity || '0'),
          notes: `خدمة آلية للدفعة #${cohort.id} (${cohort.batch_name || '-'})`,
        },
      ]
    }

    if (actionType === 'DIE_OFF') {
      launchpadData.requestedArchetype = 'BIOLOGICAL_ADJUSTMENT'
      launchpadData.requestedTaskName = 'موت' // Legacy fallback
      launchpadData.tree_count_delta = -1 // Default to 1 tree death
      launchpadData.variety = String(cohort.variety?.id || cohort.variety || '')
    }

    if (actionType === 'RATOON') {
      launchpadData.requestedArchetype = 'PERENNIAL_SERVICE'
      launchpadData.requestedTaskName = 'تربية خلفات / إحلال' // Legacy fallback
    }

    navigate('/daily-log', { state: { launchpadData } })
  }

  // [AGRI-GUARDIAN] Mass Casualty Handlers (Axis 18)
  const openMassCasualtyModal = (cohort) => {
    setMassCasualtyCohort(cohort)
    setMassCasualtyData({
      cause: 'DISEASE',
      quantity_lost: cohort.quantity, // Default to full cohort for mass casualty
      estimated_fair_value_per_unit: '',
      reason: '',
    })
    setIsMassCasualtyModalOpen(true)
  }

  const handleMassCasualtyChange = (e) => {
    const { name, value } = e.target
    setMassCasualtyData((prev) => ({ ...prev, [name]: value }))
  }

  const handleMassCasualtySubmit = async () => {
    if (!massCasualtyCohort) return
    setSaving(true)
    try {
      const payload = {
        farm_id: massCasualtyCohort.farm?.id || massCasualtyCohort.farm,
        cause: massCasualtyData.cause,
        reason: massCasualtyData.reason,
        cohort_entries: [
          {
            cohort_id: massCasualtyCohort.id,
            quantity_lost: Number(massCasualtyData.quantity_lost),
            estimated_fair_value_per_unit: massCasualtyData.estimated_fair_value_per_unit,
          },
        ],
      }

      // Axis 2: Local Idempotency Key
      const idKey = uuidv4()

      await api.post('/mass-casualty-writeoff/', payload, {
        headers: {
          'X-Idempotency-Key': idKey,
        },
      })

      toast.success('تم تسجيل الشطب الجماعي واعتماده برمجياً بنجاح.')
      setIsMassCasualtyModalOpen(false)
      fetchCohorts()
    } catch (err) {
      console.error(err)
      toast.error('فشل تسجيل الشطب الجماعي. تحقق من الصلاحيات والميزانية.')
    } finally {
      setSaving(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)

    if (!isOnline) {
      // [OFFLINE MODE] Optimistic Save via hook queue
      const displayCohort = {
        id: `temp-${uuidv4()}`,
        is_offline: true,
        payload: { ...formData },
        farm_id: formData.farm,
        location: formLocations.find((l) => String(l.id) === String(formData.location)),
        crop: crops.find((c) => String(c.id) === String(formData.crop)),
        variety: formVarieties.find((v) => String(v.id) === String(formData.variety)),
        batch_name: formData.batch_name,
        quantity: formData.quantity,
        planted_date: formData.planted_date,
        status: formData.status,
      }

      await queuePush(displayCohort)

      toast.success('تم الحفظ محلياً (الشبكة غير متصلة). سيتم المزامنة تلقائياً عند عودة الاتصال.')
      setIsModalOpen(false)
      setSaving(false)

      // Optimistic update to UI — pending items also merged via fetchCohorts
      setCohorts((prev) => [displayCohort, ...prev])
      return
    }

    try {
      await BiologicalAssetCohorts.create(formData)
      toast.success('تم تسجيل دفعة الغرس بنجاح')
      setIsModalOpen(false)
      fetchCohorts()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'تعذر تسجيل الدفعة')
    } finally {
      setSaving(false)
    }
  }

  // [Best-Practice] Open the inline confirmation modal instead of window.confirm
  const handleDeleteCohort = (cohort) => {
    if (String(cohort.id).startsWith('temp-')) {
      toast.error('لا يمكن حذف دفعة معلقة محلياً من هذه الواجهة. الرجاء الانتظار حتى تتم المزامنة.')
      return
    }
    setConfirmDeleteCohort(cohort)
  }

  // [Best-Practice] Execute the actual DELETE with optimistic UI update + rollback
  const executeDeleteCohort = async () => {
    const cohort = confirmDeleteCohort
    if (!cohort) return

    setDeleting(true)
    // Optimistic removal from UI
    setCohorts((prev) => prev.filter((c) => c.id !== cohort.id))
    setConfirmDeleteCohort(null)

    try {
      await BiologicalAssetCohorts.remove(cohort.id)
      toast.success(`تم حذف الدفعة "${cohort.batch_name}" بنجاح.`)
    } catch (err) {
      // Rollback optimistic removal
      setCohorts((prev) => [cohort, ...prev])
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'تعذر حذف الدفعة. تأكد من صلاحياتك أو وجود ارتباطات بعمليات أخرى.'
      toast.error(msg)
    } finally {
      setDeleting(false)
    }
  }

  const openModal = () => {
    setFormData((prev) => ({
      ...prev,
      farm: filters.farm,
      location: filters.location_id,
      crop: filters.crop_id,
      variety: filters.variety_id,
      quantity: '',
      batch_name: '',
      notes: '',
    }))
    setIsModalOpen(true)
  }

  const openInventoryAdjustment = () => {
    navigate('/tree-inventory', {
      state: {
        openAdjustment: true,
        adjustmentPrefill: {
          farm: filters.farm || '',
          location_id: filters.location_id || '',
          crop_id: filters.crop_id || '',
          variety_id: filters.variety_id || '',
        },
      },
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-6 space-y-6">
      {/* Premium Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-4xl font-extrabold bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-500 bg-clip-text text-transparent flex items-center gap-3">
            جرد الدفعات الشجرية
            {isOffline && (
              <span className="text-xs px-2.5 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-400 rounded-full font-bold flex items-center gap-2 border border-amber-200 dark:border-amber-800">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                وضع عدم الاتصال
              </span>
            )}
          </h1>
          <p className="text-gray-500 dark:text-slate-400">
            عرض تفصيلي للجرد الشجري وربط الرصيد الجاري بهيكل الدفعات الحية لكل موقع وصنف.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          {canAdjustTreeInventory && (
            <button
              onClick={openInventoryAdjustment}
              className="rounded-xl flex items-center justify-center gap-2 bg-white px-6 py-3 text-sm font-bold text-emerald-700 shadow-xl transition-all hover:scale-[1.02] hover:shadow-emerald-500/20 active:scale-95 border border-emerald-200"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 4v16m8-8H4"
                />
              </svg>
              تسجيل رصيد فعلي
            </button>
          )}
          {offlineQueue.length > 0 && isOnline && (
            <button
              onClick={syncOfflineQueue}
              disabled={syncing}
              className="rounded-xl flex items-center justify-center gap-2 bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-3 text-sm font-bold text-white shadow-xl transition-all hover:scale-[1.02] hover:shadow-amber-500/30 active:scale-95 disabled:opacity-50 border border-amber-400"
            >
              {syncing ? (
                <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
              ) : (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              )}
              مزامنة ({offlineQueue.length})
            </button>
          )}
          {offlineQueue.length > 0 && isOffline && (
            <span className="rounded-xl flex items-center justify-center gap-2 bg-amber-100 dark:bg-amber-900/40 px-4 py-3 text-xs font-semibold text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
              {offlineQueue.length} دفعة معلقة للمزامنة
            </span>
          )}
          <button
            onClick={openModal}
            className="rounded-xl flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-3 text-sm font-bold text-white shadow-xl transition-all hover:scale-[1.02] hover:shadow-emerald-500/30 active:scale-95 border border-emerald-500"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 4v16m8-8H4"
              />
            </svg>
            إضافة دفعة غرس جديدة
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-gray-100 dark:border-slate-700 p-5">
        <div className="grid gap-4 md:grid-cols-5">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">
              المزرعة
            </label>
            <select
              name="farm"
              value={filters.farm}
              onChange={handleFilterChange}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">-- الكل --</option>
              {farms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">
              الموقع الميداني (Location)
            </label>
            <select
              name="location_id"
              value={filters.location_id}
              onChange={handleFilterChange}
              disabled={!filters.farm}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm disabled:opacity-50"
            >
              <option value="">-- الكل --</option>
              {filterLocations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">
              المحصول
            </label>
            <select
              name="crop_id"
              value={filters.crop_id}
              onChange={handleFilterChange}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm"
            >
              <option value="">-- الكل --</option>
              {crops.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">الصنف</label>
            <select
              name="variety_id"
              value={filters.variety_id}
              onChange={handleFilterChange}
              disabled={!filters.crop_id}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm disabled:opacity-50"
            >
              <option value="">-- الكل --</option>
              {filterVarieties.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">
              الحالة الإنتاجية
            </label>
            <select
              name="status"
              value={filters.status}
              onChange={handleFilterChange}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm"
            >
              <option value="">-- جميع الحالات --</option>
              <option value="JUVENILE">غير منتجة (نمو)</option>
              <option value="PRODUCTIVE">منتجة (طرح)</option>
              <option value="SICK">مريضة</option>
              <option value="EXCLUDED">مستبعدة / خلع</option>
            </select>
          </div>
        </div>
      </div>

      {(summaryError || locationVarietySummary.length > 0) && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 dark:border-slate-700 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                ملخص المطابقة بين الجرد الجاري والدفعات
              </h2>
              <p className="text-xs text-gray-500 dark:text-slate-400">
                الرصيد الجاري يعتمد على مخزون الموقع، والدفعات الحية تعرض هيكل الدفعات في الجرد الشجري.
              </p>
            </div>
          </div>
          {summaryError ? (
            <div className="p-5 text-sm text-amber-700 dark:text-amber-400">{summaryError}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-right text-sm">
                <thead className="bg-gray-50 dark:bg-slate-900/50 text-gray-600 dark:text-slate-300">
                  <tr>
                    <th className="px-5 py-3 font-semibold">الصنف</th>
                    <th className="px-5 py-3 font-semibold">الرصيد الجاري</th>
                    <th className="px-5 py-3 font-semibold">إجمالي الدفعات الحية</th>
                    <th className="px-5 py-3 font-semibold">الفجوة</th>
                    <th className="px-5 py-3 font-semibold">التغطية بالمواقع</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700/60">
                  {locationVarietySummary.map((entry) => {
                    const locationNames = Array.isArray(entry.location_ids)
                      ? entry.location_ids
                          .map((locationId) => {
                            const match = filterLocations.find(
                              (location) => String(location.id) === String(locationId),
                            )
                            return match?.name || `الموقع ${locationId}`
                          })
                          .join('، ')
                      : '-'
                    return (
                      <tr key={entry.variety_id}>
                        <td className="px-5 py-3 font-semibold text-gray-800 dark:text-slate-200">
                          {entry.variety_name}
                        </td>
                        <td className="px-5 py-3 text-emerald-700 dark:text-emerald-300 font-bold">
                          {formatNumber(entry.current_tree_count_total)}
                        </td>
                        <td className="px-5 py-3 text-blue-700 dark:text-blue-300 font-bold">
                          {formatNumber(entry.cohort_alive_total)}
                        </td>
                        <td className="px-5 py-3">
                          {entry.has_reconciliation_gap ? (
                            <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                              فجوة: {formatNumber(entry.cohort_stock_delta)}
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                              متطابق
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-500 dark:text-slate-400">
                          {locationNames || '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal - Bulk Transition */}
      {isBulkTransitionModalOpen && selectedCohorts.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-800 w-full max-w-md rounded-2xl shadow-2xl border border-gray-100 dark:border-slate-700 flex flex-col">
            <div className="p-5 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-emerald-50 dark:bg-emerald-900/40 rounded-t-2xl">
              <h2 className="text-lg font-bold text-emerald-900 dark:text-emerald-100">نقل جماعي للحالات ({selectedCohorts.length} دفعة)</h2>
              <button
                disabled={saving}
                onClick={() => setIsBulkTransitionModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-white bg-white dark:bg-slate-700 dark:hover:bg-slate-600 rounded-full p-1 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-gray-50 dark:bg-slate-900/40 p-3 rounded-xl border border-gray-200 dark:border-slate-700">
                <p className="text-sm font-bold text-gray-800 dark:text-slate-200">
                  انتباه: سيتم نقل جميع الدفعات المحددة بالكامل إلى الحالة الجديدة.
                </p>
                <p className="text-xs text-gray-500 mt-1 dark:text-slate-400">
                  التجزئة الجزئية للدفعة لا تدعم في النقل الجماعي. الدفعات التي تكون في الحالة المطلوبة مسبقاً سيتم تخطيها.
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                  الحالة الجديدة المشتركة *
                </label>
                <select
                  name="target_status"
                  value={bulkTransitionData.target_status}
                  onChange={handleBulkTransitionChange}
                  required
                  className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                >
                  <option value="">اختر الحالة الانتقالية...</option>
                  <option value="JUVENILE">غير منتجة (في طور النمو)</option>
                  <option value="PRODUCTIVE">منتجة (طرح ثمار)</option>
                  <option value="SICK">مريضة</option>
                  <option value="RENEWING">تجديد خلفات (Ratooning)</option>
                  <option value="EXCLUDED" className="text-red-600 font-bold">إعدام أو نقص كلي</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                  ملاحظات
                  {bulkTransitionData.target_status === 'EXCLUDED' && (
                    <span className="text-red-500 text-xs mr-2">(إلزامي للتبليغ المجمع عن الفقد)</span>
                  )}
                </label>
                <textarea
                  name="notes"
                  rows="3"
                  required={bulkTransitionData.target_status === 'EXCLUDED'}
                  value={bulkTransitionData.notes}
                  onChange={handleBulkTransitionChange}
                  className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  placeholder="سبب النقل الجماعي..."
                ></textarea>
              </div>
            </div>

            <div className="p-5 border-t border-gray-100 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50 flex justify-end gap-3 rounded-b-2xl">
              <button
                disabled={saving}
                type="button"
                onClick={() => setIsBulkTransitionModalOpen(false)}
                className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-700 shadow-sm transition-colors"
              >
                إلغاء
              </button>
              <button
                disabled={
                  saving ||
                  !bulkTransitionData.target_status ||
                  (bulkTransitionData.target_status === 'EXCLUDED' && !bulkTransitionData.notes.trim())
                }
                onClick={handleBulkTransitionSubmit}
                type="button"
                className={`flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white shadow-md transition-colors rounded-xl disabled:opacity-50 ${
                  bulkTransitionData.target_status === 'EXCLUDED'
                    ? 'bg-red-600 hover:bg-red-700 disabled:bg-red-600'
                    : 'bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-600'
                }`}
              >
                {saving ? (
                  <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                ) : null}
                {bulkTransitionData.target_status === 'EXCLUDED' ? 'رفع بلاغات جماعية' : 'تطبيق النقل الجماعي'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Toggle (GIS vs Grid) */}
      {enableTreeGIS && (
        <div className="flex justify-end">
          <div className="bg-white dark:bg-slate-800 p-1 rounded-lg border border-gray-200 dark:border-slate-700 inline-flex shadow-sm">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors ${
                viewMode === 'grid'
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-400'
                  : 'text-gray-600 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700'
              }`}
            >
              شبكة البيانات (Grid)
            </button>
            <button
              onClick={() => setViewMode('gis')}
              className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors ${
                viewMode === 'gis'
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-400'
                  : 'text-gray-600 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700'
              }`}
            >
              المراقبة المكانية (GIS)
            </button>
          </div>
        </div>
      )}

      {/* View Area */}
      {viewMode === 'gis' && enableTreeGIS ? (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 shadow-sm overflow-hidden min-h-[500px] p-6 relative">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-emerald-400 via-teal-500 to-emerald-600"></div>
          <div className="flex flex-col items-center justify-center pt-20 pb-16 space-y-4">
            <div className="w-24 h-24 rounded-full bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
              <svg className="w-12 h-12 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-gray-800 dark:text-slate-200">الخريطة المكانية للأشجار (Tree GIS Heatmap)</h3>
            <p className="text-gray-500 dark:text-slate-400 max-w-lg text-center">
              هذه الواجهة مخصصة لعرض خرائط توزع الأصناف والكثافة الشجرية (Heatmap) مع إمكانية التحديد المكاني للمناطق التي تعاني من انخفاض الإنتاجية أو ارتفاع معدل الإصابات (Hotspots).
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl mt-8">
              <div className="bg-gray-50 dark:bg-slate-900/50 p-4 rounded-xl border border-gray-100 dark:border-slate-700">
                <div className="text-emerald-600 dark:text-emerald-400 font-bold mb-2 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-emerald-500"></span> الكثافة الشجرية
                </div>
                <p className="text-xs text-gray-500 dark:text-slate-400">توزيع الدفعات على المساحة الفعلية للمواقع.</p>
              </div>
              <div className="bg-gray-50 dark:bg-slate-900/50 p-4 rounded-xl border border-gray-100 dark:border-slate-700">
                <div className="text-amber-600 dark:text-amber-400 font-bold mb-2 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-amber-500"></span> البصمة الوراثية
                </div>
                <p className="text-xs text-gray-500 dark:text-slate-400">تتبع الخلفات (Ratoons) وتقارب الأجيال الشجرية.</p>
              </div>
              <div className="bg-gray-50 dark:bg-slate-900/50 p-4 rounded-xl border border-gray-100 dark:border-slate-700">
                <div className="text-red-500 font-bold mb-2 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-red-500"></span> بؤر الخطر
                </div>
                <p className="text-xs text-gray-500 dark:text-slate-400">تحديد نقاط الإصابات العالية للشطب الجماعي.</p>
              </div>
            </div>
            <button className="mt-6 px-6 py-2 bg-slate-800 dark:bg-slate-700 text-white rounded-lg shadow-md hover:bg-slate-700 transition" onClick={() => toast('سيتم تحميل مكون الخرائط 3D عما قريب.')}>
              تحميل الخريطة
            </button>
          </div>
        </div>
      ) : (
      <>
      {/* Cohorts Grid */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 shadow-sm overflow-hidden min-h-[400px]">
        {loading ? (
          <div className="p-8 flex justify-center text-emerald-600 pt-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600"></div>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">{error}</div>
        ) : cohorts.length === 0 ? (
          <div className="p-16 flex flex-col items-center justify-center text-gray-400 dark:text-slate-500">
            <svg
              className="w-16 h-16 mb-4 opacity-70"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.5"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
            <p className="text-lg font-medium">لا توجد سجلات مطابقة في دفتر الجرد</p>
            <p className="text-sm mt-1">جرب إزالة بعض الفلاتر للبحث بشكل أوسع.</p>
          </div>
        ) : (
          <div className="flex flex-col relative">
            {enableBulkTransition && selectedCohorts.length > 0 && (
              <div className="bg-emerald-50 dark:bg-emerald-900/30 border-b border-emerald-100 dark:border-emerald-800/50 p-3 flex justify-between items-center px-5 animate-in slide-in-from-top-2 duration-200 sticky top-0 z-10 shadow-sm">
                <div className="flex items-center gap-3 text-emerald-800 dark:text-emerald-300 font-bold text-sm">
                  <span className="flex items-center justify-center w-6 h-6 rounded-md bg-emerald-200 dark:bg-emerald-800 text-emerald-900 dark:text-emerald-100">
                    {selectedCohorts.length}
                  </span>
                  عناصر محددة
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setSelectedCohorts([])}
                    className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:text-emerald-800 dark:hover:text-emerald-200 hover:underline px-2"
                  >
                    إلغاء التحديد
                  </button>
                  <button
                    onClick={() => setIsBulkTransitionModalOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm text-xs font-bold transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    نقل مجمع للحالات
                  </button>
                </div>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-right text-sm">
                <thead className="bg-gray-50 dark:bg-slate-900/50 text-gray-600 dark:text-slate-300">
                  <tr>
                    {enableBulkTransition && (
                      <th className="px-5 py-4 w-12 text-center">
                        <input
                          type="checkbox"
                          checked={selectedCohorts.length === cohorts.length && cohorts.length > 0}
                          onChange={handleSelectAll}
                          className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                        />
                      </th>
                    )}
                    <th className="px-5 py-4 font-semibold">الموقع (Location)</th>
                    <th className="px-5 py-4 font-semibold">المحصول / الصنف</th>
                    <th className="px-5 py-4 font-semibold">رقم الدفعة (Cohort ID)</th>
                    <th className="px-5 py-4 font-semibold">العدد</th>
                    <th className="px-5 py-4 font-semibold">تاريخ الغرس</th>
                    <th className="px-5 py-4 font-semibold">الحالة الإنتاجية</th>
                    <th className="px-5 py-4 font-semibold text-center">إجراءات</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700/60">
                  {cohorts.map((cohort) => {
                    const statusConf = STATUS_CONFIG_MAP[cohort.status] || {}
                    return (
                      <tr
                        key={cohort.id}
                        className={`hover:bg-emerald-50/30 dark:hover:bg-slate-700/30 transition-colors ${
                          selectedCohorts.includes(cohort.id) ? 'bg-emerald-50/20 dark:bg-emerald-900/10' : ''
                        }`}
                      >
                        {enableBulkTransition && (
                          <td className="px-5 py-4 text-center border-l border-emerald-50 dark:border-slate-700/30">
                            <input
                              type="checkbox"
                              checked={selectedCohorts.includes(cohort.id)}
                              onChange={() => handleSelectCohort(cohort.id)}
                              disabled={String(cohort.id).startsWith('temp-')}
                              className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 w-4 h-4 disabled:opacity-50"
                            />
                          </td>
                        )}
                        <td className="px-5 py-4 text-gray-900 dark:text-white font-medium">
                          {cohort.location?.name || cohort.location_name || '-'}
                        </td>
                      <td className="px-5 py-4 text-gray-600 dark:text-slate-300">
                        <div className="font-semibold text-gray-800 dark:text-slate-200">
                          {cohort.crop?.name || cohort.crop_name || '-'}
                        </div>
                        <div className="text-xs">
                          {cohort.variety?.name || cohort.variety_name || '-'}
                        </div>
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-gray-500 dark:text-slate-400 flex flex-col gap-1 items-start">
                        <div className="flex items-center gap-2">
                          {String(cohort.id).startsWith('temp-') ? (
                            <span className="text-amber-500" title="قيد الانتظار لمزامنة السيرفر">
                              <svg
                                className="w-4 h-4"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                              </svg>
                            </span>
                          ) : null}
                          #{String(cohort.id).split('-')[0]}
                        </div>
                        {cohort.parent_cohort_batch && (
                          <span
                            className="text-[10px] bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 px-1.5 py-0.5 rounded"
                            title="منبثقة من هذه الدفعة (Ratooning)"
                          >
                            أُم: {cohort.parent_cohort_batch}
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex items-center justify-center px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-bold border border-slate-200 dark:border-slate-700">
                          {formatNumber(cohort.quantity)}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-gray-600 dark:text-slate-400">
                        {formatDate(cohort.planted_date)}
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded-md shadow-sm border border-transparent ${statusConf.bg} ${statusConf.color}`}
                        >
                          {statusConf.ar || cohort.status}
                        </span>
                      </td>
                      <td className="px-5 py-4 flex flex-wrap justify-center gap-2">
                        {/* Option 0: True Delete (Admin / Entry correction) */}
                        <button
                          onClick={() => handleDeleteCohort(cohort)}
                          disabled={String(cohort.id).startsWith('temp-')}
                          className="text-gray-600 hover:text-red-700 bg-gray-100 dark:bg-slate-700 hover:bg-red-100 p-2 rounded-lg transition-colors disabled:opacity-50"
                          title="حذف الدفعة نهائياً (تصحيح الإدخال)"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>

                        {/* Option C: Legacy Transition (Internal Status Change) */}
                        <button
                          onClick={() => openTransitionModal(cohort)}
                          disabled={String(cohort.id).startsWith('temp-')}
                          className="text-emerald-600 hover:text-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 hover:bg-emerald-100 p-2 rounded-lg transition-colors disabled:opacity-50"
                          title="تغيير الحالة الإدارية (تحديث الإدخال)"
                        >
                          <svg
                            className="w-5 h-5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="1.5"
                              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                            />
                          </svg>
                        </button>

                        {/* Option B: Pruning (Capitalized Service) */}
                        <button
                          onClick={() => handleLaunchpadAction(cohort, 'PRUNE')}
                          disabled={String(cohort.id).startsWith('temp-')}
                          className="text-amber-600 hover:text-amber-700 bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 p-2 rounded-lg transition-colors disabled:opacity-50"
                          title="تسجيل عملية تقليم للدفعة (يفتح السجل اليومي)"
                        >
                          <svg
                            className="w-5 h-5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758L5 19m0-14l4.121 4.121"
                            />
                          </svg>
                        </button>

                        {/* Option A: Die-off (Critical Variance) */}
                        <button
                          onClick={() => handleLaunchpadAction(cohort, 'DIE_OFF')}
                          disabled={String(cohort.id).startsWith('temp-')}
                          className="text-red-500 hover:text-red-700 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 p-2 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center font-bold"
                          title="إبلاغ عن موت جزئي/تلف أشجار (يفتح السجل اليومي)"
                        >
                           <span className="text-lg leading-none">×</span>
                        </button>

                        {/* Option D: Mass Casualty (Authoritative Write-off Axis 18) */}
                        <button
                          onClick={() => openMassCasualtyModal(cohort)}
                          disabled={String(cohort.id).startsWith('temp-')}
                          className="text-red-700 hover:text-white bg-red-100 dark:bg-red-900/40 hover:bg-red-600 p-2 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center font-bold"
                          title="شطب نصفي/جماعي (إعدام كلي مع أثر مالي)"
                        >
                          <span className="text-xl leading-none font-sans">&times;</span>
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
        )}
      </div>
      </>
      )}

      {/* Modal - New Cohort Registration */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-800 w-full max-w-xl rounded-2xl shadow-2xl border border-gray-100 dark:border-slate-700 flex flex-col max-h-[90vh]">
            <div className="p-5 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-gray-50/50 dark:bg-slate-800/50 rounded-t-2xl">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                تسجيل دفعة شجرية جديدة
              </h2>
              <button
                disabled={saving}
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-white bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:hover:bg-slate-600 rounded-full p-1 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    المزرعة *
                  </label>
                  <select
                    name="farm"
                    value={formData.farm}
                    onChange={handleFormChange}
                    required
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  >
                    <option value="">اختر المزرعة...</option>
                    {farms.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    الموقع *
                  </label>
                  <select
                    name="location"
                    value={formData.location}
                    onChange={handleFormChange}
                    required
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  >
                    <option value="">اختر الموقع...</option>
                    {formLocations.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    المحصول *
                  </label>
                  <select
                    name="crop"
                    value={formData.crop}
                    onChange={handleFormChange}
                    required
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  >
                    <option value="">اختر المحصول...</option>
                    {crops.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300">
                      الصنف
                    </label>
                    {formData.crop && (
                      <button
                        type="button"
                        onClick={() => setIsAddVarietyModalOpen(true)}
                        className="text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 text-xs font-bold flex items-center gap-1"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                        </svg>
                        إضافة صنف
                      </button>
                    )}
                  </div>
                  <select
                    name="variety"
                    value={formData.variety}
                    onChange={handleFormChange}
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  >
                    <option value="">(اختياري) اختر الصنف...</option>
                    {formVarieties.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    عدد الأشجار *
                  </label>
                  <input
                    type="number"
                    name="quantity"
                    min="1"
                    step="1"
                    required
                    value={formData.quantity}
                    onChange={handleFormChange}
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                    placeholder="مثال: 500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    اسم الدفعة *
                  </label>
                  <input
                    type="text"
                    name="batch_name"
                    required
                    value={formData.batch_name}
                    onChange={handleFormChange}
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                    placeholder="مثال: غرسية ربيع 2026"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    تاريخ الغرس / الزراعة *
                  </label>
                  <input
                    type="date"
                    name="planted_date"
                    required
                    value={formData.planted_date}
                    onChange={handleFormChange}
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    حالة الدفعة البيولوجية *
                  </label>
                  <select
                    name="status"
                    value={formData.status}
                    onChange={handleFormChange}
                    required
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500 border-l-4 border-l-emerald-500"
                  >
                    <option value="JUVENILE">غير منتجة (في طور النمو)</option>
                    <option value="PRODUCTIVE">منتجة (طرح ثمار)</option>
                    <option value="SICK">مريضة</option>
                    <option value="RENEWING">خلفة / تجديد (Ratooning)</option>
                  </select>
                </div>

                {formData.status === 'RENEWING' && (
                  <div className="col-span-2 mt-2">
                    <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                      الدفعة الأم (اختياري)
                    </label>
                    <select
                      name="parent_cohort"
                      value={formData.parent_cohort}
                      onChange={handleFormChange}
                      className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                    >
                      <option value="">-- الجيل الأول (بدون أم) --</option>
                      {filteredPotentialParents.map((c) => (
                        <option key={c.id} value={c.id}>
                          دفعة #{c.id} ({c.quantity} شجرة -{' '}
                          {STATUS_CONFIG_MAP[c.status]?.ar || c.status})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>

            <div className="p-5 border-t border-gray-100 dark:border-slate-700 bg-gray-50/80 dark:bg-slate-800/80 rounded-b-2xl flex justify-end gap-3 items-center">
              <button
                disabled={saving}
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-5 py-2.5 text-sm font-semibold text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700 rounded-xl transition-colors"
              >
                إلغاء
              </button>
              <button
                disabled={
                  saving ||
                  !formData.farm ||
                  !formData.location ||
                  !formData.quantity ||
                  !formData.batch_name
                }
                onClick={handleSubmit}
                type="submit"
                className="px-6 py-2.5 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-md transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? (
                  <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                ) : null}
                حفظ دفعة الغرس
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal - Transition */}
      {isTransitionModalOpen && transitionCohort && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-800 w-full max-w-md rounded-2xl shadow-2xl border border-gray-100 dark:border-slate-700 flex flex-col">
            <div className="p-5 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-gray-50/50 dark:bg-slate-800/50 rounded-t-2xl">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">تحديث حالة الدفعة</h2>
              <button
                disabled={saving}
                onClick={() => setIsTransitionModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-white bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:hover:bg-slate-600 rounded-full p-1 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-emerald-50 dark:bg-emerald-900/20 p-3 rounded-xl border border-emerald-100 dark:border-emerald-800/30">
                <p className="text-xs text-emerald-800 dark:text-emerald-300 font-medium">
                  الدفعة المحددة:
                </p>
                <p className="text-sm font-bold text-emerald-900 dark:text-emerald-100">
                  {transitionCohort.batch_name} ({transitionCohort.quantity} شجرة)
                </p>
                <p className="text-xs text-emerald-700 dark:text-emerald-400">
                  الحالة الحالية:{' '}
                  <span className="font-bold">
                    {STATUS_CONFIG_MAP[transitionCohort.status]?.ar}
                  </span>
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                  الحالة الجديدة *
                </label>
                <select
                  name="target_status"
                  value={transitionData.target_status}
                  onChange={handleTransitionChange}
                  required
                  className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                >
                  <option value="">اختر الحالة الانتقالية...</option>
                  {transitionCohort.status !== 'JUVENILE' && (
                    <option value="JUVENILE">غير منتجة (نمو)</option>
                  )}
                  {transitionCohort.status !== 'PRODUCTIVE' && (
                    <option value="PRODUCTIVE">منتجة (طرح)</option>
                  )}
                  {transitionCohort.status !== 'SICK' && <option value="SICK">مريضة</option>}
                  {transitionCohort.status !== 'RENEWING' && (
                    <option value="RENEWING">تجديد (Ratooning)</option>
                  )}
                  {transitionCohort.status !== 'EXCLUDED' && (
                    <option value="EXCLUDED" className="text-red-600 font-bold">
                      إعدام / استبعاد (وفاة)
                    </option>
                  )}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                  عدد الأشجار متغيرة الحالة *
                </label>
                <input
                  type="number"
                  name="quantity"
                  min="1"
                  max={transitionCohort.quantity}
                  step="1"
                  required
                  value={transitionData.quantity}
                  onChange={handleTransitionChange}
                  className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  placeholder={`الحد الأقصى المتاح: ${transitionCohort.quantity}`}
                />
                <p className="text-xs text-gray-500 mt-1">
                  يمكنك نقل جزء من الدفعة أو نقل الدفعة بأكملها.
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                  ملاحظات
                  {transitionData.target_status === 'EXCLUDED' && (
                    <span className="text-red-500 text-xs mr-2">(إلزامي للتبليغ عن الفقد)</span>
                  )}
                </label>
                <textarea
                  name="notes"
                  rows="3"
                  required={transitionData.target_status === 'EXCLUDED'}
                  value={transitionData.notes}
                  onChange={handleTransitionChange}
                  className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  placeholder={
                    transitionData.target_status === 'EXCLUDED'
                      ? 'اذكر أسباب التلف أو الخسارة لإعتمادها مالياً...'
                      : 'ملاحظات اختيارية عن الانتقال...'
                  }
                ></textarea>
              </div>
            </div>

            <div className="p-5 border-t border-gray-100 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50 flex justify-end gap-3 rounded-b-2xl">
              <button
                disabled={saving}
                type="button"
                onClick={() => setIsTransitionModalOpen(false)}
                className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-700 shadow-sm transition-colors"
              >
                إلغاء
              </button>
              <button
                disabled={
                  saving ||
                  !transitionData.target_status ||
                  !transitionData.quantity ||
                  Number(transitionData.quantity) > transitionCohort.quantity ||
                  Number(transitionData.quantity) <= 0 ||
                  (transitionData.target_status === 'EXCLUDED' && !transitionData.notes.trim())
                }
                onClick={handleTransitionSubmit}
                type="button"
                className={`flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white shadow-md transition-colors rounded-xl disabled:opacity-50 ${
                  transitionData.target_status === 'EXCLUDED'
                    ? 'bg-red-600 hover:bg-red-700 disabled:bg-red-600'
                    : 'bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-600'
                }`}
              >
                {saving && (
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                )}
                تأكيد العملية
              </button>
            </div>
          </div>
        </div>
      )}
      {/* [AGRI-GUARDIAN] Mass Casualty Modal (Axis 18) */}
      {isMassCasualtyModalOpen && massCasualtyCohort && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/70 backdrop-blur-md p-4 animate-in fade-in zoom-in duration-200">
          <div className="bg-white dark:bg-slate-800 w-full max-w-lg rounded-2xl shadow-2xl border border-red-100 dark:border-red-900/30 overflow-hidden">
            <div className="p-5 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-red-50/50 dark:bg-red-900/10">
              <div className="flex items-center gap-3">
                <span className="text-2xl">⚠️</span>
                <h2 className="text-lg font-bold text-red-700 dark:text-red-400">
                  بلاغ شطب جماعي (Mass Casualty)
                </h2>
              </div>
              <button
                disabled={saving}
                onClick={() => setIsMassCasualtyModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-xl text-sm border border-red-100 dark:border-red-800/30">
                <p className="font-bold text-red-800 dark:text-red-300 mb-1">
                  تنبيه قانوني (IAS 41):
                </p>
                <p className="text-red-700 dark:text-red-400">
                  هذا الإجراء سيقوم بشطب أصول بيولوجية من الميزانية بشكل نهائي وتوليد قيود خسارة
                  مالية (Impairment Loss). لا يستخدم إلا في الكوارث أو الآفات الجماعية.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    سبب الكارثة (Cause) *
                  </label>
                  <select
                    name="cause"
                    value={massCasualtyData.cause}
                    onChange={handleMassCasualtyChange}
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-red-500"
                  >
                    <option value="DISEASE">آفات / أمراض (Disease)</option>
                    <option value="FROST">صقيع (Frost)</option>
                    <option value="FLOOD">سيول / فيضانات (Flood)</option>
                    <option value="FIRE">حريق (Fire)</option>
                    <option value="OTHER">أسباب أخرى (Other)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    الكمية المفقودة *
                  </label>
                  <input
                    type="number"
                    name="quantity_lost"
                    min="1"
                    max={massCasualtyCohort.quantity}
                    value={massCasualtyData.quantity_lost}
                    onChange={handleMassCasualtyChange}
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-red-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    القيمة العادلة للوحدة *
                  </label>
                  <input
                    type="number"
                    name="estimated_fair_value_per_unit"
                    min="0"
                    placeholder="YER"
                    value={massCasualtyData.estimated_fair_value_per_unit}
                    onChange={handleMassCasualtyChange}
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-red-500"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                    شرح الحدث (Reason) *
                  </label>
                  <textarea
                    name="reason"
                    rows="3"
                    value={massCasualtyData.reason}
                    onChange={handleMassCasualtyChange}
                    placeholder="اشرح ظروف الحدث بالتفصيل (حد أدنى 10 أحرف)..."
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-red-500"
                  ></textarea>
                </div>
              </div>
            </div>

            <div className="p-5 border-t border-gray-100 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50 flex justify-end gap-3">
              <button
                disabled={saving}
                onClick={() => setIsMassCasualtyModalOpen(false)}
                className="px-5 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-xl hover:bg-gray-50"
              >
                إلغاء
              </button>
              <button
                disabled={
                  saving ||
                  !massCasualtyData.reason ||
                  massCasualtyData.reason.length < 10 ||
                  !massCasualtyData.estimated_fair_value_per_unit
                }
                onClick={handleMassCasualtySubmit}
                className="px-6 py-2 text-sm font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl shadow-lg disabled:opacity-50"
              >
                {saving ? 'جاري الحفظ...' : 'اعتماد الشطب المالي'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* [Best-Practice] Inline Delete Confirmation Modal — replaces window.confirm */}
      {confirmDeleteCohort && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-800 w-full max-w-md rounded-2xl shadow-2xl border border-red-100 dark:border-red-900/30 overflow-hidden">
            <div className="p-5 border-b border-gray-100 dark:border-slate-700 flex items-center gap-3 bg-red-50/60 dark:bg-red-900/10">
              <span className="text-2xl">🗑️</span>
              <h2 className="text-lg font-bold text-red-700 dark:text-red-400">تأكيد الحذف النهائي</h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-gray-700 dark:text-slate-300 text-sm leading-relaxed">
                هل أنت متأكد من رغبتك في حذف هذه الدفعة بشكل نهائي؟ لا يمكن التراجع عن هذا الإجراء.
              </p>
              <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 space-y-1 text-sm border border-slate-200 dark:border-slate-700">
                <div className="flex justify-between">
                  <span className="text-gray-500">اسم الدفعة:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{confirmDeleteCohort.batch_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">عدد الأشجار:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{formatNumber(confirmDeleteCohort.quantity)} شجرة</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">الموقع:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{confirmDeleteCohort.location?.name || confirmDeleteCohort.location_name || '—'}</span>
                </div>
              </div>
            </div>
            <div className="p-5 border-t border-gray-100 dark:border-slate-700 bg-gray-50/80 dark:bg-slate-800/80 flex justify-end gap-3">
              <button
                disabled={deleting}
                onClick={() => setConfirmDeleteCohort(null)}
                className="px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
              >
                إلغاء
              </button>
              <button
                disabled={deleting}
                onClick={executeDeleteCohort}
                className="px-6 py-2.5 text-sm font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl shadow-md transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {deleting && <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />}
                نعم، احذف الدفعة
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal - Add Variety */}
      {isAddVarietyModalOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-800 w-full max-w-sm rounded-2xl shadow-2xl border border-gray-100 dark:border-slate-700 flex flex-col">
            <div className="p-4 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-gray-50/50 dark:bg-slate-800/50 rounded-t-2xl">
              <h2 className="text-base font-bold text-gray-900 dark:text-white">إضافة صنف جديد</h2>
              <button
                disabled={saving}
                onClick={() => setIsAddVarietyModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-white"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                  اسم الصنف *
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  value={newVarietyData.name}
                  onChange={handleNewVarietyChange}
                  className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  placeholder="مثال: يافعي، سكري..."
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1">
                  ملاحظات
                </label>
                <textarea
                  name="notes"
                  rows="2"
                  value={newVarietyData.notes}
                  onChange={handleNewVarietyChange}
                  className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-4 py-2 text-sm focus:ring-emerald-500"
                  placeholder="معلومات إضافية عن الصنف..."
                ></textarea>
              </div>
            </div>
            <div className="p-4 border-t border-gray-100 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50 flex justify-end gap-3 rounded-b-2xl">
              <button
                disabled={saving}
                type="button"
                onClick={() => setIsAddVarietyModalOpen(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                إلغاء
              </button>
              <button
                disabled={saving || !newVarietyData.name.trim()}
                onClick={handleAddVarietySubmit}
                type="button"
                className="px-4 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm transition-colors disabled:opacity-50"
              >
                {saving ? 'جاري الحفظ...' : 'حفظ الصنف'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
