import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ToastProvider'
import { useDailyLogForm } from '../hooks/useDailyLogForm'
import { usePerennialLogic } from '../hooks/usePerennialLogic'
import AuditLedger from '../utils/auditLedger'
import StateSync from '../utils/stateSync'
import SentinelGuard from '../utils/sentinelGuard'
import TopicCacheManager from '../utils/topicCacheManager'
import { DailyLogWizard } from '../components/daily-log/DailyLogWizard'
import { DailyLogSmartCard } from '../components/daily-log/DailyLogSmartCard'
import { useSmartContext } from '../hooks/useSmartContext'
import { AutosaveIndicator } from '../components/ui/AutosaveIndicator'
import { useSettings } from '../contexts/SettingsContext'
import { useOfflineQueue } from '../offline/OfflineQueueProvider.jsx'
import { seedLookupCacheWithMeta, getLookupCacheEntry } from '../offline/dexie_db'
import {
  getOfflineQueueDetails,
  Farms,
  Crops,
  Tasks,
  Locations,
  Assets,
  Items,
  DailyLogs,
  Activities,
  CropPlans,
  TreeLossReasons,
  CropVarieties,
  CropProducts,
  LocationWells,
  TreeInventorySummary,
} from '../api/client'
import { extractApiError } from '../utils/errorUtils'
import { logRuntimeError } from '../utils/runtimeLogger'
import {
  getAssetFarmId,
  isOperationalMachineAsset,
  isWellLikeAsset,
} from '../utils/assetClassification'

function normalizeVarietyPayload(rawVarieties) {
  const rows = Array.isArray(rawVarieties) ? rawVarieties : []
  const diagnostics = {
    invalidRows: 0,
    missingLocationCoverageRows: 0,
    crossCropRows: 0,
  }

  const varieties = rows
    .map((variety) => {
      if (!variety || typeof variety !== 'object' || variety.id == null) {
        diagnostics.invalidRows += 1
        return null
      }

      const hasLocationIds = Array.isArray(variety.location_ids)
      const hasLocationCounts =
        variety.current_tree_count_by_location &&
        typeof variety.current_tree_count_by_location === 'object' &&
        !Array.isArray(variety.current_tree_count_by_location)

      if ((hasLocationIds && !hasLocationCounts) || (!hasLocationIds && hasLocationCounts)) {
        diagnostics.missingLocationCoverageRows += 1
      }

      return {
        ...variety,
        name: variety.name || `الصنف ${variety.id}`,
        location_ids: hasLocationIds ? variety.location_ids : [],
        available_in_all_locations: Boolean(variety.available_in_all_locations),
        current_tree_count_total: Number(variety.current_tree_count_total || 0),
        current_tree_count_by_location: hasLocationCounts
          ? Object.fromEntries(
            Object.entries(variety.current_tree_count_by_location).map(([locationId, count]) => [
              String(locationId),
              Number(count || 0),
            ]),
          )
          : {},
      }
    })
    .filter(Boolean)

  return { varieties, diagnostics }
}

const toFreshnessState = (cachedAt) => {
  if (!cachedAt) {
    return { tone: 'slate', label: 'غير متاح', cachedAt: null }
  }
  const ageMs = Date.now() - new Date(cachedAt).getTime()
  if (ageMs <= 6 * 60 * 60 * 1000) {
    return { tone: 'emerald', label: 'حديثة', cachedAt }
  }
  if (ageMs <= 48 * 60 * 60 * 1000) {
    return { tone: 'amber', label: 'قديمة لكن قابلة للاستخدام', cachedAt }
  }
  return { tone: 'rose', label: 'قديمة وتتطلب مراجعة عند المزامنة', cachedAt }
}

// freshnessClasses: available for future UI freshness badge rendering
const _freshnessClasses = {
  emerald:
    'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
  amber:
    'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200',
  rose:
    'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200',
  sky: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200',
  slate:
    'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-500/30 dark:bg-slate-500/10 dark:text-slate-200',
}

// formatDateTime: available for future offline timestamp display
const _formatDateTime = (value) => {
  if (!value) return 'غير متاح'
  try {
    return new Date(value).toLocaleString('ar-EG', { hour12: false })
  } catch {
    return String(value)
  }
}

// offlineStateLabels/Classes: reserved for future offline status badge rendering
const _offlineStateLabels = {
  draft: 'draft | مسودة محلية',
  queued: 'queued | بانتظار المزامنة',
  syncing: 'syncing | جارٍ الترحيل',
  failed: 'failed | فشل قابل لإعادة المحاولة',
  dead_letter: 'dead_letter | يحتاج مراجعة',
}

const _offlineStateClasses = {
  draft:
    'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200',
  queued:
    'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
  syncing:
    'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-200',
  failed:
    'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200',
  dead_letter:
    'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200',
}

const normalizeOfflineState = (status, deadLetter = false) => {
  if (deadLetter || status === 'dead_letter') return 'dead_letter'
  if (status === 'syncing') return 'syncing'
  if (status === 'failed') return 'failed'
  if (status === 'queued') return 'queued'
  return 'draft'
}

