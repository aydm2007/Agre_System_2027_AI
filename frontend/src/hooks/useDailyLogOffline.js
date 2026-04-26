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
} from '../offline/dexie_db'
import { sanitizeDailyLogActivityPayload } from '../utils/dailyLogPayload'
import { getQueueOwnerKey } from '../api/offlineQueueStore'

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
        
        if (pending > 0) {
           await AuditLedger.signAndLog('offline_sync', 'QUEUE_HEALTH_CHECK', { pending, failed });
        }
      }
    } catch (e) {
      console.error("[OMEGA-X] Sync Health Error:", e);
    }
  }, [])

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    migrateLegacyDraftIfPresent().catch(() => {})
    checkQueueSize();
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [checkQueueSize])

  return { isOnline, queueCount, queueSummary, checkQueueSize }
}
