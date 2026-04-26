/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import useNetworkStatus from './useNetworkStatus'
import { flushQueue, getOfflineQueueCounts } from '../api/client'
import { useToast } from '../components/ToastProvider'
import { useSettings } from '../contexts/SettingsContext'
import { performOfflinePurge } from './dexie_db'

const SYNC_INTERVAL_MS = 15 * 60 * 1000

const OfflineQueueContext = createContext({
  isOnline: true,
  queuedRequests: 0,
  queuedHarvests: 0,
  queuedDailyLogs: 0,
  queuedCustody: 0,
  failedRequests: 0,
  failedHarvests: 0,
  failedDailyLogs: 0,
  failedCustody: 0,
  syncing: false,
  lastSync: null,
  refreshCounts: () => {},
  syncNow: async () => ({ totalProcessed: 0 }),
  addToast: () => {},
})

export function OfflineQueueProvider({ children }) {
  const isOnline = useNetworkStatus()
  const [queuedRequests, setQueuedRequests] = useState(0)
  const [queuedHarvests, setQueuedHarvests] = useState(0)
  const [queuedDailyLogs, setQueuedDailyLogs] = useState(0)
  const [queuedCustody, setQueuedCustody] = useState(0)
  const [failedRequests, setFailedRequests] = useState(0)
  const [failedHarvests, setFailedHarvests] = useState(0)
  const [failedDailyLogs, setFailedDailyLogs] = useState(0)
  const [failedCustody, setFailedCustody] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState(null)
  const [lastNoPendingToastAt, setLastNoPendingToastAt] = useState(0)
  const addToast = useToast()
  const { offlineCacheRetentionDays, syncedDraftRetentionDays, deadLetterRetentionDays } = useSettings()

  const refreshCounts = useCallback(async () => {
    try {
      const counts = await getOfflineQueueCounts()
      setQueuedRequests(counts.requests || 0)
      setQueuedHarvests(counts.harvests || 0)
      setQueuedDailyLogs(counts.dailyLogs || 0)
      setQueuedCustody(counts.custody || 0)
      setFailedRequests(counts.failedRequests || 0)
      setFailedHarvests(counts.failedHarvests || 0)
      setFailedDailyLogs(counts.failedDailyLogs || 0)
      setFailedCustody(counts.failedCustody || 0)
      return counts
    } catch (error) {
      console.error('Failed to load offline queue counts', error)
      return null
    }
  }, [])

  const syncNow = useCallback(async () => {
    if (!isOnline) {
      return { totalProcessed: 0, skipped: true }
    }
    if (syncing) {
      return { totalProcessed: 0 }
    }
    const hadPendingBeforeSync =
      queuedRequests > 0 ||
      queuedHarvests > 0 ||
      queuedDailyLogs > 0 ||
      queuedCustody > 0 ||
      failedRequests > 0 ||
      failedHarvests > 0 ||
      failedDailyLogs > 0 ||
      failedCustody > 0
    setSyncing(true)
    try {
      const result = await flushQueue()
      await refreshCounts()
      if (Array.isArray(result?.syncedDailyLogs) && result.syncedDailyLogs.length) {
        window.dispatchEvent(
          new CustomEvent('offline-daily-log-synced', {
            detail: { syncedDailyLogs: result.syncedDailyLogs, timestamp: Date.now() },
          }),
        )
        window.dispatchEvent(
          new CustomEvent('offline-sync-complete', {
            detail: { syncedDailyLogs: result.syncedDailyLogs, timestamp: Date.now() },
          }),
        )
      }
      if (result.totalProcessed > 0) {
        setLastSync(new Date().toISOString())
        addToast({ intent: 'success', message: 'تمت مزامنة الطابور دون اتصال بنجاح.' })
      } else if (
        result.failedRequests ||
        result.failedHarvests ||
        result.failedDailyLogs ||
        result.failedCustody
      ) {
        addToast({
          intent: 'info',
          message: 'اكتملت المزامنة مع وجود عناصر فاشلة. راجع العناصر الفاشلة وأعد المحاولة.',
        })
      } else if (hadPendingBeforeSync) {
        const now = Date.now()
        if (now - lastNoPendingToastAt > 60000) {
          addToast({ intent: 'info', message: 'لا توجد عناصر معلّقة للمزامنة حالياً.' })
          setLastNoPendingToastAt(now)
        }
      }
      return result
    } catch (error) {
      console.error('Failed to flush offline queue', error)
      addToast({
        intent: 'error',
        message: 'تعذر مزامنة الطابور دون اتصال. تحقق من الاتصال ثم أعد المحاولة.',
      })
      throw error
    } finally {
      setSyncing(false)
    }
  }, [
    addToast,
    failedHarvests,
    failedDailyLogs,
    failedCustody,
    failedRequests,
    isOnline,
    lastNoPendingToastAt,
    queuedHarvests,
    queuedDailyLogs,
    queuedCustody,
    queuedRequests,
    refreshCounts,
    syncing,
  ])

  useEffect(() => {
    refreshCounts()
  }, [refreshCounts])

  // [AGRI-GUARDIAN Axis 22] Auto-Purge Integration
  useEffect(() => {
    if (isOnline && !syncing) {
      performOfflinePurge({
        offline_cache_retention_days: offlineCacheRetentionDays,
        synced_draft_retention_days: syncedDraftRetentionDays,
        dead_letter_retention_days: deadLetterRetentionDays,
      }).catch(err => console.error('[OfflinePurge] Error during background task', err))
    }
  }, [isOnline, syncing, offlineCacheRetentionDays, syncedDraftRetentionDays, deadLetterRetentionDays])

  useEffect(() => {
    const handleQueueChange = () => {
      refreshCounts()
    }
    window.addEventListener('offline-queue-change', handleQueueChange)
    return () => {
      window.removeEventListener('offline-queue-change', handleQueueChange)
    }
  }, [refreshCounts])

  useEffect(() => {
    if (typeof navigator === 'undefined' || !navigator.serviceWorker) {
      return
    }
    const handleMessage = (event) => {
      if (event.data?.type === 'SYNC_OFFLINE_QUEUE') {
        syncNow().catch(() => {})
      }
    }
    navigator.serviceWorker.addEventListener('message', handleMessage)
    return () => {
      navigator.serviceWorker.removeEventListener('message', handleMessage)
    }
  }, [syncNow])

  useEffect(() => {
    if (!isOnline || syncing) {
      return
    }
    if (queuedRequests > 0 || queuedHarvests > 0 || queuedDailyLogs > 0 || queuedCustody > 0) {
      syncNow().catch(() => {})
    }
  }, [isOnline, queuedRequests, queuedHarvests, queuedDailyLogs, queuedCustody, syncNow, syncing])
  useEffect(() => {
    if (!isOnline) {
      return undefined
    }
    const timer = setInterval(() => {
      syncNow().catch(() => {})
    }, SYNC_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [isOnline, syncNow])

  const value = useMemo(
    () => ({
      isOnline,
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
      refreshCounts,
      syncNow,
      addToast,
    }),
    [
      addToast,
      failedHarvests,
      failedDailyLogs,
      failedCustody,
      failedRequests,
      isOnline,
      lastSync,
      queuedHarvests,
      queuedDailyLogs,
      queuedCustody,
      queuedRequests,
      refreshCounts,
      syncNow,
      syncing,
    ],
  )

  return <OfflineQueueContext.Provider value={value}>{children}</OfflineQueueContext.Provider>
}

export function useOfflineQueue() {
  return useContext(OfflineQueueContext)
}
