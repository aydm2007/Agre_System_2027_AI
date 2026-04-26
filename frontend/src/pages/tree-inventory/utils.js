// Tree Inventory Constants & Utilities
// Extracted from TreeInventory.jsx for atomic component architecture
import { format as formatDateFns } from 'date-fns'

export const SERVICE_TYPE_LABELS = {
  general: 'عامة',
  irrigation: 'ري',
  fertilization: 'تسميد',
  pruning: 'تقليم',
  protection: 'حماية',
  cleaning: 'تنظيف',
  unknown: 'غير معروف',
}

// ─────────────────────────────────────────────────────────────────────────────
// Formatting Utilities
// ─────────────────────────────────────────────────────────────────────────────

export const formatNumber = (value, fraction = 0) => {
  const numeric = Number(value ?? 0)
  if (!Number.isFinite(numeric)) {
    return '0'
  }
  return numeric.toLocaleString('ar-EG', {
    minimumFractionDigits: fraction,
    maximumFractionDigits: fraction,
  })
}

export const formatDate = (value) => {
  if (!value) return '-'
  if (typeof value === 'string' && value.length >= 10) {
    return value.slice(0, 10)
  }
  try {
    return formatDateFns(new Date(value), 'yyyy-MM-dd')
  } catch (error) {
    return String(value)
  }
}

export const formatDateTime = (value) => {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('ar-EG')
  } catch (error) {
    return String(value)
  }
}

export const formatPercent = (value) => {
  if (value == null) return '-'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '-'
  }
  const formatted = (numeric * 100).toLocaleString('ar-EG', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
  const normalized = formatted.replace(/\u066B/g, '.').replace(/\u066C/g, ',')
  return `${normalized}%`
}

export const toAsciiDigits = (input) => {
  if (typeof input !== 'string') {
    return input
  }
  return input
    .replace(/[٠-٩]/g, (digit) => String(digit.charCodeAt(0) - 1632))
    .replace(/\u066B/g, '.')
    .replace(/\u066C/g, ',')
}

// ─────────────────────────────────────────────────────────────────────────────
// API Parameter Builders
// ─────────────────────────────────────────────────────────────────────────────

export const buildSummaryParams = (filters) => {
  const params = {}
  if (filters.farm) params.farm_id = filters.farm
  if (filters.location_id) params.location_id = filters.location_id
  if (filters.variety_id) params.variety_id = filters.variety_id
  if (filters.status_code) params.status_code = filters.status_code
  if (filters.start) params.planted_after = filters.start
  if (filters.end) params.planted_before = filters.end
  if (filters.service_start) params.service_start = filters.service_start
  if (filters.service_end) params.service_end = filters.service_end
  return params
}

export const buildEventsParams = (filters) => {
  const params = {}
  if (filters.farm) params.farm_id = filters.farm
  if (filters.location_id) params.location_id = filters.location_id
  if (filters.variety_id) params.variety_id = filters.variety_id
  if (filters.loss_reason) params.loss_reason = filters.loss_reason
  if (filters.start) params.from = filters.start
  if (filters.end) params.to = filters.end
  return params
}

// ─────────────────────────────────────────────────────────────────────────────
// File Download Utility
// ─────────────────────────────────────────────────────────────────────────────

export const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// ─────────────────────────────────────────────────────────────────────────────
// Default Filter State
// ─────────────────────────────────────────────────────────────────────────────

export const DEFAULT_FILTERS = {
  start: '',
  end: '',
  service_start: '',
  service_end: '',
  farm: '',
  location_id: '',
  variety_id: '',
  status_code: '',
  loss_reason: '',
}

export const DEFAULT_COLUMN_VISIBILITY = {
  notes: false,
  harvest: true,
  water: false,
  fertilizer: false,
  servicePeriod: true,
  serviceLifetime: true,
  serviceLatest: true,
}
