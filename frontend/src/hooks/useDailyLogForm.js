import { useState, useEffect, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { useDailyLogOffline } from './useDailyLogOffline'
import { sanitizeDailyLogActivityPayload } from '../utils/dailyLogPayload'

const INITIAL_STATE = {
  draft_uuid: '',
  date: new Date().toISOString().slice(0, 10),
  farm: '',
  locations: [],
  well_id: '',
  asset: '',
  asset_id: '',
  crop: '',
  task: '',
  variety: '',
  team: [],
  labor_entry_mode: 'REGISTERED',
  casual_workers_count: '',
  casual_batch_label: 'عمالة يومية غير مسجلة',
  surrah_count: '1.0',
  is_hourly: false,
  hours_worked: '',
  hourly_rate: '',
  fixed_wage_cost: '',
  achievement_qty: '',
  achievement_uom: '',
  notes: '',

  items: [],
  machine_hours: '',
  machine_meter_reading: '',
  fuel_consumed: '',
  water_volume: '',
  is_solar_powered: false,
  diesel_qty: '',
  product_id: '',
  harvested_item: '',
  harvested_qty: '',
  harvest_quantity: '',
  batch_number: '',
  harvest_uom: '',
  planted_area: '',
  activity_tree_count: '',
  tree_count_delta: 0,
  tree_loss_reason: '',
  serviceRows: [],
  service_provider_id: '',
  variance_note: '',
}

const buildValidationPolicy = (options = {}) => ({
  requireLaborStep: options.requireLaborStep ?? true,
  laborPolicy: options.laborPolicy ?? {
    registeredAllowed: true,
    casualBatchAllowed: true,
    surrahRequired: options.requireLaborStep ?? true,
  },
})

const applyFieldResets = (target, resets) => {
  Object.entries(resets).forEach(([key, value]) => {
    target[key] = value
  })
}

const CONTEXTUAL_DETAIL_RESETS = {
  well_id: '',
  well_reading: '',
  water_volume: '',
  is_solar_powered: false,
  diesel_qty: '',
  asset: '',
  asset_id: '',
  machine_hours: '',
  machine_meter_reading: '',
  fuel_consumed: '',
  items: [],
  product_id: '',
  harvested_item: '',
  harvested_qty: '',
  harvest_quantity: '',
  batch_number: '',
  harvest_uom: '',
  planted_area: '',
  activity_tree_count: '',
  tree_count_delta: 0,
  tree_loss_reason: '',
  tree_loss_reason_id: '',
  serviceRows: [],
  service_provider_id: '',
  variety: '',
}

const FARM_CHANGE_RESETS = {
  locations: [],
  crop: '',
  task: '',
  ...CONTEXTUAL_DETAIL_RESETS,
}

const CROP_CHANGE_RESETS = {
  task: '',
  variety: '',
  product_id: '',
  harvested_item: '',
  harvested_qty: '',
  harvest_quantity: '',
  batch_number: '',
  harvest_uom: '',
  planted_area: '',
  activity_tree_count: '',
  tree_count_delta: 0,
  tree_loss_reason: '',
  tree_loss_reason_id: '',
  serviceRows: [],
}

const LOCATION_CHANGE_RESETS = {
  well_id: '',
  well_reading: '',
  water_volume: '',
  is_solar_powered: false,
  diesel_qty: '',
  serviceRows: [],
}

const TASK_CHANGE_RESETS = {
  ...CONTEXTUAL_DETAIL_RESETS,
}

const stringifyId = (value) => {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'object') {
    return stringifyId(value.id ?? value.value ?? '')
  }
  return String(value)
}

