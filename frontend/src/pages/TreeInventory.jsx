import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'
// Unused: import PropTypes from 'prop-types' // [Agri-Guardian] Enforce strict typing
// Unused: import { format } from 'date-fns'
import {
  api,
  TreeInventory,
  TreeInventoryAdmin,
  TreeInventorySummary,
  TreeProductivityStatuses,
  TreeLossReasons,
  CropVarieties,
  Crops,
} from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Modal from '../components/Modal'
import { useToast } from '../components/ToastProvider'
import ar from '../i18n/ar'

// [Agri-Guardian] Atomic Components & Utilities
import {
  formatNumber,
  formatDate,
  formatDateTime,
  formatPercent,
  SERVICE_TYPE_LABELS,
  buildSummaryParams,
  buildEventsParams,
  downloadBlob,
} from './tree-inventory/utils'
import ServiceDetailLine from './tree-inventory/ServiceDetailLine'

const TEXT = ar.treeInventory

// formatNumber, formatDate, formatDateTime, formatPercent are now imported from utils
// SERVICE_TYPE_LABELS is now imported from utils
// ServiceDetailLine is now imported from tree-inventory/ServiceDetailLine

// Local helpers not in utils.js

export default function TreeInventoryPage() {
  const auth = useAuth()
  const routerLocation = useLocation()
  const toast = useToast()
  const addToast = toast // useToast returns the function directly

  const [farms, setFarms] = useState([])
  const [crops, setCrops] = useState([])
  const [locations, setLocations] = useState([])
  const [varieties, setVarieties] = useState([])
  const [treeStatuses, setTreeStatuses] = useState([])
  const [treeLossReasons, setTreeLossReasons] = useState([])

  const [summaryRows, setSummaryRows] = useState([])
  const [eventRows, setEventRows] = useState([])

  const [loadingSummary, setLoadingSummary] = useState(false)
  const [loadingEvents, setLoadingEvents] = useState(false)
  const [summaryError, setSummaryError] = useState('')
  const [eventsError, setEventsError] = useState('')

  const [exportingSummary, setExportingSummary] = useState(false)
  const [exportingEvents, setExportingEvents] = useState(false)
  const [isAdjustmentModalOpen, setIsAdjustmentModalOpen] = useState(false)
  const [adjustmentSaving, setAdjustmentSaving] = useState(false)
  const [adjustmentLocations, setAdjustmentLocations] = useState([])
  const [adjustmentVarieties, setAdjustmentVarieties] = useState([])
  const [adjustmentPreview, setAdjustmentPreview] = useState(null)
  const [adjustmentPreviewLoading, setAdjustmentPreviewLoading] = useState(false)
  const [adjustmentPreviewError, setAdjustmentPreviewError] = useState('')

  const defaultFilters = useMemo(
    () => ({
      start: '',
      end: '',
      service_start: '',
      service_end: '',
      farm: '',
      location_id: '',
      variety_id: '',
      status_code: '',
      loss_reason: '',
    }),
    [],
  )

  const [draftFilters, setDraftFilters] = useState(() => ({ ...defaultFilters }))
  const [appliedFilters, setAppliedFilters] = useState(() => ({ ...defaultFilters }))
  const adjustmentDefaults = useMemo(
    () => ({
      farm: '',
      location_id: '',
      crop_id: '',
      variety_id: '',
      resulting_tree_count: '',
      reason: '',
      source: 'جرد فعلي',
      notes: '',
      planting_date: '',
    }),
    [],
  )
  const [adjustmentForm, setAdjustmentForm] = useState(() => ({ ...adjustmentDefaults }))
  const prefillAppliedRef = useRef(false)

  const [columnVisibility, setColumnVisibility] = useState({
    notes: false,
    harvest: true,
    water: false,
    fertilizer: false,
    servicePeriod: true,
    serviceLifetime: true,
    serviceLatest: true,
  })

  const statusLookup = useMemo(() => {
    const lookup = {}
    treeStatuses.forEach((status) => {
      lookup[status.code] = status
    })
    return lookup
  }, [treeStatuses])

  const lossReasonLookup = useMemo(() => {
    const lookup = {}
    treeLossReasons.forEach((reason) => {
      lookup[reason.code] = reason
      if (reason.id != null) {
        lookup[String(reason.id)] = reason
      }
    })
    return lookup
  }, [treeLossReasons])

  const periodCoverageLabel = 'تغطية الفترة'
  const lifetimeCoverageLabel = 'التغطية التراكمية'
  const eventsTitle = 'سجل الحركات'
  const totalTreesHeader = 'عدد الأشجار'
  const lastServiceDateLabel = 'التاريخ'
  const lastServiceCountLabel = 'عدد الأشجار'
  const lastServiceTypeLabel = 'نوع الخدمة'
  const lastServiceByLabel = 'مسجل بواسطة'

  const farmLookup = useMemo(() => {
    const lookup = {}
    farms.forEach((farm) => {
      if (farm && farm.id != null) {
        lookup[String(farm.id)] = farm
      }
    })
    return lookup
  }, [farms])

  const totalsByStatus = useMemo(() => {
    const totals = { total: 0, status: {} }
    summaryRows.forEach((item) => {
      const count = Number(item?.current_tree_count ?? 0)
      totals.total += Number.isFinite(count) ? count : 0
      const code = item?.productivity_status?.code || item?.productivity_status_code || 'unknown'
      totals.status[code] = (totals.status[code] || 0) + (Number.isFinite(count) ? count : 0)
    })
    return totals
  }, [summaryRows])

  const productiveTotal = totalsByStatus.status['productive'] || 0
  const decliningTotal = totalsByStatus.status['declining'] || 0

  const statusBreakdown = useMemo(() => {
    return treeStatuses
      .map((status) => ({
        code: status.code,
        label: status.name_ar || status.name_en || status.code,
        value: totalsByStatus.status[status.code] || 0,
      }))
      .filter((entry) => entry.value > 0)
  }, [treeStatuses, totalsByStatus])

  const canAdjustTreeInventory =
    auth.isAdmin || auth.isSuperuser || auth.canChangeModel?.('locationtreestock')

  const selectedAdjustmentCrop = useMemo(
    () =>
      crops.find((crop) => String(crop.id) === String(adjustmentForm.crop_id || '')) || null,
    [crops, adjustmentForm.crop_id],
  )

  const filteredAdjustmentVarieties = useMemo(() => {
    if (!adjustmentForm.crop_id) {
      return adjustmentVarieties
    }
    return adjustmentVarieties.filter((variety) => {
      const cropId = variety.crop_id ?? (typeof variety.crop === 'object' ? variety.crop?.id : variety.crop) ?? null
      return String(cropId) === String(adjustmentForm.crop_id)
    })
  }, [adjustmentVarieties, adjustmentForm.crop_id])

  const selectedAdjustmentVariety = useMemo(
    () =>
      filteredAdjustmentVarieties.find(
        (variety) => String(variety.id) === String(adjustmentForm.variety_id || ''),
      ) || null,
    [filteredAdjustmentVarieties, adjustmentForm.variety_id],
  )

  const previewByLocation = useMemo(() => {
    if (!adjustmentPreview?.by_location || !adjustmentForm.location_id) {
      return null
    }
    return adjustmentPreview.by_location[String(adjustmentForm.location_id)] || null
  }, [adjustmentPreview, adjustmentForm.location_id])

  const previewCurrentCount = Number(
    previewByLocation?.current_tree_count ?? adjustmentPreview?.current_tree_count_total ?? 0,
  )
  const requestedAdjustmentCount =
    adjustmentForm.resulting_tree_count === '' ? null : Number(adjustmentForm.resulting_tree_count)
  const adjustmentDelta =
    requestedAdjustmentCount == null || Number.isNaN(requestedAdjustmentCount)
      ? null
      : requestedAdjustmentCount - previewCurrentCount
  const adjustmentChangeLabel =
    requestedAdjustmentCount == null
      ? '-'
      : previewByLocation
        ? adjustmentDelta > 0
          ? TEXT.adjustment.changeIncrease
          : adjustmentDelta < 0
            ? TEXT.adjustment.changeDecrease
            : TEXT.adjustment.changeStable
        : TEXT.adjustment.changeInitial
  const isLargeAdjustment =
    adjustmentDelta != null &&
    Math.abs(adjustmentDelta) >= Math.max(25, Math.ceil(previewCurrentCount * 0.1))
  const isMassCasualtyHint =
    adjustmentDelta != null &&
    adjustmentDelta < 0 &&
    Math.abs(adjustmentDelta) >= Math.max(100, Math.ceil(previewCurrentCount * 0.25))

  const applyAdjustmentPrefill = useCallback(
    (prefill, autoOpen = false) => {
      if (!prefill) {
        return
      }
      const nextFilters = {
        ...defaultFilters,
        farm: prefill.farm ? String(prefill.farm) : '',
        location_id: prefill.location_id ? String(prefill.location_id) : '',
        variety_id: prefill.variety_id ? String(prefill.variety_id) : '',
      }
      setDraftFilters(nextFilters)
      setAppliedFilters(nextFilters)
      setAdjustmentForm((prev) => ({
        ...prev,
        farm: prefill.farm ? String(prefill.farm) : prev.farm,
        location_id: prefill.location_id ? String(prefill.location_id) : prev.location_id,
        crop_id: prefill.crop_id ? String(prefill.crop_id) : prev.crop_id,
        variety_id: prefill.variety_id ? String(prefill.variety_id) : prev.variety_id,
      }))
      if (autoOpen && canAdjustTreeInventory) {
        setIsAdjustmentModalOpen(true)
      }
    },
    [canAdjustTreeInventory, defaultFilters],
  )

  const loadVarietiesForFarm = useCallback(async (farmId, farmCrops = null) => {
    const cropsForFarm = Array.isArray(farmCrops) && farmCrops.length ? farmCrops : null
    let cropRows = cropsForFarm
    if (!cropRows) {
      const cropResponse = await Crops.list({ farm_id: farmId })
      cropRows = cropResponse?.data?.results ?? cropResponse?.data ?? []
    }

    const varietyResponses = await Promise.all(
      (Array.isArray(cropRows) ? cropRows : []).map((crop) =>
        CropVarieties.list({ crop: crop.id }).catch(() => ({ data: [] })),
      ),
    )

    const deduped = new Map()
    varietyResponses.forEach((response) => {
      const rows = response?.data?.results ?? response?.data ?? []
      rows.forEach((row) => {
        if (row?.id != null && !deduped.has(String(row.id))) {
          deduped.set(String(row.id), row)
        }
      })
    })
    return {
      crops: Array.isArray(cropRows) ? cropRows : [],
      varieties: Array.from(deduped.values()),
    }
  }, [])

  useEffect(() => {
    const loadStaticData = async () => {
      try {
        const response = await api.get('/farms/')
        setFarms(response.data.results || response.data || [])
      } catch (error) {
        addToast({
          intent: 'error',
          title: TEXT.title,
          message: 'تعذر تحميل قائمة المزارع.',
        })
      }
      try {
        const [statusResponse, reasonsResponse] = await Promise.all([
          TreeProductivityStatuses.list(),
          TreeLossReasons.list(),
        ])
        const statusData = statusResponse?.data?.results ?? statusResponse?.data ?? []
        const reasonData = reasonsResponse?.data?.results ?? reasonsResponse?.data ?? []
        setTreeStatuses(Array.isArray(statusData) ? statusData : [])
        setTreeLossReasons(Array.isArray(reasonData) ? reasonData : [])
      } catch (error) {
        addToast({
          intent: 'error',
          title: TEXT.title,
          message: 'تعذر تحميل القوائم المرجعية للأشجار.',
        })
      }
    }
    loadStaticData()
  }, [addToast])

  useEffect(() => {
    let isActive = true
    const loadFarmDependencies = async () => {
      if (!draftFilters.farm) {
        setLocations([])
        setVarieties([])
        return
      }
      try {
        const [locationsResponse, farmVarieties] = await Promise.all([
          api.get('/locations/', { params: { farm_id: draftFilters.farm } }),
          loadVarietiesForFarm(draftFilters.farm),
        ])
        if (!isActive) return
        setLocations(locationsResponse.data.results || locationsResponse.data || [])
        setVarieties(farmVarieties.varieties || [])
      } catch (error) {
        if (!isActive) return
        addToast({
          intent: 'error',
          title: TEXT.title,
          message: 'تعذر تحميل المواقع أو الأصناف المرتبطة بالمزرعة.',
        })
      }
    }
    loadFarmDependencies()
    return () => {
      isActive = false
    }
  }, [draftFilters.farm, addToast, loadVarietiesForFarm])

  useEffect(() => {
    let isActive = true
    const loadAdjustmentDependencies = async () => {
      if (!adjustmentForm.farm) {
        setAdjustmentLocations([])
        setAdjustmentVarieties([])
        setCrops([])
        return
      }
      try {
        const [cropResponse, locationResponse] = await Promise.all([
          Crops.list({ farm_id: adjustmentForm.farm }),
          api.get('/locations/', { params: { farm_id: adjustmentForm.farm } }),
        ])
        if (!isActive) return
        const cropRows = cropResponse?.data?.results ?? cropResponse?.data ?? []
        const farmVarieties = await loadVarietiesForFarm(adjustmentForm.farm, cropRows)
        if (!isActive) return
        setCrops(farmVarieties.crops || [])
        setAdjustmentLocations(locationResponse?.data?.results ?? locationResponse?.data ?? [])
        setAdjustmentVarieties(farmVarieties.varieties || [])
      } catch (error) {
        if (!isActive) return
        addToast({
          intent: 'error',
          title: TEXT.title,
          message: TEXT.adjustment.loadDependenciesError,
        })
      }
    }
    loadAdjustmentDependencies()
    return () => {
      isActive = false
    }
  }, [adjustmentForm.farm, addToast, loadVarietiesForFarm])

  useEffect(() => {
    const prefill = routerLocation.state?.adjustmentPrefill
    const shouldOpen = Boolean(routerLocation.state?.openAdjustment)
    if (!prefill || prefillAppliedRef.current) {
      return
    }
    prefillAppliedRef.current = true
    applyAdjustmentPrefill(prefill, shouldOpen)
  }, [routerLocation.state, applyAdjustmentPrefill, canAdjustTreeInventory])

  useEffect(() => {
    let isActive = true
    const loadAdjustmentPreview = async () => {
      if (
        !adjustmentForm.farm ||
        !adjustmentForm.location_id ||
        !adjustmentForm.variety_id
      ) {
        setAdjustmentPreview(null)
        setAdjustmentPreviewError('')
        return
      }
      setAdjustmentPreviewLoading(true)
      setAdjustmentPreviewError('')
      try {
        const params = {
          farm_id: adjustmentForm.farm,
          location_id: adjustmentForm.location_id,
          variety_id: adjustmentForm.variety_id,
        }
        if (adjustmentForm.crop_id) {
          params.crop_id = adjustmentForm.crop_id
        }
        const response = await TreeInventorySummary.locationVarietySummary(params)
        if (!isActive) return
        const payload = response?.data?.results ?? []
        setAdjustmentPreview(Array.isArray(payload) && payload.length ? payload[0] : null)
      } catch (error) {
        if (!isActive) return
        setAdjustmentPreview(null)
        setAdjustmentPreviewError(TEXT.adjustment.previewError)
      } finally {
        if (isActive) {
          setAdjustmentPreviewLoading(false)
        }
      }
    }
    loadAdjustmentPreview()
    return () => {
      isActive = false
    }
  }, [
    adjustmentForm.farm,
    adjustmentForm.location_id,
    adjustmentForm.variety_id,
    adjustmentForm.crop_id,
  ])

  useEffect(() => {
    const fetchInventory = async () => {
      setLoadingSummary(true)
      setLoadingEvents(true)
      setSummaryError('')
      setEventsError('')
      const summaryParams = buildSummaryParams(appliedFilters)
      const eventsParams = buildEventsParams(appliedFilters)
      try {
        const [summaryResult, eventsResult] = await Promise.allSettled([
          TreeInventory.summary(summaryParams),
          TreeInventory.events(eventsParams),
        ])

        if (summaryResult.status === 'fulfilled') {
          const payload = summaryResult.value?.data?.results ?? summaryResult.value?.data ?? []
          setSummaryRows(Array.isArray(payload) ? payload : [])
        } else {
          setSummaryRows([])
          const errMsg = summaryResult.reason?.response?.data?.detail || TEXT.feedback.summaryError
          setSummaryError(errMsg)
          // Suppress initial empty filter error toasts
          if (Object.values(appliedFilters).some((v) => v !== '')) {
            addToast({ intent: 'error', title: TEXT.title, message: errMsg })
          }
        }

        if (eventsResult.status === 'fulfilled') {
          const payload = eventsResult.value?.data?.results ?? eventsResult.value?.data ?? []
          setEventRows(Array.isArray(payload) ? payload : [])
        } else {
          setEventRows([])
          const errMsg = eventsResult.reason?.response?.data?.detail || TEXT.feedback.eventsError
          setEventsError(errMsg)
          // Suppress initial empty filter error toasts
          if (Object.values(appliedFilters).some((v) => v !== '')) {
            addToast({ intent: 'error', title: TEXT.title, message: errMsg })
          }
        }
      } finally {
        setLoadingSummary(false)
        setLoadingEvents(false)
      }
    }
    fetchInventory()
  }, [appliedFilters, addToast])

  const handleFilterChange = (event) => {
    const { name, value } = event.target
    setDraftFilters((prev) => {
      const next = { ...prev, [name]: value }
      if (name === 'farm') {
        next.location_id = ''
        next.variety_id = ''
      }
      if (name === 'location_id' && value === '') {
        next.location_id = ''
      }
      if (name === 'variety_id' && value === '') {
        next.variety_id = ''
      }
      if (name === 'status_code' && value === '') {
        next.status_code = ''
      }
      if (name === 'loss_reason' && value === '') {
        next.loss_reason = ''
      }
      return next
    })
  }

  const handleApplyFilters = () => {
    setAppliedFilters({ ...draftFilters })
  }

  const handleResetFilters = () => {
    setDraftFilters({ ...defaultFilters })
    setAppliedFilters({ ...defaultFilters })
    setLocations([])
    setVarieties([])
  }

  const toggleColumnVisibility = (key) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  const handleExport = async (type) => {
    const summaryParams = buildSummaryParams(appliedFilters)
    const eventsParams = buildEventsParams(appliedFilters)
    if (type === 'summary') {
      setExportingSummary(true)
      try {
        const response = await TreeInventory.summaryExport(summaryParams)
        const startLabel = appliedFilters.start || 'all'
        const endLabel = appliedFilters.end || 'all'
        downloadBlob(response.data, `tree_inventory_summary_${startLabel}_${endLabel}.csv`)
      } catch (error) {
        addToast({
          intent: 'error',
          title: TEXT.title,
          message: TEXT.feedback.exportSummaryError,
        })
      } finally {
        setExportingSummary(false)
      }
    } else if (type === 'events') {
      setExportingEvents(true)
      try {
        const response = await TreeInventory.eventsExport(eventsParams)
        const startLabel = appliedFilters.start || 'all'
        const endLabel = appliedFilters.end || 'all'
        downloadBlob(response.data, `tree_inventory_events_${startLabel}_${endLabel}.csv`)
      } catch (error) {
        addToast({
          intent: 'error',
          title: TEXT.title,
          message: TEXT.feedback.exportEventsError,
        })
      } finally {
        setExportingEvents(false)
      }
    }
  }

  const resetAdjustmentForm = (prefill = null) => {
    setAdjustmentPreview(null)
    setAdjustmentPreviewError('')
    setAdjustmentForm({
      ...adjustmentDefaults,
      farm: prefill?.farm ? String(prefill.farm) : draftFilters.farm || '',
      location_id: prefill?.location_id ? String(prefill.location_id) : '',
      crop_id: prefill?.crop_id ? String(prefill.crop_id) : '',
      variety_id: prefill?.variety_id ? String(prefill.variety_id) : '',
    })
  }

  const openAdjustmentModal = (prefill = null) => {
    resetAdjustmentForm(prefill)
    setIsAdjustmentModalOpen(true)
  }

  const closeAdjustmentModal = () => {
    setIsAdjustmentModalOpen(false)
    resetAdjustmentForm()
  }

  const handleAdjustmentFieldChange = (event) => {
    const { name, value } = event.target
    setAdjustmentForm((prev) => {
      const next = { ...prev, [name]: value }
      if (name === 'farm') {
        next.location_id = ''
        next.crop_id = ''
        next.variety_id = ''
      }
      if (name === 'crop_id') {
        next.variety_id = ''
      }
      if (name === 'location_id' && value === '') {
        next.location_id = ''
      }
      if (name === 'variety_id' && value) {
        const selectedVariety = adjustmentVarieties.find(
          (variety) => String(variety.id) === String(value),
        )
        const cropId = selectedVariety?.crop_id ?? selectedVariety?.crop?.id ?? ''
        if (!next.crop_id && cropId) {
          next.crop_id = String(cropId)
        }
      }
      return next
    })
  }

  const handleSubmitAdjustment = async (event) => {
    event.preventDefault()
    if (!canAdjustTreeInventory) {
      return
    }
    const payload = {
      resulting_tree_count: Number(adjustmentForm.resulting_tree_count),
      reason: adjustmentForm.reason.trim(),
      source: adjustmentForm.source.trim(),
      notes: adjustmentForm.notes.trim(),
    }
    if (adjustmentForm.planting_date) {
      payload.planting_date = adjustmentForm.planting_date
    }
    if (previewByLocation?.location_id && selectedAdjustmentVariety?.id) {
      const matchingRow = summaryRows.find((item) => {
        const locationId = item.location?.id ?? item.location_tree_stock?.location?.id
        const varietyId = item.crop_variety?.id ?? item.location_tree_stock?.crop_variety?.id
        return (
          String(locationId) === String(previewByLocation.location_id) &&
          String(varietyId) === String(selectedAdjustmentVariety.id)
        )
      })
      if (matchingRow?.id) {
        payload.stock_id = matchingRow.id
      }
    }
    if (!payload.stock_id) {
      payload.location_id = Number(adjustmentForm.location_id)
      payload.variety_id = Number(adjustmentForm.variety_id)
    }

    setAdjustmentSaving(true)
    try {
      await TreeInventoryAdmin.adjust(payload, uuidv4())
      addToast({
        intent: 'success',
        title: TEXT.adjustment.successTitle,
        message: TEXT.adjustment.successMessage,
      })
      setIsAdjustmentModalOpen(false)
      resetAdjustmentForm()
      setAppliedFilters((prev) => ({ ...prev }))
    } catch (error) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.reason ||
        Object.values(error?.response?.data || {})?.flat?.()?.[0] ||
        TEXT.adjustment.submitError
      addToast({
        intent: 'error',
        title: TEXT.adjustment.errorTitle,
        message: String(detail),
      })
    } finally {
      setAdjustmentSaving(false)
    }
  }

  const columnLabels = {
    notes: TEXT.columnToggles.notes,
    harvest: TEXT.columnToggles.harvest,
    water: TEXT.columnToggles.water,
    fertilizer: TEXT.columnToggles.fertilizer,
    servicePeriod: TEXT.columnToggles.servicePeriod,
    serviceLifetime: TEXT.columnToggles.serviceLifetime,
    serviceLatest: TEXT.columnToggles.serviceLatest,
  }

  const renderFarmName = (location) => {
    if (!location) {
      return '-'
    }
    const farmValue = location.farm ?? location.farm_id ?? null
    if (farmValue && typeof farmValue === 'object') {
      return farmValue.name || '-'
    }
    if (farmValue != null && farmLookup[String(farmValue)]) {
      return farmLookup[String(farmValue)].name || '-'
    }
    return '-'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-6 space-y-6">
      {/* Premium Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-4xl font-extrabold bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-500 bg-clip-text text-transparent">
            {TEXT.title}
          </h1>
          <p className="text-gray-500 dark:text-slate-400">{TEXT.description}</p>
        </div>
        {canAdjustTreeInventory && (
          <button
            type="button"
            onClick={() =>
              openAdjustmentModal(routerLocation.state?.adjustmentPrefill || null)
            }
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
            data-testid="tree-inventory-open-adjustment"
          >
            {TEXT.adjustment.openAction}
          </button>
        )}
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-gray-200 dark:border-slate-700 p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-600 dark:text-slate-400" htmlFor="filter-start">
              من تاريخ
            </label>
            <input
              id="filter-start"
              aria-label="تاريخ البداية"
              type="date"
              name="start"
              value={draftFilters.start}
              onChange={handleFilterChange}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-600 dark:text-slate-400" htmlFor="filter-end">
              إلى تاريخ
            </label>
            <input
              id="filter-end"
              aria-label="تاريخ النهاية"
              type="date"
              name="end"
              value={draftFilters.end}
              onChange={handleFilterChange}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label
              className="text-xs text-gray-600 dark:text-slate-400"
              htmlFor="filter-service-start"
            >
              {TEXT.filters.serviceStart}
            </label>
            <input
              id="filter-service-start"
              type="date"
              name="service_start"
              value={draftFilters.service_start}
              onChange={handleFilterChange}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label
              className="text-xs text-gray-600 dark:text-slate-400"
              htmlFor="filter-service-end"
            >
              {TEXT.filters.serviceEnd}
            </label>
            <input
              id="filter-service-end"
              type="date"
              name="service_end"
              value={draftFilters.service_end}
              onChange={handleFilterChange}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-600 dark:text-slate-400" htmlFor="filter-farm">
              {TEXT.filters.farm}
            </label>
            <select
              id="filter-farm"
              name="farm"
              aria-label="تصفية حسب المزرعة"
              value={draftFilters.farm}
              onChange={handleFilterChange}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            >
              <option value="">{TEXT.filters.any}</option>
              {farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-600 dark:text-slate-400" htmlFor="filter-location">
              {TEXT.filters.location}
            </label>
            <select
              id="filter-location"
              name="location_id"
              aria-label="تصفية حسب الموقع"
              value={draftFilters.location_id}
              onChange={handleFilterChange}
              disabled={!locations.length}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-slate-700/60"
            >
              <option value="">{TEXT.filters.any}</option>
              {locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-600 dark:text-slate-400" htmlFor="filter-variety">
              {TEXT.filters.variety}
            </label>
            <select
              id="filter-variety"
              name="variety_id"
              value={draftFilters.variety_id}
              onChange={handleFilterChange}
              disabled={!varieties.length}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-slate-700/60"
            >
              <option value="">{TEXT.filters.any}</option>
              {varieties.map((variety) => (
                <option key={variety.id} value={variety.id}>
                  {variety.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-600 dark:text-slate-400" htmlFor="filter-status">
              الحالة الإنتاجية
            </label>
            <select
              id="filter-status"
              name="status_code"
              value={draftFilters.status_code}
              onChange={handleFilterChange}
              disabled={!treeStatuses.length}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-slate-700/60"
            >
              <option value="">{TEXT.filters.any}</option>
              {treeStatuses.map((status) => (
                <option key={status.code} value={status.code}>
                  {status.name_ar || status.name_en || status.code}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-600 dark:text-slate-400" htmlFor="filter-loss">
              {TEXT.filters.lossReason}
            </label>
            <select
              id="filter-loss"
              name="loss_reason"
              value={draftFilters.loss_reason}
              onChange={handleFilterChange}
              disabled={!treeLossReasons.length}
              className="rounded-md border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-slate-700/60"
            >
              <option value="">{TEXT.filters.any}</option>
              {treeLossReasons.map((reason) => (
                <option key={reason.code} value={reason.code}>
                  {reason.name_ar || reason.name_en || reason.code}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleApplyFilters}
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark"
            aria-label="تطبيق الفلاتر المختارة"
          >
            {TEXT.filters.apply}
          </button>
          <button
            type="button"
            onClick={handleResetFilters}
            className="rounded-md border border-gray-300 dark:border-slate-600 px-4 py-2 text-sm font-semibold text-gray-700 dark:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-700"
            aria-label="إعادة تعيين الفلاتر"
          >
            {TEXT.filters.reset}
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 shadow-sm p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {TEXT.summary.title}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {Object.entries(columnLabels).map(([key, label]) => (
              <label
                key={key}
                className="flex items-center gap-2 text-xs text-gray-600 dark:text-slate-300"
              >
                <input
                  type="checkbox"
                  checked={columnVisibility[key]}
                  onChange={() => toggleColumnVisibility(key)}
                />
                <span>{label}</span>
              </label>
            ))}
            <button
              type="button"
              onClick={() => handleExport('summary')}
              disabled={exportingSummary}
              className="rounded-md border border-primary px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
              aria-label="تصدير بيانات الملخص كملف CSV"
            >
              {exportingSummary ? '...' : 'تصدير الملخص'}
            </button>
          </div>
        </div>

        {/* Premium Summary Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          <div className="relative overflow-hidden rounded-2xl bg-white/80 dark:bg-slate-900/70 backdrop-blur-xl border border-white/20 dark:border-slate-700 shadow-xl p-5 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1">
            <div className="text-sm text-gray-500 dark:text-slate-300 mb-1">
              {TEXT.summary.total}
            </div>
            <div className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
              {formatNumber(totalsByStatus.total, 0)}
            </div>
            <div className="h-1 mt-3 bg-gradient-to-r from-gray-400 to-gray-600 rounded-full" />
          </div>
          <div className="relative overflow-hidden rounded-2xl bg-white/80 dark:bg-slate-900/70 backdrop-blur-xl border border-emerald-200/50 dark:border-emerald-700/40 shadow-xl p-5 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1">
            <div className="text-sm text-emerald-600 mb-1">{TEXT.summary.productive}</div>
            <div className="text-3xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
              {formatNumber(productiveTotal, 0)}
            </div>
            <div className="h-1 mt-3 bg-gradient-to-r from-emerald-400 to-teal-500 rounded-full" />
          </div>
          <div className="relative overflow-hidden rounded-2xl bg-white/80 dark:bg-slate-900/70 backdrop-blur-xl border border-amber-200/50 dark:border-amber-700/40 shadow-xl p-5 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1">
            <div className="text-sm text-amber-600 mb-1">{TEXT.summary.declining}</div>
            <div className="text-3xl font-bold bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent">
              {formatNumber(decliningTotal, 0)}
            </div>
            <div className="h-1 mt-3 bg-gradient-to-r from-amber-400 to-orange-500 rounded-full" />
          </div>
        </div>

        {statusBreakdown.length > 0 && (
          <div className="flex flex-wrap gap-3">
            {statusBreakdown.map((entry) => (
              <div
                key={entry.code}
                className="rounded-md border border-gray-200 dark:border-slate-600 px-3 py-2 text-xs"
              >
                <div className="text-gray-500 dark:text-slate-300">{entry.label}</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {formatNumber(entry.value, 0)}
                </div>
              </div>
            ))}
          </div>
        )}

        {loadingSummary ? (
          <div className="text-sm text-gray-500">جار التحميل...</div>
        ) : summaryError ? (
          <div className="text-sm text-red-600">{summaryError}</div>
        ) : summaryRows.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm text-gray-800 dark:text-slate-100">
              <thead className="bg-gray-50 dark:bg-slate-700/70 text-xs text-gray-600 dark:text-slate-200">
                <tr>
                  <th className="px-3 py-2 text-end">{TEXT.summary.table.farm}</th>
                  <th className="px-3 py-2 text-end">{TEXT.summary.table.location}</th>
                  <th className="px-3 py-2 text-end">{TEXT.summary.table.variety}</th>
                  <th className="px-3 py-2 text-end">{TEXT.summary.table.status}</th>
                  <th className="px-3 py-2 text-center">{totalTreesHeader}</th>
                  {columnVisibility.servicePeriod && (
                    <th className="px-3 py-2 text-end">{TEXT.summary.table.servicePeriod}</th>
                  )}
                  {columnVisibility.serviceLifetime && (
                    <th className="px-3 py-2 text-end">{TEXT.summary.table.serviceLifetime}</th>
                  )}
                  {columnVisibility.serviceLatest && (
                    <th className="px-3 py-2 text-end">{TEXT.summary.table.lastService}</th>
                  )}
                  <th className="px-3 py-2 text-end">{TEXT.summary.table.plantingDate}</th>
                  <th className="px-3 py-2 text-end">{TEXT.summary.table.source}</th>
                  {columnVisibility.notes && (
                    <th className="px-3 py-2 text-end">{TEXT.summary.table.notes}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {summaryRows.map((item, index) => {
                  const location = item.location || item.location_tree_stock?.location || null
                  const variety =
                    item.crop_variety || item.location_tree_stock?.crop_variety || null
                  const status = item.productivity_status || null
                  const statusCode =
                    item.productivity_status?.code || item.productivity_status_code || null
                  const statusLabel =
                    status?.name_ar ||
                    status?.name_en ||
                    statusLookup[statusCode]?.name_ar ||
                    statusLookup[statusCode]?.name_en ||
                    statusCode ||
                    '-'
                  const serviceStats = item.service_stats || {}
                  const periodStats = serviceStats.period || {}
                  const lifetimeStats = serviceStats.lifetime || {}
                  const latestEntry = serviceStats.latest_entry || null
                  const periodTotal = formatNumber(periodStats.total_serviced ?? 0, 0)
                  const periodCoverageValue = formatPercent(periodStats.coverage_ratio)
                  const periodEntriesValue = formatNumber(periodStats.entries ?? 0, 0)
                  const lifetimeTotal = formatNumber(lifetimeStats.total_serviced ?? 0, 0)
                  const lifetimeCoverageValue = formatPercent(lifetimeStats.coverage_ratio)
                  const lifetimeEntriesValue = formatNumber(lifetimeStats.entries ?? 0, 0)
                  const latestDateRaw =
                    latestEntry?.activity_date ||
                    periodStats.last_service_date ||
                    lifetimeStats.last_service_date ||
                    null
                  const latestDateLabel = latestDateRaw ? formatDate(latestDateRaw) : null
                  const latestCountValue =
                    latestEntry && latestEntry.service_count != null
                      ? formatNumber(latestEntry.service_count ?? 0, 0)
                      : null
                  const latestTypeCode = latestEntry?.service_type || null
                  const latestTypeLabel = latestTypeCode
                    ? SERVICE_TYPE_LABELS[latestTypeCode] ||
                      SERVICE_TYPE_LABELS.unknown ||
                      latestTypeCode
                    : null
                  const latestRecordedBy = latestEntry?.recorded_by_name || ''
                  return (
                    <tr
                      key={item.id || `row-${index}`}
                      className="border-t border-gray-100 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/40"
                    >
                      <td className="px-3 py-2">{renderFarmName(location)}</td>
                      <td className="px-3 py-2">{location?.name || '-'}</td>
                      <td className="px-3 py-2">{variety?.name || '-'}</td>
                      <td className="px-3 py-2">{statusLabel}</td>
                      <td className="px-3 py-2 text-center">
                        {formatNumber(item.current_tree_count ?? 0, 0)}
                      </td>
                      {columnVisibility.servicePeriod && (
                        <td className="px-3 py-2 text-end">
                          <div className="font-semibold text-gray-900 dark:text-white">
                            {periodTotal}
                          </div>
                          <ServiceDetailLine
                            className="text-[11px] text-gray-500"
                            label={periodCoverageLabel}
                            value={periodCoverageValue}
                            direction="ltr"
                          />
                          <ServiceDetailLine
                            className="text-[11px] text-gray-400"
                            label={TEXT.summary.table.periodEntriesLabel}
                            value={periodEntriesValue}
                            direction="ltr"
                          />
                        </td>
                      )}
                      {columnVisibility.serviceLifetime && (
                        <td className="px-3 py-2 text-end">
                          <div className="font-semibold text-gray-900 dark:text-white">
                            {lifetimeTotal}
                          </div>
                          <ServiceDetailLine
                            className="text-[11px] text-gray-500"
                            label={lifetimeCoverageLabel}
                            value={lifetimeCoverageValue}
                            direction="ltr"
                          />
                          <ServiceDetailLine
                            className="text-[11px] text-gray-400"
                            label={TEXT.summary.table.lifetimeEntriesLabel}
                            value={lifetimeEntriesValue}
                            direction="ltr"
                          />
                        </td>
                      )}
                      {columnVisibility.serviceLatest && (
                        <td className="px-3 py-2 text-end">
                          {latestDateLabel ||
                          latestCountValue ||
                          latestTypeLabel ||
                          latestRecordedBy ? (
                            <div className="space-y-1 text-xs text-gray-600 dark:text-slate-300">
                              <ServiceDetailLine
                                label={lastServiceDateLabel}
                                value={latestDateLabel}
                                direction="ltr"
                              />
                              <ServiceDetailLine
                                label={lastServiceCountLabel}
                                value={latestCountValue}
                                direction="ltr"
                              />
                              <ServiceDetailLine
                                label={lastServiceTypeLabel}
                                value={latestTypeLabel}
                              />
                              <ServiceDetailLine
                                label={lastServiceByLabel}
                                value={latestRecordedBy}
                              />
                            </div>
                          ) : (
                            <div className="text-xs text-gray-400 dark:text-slate-400">
                              {TEXT.summary.table.lastServiceMissing}
                            </div>
                          )}
                        </td>
                      )}
                      <td className="px-3 py-2">{formatDate(item.planting_date)}</td>
                      <td className="px-3 py-2">{item.source || '-'}</td>
                      {columnVisibility.notes && <td className="px-3 py-2">{item.notes || '-'}</td>}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-gray-500">{TEXT.empty.summary}</div>
        )}
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 shadow-sm p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{eventsTitle}</h2>
          <button
            type="button"
            onClick={() => handleExport('events')}
            disabled={exportingEvents}
            className="rounded-md border border-primary px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {exportingEvents ? '...' : 'تصدير الحركات'}
          </button>
        </div>

        {loadingEvents ? (
          <div className="text-sm text-gray-500">جار التحميل...</div>
        ) : eventsError ? (
          <div className="text-sm text-red-600">{eventsError}</div>
        ) : eventRows.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm text-gray-800 dark:text-slate-100">
              <thead className="bg-gray-50 dark:bg-slate-700/70 text-xs text-gray-600 dark:text-slate-200">
                <tr>
                  <th className="px-3 py-2 text-end">{TEXT.events.table.date}</th>
                  <th className="px-3 py-2 text-end">{TEXT.events.table.type}</th>
                  <th className="px-3 py-2 text-end">{TEXT.events.table.farm}</th>
                  <th className="px-3 py-2 text-end">{TEXT.events.table.location}</th>
                  <th className="px-3 py-2 text-end">{TEXT.events.table.variety}</th>
                  <th className="px-3 py-2 text-center">{TEXT.events.table.delta}</th>
                  <th className="px-3 py-2 text-center">{TEXT.events.table.resulting}</th>
                  <th className="px-3 py-2 text-end">{TEXT.events.table.reason}</th>
                  {columnVisibility.harvest && (
                    <th className="px-3 py-2 text-center">{TEXT.events.table.harvestQuantity}</th>
                  )}
                  {columnVisibility.water && (
                    <th className="px-3 py-2 text-center">{TEXT.events.table.waterVolume}</th>
                  )}
                  {columnVisibility.fertilizer && (
                    <th className="px-3 py-2 text-center">
                      {TEXT.events.table.fertilizerQuantity}
                    </th>
                  )}
                  <th className="px-3 py-2 text-end">{TEXT.events.table.source}</th>
                </tr>
              </thead>
              <tbody>
                {eventRows.map((event, index) => {
                  const stock = event.location_tree_stock || {}
                  const location = stock.location || {}
                  const variety = stock.crop_variety || {}
                  const reason =
                    event.loss_reason ||
                    lossReasonLookup[event.tree_loss_reason_id] ||
                    lossReasonLookup[event.loss_reason_code] ||
                    null
                  const farmName = renderFarmName(location)
                  const eventLocationLabel = location?.name || '-'
                  const eventLocationWithFarm =
                    eventLocationLabel !== '-' && farmName && farmName !== '-'
                      ? `${eventLocationLabel} – ${farmName}`
                      : eventLocationLabel
                  return (
                    <tr
                      key={event.id || `evt-${index}`}
                      className="border-t border-gray-100 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/40"
                    >
                      <td className="px-3 py-2">{formatDateTime(event.event_timestamp)}</td>
                      <td className="px-3 py-2">{event.event_type}</td>
                      <td className="px-3 py-2">{farmName}</td>
                      <td className="px-3 py-2">{eventLocationWithFarm}</td>
                      <td className="px-3 py-2">{variety?.name || '-'}</td>
                      <td className="px-3 py-2 text-center">
                        {formatNumber(event.tree_count_delta ?? 0, 0)}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {event.resulting_tree_count != null
                          ? formatNumber(event.resulting_tree_count, 0)
                          : '-'}
                      </td>
                      <td className="px-3 py-2">
                        {reason?.name_ar || reason?.name_en || reason?.code || event.notes || '-'}
                      </td>
                      {columnVisibility.harvest && (
                        <td className="px-3 py-2 text-center">
                          {event.harvest_quantity != null
                            ? formatNumber(event.harvest_quantity, 2)
                            : '-'}
                        </td>
                      )}
                      {columnVisibility.water && (
                        <td className="px-3 py-2 text-center">
                          {event.water_volume != null
                            ? `${formatNumber(event.water_volume, 2)} ${event.water_uom || ''}`.trim()
                            : '-'}
                        </td>
                      )}
                      {columnVisibility.fertilizer && (
                        <td className="px-3 py-2 text-center">
                          {event.fertilizer_quantity != null
                            ? `${formatNumber(event.fertilizer_quantity, 2)} ${event.fertilizer_uom || ''}`.trim()
                            : '-'}
                        </td>
                      )}
                      <td className="px-3 py-2">{event.source || '-'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-gray-500">{TEXT.empty.events}</div>
        )}
      </div>

      <Modal
        isOpen={isAdjustmentModalOpen}
        onClose={closeAdjustmentModal}
        title={TEXT.adjustment.modalTitle}
      >
        <form className="space-y-4" onSubmit={handleSubmitAdjustment}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-farm">
                {TEXT.adjustment.fields.farm}
              </label>
              <select
                id="adjustment-farm"
                name="farm"
                value={adjustmentForm.farm}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                required
              >
                <option value="">{TEXT.filters.any}</option>
                {farms.map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-location">
                {TEXT.adjustment.fields.location}
              </label>
              <select
                id="adjustment-location"
                name="location_id"
                value={adjustmentForm.location_id}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                disabled={!adjustmentLocations.length}
                required
              >
                <option value="">{TEXT.filters.any}</option>
                {adjustmentLocations.map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-crop">
                {TEXT.adjustment.fields.crop}
              </label>
              <select
                id="adjustment-crop"
                name="crop_id"
                value={adjustmentForm.crop_id}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                disabled={!crops.length}
                required
              >
                <option value="">{TEXT.filters.any}</option>
                {crops.map((crop) => (
                  <option key={crop.id} value={crop.id}>
                    {crop.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-variety">
                {TEXT.adjustment.fields.variety}
              </label>
              <select
                id="adjustment-variety"
                name="variety_id"
                value={adjustmentForm.variety_id}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                disabled={!filteredAdjustmentVarieties.length}
                required
              >
                <option value="">{TEXT.filters.any}</option>
                {filteredAdjustmentVarieties.map((variety) => (
                  <option key={variety.id} value={variety.id}>
                    {variety.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-count">
                {TEXT.adjustment.fields.resultingCount}
              </label>
              <input
                id="adjustment-count"
                name="resulting_tree_count"
                type="number"
                min="0"
                step="1"
                value={adjustmentForm.resulting_tree_count}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                required
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-planting-date">
                {TEXT.adjustment.fields.plantingDate}
              </label>
              <input
                id="adjustment-planting-date"
                name="planting_date"
                type="date"
                value={adjustmentForm.planting_date}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-reason">
                {TEXT.adjustment.fields.reason}
              </label>
              <input
                id="adjustment-reason"
                name="reason"
                value={adjustmentForm.reason}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                maxLength={250}
                required
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-source">
                {TEXT.adjustment.fields.source}
              </label>
              <input
                id="adjustment-source"
                name="source"
                value={adjustmentForm.source}
                onChange={handleAdjustmentFieldChange}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                maxLength={120}
                required
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700 dark:text-slate-200" htmlFor="adjustment-notes">
              {TEXT.adjustment.fields.notes}
            </label>
            <textarea
              id="adjustment-notes"
              name="notes"
              value={adjustmentForm.notes}
              onChange={handleAdjustmentFieldChange}
              rows={3}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              maxLength={500}
            />
          </div>

          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm dark:border-slate-700 dark:bg-slate-900/60">
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <div className="text-xs text-gray-500 dark:text-slate-400">{TEXT.adjustment.preview.currentBalance}</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {adjustmentPreviewLoading ? TEXT.adjustment.loading : formatNumber(previewCurrentCount, 0)}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-slate-400">{TEXT.adjustment.preview.changeType}</div>
                <div className="font-semibold text-gray-900 dark:text-white">{adjustmentChangeLabel}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-slate-400">{TEXT.adjustment.preview.delta}</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {adjustmentDelta == null ? '-' : formatNumber(adjustmentDelta, 0)}
                </div>
              </div>
            </div>
            {selectedAdjustmentCrop && (
              <div className="mt-3 text-xs text-gray-500 dark:text-slate-300">
                {TEXT.adjustment.preview.selectedCrop}: {selectedAdjustmentCrop.name}
              </div>
            )}
            {adjustmentPreviewError && (
              <div className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
                {adjustmentPreviewError}
              </div>
            )}
            {isLargeAdjustment && (
              <div className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
                {TEXT.adjustment.warnings.largeAdjustment}
              </div>
            )}
            {isMassCasualtyHint && (
              <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">
                {TEXT.adjustment.warnings.massCasualtyHint}
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={closeAdjustmentModal}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              {TEXT.adjustment.cancel}
            </button>
            <button
              type="submit"
              disabled={adjustmentSaving}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              data-testid="tree-inventory-submit-adjustment"
            >
              {adjustmentSaving ? TEXT.adjustment.submitting : TEXT.adjustment.submit}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
