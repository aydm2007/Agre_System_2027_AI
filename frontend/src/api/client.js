import axios from 'axios'
import { toast } from 'react-hot-toast'
import { dataUrlToFile, nowIso, generateOfflineId, resolveApiRoots } from './helpers'
import {
  OFFLINE_REQUESTS_KEY,
  OFFLINE_DAILY_LOGS_KEY,
  getQueueOwnerKey,
  readScopedValue,
  writeScopedValue,
  summarizeQueueItem,
  readScopedQueue,
  writeScopedQueue,
  sortByQueuedAt,
  readFailures,
  writeFailures,
} from './offlineQueueStore'
import {
  db,
  queueHarvest,
  queueGenericRequest,
  getGenericQueueCounts,
  getGenericQueueDetails,
  clearGenericQueue,
  removeGenericQueueItem,
  requeueGenericFailures,
  getHarvestQueueCounts,
  getHarvestQueueDetails,
  clearHarvestQueue,
  removeHarvestQueueItem,
  requeueHarvestFailures,
  getPendingSales,
  getDailyLogQueueCounts,
  getDailyLogQueueDetails,
  getCustodyQueueCounts,
  getCustodyQueueDetails,
  clearDailyLogQueue,
  clearCustodyQueue,
  removeDailyLogQueueItem,
  removeCustodyQueueItem,
  requeueDailyLogFailures,
  requeueCustodyFailures,
  performOfflinePurge,
  nextOfflineClientSeq,
} from '../offline/dexie_db'
import {
  getAccessTokenValue,
  setAccessTokenValue,
  clearAccessTokenValue,
  getRefreshTokenValue,
  setRefreshTokenValue,
  clearRefreshTokenValue,
} from './tokenStorage'
import { createApprovalClients } from './approvalClient'
import { createAuthClient } from './authClient'
import { createReportingClients } from './reportingClient'
import { getAuthContext } from '../auth/contextBridge'
import { sanitizeDailyLogActivityPayload, sanitizeDailyLogEnvelope } from '../utils/dailyLogPayload'
import { normalizeServiceCountsList } from '../utils/serviceCoveragePayload'
import {
  buildDailyLogIdempotencyRotationPatch,
  isIdempotencyMismatch409,
  resolveDailyLogReplayIdentity,
} from '../utils/offlineDailyLogIdentity'

const { authBase: AUTH_BASE, apiV1Base: API_V1_BASE } = resolveApiRoots()
const rawAppVersion = import.meta.env.VITE_APP_VERSION
const APP_VERSION = (typeof rawAppVersion === 'string' && rawAppVersion.trim()) || '2.0.0'
const MUTATING_METHODS = new Set(['post', 'put', 'patch', 'delete'])

const MAX_QUEUE_BATCH = 10
const MAX_QUEUE_ATTEMPTS = 5
const BASE_BACKOFF_MS = 5 * 60 * 1000
const MAX_BACKOFF_MS = 60 * 60 * 1000
const OFFLINE_FINANCE_ROUTE_PATTERNS = [
  /^\/finance\//,
  /^\/shadow-ledger\//,
  /^\/reports\/export-jobs\//,
]
const OFFLINE_DIRECT_UPLOAD_BLOCKLIST = [/^\/attachments\/?$/]
const OFFLINE_RETRYABLE_STATUSES = new Set(['pending', 'syncing', 'failed_retryable'])
const OFFLINE_FAILED_STATUSES = new Set(['dead_letter', 'quarantined'])

const describeError = (error) => {
  if (!error) return 'لا توجد تفاصيل متاحة للخطأ'
  const status = error?.response?.status
  const data = error?.response?.data
  if (status) {
    const payload = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
    return `HTTP ${status}: ${payload}`
  }
  if (error?.message) {
    return error.message
  }
  return 'خطأ غير معروف'
}

const computeNextAttempt = (attempts) => {
  const backoff = Math.min(BASE_BACKOFF_MS * Math.pow(2, Math.max(0, attempts - 1)), MAX_BACKOFF_MS)
  return new Date(Date.now() + backoff).toISOString()
}

const resolveQueueStatus = (status, deadLetter = false) => {
  if (deadLetter) return 'dead_letter'
  if (status === 'failed') return 'failed_retryable'
  if (status === 'complete' || status === 'completed') return 'synced'
  return status || 'pending'
}

const normalizeDailyLogReplayEntry = (entry = {}) => {
  const legacyData = entry.data && typeof entry.data === 'object' ? entry.data : {}
  const rawLogPayload =
    entry.logPayload && typeof entry.logPayload === 'object' ? entry.logPayload : {}
  const rawActivityPayload =
    entry.activityPayload && typeof entry.activityPayload === 'object'
      ? entry.activityPayload
      : legacyData
  const farmId =
    entry.farm_id ??
    rawLogPayload.farm_id ??
    rawLogPayload.farm ??
    legacyData.farm_id ??
    legacyData.farm ??
    entry.meta?.farmId ??
    null
  const logPayload = {
    ...rawLogPayload,
  }
  if (farmId && logPayload.farm == null && logPayload.farm_id == null) {
    logPayload.farm = farmId
  }
  if (logPayload.log_date == null && logPayload.date == null) {
    logPayload.log_date = legacyData.log_date || legacyData.date || entry.meta?.date || nowIso().slice(0, 10)
  }
  if (logPayload.notes == null && legacyData.notes != null) {
    logPayload.notes = legacyData.notes
  }
  if (logPayload.variance_note == null && legacyData.variance_note != null) {
    logPayload.variance_note = legacyData.variance_note
  }

  const activityPayload = { ...rawActivityPayload }
  if (Array.isArray(activityPayload.service_counts_payload)) {
    activityPayload.service_counts_payload = normalizeServiceCountsList(
      activityPayload.service_counts_payload,
    )
  }
  if (Array.isArray(activityPayload.service_counts)) {
    activityPayload.service_counts = normalizeServiceCountsList(activityPayload.service_counts)
  }

  return {
    ...entry,
    farm_id: farmId,
    logPayload,
    activityPayload,
    meta: {
      ...(entry.meta || {}),
      ...(farmId ? { farmId } : {}),
      ...(logPayload.log_date || logPayload.date ? { date: logPayload.log_date || logPayload.date } : {}),
    },
  }
}

const DAILY_LOG_SYNC_HISTORY_KEY = 'daily-log-sync-history'
const MAX_DAILY_LOG_SYNC_HISTORY = 50

const recordDailyLogSyncHistory = async (entry) => {
  if (!entry) return
  try {
    const existing = (await db.userData.get(DAILY_LOG_SYNC_HISTORY_KEY))?.value
    const rows = Array.isArray(existing) ? existing : []
    const nextRows = [
      {
        ...entry,
        status: entry.status || 'success',
        syncedAt: entry.syncedAt || nowIso(),
      },
      ...rows.filter((row) => row.payloadUuid !== entry.payloadUuid && row.activityId !== entry.activityId),
    ].slice(0, MAX_DAILY_LOG_SYNC_HISTORY)
    await db.userData.put({ key: DAILY_LOG_SYNC_HISTORY_KEY, value: nextRows, updated_at: nowIso() })
  } catch (error) {
    console.warn('[daily-log-sync-history] failed to record sync result', error)
  }
}

const getDailyLogSyncHistory = async () => {
  try {
    const existing = (await db.userData.get(DAILY_LOG_SYNC_HISTORY_KEY))?.value
    return Array.isArray(existing) ? existing : []
  } catch {
    return []
  }
}

const isBlockedOfflineRoute = (url) =>
  OFFLINE_FINANCE_ROUTE_PATTERNS.some((pattern) => pattern.test(String(url || '')))

const isDirectUploadRoute = (url) =>
  OFFLINE_DIRECT_UPLOAD_BLOCKLIST.some((pattern) => pattern.test(String(url || '')))

const assertOfflineReplayPolicy = (url) => {
  if (isBlockedOfflineRoute(url)) {
    throw new Error('This workflow is posture-only offline and cannot be queued for replay.')
  }
  if (isDirectUploadRoute(url)) {
    throw new Error('Attachments are stored locally as transient draft data and uploaded only after business replay succeeds.')
  }
}

const buildOfflineEnvelope = async ({
  category,
  ownerKey,
  farmId = null,
  draftUuid = null,
  payloadUuid = null,
  idempotencyKey = null,
  deviceId = 'web-client',
  extra = {},
}) => {
  const scope = farmId ? `farm:${farmId}` : 'global'
  const clientSeq = await nextOfflineClientSeq(ownerKey, category, scope)
  const uuid = payloadUuid || generateOfflineId()
  const key = idempotencyKey || makeUUID()
  return {
    queue_id: uuid,
    payload_uuid: uuid,
    uuid,
    category,
    farm_id: farmId,
    owner_key: ownerKey,
    draft_uuid: draftUuid,
    device_id: deviceId,
    client_seq: clientSeq,
    idempotency_key: key,
    status: 'pending',
    dead_letter: false,
    retry_count: 0,
    created_at: nowIso(),
    updated_at: nowIso(),
    next_attempt_at: nowIso(),
    ...extra,
  }
}

const shouldRetry = (error) => {
  const status = error?.response?.status
  if (!status) return true
  if (status === 408 || status === 429 || status >= 500) {
    return true
  }
  return false
}

let legacyOfflineMigrationPromise = null

const extractReadyJobs = (items) => {
  const now = Date.now()
  const ready = []
  const pending = []
  for (const item of items) {
    const next = new Date(item.nextAttemptAt || item.queuedAt || nowIso()).getTime()
    if (Number.isFinite(next) && next > now) {
      pending.push(item)
    } else {
      ready.push(item)
    }
  }
  return { ready, pending }
}

const scheduleBackgroundSync = () => {
  if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator && 'SyncManager' in window) {
    navigator.serviceWorker.ready
      .then((registration) => registration.sync.register('sync-offline-queue'))
      .catch((error) => {
        console.warn('Failed to register background sync', error)
      })
  }
}

const notifyQueueChange = () => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('offline-queue-change'))
  }
  scheduleBackgroundSync()
}

const migrateLegacyOfflineEntries = async () => {
  if (legacyOfflineMigrationPromise) {
    return legacyOfflineMigrationPromise
  }

  legacyOfflineMigrationPromise = (async () => {
    const ownerKey = await getQueueOwnerKey()
    const [legacyRequests, legacyDailyLogs, legacyFailures] = await Promise.all([
      readScopedQueue(OFFLINE_REQUESTS_KEY),
      readScopedQueue(OFFLINE_DAILY_LOGS_KEY),
      readFailures(),
    ])

    const migratedGeneric = (legacyRequests || []).map((item) =>
      queueGenericRequest({
        ...summarizeQueueItem(item),
        owner_key: ownerKey,
        status: resolveQueueStatus(item?.status),
        dead_letter: false,
      }),
    )

    const migratedDailyLogQueue = (legacyDailyLogs || []).map((item) =>
      db.daily_log_queue.put({
        ...summarizeQueueItem(item),
        owner_key: ownerKey,
        category: 'daily_log',
        status: resolveQueueStatus(item?.status),
        dead_letter: false,
        created_at: item?.created_at || item?.queuedAt || nowIso(),
        updated_at: nowIso(),
      }),
    )

    const migratedGenericFailures = (legacyFailures?.requests || []).map((item) =>
      queueGenericRequest({
        ...summarizeQueueItem(item),
        owner_key: ownerKey,
        status: 'dead_letter',
        dead_letter: true,
        last_error: item?.last_error || item?.lastError || null,
        dead_letter_reason: item?.last_error || item?.lastError || 'legacy_failure',
      }),
    )

    const migratedDailyFailures = (legacyFailures?.dailyLogs || []).map((item) =>
      db.daily_log_queue.put({
        ...summarizeQueueItem(item),
        owner_key: ownerKey,
        category: 'daily_log',
        status: 'dead_letter',
        dead_letter: true,
        created_at: item?.created_at || item?.queuedAt || nowIso(),
        updated_at: nowIso(),
        next_attempt_at: null,
      }),
    )

    if (
      migratedGeneric.length ||
      migratedDailyLogQueue.length ||
      migratedGenericFailures.length ||
      migratedDailyFailures.length
    ) {
      await Promise.all([
        ...migratedGeneric,
        ...migratedDailyLogQueue,
        ...migratedGenericFailures,
        ...migratedDailyFailures,
      ])
      await Promise.all([
        writeScopedQueue(OFFLINE_REQUESTS_KEY, []),
        writeScopedQueue(OFFLINE_DAILY_LOGS_KEY, []),
        writeFailures({ requests: [], dailyLogs: [] }),
      ])
    }
  })()

  try {
    await legacyOfflineMigrationPromise
  } finally {
    legacyOfflineMigrationPromise = null
  }
}

