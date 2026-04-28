import Dexie from 'dexie'
import { buildDailyLogIdempotencyRotationPatch } from '../utils/offlineDailyLogIdentity'

export const db = new Dexie('AgriOfflineDB')

db.version(2).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, farm_id, dead_letter',
  harvest_queue: '++id, status, created_at, farm_id',
  userData: 'key',
})

db.version(3).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, farm_id, dead_letter',
  harvest_queue: '++id, status, created_at, farm_id',
  daily_log_queue: '++id, uuid, status, farm_id, created_at',
  userData: 'key',
})

db.version(4).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, farm_id, dead_letter',
  harvest_queue: '++id, status, created_at, farm_id',
  daily_log_queue: '++id, uuid, status, dead_letter, farm_id, created_at',
  userData: 'key',
  lookup_cache: 'key',
})

db.version(5).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, farm_id, dead_letter',
  harvest_queue: '++id, status, created_at, farm_id',
  daily_log_queue: '++id, uuid, status, dead_letter, farm_id, created_at, next_attempt_at',
  custody_queue: '++id, uuid, status, dead_letter, farm_id, supervisor_id, created_at, next_attempt_at',
  userData: 'key',
  lookup_cache: 'key',
})

db.version(6).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  generic_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  harvest_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  daily_log_queue: '++id, uuid, status, dead_letter, farm_id, created_at, next_attempt_at',
  custody_queue: '++id, uuid, status, dead_letter, farm_id, supervisor_id, created_at, next_attempt_at',
  userData: 'key',
  lookup_cache: 'key',
})

db.version(7).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  generic_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  harvest_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  daily_log_queue:
    '++id, uuid, status, dead_letter, farm_id, draft_uuid, created_at, next_attempt_at',
  daily_log_drafts:
    'draft_uuid, farm_id, supervisor_id, log_date, status, updated_at, [farm_id+log_date], [farm_id+supervisor_id+log_date]',
  custody_queue:
    '++id, uuid, status, dead_letter, farm_id, supervisor_id, created_at, next_attempt_at',
  userData: 'key',
  lookup_cache: 'key',
})

db.version(9).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  generic_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  harvest_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  daily_log_queue:
    '++id, uuid, status, dead_letter, farm_id, draft_uuid, created_at, next_attempt_at',
  daily_log_drafts:
    'draft_uuid, farm_id, supervisor_id, log_date, status, updated_at, [farm_id+log_date], [farm_id+supervisor_id+log_date]',
  custody_queue:
    '++id, uuid, status, dead_letter, farm_id, supervisor_id, created_at, next_attempt_at',
  attachments_queue:
    '++id, uuid, attachment_class, status, dead_letter, farm_id, created_at, next_attempt_at',
  purge_logs: '++id, table_name, count, timestamp',
  userData: 'key',
  lookup_cache: 'key, cached_at',
})

db.version(10).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  crop_materials: 'id, crop_id, item_id, farm_id, [farm_id+crop_id]',
  locations: 'id, name, farm_id',
  sales_queue: '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  generic_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  harvest_queue:
    '++id, uuid, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  daily_log_queue:
    '++id, uuid, status, dead_letter, farm_id, draft_uuid, created_at, next_attempt_at',
  daily_log_drafts:
    'draft_uuid, farm_id, supervisor_id, log_date, status, updated_at, [farm_id+log_date], [farm_id+supervisor_id+log_date]',
  custody_queue:
    '++id, uuid, status, dead_letter, farm_id, supervisor_id, created_at, next_attempt_at',
  attachments_queue:
    '++id, uuid, attachment_class, status, dead_letter, farm_id, created_at, next_attempt_at',
  userData: 'key',
  lookup_cache: 'key, cached_at',
})

