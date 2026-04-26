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

export function useDailyLogForm(initialOverrides = {}, options = {}) {
  const [form, setForm] = useState({
    ...INITIAL_STATE,
    ...initialOverrides,
    draft_uuid: initialOverrides.draft_uuid || uuidv4(),
  })
  const [errors, setErrors] = useState({})
  const [isSubmitting] = useState(false)
  const [step, setStep] = useState(1)
  const [validationPolicy, setValidationPolicy] = useState(buildValidationPolicy(options))
  const [drafts, setDrafts] = useState([])

  const { saveDraft, loadDraft, loadDrafts, clearDraft, queueLogSubmission, isOnline } =
    useDailyLogOffline()

  useEffect(() => {
    const restoreDraftUuid = options.restoreDraftUuid || null
    loadDraft({
      draftUuid: restoreDraftUuid,
      farmId: initialOverrides.farm || null,
      logDate: initialOverrides.date || null,
    }).then((draft) => {
      if (draft?.data) {
        const draftData = { ...draft.data, draft_uuid: draft.draft_uuid }
        // [FIX]: تصحيح التاريخ الفاسد من المسودة المخزنة — مثال: 60404-02-20
        if (draftData.date) {
          const dateStr = String(draftData.date).split('T')[0]
          const [y, m, d] = dateStr.split('-').map(Number)
          if (!y || !m || !d || y < 2020 || y > 2099 || m < 1 || m > 12 || d < 1 || d > 31) {
            console.warn('[Draft] تاريخ فاسد في المسودة المخزنة:', draftData.date, '→ تم استبداله بتاريخ اليوم')
            draftData.date = new Date().toISOString().slice(0, 10)
          }
        }
        setForm((prev) => ({ ...prev, ...draftData }))
      } else {
        setForm((prev) => ({
          ...prev,
          draft_uuid: prev.draft_uuid || uuidv4(),
        }))
      }
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
        // [FIX]: التحقق من صحة صيغة التاريخ لمنع إرسال تواريخ فاسدة مثل 60404-02-20
        const [y, m, d] = String(form.date).split('T')[0].split('-').map(Number)
        if (!y || !m || !d || y < 2020 || y > 2099) {
          newErrors.date = 'تاريخ غير صالح — يرجى إعادة اختيار التاريخ'
        }
      }
      if (!form.farm) newErrors.farm = 'اختر المزرعة'
      if (!form.locations || form.locations.length === 0) newErrors.locations = 'اختر الموقع'
      if (!form.task) newErrors.task = 'اختر المهمة'
    }

    if (currentStep === 2) {
      if (!requireLaborStep) {
        // Labor is disabled by task contract.
      } else if (!laborPolicy.registeredAllowed && !laborPolicy.casualBatchAllowed) {
        // Defensive fallback when task policy blocks both entry modes.
      } else if (form.labor_entry_mode === 'CASUAL_BATCH') {
        if (!laborPolicy.casualBatchAllowed) {
          newErrors.labor_entry_mode = 'هذه المهمة لا تسمح بإدخال عمالة يومية.'
        }
        const workers = Number(form.casual_workers_count)
        if (!workers || Number.isNaN(workers) || workers <= 0) {
          newErrors.casual_workers_count = 'حدد عدد العمالة اليومية'
        }
      } else {
        if (!laborPolicy.registeredAllowed) {
          newErrors.labor_entry_mode = 'هذه المهمة لا تسمح بإدخال عمالة مسجلة.'
        }
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
      setForm((prev) => ({
        ...prev,
        ...draft.data,
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

    const requireLaborStep = validationPolicy.requireLaborStep
    const laborPolicy = validationPolicy.laborPolicy

    if (!cleaned.variance_note) cleaned.variance_note = ''

    cleaned.locations = Array.isArray(cleaned.locations)
      ? cleaned.locations.map((loc) => Number(loc)).filter((id) => !isNaN(id))
      : []
    delete cleaned.location

    const nullableFKs = ['well_id', 'asset', 'service_provider_id', 'crop', 'farm']
    nullableFKs.forEach((key) => {
      if (cleaned[key] === '') cleaned[key] = null
    })

    const normalizeNum = (val) => {
      if (val === null || val === undefined || val === '') return null
      if (typeof val === 'number') return isNaN(val) ? null : val
      const englishStr = String(val).replace(/[٠-٩]/g, (d) => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
      const parsed = Number(englishStr)
      return isNaN(parsed) ? null : parsed
    }

    const numericFields = [
      'surrah_count',
      'machine_hours',
      'fuel_consumed',
      'well_reading',
      'machine_meter_reading',
      'harvested_qty',
      'harvest_quantity',
      'water_volume',
      'fertilizer_quantity',
      'planted_area',
      'activity_tree_count',
      'tree_count_delta',
      'diesel_qty',
      'fixed_wage_cost',
    ]

    numericFields.forEach((key) => {
      cleaned[key] = normalizeNum(cleaned[key])
    })

    // V445: Solar power scrubbing (Force boolean to avoid NULL constraint violation)
    cleaned.is_solar_powered = Boolean(cleaned.is_solar_powered)
    if (cleaned.is_solar_powered) {
      cleaned.diesel_qty = null
    }

    // [AGRI-GUARDIAN] Per-Row Aggregation for Delta & Harvest
    if (cleaned.serviceRows && cleaned.serviceRows.length > 0) {
      let aggregatedDelta = 0
      let aggregatedHarvest = 0
      let lossReasonId = null

      cleaned.serviceRows.forEach((row) => {
        const rowDelta = normalizeNum(row.delta) || 0
        const rowHarvest = normalizeNum(row.harvestQty) || 0
        aggregatedDelta += rowDelta
        aggregatedHarvest += rowHarvest
        if (rowDelta < 0 && row.lossReasonId && !lossReasonId) {
          lossReasonId = row.lossReasonId
        }
      })

      if (aggregatedDelta !== 0) cleaned.tree_count_delta = aggregatedDelta
      if (aggregatedHarvest !== 0) cleaned.harvest_quantity = aggregatedHarvest
      if (lossReasonId) cleaned.tree_loss_reason_id = lossReasonId
    }

    if (!cleaned.team) cleaned.team = []

    if (!requireLaborStep || (!laborPolicy.registeredAllowed && !laborPolicy.casualBatchAllowed)) {
      cleaned.team = []
      cleaned.employees = []
      cleaned.employees_payload = []
      cleaned.casual_workers_count = ''
    } else if (cleaned.labor_entry_mode === 'CASUAL_BATCH') {
      if (!laborPolicy.casualBatchAllowed) {
        cleaned.labor_entry_mode = laborPolicy.registeredAllowed ? 'REGISTERED' : 'CASUAL_BATCH'
        cleaned.casual_workers_count = ''
      }
    } else if (!laborPolicy.registeredAllowed && laborPolicy.casualBatchAllowed) {
      cleaned.labor_entry_mode = 'CASUAL_BATCH'
      cleaned.team = []
    }

    const normalizeLaborRow = (row) => ({
      ...row,
      is_hourly: !!cleaned.is_hourly,
      hours_worked: normalizeNum(cleaned.hours_worked || 0),
      hourly_rate: normalizeNum(cleaned.hourly_rate || 0),
      fixed_wage_cost: normalizeNum(cleaned.fixed_wage_cost || 0),
      achievement_qty: normalizeNum(cleaned.achievement_qty || 0),
      achievement_uom: cleaned.achievement_uom || '',
    })

    if (cleaned.labor_entry_mode === 'CASUAL_BATCH') {
      cleaned.team = []
      cleaned.employees = []
      cleaned.employees_payload = [
        normalizeLaborRow({
          labor_type: 'CASUAL_BATCH',
          workers_count: Number(cleaned.casual_workers_count || 0),
          surrah_share: Number(cleaned.surrah_count || 0),
          labor_batch_label: cleaned.casual_batch_label || 'دفعة عمالة يومية',
        }),
      ]
    } else if (Array.isArray(cleaned.team) && cleaned.team.length > 0) {
      cleaned.employees = cleaned.team
      cleaned.employees_payload = cleaned.team.map((employeeId) =>
        normalizeLaborRow({
          labor_type: 'REGISTERED',
          employee_id: Number(employeeId),
          surrah_share: Number(cleaned.surrah_count || 0),
        }),
      )
    } else {
      cleaned.employees = []
      cleaned.employees_payload = []
    }


    // [FIX] Normalize items array for submission
      if (Array.isArray(cleaned.items) && cleaned.items.length > 0) {
        cleaned.items_payload = cleaned.items
        .filter((it) => (it.item_id || it.item) && it.qty)
        .map((it) => ({
          item_id: Number(it.item_id || it.item),
          qty: Number(it.qty),
          applied_qty:
            it.applied_qty === '' || it.applied_qty === undefined || it.applied_qty === null
              ? Number(it.qty)
              : Number(it.applied_qty),
          waste_qty:
            it.waste_qty === '' || it.waste_qty === undefined || it.waste_qty === null
              ? 0
              : Number(it.waste_qty),
          waste_reason: it.waste_reason || '',
          uom: it.uom || '',
          batch_number: it.batch_number || undefined,
        }))
      } else {
        cleaned.items_payload = []
      }

      if (Array.isArray(cleaned.serviceRows) && cleaned.serviceRows.length > 0) {
        cleaned.service_counts_payload = cleaned.serviceRows.map((row) => ({
          variety_id: Number(row.varietyId || row.variety_id),
          location_id: row.locationId || row.location_id ? Number(row.locationId || row.location_id) : null,
          service_count: Number(row.serviceCount || row.service_count || 0),
          service_type: row.serviceType || row.service_type || 'general',
          service_scope: row.serviceScope || row.service_scope || 'location',
          distribution_mode: row.distributionMode || row.distribution_mode || 'uniform',
          distribution_factor:
            row.distributionFactor === '' || row.distributionFactor === undefined || row.distributionFactor === null
              ? null
              : Number(row.distributionFactor),
          notes: row.notes || '',
        }))
      }

    if (draft_uuid) {
      cleaned.draft_uuid = draft_uuid
    }


    return sanitizeDailyLogActivityPayload(cleaned)
  }


  const submitLog = async (payloadOverride = null, queueOptions = {}) => {
    const payload = payloadOverride || scrubPayload(form)
    const result = await queueLogSubmission(payload, queueOptions)
    await refreshDrafts()
    return result
  }

  return {
    form,
    errors,
    step,
    setStep,
    isSubmitting,
    isOnline,
    updateField,
    setForm,
    nextStep,
    prevStep,
    resetForm,
    startNewDraft,
    resumeDraft,
    drafts,
    refreshDrafts,
    queueLogSubmission: submitLog,
    scrubPayload,
    setValidationPolicy,
  }
}