const hydratePayloadToForm = (rawData) => {
  if (!rawData) return rawData;
  const hydrated = { ...rawData };

  hydrated.asset_id = stringifyId(hydrated.asset_id || hydrated.asset)
  hydrated.asset = hydrated.asset_id
  hydrated.well_id = stringifyId(hydrated.well_id || hydrated.well_asset_id || hydrated.well)
  hydrated.product_id = stringifyId(hydrated.product_id || hydrated.product)
  hydrated.variety = stringifyId(hydrated.variety || hydrated.variety_id)
  if (Array.isArray(hydrated.locations)) {
    hydrated.locations = hydrated.locations.map((location) => stringifyId(location)).filter(Boolean)
  }

  if (Array.isArray(hydrated.employees_payload) && hydrated.employees_payload.length > 0) {
    const firstEmp = hydrated.employees_payload[0];
    if (firstEmp.labor_type === 'CASUAL_BATCH') {
      hydrated.labor_entry_mode = 'CASUAL_BATCH';
      hydrated.casual_workers_count = String(firstEmp.workers_count || '');
      hydrated.casual_batch_label = firstEmp.labor_batch_label || 'عمالة يومية غير مسجلة';
      hydrated.surrah_count = String(firstEmp.surrah_share || '1.0');
    } else {
      hydrated.labor_entry_mode = 'REGISTERED';
      hydrated.team = hydrated.employees_payload.map(emp => String(emp.employee_id));
      hydrated.surrah_count = String(firstEmp.surrah_share || '1.0');
    }
  }

  if (Array.isArray(hydrated.items_payload) && hydrated.items_payload.length > 0) {
    hydrated.items = hydrated.items_payload.map((it) => ({
      item_id: stringifyId(it.item_id || it.item),
      qty: String(it.qty || ''),
      uom: it.uom || ''
    }));
  } else if (Array.isArray(hydrated.items)) {
    hydrated.items = hydrated.items.map((it) => ({
      item_id: stringifyId(it.item_id || it.item),
      qty: String(it.qty || ''),
      uom: it.uom || ''
    }));
  }

  if (Array.isArray(hydrated.service_counts_payload) && hydrated.service_counts_payload.length > 0) {
    const defaultLocation = Array.isArray(hydrated.locations) && hydrated.locations.length > 0 ? stringifyId(hydrated.locations[0]) : '';
    hydrated.serviceRows = hydrated.service_counts_payload.map((row) => ({
      key: uuidv4(),
      varietyId: stringifyId(row.variety_id || row.varietyId || row.variety),
      locationId: stringifyId(row.location_id || row.locationId || defaultLocation),
      serviceCount: String(row.service_count || ''),
      notes: row.notes || ''
    }));
  } else if (Array.isArray(hydrated.serviceRows)) {
    hydrated.serviceRows = hydrated.serviceRows.map((row) => ({
      key: row.key || uuidv4(),
      varietyId: stringifyId(row.varietyId || row.variety_id || row.variety),
      locationId: stringifyId(row.locationId || row.location_id || row.location),
      serviceCount: String(row.serviceCount || row.service_count || ''),
      notes: row.notes || '',
    }));
  }

  return hydrated;
};

