import { get, set, del } from 'idb-keyval'
import { nowIso, generateOfflineId } from './helpers'
import { normalizeQueueItem } from './offlineQueueUtils'

export const OFFLINE_REQUESTS_KEY = 'offline-queue'
export const OFFLINE_DAILY_LOGS_KEY = 'offline-daily-logs'
export const OFFLINE_FAILED_KEY = 'offline-failures'

const DEFAULT_QUEUE_OWNER = 'user:anonymous'
let globalQueueOwnerId = null

export const setQueueOwnerId = (id) => {
  globalQueueOwnerId = id
}

const resolveQueueOwnerKey = async () => {
  if (globalQueueOwnerId) {
    return `user:${globalQueueOwnerId}`
  }
  return DEFAULT_QUEUE_OWNER
}

export const getQueueOwnerKey = async () => resolveQueueOwnerKey()

const resolveScopedKey = async (baseKey) => {
  const owner = await resolveQueueOwnerKey()
  return `${baseKey}::${owner}`
}

export const readScopedValue = async (baseKey) => {
  const scoped = await resolveScopedKey(baseKey)
  const [scopedValue, legacyValue] = await Promise.all([get(scoped), get(baseKey)])
  if (scopedValue !== undefined && scopedValue !== null) {
    if (legacyValue !== undefined && legacyValue !== null) {
      await del(baseKey)
    }
    return scopedValue
  }
  if (legacyValue !== undefined && legacyValue !== null) {
    await set(scoped, legacyValue)
    await del(baseKey)
    return legacyValue
  }
  return null
}

export const writeScopedValue = async (baseKey, value) => {
  const scoped = await resolveScopedKey(baseKey)
  const shouldRemove =
    value === null ||
    value === undefined ||
    (Array.isArray(value) && value.length === 0) ||
    (typeof value === 'object' && !Array.isArray(value) && !Object.keys(value).length)
  if (shouldRemove) {
    await del(scoped)
    return
  }
  await set(scoped, value)
}

export const summarizeQueueItem = (item) => {
  const base = normalizeQueueItem(item || {})
  const queuedAt = base.queuedAt || nowIso()
  return {
    ...base,
    id: base.id || generateOfflineId(),
    queuedAt,
    attempts: base.attempts || 0,
    nextAttemptAt: base.nextAttemptAt || queuedAt,
  }
}

export const sortByQueuedAt = (a, b) => {
  const left = new Date(a.queuedAt || 0).getTime()
  const right = new Date(b.queuedAt || 0).getTime()
  return left - right
}

export const readScopedQueue = async (baseKey) => {
  const raw = await readScopedValue(baseKey)
  if (Array.isArray(raw)) {
    return raw.map(summarizeQueueItem)
  }
  return []
}

export const writeScopedQueue = async (baseKey, items) => {
  if (Array.isArray(items) && items.length) {
    const normalized = items.map(summarizeQueueItem).sort(sortByQueuedAt)
    await writeScopedValue(baseKey, normalized)
  } else {
    await writeScopedValue(baseKey, null)
  }
}

export const readFailures = async () => {
  const existing = await readScopedValue(OFFLINE_FAILED_KEY)
  if (existing && typeof existing === 'object') {
    return {
      requests: Array.isArray(existing.requests) ? existing.requests : [],
      dailyLogs: Array.isArray(existing.dailyLogs) ? existing.dailyLogs : [],
    }
  }
  return { requests: [], dailyLogs: [] }
}

export const writeFailures = async (payload) => {
  if (!payload.requests.length && !payload.dailyLogs.length) {
    await writeScopedValue(OFFLINE_FAILED_KEY, null)
  } else {
    await writeScopedValue(OFFLINE_FAILED_KEY, payload)
  }
}
