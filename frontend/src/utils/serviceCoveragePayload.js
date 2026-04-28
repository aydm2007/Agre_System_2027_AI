export const DEFAULT_SERVICE_SCOPE = 'general'
export const DEFAULT_DISTRIBUTION_MODE = 'uniform'

const DISTRIBUTION_MODE_ALIASES = {
  equal: 'uniform',
  equally: 'uniform',
  uniform: 'uniform',
  weighted: 'exception_weighted',
  exception_weighted: 'exception_weighted',
}

export const normalizeServiceScopeValue = (value, fallback = DEFAULT_SERVICE_SCOPE) => {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed) {
      return trimmed
    }
  }
  return fallback
}

export const normalizeDistributionMode = (value, fallback = DEFAULT_DISTRIBUTION_MODE) => {
  if (typeof value === 'string') {
    const normalized = DISTRIBUTION_MODE_ALIASES[value.trim().toLowerCase()]
    if (normalized) {
      return normalized
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
  normalized.distribution_mode = normalizeDistributionMode(entry.distribution_mode)
  return normalized
}

export const normalizeServiceCountsList = (entries) => {
  if (!Array.isArray(entries)) {
    return []
  }
  return entries.map((item) => normalizeServiceCountEntry(item) || item)
}
