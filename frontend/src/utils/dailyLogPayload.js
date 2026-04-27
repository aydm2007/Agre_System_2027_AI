const BACKEND_OWNED_COST_FIELDS = [
  'cost_materials',
  'cost_labor',
  'cost_machinery',
  'cost_overhead',
  'cost_wastage',
  'cost_total',
]

const READ_ONLY_ACTIVITY_FIELDS = [
  'smart_card_stack',
  'log_details',
  'farm_details',
  'crop_details',
  'task_details',
  'created_by',
  'updated_by',
  'created_at',
  'updated_at',
  'deleted_at',
  'budget_remaining',
  'budget_consumption_pct',
  'plan_overrun_warning',
  'available_wells',
  'available_products',
  'available_varieties_by_location',
  'material_governance_blocked',
  'governance_flags',
  'item_governance_flags',
]

const OBJECT_ID_FIELDS = [
  'farm',
  'crop',
  'task',
  'asset',
  'well_asset',
  'variety',
  'product',
  'tree_loss_reason',
  'crop_plan',
]

const ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩'
const EASTERN_ARABIC_DIGITS = '۰۱۲۳۴۵۶۷۸۹'

const normalizeDigits = (value) =>
  String(value)
    .replace(/[٠-٩]/g, (digit) => String(ARABIC_DIGITS.indexOf(digit)))
    .replace(/[۰-۹]/g, (digit) => String(EASTERN_ARABIC_DIGITS.indexOf(digit)))

const normalizeDecimalString = (value, decimalPlaces) => {
  if (value === null || value === undefined || value === '') return value
  const normalized = normalizeDigits(value).trim()
  if (!normalized) return value
  if (!/^-?\d+(\.\d+)?$/.test(normalized)) return value

  const sign = normalized.startsWith('-') ? '-' : ''
  const unsigned = sign ? normalized.slice(1) : normalized
  const [rawWhole, rawFraction = ''] = unsigned.split('.')
  const whole = rawWhole.replace(/^0+(?=\d)/, '') || '0'
  if (decimalPlaces <= 0) return `${sign}${whole}`

  const fraction = rawFraction.slice(0, decimalPlaces)
  return fraction ? `${sign}${whole}.${fraction}` : `${sign}${whole}`
}

const DECIMAL_FIELD_SCALE = {
  surrah_count: 2,
  days_spent: 2,
  machine_hours: 2,
  hours_worked: 2,
  hourly_rate: 4,
  fixed_wage_cost: 4,
  achievement_qty: 4,
  fuel_consumed: 4,
  well_reading: 3,
  machine_meter_reading: 3,
  start_meter: 3,
  end_meter: 3,
  material_qty: 3,
  planted_area: 3,
  planted_area_m2: 3,
  activity_tree_count: 0,
  tree_count_delta: 0,
  harvested_qty: 3,
  harvest_quantity: 3,
  water_volume: 3,
  fertilizer_quantity: 3,
  diesel_qty: 3,
}

const UOM_ARABIC_TO_EN = {
  'كجم': 'kg',
  'كيلوجرام': 'kg',
  'جرام': 'g',
  'غرام': 'g',
  'لتر': 'L',
  'مل': 'ml',
  'مليلتر': 'ml',
  'حبة': 'pcs',
  'قطعة': 'pcs',
  'كيس': 'pack',
  'عبوة': 'pack',
  'طن': 'ton',
  'متر': 'm',
  'متر مربع': 'm2',
  'متر مكعب': 'm3',
  'kg': 'kg',
  'KG': 'kg',
  'Kg': 'kg',
  'l': 'L',
  'L': 'L',
  'ltr': 'L',
  'g': 'g',
  'G': 'g',
  'm3': 'm3',
  'M3': 'm3',
  'pack': 'pack',
  'pcs': 'pcs',
  'ton': 'ton',
}

const normalizeUOM = (uom) => {
  if (!uom) return uom;
  const raw = String(uom).trim();
  const match = UOM_ARABIC_TO_EN[raw] || UOM_ARABIC_TO_EN[raw.toLowerCase()];
  return match || raw;
}

