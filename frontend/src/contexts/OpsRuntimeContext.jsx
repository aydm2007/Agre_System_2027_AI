/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useOfflineQueue } from '../offline/OfflineQueueProvider'
import useNotifications from '../hooks/useNotifications'

const OpsRuntimeContext = createContext(null)

const OPERATOR_ROLES = ['رئيس حسابات القطاع', 'المدير المالي لقطاع المزارع', 'مدير القطاع', 'مدير النظام']

const SEVERITY_ORDER = { critical: 0, attention: 1 }

const mergeAlerts = (left = [], right = []) => {
  const mapped = new Map()
  ;[...left, ...right].forEach((item) => {
    if (!item?.fingerprint) return
    mapped.set(item.fingerprint, item)
  })
  return Array.from(mapped.values()).sort((a, b) => {
    const severityDelta =
      (SEVERITY_ORDER[a?.severity] ?? 99) - (SEVERITY_ORDER[b?.severity] ?? 99)
    if (severityDelta !== 0) return severityDelta
    return String(b?.created_at || '').localeCompare(String(a?.created_at || ''))
  })
}

export function OpsRuntimeProvider({ children }) {
  const {
    isAdmin,
    isSuperuser,
    hasPermission,
    hasFarmRole,
    isAuthenticated,
    isLoading: authLoading,
  } = useAuth()
  const offlineQueue = useOfflineQueue()
  const canObserveOps = useMemo(
    () =>
      Boolean(
        isAdmin ||
          isSuperuser ||
          hasPermission?.('can_sector_finance_approve') ||
          OPERATOR_ROLES.some((role) => hasFarmRole?.(role)),
      ),
    [hasFarmRole, hasPermission, isAdmin, isSuperuser],
  )
  const notificationsEnabled = canObserveOps && isAuthenticated && !authLoading
  const { opsEvents, runtimeAlerts, approvalCount, isConnected } = useNotifications(null, {
    enabled: notificationsEnabled,
  })
  const [alertsSnapshot, setAlertsSnapshot] = useState({ items: [], summary: {} })
  const [offlineSnapshot, setOfflineSnapshot] = useState({
    sync_conflict_dlq_pending: 0,
    offline_sync_quarantine_pending: 0,
    pending_mode_switch_quarantines: 0,
    farms: [],
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    if (!canObserveOps) {
      setAlertsSnapshot({ items: [], summary: {} })
      setOfflineSnapshot({
        sync_conflict_dlq_pending: 0,
        offline_sync_quarantine_pending: 0,
        pending_mode_switch_quarantines: 0,
        farms: [],
      })
      return
    }
    setLoading(true)
    setError('')
    try {
      const [alertsRes, offlineRes] = await Promise.all([
        api.get('/dashboard/ops-alerts/', { params: { limit: 30 } }),
        api.get('/dashboard/offline-ops/').catch(() => ({ data: { farms: [] } })),
      ])
      setAlertsSnapshot(alertsRes.data || { items: [], summary: {} })
      setOfflineSnapshot(
        offlineRes.data || {
          sync_conflict_dlq_pending: 0,
          offline_sync_quarantine_pending: 0,
          pending_mode_switch_quarantines: 0,
          farms: [],
        },
      )
    } catch (err) {
      console.error('Failed to load ops alerts', err)
      setError(err?.response?.data?.detail || 'تعذر تحميل التنبيهات التشغيلية.')
    } finally {
      setLoading(false)
    }
  }, [canObserveOps])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    if (!canObserveOps) return undefined
    const timer = window.setInterval(() => {
      refresh()
    }, 60000)
    return () => window.clearInterval(timer)
  }, [canObserveOps, refresh])

  const alerts = useMemo(
    () => mergeAlerts(alertsSnapshot.items || [], opsEvents || []),
    [alertsSnapshot.items, opsEvents],
  )

  const topAlerts = useMemo(() => alerts.slice(0, 5), [alerts])

  const localOfflineSignals = useMemo(
    () => ({
      queuedRequests: offlineQueue.queuedRequests || 0,
      queuedHarvests: offlineQueue.queuedHarvests || 0,
      queuedDailyLogs: offlineQueue.queuedDailyLogs || 0,
      queuedCustody: offlineQueue.queuedCustody || 0,
      failedRequests: offlineQueue.failedRequests || 0,
      failedHarvests: offlineQueue.failedHarvests || 0,
      failedDailyLogs: offlineQueue.failedDailyLogs || 0,
      failedCustody: offlineQueue.failedCustody || 0,
      syncing: Boolean(offlineQueue.syncing),
      lastSync: offlineQueue.lastSync || null,
      isOnline: Boolean(offlineQueue.isOnline),
    }),
    [offlineQueue],
  )

  const acknowledgeAlert = useCallback(
    async (fingerprint, note = '') => {
      if (!canObserveOps || !fingerprint) return null
      const response = await api.post('/dashboard/ops-alerts/acknowledge/', {
        fingerprint,
        note,
      })
      await refresh()
      return response.data
    },
    [canObserveOps, refresh],
  )

  const snoozeAlert = useCallback(
    async (fingerprint, hours, note = '') => {
      if (!canObserveOps || !fingerprint) return null
      const response = await api.post('/dashboard/ops-alerts/snooze/', {
        fingerprint,
        hours,
        note,
      })
      await refresh()
      return response.data
    },
    [canObserveOps, refresh],
  )

  const loadRequestTrace = useCallback(async (params = {}) => {
    const response = await api.get('/finance/approval-requests/request-trace/', { params })
    return response.data
  }, [])

  const loadOutboxTrace = useCallback(async (params = {}) => {
    const response = await api.get('/dashboard/outbox-health/trace/', { params })
    return response.data
  }, [])

  const loadAttachmentTrace = useCallback(async (params = {}) => {
    const response = await api.get('/dashboard/attachment-runtime-health/trace/', { params })
    return response.data
  }, [])

  const value = useMemo(
    () => ({
      alerts,
      topAlerts,
      summary: alertsSnapshot.summary || {},
      runtimeAlerts,
      approvalCount,
      offlineSnapshot,
      localOfflineSignals,
      canObserveOps,
      isConnected,
      loading,
      error,
      refresh,
      acknowledgeAlert,
      snoozeAlert,
      loadRequestTrace,
      loadOutboxTrace,
      loadAttachmentTrace,
    }),
    [
      acknowledgeAlert,
      alerts,
      alertsSnapshot.summary,
      canObserveOps,
      error,
      isConnected,
      loadAttachmentTrace,
      loadOutboxTrace,
      loadRequestTrace,
      loading,
      localOfflineSignals,
      offlineSnapshot,
      approvalCount,
      refresh,
      runtimeAlerts,
      snoozeAlert,
      topAlerts,
    ],
  )

  return <OpsRuntimeContext.Provider value={value}>{children}</OpsRuntimeContext.Provider>
}

export function useOpsRuntime() {
  const context = useContext(OpsRuntimeContext)
  if (!context) {
    throw new Error('useOpsRuntime must be used within an OpsRuntimeProvider')
  }
  return context
}