export async function uploadAttachmentsFromCache(attachments = []) {
  const uploaded = []
  for (const attachment of attachments) {
    if (!attachment) continue
    if (attachment.id && !attachment.data) {
      uploaded.push(attachment)
      continue
    }
    if (!attachment.data) continue
    const file = dataUrlToFile(
      attachment.data,
      attachment.name || 'attachment',
      attachment.type || 'application/octet-stream',
    )
    if (!file) {
      throw new Error('Failed to reconstruct attachment from cached data')
    }
    const response = await Attachments.upload(file)
    const newId = response?.data?.id
    if (!newId) {
      throw new Error('Missing attachment id from response')
    }
    uploaded.push({ id: newId, name: attachment.name })
  }
  return uploaded
}

export const api = axios.create({
  baseURL: API_V1_BASE,
  timeout: 25000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})
api.defaults.headers.common['X-App-Version'] = APP_VERSION

export const authApi = axios.create({
  baseURL: AUTH_BASE,
  timeout: 25000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})
authApi.defaults.headers.common['X-App-Version'] = APP_VERSION

const makeUUID = () => {
  const cryptoObj = globalThis.crypto
  if (cryptoObj?.randomUUID) {
    return cryptoObj.randomUUID()
  }

  const randomFill = (arr) =>
    cryptoObj?.getRandomValues
      ? cryptoObj.getRandomValues(arr)
      : Array.from({ length: arr.length }, () => Math.floor(Math.random() * 256))

  const buffer = new Uint8Array(16)
  randomFill(buffer)

  buffer[6] = (buffer[6] & 0x0f) | 0x40
  buffer[8] = (buffer[8] & 0x3f) | 0x80

  const hex = [...buffer].map((b) => b.toString(16).padStart(2, '0'))
  return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10, 16).join('')}`
}

const applyAuthHeader = (config) => {
  const cfg = config || {}
  cfg.headers = cfg.headers || {}
  const token = getAccessTokenValue()
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`
  }
  const method = cfg.method?.toLowerCase?.()
  if (method && MUTATING_METHODS.has(method)) {
    // [Agri-Guardian] Network Shield: Auto-Idempotency
    // We bind X-Idempotency-Key for strict backend checks.
    const key = makeUUID()
    if (!cfg.headers['X-Idempotency-Key']) {
      cfg.headers['X-Idempotency-Key'] = key
    }
    // Maintain legacy header just in case, or alias it
    if (!cfg.headers['Idempotency-Key']) {
      cfg.headers['Idempotency-Key'] = key
    }
  }
  return cfg
}

const resolveFarmIdFromConfig = (config) => {
  const cfg = config || {}
  const params = cfg.params || {}
  const data = cfg.data && typeof cfg.data === 'object' ? cfg.data : {}
  const candidate =
    params.farm_id ?? params.farm ?? data.farm_id ?? data.farm ?? data.farmId ?? null
  if (candidate === null || candidate === undefined || candidate === '') {
    return null
  }
  return String(candidate)
}

const resolveFarmIdFromActivePageScope = () => {
  if (typeof window === 'undefined' || !window.localStorage) return null
  const pathname = String(window.location?.pathname || '/')
  const parts = pathname.split('/').filter(Boolean)
  const page = parts[0] || 'dashboard'
  const key = `page_farm.${page}`
  const value = window.localStorage.getItem(key)
  if (!value || value === 'all') return null
  return value
}

// Farm scope propagation:
// Do not rely on global selector state. Only propagate explicit farm scope
// from request params/payload or existing header.
const applyFarmHeader = (config) => {
  const cfg = config || {}
  cfg.headers = cfg.headers || {}
  const existingHeader = cfg.headers['X-Farm-ID'] || cfg.headers['X-Farm-Id']
  const requestUrl = String(cfg.url || '')
  const requiresExplicitScope =
    /\/daily-logs(\/|$)/.test(requestUrl) ||
    /\/crop-plans(\/|$)/.test(requestUrl) ||
    /\/activities(\/|$)/.test(requestUrl)
  if (!existingHeader) {
    const resolvedFarmId =
      resolveFarmIdFromConfig(cfg) ||
      (requiresExplicitScope ? null : resolveFarmIdFromActivePageScope())
    if (resolvedFarmId) {
      cfg.headers['X-Farm-ID'] = resolvedFarmId
    }
  }
  return cfg
}

api.interceptors.request.use((config) => applyFarmHeader(applyAuthHeader(config)))

authApi.interceptors.request.use((config) => {
  const cfg = { ...config }
  cfg.headers = cfg.headers || {}
  cfg.headers['Content-Type'] = cfg.headers['Content-Type'] || 'application/json'
  return cfg
})

let refreshPromise = null