db.version(2022).stores({
  customers: 'id, name, phone, farm_id',
  items: 'id, name, category, farm_id',
  crop_materials: 'id, crop_id, item_id, farm_id, [farm_id+crop_id]',
  locations: 'id, name, farm_id',
  sales_queue:
    '++id, queue_id, uuid, payload_uuid, category, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  generic_queue:
    '++id, queue_id, uuid, payload_uuid, category, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  harvest_queue:
    '++id, queue_id, uuid, payload_uuid, category, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  daily_log_queue:
    '++id, queue_id, uuid, payload_uuid, category, status, dead_letter, farm_id, owner_key, draft_uuid, created_at, next_attempt_at',
  daily_log_drafts:
    'draft_uuid, farm_id, supervisor_id, log_date, status, updated_at, [farm_id+log_date], [farm_id+supervisor_id+log_date]',
  custody_queue:
    '++id, queue_id, uuid, payload_uuid, category, status, dead_letter, farm_id, owner_key, supervisor_id, created_at, next_attempt_at',
  attachments_queue:
    '++id, queue_id, uuid, payload_uuid, category, attachment_class, status, dead_letter, farm_id, owner_key, created_at, next_attempt_at',
  audit_logs: 'id, timestamp, agent, action, public_key',
  userData: 'key',
  lookup_cache: 'key, cached_at',
})


db.version(2).upgrade((tx) =>
  tx.sales_queue.toCollection().modify((record) => {
    if (record.retry_count === undefined) record.retry_count = 0
    if (record.dead_letter === undefined) record.dead_letter = false
    if (!record.updated_at) record.updated_at = new Date().toISOString()
  }),
)

const nowIso = () => new Date().toISOString()
const PENDING_QUEUE_STATUSES = new Set(['pending', 'syncing', 'failed_retryable'])
const FAILED_QUEUE_STATUSES = new Set(['dead_letter', 'quarantined'])
const normalizeQueueStatus = (status, deadLetter = false) => {
  if (deadLetter) return 'dead_letter'
  if (status === 'failed') return 'failed_retryable'
  if (status === 'complete' || status === 'completed') return 'synced'
  if (status === 'quarantined') return 'quarantined'
  if (status === 'dead_letter') return 'dead_letter'
  if (status === 'syncing') return 'syncing'
  if (status === 'synced') return 'synced'
  return 'pending'
}

const ensureQueueRecord = (record, defaults = {}) => {
  const now = nowIso()
  const normalizedStatus = normalizeQueueStatus(
    record?.status || defaults.status || 'pending',
    Boolean(record?.dead_letter),
  )
  return {
    ...record,
    queue_id: record?.queue_id || record?.queueId || record?.id || record?.uuid || null,
    uuid: record?.uuid || record?.idempotency_key || (typeof globalThis.crypto?.randomUUID === 'function' ? globalThis.crypto.randomUUID() : null),
    payload_uuid:
      record?.payload_uuid ||
      record?.payloadUuid ||
      record?.uuid ||
      record?.idempotency_key ||
      null,
    category: record?.category || defaults.category || 'generic',
    owner_key: record?.owner_key || record?.ownerKey || defaults.owner_key || null,
    status: normalizedStatus,
    dead_letter: normalizedStatus === 'dead_letter' || Boolean(record?.dead_letter),
    retry_count: Number(record?.retry_count || defaults.retry_count || 0),
    created_at: record?.created_at || record?.queuedAt || defaults.created_at || now,
    updated_at: record?.updated_at || defaults.updated_at || now,
    next_attempt_at:
      record?.next_attempt_at ||
      record?.nextAttemptAt ||
      defaults.next_attempt_at ||
      defaults.nextAttemptAt ||
      null,
    last_error: record?.last_error || record?.lastError || defaults.last_error || null,
    dead_letter_reason:
      record?.dead_letter_reason || record?.deadLetterReason || defaults.dead_letter_reason || null,
  }
}

const getQueueCounts = async (tableName, ownerKey = null) => {
  try {
    const all = await db[tableName].toArray()
    const scoped = ownerKey ? all.filter((item) => item.owner_key === ownerKey) : all
    return {
      pending: scoped.filter((item) => PENDING_QUEUE_STATUSES.has(item.status)).length,
      failed: scoped.filter((item) => FAILED_QUEUE_STATUSES.has(item.status) || item.dead_letter).length,
    }
  } catch (err) {
    console.error(`[Dexie] Failed to get ${tableName} counts`, err)
    return { pending: 0, failed: 0 }
  }
}

const getQueueDetails = async (tableName, ownerKey = null) => {
  try {
    const all = await db[tableName].toArray()
    const scoped = ownerKey ? all.filter((item) => item.owner_key === ownerKey) : all
    return {
      pending: scoped.filter((item) => PENDING_QUEUE_STATUSES.has(item.status)),
      failed: scoped.filter((item) => FAILED_QUEUE_STATUSES.has(item.status) || item.dead_letter),
    }
  } catch (err) {
    console.error(`[Dexie] Failed to get ${tableName} details`, err)
    return { pending: [], failed: [] }
  }
}