export function useDailyLogForm(initialOverrides = {}, options = {}) {
  const [form, setForm] = useState({
    ...INITIAL_STATE,
    ...initialOverrides,
    draft_uuid: initialOverrides.draft_uuid || uuidv4(),
  })
  const [errors, setErrors] = useState({})
  const [isSubmitting] = useState(false)
  const [step, setStep] = useState(1)
  const [, setIsRestoring] = useState(false) // [ZENITH 11.5 FIX]
  const [validationPolicy, setValidationPolicy] = useState(buildValidationPolicy(options))
  const [drafts, setDrafts] = useState([])

  const { saveDraft, loadDraft, loadDrafts, clearDraft, queueLogSubmission, isOnline } =
    useDailyLogOffline()

  useEffect(() => {
    const restoreDraftUuid = options.restoreDraftUuid || null
    setIsRestoring(true)
    loadDraft({
      draftUuid: restoreDraftUuid,
      farmId: initialOverrides.farm || null,
      logDate: initialOverrides.date || null,
    }).then((draft) => {
      if (draft?.data) {
        const draftData = { ...draft.data, draft_uuid: draft.draft_uuid }
        // [FIX]: تصحيح التاريخ الفاسد من المسودة المخزنة
        if (draftData.date) {
          const dateStr = String(draftData.date).split('T')[0]
          const [y, m, d] = dateStr.split('-').map(Number)
          if (!y || !m || !d || y < 2020 || y > 2099 || m < 1 || m > 12 || d < 1 || d > 31) {
            draftData.date = new Date().toISOString().slice(0, 10)
          }
        }
        
        const hydratedData = hydratePayloadToForm(draftData);
        setForm((prev) => ({ ...prev, ...hydratedData }))
      } else {
        setForm((prev) => ({
          ...prev,
          draft_uuid: prev.draft_uuid || uuidv4(),
        }))
      }
      setIsRestoring(false)
    })
  }, [initialOverrides.date, initialOverrides.farm, loadDraft, options.restoreDraftUuid])

  const refreshDrafts = useCallback(
    async (filters = {}) => {
      const data = await loadDrafts({
        farmId: filters.farmId ?? form.farm ?? null,
        logDate: filters.logDate ?? form.date ?? null,
      })
      setDrafts(data)
      return data
    },
    [form.date, form.farm, loadDrafts],
  )

  useEffect(() => {
    refreshDrafts().catch(() => {})
  }, [form.farm, form.date, refreshDrafts])

  useEffect(() => {
    const timeout = setTimeout(() => {
      saveDraft(form, {
        draftUuid: form.draft_uuid,
        farmId: form.farm || null,
        logDate: form.date || null,
        status: 'draft',
      }).then(() => {
        refreshDrafts().catch(() => {})
      })
    }, 1000)
    return () => clearTimeout(timeout)
  }, [form, refreshDrafts, saveDraft])

  const updateField = useCallback(
    (field, value) => {
      setForm((prev) => {
        const updated = { ...prev, [field]: value }

        if (field === 'farm') {
          applyFieldResets(updated, FARM_CHANGE_RESETS)
        }
        if (field === 'crop') {
          applyFieldResets(updated, CROP_CHANGE_RESETS)
        }
        if (field === 'locations') {
          applyFieldResets(updated, LOCATION_CHANGE_RESETS)
        }
        if (field === 'task') {
          applyFieldResets(updated, TASK_CHANGE_RESETS)
        }

        return updated
      })

      if (errors[field]) {
        setErrors((prev) => {
          const nextErrors = { ...prev }
          delete nextErrors[field]
          return nextErrors
        })
      }
    },
    [errors],
  )

  const validateStep = (currentStep) => {
    const newErrors = {}
    let isValid = true
    const requireLaborStep = validationPolicy.requireLaborStep
    const laborPolicy = validationPolicy.laborPolicy

    if (currentStep === 1) {
      if (!form.date) {
        newErrors.date = 'ادخل التاريخ'
      } else {
        const [y, m, d] = String(form.date).split('T')[0].split('-').map(Number)
        if (!y || !m || !d || y < 2020 || y > 2099) {
          newErrors.date = 'تاريخ غير صالح'
        }
      }
      if (!form.farm) newErrors.farm = 'اختر المزرعة'
      if (!form.locations || form.locations.length === 0) newErrors.locations = 'اختر الموقع'
      if (!form.task) newErrors.task = 'اختر المهمة'
    }

    if (
      currentStep === 2 &&
      requireLaborStep &&
      (laborPolicy.registeredAllowed || laborPolicy.casualBatchAllowed)
    ) {
      if (form.labor_entry_mode === 'REGISTERED' && !laborPolicy.registeredAllowed) {
        newErrors.labor_entry_mode = 'هذه المهمة لا تسمح بإدخال عمالة مسجلة.'
      }
      if (form.labor_entry_mode === 'CASUAL_BATCH' && !laborPolicy.casualBatchAllowed) {
        newErrors.labor_entry_mode = 'هذه المهمة لا تسمح بإدخال عمالة يومية.'
      }
      if (form.labor_entry_mode === 'CASUAL_BATCH') {
        const workers = Number(form.casual_workers_count)
        if (!workers || workers <= 0) {
          newErrors.casual_workers_count = 'حدد عدد العمالة اليومية'
        }
      } else {
        if (!form.team || form.team.length === 0) {
          newErrors.team = 'حدد فريق العمل'
        }
      }

      if (requireLaborStep && laborPolicy.surrahRequired && !form.surrah_count) {
        newErrors.surrah_count = 'حدد عدد الفترات'
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      isValid = false
    }
    return isValid
  }

  const nextStep = () => {
    if (validateStep(step)) {
      setStep((prev) => prev + 1)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const prevStep = () => {
    setStep((prev) => Math.max(1, prev - 1))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const startNewDraft = useCallback(
    async ({ preserveContext = true, discardCurrent = false } = {}) => {
      const nextDraftUuid = uuidv4()
      const baseState = preserveContext
        ? {
            date: form.date || INITIAL_STATE.date,
            farm: form.farm || '',
            locations: Array.isArray(form.locations) ? form.locations : [],
            crop: form.crop || '',
          }
        : {}
      if (discardCurrent && form.draft_uuid) {
        await clearDraft(form.draft_uuid)
      }
      setForm({
        ...INITIAL_STATE,
        ...baseState,
        draft_uuid: nextDraftUuid,
      })
      setStep(1)
      setErrors({})
      await refreshDrafts({
        farmId: preserveContext ? form.farm : null,
        logDate: preserveContext ? form.date : null,
      })
      return nextDraftUuid
    },
    [clearDraft, form.crop, form.date, form.draft_uuid, form.farm, form.locations, refreshDrafts],
  )

  const resumeDraft = useCallback(
    async (draftUuid) => {
      const draft = await loadDraft({ draftUuid })
      if (!draft?.data) {
        return null
      }
      
      const hydratedData = hydratePayloadToForm(draft.data);
      setForm((prev) => ({
        ...prev,
        ...hydratedData,
        draft_uuid: draft.draft_uuid,
      }))
      setStep(1)
      setErrors({})
      return draft
    },
    [loadDraft],
  )

  const resetForm = useCallback(async () => {
    if (form.draft_uuid) {
      await clearDraft(form.draft_uuid)
    }
    await startNewDraft({ preserveContext: false })
    setStep(1)
    setErrors({})
  }, [clearDraft, form.draft_uuid, startNewDraft])

  const scrubPayload = (rawData) => {
    const cleaned = { ...rawData }
    const draft_uuid = rawData.draft_uuid || null
    const laborStepEnabled =
      validationPolicy.requireLaborStep &&
      (validationPolicy.laborPolicy.registeredAllowed || validationPolicy.laborPolicy.casualBatchAllowed)

    if (!cleaned.variance_note) cleaned.variance_note = ''

    cleaned.locations = Array.isArray(cleaned.locations)
      ? cleaned.locations.map((loc) => Number(loc)).filter((id) => !isNaN(id))
      : []

    const nullableFKs = ['well_id', 'asset', 'service_provider_id', 'crop', 'farm', 'variety']
    nullableFKs.forEach((key) => {
      if (cleaned[key] === '') cleaned[key] = null
    })

    const normalizeNum = (val) => {
      if (val === null || val === undefined || val === '') return null
      return Number(val)
    }

    const numericFields = [
      'surrah_count', 'machine_hours', 'fuel_consumed', 'well_reading', 
      'machine_meter_reading', 'harvested_qty', 'harvest_quantity', 
      'water_volume', 'planted_area', 'activity_tree_count', 
      'tree_count_delta', 'diesel_qty', 'fixed_wage_cost'
    ]

    numericFields.forEach((key) => {
      cleaned[key] = normalizeNum(cleaned[key])
    })

    cleaned.is_solar_powered = Boolean(cleaned.is_solar_powered)
    if (cleaned.is_solar_powered) {
      cleaned.diesel_qty = null
    }

    if (cleaned.serviceRows && cleaned.serviceRows.length > 0) {
      let aggregatedDelta = 0
      let aggregatedHarvest = 0
      cleaned.serviceRows.forEach((row) => {
        aggregatedDelta += Number(row.delta || 0)
        aggregatedHarvest += Number(row.harvestQty || 0)
      })
      if (aggregatedDelta !== 0) cleaned.tree_count_delta = aggregatedDelta
      if (aggregatedHarvest !== 0) cleaned.harvest_quantity = aggregatedHarvest
    }

    if (!laborStepEnabled) {
      cleaned.team = []
      cleaned.employees = []
      cleaned.employees_payload = []
      cleaned.casual_workers_count = ''
      cleaned.casual_batch_label = ''
    } else if (cleaned.labor_entry_mode === 'CASUAL_BATCH') {
      cleaned.employees_payload = [{
        labor_type: 'CASUAL_BATCH',
        workers_count: String(cleaned.casual_workers_count || 0),
        surrah_share: String(cleaned.surrah_count || 1.0),
        labor_batch_label: cleaned.casual_batch_label
      }]
    } else if (Array.isArray(cleaned.team) && cleaned.team.length > 0) {
      cleaned.employees = [...cleaned.team]
      cleaned.employees_payload = cleaned.team.map(id => ({
        labor_type: 'REGISTERED',
        employee_id: Number(id),
        surrah_share: String(cleaned.surrah_count || 1.0)
      }))
    }

    if (Array.isArray(cleaned.items) && cleaned.items.length > 0) {
      cleaned.items_payload = cleaned.items
        .filter(it => (it.item_id || it.item) && it.qty)
        .map(it => ({
          item_id: Number(it.item_id || it.item),
          qty: String(it.qty),
          applied_qty: it.applied_qty,
          waste_qty: it.waste_qty,
          waste_reason: it.waste_reason,
          uom: String(it.uom || '').toLowerCase(),
          batch_number: it.batch_number,
        }))
    }

    if (Array.isArray(cleaned.serviceRows) && cleaned.serviceRows.length > 0) {
      cleaned.service_counts_payload = cleaned.serviceRows.map(row => ({
        variety_id: Number(row.varietyId),
        location_id: row.locationId ? Number(row.locationId) : null,
        service_count: String(row.serviceCount || 0),
        service_type: row.serviceType || 'general',
        service_scope: row.serviceScope || 'location',
        distribution_mode: row.distributionMode || 'uniform',
        distribution_factor: row.distributionFactor || '',
        notes: row.notes || ''
      }))
    }

    if (draft_uuid) cleaned.draft_uuid = draft_uuid
    const sanitized = sanitizeDailyLogActivityPayload(cleaned)
    if (Array.isArray(cleaned.items_payload)) {
      sanitized.items_payload = cleaned.items_payload
    }
    return sanitized
  }

  const submitLog = async (payloadOverride = null, queueOptions = {}) => {
    const payload = payloadOverride || scrubPayload(form)
    const result = await queueLogSubmission(payload, queueOptions)
    await refreshDrafts()
    return result
  }

  return {
    form, errors, step, setStep, isSubmitting, isOnline, updateField,
    setForm, nextStep, prevStep, resetForm, startNewDraft, resumeDraft,
    drafts, refreshDrafts, queueLogSubmission: submitLog, scrubPayload,
    setValidationPolicy
  }
}
