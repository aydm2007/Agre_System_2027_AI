export const DEFAULT_SERVICE_SCOPE = 'general'

export const normalizeServiceScopeValue = (value, fallback = DEFAULT_SERVICE_SCOPE) => {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed) {
      return trimmed
    }
  }
  return fallback
}

export const normalizeServiceCountEntry = (entry) => {
  if (!entry || typeof entry !== 'object') {
    return null
  }
  const normalized = { ...entry }
  const scope = normalizeServiceScopeValue(
    entry.service_scope,
    normalizeServiceScopeValue(entry.service_type, DEFAULT_SERVICE_SCOPE),
  )
  normalized.service_scope = scope
  if (
    !normalized.service_type ||
    typeof normalized.service_type !== 'string' ||
    !normalized.service_type.trim()
  ) {
    normalized.service_type = scope
  }
  return normalized
}

export const normalizeServiceCountsList = (entries) => {
  if (!Array.isArray(entries)) {
    return Array.isArray(entries) ? entries : []
  }
  return entries.map((item) => normalizeServiceCountEntry(item) || item)
}

export const normalizeDailyLogQueueEntry = (entry) => {
  if (!entry || entry.type !== 'daily-log') {
    return entry
  }

  const normalized = { ...entry }

  if (Array.isArray(entry.service_counts_payload)) {
    normalized.service_counts_payload = normalizeServiceCountsList(entry.service_counts_payload)
  }

  if (entry.activityPayload) {
    normalized.activityPayload = {
      ...entry.activityPayload,
    }
    if (Array.isArray(entry.activityPayload.service_counts_payload)) {
      normalized.activityPayload.service_counts_payload = normalizeServiceCountsList(
        entry.activityPayload.service_counts_payload,
      )
    }
    if (Array.isArray(entry.activityPayload.service_counts)) {
      normalized.activityPayload.service_counts = normalizeServiceCountsList(
        entry.activityPayload.service_counts,
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