const clearQueue = async (tableName, type = 'all', ownerKey = null) => {
  try {
    if (type === 'pending') {
      const pending = await db[tableName]
        .filter(
          (item) =>
            (!ownerKey || item.owner_key === ownerKey) &&
            PENDING_QUEUE_STATUSES.has(item.status),
        )
        .toArray()
      await db[tableName].bulkDelete(pending.map((item) => item.id))
    } else if (type === 'failed') {
      const failed = await db[tableName]
        .filter(
          (item) =>
            (!ownerKey || item.owner_key === ownerKey) &&
            (FAILED_QUEUE_STATUSES.has(item.status) || item.dead_letter),
        )
        .toArray()
      await db[tableName].bulkDelete(failed.map((item) => item.id))
    } else if (ownerKey) {
      const scoped = await db[tableName].filter((item) => item.owner_key === ownerKey).toArray()
      await db[tableName].bulkDelete(scoped.map((item) => item.id))
    } else {
      await db[tableName].clear()
    }
    return true
  } catch (err) {
    console.error(`[Dexie] Failed to clear ${tableName}`, err)
    return false
  }
}

const removeQueueItem = async (tableName, id, ownerKey = null) => {
  try {
    const existing = await db[tableName].get(id)
    if (!existing) {
      return false
    }
    if (ownerKey && existing.owner_key !== ownerKey) {
      return false
    }
    const deletedCount = await db[tableName].where('id').equals(id).delete()
    return deletedCount > 0
  } catch (err) {
    console.error(`[Dexie] Failed to remove ${tableName} item`, err, { id })
    return false
  }
}