async function refreshAccessToken() {
  if (refreshPromise) {
    return refreshPromise
  }
  const refreshToken = getRefreshTokenValue()
  if (!refreshToken) {
    return null
  }

  refreshPromise = authApi
    .post('/v1/auth/refresh/', { refresh: refreshToken })
    .then(({ data }) => {
      const newAccess = data?.access
      const newRefresh = data?.refresh || refreshToken
      if (!newAccess) {
        throw new Error('Missing access token from refresh response')
      }
      setAccessTokenValue(newAccess)
      if (newRefresh) {
        setRefreshTokenValue(newRefresh)
      }
      return newAccess
    })
    .catch((error) => {
      clearAccessTokenValue()
      clearRefreshTokenValue()
      throw error
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

const handleUpgradeRequired = (response) => {
  const message =
    response?.data?.detail || '???? ??????? ?????? ????? ????? ??????? ?? ????? ????????.'
  toast.error(message)
  if (typeof window !== 'undefined' && window.location) {
    window.location.reload(true)
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error || {}
    if (!response || !config) {
      return Promise.reject(error)
    }

    if (response.status === 426) {
      handleUpgradeRequired(response)
      return Promise.reject(error)
    }

    if (response.status === 401 && !config._retry) {
      config._retry = true
      try {
        const refreshedToken = await refreshAccessToken()
        if (refreshedToken) {
          config.headers = config.headers || {}
          config.headers.Authorization = `Bearer ${refreshedToken}`
          return api.request(config)
        }
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    }

    // Global handling for Validation, Permissions, and Idempotency errors
    if (response.status === 403) {
      const msg = response?.data?.detail || response?.data?.error || 'ليس لديك الصلاحية للقيام بهذا الإجراء (403)';
      toast.error(`🔒 تنبيه حوكمة: ${msg}`, { duration: 6000 });
    } else if (response.status === 409) {
      const msg = response?.data?.detail || response?.data?.error || 'تم إرسال هذا الطلب بالفعل لتجنب التكرار (409)';
      toast.error(`⏳ معالجة متكررة: ${msg}`, { duration: 6000 });
    } else if (response.status === 400) {
      let errorText = 'بيانات غير صالحة (400)'
      if (response.data) {
        if (typeof response.data === 'string') {
          errorText = response.data
        } else if (response.data.detail) {
          errorText = response.data.detail
        } else if (response.data.error) {
          errorText = typeof response.data.error === 'string'
            ? response.data.error
            : response.data.error.message || JSON.stringify(response.data.error)
        } else if (response.data.non_field_errors) {
          errorText = Array.isArray(response.data.non_field_errors)
            ? response.data.non_field_errors.join(' - ')
            : response.data.non_field_errors
        } else {
          // [AGRI-GUARDIAN] Extract standard DRF field validation arrays natively
          const firstKey = Object.keys(response.data).find(
            (key) => Array.isArray(response.data[key]) && typeof response.data[key][0] === 'string',
          )
          if (firstKey) {
            errorText = `${firstKey}: ${response.data[firstKey][0]}`
          } else {
            // Unhandled nested objects fallback
            try {
              errorText = JSON.stringify(response.data)
            } catch (e) {
              // ignore
            }
          }
        }
        // Normalize the payload so all .catch() blocks in components see a clean .detail string
        if (
          !response.data.detail &&
          typeof response.data === 'object' &&
          !Array.isArray(response.data)
        ) {
          response.data.detail = errorText
        }
      }
      toast.error(`⚠️ رفض النظام: ${errorText}`, { duration: 6000 })
    }

    return Promise.reject(error)
  },
)

const pickStableOfflineHeaders = (headers) => {
  const src = headers || {}
  const keep = {}
    ;['X-Idempotency-Key', 'Idempotency-Key', 'X-Farm-ID', 'X-Farm-Id', 'Content-Type'].forEach(
      (key) => {
        if (src[key]) {
          keep[key] = src[key]
        }
      },
    )
  return keep
}

export async function safeRequest(method, url, data, options = {}) {
  let payload = data
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    payload = { ...data }
    const hasLegacyWellId = Object.prototype.hasOwnProperty.call(payload, 'well_id')
    const hasWellAssetId = Object.prototype.hasOwnProperty.call(payload, 'well_asset_id')
    if (
      hasLegacyWellId &&
      !hasWellAssetId &&
      payload.well_id !== null &&
      payload.well_id !== undefined &&
      payload.well_id !== ''
    ) {
      payload.well_asset_id = payload.well_id
    }
    if (
      Object.prototype.hasOwnProperty.call(payload, 'well_asset_id') &&
      payload.well_asset_id !== null &&
      payload.well_asset_id !== undefined &&
      payload.well_asset_id !== ''
    ) {
      const numericWell = Number(payload.well_asset_id)
      if (Number.isFinite(numericWell)) {
        payload.well_asset_id = numericWell
      }
    }
    if (hasLegacyWellId) {
      delete payload.well_id
    }
  }

  if (navigator.onLine) {
    // Explicitly add X-Idempotency-Key if this is a mutating method and not already present
    const isMutating = ['post', 'put', 'patch', 'delete'].includes(method.toLowerCase())
    const onlineOptions = { ...options }
    onlineOptions.headers = onlineOptions.headers || {}
    
    if (isMutating && !onlineOptions.headers['X-Idempotency-Key']) {
      onlineOptions.headers['X-Idempotency-Key'] = makeUUID()
    }

    if (url === '/activities/' && method === 'post' && payload) {
      const requestData = { ...payload }
      if (typeof requestData.log === 'string') {
        requestData.log = parseInt(requestData.log, 10)
      }
      return api.request({ ...onlineOptions, method, url, data: requestData })
    }
    return api.request({ ...onlineOptions, method, url, data: payload })
  }

  assertOfflineReplayPolicy(url)

  let offlinePayload = payload
  if (url === '/activities/' && method === 'post' && payload) {
    const requestData = { ...payload }
    if (typeof requestData.log === 'string') {
      requestData.log = parseInt(requestData.log, 10)
    }
    offlinePayload = requestData
  }

  const offlineHeadersConfig = applyFarmHeader(
    applyAuthHeader({ method, url, headers: { ...(options.headers || {}) } }),
  )

  await queueOfflineRequest({
    type: 'generic',
    method,
    url,
    data: offlinePayload,
    headers: pickStableOfflineHeaders(offlineHeadersConfig.headers),
    params: options.params,
  })
  return { data: { queued: true } }
}

const queueOfflineRequest = async (job) => {
  const entry = summarizeQueueItem(job)
  const ownerKey = await getQueueOwnerKey()
  await migrateLegacyOfflineEntries()
  await queueGenericRequest({
    ...entry,
    category: entry?.category || 'generic',
    owner_key: ownerKey,
    status: resolveQueueStatus(entry?.status),
    dead_letter: false,
  })
  notifyQueueChange()
}

export const withFarmScope = ({ farmId, paramName = 'farm_id' } = {}) => {
  if (!farmId || farmId === 'all') {
    return {}
  }
  return { [paramName]: farmId }
}

const queueOfflineDailyLog = async (entry) => {
  const normalized = summarizeQueueItem(entry)
  await db.daily_log_queue.put({
    ...normalized,
    category: normalized.category || 'daily_log',
    status: resolveQueueStatus(normalized.status, normalized.dead_letter),
    dead_letter: Boolean(normalized.dead_letter) || resolveQueueStatus(normalized.status) === 'dead_letter',
    created_at: normalized.created_at || normalized.queuedAt || nowIso(),
    updated_at: nowIso(),
  })
  notifyQueueChange()
}

async function flushGenericQueue() {
  await migrateLegacyOfflineEntries()
  const ownerKey = await getQueueOwnerKey()
  const genericQueue = await getGenericQueueDetails(ownerKey)
  const rawQueue = (genericQueue.pending || [])
    .map((item) => ({ ...item, queuedAt: item.created_at || item.queuedAt }))
    .sort(sortByQueuedAt)
  if (!rawQueue.length) {
    return { processed: 0, remaining: 0, failed: 0 }
  }

  const { ready, pending } = extractReadyJobs(rawQueue)
  const toProcess = ready.slice(0, MAX_QUEUE_BATCH)
  const remaining = ready.slice(MAX_QUEUE_BATCH).concat(pending)
  let processed = 0
  let failed = 0

  for (const job of toProcess) {
    try {
      await db.generic_queue.update(job.id, { status: 'syncing', updated_at: nowIso() })
      await api.request({
        method: job.method,
        url: job.url,
        data: job.data,
        headers: job.headers || {},
        params: job.params,
      })
      processed += 1
      await db.generic_queue.delete(job.id)
    } catch (error) {
      const attempts = (job.attempts || 0) + 1
      const retryable = shouldRetry(error) && attempts < MAX_QUEUE_ATTEMPTS
      if (retryable) {
        await db.generic_queue.update(job.id, {
          status: 'failed_retryable',
          retry_count: attempts,
          last_error: describeError(error),
          next_attempt_at: computeNextAttempt(attempts),
          updated_at: nowIso(),
        })
        remaining.push({
          ...job,
          attempts,
          lastError: describeError(error),
          nextAttemptAt: computeNextAttempt(attempts),
        })
      } else {
        await db.generic_queue.update(job.id, {
          status: 'dead_letter',
          dead_letter: true,
          retry_count: attempts,
          last_error: describeError(error),
          dead_letter_reason: describeError(error),
          next_attempt_at: null,
          updated_at: nowIso(),
        })
        failed += 1
      }
    }
  }

  notifyQueueChange()
  return {
    processed,
    remaining: remaining.length,
    failed,
  }
}

async function flushSalesQueue() {
  const ownerKey = await getQueueOwnerKey()
  const rawQueue = (await getPendingSales(ownerKey))
    .map((item) => ({ ...item, queuedAt: item.created_at || item.queuedAt }))
    .sort(sortByQueuedAt)
  if (!rawQueue.length) {
    return { processed: 0, remaining: 0, failed: 0 }
  }

  const { ready, pending } = extractReadyJobs(rawQueue)
  const toProcess = ready.slice(0, MAX_QUEUE_BATCH)
  const remaining = ready.slice(MAX_QUEUE_BATCH).concat(pending)
  let processed = 0
  let failed = 0

  for (const sale of toProcess) {
    try {
      await db.sales_queue.update(sale.id, { status: 'syncing', updated_at: nowIso() })
      const payload = { ...sale }
      delete payload.id
      delete payload.status
      delete payload.created_at
      delete payload.updated_at
      delete payload.dead_letter
      delete payload.retry_count
      delete payload.last_error
      delete payload.next_attempt_at
      delete payload.owner_key
      await api.post('/sales/', payload, {
        headers: { 'X-Idempotency-Key': sale.uuid || sale.idempotency_key || makeUUID() },
      })
      processed += 1
      await db.sales_queue.delete(sale.id)
    } catch (error) {
      const attempts = (sale.retry_count || 0) + 1
      const retryable = shouldRetry(error) && attempts < MAX_QUEUE_ATTEMPTS
      if (retryable) {
        await db.sales_queue.update(sale.id, {
          status: 'failed_retryable',
          retry_count: attempts,
          last_error: describeError(error),
          next_attempt_at: computeNextAttempt(attempts),
          updated_at: nowIso(),
        })
        remaining.push({
          ...sale,
          retry_count: attempts,
          next_attempt_at: computeNextAttempt(attempts),
        })
      } else {
        await db.sales_queue.update(sale.id, {
          status: 'dead_letter',
          dead_letter: true,
          retry_count: attempts,
          last_error: describeError(error),
          dead_letter_reason: describeError(error),
          next_attempt_at: null,
          updated_at: nowIso(),
        })
        failed += 1
      }
    }
  }

  notifyQueueChange()
  return { processed, remaining: remaining.length, failed }
}

async function clearQueueSales(type = 'all', ownerKey = null) {
  const all = await db.sales_queue.toArray()
  const scoped = ownerKey ? all.filter((item) => item.owner_key === ownerKey) : all
  const filtered =
    type === 'pending'
      ? scoped.filter((item) => ['pending', 'syncing'].includes(item.status))
      : type === 'failed'
        ? scoped.filter((item) => item.status === 'dead_letter' || item.dead_letter)
        : scoped
  if (!filtered.length) {
    return true
  }
  await db.sales_queue.bulkDelete(filtered.map((item) => item.id))
  return true
}

async function removeQueueSaleItem(id, ownerKey = null) {
  const item = await db.sales_queue.get(id)
  if (!item) {
    return false
  }
  if (ownerKey && item.owner_key !== ownerKey) {
    return false
  }
  const deletedCount = await db.sales_queue.where('id').equals(id).delete()
  return deletedCount > 0
}

async function requeueQueueSales(ownerKey = null) {
  const failed = await db.sales_queue
    .filter(
      (item) =>
        (!ownerKey || item.owner_key === ownerKey) &&
        (item.status === 'dead_letter' || item.dead_letter),
    )
    .toArray()
  if (!failed.length) {
    return 0
  }
  await Promise.all(
    failed.map((item) =>
      db.sales_queue.update(item.id, {
        status: 'pending',
        dead_letter: false,
        retry_count: 0,
        last_error: null,
        next_attempt_at: null,
        updated_at: nowIso(),
      }),
    ),
  )
  return failed.length
}

async function flushHarvestQueue() {
  const ownerKey = await getQueueOwnerKey()
  const harvestQueue = await getHarvestQueueDetails(ownerKey)
  const rawQueue = (harvestQueue.pending || [])
    .map((item) => ({ ...item, queuedAt: item.created_at || item.queuedAt }))
    .sort(sortByQueuedAt)
  if (!rawQueue.length) {
    return { processed: 0, remaining: 0, failed: 0 }
  }

  const { ready, pending } = extractReadyJobs(rawQueue)
  const toProcess = ready.slice(0, MAX_QUEUE_BATCH)
  const remaining = ready.slice(MAX_QUEUE_BATCH).concat(pending)
  let processed = 0
  let failed = 0

  for (const item of toProcess) {
    try {
      await db.harvest_queue.update(item.id, { status: 'syncing', updated_at: nowIso() })
      const replayPayload = {
        uuid: item.payload_uuid || item.uuid || item.id,
        payload_uuid: item.payload_uuid || item.uuid || item.id,
        idempotency_key: item.idempotency_key || item.uuid || makeUUID(),
        farm_id: item.farm_id || item.payload?.farm_id || item.payload?.farm || null,
        client_seq: item.client_seq || item.clientSeq || 1,
        device_id: item.device_id || item.deviceId || 'web-client',
        draft_uuid: item.draft_uuid || null,
        device_timestamp: item.device_timestamp || item.deviceTimestamp || item.created_at || nowIso(),
        harvest: item.payload || item.harvest || {},
      }
      await api.post('/offline/harvest-replay/atomic/', replayPayload, {
        headers: { 'X-Idempotency-Key': replayPayload.idempotency_key },
      })
      processed += 1
      await db.harvest_queue.delete(item.id)
    } catch (error) {
      const attempts = (item.retry_count || 0) + 1
      const retryable = shouldRetry(error) && attempts < MAX_QUEUE_ATTEMPTS
      if (retryable) {
        await db.harvest_queue.update(item.id, {
          status: 'failed_retryable',
          retry_count: attempts,
          last_error: describeError(error),
          next_attempt_at: computeNextAttempt(attempts),
          updated_at: nowIso(),
        })
        remaining.push({
          ...item,
          retry_count: attempts,
          next_attempt_at: computeNextAttempt(attempts),
        })
      } else {
        await db.harvest_queue.update(item.id, {
          status: 'dead_letter',
          dead_letter: true,
          retry_count: attempts,
          last_error: describeError(error),
          dead_letter_reason: describeError(error),
          next_attempt_at: null,
          updated_at: nowIso(),
        })
        failed += 1
      }
    }
  }

  notifyQueueChange()
  return { processed, remaining: remaining.length, failed }
}

/**
 * [AGRI-GUARDIAN] Extract the server's expected client_seq from a VALIDATION_ERROR response.
 * Returns the expected integer or null if not applicable.
 */
function extractExpectedSeq(error) {
  try {
    const data = error?.response?.data
    if (!data) return null
    const details = data?.error?.details || data?.details || {}
    const expected = details?.expected_client_seq
    if (Array.isArray(expected) && expected.length > 0) {
      const val = parseInt(expected[0], 10)
      return Number.isFinite(val) ? val : null
    }
    if (typeof expected === 'number') return expected
    if (typeof expected === 'string') {
      const val = parseInt(expected, 10)
      return Number.isFinite(val) ? val : null
    }
    return null
  } catch (e) {
    return null
  }
}

async function flushOfflineDailyLogs() {
  const ownerKey = await getQueueOwnerKey()
  const allEntries = await db.daily_log_queue.toArray()

  // [AGRI-GUARDIAN] Stale Syncing Recovery: reset items stuck in 'syncing' for >60s
  const STALE_SYNCING_MS = 60 * 1000
  const staleCutoff = Date.now()
  for (const item of allEntries) {
    if (item.status === 'syncing' && item.updated_at) {
      const elapsed = staleCutoff - new Date(item.updated_at).getTime()
      if (elapsed > STALE_SYNCING_MS) {
        await db.daily_log_queue.update(item.id, {
          status: 'pending',
          dead_letter: false,
          next_attempt_at: nowIso(),
          updated_at: nowIso(),
        })
        item.status = 'pending'
      }
    }
  }

  const rawQueue = allEntries
    .filter((item) => (!ownerKey || item.owner_key === ownerKey) && OFFLINE_RETRYABLE_STATUSES.has(item.status))
    .map((item) => ({ ...item, queuedAt: item.created_at || item.queuedAt }))
    .sort(sortByQueuedAt)
  if (!rawQueue.length) {
    return { processed: 0, remaining: 0, failed: 0, syncedEntries: [] }
  }

  const { ready, pending } = extractReadyJobs(rawQueue)
  const toProcess = ready.slice(0, MAX_QUEUE_BATCH)
  const remaining = ready.slice(MAX_QUEUE_BATCH).concat(pending)
  let processed = 0
  let failed = 0
  const syncedEntries = []

  for (const entry of toProcess) {
    const normalizedEntry = normalizeDailyLogReplayEntry(entry)
    const attachments = Array.isArray(entry.attachments) ? entry.attachments : []
    const previouslyUploaded = Array.isArray(entry.uploadedAttachmentIds)
      ? entry.uploadedAttachmentIds
      : []
    let attachmentIds = previouslyUploaded.slice()
    try {
      await db.daily_log_queue.update(entry.id, { status: 'syncing', updated_at: nowIso() })
      const freshUploads = attachments.length ? await uploadAttachmentsFromCache(attachments) : []
      attachmentIds = Array.from(
        new Set(
          [
            ...previouslyUploaded,
            ...(Array.isArray(entry.logPayload?.attachments) ? entry.logPayload.attachments : []),
            ...freshUploads.map((att) => att.id),
          ].filter(Boolean),
        ),
      )

        const logPayload = attachmentIds.length
          ? { ...normalizedEntry.logPayload, attachments: attachmentIds }
          : normalizedEntry.logPayload

        const replayIdentity = resolveDailyLogReplayIdentity(normalizedEntry, makeUUID)
        const previousAttemptKey = normalizedEntry.idempotency_key || normalizedEntry.idempotencyKey || null
        if (previousAttemptKey !== replayIdentity.idempotencyKey) {
          const rotatedAt = nowIso()
          await db.daily_log_queue.update(entry.id, {
            idempotency_key: replayIdentity.idempotencyKey,
            previous_idempotency_key: previousAttemptKey,
            updated_at: rotatedAt,
            meta: {
              ...(normalizedEntry.meta || {}),
              ...(previousAttemptKey ? { previous_idempotency_key: previousAttemptKey } : {}),
              idempotency_key_rotated_at: rotatedAt,
              idempotency_key_rotation_reason: 'invalid_uuid',
            },
          })
          notifyQueueChange()
        }
        const replayPayload = {
          uuid: replayIdentity.payloadUuid,
          payload_uuid: replayIdentity.payloadUuid,
          idempotency_key: replayIdentity.idempotencyKey,
          draft_uuid: normalizedEntry.draft_uuid || normalizedEntry.meta?.draft_uuid || null,
          device_timestamp: normalizedEntry.device_timestamp || normalizedEntry.deviceTimestamp || nowIso(),
          client_seq: normalizedEntry.client_seq || normalizedEntry.clientSeq || 1,
          device_id: normalizedEntry.device_id || normalizedEntry.deviceId || 'web-client',
          farm_id: normalizedEntry.farm_id || logPayload?.farm || normalizedEntry.meta?.farmId || null,
          supervisor_id: normalizedEntry.supervisor_id || normalizedEntry.meta?.supervisorId || normalizedEntry.activityPayload?.supervisor_id || normalizedEntry.activityPayload?.supervisor || null,
          log: logPayload,
          activity: normaliseActivityPayload(normalizedEntry.activityPayload || {}),
          client_metadata: normalizedEntry.meta || {},
          attachment_refs: attachmentIds,
          lookup_snapshot_version:
            normalizedEntry.lookup_snapshot_version || normalizedEntry.meta?.lookup_snapshot_version || null,
          task_contract_snapshot:
            normalizedEntry.task_contract_snapshot || normalizedEntry.meta?.task_contract_snapshot || null,
        }

        const replayResponse = await api.post('/offline/daily-log-replay/atomic/', replayPayload, {
          headers: { 'X-Idempotency-Key': replayPayload.idempotency_key },
        })
        const logId = replayResponse?.data?.log_id
        const activityId = replayResponse?.data?.activity_id

        processed += 1
        await db.daily_log_queue.delete(entry.id)
        syncedEntries.push({
          logId,
          activityId,
          payloadUuid: replayPayload.payload_uuid,
          draftUuid: normalizedEntry.draft_uuid || normalizedEntry.meta?.draft_uuid || null,
          farmId: replayPayload.farm_id ?? logPayload?.farm ?? normalizedEntry.meta?.farmId ?? null,
          date: logPayload?.log_date || logPayload?.date || normalizedEntry.meta?.date || null,
          taskId: normalizedEntry.activityPayload?.task_id ?? normalizedEntry.meta?.taskId ?? null,
        taskName:
          normalizedEntry.meta?.taskName || normalizedEntry.meta?.taskLabel || normalizedEntry.activityPayload?.task_name || null,
        meta: normalizedEntry.meta || null,
        queuedAt: normalizedEntry.queuedAt || normalizedEntry.queued_at || null,
      })
        await recordDailyLogSyncHistory(syncedEntries[syncedEntries.length - 1])
    } catch (error) {
      if (isIdempotencyMismatch409(error)) {
        const patch = buildDailyLogIdempotencyRotationPatch(entry, {
          newKey: makeUUID(),
          nowIsoValue: nowIso(),
          lastError: describeError(error),
        })
        await db.daily_log_queue.update(entry.id, {
          ...patch,
          uploadedAttachmentIds: attachmentIds,
        })
        notifyQueueChange()
        remaining.push({
          ...entry,
          ...patch,
          uploadedAttachmentIds: attachmentIds,
        })
        continue
      }
      // [AGRI-GUARDIAN] Auto-correct client_seq on server rejection
      const serverExpectedSeq = extractExpectedSeq(error)
      if (serverExpectedSeq !== null) {
        console.warn('[OfflineSync] Server expected seq ' + serverExpectedSeq + ', client sent ' + entry.client_seq + '. Auto-correcting...')
        const allQueueItems = (await db.daily_log_queue.toArray())
          .filter(function(item) { return item.status === 'pending' || item.status === 'syncing' || item.status === 'failed_retryable' || item.id === entry.id })
          .sort(function(a, b) { return new Date(a.created_at || a.queuedAt || 0) - new Date(b.created_at || b.queuedAt || 0) })
        let correctedSeq = serverExpectedSeq
        for (const qItem of allQueueItems) {
          await db.daily_log_queue.update(qItem.id, {
            client_seq: correctedSeq,
            status: 'pending',
            retry_count: 0,
            last_error: null,
            next_attempt_at: null,
            updated_at: nowIso(),
          })
          correctedSeq++
        }
        await db.userData.put({ key: 'daily_log_client_seq', value: correctedSeq - 1, updated_at: nowIso() })
        remaining.push({ ...entry, client_seq: serverExpectedSeq, retry_count: 0, status: 'pending' })
      } else {
      const attempts = (entry.attempts || 0) + 1
      const retryable = shouldRetry(error) && attempts < MAX_QUEUE_ATTEMPTS
      const enriched = summarizeQueueItem({
        ...entry,
        attempts,
        lastError: describeError(error),
        nextAttemptAt: computeNextAttempt(attempts),
        uploadedAttachmentIds: attachmentIds,
      })
        if (retryable) {
          await db.daily_log_queue.update(entry.id, {
            status: 'failed_retryable',
            retry_count: attempts,
            last_error: describeError(error),
            next_attempt_at: computeNextAttempt(attempts),
            uploadedAttachmentIds: attachmentIds,
            updated_at: nowIso(),
          })
          remaining.push(enriched)
        } else {
          await db.daily_log_queue.update(entry.id, {
            status: 'dead_letter',
            dead_letter: true,
            retry_count: attempts,
            last_error: describeError(error),
            dead_letter_reason: describeError(error),
            next_attempt_at: null,
            uploadedAttachmentIds: attachmentIds,
            updated_at: nowIso(),
          })
          failed += 1
        }
      }
    }
  }

  notifyQueueChange()
  return { processed, remaining: remaining.length, failed, syncedEntries }
}

async function flushCustodyQueue() {
  const ownerKey = await getQueueOwnerKey()
  const allEntries = await db.custody_queue.toArray()
  const rawQueue = allEntries
    .filter((item) => (!ownerKey || item.owner_key === ownerKey) && OFFLINE_RETRYABLE_STATUSES.has(item.status))
    .map((item) => ({ ...item, queuedAt: item.created_at || item.queuedAt }))
    .sort(sortByQueuedAt)
  if (!rawQueue.length) {
    return { processed: 0, remaining: 0, failed: 0 }
  }

  const { ready, pending } = extractReadyJobs(rawQueue)
  const toProcess = ready.slice(0, MAX_QUEUE_BATCH)
  const remaining = ready.slice(MAX_QUEUE_BATCH).concat(pending)
  let processed = 0
  let failed = 0

  for (const entry of toProcess) {
    try {
      await db.custody_queue.update(entry.id, { status: 'syncing', updated_at: nowIso() })
      const payload = entry.payload || {}
      const actionName = entry.action_name || payload.action_name
      const transferId = entry.transfer_id || payload.transfer_id || null
      if (!actionName) {
        throw new Error('Missing custody action context')
      }
      const replayPayload = {
        uuid: entry.payload_uuid || entry.uuid || entry.id,
        payload_uuid: entry.payload_uuid || entry.uuid || entry.id,
        idempotency_key: entry.idempotency_key || makeUUID(),
        farm_id: entry.farm_id || payload.farm_id || payload.farm || null,
        supervisor_id: entry.supervisor_id || payload.supervisor_id || payload.supervisor || null,
        client_seq: entry.client_seq || entry.clientSeq || 1,
        device_id: entry.device_id || entry.deviceId || 'web-client',
        device_timestamp: entry.device_timestamp || entry.deviceTimestamp || entry.created_at || nowIso(),
        action_name: actionName,
        transfer_id: transferId,
        payload,
      }
      await api.post('/offline/custody-replay/atomic/', replayPayload, {
        headers: { 'X-Idempotency-Key': replayPayload.idempotency_key },
      })
      processed += 1
      await db.custody_queue.delete(entry.id)
    } catch (error) {
      const attempts = (entry.retry_count || entry.attempts || 0) + 1
      const retryable = shouldRetry(error) && attempts < MAX_QUEUE_ATTEMPTS
      if (retryable) {
        await db.custody_queue.update(entry.id, {
          status: 'failed_retryable',
          retry_count: attempts,
          last_error: describeError(error),
          next_attempt_at: computeNextAttempt(attempts),
          updated_at: nowIso(),
        })
        remaining.push(entry)
      } else {
        await db.custody_queue.update(entry.id, {
          status: 'dead_letter',
          dead_letter: true,
          retry_count: attempts,
          last_error: describeError(error),
          dead_letter_reason: describeError(error),
          next_attempt_at: null,
          updated_at: nowIso(),
        })
        failed += 1
      }
    }
  }
  notifyQueueChange()
  return { processed, remaining: remaining.length, failed }
}

export async function enqueueDailyLogSubmission(entry) {
  const sanitizedEntry = sanitizeDailyLogEnvelope(entry)
  const ownerKey = await getQueueOwnerKey()
  const farmId =
    sanitizedEntry?.logPayload?.farm ??
    sanitizedEntry?.logPayload?.farm_id ??
    sanitizedEntry?.activityPayload?.farm_id ??
    sanitizedEntry?.activityPayload?.farm ??
    sanitizedEntry?.meta?.farmId ??
    null
  const draftUuid = sanitizedEntry?.draft_uuid || sanitizedEntry?.meta?.draft_uuid || generateOfflineId()
  const envelope = await buildOfflineEnvelope({
    category: 'daily_log',
    ownerKey,
    farmId,
    draftUuid,
    payloadUuid: sanitizedEntry?.uuid || sanitizedEntry?.id || generateOfflineId(),
    extra: {
      lookup_snapshot_version: sanitizedEntry?.lookup_snapshot_version || sanitizedEntry?.meta?.lookup_snapshot_version || null,
      task_contract_snapshot: sanitizedEntry?.task_contract_snapshot || sanitizedEntry?.meta?.task_contract_snapshot || null,
    },
  })
  const safeEntry = summarizeQueueItem({
    id: envelope.queue_id,
    type: 'daily-log',
    category: 'daily_log',
    logPayload: sanitizedEntry.logPayload,
    activityPayload: sanitizedEntry.activityPayload,
    meta: sanitizedEntry?.meta ? { ...sanitizedEntry.meta } : null,
    attachments: Array.isArray(sanitizedEntry.attachments)
      ? sanitizedEntry.attachments.map((att) => ({
        name: att.name,
        type: att.type,
        size: att.size,
        data: att.data,
      }))
      : [],
    farm_id: farmId,
    owner_key: ownerKey,
    draft_uuid: draftUuid,
    queue_id: envelope.queue_id,
    payload_uuid: envelope.payload_uuid,
    device_id: envelope.device_id,
    client_seq: envelope.client_seq,
    idempotency_key: envelope.idempotency_key,
    queuedAt: envelope.created_at,
    attempts: 0,
    lastError: null,
    nextAttemptAt: envelope.next_attempt_at,
    idempotencyKey: envelope.idempotency_key,
    activityIdempotencyKey: makeUUID(),
    lookup_snapshot_version: envelope.lookup_snapshot_version,
    task_contract_snapshot: envelope.task_contract_snapshot,
  })
  await queueOfflineDailyLog(safeEntry)
  return { queued: true }
}

export async function enqueueOfflineMutation({ category, payload = {}, meta = {}, attachments = [] }) {
  if (category === 'daily_log') {
    return enqueueDailyLogSubmission({
      logPayload: payload.logPayload || payload.log || {},
      activityPayload: payload.activityPayload || payload.activity || {},
      meta,
      attachments,
      uuid: payload.uuid || payload.payload_uuid || null,
      draft_uuid: payload.draft_uuid || meta?.draft_uuid || null,
      lookup_snapshot_version: payload.lookup_snapshot_version || meta?.lookup_snapshot_version || null,
      task_contract_snapshot: payload.task_contract_snapshot || meta?.task_contract_snapshot || null,
    })
  }
  if (category === 'harvest') {
    return HarvestLogs.create(payload)
  }
  if (category === 'custody') {
    return CustodyTransfers.enqueueOfflineAction({
      transferId: payload.transfer_id || null,
      actionName: payload.action_name || meta?.action_name || 'issue',
      body: payload.body || payload,
      farmId: payload.farm_id || payload.farm || meta?.farmId || null,
      supervisorId: payload.supervisor_id || payload.supervisor || meta?.supervisorId || null,
      idempotencyKey: payload.idempotency_key || null,
    })
  }
  throw new Error(`Unsupported offline mutation category: ${category}`)
}
export async function flushQueue() {
  const ownerKey = await getQueueOwnerKey()
  const [genericResult, salesResult, harvestResult, dailyResult, custodyResult] = await Promise.all([
    flushGenericQueue(ownerKey),
    flushSalesQueue(ownerKey),
    flushHarvestQueue(ownerKey),
    flushOfflineDailyLogs(ownerKey),
    flushCustodyQueue(),
  ])
  const requestResult = genericResult || { processed: 0, remaining: 0, failed: 0 }

  const result = {
    processedRequests: requestResult.processed + salesResult.processed,
    processedHarvests: harvestResult.processed,
    processedDailyLogs: dailyResult.processed,
    processedCustody: custodyResult.processed,
    failedRequests: requestResult.failed + salesResult.failed,
    failedHarvests: harvestResult.failed,
    failedDailyLogs: dailyResult.failed,
    failedCustody: custodyResult.failed,
    remainingRequests: requestResult.remaining + salesResult.remaining,
    remainingHarvests: harvestResult.remaining,
    remainingDailyLogs: dailyResult.remaining,
    remainingCustody: custodyResult.remaining,
    totalProcessed:
      requestResult.processed +
      salesResult.processed +
      harvestResult.processed +
      dailyResult.processed +
      custodyResult.processed,
    syncedDailyLogs: dailyResult.syncedEntries || [],
  }

  // [AGRI-GUARDIAN] Axis 20: Auto-Purge Trigger
  if (result.totalProcessed > 0 && navigator.onLine) {
    try {
      // Lazy fetch settings to avoid circular dependencies or heavy upfront load
      const { data: currentSettings } = await Farms.settings()
      if (currentSettings?.enable_offline_media_purge || currentSettings?.offline_cache_retention_days) {
        await performOfflinePurge(currentSettings)
      }
    } catch (e) {
      console.warn('[flushQueue] Auto-purge trigger failed (non-critical)', e)
    }
  }

  return result
}

export async function getOfflineQueueCounts() {
  await migrateLegacyOfflineEntries()
  const ownerKey = await getQueueOwnerKey()
  const [genericCounts, sales, harvestCounts, dexieCounts, custodyCounts] = await Promise.all([
    getGenericQueueCounts(ownerKey),
    db.sales_queue.toArray(),
    getHarvestQueueCounts(ownerKey),
    getDailyLogQueueCounts(ownerKey),
    getCustodyQueueCounts(ownerKey),
  ])

  const scopedSales = sales.filter((item) => item.owner_key === ownerKey)
  const requests =
    (genericCounts.pending || 0) +
    scopedSales.filter((item) => OFFLINE_RETRYABLE_STATUSES.has(item.status)).length
  const harvests = harvestCounts.pending || 0
  const dailyLogs = dexieCounts.pending || 0
  const custody = custodyCounts.pending || 0
  const failedRequests =
    (genericCounts.failed || 0) +
    scopedSales.filter((item) => OFFLINE_FAILED_STATUSES.has(item.status) || item.dead_letter).length
  const failedHarvests = harvestCounts.failed || 0
  const failedDailyLogs = dexieCounts.failed || 0
  const failedCustody = custodyCounts.failed || 0

  return {
    requests,
    harvests,
    dailyLogs,
    custody,
    failedRequests,
    failedHarvests,
    failedDailyLogs,
    failedCustody,
  }
}


export async function getOfflineQueueDetails(options = {}) {
  const { limit = 100 } = options
  await migrateLegacyOfflineEntries()
  const ownerKey = await getQueueOwnerKey()

  const [genericQueue, salesQueue, harvestQueue, dexieQueue, custodyQueue, syncRecordsResponse, syncConflictsResponse, quarantinesResponse] = await Promise.all([
    getGenericQueueDetails(ownerKey),
    db.sales_queue.toArray(),
    getHarvestQueueDetails(ownerKey),
    getDailyLogQueueDetails(ownerKey),
    getCustodyQueueDetails(ownerKey),
    api.get('/sync-records/', { params: { page_size: limit, status: 'success', exclude_demo: 1 } }).catch(() => ({ data: [] })),
    api.get('/sync-conflict-dlq/', { params: { page_size: limit, status: 'PENDING', exclude_demo: 1 } }).catch(() => ({ data: [] })),
    api.get('/offline-sync-quarantines/', { params: { page_size: limit, status: 'PENDING_REVIEW', exclude_demo: 1 } }).catch(() => ({ data: [] })),
  ])
  const localDailyLogSyncHistory = await getDailyLogSyncHistory()

  const salesPending = salesQueue
    .filter((item) => item.owner_key === ownerKey && OFFLINE_RETRYABLE_STATUSES.has(item.status))
    .map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      method: 'post',
      url: '/sales/',
      meta: {
        ...(item.meta || {}),
        queueLabel: 'sales_queue',
      },
    }))
    .sort(sortByQueuedAt)
  const salesFailed = salesQueue
    .filter((item) => item.owner_key === ownerKey && (OFFLINE_FAILED_STATUSES.has(item.status) || item.dead_letter))
    .map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      status: 'dead_letter',
      method: 'post',
      url: '/sales/',
      meta: {
        ...(item.meta || {}),
        queueLabel: 'sales_queue',
      },
    }))
    .sort(sortByQueuedAt)

  const allRequests = [
    ...(genericQueue.pending || []).map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      meta: {
        ...(item.meta || {}),
        queueLabel: 'generic_queue',
      },
    })),
    ...salesPending,
  ].sort(sortByQueuedAt)

  const allHarvests = (harvestQueue.pending || [])
    .map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      meta: {
        ...(item.meta || {}),
        queueLabel: 'harvest_queue',
      },
    }))
    .sort(sortByQueuedAt)

  const dexiePendingLogs = (dexieQueue.pending || []).map((item) => ({
    ...item,
    queuedAt: item.created_at || item.queuedAt,
  }))
  const allDailyLogs = dexiePendingLogs.sort(sortByQueuedAt)
  const allCustody = (custodyQueue.pending || [])
    .map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
    }))
    .sort(sortByQueuedAt)

  const allFailedRequests = [
    ...(genericQueue.failed || []).map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      status: 'dead_letter',
      meta: {
        ...(item.meta || {}),
        queueLabel: 'generic_queue',
      },
    })),
    ...salesFailed,
  ].sort(sortByQueuedAt)
  const allFailedHarvests = (harvestQueue.failed || [])
    .map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      status: 'dead_letter',
      meta: {
        ...(item.meta || {}),
        queueLabel: 'harvest_queue',
      },
    }))
    .sort(sortByQueuedAt)
  const allFailedDailyLogs = (dexieQueue.failed || [])
    .map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      status: 'dead_letter',
    }))
    .sort(sortByQueuedAt)
  const allFailedCustody = (custodyQueue.failed || [])
    .map((item) => ({
      ...item,
      queuedAt: item.created_at || item.queuedAt,
      status: 'dead_letter',
    }))
    .sort(sortByQueuedAt)

  const take = (items) => {
    if (!Number.isFinite(limit) || limit <= 0) {
      return items
    }
    return items.slice(0, limit)
  }

  const buildMeta = (items, limited) => ({
    total: items.length,
    returned: limited.length,
    truncated: items.length > limited.length,
  })

    const limitedRequests = take(allRequests)
    const limitedHarvests = take(allHarvests)
    const limitedDailyLogs = take(allDailyLogs)
    const limitedCustody = take(allCustody)
    const limitedFailedRequests = take(allFailedRequests)
    const limitedFailedHarvests = take(allFailedHarvests)
    const limitedFailedDailyLogs = take(allFailedDailyLogs)
    const limitedFailedCustody = take(allFailedCustody)
    const serverSyncRecords = Array.isArray(syncRecordsResponse?.data?.results) ? syncRecordsResponse.data.results : syncRecordsResponse?.data || []
    const syncRecords = take([
      ...localDailyLogSyncHistory.map((row) => ({
        id: row.payloadUuid || row.activityId || row.syncedAt,
        category: 'daily_log',
        reference: row.payloadUuid || row.draftUuid || row.activityId,
        status: row.status || 'success',
        payload: row,
        updated_at: row.syncedAt,
        local: true,
      })),
      ...serverSyncRecords,
    ]
      .filter((row) => row?.status === 'success')
      .filter((row) => !(row?.payload?.demo_fixture || row?.reference?.startsWith?.('demo-')))
      .sort((left, right) =>
        String(right?.updated_at || right?.created_at || '').localeCompare(
          String(left?.updated_at || left?.created_at || ''),
        ),
      ))
    const syncConflicts = take(Array.isArray(syncConflictsResponse?.data?.results) ? syncConflictsResponse.data.results : syncConflictsResponse?.data || [])
    const quarantines = take(Array.isArray(quarantinesResponse?.data?.results) ? quarantinesResponse.data.results : quarantinesResponse?.data || [])

    return {
      requests: limitedRequests,
      harvests: limitedHarvests,
      dailyLogs: limitedDailyLogs,
      custody: limitedCustody,
      failedRequests: limitedFailedRequests,
      failedHarvests: limitedFailedHarvests,
      failedDailyLogs: limitedFailedDailyLogs,
      failedCustody: limitedFailedCustody,
      syncRecords,
      syncConflicts,
      quarantines,
      meta: {
        requests: buildMeta(allRequests, limitedRequests),
        harvests: buildMeta(allHarvests, limitedHarvests),
        dailyLogs: buildMeta(allDailyLogs, limitedDailyLogs),
        custody: buildMeta(allCustody, limitedCustody),
        failedRequests: buildMeta(allFailedRequests, limitedFailedRequests),
        failedHarvests: buildMeta(allFailedHarvests, limitedFailedHarvests),
        failedDailyLogs: buildMeta(allFailedDailyLogs, limitedFailedDailyLogs),
        failedCustody: buildMeta(allFailedCustody, limitedFailedCustody),
        syncRecords: { total: syncRecords.length, returned: syncRecords.length, truncated: false },
        syncConflicts: { total: syncConflicts.length, returned: syncConflicts.length, truncated: false },
        quarantines: { total: quarantines.length, returned: quarantines.length, truncated: false },
      },
    }
}

