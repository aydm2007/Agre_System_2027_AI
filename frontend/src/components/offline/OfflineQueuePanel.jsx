import { useCallback, useEffect, useMemo, useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { useNavigate } from 'react-router-dom'
import { useOfflineQueue } from '../../offline/OfflineQueueProvider.jsx'
import {
  getOfflineQueueDetails,
  clearOfflineQueue,
  requeueFailedItems,
  removeOfflineQueueItem,
} from '../../api/client.js'
import { getQueueOwnerKey } from '../../api/offlineQueueStore.js'
import { db } from '../../offline/dexie_db.js'
import { buildDailyLogIdempotencyRotationPatch } from '../../utils/offlineDailyLogIdentity.js'
import OfflineQueueRow from './OfflineQueueRow.jsx'

const DEFAULT_DETAIL_LIMIT = 100

const createEmptyMeta = () => ({
  requests: { total: 0, returned: 0, truncated: false },
  harvests: { total: 0, returned: 0, truncated: false },
  dailyLogs: { total: 0, returned: 0, truncated: false },
  custody: { total: 0, returned: 0, truncated: false },
  failedRequests: { total: 0, returned: 0, truncated: false },
  failedHarvests: { total: 0, returned: 0, truncated: false },
  failedDailyLogs: { total: 0, returned: 0, truncated: false },
  failedCustody: { total: 0, returned: 0, truncated: false },
  syncRecords: { total: 0, returned: 0, truncated: false },
  syncConflicts: { total: 0, returned: 0, truncated: false },
  quarantines: { total: 0, returned: 0, truncated: false },
})

const getErrorMessage = (error) => {
  if (!error) {
    return 'خطأ غير معروف'
  }
  if (typeof error === 'string') {
    return error
  }
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || 'خطأ غير معروف'
}

const formatDateTime = (value) => {
  if (!value) return 'غير معروف'
  try {
    return new Date(value).toLocaleString('ar-EG', { hour12: false })
  } catch {
    return value
  }
}

const queueStateLabels = {
  stale_syncing: 'stale_syncing | auto-recovered for replay',
  pending: 'queued | بانتظار المزامنة',
  syncing: 'syncing | جارٍ الترحيل',
  failed: 'failed | فشل قابل للإعادة',
  dead_letter: 'dead_letter | يحتاج مراجعة',
  draft: 'draft | مسودة محلية',
}

const queueStateClasses = {
  stale_syncing:
    'border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-500/30 dark:bg-cyan-500/10 dark:text-cyan-200',
  pending:
    'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
  syncing:
    'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-200',
  failed:
    'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200',
  dead_letter:
    'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200',
  draft:
    'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200',
}

const _resolveQueueState = (entry, fallbackStatus = 'pending') => {
  if (entry?.dead_letter || entry?.status === 'dead_letter') return 'dead_letter'
  if (entry?.status === 'syncing') return 'syncing'
  if (entry?.status === 'failed') return 'failed'
  return fallbackStatus
}

const canonicalQueueStateLabels = {
  ...queueStateLabels,
  failed_retryable: 'failed_retryable | retry pending review',
  quarantined: 'quarantined | held for review',
  synced: 'synced | replay completed',
}

const canonicalQueueStateClasses = {
  ...queueStateClasses,
  failed_retryable:
    'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200',
  quarantined:
    'border-fuchsia-200 bg-fuchsia-50 text-fuchsia-700 dark:border-fuchsia-500/30 dark:bg-fuchsia-500/10 dark:text-fuchsia-200',
  synced:
    'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200',
}

const resolveCanonicalQueueState = (entry, fallbackStatus = 'pending') => {
  if (entry?.dead_letter || entry?.status === 'dead_letter') return 'dead_letter'
  if (entry?.status === 'quarantined') return 'quarantined'
  if (entry?.sync_recovery_status === 'stale_syncing' || entry?.meta?.stale_syncing_recovered_at) return 'stale_syncing'
  if (entry?.status === 'syncing') return 'syncing'
  if (entry?.status === 'synced') return 'synced'
  if (entry?.status === 'failed_retryable') return 'failed_retryable'
  if (entry?.status === 'failed') return 'failed'
  if (entry?.status === 'draft') return 'draft'
  return fallbackStatus
}

export default function OfflineQueuePanel() {
  const {
    queuedRequests,
    queuedHarvests,
    queuedDailyLogs,
    queuedCustody,
    failedRequests,
    failedHarvests,
    failedDailyLogs,
    failedCustody,
    syncing,
    lastSync,
    syncNow,
    addToast,
    refreshCounts,
  } = useOfflineQueue()
  const navigate = useNavigate()

  const [details, setDetails] = useState({
    requests: [],
    harvests: [],
    dailyLogs: [],
    custody: [],
    failedRequests: [],
    failedHarvests: [],
    failedDailyLogs: [],
    failedCustody: [],
    syncRecords: [],
    syncConflicts: [],
    quarantines: [],
  })
  const [detailMeta, setDetailMeta] = useState(() => createEmptyMeta())
  const [detailLimit, setDetailLimit] = useState(DEFAULT_DETAIL_LIMIT)
  const [selectedItem, setSelectedItem] = useState(null)

  const loadDetails = useCallback(
    async (overrideLimit) => {
      const resolvedLimit = typeof overrideLimit === 'number' ? overrideLimit : detailLimit
      try {
        const data = await getOfflineQueueDetails({ limit: resolvedLimit })
        setDetails({
          requests: Array.isArray(data?.requests) ? data.requests : [],
          harvests: Array.isArray(data?.harvests) ? data.harvests : [],
          dailyLogs: Array.isArray(data?.dailyLogs) ? data.dailyLogs : [],
          custody: Array.isArray(data?.custody) ? data.custody : [],
          failedRequests: Array.isArray(data?.failedRequests) ? data.failedRequests : [],
          failedHarvests: Array.isArray(data?.failedHarvests) ? data.failedHarvests : [],
          failedDailyLogs: Array.isArray(data?.failedDailyLogs) ? data.failedDailyLogs : [],
          failedCustody: Array.isArray(data?.failedCustody) ? data.failedCustody : [],
          syncRecords: Array.isArray(data?.syncRecords) ? data.syncRecords : [],
          syncConflicts: Array.isArray(data?.syncConflicts) ? data.syncConflicts : [],
          quarantines: Array.isArray(data?.quarantines) ? data.quarantines : [],
        })
        setDetailMeta(() => ({
          ...createEmptyMeta(),
          ...(data?.meta || {}),
        }))
        setDetailLimit(resolvedLimit)
      } catch (error) {
        console.error('Failed to load offline queue details', error)
        addToast({
          intent: 'error',
          message: `تعذر تحميل تفاصيل الانتظار: ${getErrorMessage(error)}`,
        })
      }
    },
    [addToast, detailLimit],
  )

  useEffect(() => {
    loadDetails()
  }, [loadDetails])

  useEffect(() => {
    loadDetails()
  }, [
    queuedRequests,
    queuedHarvests,
    queuedDailyLogs,
    queuedCustody,
    failedRequests,
    failedHarvests,
    failedDailyLogs,
    failedCustody,
    loadDetails,
  ])

  const handleSync = async () => {
    try {
      await syncNow()
    } catch (error) {
      console.error('Manual sync failed', error)
    }
  }

  const handleResetSequence = async () => {
    try {
      const ownerKey = await getQueueOwnerKey()
      const seqCacheKey = `daily_log_client_seq:${ownerKey || 'anonymous'}`
      const allItems = await db.daily_log_queue.toArray()
      // Filter items belonging to THIS owner only for precise reset
      const sorted = allItems
        .filter(item =>
          (!ownerKey || item.owner_key === ownerKey) && (
            item.status === 'pending' ||
            item.status === 'syncing' ||
            item.status === 'failed' ||
            item.status === 'failed_retryable' ||
            item.status === 'dead_letter' ||
            item.dead_letter === true
          )
        )
        .sort((a, b) => new Date(a.created_at || a.queuedAt || 0) - new Date(b.created_at || b.queuedAt || 0))

      if (sorted.length === 0) {
        addToast({ intent: 'info', message: 'لا توجد عناصر للمستخدم الحالي تحتاج إعادة ترقيم.' })
        return
      }

      let seq = 1
      for (const item of sorted) {
        const newUid = uuidv4()
        const updates = {
          client_seq: seq,
          ...buildDailyLogIdempotencyRotationPatch(item, {
            newKey: newUid,
            nowIsoValue: new Date().toISOString(),
          }),
        }
        // Resurrect dead_letter items back to pending so they can be re-flushed
        if (item.status === 'dead_letter' || item.dead_letter) {
          updates.status = 'pending'
          updates.dead_letter = false
          updates.dead_letter_reason = null
          updates.last_error = null
          updates.retry_count = 0
          updates.next_attempt_at = null
        }
        // Also reset failed/syncing items to pending
        if (item.status === 'failed_retryable' || item.status === 'failed' || item.status === 'syncing') {
          updates.status = 'pending'
          updates.retry_count = 0
          updates.last_error = null
          updates.next_attempt_at = null
        }
        updates.updated_at = new Date().toISOString()
        await db.daily_log_queue.update(item.id, updates)
        seq++
      }
      // Reset the user-scoped sequence counter
      await db.userData.put({ key: seqCacheKey, value: seq - 1, updated_at: new Date().toISOString() })
      addToast({ intent: 'success', message: `تم إحياء وإعادة ترقيم ${sorted.length} سجل(ات) خاصة بك — الترقيم الجديد يبدأ من 1. اضغط "مزامنة الآن".` })
      await refreshCounts()
      loadDetails()
    } catch (e) {
      console.error('[SeqReset] Failed', e)
      addToast({ intent: 'error', message: 'فشل تصحيح الترقيم: ' + (e?.message || '') })
    }
  }

  const handleClearPending = async (type) => {
    try {
      await clearOfflineQueue(type)
      addToast({ intent: 'info', message: 'تم تفريغ العناصر المعلقة.' })
      await refreshCounts()
      loadDetails()
    } catch (error) {
      console.error('Failed to clear queue', error)
      addToast({
        intent: 'error',
        message: `تعذر تفريغ العناصر المعلقة: ${getErrorMessage(error)}`,
      })
    }
  }

  const handleClearFailed = async (type) => {
    const failedType =
      type === 'daily-log'
        ? 'failed-daily-log'
        : type === 'harvest'
          ? 'failed-harvest'
          : type === 'custody'
            ? 'failed-custody'
            : 'failed-generic'
    try {
      await clearOfflineQueue(failedType)
      addToast({ intent: 'info', message: 'تم حذف العناصر الفاشلة.' })
      await refreshCounts()
      loadDetails()
    } catch (error) {
      console.error('Failed to clear failed queue', error)
      addToast({
        intent: 'error',
        message: `تعذر حذف العناصر الفاشلة: ${getErrorMessage(error)}`,
      })
    }
  }

  const handleRetryFailures = async (type) => {
    try {
      const count = await requeueFailedItems(type)
      if (count > 0) {
        addToast({ intent: 'success', message: 'تمت إعادة العناصر الفاشلة إلى قائمة الانتظار.' })
      }
      await refreshCounts()
      loadDetails()
    } catch (error) {
      console.error('Failed to requeue failures', error)
      addToast({
        intent: 'error',
        message: `تعذر إعادة العناصر الفاشلة إلى قائمة الانتظار: ${getErrorMessage(error)}`,
      })
    }
  }

  const handleInspectItem = useCallback((queueType, entry, status) => {
    if (!entry) {
      return
    }
    setSelectedItem({ queueType, entry, status })
  }, [])

  const handleRestoreItem = useCallback(
    (entry) => {
      if (!entry) {
        return
      }
      try {
        if (typeof window !== 'undefined' && window.sessionStorage) {
          window.sessionStorage.setItem(
            'offline-daily-log-draft',
            JSON.stringify({
              id: entry.id,
              logPayload: entry.logPayload,
              activityPayload: entry.activityPayload,
              attachments: entry.attachments || [],
              meta: entry.meta || {},
            }),
          )
        }
        setSelectedItem(null)
        addToast({ intent: 'info', message: 'تم فتح السجل غير المتزامن للمراجعة.' })
        navigate('/daily-log', {
          state: {
            source: 'offline-queue',
            restoreDraftUuid: entry.draft_uuid || entry.meta?.draft_uuid || null,
            restoredQueueItemId: entry.id,
          },
        })
      } catch (error) {
        console.error('Failed to stage offline draft for restore', error)
        addToast({ intent: 'error', message: 'تعذر فتح السجل غير المتزامن. حاول مرة أخرى.' })
      }
    },
    [addToast, navigate],
  )

  const handleRemoveItem = useCallback(
    async (queueType, itemId) => {
      if (!itemId) {
        return
      }
      try {
        const removed = await removeOfflineQueueItem(queueType, itemId)
        if (removed) {
          addToast({ intent: 'success', message: 'تم حذف العنصر من قائمة الانتظار.' })
          setSelectedItem((current) => (current?.entry?.id === itemId ? null : current))
          await refreshCounts()
          loadDetails()
        } else {
          addToast({ intent: 'info', message: 'لم يتم العثور على العنصر المطلوب.' })
        }
      } catch (error) {
        console.error('Failed to remove offline queue item', error)
        addToast({
          intent: 'error',
          message: `تعذر حذف العنصر من قائمة الانتظار: ${getErrorMessage(error)}`,
        })
      }
    },
    [addToast, loadDetails, refreshCounts],
  )

  const closeSelectedItem = useCallback(() => setSelectedItem(null), [])

  const handleLoadMoreDetails = useCallback(async () => {
    const nextLimit = detailLimit + DEFAULT_DETAIL_LIMIT
    await loadDetails(nextLimit)
  }, [detailLimit, loadDetails])

  const summaries = useMemo(
    () => [
      {
        id: 'dailyLogs',
        title: 'سجلات اليوميات غير المتزامنة',
        description: 'يتم حفظ سجلات الإنجاز اليومية محليًا إلى أن يتوفر اتصال أو يتم تشغيل الخادم.',
        pendingCount: queuedDailyLogs,
        failedCount: failedDailyLogs,
        pendingDetails: details.dailyLogs,
        failedDetails: details.failedDailyLogs,
        type: 'daily-log',
        meta: {
          pending: detailMeta.dailyLogs,
          failed: detailMeta.failedDailyLogs,
        },
      },
      {
        id: 'requests',
        title: 'الطلبات الإدارية وحركات البيع غير المتزامنة',
        description: 'تشمل التعديلات على المزارع والمهام والأصول، إضافة إلى حركات البيع المعلقة.',
        pendingCount: queuedRequests,
        failedCount: failedRequests,
        pendingDetails: details.requests,
        failedDetails: details.failedRequests,
        type: 'generic',
        meta: {
          pending: detailMeta.requests,
          failed: detailMeta.failedRequests,
        },
      },
      {
        id: 'harvests',
        title: 'سجلات الحصاد غير المتزامنة',
        description: 'تشمل تسجيلات الإنتاج والحصاد التي تنتظر الترحيل إلى سجلات الحصاد.',
        pendingCount: queuedHarvests,
        failedCount: failedHarvests,
        pendingDetails: details.harvests,
        failedDetails: details.failedHarvests,
        type: 'harvest',
        meta: {
          pending: detailMeta.harvests,
          failed: detailMeta.failedHarvests,
        },
      },
      {
        id: 'custody',
        title: 'عهدة المشرف غير المتزامنة',
        description: 'تشمل قبول العهدة أو رفضها أو إرجاعها عند العمل دون اتصال.',
        pendingCount: queuedCustody,
        failedCount: failedCustody,
        pendingDetails: details.custody,
        failedDetails: details.failedCustody,
        type: 'custody',
        meta: {
          pending: detailMeta.custody,
          failed: detailMeta.failedCustody,
        },
      },
    ],
    [
      queuedRequests,
      queuedHarvests,
      queuedDailyLogs,
      queuedCustody,
      failedRequests,
      failedHarvests,
      failedDailyLogs,
      failedCustody,
      details.requests,
      details.harvests,
      details.dailyLogs,
      details.custody,
      details.failedRequests,
      details.failedHarvests,
      details.failedDailyLogs,
      details.failedCustody,
      detailMeta,
    ],
  )

  const hasAnyFailed = failedRequests + failedHarvests + failedDailyLogs + failedCustody > 0
  const hasAnyPending = queuedRequests + queuedHarvests + queuedDailyLogs + queuedCustody > 0
  const serverConflictCount = details.syncConflicts.length
  const serverQuarantineCount = details.quarantines.length
  const successfulReplayCount = details.syncRecords.filter((item) => item.status === 'success').length
  const hasServerForensics = serverConflictCount > 0 || serverQuarantineCount > 0 || successfulReplayCount > 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">إدارة عناصر الوضع دون اتصال</h3>
          <p className="text-sm text-gray-500">
            تُخزَّن الطلبات هنا عندما لا يتوفر اتصال بالشبكة، وسيتم إرسالها تلقائيًا عند نجاح المزامنة.
          </p>
          {summaries.every((item) => item.pendingCount === 0 && item.failedCount === 0) && (
            <p className="mt-1 text-xs text-gray-400">لا توجد عناصر معلقة أو فاشلة حاليًا.</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="rounded bg-primary px-3 py-2 text-sm text-white disabled:opacity-60"
            onClick={handleSync}
            disabled={syncing}
          >
            مزامنة الآن
          </button>
          <button
            type="button"
            className="rounded border border-emerald-300 px-3 py-2 text-sm hover:bg-emerald-50 text-emerald-700 dark:border-emerald-600 dark:text-emerald-400 dark:hover:bg-emerald-900/30"
            onClick={handleResetSequence}
          >
            إصلاح تسلسل المزامنة
          </button>
          <button
            type="button"
            className="rounded border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
            onClick={loadDetails}
          >
            تحديث القائمة
          </button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-800/60">
          <div className="text-xs text-slate-500 dark:text-slate-400">آخر مزامنة ناجحة</div>
          <div className="mt-1 font-semibold text-slate-900 dark:text-white">
            {formatDateTime(lastSync)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-800/60">
          <div className="text-xs text-slate-500 dark:text-slate-400">التشخيص الحالي</div>
          <div className="mt-1 font-semibold text-slate-900 dark:text-white">
            {hasAnyFailed
              ? 'توجد عناصر تحتاج معالجة أو إعادة محاولة'
              : hasAnyPending
                ? 'توجد عناصر قيد الانتظار وسيتم دفعها عند نجاح المزامنة'
                : 'الطوابير التشغيلية سليمة ولا توجد عناصر مؤجلة'}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-800/60">
          <div className="text-xs text-slate-500 dark:text-slate-400">تصنيف الطوابير</div>
          <div className="mt-1 font-semibold text-slate-900 dark:text-white">
            الطوابير التشغيلية المعتمدة:
            <span className="font-mono"> generic_queue</span>،
            <span className="font-mono"> harvest_queue</span>،
            <span className="font-mono"> daily_log_queue</span>،
            <span className="font-mono"> custody_queue</span>.
            أما <span className="font-mono">lookup_cache</span> فهي ذاكرة قراءة فقط وليست مسار ترحيل تشغيلي.
          </div>
        </div>
      </div>

      {hasAnyFailed && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">
          التوصية الحالية: راجع سبب الفشل داخل تفاصيل العنصر، ثم أعد المحاولة إذا كان الخطأ مؤقتًا. إذا كان السبب تعارضًا منطقيًا فقم بالتصحيح من الشاشة المعنية قبل إعادة المزامنة.
        </div>
      )}

      {hasServerForensics && (
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
          <div>
            <h4 className="text-base font-semibold text-slate-900 dark:text-white">مراقبة Replay الخادوم</h4>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              تعرض هذه اللوحة السجلات المرحّلة، تعارضات `DLQ`، والحمولات المعزولة ضمن farm scope الفعلي.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm dark:border-emerald-500/30 dark:bg-emerald-500/10">
              <div className="text-xs text-emerald-700 dark:text-emerald-200">Sync Records</div>
              <div className="mt-1 text-xl font-semibold text-emerald-900 dark:text-emerald-100">{successfulReplayCount}</div>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm dark:border-amber-500/30 dark:bg-amber-500/10">
              <div className="text-xs text-amber-700 dark:text-amber-200">DLQ Pending</div>
              <div className="mt-1 text-xl font-semibold text-amber-900 dark:text-amber-100">{serverConflictCount}</div>
            </div>
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm dark:border-rose-500/30 dark:bg-rose-500/10">
              <div className="text-xs text-rose-700 dark:text-rose-200">Quarantine Pending</div>
              <div className="mt-1 text-xl font-semibold text-rose-900 dark:text-rose-100">{serverQuarantineCount}</div>
            </div>
          </div>
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="rounded-xl border border-slate-200 px-3 py-3 dark:border-slate-700">
              <div className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">Sync Records</div>
              <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                {details.syncRecords.slice(0, 5).map((item) => (
                  <div key={`sync-${item.id}`} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/70">
                    <div className="font-mono">{item.category || 'unknown'} / {item.reference || item.id}</div>
                    <div>الحالة: {item.status || 'unknown'}</div>
                  </div>
                ))}
                {details.syncRecords.length === 0 && <div>لا توجد سجلات مرحّلة ضمن النطاق الحالي.</div>}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 px-3 py-3 dark:border-slate-700">
              <div className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">DLQ</div>
              <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                {details.syncConflicts.slice(0, 5).map((item) => (
                  <div key={`dlq-${item.id}`} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/70">
                    <div className="font-mono">{item.conflict_type || 'conflict'}</div>
                    <div>{item.conflict_reason || 'بدون سبب مفصل'}</div>
                  </div>
                ))}
                {details.syncConflicts.length === 0 && <div>لا توجد تعارضات مزامنة معلقة.</div>}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 px-3 py-3 dark:border-slate-700">
              <div className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">Quarantine</div>
              <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                {details.quarantines.slice(0, 5).map((item) => (
                  <div key={`quarantine-${item.id}`} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/70">
                    <div className="font-mono">{item.variance_type || 'quarantine'}</div>
                    <div>الحالة: {item.status || 'unknown'}</div>
                  </div>
                ))}
                {details.quarantines.length === 0 && <div>لا توجد حمولات معزولة ضمن النطاق الحالي.</div>}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {summaries.map((summary) => (
          <OfflineQueueRow
            key={summary.id}
            summary={summary}
            onClearPending={() => handleClearPending(summary.type)}
            onClearFailed={() => handleClearFailed(summary.type)}
            onRetryFailed={() => handleRetryFailures(summary.type)}
            onInspectItem={handleInspectItem}
            onRestoreItem={handleRestoreItem}
            onRemoveItem={handleRemoveItem}
            formatDateTime={formatDateTime}
            onLoadMore={handleLoadMoreDetails}
          />
        ))}
      </div>

      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-xl space-y-3 rounded bg-white p-4 shadow-lg dark:bg-slate-800">
            {(() => {
              const resolvedState = resolveCanonicalQueueState(
                selectedItem.entry,
                selectedItem.status === 'failed' ? 'failed' : 'pending',
              )
              const queueLabel =
                selectedItem.entry?.meta?.queueLabel || selectedItem.queueType || 'offline_queue'
              const lastError = getErrorMessage(selectedItem.entry?.last_error)
              return (
                <div className="space-y-2 rounded border border-slate-200 bg-slate-50 px-3 py-3 text-xs dark:border-slate-600 dark:bg-slate-700/60">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full border px-2 py-1 font-semibold ${canonicalQueueStateClasses[resolvedState]}`}
                    >
                      {canonicalQueueStateLabels[resolvedState]}
                    </span>
                    <span className="rounded-full border border-slate-300 px-2 py-1 font-mono text-slate-600 dark:border-slate-500 dark:text-slate-200">
                      {queueLabel}
                    </span>
                  </div>
                  <div className="text-slate-600 dark:text-slate-300">
                    المعرف: #{selectedItem.entry?.id || 'n/a'} | وقت الإدراج:{' '}
                    {formatDateTime(selectedItem.entry?.queuedAt || selectedItem.entry?.created_at)}
                  </div>
                  {(resolvedState === 'failed' || resolvedState === 'dead_letter') && (
                    <div className="rounded border border-rose-200 bg-rose-50 px-3 py-2 leading-6 text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300">
                      السبب: {lastError}
                    </div>
                  )}
                </div>
              )
            })()}
            <div className="flex items-start justify-between gap-3">
              <h4 className="text-lg font-semibold text-gray-800 dark:text-white">تفاصيل العنصر غير المتزامن</h4>
              <button
                type="button"
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
                onClick={closeSelectedItem}
              >
                إغلاق
              </button>
            </div>
            <div className="max-h-64 overflow-y-auto rounded border border-gray-200 bg-gray-50 p-3 text-xs dark:border-slate-600 dark:bg-slate-700">
              {(selectedItem.queueType === 'daily-log' ||
                selectedItem.queueType === 'failed-daily-log') && (
                <div className="mb-3 grid gap-1 rounded border border-cyan-200 bg-cyan-50 p-2 text-[11px] text-cyan-900 dark:border-cyan-700 dark:bg-cyan-950/30 dark:text-cyan-100">
                  <div>
                    <span className="font-semibold">payload_uuid:</span>{' '}
                    <span className="font-mono">{selectedItem.entry?.payload_uuid || selectedItem.entry?.uuid || '-'}</span>
                  </div>
                  <div>
                    <span className="font-semibold">idempotency_key:</span>{' '}
                    <span className="font-mono">{selectedItem.entry?.idempotency_key || '-'}</span>
                  </div>
                </div>
              )}
              <pre className="whitespace-pre-wrap break-words dark:text-slate-200">
                {JSON.stringify(selectedItem.entry, null, 2)}
              </pre>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              {(selectedItem.queueType === 'daily-log' ||
                selectedItem.queueType === 'failed-daily-log') && (
                <button
                  type="button"
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
                  onClick={() => handleRestoreItem(selectedItem.entry)}
                >
                  استعادة للسجل اليومي
                </button>
              )}
              <button
                type="button"
                className="rounded bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700"
                onClick={() => handleRemoveItem(selectedItem.queueType, selectedItem.entry?.id)}
              >
                حذف من القائمة
              </button>
              <button
                type="button"
                className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                onClick={closeSelectedItem}
              >
                إغلاق
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
