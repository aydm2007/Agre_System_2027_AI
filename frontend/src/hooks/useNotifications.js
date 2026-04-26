/**
 * [AGRI-GUARDIAN] useNotifications — Real-Time SSE Hook
 *
 * Connects to the backend SSE stream for live notifications:
 * - Variance alerts
 * - Pending approvals
 * - Connection heartbeats
 *
 * Usage:
 *   const { alerts, approvalCount, isConnected } = useNotifications(farmId)
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { getAccessTokenValue } from '../api/tokenStorage'

const SSE_PATH = '/api/v1/notifications/stream/'

export function useNotifications(farmId, options = {}) {
  const { enabled = true } = options
  const [alerts, setAlerts] = useState([])
  const [approvalCount, setApprovalCount] = useState(0)
  const [opsEvents, setOpsEvents] = useState([])
  const [runtimeAlerts, setRuntimeAlerts] = useState({
    approval: null,
    attachment: null,
    outbox: null,
    release: null,
    offline: null,
  })
  const [isConnected, setIsConnected] = useState(false)
  const eventSourceRef = useRef(null)
  const reconnectTimerRef = useRef(null)

  const connect = useCallback(() => {
    if (!enabled) {
      setIsConnected(false)
      return
    }

    // Don't connect if offline
    if (typeof navigator !== 'undefined' && !navigator.onLine) return

    const params = new URLSearchParams()
    if (farmId && farmId !== 'all') params.set('farm_id', farmId)
    const accessToken = getAccessTokenValue()
    if (!accessToken) {
      setIsConnected(false)
      return
    }
    params.set('access_token', accessToken)

    const url = `${SSE_PATH}${params.toString() ? '?' + params.toString() : ''}`

    try {
      const source = new EventSource(url, { withCredentials: true })
      eventSourceRef.current = source

      source.onopen = () => {
        setIsConnected(true)
      }

      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const normalizedAlert = data?.fingerprint
            ? {
                ...data,
                kind: data.kind || data.type,
                type: data.type || data.kind,
              }
            : null

          const mergeOpsEvent = (payload) => {
            if (!payload?.fingerprint) return
            setOpsEvents((prev) => {
              const next = [
                payload,
                ...prev.filter((item) => item.fingerprint !== payload.fingerprint),
              ]
              return next.slice(0, 30)
            })
          }

          switch (data.type) {
            case 'variance_alert':
              setAlerts(data.alerts || [])
              break
            case 'approval_pending':
              setApprovalCount(data.count || 0)
              break
            case 'approval_runtime_attention':
              setRuntimeAlerts((prev) => ({ ...prev, approval: normalizedAlert || data }))
              mergeOpsEvent(normalizedAlert || data)
              break
            case 'attachment_runtime_attention':
              setRuntimeAlerts((prev) => ({ ...prev, attachment: normalizedAlert || data }))
              mergeOpsEvent(normalizedAlert || data)
              break
            case 'outbox_dead_letter_attention':
              setRuntimeAlerts((prev) => ({ ...prev, outbox: normalizedAlert || data }))
              mergeOpsEvent(normalizedAlert || data)
              break
            case 'release_health_warning':
              setRuntimeAlerts((prev) => ({ ...prev, release: normalizedAlert || data }))
              mergeOpsEvent(normalizedAlert || data)
              break
            case 'offline_sync_attention':
              setRuntimeAlerts((prev) => ({ ...prev, offline: normalizedAlert || data }))
              mergeOpsEvent(normalizedAlert || data)
              break
            case 'connected':
              setIsConnected(true)
              break
            case 'disconnected':
              setIsConnected(false)
              break
            case 'heartbeat':
              // Keep-alive, no UI update needed
              break
            default:
              break
          }
        } catch {
          // Malformed event data — skip
        }
      }

      source.onerror = () => {
        source.close()
        setIsConnected(false)
        if (!enabled || !getAccessTokenValue()) {
          return
        }
        // Reconnect after 30 seconds
        reconnectTimerRef.current = setTimeout(connect, 30000)
      }
    } catch {
      // EventSource not supported or URL invalid
      setIsConnected(false)
    }
  }, [enabled, farmId])

  useEffect(() => {
    connect()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
      }
    }
  }, [connect])

  return { alerts, approvalCount, runtimeAlerts, opsEvents, isConnected }
}

export default useNotifications