export const flushOfflineQueue = flushQueue
export const getOfflineQueueStatus = getOfflineQueueCounts
export const retryDeadLetters = requeueFailedItems
export const removeQueuedItem = removeOfflineQueueItem


export const Farms = {
  list: async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []

    const filteredParams =
      !params.farm_id && userFarmIds.length > 0
        ? { ...params, farm_id: userFarmIds.join(',') }
        : params

    return api.get('/farms/', { params: filteredParams })
  },
  retrieve: async (id) => {
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(id)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return api.get(`/farms/${id}/`)
  },
  create: (payload) => safeRequest('post', '/farms/', payload),
  update: async (id, payload) => {
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(id)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('patch', `/farms/${id}/`, payload)
  },
  delete: async (id) => {
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(id)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('delete', `/farms/${id}/`)
  },
}
export const CostCenters = {
  list: async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []
    const filteredParams =
      !params.farm_id && userFarmIds.length > 0
        ? { ...params, farm_id: userFarmIds.join(',') }
        : params
    return api.get('/finance/cost-centers/', { params: filteredParams })
  },
  create: (payload) => safeRequest('post', '/finance/cost-centers/', payload),
  update: (id, payload) => safeRequest('patch', `/finance/cost-centers/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/finance/cost-centers/${id}/`),
}
const { ApprovalRules, ApprovalRequests } = createApprovalClients({ api, safeRequest })
export { ApprovalRules, ApprovalRequests }