const requeueFailures = async (tableName, ownerKey = null) => {
  try {
    const failed = await db[tableName]
      .filter(
        (item) =>
          (!ownerKey || item.owner_key === ownerKey) &&
          (FAILED_QUEUE_STATUSES.has(item.status) || item.dead_letter),
      )
      .toArray()
    if (!failed.length) {
      return 0
    }
    await Promise.all(
      failed.map((item) => {
        const newUid = (typeof globalThis.crypto?.randomUUID === 'function')
          ? globalThis.crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`
        if (tableName === 'daily_log_queue') {
          return db[tableName].update(
            item.id,
            buildDailyLogIdempotencyRotationPatch(item, {
              newKey: newUid,
              nowIsoValue: nowIso(),
            }),
          )
        }
        return db[tableName].update(item.id, {
          status: 'pending',
          dead_letter: false,
          uuid: newUid,
          idempotency_key: newUid,
          retry_count: 0,
          next_attempt_at: null,
          last_error: null,
          dead_letter_reason: null,
          updated_at: nowIso(),
        });
      }),
    )
    return failed.length
  } catch (err) {
    console.error(`[Dexie] Failed to requeue ${tableName} failures`, err)
    return 0
  }
}

export async function updateCatalog(table, data) {
  await db[table].bulkPut(data)
}

export async function queueSale(saleData) {
  const record = ensureQueueRecord(
    {
      ...saleData,
      owner_key: saleData?.owner_key || saleData?.ownerKey || null,
      uuid: saleData?.uuid || saleData?.idempotency_key || saleData?.idempotencyKey || null,
    },
    { status: 'pending' },
  )
  return db.sales_queue.add(record)
}

export async function getPendingSales(ownerKey = null) {
  const pending = await db.sales_queue
    .filter((item) => PENDING_QUEUE_STATUSES.has(item.status) && !item.dead_letter)
    .toArray()
  return ownerKey ? pending.filter((item) => item.owner_key === ownerKey) : pending
}

export async function markSaleRetry(saleId, errorMessage) {
  const record = await db.sales_queue.get(saleId)
  if (!record) return
  const now = nowIso()
  return db.sales_queue.update(saleId, {
    retry_count: (record.retry_count || 0) + 1,
    last_error: errorMessage,
    updated_at: now,
  })
}

export async function moveSaleToDeadLetter(record, reason) {
  return db.sales_queue.update(record.id, {
    status: 'dead_letter',
    dead_letter: true,
    failed_reason: reason,
    last_error: reason,
    updated_at: nowIso(),
  })
}

export async function queueGenericRequest(entry) {
  const record = ensureQueueRecord(
    {
      ...entry,
      owner_key: entry?.owner_key || entry?.ownerKey || null,
      uuid: entry?.uuid || entry?.idempotency_key || entry?.idempotencyKey || null,
    },
    { status: 'pending' },
  )
  await db.generic_queue.put(record)
  return record
}

export async function getGenericQueueCounts(ownerKey = null) {
  return getQueueCounts('generic_queue', ownerKey)
}

export async function getGenericQueueDetails(ownerKey = null) {
  return getQueueDetails('generic_queue', ownerKey)
}

export async function clearGenericQueue(type = 'all', ownerKey = null) {
  return clearQueue('generic_queue', type, ownerKey)
}

export async function removeGenericQueueItem(id, ownerKey = null) {
  return removeQueueItem('generic_queue', id, ownerKey)
}

export async function requeueGenericFailures(ownerKey = null) {
  return requeueFailures('generic_queue', ownerKey)
}

export async function queueHarvest(harvestData) {
  const record = ensureQueueRecord(
    {
      ...harvestData,
      owner_key: harvestData?.owner_key || harvestData?.ownerKey || null,
      uuid: harvestData?.uuid || harvestData?.idempotency_key || harvestData?.idempotencyKey || null,
    },
    { status: 'pending' },
  )
  return db.harvest_queue.add(record)
}

export async function getPendingHarvests(ownerKey = null) {
  const pending = await db.harvest_queue
    .filter((item) => PENDING_QUEUE_STATUSES.has(item.status) && !item.dead_letter)
    .toArray()
  return ownerKey ? pending.filter((item) => item.owner_key === ownerKey) : pending
}

export async function getHarvestQueueCounts(ownerKey = null) {
  return getQueueCounts('harvest_queue', ownerKey)
}

export async function getHarvestQueueDetails(ownerKey = null) {
  return getQueueDetails('harvest_queue', ownerKey)
}

export async function clearHarvestQueue(type = 'all', ownerKey = null) {
  return clearQueue('harvest_queue', type, ownerKey)
}

export async function removeHarvestQueueItem(id, ownerKey = null) {
  return removeQueueItem('harvest_queue', id, ownerKey)
}

export async function requeueHarvestFailures(ownerKey = null) {
  return requeueFailures('harvest_queue', ownerKey)
}

export async function seedLookupCache(key, data) {
  if (typeof indexedDB === 'undefined') return
  try {
    await db.lookup_cache.put({
      key,
      data,
      cached_at: nowIso(),
      source_name: key,
      farm_scope: null,
      version_hash: null,
    })
  } catch (err) {
    console.warn(`[OfflineCache] Failed to seed cache for "${key}"`, err)
  }
}

export async function seedLookupCacheWithMeta(key, data, metadata = {}) {
  try {
    await db.lookup_cache.put({
      key,
      data,
      cached_at: metadata.cached_at || nowIso(),
      source_name: metadata.source_name || key,
      farm_scope: metadata.farm_scope ?? null,
      version_hash: metadata.version_hash ?? null,
    })
  } catch (err) {
    console.warn(`[OfflineCache] Failed to seed cache for "${key}"`, err)
  }
}

export async function getLookupCache(key, maxAgeMs = 24 * 60 * 60 * 1000) {
  if (typeof indexedDB === 'undefined') return null
  try {
    const record = await db.lookup_cache.get(key)
    if (!record) return null
    const age = Date.now() - new Date(record.cached_at).getTime()
    if (age > maxAgeMs) return null
    return record.data
  } catch (err) {
    console.warn(`[OfflineCache] Failed to read cache for "${key}"`, err)
    return null
  }
}

export async function getLookupCacheEntry(key) {
  if (typeof indexedDB === 'undefined') return null
  try {
    return (await db.lookup_cache.get(key)) || null
  } catch (err) {
    console.warn(`[OfflineCache] Failed to read cache entry for "${key}"`, err)
    return null
  }
}

const normalizeDraftRecord = (draft, defaults = {}) => {
  const now = nowIso()
  return {
    draft_uuid: draft?.draft_uuid || defaults.draft_uuid,
    farm_id: draft?.farm_id ?? defaults.farm_id ?? null,
    supervisor_id: draft?.supervisor_id ?? defaults.supervisor_id ?? null,
    log_date: draft?.log_date || defaults.log_date || null,
    data: draft?.data || defaults.data || {},
    status: draft?.status || defaults.status || 'draft',
    created_at: draft?.created_at || defaults.created_at || now,
    updated_at: draft?.updated_at || defaults.updated_at || now,
    last_queued_at: draft?.last_queued_at || defaults.last_queued_at || null,
    queue_entry_id: draft?.queue_entry_id || defaults.queue_entry_id || null,
    lookup_snapshot_version:
      draft?.lookup_snapshot_version || defaults.lookup_snapshot_version || null,
    freshness_summary: draft?.freshness_summary || defaults.freshness_summary || null,
  }
}

export async function upsertDailyLogDraft(draft) {
  const record = normalizeDraftRecord(draft)
  await db.daily_log_drafts.put(record)
  
  // 🛡️ [SOVEREIGN-OFFLINE] توثيق الحفظ الجنائي
  try {
    const { AuditLedger } = await import('../utils/auditLedger');
    await AuditLedger.signAndLog('dexie_db', 'UPSERT_DRAFT', { draftUuid: record.draft_uuid });
  } catch (e) { /* Fallback */ }
  
  return record
}

export async function getDailyLogDraft(draftUuid) {
  if (!draftUuid) return null
  return (await db.daily_log_drafts.get(draftUuid)) || null
}

export async function listDailyLogDrafts(filters = {}) {
  const allDrafts = await db.daily_log_drafts.toArray()
  return allDrafts
    .filter((draft) => {
      if (filters.status && draft.status !== filters.status) return false
      if (filters.farm_id != null && String(draft.farm_id || '') !== String(filters.farm_id)) {
        return false
      }
      if (
        filters.supervisor_id != null &&
        String(draft.supervisor_id || '') !== String(filters.supervisor_id)
      ) {
        return false
      }
      if (filters.log_date && String(draft.log_date || '') !== String(filters.log_date)) {
        return false
      }
      if (filters.exclude_statuses && filters.exclude_statuses.includes(draft.status)) {
        return false
      }
      return true
    })
    .sort(
      (a, b) =>
        new Date(b.updated_at || b.created_at || 0).getTime() -
        new Date(a.updated_at || a.created_at || 0).getTime(),
    )
}

export async function getLatestDailyLogDraft(filters = {}) {
  const drafts = await listDailyLogDrafts(filters)
  return drafts[0] || null
}

export async function deleteDailyLogDraft(draftUuid) {
  if (!draftUuid) return false
  await db.daily_log_drafts.delete(draftUuid)
  
  // 🛡️ [SOVEREIGN-OFFLINE] توثيق الحذف الجنائي
  try {
    const { AuditLedger } = await import('../utils/auditLedger');
    await AuditLedger.signAndLog('dexie_db', 'DELETE_DRAFT', { draftUuid });
  } catch (e) { }

  return true
}

export async function getDailyLogQueueCounts(ownerKey = null) {
  return getQueueCounts('daily_log_queue', ownerKey)
}

export async function getCustodyQueueCounts(ownerKey = null) {
  return getQueueCounts('custody_queue', ownerKey)
}

export async function getDailyLogQueueDetails(ownerKey = null) {
  return getQueueDetails('daily_log_queue', ownerKey)
}

export async function getCustodyQueueDetails(ownerKey = null) {
  return getQueueDetails('custody_queue', ownerKey)
}

export async function clearDailyLogQueue(type = 'all', ownerKey = null) {
  return clearQueue('daily_log_queue', type, ownerKey)
}

export async function clearCustodyQueue(type = 'all', ownerKey = null) {
  return clearQueue('custody_queue', type, ownerKey)
}

export async function removeDailyLogQueueItem(id, ownerKey = null) {
  return removeQueueItem('daily_log_queue', id, ownerKey)
}

export async function removeCustodyQueueItem(id, ownerKey = null) {
  return removeQueueItem('custody_queue', id, ownerKey)
}

export async function requeueDailyLogFailures(ownerKey = null) {
  return requeueFailures('daily_log_queue', ownerKey)
}

export async function requeueCustodyFailures(ownerKey = null) {
  return requeueFailures('custody_queue', ownerKey)
}

export async function nextOfflineClientSeq(ownerKey, category, scope = 'default') {
  const key = `offline-seq:${ownerKey || 'anonymous'}:${category}:${scope}`
  const existing = await db.userData.get(key)
  const nextValue = Number(existing?.value || 0) + 1
  await db.userData.put({
    key,
    value: nextValue,
    updated_at: nowIso(),
  })
  return nextValue
}

/**
 * [AGRI-GUARDIAN Axis 22] Auto-Purge Engine
 * Cleans up old cache entries and synced drafts to prevent DB bloat.
 * 
 * @param {Object} settings - Active FarmSettings with retention thresholds
 */
export async function performOfflinePurge(settings = {}) {
  const cacheTtl = (settings.offline_cache_retention_days || 7) * 24 * 60 * 60 * 1000
  const syncedTtl = (settings.synced_draft_retention_days || 3) * 24 * 60 * 60 * 1000
  const deadLetterTtl = (settings.dead_letter_retention_days || 14) * 24 * 60 * 60 * 1000
  
  const now = Date.now()
  const cacheCutoff = new Date(now - cacheTtl).toISOString()
  const syncedCutoff = new Date(now - syncedTtl).toISOString()
  const deadLetterCutoff = new Date(now - deadLetterTtl).toISOString()

  try {
    // 1. Purge Old Lookup Cache
    const oldCache = await db.lookup_cache.where('cached_at').below(cacheCutoff).toArray()
    if (oldCache.length) {
      await db.lookup_cache.bulkDelete(oldCache.map(c => c.key))
      console.log(`[OfflinePurge] Deleted ${oldCache.length} expired lookup cache entries.`)
    }

    // 2. Purge Synced/Completed Drafts
    const oldDrafts = await db.daily_log_drafts
      .filter(d => (d.status === 'synced' || d.status === 'completed') && d.updated_at < syncedCutoff)
      .toArray()
    if (oldDrafts.length) {
      await db.daily_log_drafts.bulkDelete(oldDrafts.map(d => d.draft_uuid))
      console.log(`[OfflinePurge] Deleted ${oldDrafts.length} old synced drafts.`)
    }

    // 3. Purge Dead Letter Queue Items (Across all queues)
    const queueTables = [
      'generic_queue', 'harvest_queue', 'sales_queue', 
      'daily_log_queue', 'custody_queue', 'attachments_queue'
    ]
    
    for (const table of queueTables) {
      const oldFailures = await db[table]
        .filter(item => (item.status === 'dead_letter' || item.dead_letter) && (item.created_at || item.queuedAt || item.updated_at) < deadLetterCutoff)
        .toArray()
      if (oldFailures.length) {
        await db[table].bulkDelete(oldFailures.map(f => f.id))
        console.log(`[OfflinePurge] Deleted ${oldFailures.length} stale failures from ${table}.`)
        if (settings.enable_local_purge_audit) {
          await db.purge_logs.add({ table_name: table, count: oldFailures.length, type: 'dead_letter', timestamp: new Date().toISOString() })
        }
      }
    }

    // 4. Enhanced Media Purge (Success Synced)
    if (settings.enable_offline_media_purge) {
      const syncedMedia = await db.attachments_queue
        .filter(item => item.status === 'synced' || item.status === 'completed')
        .toArray()
      
      if (syncedMedia.length) {
        await db.attachments_queue.bulkDelete(syncedMedia.map(m => m.id))
        console.log(`[OfflinePurge] Media Purge: Deleted ${syncedMedia.length} successfully synced attachments.`)
        if (settings.enable_local_purge_audit) {
          await db.purge_logs.add({ table_name: 'attachments_queue', count: syncedMedia.length, type: 'media_success', timestamp: new Date().toISOString() })
        }
      }
    }

    // 5. Cleanup Purge Logs (Keep latest 100)
    if (settings.enable_local_purge_audit) {
      const logCount = await db.purge_logs.count()
      if (logCount > 100) {
        const excess = logCount - 100
        const oldestLogs = await db.purge_logs.orderBy('id').limit(excess).toArray()
        await db.purge_logs.bulkDelete(oldestLogs.map(l => l.id))
      }
    }
  } catch (err) {
    console.error('[OfflinePurge] Error during automatic cleanup', err)
  }
}
