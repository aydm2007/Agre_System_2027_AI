import {
  DEFAULT_DISTRIBUTION_MODE,
  DEFAULT_SERVICE_SCOPE,
  normalizeDistributionMode,
  normalizeServiceCountEntry,
  normalizeServiceCountsList,
  normalizeServiceScopeValue,
} from '../utils/serviceCoveragePayload'

export {
  DEFAULT_DISTRIBUTION_MODE,
  DEFAULT_SERVICE_SCOPE,
  normalizeDistributionMode,
  normalizeServiceCountEntry,
  normalizeServiceCountsList,
  normalizeServiceScopeValue,
}

export const normalizeDailyLogQueueEntry = (entry) => {
  const isDailyLogEntry =
    entry?.type === 'daily-log' ||
    entry?.category === 'daily_log' ||
    entry?.category === 'daily-log' ||
    (entry?.data && !entry?.method)
  if (!entry || !isDailyLogEntry) {
    return entry
  }

  const normalized = { ...entry }
  const data = entry.data && typeof entry.data === 'object' ? entry.data : {}

  if (!normalized.farm_id) {
    normalized.farm_id =
      entry.logPayload?.farm_id ||
      entry.logPayload?.farm ||
      data.farm_id ||
      data.farm ||
      entry.meta?.farmId ||
      null
  }

  if (!normalized.logPayload && Object.keys(data).length > 0) {
    normalized.logPayload = {
      farm: normalized.farm_id,
      log_date: data.log_date || data.date || entry.meta?.date || null,
      notes: data.notes || '',
      ...(data.variance_note ? { variance_note: data.variance_note } : {}),
    }
  }

  if (!normalized.activityPayload && Object.keys(data).length > 0) {
    normalized.activityPayload = { ...data }
  }

  if (Array.isArray(entry.service_counts_payload)) {
    normalized.service_counts_payload = normalizeServiceCountsList(entry.service_counts_payload)
  }

  if (normalized.activityPayload) {
    normalized.activityPayload = {
      ...normalized.activityPayload,
    }
    if (Array.isArray(normalized.activityPayload.service_counts_payload)) {
      normalized.activityPayload.service_counts_payload = normalizeServiceCountsList(
        normalized.activityPayload.service_counts_payload,
      )
    }
    if (Array.isArray(normalized.activityPayload.service_counts)) {
      normalized.activityPayload.service_counts = normalizeServiceCountsList(
        normalized.activityPayload.service_counts,
      )
    }
  }

  if (entry.meta) {
    normalized.meta = { ...entry.meta }
    if (Array.isArray(entry.meta.serviceCounts)) {
      normalized.meta.serviceCounts = normalizeServiceCountsList(entry.meta.serviceCounts)
    }
  }

  return normalized
}

export const normalizeQueueItem = (entry) => normalizeDailyLogQueueEntry(entry)