export const CropRecipes = {
  list: async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []
    const filteredParams =
      !params.farm_id && userFarmIds.length > 0
        ? { ...params, farm_id: userFarmIds.join(',') }
        : params
    return api.get('/crop-recipes/', { params: filteredParams })
  },
  retrieve: (id) => api.get(`/crop-recipes/${id}/`),
  create: (payload) => safeRequest('post', '/crop-recipes/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-recipes/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/crop-recipes/${id}/`),
}

export const CropRecipeMaterials = {
  list: async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []
    const filteredParams =
      !params.farm_id && userFarmIds.length > 0
        ? { ...params, farm_id: userFarmIds.join(',') }
        : params
    return api.get('/crop-recipe-materials/', { params: filteredParams })
  },
  create: (payload) => safeRequest('post', '/crop-recipe-materials/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-recipe-materials/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/crop-recipe-materials/${id}/`),
}

export const CropRecipeTasks = {
  list: async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []
    const filteredParams =
      !params.farm_id && userFarmIds.length > 0
        ? { ...params, farm_id: userFarmIds.join(',') }
        : params
    return api.get('/crop-recipe-tasks/', { params: filteredParams })
  },
  create: (payload) => safeRequest('post', '/crop-recipe-tasks/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-recipe-tasks/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/crop-recipe-tasks/${id}/`),
}

export const VarianceAlerts = {
  list: async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []
    const filteredParams =
      !params.farm_id && userFarmIds.length > 0
        ? { ...params, farm_id: userFarmIds.join(',') }
        : params
    return api.get('/variance-alerts/', { params: filteredParams })
  },
  retrieve: (id) => api.get(`/variance-alerts/${id}/`),
  update: (id, payload) => safeRequest('patch', `/variance-alerts/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/variance-alerts/${id}/`),
}

