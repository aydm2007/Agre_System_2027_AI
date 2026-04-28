import { useState, useEffect, useCallback } from 'react'
import { get as idbGet, del as idbDel } from 'idb-keyval'
import { v4 as uuidv4 } from 'uuid'
import { AuditLedger } from '../utils/auditLedger'

import {
  db,
  upsertDailyLogDraft,
  getDailyLogDraft,
  getLatestDailyLogDraft,
  listDailyLogDrafts,
  deleteDailyLogDraft,
  nextOfflineClientSeq,
} from '../offline/dexie_db'
import { getQueueOwnerKey } from '../api/offlineQueueStore'
import { normalizeServiceCountsList } from '../utils/serviceCoveragePayload'

const LEGACY_DRAFT_KEY = 'daily-log-draft-v1'
const nowIso = () => new Date().toISOString()

const coerceDraftPayload = (formData, overrides = {}) => {
  const draftUuid = overrides.draftUuid || formData?.draft_uuid || uuidv4()
  return {
    draft_uuid: draftUuid,
    farm_id: overrides.farmId ?? formData?.farm ?? formData?.farm_id ?? null,
    status: overrides.status || 'draft',
    created_at: overrides.createdAt || formData?.created_at || nowIso(),
    updated_at: nowIso(),
    data: { ...formData, draft_uuid: draftUuid }
  }
}

async function migrateLegacyDraftIfPresent() {
  const legacy = await idbGet(LEGACY_DRAFT_KEY)
  if (!legacy?.data) return null
  const draft = coerceDraftPayload(legacy.data, {
    draftUuid: legacy.draft_uuid || legacy.data?.draft_uuid || uuidv4(),
  })
  await upsertDailyLogDraft(draft)
  await idbDel(LEGACY_DRAFT_KEY)
  return draft
}

export function useDailyLogOffline() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [queueCount, setQueueCount] = useState(0)
  const [queueSummary, setQueueSummary] = useState({ pending: 0, failed: 0 })

  const checkQueueSize = useCallback(async () => {
    try {
      if (db.daily_log_queue) {
        const queue = await db.daily_log_queue.toArray()
        const pending = queue.filter(i => i.status === 'pending').length
        const failed = queue.filter(i => i.status === 'failed').length
        setQueueCount(pending)
        setQueueSummary({ pending, failed })
      }
    } catch (e) {
      console.error("[OMEGA-X] Sync Health Error:", e)
    }
  }, [])

  const loadDraft = useCallback(async ({ draftUuid = null, farmId = null, logDate = null } = {}) => {
      if (draftUuid) return await getDailyLogDraft(draftUuid);
      return await getLatestDailyLogDraft({ 
          status: 'draft', 
          ...(farmId ? { farm_id: String(farmId) } : {}),
          ...(logDate ? { created_at: logDate } : {})
      });
  }, []);

  const loadDrafts = useCallback(async (filters = {}) => {
      return await listDailyLogDrafts(filters);
  }, []);

  const saveDraft = useCallback(async (formData, overrides = {}) => {
      const draft = coerceDraftPayload(formData, overrides);
      await upsertDailyLogDraft(draft);
      return draft;
  }, []);

  const clearDraft = useCallback(async (draftUuid) => {
      if (!draftUuid) return;
      await deleteDailyLogDraft(draftUuid);
  }, []);

  const queueLogSubmission = useCallback(async (payload, queueOptions = {}) => {
      const ownerKey = await getQueueOwnerKey();
      const farmId = payload?.farm_id ?? payload?.farm ?? queueOptions?.meta?.farmId ?? null
      const draftUuid = payload?.draft_uuid || queueOptions?.meta?.draft_uuid || uuidv4()
      const payloadUuid = payload?.uuid || payload?.payload_uuid || uuidv4()
      const scope = farmId ? `farm:${farmId}` : 'global'
      const clientSeq = await nextOfflineClientSeq(ownerKey, 'daily_log', scope)
      const createdAt = nowIso()
      const activityPayload = {
          ...payload,
          service_counts_payload: normalizeServiceCountsList(payload?.service_counts_payload || []),
      }
      if (Array.isArray(payload?.service_counts)) {
          activityPayload.service_counts = normalizeServiceCountsList(payload.service_counts)
      }
      const logPayload = {
          farm: farmId,
          log_date: payload?.log_date || payload?.date || createdAt.slice(0, 10),
          notes: payload?.notes || '',
      }
      if (payload?.variance_note) {
          logPayload.variance_note = payload.variance_note
      }
      const entry = {
          queue_id: payloadUuid,
          payload_uuid: payloadUuid,
          uuid: payloadUuid,
          category: 'daily_log',
          owner_key: ownerKey,
          farm_id: farmId,
          draft_uuid: draftUuid,
          device_id: queueOptions?.meta?.device_id || 'web-client',
          client_seq: clientSeq,
          idempotency_key: payload?.idempotency_key || uuidv4(),
          logPayload,
          activityPayload,
          meta: queueOptions?.meta ? { ...queueOptions.meta } : null,
          lookup_snapshot_version: queueOptions?.meta?.lookup_snapshot_version || null,
          task_contract_snapshot: queueOptions?.meta?.task_contract_snapshot || null,
          data: activityPayload,
          status: 'pending',
          dead_letter: false,
          retry_count: 0,
          created_at: createdAt,
          updated_at: createdAt,
          next_attempt_at: createdAt,
          queuedAt: createdAt,
      };
      if (db.daily_log_queue) {
          await db.daily_log_queue.put(entry);
          await AuditLedger.signAndLog('DAILY_LOG', 'QUEUE_SUBMISSION', { uuid: entry.uuid });
          await checkQueueSize();
      }
      return entry;
  }, [checkQueueSize]);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    migrateLegacyDraftIfPresent().catch(() => {})
    checkQueueSize()
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [checkQueueSize])

  return { 
      isOnline, 
      queueCount, 
      queueSummary, 
      checkQueueSize, 
      loadDraft, 
      loadDrafts,
      saveDraft, 
      clearDraft,
      queueLogSubmission 
  }
}