const normalizeNestedOperationalDecimals = (payload) => {
  if (Array.isArray(payload.items)) {
    payload.items = payload.items.map((itemObj) => {
      const { item_id, item, uom, out_uom, ...rest } = itemObj;
      return {
        ...rest,
        // [ZENITH 11.5 FIX] Backend explicitly expects 'item' instead of 'item_id'
        item: item ?? item_id,
        uom: normalizeUOM(uom),
        qty: normalizeDecimalString(itemObj.qty, 3),
        applied_qty: normalizeDecimalString(itemObj.applied_qty, 3),
        waste_qty: normalizeDecimalString(itemObj.waste_qty, 3),
      }
    })
  }
  if (Array.isArray(payload.items_payload)) {
    payload.items_payload = payload.items_payload.map((itemObj) => {
      const { item_id, item, uom, out_uom, ...rest } = itemObj;
      return {
        ...rest,
        item: item ?? item_id,
        uom: normalizeUOM(uom),
        qty: normalizeDecimalString(itemObj.qty, 3),
        applied_qty: normalizeDecimalString(itemObj.applied_qty, 3),
        waste_qty: normalizeDecimalString(itemObj.waste_qty, 3),
      }
    })
  }
  if (Array.isArray(payload.employees_payload)) {
    payload.employees_payload = payload.employees_payload.map((row) => ({
      ...row,
      workers_count: normalizeDecimalString(row.workers_count, 2),
      surrah_share: normalizeDecimalString(row.surrah_share, 2),
      hours_worked: normalizeDecimalString(row.hours_worked, 2),
      hourly_rate: normalizeDecimalString(row.hourly_rate, 4),
      fixed_wage_cost: normalizeDecimalString(row.fixed_wage_cost, 4),
      achievement_qty: normalizeDecimalString(row.achievement_qty, 4),
    }))
  }
  if (Array.isArray(payload.service_counts_payload)) {
    payload.service_counts_payload = payload.service_counts_payload.map((row) => ({
      ...row,
      service_count: normalizeDecimalString(row.service_count, 0),
      distribution_factor: normalizeDecimalString(row.distribution_factor, 4),
    }))
  }
  if (Array.isArray(payload.service_counts)) {
    payload.service_counts = payload.service_counts.map((row) => ({
      ...row,
      service_count: normalizeDecimalString(row.service_count, 0),
      distribution_factor: normalizeDecimalString(row.distribution_factor, 4),
    }))
  }
}

export const sanitizeDailyLogActivityPayload = (payload = {}) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return payload

  const cleaned = { ...payload }
  BACKEND_OWNED_COST_FIELDS.forEach((field) => delete cleaned[field])
  READ_ONLY_ACTIVITY_FIELDS.forEach((field) => delete cleaned[field])

  OBJECT_ID_FIELDS.forEach((field) => {
    const value = cleaned[field]
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const id = value.id ?? value.pk ?? null
      if (id !== null && id !== undefined && !cleaned[`${field}_id`]) {
        cleaned[`${field}_id`] = id
      }
      delete cleaned[field]
    }
  })

  Object.entries(DECIMAL_FIELD_SCALE).forEach(([field, scale]) => {
    if (Object.prototype.hasOwnProperty.call(cleaned, field)) {
      cleaned[field] = normalizeDecimalString(cleaned[field], scale)
    }
  })

  // [ZENITH 11.5 — BACKEND OWNED] cost_* حقول مالية تُحسب على الـ backend حصراً.
  // تم حذفها في الأعلى عبر BACKEND_OWNED_COST_FIELDS — لا إجراء إضافي.

  normalizeNestedOperationalDecimals(cleaned)

  return cleaned
}

export const sanitizeDailyLogEnvelope = (entry = {}) => {
  if (!entry || typeof entry !== 'object') return entry
  return {
    ...entry,
    activityPayload: sanitizeDailyLogActivityPayload(entry.activityPayload || {}),
  }
}