export const Crops = {
  list: async (params = {}) => {
    if (params.global) {
      const globalParams = { ...params }
      delete globalParams.global
      return api.get('/crops/', { params: globalParams })
    }

    if (params.farm_id) {
      return api.get('/crops/', { params })
    }

    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []

    if (userFarmIds.length === 0) {
      return { data: [] }
    }

    if (userFarmIds.length === 1) {
      return api.get('/crops/', { params: { ...params, farm_id: userFarmIds[0] } })
    }

    const promises = userFarmIds.map((farmId) =>
      api.get('/crops/', { params: { ...params, farm_id: farmId } }),
    )

    const responses = await Promise.all(promises)

    const allCrops = responses.flatMap((response) => response.data.results || response.data)

    const uniqueCrops = []
    const cropIds = new Set()

    for (const crop of allCrops) {
      if (!cropIds.has(crop.id)) {
        cropIds.add(crop.id)
        uniqueCrops.push(crop)
      }
    }

    return {
      data: {
        results: uniqueCrops,
        count: uniqueCrops.length,
      },
    }
  },
  tasks: async (cropId, params = {}) => {
    return api.get('/tasks/', { params: { crop: cropId, ...params } })
  },
  varieties: (cropId, params = {}) =>
    api.get('/crop-varieties/', { params: { crop: cropId, ...params } }),
  addTask: (cropId, payload) => safeRequest('post', '/tasks/', { ...payload, crop: cropId }),
  updateTask: (cropId, taskId, payload) => safeRequest('patch', `/tasks/${taskId}/`, payload),
  deleteTask: (cropId, taskId) => safeRequest('delete', `/tasks/${taskId}/`),
  create: (payload) => safeRequest('post', '/crops/', payload),
  update: (id, payload) => safeRequest('patch', `/crops/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/crops/${id}/`),
}