export default function DailyLog() {
  const { user, strictErpMode } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const draftId = searchParams.get('draftId')
  const localDraftUuid = searchParams.get('localDraft')
  const addToast = useToast()

  const {
    form,
    updateField,
    errors,
    step,
    nextStep,
    prevStep,
    isSubmitting,
    isOnline,
    queueLogSubmission,
    resetForm,
    startNewDraft,
    resumeDraft,
    drafts,
    refreshDrafts,
    setForm,
    scrubPayload,
    setStep,
    setValidationPolicy,
  } = useDailyLogForm(location.state?.launchpadData || {}, {
    restoreDraftUuid: location.state?.restoreDraftUuid || localDraftUuid || null,
  })

  const {
    allowCrossPlanActivities,
    modeLabel,
    isStrictMode,
    remoteSite,
    weeklyRemoteReviewRequired,
  } = useSettings()
  const {
    queuedDailyLogs,
    failedDailyLogs,
    queuedHarvests: _queuedHarvests,
    queuedCustody: _queuedCustody,
    failedHarvests: _failedHarvests,
    failedCustody: _failedCustody,
    lastSync: _lastSync,
  } = useOfflineQueue()
  const simpleHomeRoute = isStrictMode ? '/dashboard' : '/simple-hub'
  const [_pendingOfflineEntries, setPendingOfflineEntries] = useState([])
  const [_failedOfflineEntries, setFailedOfflineEntries] = useState([])
  const [lookupFreshness, setLookupFreshness] = useState({
    base: { tone: 'slate', label: 'غير متاح', cachedAt: null },
    farm: { tone: 'slate', label: 'غير متاح', cachedAt: null },
    locations: { tone: 'slate', label: 'غير متاح', cachedAt: null },
    crop: { tone: 'slate', label: 'غير متاح', cachedAt: null },
  })

  const [loading, setLoading] = useState(true)
  const [lookups, setLookups] = useState({
    farms: [],
    crops: [],
    tasks: [],
    locations: [],
    assets: [],
    materials: [],
    wells: [],
    varieties: [],
    treeVarietySummary: [],
    varietiesMeta: {
      usedFallback: false,
      emptyReason: '',
      selectedLocationIds: [],
      diagnostics: null,
    },
    products: [],
    treeLossReasons: [],
  })
  const [linkedCropPlan, setLinkedCropPlan] = useState(null)
  const [linkageLoading, setLinkageLoading] = useState(false)

  const setFreshness = useCallback((key, freshness) => {
    setLookupFreshness((prev) => ({
      ...prev,
      [key]: freshness,
    }))
  }, [])

  const loadCachedLookup = useCallback(
    async (cacheKey, freshnessKey) => {
      const entry = await getLookupCacheEntry(cacheKey)
      if (!entry) {
        setFreshness(freshnessKey, { tone: 'slate', label: 'غير متاح', cachedAt: null })
        return null
      }
      const freshness = toFreshnessState(entry.cached_at)
      setFreshness(freshnessKey, freshness)
      return entry.data
    },
    [setFreshness],
  )

  const lookupSnapshotVersion = useMemo(
    () =>
      Object.entries(lookupFreshness)
        .map(([key, value]) => `${key}:${value.label}:${value.cachedAt || 'none'}`)
        .join('|'),
    [lookupFreshness],
  )

  const currentDraftRecord = useMemo(
    () => drafts.find((draft) => draft.draft_uuid === form.draft_uuid) || null,
    [drafts, form.draft_uuid],
  )
  const _currentDraftState = normalizeOfflineState(currentDraftRecord?.status || 'draft')

  useEffect(() => {
    const loadPendingEntries = async () => {
      const details = await getOfflineQueueDetails({ limit: 5 })
      setPendingOfflineEntries(details.dailyLogs || [])
      setFailedOfflineEntries(details.failedDailyLogs || [])
    }
    loadPendingEntries().catch(() => {})
  }, [queuedDailyLogs, failedDailyLogs])
  useEffect(() => {
    const loadData = async () => {
      try {
        // Parallel fetching for speed; tolerate partial failures under weak network.
        const [farmsRes, assetsRes, itemsRes, wellsRes, lossReasonsRes] = await Promise.allSettled([
          Farms.list(),
          Assets.list(),
          Items.list(),
          LocationWells.list(),
          TreeLossReasons.list(),
        ])

        const readPayload = (result) =>
          result.status === 'fulfilled'
            ? result.value?.data?.results || result.value?.data || []
            : []

        const farms = readPayload(farmsRes)
        const materials = readPayload(itemsRes)
        const assets = readPayload(assetsRes)

        setLookups((prev) => ({
          ...prev,
          farms,
          assets,
          materials,
          wells: readPayload(wellsRes),
          treeLossReasons: readPayload(lossReasonsRes),
        }))

        // [OFFLINE v4] Seed lookup cache so page works next visit without internet
        if (farms.length) {
          seedLookupCacheWithMeta('farms', farms, { farm_scope: 'global' }).catch(() => {})
        }
        if (materials.length) {
          seedLookupCacheWithMeta('materials', materials, { farm_scope: 'global' }).catch(() => {})
        }
        if (assets.length) {
          seedLookupCacheWithMeta('assets', assets, { farm_scope: 'global' }).catch(() => {})
        }
        setFreshness('base', { tone: 'emerald', label: 'حديثة', cachedAt: new Date().toISOString() })

      } catch (err) {
        logRuntimeError('DAILY_LOG_LOOKUPS_LOAD_FAILED', err)

        // [OFFLINE v4] Fallback: load from Dexie cache when offline
        const [cachedFarms, cachedMaterials, cachedAssets] = await Promise.all([
          loadCachedLookup('farms', 'base'),
          loadCachedLookup('materials', 'base'),
          loadCachedLookup('assets', 'base'),
        ])

        if (cachedFarms || cachedMaterials || cachedAssets) {
          setLookups((prev) => ({
            ...prev,
            farms: cachedFarms || prev.farms,
            materials: cachedMaterials || prev.materials,
            assets: cachedAssets || prev.assets,
          }))
          addToast('تم تحميل البيانات من الذاكرة المحلية (وضع عدم الاتصال).', 'warning')
        } else {
          addToast('فشل تحميل البيانات الأساسية. يرجى التحقق من الاتصال.', 'error')
        }
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      loadData()
    }
  }, [user, addToast, loadCachedLookup, setFreshness])

  // [PHASE 11: Editable Rejected Logs] - Load Server Draft
  useEffect(() => {
    const loadServerDraft = async () => {
      if (!draftId || !user) return
      try {
        setLoading(true)
        const [logRes, actRes] = await Promise.all([
          DailyLogs.get(draftId),
          Activities.list({ log: draftId }),
        ])
        const logData = logRes.data
        const activities = actRes.data?.results || actRes.data || []

        if (logData && activities.length > 0) {
          const act = activities[0] // Assuming 1 activity per log for this flow

          // Hydrate form structure from backend data
          const hydratedForm = {
            date: logData.log_date || new Date().toISOString().slice(0, 10),
            farm: String(logData.farm || ''),
            locations:
              Array.isArray(act.locations) && act.locations.length > 0
                ? act.locations.map((l) => String(l.id || l))
                : act.location
                  ? [String(act.location)]
                  : [],
            crop: String(act.crop || ''),
            task: String(act.task || ''),
            variety: String(act.variety || ''),
            notes: act.activity_notes || logData.notes || '',
            variance_note: logData.variance_note || '',
            rejection_reason: logData.rejection_reason || '',
            status: logData.status || '',

            // Labor
            labor_entry_mode: act.employee_details?.some((e) => e.labor_type === 'CASUAL_BATCH')
              ? 'CASUAL_BATCH'
              : 'REGISTERED',
            casual_workers_count:
              act.employee_details?.find((e) => e.labor_type === 'CASUAL_BATCH')?.workers_count ||
              '',
            team:
              act.employee_details
                ?.filter((e) => e.labor_type === 'REGISTERED')
                .map((e) => String(e.employee)) || [],
            surrah_count: act.employee_details?.[0]?.surrah_share || '1.0',

            // Machinery
            asset: act.asset ? String(act.asset.id || act.asset) : '',
            machine_hours: act.machine_details?.machine_hours || '',
            machine_meter_reading: act.machine_details?.machine_meter_reading || '',
            fuel_consumed: act.machine_details?.fuel_consumed || '',

            // Materials
            items:
              act.items?.map((i) => ({
                item_id: String(i.item || ''),
                qty: i.qty,
                uom: i.uom,
              })) || [],

            // Field Data
            planted_area: act.planted_area || '',
            water_volume: act.water_volume || '',
            well_id: act.well ? String(act.well) : '',
            is_solar_powered: act.irrigation_details?.is_solar_powered || false,
            diesel_qty: act.irrigation_details?.diesel_qty || '',
            harvest_quantity: act.harvest_quantity || act.harvested_qty || '', // Backward compat
            product_id: act.product_id ? String(act.product_id) : '',

            // Perennial
            tree_count_delta: act.tree_count_delta || 0,
            tree_loss_reason: act.tree_loss_reason ? String(act.tree_loss_reason) : '',
            serviceRows:
              act.service_counts?.map((s) => ({
                varietyId: String(s.variety_id || ''),
                locationId: String(s.location_id || ''),
                serviceCount: s.service_count,
                notes: s.notes || '',
              })) || [],
          }

          setForm((prev) => ({ ...prev, ...hydratedForm }))
        }
      } catch (err) {
        logRuntimeError('DAILY_LOG_DRAFT_LOAD_FAILED', err, { draftId })
        addToast('فشل في استرداد السجل من الخادم', 'error')
      } finally {
        setLoading(false)
      }
    }

    loadServerDraft()
  }, [draftId, user, setForm, addToast])

  // [CASCADE FETCH] Load Crops & Tasks when Farm changes
  useEffect(() => {
    const fetchFarmResources = async () => {
      if (!form.farm) {
        setLookups((prev) => ({ ...prev, crops: [], tasks: [] }))
        return
      }

      try {
        const [cropsRes, tasksRes] = await Promise.all([
          Crops.list({ farm_id: form.farm }),
          Tasks.list({ farm_id: form.farm }),
        ])

        const crops = cropsRes.data?.results || cropsRes.data || []
        const tasks = tasksRes.data?.results || tasksRes.data || []

        setLookups((prev) => ({ ...prev, crops, tasks }))

        // [OFFLINE v4] Seed per-farm tasks and crops into Dexie
        seedLookupCacheWithMeta(`crops_${form.farm}`, crops, { farm_scope: form.farm }).catch(() => {})
        seedLookupCacheWithMeta(`tasks_${form.farm}`, tasks, { farm_scope: form.farm }).catch(() => {})
        setFreshness('farm', { tone: 'emerald', label: 'حديثة', cachedAt: new Date().toISOString() })

      } catch (err) {
        logRuntimeError('DAILY_LOG_FARM_RESOURCES_FAILED', err, { farm_id: form.farm })

        // [OFFLINE v4] Fallback to Dexie cache when offline
        const [cachedCrops, cachedTasks] = await Promise.all([
          loadCachedLookup(`crops_${form.farm}`, 'farm'),
          loadCachedLookup(`tasks_${form.farm}`, 'farm'),
        ])

        if (cachedCrops || cachedTasks) {
          setLookups((prev) => ({
            ...prev,
            crops: cachedCrops || prev.crops,
            tasks: cachedTasks || prev.tasks,
          }))
          addToast('تم تحميل المهام والمحاصيل من الذاكرة المحلية (وضع عدم الاتصال).', 'warning')
        } else {
          addToast('فشل تحميل المحاصيل والمهام لهذه المزرعة', 'error')
        }
      }
    }

    fetchFarmResources()
  }, [form.farm, addToast, loadCachedLookup, setFreshness])

  // [AGRI-GUARDIAN] Launchpad Auto-Task Selection (ARCHETYPE-DRIVEN 100/100)
  useEffect(() => {
    const launchpadData = location.state?.launchpadData
    if (lookups.tasks?.length > 0 && !form.task) {
      let taskMatch = null

      // Phase 3: Try to match by strict Archetype first (e.g. PERENNIAL_SERVICE or BIOLOGICAL_ADJUSTMENT)
      if (launchpadData?.requestedArchetype) {
        taskMatch = lookups.tasks.find((t) => t.archetype === launchpadData.requestedArchetype)
      }

      // Fallback for legacy calls
      if (!taskMatch && launchpadData?.requestedTaskName) {
        taskMatch = lookups.tasks.find((t) =>
          String(t.name).includes(launchpadData.requestedTaskName),
        )
      }

      if (taskMatch) {
        setForm((prev) => ({ ...prev, task: String(taskMatch.id) }))
      }
    }
  }, [lookups.tasks, location.state, form.task, setForm])

  // [CASCADE FETCH] Load Locations, Wells & Assets when Farm changes
  // [AGRI-GUARDIAN FIX] Assets are fetched here with explicit farm_id to avoid
  // the race condition where Assets.list() on mount returns empty because
  // userFarmIds hasn't been populated yet in AuthContext.
  useEffect(() => {
    const fetchLocationsWellsAndAssets = async () => {
      if (!form.farm) {
        setLookups((prev) => ({ ...prev, locations: [], wells: [], assets: [] }))
        return
      }

      try {
        // Fetch all three in parallel with explicit farm_id.
        // Never block locations/tasks flow when wells endpoint fails.
        const [locRes, wellsRes, assetsRes] = await Promise.allSettled([
          Locations.list({ farm_id: form.farm }),
          LocationWells.list({ farm_id: form.farm }),
          Assets.list({ farm_id: form.farm }),
        ])
        const readPayload = (result) =>
          result.status === 'fulfilled'
            ? result.value?.data?.results || result.value?.data || []
            : []
        const locData = readPayload(locRes)
        const wellsData = readPayload(wellsRes)
        const assetsData = readPayload(assetsRes)
        setLookups((prev) => ({
          ...prev,
          locations: locData,
          wells: wellsData,
          assets: assetsData,
        }))

        // [OFFLINE v4] Seed caches
        if (locData.length) {
          seedLookupCacheWithMeta(`locations_${form.farm}`, locData, { farm_scope: form.farm }).catch(() => {})
        }
        if (wellsData.length) {
          seedLookupCacheWithMeta(`wells_${form.farm}`, wellsData, { farm_scope: form.farm }).catch(() => {})
        }
        if (assetsData.length) {
          seedLookupCacheWithMeta(`assets_${form.farm}`, assetsData, { farm_scope: form.farm }).catch(() => {})
        }
        setFreshness('locations', { tone: 'emerald', label: 'حديثة', cachedAt: new Date().toISOString() })
      } catch (err) {
        logRuntimeError('DAILY_LOG_LOCATIONS_WELLS_ASSETS_FAILED', err, { farm_id: form.farm })

        // [OFFLINE v4] Fallback to Dexie cache
        const [cachedLocs, cachedWells, cachedAssets] = await Promise.all([
          loadCachedLookup(`locations_${form.farm}`, 'locations'),
          loadCachedLookup(`wells_${form.farm}`, 'locations'),
          loadCachedLookup(`assets_${form.farm}`, 'locations'),
        ])

        if (cachedLocs || cachedWells || cachedAssets) {
          setLookups((prev) => ({
            ...prev,
            locations: cachedLocs || prev.locations,
            wells: cachedWells || prev.wells,
            assets: cachedAssets || prev.assets,
          }))
          addToast('تم تحميل بيانات المواقع والآبار من الذاكرة المحلية.', 'warning')
        } else {
          addToast('فشل تحميل المواقع أو الآبار لهذه المزرعة', 'error')
        }
      }

    }

    fetchLocationsWellsAndAssets()
  }, [form.farm, addToast, loadCachedLookup, setFreshness])

  // [CASCADE FETCH] Load Varieties & Products when Crop changes
  useEffect(() => {
    const fetchVarietiesAndProducts = async () => {
      if (!form.crop) {
        setLookups((prev) => ({
          ...prev,
          varieties: [],
          treeVarietySummary: [],
          varietiesMeta: {
            usedFallback: false,
            emptyReason: '',
            selectedLocationIds: [],
            diagnostics: null,
          },
          products: [],
        }))
        return
      }

      const selectedLocationIds = Array.isArray(form.locations)
        ? form.locations.map((locationId) => String(locationId)).filter(Boolean)
        : []
      const locationScopedVarietyKey = `varieties_${form.crop}_${selectedLocationIds.join('_') || 'all'}`

      try {
        const varietyParams = {
          crop: form.crop,
          crop_id: form.crop, // [ZENITH 11.5] التوافق المزدوج
          ...(form.farm ? { farm_id: form.farm } : {}),
          // [STOCK-SYNC FIX] إرسال location_ids ليُعيد الباكند الأصناف من LocationTreeStock أيضاً
          ...(selectedLocationIds.length > 0 ? { location_ids: selectedLocationIds.join(',') } : {}),
        }
        const [varRes, prodRes, summaryRes] = await Promise.allSettled([
          CropVarieties.list(varietyParams),
          CropProducts.list({ crop: form.crop }),
          selectedLocationIds.length > 0
            ? TreeInventorySummary.locationVarietySummary({
              farm_id: form.farm,
              crop_id: form.crop,
              location_ids: selectedLocationIds.join(','),
            })
            : Promise.resolve({ data: { results: [] } }),
        ])
        const rawLocationAwareVarieties =
          varRes.status === 'fulfilled' ? varRes.value.data?.results || varRes.value.data || [] : []
        let chosenVarieties = rawLocationAwareVarieties
        let usedFallback = false
        let emptyReason = ''

        if (selectedLocationIds.length > 0 && rawLocationAwareVarieties.length === 0) {
          const fallbackResponse = await CropVarieties.list({
            crop: form.crop,
            ...(form.farm ? { farm_id: form.farm } : {}),
          })
          const rawFallbackVarieties = fallbackResponse.data?.results || fallbackResponse.data || []
          if (rawFallbackVarieties.length > 0) {
            chosenVarieties = rawFallbackVarieties
            usedFallback = true
            emptyReason = 'تعذر تحميل تغطية الأصناف حسب الموقع، وتم عرض أصناف المحصول المتاحة كقائمة احتياطية.'
            // تم الإسكات عمداً (Silenced) لأن مسودات عدم الاتصال تمر بهذه الحالة بشكل طبيعي
          } else {
            emptyReason = 'لا توجد أصناف أشجار فعالة مرتبطة بالمواقع المختارة لهذا المحصول.'
          }
        }

        const { varieties, diagnostics } = normalizeVarietyPayload(chosenVarieties)
        const cropScopedVarieties = varieties.filter((variety) => {
          const varietyCropId = variety?.crop?.id || variety?.crop || variety?.crop_id || null
          if (form.crop == null || form.crop === '') {
            return true
          }
          if (varietyCropId == null) {
            // [FIX]: Backend returns varieties with crop__isnull=True. We must keep them!
            return true
          }
          const matches = String(varietyCropId) === String(form.crop)
          if (!matches) {
            diagnostics.crossCropRows += 1
          }
          return matches
        })
        const treeVarietySummary =
          summaryRes.status === 'fulfilled'
            ? summaryRes.value.data?.results || summaryRes.value.data || []
            : []

        if (summaryRes.status === 'rejected' && selectedLocationIds.length > 0) {
          // تم تجاهل الخطأ لأن الباكند قد يرفض بعض المواقع المسجلة في المسودات (Drafts)
          // والنظام مصمم بحيث يعتمد على Fallback بكل أمان دون التسبب بإحباط المستخدم.
        }

        if (
          selectedLocationIds.length > 0 &&
          diagnostics.missingLocationCoverageRows > 0 &&
          !usedFallback
        ) {
          logRuntimeError(
            'DAILY_LOG_VARIETIES_LOCATION_SHAPE_INCOMPLETE',
            new Error('Variety payload missing location-aware coverage fields.'),
            {
              crop_id: form.crop,
              farm_id: form.farm,
              selected_location_ids: selectedLocationIds,
              varieties_count: varieties.length,
              missing_location_coverage_rows: diagnostics.missingLocationCoverageRows,
            },
          )
        }

        if (diagnostics.crossCropRows > 0) {
          logRuntimeError(
            'DAILY_LOG_VARIETIES_CROSS_CROP_FILTERED',
            new Error('Filtered cross-crop varieties from daily-log lookup payload.'),
            {
              crop_id: form.crop,
              farm_id: form.farm,
              selected_location_ids: selectedLocationIds,
              filtered_rows: diagnostics.crossCropRows,
              varieties_count: cropScopedVarieties.length,
            },
          )
        }

        setLookups((prev) => ({
          ...prev,
          varieties: cropScopedVarieties,
          treeVarietySummary,
          varietiesMeta: {
            usedFallback,
            emptyReason,
            selectedLocationIds,
            diagnostics: {
              ...diagnostics,
              varietiesCount: cropScopedVarieties.length,
              treeSummaryCount: Array.isArray(treeVarietySummary) ? treeVarietySummary.length : 0,
            },
          },
          products:
            prodRes.status === 'fulfilled'
              ? prodRes.value.data?.results || prodRes.value.data || []
              : [],
        }))

        // [OFFLINE v4] Seed caches
        if (cropScopedVarieties.length) {
          seedLookupCacheWithMeta(locationScopedVarietyKey, cropScopedVarieties, {
            farm_scope: form.farm,
          }).catch(() => {})
          seedLookupCacheWithMeta(`varieties_${form.crop}`, cropScopedVarieties, {
            farm_scope: form.farm,
          }).catch(() => {})
        }
        if (Array.isArray(treeVarietySummary) && treeVarietySummary.length > 0) {
          const summaryCacheKey = `tree_summary_${form.crop}_${selectedLocationIds.join('_') || 'all'}`
          seedLookupCacheWithMeta(summaryCacheKey, treeVarietySummary, {
            farm_scope: form.farm,
          }).catch(() => {})
          // Also seed the general crop summary for broader fallback
          seedLookupCacheWithMeta(`tree_summary_${form.crop}`, treeVarietySummary, {
            farm_scope: form.farm,
          }).catch(() => {})
        }
        const productsData =
          prodRes.status === 'fulfilled' ? prodRes.value.data?.results || prodRes.value.data || [] : []
        if (productsData.length)
          seedLookupCacheWithMeta(`products_${form.crop}`, productsData, {
            farm_scope: form.farm,
          }).catch(() => {})
        setFreshness('crop', { tone: 'emerald', label: 'حديثة', cachedAt: new Date().toISOString() })
      } catch (err) {
        logRuntimeError('DAILY_LOG_VARIETIES_PRODUCTS_FAILED', err, {
          crop_id: form.crop,
          farm_id: form.farm,
          location_ids: form.locations,
        })

        // [OFFLINE v4] Fallback to Dexie cache
        const [cachedVarieties, cachedProducts, cachedSummary] = await Promise.all([
          loadCachedLookup(locationScopedVarietyKey, 'crop').then((data) =>
            data || loadCachedLookup(`varieties_${form.crop}`, 'crop'),
          ),
          loadCachedLookup(`products_${form.crop}`, 'crop'),
          loadCachedLookup(`tree_summary_${form.crop}_${selectedLocationIds.join('_') || 'all'}`, 'crop').then((data) =>
            data || loadCachedLookup(`tree_summary_${form.crop}`, 'crop')
          ),
        ])

        if (cachedVarieties || cachedProducts || cachedSummary) {
          setLookups((prev) => ({
            ...prev,
            varieties: cachedVarieties || prev.varieties,
            products: cachedProducts || prev.products,
            treeVarietySummary: cachedSummary || prev.treeVarietySummary,
          }))
          addToast('تم تحميل الأصناف والمنتجات من الذاكرة المحلية.', 'warning')
        } else {
          addToast('فشل تحميل أصناف أو منتجات الحصاد للمحصول المحدد', 'error')
        }
      }

    }
        // [ZENITH 11.5 OMEGA-Z] CRYSTAL-AST-SYNC
        StateSync.reportIntegrity('DailyLogUpdate', { state: 'Refresh' }).catch(() => {})


    fetchVarietiesAndProducts()
  }, [form.crop, form.farm, form.locations, addToast, loadCachedLookup, setFreshness])

  useEffect(() => {
    // [FIX]: يجب أن تشمل القائمة البيضاء أصناف الجرد الشجري أيضاً وليس فقط كتالوج CropVariety
    // لأن بعض الأصناف موجودة في LocationTreeStock/BiologicalAssetCohort فقط
    const catalogIds = (lookups.varieties || []).map((variety) => String(variety.id))
    const treeCensusIds = (lookups.treeVarietySummary || [])
      .filter((entry) => entry?.variety_id != null)
      .map((entry) => String(entry.variety_id))
    const availableVarietyIds = new Set([...catalogIds, ...treeCensusIds])
    if (!form.variety && (!Array.isArray(form.serviceRows) || form.serviceRows.length === 0)) {
      return
    }

    if (form.variety && !availableVarietyIds.has(String(form.variety))) {
      setForm((prev) => ({ ...prev, variety: '' }))
    }

    if (Array.isArray(form.serviceRows) && form.serviceRows.some((row) => row.varietyId && !availableVarietyIds.has(String(row.varietyId)))) {
      setForm((prev) => ({
        ...prev,
        serviceRows: (prev.serviceRows || []).map((row) =>
          row.varietyId && !availableVarietyIds.has(String(row.varietyId))
            ? { ...row, varietyId: '' }
            : row,
        ),
      }))
    }
  }, [lookups.varieties, lookups.treeVarietySummary, form.variety, form.serviceRows, setForm])

  useEffect(() => {
    const resolveLinkedPlan = async () => {
      if (
        !form.farm ||
        !form.crop ||
        !form.locations ||
        form.locations.length === 0 ||
        !form.date
      ) {
        setLinkedCropPlan(null)
        return
      }
      try {
        setLinkageLoading(true)
        const response = await CropPlans.list({ farm: form.farm, page_size: 300 })
        const plans = response?.data?.results || response?.data || []
        // Safely parse YYYY-MM-DD ignoring timezone offsets that shift dates on mobile
        const parseDateOnly = (dStr) => {
          if (!dStr) return null
          const [y, m, d] = String(dStr).split('T')[0].split('-')
          if (!y || !m || !d) return new Date(dStr)
          return new Date(Number(y), Number(m) - 1, Number(d))
        }

        const selectedDate = parseDateOnly(form.date)
        if (selectedDate) selectedDate.setHours(12, 0, 0, 0)

        // [DIAGNOSTIC] تسجيل تفاصيل لتصحيح الأخطاء عند عدم العثور على خطة مطابقة
        const diagnostics = []
        const match = plans.find((plan) => {
          const cropMatch = String(plan.crop?.id || plan.crop) === String(form.crop)
          if (!cropMatch) {
            diagnostics.push({ plan_id: plan.id, name: plan.name, reason: 'CROP_MISMATCH', plan_crop: plan.crop, form_crop: form.crop })
            return false
          }

          // Allow match if plan has no locations (farm-wide plan) OR any activity location overlaps
          const planLocs = Array.isArray(plan.locations)
            ? plan.locations.map((l) => String(l.id || l)).filter(Boolean)
            : []
          if (planLocs.length > 0) {
            const hasLocationMatch = form.locations.some((locId) => planLocs.includes(String(locId)))
            if (!hasLocationMatch) {
              diagnostics.push({ plan_id: plan.id, name: plan.name, reason: 'LOCATION_MISMATCH', plan_locs: planLocs, form_locs: form.locations })
              return false
            }
          }
          // If planLocs is empty, the plan is farm-wide → pass location check

          const planStatus = String(plan.status || '').toUpperCase()
          if (planStatus !== 'ACTIVE') {
            diagnostics.push({ plan_id: plan.id, name: plan.name, reason: 'STATUS_NOT_ACTIVE', status: plan.status })
            return false
          }

          const start = parseDateOnly(plan.start_date)
          const end = parseDateOnly(plan.end_date)
          if (!start || !end || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
            diagnostics.push({ plan_id: plan.id, name: plan.name, reason: 'INVALID_DATES', start_date: plan.start_date, end_date: plan.end_date })
            return false
          }
          // Zero out time just to be absolutely sure
          start.setHours(0, 0, 0, 0)
          end.setHours(23, 59, 59, 999)

          const inRange = selectedDate >= start && selectedDate <= end
          if (!inRange) {
            diagnostics.push({ plan_id: plan.id, name: plan.name, reason: 'DATE_OUT_OF_RANGE', plan_start: plan.start_date, plan_end: plan.end_date, form_date: form.date })
            return false
          }
          return true
        })

        if (!match && plans.length > 0) {
          console.warn('[CropPlan-Linkage] لم يتم العثور على خطة مطابقة. التشخيص:', {
            form: { farm: form.farm, crop: form.crop, locations: form.locations, date: form.date },
            total_plans: plans.length,
            diagnostics,
          })
        }

        setLinkedCropPlan(match || null)
      } catch (error) {
        console.error('[CropPlan-Linkage] خطأ في الربط:', error)
        setLinkedCropPlan(null)
      } finally {
        setLinkageLoading(false)
      }
    }
    resolveLinkedPlan()
  }, [form.crop, form.date, form.farm, form.locations])

  const selectedTask = lookups.tasks.find((task) => String(task.id) === String(form.task)) || null
  const taskContext = useMemo(() => {
    const contract =
      selectedTask?.effective_task_contract || selectedTask?.task_contract || {}
    const smartCards =
      contract && typeof contract.smart_cards === 'object' && contract.smart_cards !== null
        ? contract.smart_cards
        : {}
    const cardEnabled = (config) =>
      typeof config === 'object' && config !== null ? Boolean(config.enabled) : Boolean(config)
    const enabledCards = {
      execution: true,
      control: true,
      variance: true,
      materials: cardEnabled(smartCards.materials),
      labor: cardEnabled(smartCards.labor),
      well: cardEnabled(smartCards.well),
      machinery: cardEnabled(smartCards.machinery),
      fuel: cardEnabled(smartCards.fuel),
      perennial: cardEnabled(smartCards.perennial),
      harvest: cardEnabled(smartCards.harvest),
    }
    return {
      taskName: selectedTask?.name || '',
      enabledCards,
      requiredInputs: {
        requiresWell: Boolean(selectedTask?.requires_well),
        requiresMachinery: Boolean(selectedTask?.requires_machinery),
        requiresTreeCount: Boolean(selectedTask?.requires_tree_count),
        isPerennialProcedure: Boolean(selectedTask?.is_perennial_procedure),
        isHarvestTask: Boolean(selectedTask?.is_harvest_task),
        requiresArea: Boolean(selectedTask?.requires_area),
      },
      modeVisibility: contract.mode_visibility || {},
      inputProfile: contract.input_profile || {},
      laborPolicy: {
        registeredAllowed:
          smartCards.labor?.policy?.registered_allowed !== false,
        casualBatchAllowed:
          smartCards.labor?.policy?.casual_batch_allowed !== false,
        surrahRequired: enabledCards.labor,
      },
      perennialPolicy: {
        rowLocationRequired:
          enabledCards.perennial && Array.isArray(form.locations) && form.locations.length > 1,
        selectedLocationIds: Array.isArray(form.locations)
          ? form.locations.map((locationId) => String(locationId))
          : [],
      },
    }
  }, [form.locations, selectedTask])

  useEffect(() => {
    const irrigationEnabled = Boolean(
      taskContext.enabledCards.well || taskContext.requiredInputs.requiresWell,
    )
    const machineryEnabled = Boolean(
      taskContext.enabledCards.machinery ||
        taskContext.enabledCards.fuel ||
        taskContext.requiredInputs.requiresMachinery,
    )

    const selectedLocationIds = Array.isArray(form.locations)
      ? form.locations.map((locationId) => String(locationId))
      : []
    const linkedWellIds = (lookups.wells || [])
      .filter((link) => selectedLocationIds.includes(String(link.location || link.location_id)))
      .map((link) => String(link.well || link.well_id))

    const validWellIds = new Set(
      (lookups.assets || [])
        .filter((asset) => {
          if (!isWellLikeAsset(asset)) {
            return false
          }
          if (linkedWellIds.length > 0) {
            return linkedWellIds.includes(String(asset.id))
          }
          return String(getAssetFarmId(asset) || '') === String(form.farm)
        })
        .map((asset) => String(asset.id)),
    )

    const validAssetIds = new Set(
      (lookups.assets || [])
        .filter((asset) => {
          const farmId = getAssetFarmId(asset)
          if (form.farm && farmId && String(farmId) !== String(form.farm)) {
            return false
          }
          return isOperationalMachineAsset(asset)
        })
        .map((asset) => String(asset.id)),
    )
    const wellOptionsLoaded = Array.isArray(lookups.assets) && lookups.assets.length > 0
    const assetOptionsLoaded = Array.isArray(lookups.assets) && lookups.assets.length > 0

    const shouldClearWell =
      Boolean(form.well_id) &&
      (!irrigationEnabled || (wellOptionsLoaded && !validWellIds.has(String(form.well_id))))
    const shouldClearAsset =
      Boolean(form.asset_id) &&
      (!machineryEnabled || (assetOptionsLoaded && !validAssetIds.has(String(form.asset_id))))

    if (!shouldClearWell && !shouldClearAsset) {
      return
    }

    setForm((prev) => {
      const next = { ...prev }
      if (shouldClearWell) {
        next.well_id = ''
        next.well_reading = ''
        next.water_volume = ''
        next.is_solar_powered = false
        next.diesel_qty = ''
      }
      if (shouldClearAsset) {
        next.asset_id = ''
        next.asset = ''
        next.machine_hours = ''
        next.machine_meter_reading = ''
        next.fuel_consumed = ''
      }
      return next
    })
  }, [
    form.asset_id,
    form.farm,
    form.locations,
    form.well_id,
    lookups.assets,
    lookups.wells,
    setForm,
    taskContext.enabledCards.fuel,
    taskContext.enabledCards.machinery,
    taskContext.enabledCards.well,
    taskContext.requiredInputs.requiresMachinery,
    taskContext.requiredInputs.requiresWell,
  ])

  useEffect(() => {
    setValidationPolicy({
      requireLaborStep: taskContext.enabledCards.labor,
      laborPolicy: taskContext.laborPolicy,
    })
  }, [setValidationPolicy, taskContext])

  const perennialLogic = usePerennialLogic(form, setForm, lookups, strictErpMode, taskContext)
  const handleNextStep = () => {
    if (step === 2 && !taskContext.enabledCards.labor) {
      setStep((prev) => prev + 1)
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }
    nextStep()
  }
  const buildTaskAwareActivityPayload = () => {
    const cleanedForm = scrubPayload(form)
    const enabledCards = taskContext.enabledCards || {}
    const requiredInputs = taskContext.requiredInputs || {}

    if (!taskContext.enabledCards.labor) {
      cleanedForm.team = []
      cleanedForm.employees = []
      cleanedForm.employees_payload = []
    }

    if (!(enabledCards.well || requiredInputs.requiresWell)) {
      cleanedForm.well_id = null
      cleanedForm.well_asset_id = null
      cleanedForm.well_reading = null
      cleanedForm.water_volume = null
      cleanedForm.is_solar_powered = false
      cleanedForm.diesel_qty = null
    }

    if (!(enabledCards.machinery || enabledCards.fuel || requiredInputs.requiresMachinery)) {
      cleanedForm.asset = null
      cleanedForm.asset_id = null
      cleanedForm.machine_hours = null
      cleanedForm.machine_meter_reading = null
      cleanedForm.start_meter = null
      cleanedForm.end_meter = null
      cleanedForm.fuel_consumed = null
    }

    if (!enabledCards.materials) {
      cleanedForm.items = []
      cleanedForm.fertilizer_quantity = null
      cleanedForm.fertilizer_uom = null
    }

    if (!(enabledCards.harvest || requiredInputs.isHarvestTask)) {
      cleanedForm.product_id = null
      cleanedForm.product = null
      cleanedForm.harvested_item = ''
      cleanedForm.harvested_qty = null
      cleanedForm.harvest_quantity = null
      cleanedForm.batch_number = ''
      cleanedForm.harvest_uom = null
    }

    if (!(enabledCards.perennial || requiredInputs.requiresTreeCount || requiredInputs.isPerennialProcedure)) {
      cleanedForm.activity_tree_count = null
      cleanedForm.tree_count_delta = 0
      cleanedForm.tree_loss_reason = null
      cleanedForm.tree_loss_reason_id = null
      cleanedForm.serviceRows = []
      cleanedForm.service_counts = []
    }

    if (!(requiredInputs.requiresArea || enabledCards.perennial)) {
      cleanedForm.planted_area = null
    }

    return cleanedForm
  }

  const { fetchSuggestions } = useSmartContext(form, setForm, lookups)

  // [SUBMISSION HANDLER]
  const handleSubmit = async () => {
    const extractFirstErrorMessage = (errors) => {
      if (!errors) return ''
      if (typeof errors === 'string') return errors
      if (Array.isArray(errors)) {
        return extractFirstErrorMessage(errors[0])
      }
      if (typeof errors === 'object') {
        const firstKey = Object.keys(errors)[0]
        return extractFirstErrorMessage(errors[firstKey])
      }
      return ''
    }

    // 1. [AGRI-GUARDIAN] Strict Validation (Triangle of Consistency)
    const logicErrors = perennialLogic.validatePerennialCompliance()
    if (logicErrors) {
      const firstErrorMsg =
        extractFirstErrorMessage(logicErrors) || 'يرجى مراجعة الحقول الإلزامية في تفاصيل السجل.'
      addToast(firstErrorMsg, 'error')
      if (import.meta.env.DEV) {
        console.warn('Logic Validation Failed:', logicErrors)
      }
      return
    }

    // [AGRI-GUARDIAN] Cross-Plan Validation Policy
    // [AREA GOVERNANCE] Soft warning when area is enabled but not filled
    if (
      taskContext.requiredInputs.requiresArea &&
      (!form.planted_area || Number(form.planted_area) <= 0)
    ) {
      addToast('تنبيه: المساحة المنفذة غير مُدخلة. يمكنك المتابعة بدون إدخالها.', 'warning')
    }

    if (!allowCrossPlanActivities && linkedCropPlan && form.locations?.length > 0) {
      const planLocIds = Array.isArray(linkedCropPlan.locations)
        ? linkedCropPlan.locations.map((l) => String(l.id || l))
        : []

      const hasOutsideLocations = form.locations.some(
        (locId) => !planLocIds.includes(String(locId)),
      )

      if (hasOutsideLocations) {
        addToast(
          'السياسات تمنع جمع مواقع من خطط مختلفة في نشاط واحد (تسرب مالي/Financial Leakage). يرجى تفعيل الخيار من إعدادات الحوكمة أو تقسيم النشاط.',
          'error',
        )
        return
      }
    }

    // Check network
    if (!isOnline) {
      const queued = await queueLogSubmission(buildTaskAwareActivityPayload(), {
        meta: {
          lookup_snapshot_version: lookupSnapshotVersion,
          freshness_summary: lookupFreshness,
          task_contract_snapshot: taskContext,
          remote_site_policy: {
            remote_site: remoteSite,
            weekly_remote_review_required: weeklyRemoteReviewRequired,
          },
          taskName: selectedTask?.name || '',
        },
      })
      if (queued) {
        addToast('تم حفظ السجل في القائمة المؤجلة (Offline). سيتم رفعه تلقائياً.', 'warning')
        await refreshDrafts()
        await startNewDraft({ preserveContext: true })
      } else {
        addToast('فشل الحفظ المحلي. تأكد من مساحة التخزين.', 'error')
      }
      return
    }

    
    // [ZENITH 11.5 OMEGA-Z] SENTINEL-COHORT ANALYSIS
    const sentinelReport = SentinelGuard.analyzeActivity(buildTaskAwareActivityPayload(), { 
        lookups, 
        taskContext 
    })
    
    if (sentinelReport.hasAnomalies) {
        const severeAnomaly = sentinelReport.anomalies.find(a => a.severity === 'HIGH' || a.severity === 'CRITICAL')
        if (severeAnomaly) {
            addToast(`تنبيه أمني: ${severeAnomaly.message}`, 'error')
            // If critical error, we might want to block? For now, just a strong warning
            if (severeAnomaly.severity === 'CRITICAL') return
        } else {
            sentinelReport.anomalies.forEach(a => addToast(a.message, 'warning'))
        }
    }

    // Online Submit
    try {
      const logPayload = {
        farm: form.farm,
        log_date: form.date,
      }
      if (form.variance_note) {
        logPayload.variance_note = form.variance_note
      }
      const logResponse = await DailyLogs.create(logPayload)
      const logId = logResponse?.data?.id || logResponse?.id

      if (!logId) {
        throw new Error('فشل إنشاء سجل اليوم')
      }

      const activityPayload = {
        ...buildTaskAwareActivityPayload(),
        log_id: logId,
      }

      // [ZENITH 11.5 OMEGA-Z] CRYPTOGRAPHIC SEALING
      const auditSignature = await AuditLedger.signTransaction(activityPayload)
      activityPayload.audit_signature = auditSignature.fingerprint
      activityPayload.audit_metadata = auditSignature

      // [ZENITH 11.5 FIX] Strict Field Syncing & Decimal Precision (Max 4)
      if (activityPayload.asset_id && !activityPayload.asset) activityPayload.asset = activityPayload.asset_id
      if (activityPayload.well_id && !activityPayload.well_asset_id) activityPayload.well_asset_id = activityPayload.well_id
      
      // Ensure machine meter reading is treated as optional (null if empty)
      if (activityPayload.machine_meter_reading === '') activityPayload.machine_meter_reading = null

      if (!activityPayload.crop_plan_id && linkedCropPlan?.id) {
        activityPayload.crop_plan_id = linkedCropPlan.id
      }

      if (form.serviceRows && form.serviceRows.length > 0) {
        const singleLocationId =
          Array.isArray(form.locations) && form.locations.length === 1 ? form.locations[0] : null
        
        activityPayload.service_counts = form.serviceRows
          .filter(row => row.varietyId || row.serviceCount)
          .map((row) => ({
            variety_id: row.varietyId ? Number(row.varietyId) : null,
            location_id: (row.locationId || singleLocationId) ? Number(row.locationId || singleLocationId) : null,
            service_count: Number(row.serviceCount || 0),
            notes: row.notes || '',
          }))

        if (!activityPayload.variety_id && activityPayload.service_counts.length > 0) {
          activityPayload.variety_id = activityPayload.service_counts[0].variety_id
        }

        const totalServiced = activityPayload.service_counts.reduce(
          (sum, row) => sum + (row.service_count || 0),
          0,
        )
        if (totalServiced > 0) {
          activityPayload.activity_tree_count = totalServiced
        }
      }

      
      await DailyLogs.addActivity(activityPayload)
      // [ZENITH 11.5 OMEGA-Z] TOPIC-CACHE LEARNING
      TopicCacheManager.learnFromActivity(activityPayload)


      addToast('تم حفظ النشاط بنجاح!', 'success')
      await resetForm()
      navigate('/daily-log-history')
    } catch (err) {
      logRuntimeError('DAILY_LOG_SUBMIT_FAILED', err, { farm_id: form.farm, crop_id: form.crop })
      // [AGRI-GUARDIAN] Robust error extraction for 400 validation errors
      const errorMsg = extractApiError(err, 'حدث خطأ أثناء الحفظ. حاول مرة أخرى.')

      addToast(errorMsg, 'error')
      // If error is 500/Network, offer to queue?
      if (!navigator.onLine) {
        queueLogSubmission(buildTaskAwareActivityPayload(), {
          meta: {
            lookup_snapshot_version: lookupSnapshotVersion,
            freshness_summary: lookupFreshness,
            task_contract_snapshot: taskContext,
            remote_site_policy: {
              remote_site: remoteSite,
              weekly_remote_review_required: weeklyRemoteReviewRequired,
            },
            taskName: selectedTask?.name || '',
          },
        })
      }
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-slate-900">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-12 w-12 bg-gray-200 dark:bg-slate-700 rounded-full mb-4"></div>
          <div className="h-4 w-48 bg-gray-200 dark:bg-slate-700 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 pt-6 px-4 text-gray-900 dark:text-slate-100">


      {/* [AGRI-GUARDIAN] Launchpad Context Banner */}
      {location.state?.launchpadData?.launchpadMetaData && (
        <div className="bg-emerald-50 dark:bg-emerald-900/20 border-l-4 border-emerald-500 p-4 mb-6 rounded shadow-sm max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-xl me-3">🚀</span>
            <div>
              <p className="text-sm font-bold text-emerald-800 dark:text-emerald-300">
                وضع الإدخال السريع (Launchpad Mode)
              </p>
              <p className="text-xs text-emerald-700 dark:text-emerald-400">
                أنت الآن تسجل عملية لدفعة الأشجار:{' '}
                <strong>{location.state.launchpadData.launchpadMetaData.batch_name}</strong>
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/tree-census')}
            className="text-xs bg-white dark:bg-slate-800 px-2 py-1 rounded border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-50"
          >
            تغيير الدفعة
          </button>
        </div>
      )}

      {location.state?.launchpadData?.launchSurface === 'harvest-entry' && (
        <div
          data-testid="daily-log-launch-banner"
          className="bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500 p-4 mb-6 rounded shadow-sm max-w-4xl mx-auto"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-green-800 dark:text-green-300">
                مسار سريع لإدخال الإنتاج والحصاد
              </p>
              <p className="mt-1 text-xs text-green-700 dark:text-green-400">
                تم توجيهك إلى السجل اليومي لأن الإدخال التنفيذي للحصاد يتم من هنا. شاشة
                التقارير للقراءة والتوليد فقط، بينما يبقى المسار المالي محكومًا وفق {modeLabel}.
              </p>
            </div>
            <span className="rounded-full bg-white/80 px-2 py-1 text-xs font-semibold text-green-800 dark:bg-slate-900/50 dark:text-green-200">
              {isStrictMode ? 'STRICT' : 'SIMPLE'}
            </span>
          </div>
        </div>
      )}

      {/* 🚀 Compact Action & Sync Bar */}
      <div className="max-w-4xl mx-auto mb-6 flex flex-col md:flex-row items-center justify-between gap-4 bg-white dark:bg-slate-800 p-3 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
        
        {/* Quick Actions */}
        <div className="flex items-center gap-2">
          {!isStrictMode && (
            <>
              <button
                type="button"
                onClick={() => navigate('/daily-log/harvest', { state: { source: 'daily-log', requestedFrom: 'simple-banner' } })}
                className="flex items-center gap-1.5 rounded-xl bg-slate-50 border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-emerald-900/40 dark:hover:text-emerald-400"
              >
                <span>🌾</span> مسار الحصاد
              </button>
              <button
                type="button"
                onClick={() => navigate('/inventory/custody', { state: { source: 'daily-log' } })}
                className="flex items-center gap-1.5 rounded-xl bg-slate-50 border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-sky-50 hover:text-sky-700 hover:border-sky-200 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-sky-900/40 dark:hover:text-sky-400"
              >
                <span>📦</span> مراجعة العهدة
              </button>
              <button
                type="button"
                onClick={() => navigate('/reports', { state: { source: 'daily-log', simplePreset: 'daily_execution' } })}
                className="flex items-center gap-1.5 rounded-xl bg-slate-50 border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <span>📊</span> التقارير
              </button>
            </>
          )}
          {(remoteSite || weeklyRemoteReviewRequired) && (
            <span className="flex items-center gap-1 rounded-xl bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" title="وضع الموقع الجغرافي البعيد نشط">
              📍 موقع بعيد
            </span>
          )}
        </div>

        {/* Sync & Draft Status */}
        <div className="flex items-center gap-3">
          
          {/* Drafts Dropdown / Pills */}
          <div className="relative group">
            {form.draft_uuid ? (
              <div className="flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200 shadow-sm cursor-default">
                <span>📝 {lookups.tasks?.find(t => String(t.id) === String(form.task))?.name || form.draft_uuid.slice(0, 8)}</span>
                <button type="button" onClick={() => startNewDraft({ preserveContext: true })} className="mr-2 hover:text-sky-900 dark:hover:text-sky-100 transition-colors" title="استكشاف مسودة جديدة">➕</button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => startNewDraft({ preserveContext: true })}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 shadow-sm transition-colors"
              >
                ➕ مسودة جديدة
              </button>
            )}

            {/* Hover Tooltip/Dropdown for multiple drafts */}
            {drafts.length > 0 && (
               <div className="absolute left-0 top-full mt-2 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 dark:border-slate-700 dark:bg-slate-800">
                  <div className="text-[10px] font-bold text-slate-500 mb-2 px-2 flex justify-between">
                    <span>مسودات سابقة ({drafts.length})</span>
                    <button type="button" onClick={() => refreshDrafts()} className="hover:text-primary">🔄</button>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {drafts.map((draft) => {
                      const taskName = lookups.tasks?.find(t => String(t.id) === String(draft.data?.task))?.name || `مسودة ${draft.draft_uuid.slice(0, 5)}`;
                      return (
                        <button
                          key={draft.draft_uuid}
                          type="button"
                          onClick={() => resumeDraft(draft.draft_uuid)}
                          className={`w-full text-right rounded-lg px-2 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 flex justify-between items-center ${form.draft_uuid === draft.draft_uuid ? 'text-primary bg-primary/5 font-bold' : 'text-slate-700 dark:text-slate-300'}`}
                        >
                          <span className="truncate max-w-[130px]" title={taskName}>{taskName}</span>
                          <span className="text-[10px] opacity-70 whitespace-nowrap">{draft.log_date?.slice(5) || '--'}</span>
                        </button>
                      );
                    })}
                  </div>
               </div>
            )}
          </div>

          {/* Cloud Sync State */}
          <button 
             type="button"
             onClick={() => navigate('/settings?tab=offline', { state: { source: 'daily-log' } })}
             className="flex items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 shadow-sm transition-colors"
          >
            {failedDailyLogs > 0 ? (
               <><span className="text-rose-500 text-sm">⚠️</span> <span>{failedDailyLogs} مرفوضة</span></>
            ) : queuedDailyLogs > 0 ? (
               <><span className="text-amber-500 text-sm">☁️</span> <span>{queuedDailyLogs} قيد الانتظار</span></>
            ) : !isOnline ? (
               <><span className="text-slate-400 text-sm">☁️</span> <span>غير متصل (يُحفظ محلياً)</span></>
            ) : (
               <><span className="text-emerald-500 text-sm">☁️</span> <span>متزامن</span></>
            )}
          </button>
        </div>
      </div>

      {/* [AGRI-GUARDIAN] Rejected Log Sticky Banner */}
      {form.status === 'REJECTED' && form.rejection_reason && (
        <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-6 rounded shadow-sm max-w-4xl mx-auto sticky top-4 z-40 relative">
          <div className="flex">
            <div className="flex-shrink-0 mt-0.5">
              <span className="text-xl">⚠️</span>
            </div>
            <div className="ms-3">
              <h3 className="text-sm font-bold text-red-800 dark:text-red-300">
                تنبيه: تم إرجاع هذا السجل وتتطلب بياناته التعديل لإعادة التقديم
              </h3>
              <p className="text-sm text-red-700 dark:text-red-400 mt-1 whitespace-pre-wrap">
                <span className="font-semibold">سبب الرفض:</span> {form.rejection_reason}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Wizard UI */}
      <div className="flex justify-between items-center max-w-4xl mx-auto mb-6">
        <h1
          data-testid="daily-log-page-title"
          className="text-2xl font-bold text-gray-900 dark:text-slate-100"
        >
          سجل النشاط اليومي
        </h1>
        <button
          onClick={() => navigate(simpleHomeRoute)}
          className="text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition"
        >
          إلغاء الأمر
        </button>
      </div>

      <div className="max-w-4xl mx-auto mb-4">
        <div
          data-testid="linked-crop-plan-indicator"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm dark:border-emerald-800 dark:bg-emerald-900/20"
        >
          {linkageLoading ? (
            <span className="text-emerald-700 dark:text-emerald-300">
              جاري التحقق من الخطة الزراعية الفعّالة...
            </span>
          ) : linkedCropPlan ? (
            <div className="space-y-2">
              <span className="text-emerald-800 dark:text-emerald-300">
                الخطة المرتبطة تلقائيًا: <strong>{linkedCropPlan.name}</strong>
              </span>
              {/* [AGRI-GUARDIAN 102] Burn Rate Indicator */}
              {linkedCropPlan.budget_total > 0 && (
                <div className="flex items-center gap-3 mt-1">
                  {(() => {
                    const budget = Number(linkedCropPlan.budget_total || 0)
                    const actual = Number(
                      linkedCropPlan.actual_total || linkedCropPlan.cost_total || 0,
                    )
                    const pct = budget > 0 ? Math.round((actual / budget) * 100) : 0
                    const barColor =
                      pct > 100 ? 'bg-rose-500' : pct > 90 ? 'bg-amber-500' : 'bg-emerald-500'
                    const textColor =
                      pct > 100
                        ? 'text-rose-700 dark:text-rose-400'
                        : pct > 90
                          ? 'text-amber-700 dark:text-amber-400'
                          : 'text-emerald-700 dark:text-emerald-400'
                    return (
                      <>
                        <div className="flex-1 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${barColor}`}
                            style={{ width: `${Math.min(pct, 100)}%` }}
                          />
                        </div>
                        <span className={`text-xs font-bold ${textColor} whitespace-nowrap`}>
                          {pct}% مستهلك
                          {pct > 90 && ' ⚠️'}
                        </span>
                      </>
                    )
                  })()}
                </div>
              )}
              {(!linkedCropPlan.budget_total || linkedCropPlan.budget_total === 0) && (
                <div className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                  ⚠️ لم تُحدد ميزانية لهذه الخطة بعد
                </div>
              )}
            </div>
          ) : (
            <span className="text-amber-700 dark:text-amber-300">
              لا توجد خطة زراعية فعّالة مطابقة حاليًا (مزرعة/محصول/موقع/تاريخ).
            </span>
          )}
        </div>
      </div>

      <DailyLogSmartCard form={form} linkedCropPlan={linkedCropPlan} offlineDrafts={drafts} />

      <DailyLogWizard
        form={form}
        updateField={updateField}
        errors={errors}
        step={step}
        nextStep={handleNextStep}
        prevStep={prevStep}
        isSubmitting={isSubmitting}
        lookups={lookups}
        onSubmit={handleSubmit}
        // [Agri-Guardian] Logic Injection

        // [Agri-Guardian] Logic Injection
        perennialLogic={perennialLogic}
        fetchSuggestions={fetchSuggestions}
        taskContext={taskContext}
      />

      {/* [AGRI-GUARDIAN] Autosave Indicator */}
      <AutosaveIndicator lastSaved={form.date ? new Date() : null} />
    </div>
  )
}