export const FarmCrops = {
  list: async (params = {}) => {
    if (params.farm_id) {
      return api.get('/farm-crops/', { params })
    }

    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []

    if (userFarmIds.length === 0) {
      return { data: [] }
    }

    if (userFarmIds.length === 1) {
      return api.get('/farm-crops/', { params: { ...params, farm_id: userFarmIds[0] } })
    }

    const promises = userFarmIds.map((farmId) =>
      api.get('/farm-crops/', { params: { ...params, farm_id: farmId } }),
    )

    const responses = await Promise.all(promises)

    const allFarmCrops = responses.flatMap((response) => response.data.results || response.data)

    return {
      data: {
        results: allFarmCrops,
        count: allFarmCrops.length,
      },
    }
  },
  create: async (payload) => {
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(payload.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('post', '/farm-crops/', payload)
  },
  delete: async (id) => {
    const { data } = await api.get(`/farm-crops/${id}/`)
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(data.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('delete', `/farm-crops/${id}/`)
  },
}

export const Locations = {
  list: async (params = {}) => {
    if (params.farm_id) {
      return api.get('/locations/', { params })
    }

    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []

    if (userFarmIds.length === 0) {
      return { data: [] }
    }

    if (userFarmIds.length === 1) {
      return api.get('/locations/', { params: { ...params, farm_id: userFarmIds[0] } })
    }

    const promises = userFarmIds.map((farmId) =>
      api.get('/locations/', { params: { ...params, farm_id: farmId } }),
    )

    const responses = await Promise.all(promises)

    const allLocations = responses.flatMap((response) => response.data.results || response.data)

    return {
      data: {
        results: allLocations,
        count: allLocations.length,
      },
    }
  },
  create: async (payload) => {
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(payload.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('post', '/locations/', payload)
  },
  update: async (id, payload) => {
    const { data } = await api.get(`/locations/${id}/`)
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(data.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('patch', `/locations/${id}/`, payload)
  },
  delete: async (id) => {
    const { data } = await api.get(`/locations/${id}/`)
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(data.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('delete', `/locations/${id}/`)
  },
}

export const Assets = {
  list: async (params = {}) => {
    if (params.farm_id) {
      return api.get('/assets/', { params })
    }

    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []

    if (userFarmIds.length === 0) {
      return { data: [] }
    }

    if (userFarmIds.length === 1) {
      return api.get('/assets/', { params: { ...params, farm_id: userFarmIds[0] } })
    }

    const promises = userFarmIds.map((farmId) =>
      api.get('/assets/', { params: { ...params, farm_id: farmId } }),
    )

    const responses = await Promise.all(promises)

    const allAssets = responses.flatMap((response) => response.data.results || response.data)

    return {
      data: {
        results: allAssets,
        count: allAssets.length,
      },
    }
  },
  create: async (payload) => {
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(payload.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('post', '/assets/', payload)
  },
  update: async (id, payload) => {
    const { data } = await api.get(`/assets/${id}/`)
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(data.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('patch', `/assets/${id}/`, payload)
  },
  delete: async (id) => {
    const { data } = await api.get(`/assets/${id}/`)
    const authContext = getAuthContext()
    const hasFarmAccess = authContext ? authContext.hasFarmAccess : () => false

    if (!hasFarmAccess(data.farm)) {
      throw new Error('لا تملك صلاحية الوصول إلى هذه المزرعة')
    }

    return safeRequest('delete', `/assets/${id}/`)
  },
  get: (id) => api.get(`/assets/${id}/`),
  retrieve: (id) => api.get(`/assets/${id}/`),
  remove: async function(id) { return this.delete(id) },
  treeSnapshot: (id, params) =>
    api.get(`/assets/tree-snapshot/`, { params: { location_id: id, ...params } }),
}
export const Units = {
  list: (params = {}) => api.get('/units/', { params }),
  create: (payload) => safeRequest('post', '/units/', payload),
  update: (id, payload) => safeRequest('patch', `/units/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/units/${id}/`),
}

export const StockMovements = {
  create: (payload) => safeRequest('post', '/stock-ledger/', payload),
}

export const UnitConversions = {
  list: (params = {}) => api.get('/unit-conversions/', { params }),
  create: (payload) => safeRequest('post', '/unit-conversions/', payload),
  update: (id, payload) => safeRequest('patch', `/unit-conversions/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/unit-conversions/${id}/`),
}

export const Items = {
  list: (params = {}) => api.get('/items/', { params }),
  create: (payload) => safeRequest('post', '/items/', payload),
  update: (id, payload) => safeRequest('patch', `/items/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/items/${id}/`),
}

export const ItemInventories = {
  list: (params = {}) => api.get('/item-inventories/', { params }),
}

export const MaterialCatalog = {
  list: (params = {}) => api.get('/material-catalog/', { params }),
}

export const HarvestProductCatalog = {
  list: (params = {}) => api.get('/harvest-product-catalog/', { params }),
}

export const CropProducts = {
  list: (params = {}) => api.get('/crop-products/', { params }),
  create: (payload) => safeRequest('post', '/crop-products/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-products/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/crop-products/${id}/`),
}

export const CropCards = {
  list: (params = {}) => api.get('/crop-cards/', { params }),
}

export const CropVarieties = {
  list: (params = {}) => api.get('/crop-varieties/', { params }),
  create: (payload) => api.post('/crop-varieties/', payload),
}

export const TreeLossReasons = {
  list: () => api.get('/tree-loss-reasons/'),
}

export const TreeProductivityStatuses = {
  list: () => api.get('/tree-productivity-statuses/'),
}

export const TreeInventory = {
  summary: (params = {}) => api.get('/tree-inventory/summary/', { params }),
  locationSummary: (params = {}, config = {}) =>
    api.get('/tree-inventory/summary/location-summary/', { params, ...config }),
  events: (params = {}) => api.get('/tree-inventory/events/', { params }),
  summaryExport: (params = {}) =>
    api.get('/tree-inventory/summary/export/', { params, responseType: 'blob' }),
  eventsExport: (params = {}) =>
    api.get('/tree-inventory/events/export/', { params, responseType: 'blob' }),
}

export const TreeInventoryAdmin = {
  adjust: (payload, idempotencyKey) =>
    api.post('/tree-inventory/admin/adjust/', payload, {
      headers: idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : {},
    }),
}

export const ResourceAnalytics = {
  list: (params = {}) => api.get('/resource-analytics/', { params }),
}

export const ExportJobs = {
  templates: (params = {}) => api.get('/export-templates/', { params }),
  list: (params = {}) => api.get('/export-jobs/', { params }),
  create: (payload) => api.post('/export-jobs/', payload),
  status: (id) => api.get(`/export-jobs/${id}/`),
  download: (id) => api.get(`/export-jobs/${id}/download/`, { responseType: 'blob' }),
}

export const ImportJobs = {
  templates: (params = {}) => api.get('/import-templates/', { params }),
  list: (params = {}) => api.get('/import-jobs/', { params }),
  downloadTemplate: (templateCode, params = {}) =>
    api.get(`/import-templates/${templateCode}/download/`, { params, responseType: 'blob' }),
  upload: (payload) => {
    const form = new FormData()
    form.append('template_code', payload.template_code)
    form.append('farm_id', payload.farm_id)
    if (payload.crop_plan_id) {
      form.append('crop_plan_id', payload.crop_plan_id)
    }
    form.append('file', payload.file)
    return api.post('/import-jobs/upload/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  validate: (id) => api.post(`/import-jobs/${id}/validate/`, {}),
  preview: (id) => api.get(`/import-jobs/${id}/preview/`),
  apply: (id) => api.post(`/import-jobs/${id}/apply/`, {}),
  downloadErrors: (id) =>
    api.get(`/import-jobs/${id}/errors/download/`, { responseType: 'blob' }),
}

export const Memberships = {
  list: (params = {}) => api.get('/memberships/', { params }),
  roles: () => api.get('/memberships/roles/'),
  create: (payload) => safeRequest('post', '/memberships/', payload),
  update: (id, payload) => safeRequest('patch', `/memberships/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/memberships/${id}/`),
  available: (params = {}) => api.get('/memberships/available-users/', { params }),
}

export const Attachments = {
  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return safeRequest('post', '/attachments/', fd)
  },
}

const normaliseActivityPayload = (payload = {}) => {
  if (!payload || typeof payload !== 'object') {
    return {}
  }

  const formattedPayload = sanitizeDailyLogActivityPayload(payload)

  // [AGRI-GUARDIAN] Fix: Prevent Number('') === 0 coercion for FKs
  const coerceId = (val) => {
    if (val === null || val === undefined || val === '') return null
    const num = Number(val)
    return Number.isFinite(num) && num !== 0 ? num : null
  }

  if (formattedPayload.log_id == null && formattedPayload.log != null) {
    formattedPayload.log_id = coerceId(formattedPayload.log)
    delete formattedPayload.log
  }

  if (formattedPayload.log_id != null) {
    formattedPayload.log_id = coerceId(formattedPayload.log_id)
  }

  if (formattedPayload.location_id == null && formattedPayload.location != null) {
    formattedPayload.location_id = coerceId(formattedPayload.location)
    delete formattedPayload.location
  }

  if (formattedPayload.asset_id == null && formattedPayload.asset != null) {
    formattedPayload.asset_id = coerceId(formattedPayload.asset)
    delete formattedPayload.asset
  }

  if (formattedPayload.well_asset_id == null && formattedPayload.well_asset != null) {
    formattedPayload.well_asset_id = coerceId(formattedPayload.well_asset)
    delete formattedPayload.well_asset
  }

  if (formattedPayload.crop_id == null && formattedPayload.crop != null) {
    formattedPayload.crop_id = coerceId(formattedPayload.crop)
    delete formattedPayload.crop
  }

  if (formattedPayload.task_id == null && formattedPayload.task != null) {
    formattedPayload.task_id = coerceId(formattedPayload.task)
    delete formattedPayload.task
  }

  if (formattedPayload.variety_id == null && formattedPayload.variety != null) {
    formattedPayload.variety_id = coerceId(formattedPayload.variety)
    delete formattedPayload.variety
  }

  if (formattedPayload.product_id == null && formattedPayload.product != null) {
    formattedPayload.product_id = coerceId(formattedPayload.product)
    delete formattedPayload.product
  }

  if (formattedPayload.tree_loss_reason_id == null && formattedPayload.tree_loss_reason != null) {
    formattedPayload.tree_loss_reason_id = coerceId(formattedPayload.tree_loss_reason)
    delete formattedPayload.tree_loss_reason
  }

  if (formattedPayload.crop_plan_id == null && formattedPayload.crop_plan != null) {
    formattedPayload.crop_plan_id = coerceId(formattedPayload.crop_plan)
    delete formattedPayload.crop_plan
  }

  const numericFields = [
    'log_id',
    'location_id',
    'asset_id',
    'well_asset_id',
    'crop_id',
    'task_id',
    'variety_id',
    'tree_loss_reason_id',
    'product_id', // Added product_id
    'crop_plan_id',
  ]
  numericFields.forEach((field) => {
    if (Object.prototype.hasOwnProperty.call(formattedPayload, field)) {
      const coerced = coerceId(formattedPayload[field])
      if (coerced === null) {
        delete formattedPayload[field]
      } else {
        formattedPayload[field] = coerced
      }
    }
  })

  // Decimals can be 0, so separate logic, supporting Arabic numerals
  const coerceDecimal = (val) => {
    if (val === null || val === undefined || val === '') return null
    if (typeof val === 'number') return Number.isFinite(val) ? val : null
    const englishStr = String(val).replace(/[٠-٩]/g, (d) => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
    const num = Number(englishStr)
    return Number.isFinite(num) ? num : null
  }

  const decimalFields = [
    'hours',
    'well_reading',
    'machine_hours',
    'machine_meter_reading',
    'fuel_consumed',
    'material_qty',
    'planted_area',
    'activity_tree_count',
    'tree_count_delta',
    'harvested_qty',
    'harvest_quantity',
    'water_volume',
    'fertilizer_quantity',
  ]
  decimalFields.forEach((field) => {
    if (Object.prototype.hasOwnProperty.call(formattedPayload, field)) {
      formattedPayload[field] = coerceDecimal(formattedPayload[field])
    }
  })

  // [AGRI-GUARDIAN FIX] Strict Payload Mapping
  // 1. Map 'team' (Array) to 'employees' (List[int])
  if (Array.isArray(formattedPayload.team)) {
    formattedPayload.employees = formattedPayload.team
    // Backend expects team as legacy text, not list. Keep employees only.
    delete formattedPayload.team
  }

  // 2. Ensure ID fields are mapped (task -> task_id)
  const idFields = ['task', 'asset', 'location', 'crop', 'variety', 'product', 'well_asset']
  idFields.forEach((field) => {
    if (formattedPayload[field] && !formattedPayload[`${field}_id`]) {
      formattedPayload[`${field}_id`] = formattedPayload[field]
    }
  })

  // 3. Ensure Surrah Count is numeric
  if (formattedPayload.surrah_count) {
    formattedPayload.surrah_count = Number(formattedPayload.surrah_count)
  }

  return formattedPayload
}
export const DailyLogs = {
  // [DOCUMENT CYCLE] CRUD + Workflow Actions
  list: (params = {}) => api.get('/daily-logs/', { params }),
  get: (id) => api.get(`/daily-logs/${id}/`),
  create: (payload) => safeRequest('post', '/daily-logs/', payload),
  replayAtomic: (payload) =>
    safeRequest('post', '/offline/daily-log-replay/atomic/', payload, {
      headers: { 'X-Idempotency-Key': payload?.idempotency_key || makeUUID() },
    }),
  addActivity: (payload) => {
    const formattedPayload = normaliseActivityPayload(payload)
    return safeRequest('post', '/activities/', formattedPayload)
  },
  updateActivity: (id, payload) => {
    if (!id) {
      return Promise.reject(new Error('Missing activity id'))
    }
    const formattedPayload = normaliseActivityPayload(payload)
    return safeRequest('patch', `/activities/${id}/`, formattedPayload)
  },
  deleteActivity: (id) => {
    if (!id) {
      return Promise.reject(new Error('Missing activity id'))
    }
    return safeRequest('delete', `/activities/${id}/`)
  },
  daySummary: (params = {}) => api.get('/daily-logs/day-summary/', { params }),
  // [DOCUMENT CYCLE] Status Workflow Actions
  submit: (id) => safeRequest('post', `/daily-logs/${id}/submit/`),
  approve: (id) => safeRequest('post', `/daily-logs/${id}/approve/`),
  reject: (id, reason) => safeRequest('post', `/daily-logs/${id}/reject/`, { reason }),
  warningNote: (id, note) => safeRequest('post', `/daily-logs/${id}/warning-note/`, { note }),
  approveVariance: (id, note) =>
    safeRequest('post', `/daily-logs/${id}/approve-variance/`, { note }),
  reopen: (id) => safeRequest('post', `/daily-logs/${id}/reopen/`),
}

export const CustodyTransfers = {
  list: (params = {}) => api.get('/inventory/custody-transfers/', { params }),
  issue: async (payload) => {
    const idempotencyKey = makeUUID()
    if (navigator.onLine) {
      return safeRequest('post', '/inventory/custody-transfers/issue/', payload, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      })
    }
    return CustodyTransfers.enqueueOfflineAction({
      actionName: 'issue',
      body: payload,
      farmId: payload?.farm_id || payload?.farm || null,
      supervisorId: payload?.supervisor_id || payload?.supervisor || null,
      idempotencyKey,
    })
  },
  accept: async (id, payload = {}) => {
    const idempotencyKey = makeUUID()
    if (navigator.onLine) {
      return safeRequest('post', `/inventory/custody-transfers/${id}/accept/`, payload, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      })
    }
    return CustodyTransfers.enqueueOfflineAction({
      transferId: id,
      actionName: 'accept',
      body: payload,
      farmId: payload?.farm_id || payload?.farm || null,
      supervisorId: payload?.supervisor_id || payload?.supervisor || null,
      idempotencyKey,
    })
  },
  reject: async (id, payload = {}) => {
    const idempotencyKey = makeUUID()
    if (navigator.onLine) {
      return safeRequest('post', `/inventory/custody-transfers/${id}/reject/`, payload, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      })
    }
    return CustodyTransfers.enqueueOfflineAction({
      transferId: id,
      actionName: 'reject',
      body: payload,
      farmId: payload?.farm_id || payload?.farm || null,
      supervisorId: payload?.supervisor_id || payload?.supervisor || null,
      idempotencyKey,
    })
  },
  returnTransfer: async (id, payload = {}) => {
    const idempotencyKey = makeUUID()
    if (navigator.onLine) {
      return safeRequest('post', `/inventory/custody-transfers/${id}/return/`, payload, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      })
    }
    return CustodyTransfers.enqueueOfflineAction({
      transferId: id,
      actionName: 'return',
      body: payload,
      farmId: payload?.farm_id || payload?.farm || null,
      supervisorId: payload?.supervisor_id || payload?.supervisor || null,
      idempotencyKey,
    })
  },
  balance: (params = {}) => api.get('/inventory/custody-balance/', { params }),
  enqueueOfflineAction: async ({ transferId, actionName, body = {}, farmId = null, supervisorId = null, idempotencyKey = null }) => {
    const ownerKey = await getQueueOwnerKey()
    const envelope = await buildOfflineEnvelope({
      category: 'custody',
      ownerKey,
      farmId,
      extra: {
        supervisor_id: supervisorId,
      },
      idempotencyKey,
    })
    await db.custody_queue.add({
      ...envelope,
      transfer_id: transferId,
      action_name: actionName,
      payload: { transfer_id: transferId, action_name: actionName, body },
      farm_id: farmId,
      owner_key: ownerKey,
      supervisor_id: supervisorId,
    })
    notifyQueueChange()
    return { queued: true }
  },
}

export const Activities = {
  list: (params = {}) => api.get('/activities/', { params }),
  teamSuggestions: (params = {}) => api.get('/activities/team-suggestions/', { params }),
  defaults: (params = {}) => api.get('/activities/defaults/', { params }),
}

export const Audit = { list: (params = {}) => api.get('/audit-logs/', { params }) }

export const SalesInvoices = {
  list: (params = {}) => api.get('/sales-invoices/', { params }),
  create: (data) => api.post('/sales-invoices/', data),
  update: (id, data) => api.patch(`/sales-invoices/${id}/`, data),
  delete: (id) => api.delete(`/sales-invoices/${id}/`),
  approve: (id) => api.post(`/sales-invoices/${id}/approve/`),
}

export const Employees = {
  list: async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []

    const filteredParams =
      !params.farm_id && userFarmIds.length > 0
        ? { ...params, farm_id: userFarmIds.join(',') }
        : params

    return api.get('/employees/', { params: filteredParams })
  },
}

export const Timesheets = {
  list: (params = {}) => api.get('/core/timesheets/', { params }),
  retrieve: (id) => api.get(`/core/timesheets/${id}/`),
  create: (data) => api.post('/core/timesheets/', data),
  update: (id, data) => api.patch(`/core/timesheets/${id}/`, data),
  delete: (id) => api.delete(`/core/timesheets/${id}/`),
  monthlySummary: (params = {}) => api.get('/core/timesheets/monthly-summary/', { params }),
}

export const EmployeeAdvances = {
  list: (params = {}) => api.get('/core/employee-advances/', { params }),
  retrieve: (id) => api.get(`/core/employee-advances/${id}/`),
  create: (data) => api.post('/core/employee-advances/', data),
  update: (id, data) => api.patch(`/core/employee-advances/${id}/`, data),
  delete: (id) => api.delete(`/core/employee-advances/${id}/`),
  approve: (id) => api.post(`/core/employee-advances/${id}/approve/`),
}

export const LaborEstimates = {
  preview: (payload) => api.post('/labor-estimates/preview/', payload),
}

export const Auth = createAuthClient({
  api,
  authApi,
  getAccessTokenValue,
  getRefreshTokenValue,
  setAccessTokenValue,
  setRefreshTokenValue,
  clearAccessTokenValue,
  clearRefreshTokenValue,
})

export const Supervisors = {
  list: (params = {}) => api.get('/supervisors/', { params }),
  create: (payload) => safeRequest('post', '/supervisors/', payload),
  update: (id, payload) => safeRequest('patch', `/supervisors/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/supervisors/${id}/`),
}

const { Reports, AsyncReports } = createReportingClients({ api })

export { Reports, AsyncReports }

export const LocationWells = {
  list: (params = {}) => api.get('/location-wells/', { params }),
  create: (payload) => safeRequest('post', '/location-wells/', payload),
  retrieve: (id) => api.get(`/location-wells/${id}/`),
  update: (id, payload) => safeRequest('patch', `/location-wells/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/location-wells/${id}/`),
  summary: (params = {}) => api.get('/location-wells/summary/', { params }),
}

export async function clearOfflineQueue(type) {
  await migrateLegacyOfflineEntries()
  const ownerKey = await getQueueOwnerKey()
  if (type === 'daily-log') {
    await clearDailyLogQueue('pending', ownerKey)
  } else if (type === 'harvest') {
    await clearHarvestQueue('pending', ownerKey)
  } else if (type === 'custody') {
    await clearCustodyQueue('pending', ownerKey)
  } else if (type === 'generic') {
    await Promise.all([clearGenericQueue('pending', ownerKey), clearQueueSales('pending', ownerKey)])
  } else if (type === 'failed-daily-log') {
    await clearDailyLogQueue('failed', ownerKey)
  } else if (type === 'failed-harvest') {
    await clearHarvestQueue('failed', ownerKey)
  } else if (type === 'failed-custody') {
    await clearCustodyQueue('failed', ownerKey)
  } else if (type === 'failed-generic') {
    await Promise.all([clearGenericQueue('failed', ownerKey), clearQueueSales('failed', ownerKey)])
  } else {
    await Promise.all([
      clearGenericQueue('all', ownerKey),
      clearHarvestQueue('all', ownerKey),
      clearQueueSales('all', ownerKey),
      clearDailyLogQueue('all', ownerKey),
      clearCustodyQueue('all', ownerKey),
    ])
  }
  notifyQueueChange()
  return true
}


export async function removeOfflineQueueItem(type, id) {
  if (!id) {
    return false
  }
  await migrateLegacyOfflineEntries()
  const ownerKey = await getQueueOwnerKey()
  let removed = false
  if (type === 'daily-log' || type === 'failed-daily-log') {
    removed = await removeDailyLogQueueItem(id, ownerKey)
  } else if (type === 'harvest' || type === 'failed-harvest') {
    removed = await removeHarvestQueueItem(id, ownerKey)
  } else if (type === 'custody' || type === 'failed-custody') {
    removed = await removeCustodyQueueItem(id, ownerKey)
  } else if (type === 'generic') {
    removed = (await removeGenericQueueItem(id, ownerKey)) || (await removeQueueSaleItem(id, ownerKey))
  } else if (type === 'failed-generic') {
    removed = (await removeGenericQueueItem(id, ownerKey)) || (await removeQueueSaleItem(id, ownerKey))
  } else {
    return false
  }

  if (removed) {
    notifyQueueChange()
  }
  return removed
}


export async function requeueFailedItems(type) {
  await migrateLegacyOfflineEntries()
  const ownerKey = await getQueueOwnerKey()
  let count = 0
  if (type === 'daily-log') {
    count += await requeueDailyLogFailures(ownerKey)
  } else if (type === 'harvest') {
    count += await requeueHarvestFailures(ownerKey)
  } else if (type === 'custody') {
    count += await requeueCustodyFailures(ownerKey)
  } else {
    count += await requeueGenericFailures(ownerKey)
    count += await requeueQueueSales(ownerKey)
  }

  if (count > 0) {
    notifyQueueChange()
  }
  return count
}


export const ServiceProviders = {
  list: (params = {}) => api.get('/service-providers/', { params }),
  create: (payload) => safeRequest('post', '/service-providers/', payload),
  update: (id, payload) => safeRequest('patch', `/service-providers/${id}/`, payload),
  delete: (id) => safeRequest('delete', `/service-providers/${id}/`),
}

export const ServiceCards = {
  list: (params = {}) => api.get('/service-cards/', { params }),
}

export const MaterialCards = {
  list: (params = {}) => api.get('/material-cards/', { params }),
}

export const CropMaterials = {
  list: (params = {}) => api.get('/crop-materials/', { params }),
  create: (payload) => safeRequest('post', '/crop-materials/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-materials/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/crop-materials/${id}/`),
}

export const CropTemplates = {
  list: (params = {}) => api.get('/crop-templates/', { params }),
  create: (payload) => safeRequest('post', '/crop-templates/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-templates/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/crop-templates/${id}/`),
  retrieve: (id, params = {}) => api.get(`/crop-templates/${id}/`, { params }),
}

export const CropTemplateMaterials = {
  create: (payload) => safeRequest('post', '/crop-template-materials/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-template-materials/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/crop-template-materials/${id}/`),
}

export const CropTemplateTasks = {
  create: (payload) => safeRequest('post', '/crop-template-tasks/', payload),
  update: (id, payload) => safeRequest('patch', `/crop-template-tasks/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/crop-template-tasks/${id}/`),
}

export const CropPlans = {
  list: (params = {}) => api.get('/crop-plans/', { params }),
  create: (payload) =>
    safeRequest('post', '/crop-plans/', payload, { headers: { 'X-Idempotency-Key': makeUUID() } }),
  retrieve: (id) => api.get(`/crop-plans/${id}/`),
  approve: (id) =>
    safeRequest('post', `/crop-plans/${id}/approve/`, null, {
      headers: { 'X-Idempotency-Key': makeUUID() },
    }),
  variance: (id) => api.get(`/crop-plans/${id}/variance/`),
  financialSummary: (id) => api.get(`/crop-plans/${id}/financial_summary/`),
  importBudget: (id, payload) =>
    safeRequest('post', `/crop-plans/${id}/import_budget/`, payload, {
      headers: { 'X-Idempotency-Key': makeUUID() },
    }),
  exportTemplate: (id) =>
    api.get(`/crop-plans/${id}/export_template/`, { responseType: 'arraybuffer' }),
  importTemplate: (id, file, replace = true) => {
    const form = new FormData()
    form.append('file', file)
    form.append('replace', replace ? 'true' : 'false')
    return safeRequest('post', `/crop-plans/${id}/import_template/`, form, {
      headers: { 'X-Idempotency-Key': makeUUID() },
    })
  },
  bulkImport: (payload) =>
    safeRequest('post', '/crop-plans/bulk-import/', payload, {
      headers: { 'X-Idempotency-Key': makeUUID() },
    }),
}

export const CropPlanBudgetLines = {
  list: (params = {}) => api.get('/crop-plan-budget-lines/', { params }),
  create: (payload) =>
    safeRequest('post', '/crop-plan-budget-lines/', payload, {
      headers: { 'X-Idempotency-Key': makeUUID() },
    }),
  update: (id, payload) =>
    safeRequest('patch', `/crop-plan-budget-lines/${id}/`, payload, {
      headers: { 'X-Idempotency-Key': makeUUID() },
    }),
  remove: (id) => safeRequest('delete', `/crop-plan-budget-lines/${id}/`),
}

export const PlanImportLogs = {
  list: (params = {}) => api.get('/plan-import-logs/', { params }),
}

export const Tasks = {
  list: (params = {}) => api.get('/tasks/', { params }),
  create: (payload) => safeRequest('post', '/tasks/', payload),
  update: (id, payload) => safeRequest('patch', `/tasks/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/tasks/${id}/`),
}

export async function getFinancialRiskZone(farmId, cropId, seasonId) {
  const { data } = await api.get('/crop-plans/financial-risk-zone/', {
    params: { farm_id: farmId, crop_id: cropId, season_id: seasonId || '' },
  })
  return data
}

export const HarvestLogs = {
  list: (params = {}) => api.get('/harvest-logs/', { params }),
  create: async (payload) => {
    const ownerKey = await getQueueOwnerKey()
    const idempotencyKey = makeUUID()
    const farmId = payload?.farm_id || payload?.farm || payload?.farmId || null
    if (navigator.onLine) {
      const envelope = await buildOfflineEnvelope({
        category: 'harvest',
        ownerKey,
        farmId,
        payloadUuid: generateOfflineId(),
        idempotencyKey,
      })
      return api.post('/offline/harvest-replay/atomic/', {
        uuid: envelope.uuid,
        payload_uuid: envelope.payload_uuid,
        idempotency_key: envelope.idempotency_key,
        farm_id: farmId,
        client_seq: envelope.client_seq,
        device_id: envelope.device_id,
        device_timestamp: envelope.created_at,
        harvest: payload,
      }, {
        headers: { 'X-Idempotency-Key': envelope.idempotency_key },
      })
    }
    const envelope = await buildOfflineEnvelope({
      category: 'harvest',
      ownerKey,
      farmId,
      payloadUuid: generateOfflineId(),
      idempotencyKey,
    })
    await queueHarvest({
      ...envelope,
      payload,
    })
    notifyQueueChange()
    return { data: { queued: true } }
  },
  retrieve: (id) => api.get(`/harvest-logs/${id}/`),
  update: (id, payload) => safeRequest('patch', `/harvest-logs/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/harvest-logs/${id}/`),
}

export const SyncRecords = {
  list: (params = {}) => api.get('/sync-records/', { params }),
}

export const SyncConflictDLQ = {
  list: (params = {}) => api.get('/sync-conflict-dlq/', { params }),
}

export const OfflineSyncQuarantines = {
  list: (params = {}) => api.get('/offline-sync-quarantines/', { params }),
}

export const HarvestLots = {
  list: (params = {}) => api.get('/harvest-lots/', { params }),
  retrieve: (id) => api.get(`/harvest-lots/${id}/`),
}

export const Customers = {
  list: (params = {}) => api.get('/customers/', { params }),
  create: (payload) => safeRequest('post', '/customers/', payload),
  update: (id, payload) => safeRequest('patch', `/customers/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/customers/${id}/`),
}

export const Seasons = {
  list: (params = {}) => api.get('/seasons/', { params }),
  create: (payload) => safeRequest('post', '/seasons/', payload),
  update: (id, payload) => safeRequest('patch', `/seasons/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/seasons/${id}/`),
}

export async function fetchDashboardStats() {
  try {
    const { data } = await api.get('/dashboard-stats/')
    // Cache the fresh data
    await writeScopedValue('dashboard-stats-cache', data)
    return data
  } catch (error) {
    if (!navigator.onLine) {
      // Try to read from cache
      const cached = await readScopedValue('dashboard-stats-cache')
      if (cached) {
        // [AG-CLEANUP] console.log('Serving dashboard stats from cache (offline)')
        return cached
      }
    }
    throw error
  }
}
export const Sales = {
  list: (params) => api.get('/sales-invoices/', { params }),
  get: (id) => api.get(`/sales-invoices/${id}/`),
  create: (data) => api.post('/sales-invoices/', data),
  update: (id, data) => api.put(`/sales-invoices/${id}/`, data),
  delete: (id) => api.delete(`/sales-invoices/${id}/`),
  // Strictly typed invoice generation
  generateInvoice: (id) => api.get(`/sales-invoices/${id}/invoice/`, { responseType: 'blob' }),
}

export const Suggestions = {
  list: (params = {}) => api.get('/suggestions/', { params }),
}

export const BiologicalAssetCohorts = {
  list: (params = {}) => api.get('/biological-asset-cohorts/', { params }),
  retrieve: (id) => api.get(`/biological-asset-cohorts/${id}/`),
  create: (payload) => safeRequest('post', '/biological-asset-cohorts/', payload),
  update: (id, payload) => safeRequest('patch', `/biological-asset-cohorts/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/biological-asset-cohorts/${id}/`),
  transition: (id, payload, idempotencyKey) =>
    api.post(`/biological-asset-cohorts/${id}/transition/`, payload, {
      headers: idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : {},
    }),
  bulkTransition: (payload, idempotencyKey) =>
    api.post('/biological-asset-cohorts/bulk_transition/', payload, {
      headers: idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : {},
    }),
  aggregateByLocation: (params = {}) =>
    api.get('/biological-asset-cohorts/aggregate_by_location/', { params }),
}

export const TreeInventorySummary = {
  list: (params = {}) => api.get('/tree-inventory/summary/', { params }),
  locationSummary: (params = {}) => api.get('/tree-inventory/summary/location-summary/', { params }),
  locationVarietySummary: (params = {}) =>
    api.get('/tree-inventory/summary/location-variety-summary/', { params }),
}

export const BiologicalAssetTransactions = {
  list: (params = {}) => api.get('/biological-asset-transactions/', { params }),
  retrieve: (id) => api.get(`/biological-asset-transactions/${id}/`),
}

export const TreeCensusVarianceAlerts = {
  list: (params = {}) => api.get('/tree-census-variance-alerts/', { params }),
  retrieve: (id) => api.get(`/tree-census-variance-alerts/${id}/`),
  resolve: (id, payload, idempotencyKey) =>
    api.post(`/tree-census-variance-alerts/${id}/resolve/`, payload, {
      headers: idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : {},
    }),
}

export const SharecroppingContracts = {
  list: (params = {}) => api.get('/sharecropping-contracts/', { params }),
  dashboard: (params = {}) => api.get('/sharecropping-contracts/dashboard/', { params }),
  create: (payload) => safeRequest('post', '/sharecropping-contracts/', payload),
  update: (id, payload) => safeRequest('patch', `/sharecropping-contracts/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/sharecropping-contracts/${id}/`),
  registerTouring: (id, payload) =>
    safeRequest('post', `/sharecropping-contracts/${id}/register_touring/`, payload),
  processHarvest: (id, payload) =>
    safeRequest('post', `/sharecropping-contracts/${id}/process_harvest/`, payload),
  recordRentPayment: (id, payload) =>
    safeRequest('post', `/sharecropping-contracts/${id}/record-rent-payment/`, payload),
}

export const PurchaseOrders = {
  list: (params = {}) => api.get('/purchase-orders/', { params }),
  retrieve: (id) => api.get(`/purchase-orders/${id}/`),
  create: (payload) => safeRequest('post', '/purchase-orders/', payload),
  update: (id, payload) => safeRequest('patch', `/purchase-orders/${id}/`, payload),
  remove: (id) => safeRequest('delete', `/purchase-orders/${id}/`),
  submit: (id) => safeRequest('post', `/purchase-orders/${id}/submit/`),
  approve: (id, role) => safeRequest('post', `/purchase-orders/${id}/approve/`, { role }),
}

export const SupplierSettlements = {
  list: (params = {}) => api.get('/finance/supplier-settlements/', { params }),
  create: (payload) => safeRequest('post', '/finance/supplier-settlements/', payload),
  submitReview: (id) =>
    safeRequest('post', `/finance/supplier-settlements/${id}/submit_review/`, {}),
  approve: (id) => safeRequest('post', `/finance/supplier-settlements/${id}/approve/`, {}),
  reject: (id, reason) =>
    safeRequest('post', `/finance/supplier-settlements/${id}/reject/`, { reason }),
  reopen: (id) => safeRequest('post', `/finance/supplier-settlements/${id}/reopen/`, {}),
  recordPayment: (id, payload) =>
    safeRequest('post', `/finance/supplier-settlements/${id}/record_payment/`, payload),
}

// [V21 GOVERNANCE CLIENTS]
export const RoleDelegations = {
  list: (params = {}) => api.get('/governance/role-delegations/', { params }),
  create: (payload) => safeRequest('post', '/governance/role-delegations/', payload),
  remove: (id) => safeRequest('delete', `/governance/role-delegations/${id}/`),
}

export const FarmGovernanceProfiles = {
  list: (params = {}) => api.get('/governance/farm-profiles/', { params }),
  retrieve: (id) => api.get(`/governance/farm-profiles/${id}/`),
}

export const RaciTemplates = {
  list: (params = {}) => api.get('/governance/raci-templates/', { params }),
}

export const PermissionTemplates = {
  list: (params = {}) => api.get('/governance/permission-templates/', { params }),
}

// Duplicate Assets export removed

export default api
