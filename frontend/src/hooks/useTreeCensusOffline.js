import { useState, useEffect, useCallback, useRef } from 'react'
import { get as idbGet, set as idbSet } from 'idb-keyval'

/**
 * [Agri-Guardian] Offline-First Infrastructure Hook for Tree Census Module.
 *
 * Design Principles (per AGENTS.md §18 – Offline & Field Mode Protocols):
 *   1. Cache-First reads: All GET data is cached in IndexedDB on success,
 *      and served from cache on network failure.
 *   2. Sequential queue: Offline mutations are queued and flushed FIFO
 *      to maintain strict ordering (Idempotency compliance).
 *   3. Auto-sync on reconnect: When navigator.onLine transitions true,
 *      pending queue is automatically drained.
 *   4. Financial mutations are NEVER queued: Resolve/approve actions
 *      must always require live server confirmation.
 *
 * Context: Northern Yemen — weak/unstable internet, manual entry as source of truth.
 */

// ─── IndexedDB Key Constants ─────────────────────────────────────────────────
export const IDB_KEYS = {
  FARMS: 'tc-cache-farms-v1',
  CROPS: 'tc-cache-crops-v1',
  LOCATIONS_PREFIX: 'tc-cache-locations-farm-',
  VARIETIES_PREFIX: 'tc-cache-varieties-crop-',
  COHORTS_PREFIX: 'tc-cache-cohorts-',
  ALERTS_PREFIX: 'tc-cache-alerts-',
  CENSUS_QUEUE: 'tree-census-offline-queue',
}

// ─── Cache Helpers ───────────────────────────────────────────────────────────

/**
 * Write data to IndexedDB with a timestamp for staleness detection.
 * @param {string} key - IndexedDB key
 * @param {*} data - Data to cache
 */
export async function cacheSet(key, data) {
  try {
    await idbSet(key, { timestamp: Date.now(), data })
  } catch (err) {
    console.warn('[TreeCensusOffline] cacheSet failed:', key, err)
  }
}

/**
 * Read data from IndexedDB. Returns { timestamp, data } or null.
 * @param {string} key - IndexedDB key
 * @returns {Promise<{timestamp: number, data: *}|null>}
 */
export async function cacheGet(key) {
  try {
    return await idbGet(key)
  } catch (err) {
    console.warn('[TreeCensusOffline] cacheGet failed:', key, err)
    return null
  }
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useTreeCensusOffline() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [offlineQueue, setOfflineQueue] = useState([])
  const [syncing, setSyncing] = useState(false)
  const reconnectCallbacks = useRef([])

  // ── Network listeners ───────────────────────────────────────────────────
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      // Fire all registered reconnect callbacks
      reconnectCallbacks.current.forEach((cb) => {
        try {
          cb()
        } catch (e) {
          console.error('[TreeCensusOffline] reconnect callback error:', e)
        }
      })
    }
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // ── Load persisted queue on mount ───────────────────────────────────────
  useEffect(() => {
    idbGet(IDB_KEYS.CENSUS_QUEUE)
      .then((q) => {
        if (Array.isArray(q)) setOfflineQueue(q)
      })
      .catch(() => {})
  }, [])

  // ── Register a callback that fires when network transitions to online ──
  const onReconnect = useCallback((callback) => {
    reconnectCallbacks.current.push(callback)
    // Return unsubscribe function
    return () => {
      reconnectCallbacks.current = reconnectCallbacks.current.filter((cb) => cb !== callback)
    }
  }, [])

  // ── Push an item to the offline queue ──────────────────────────────────
  const queuePush = useCallback(
    async (item) => {
      const updated = [...offlineQueue, item]
      setOfflineQueue(updated)
      await idbSet(IDB_KEYS.CENSUS_QUEUE, updated)
      return updated
    },
    [offlineQueue],
  )

  // ── Flush the queue sequentially (FIFO order per AGENTS.md Idempotency) ─
  const queueFlush = useCallback(
    async (apiCall) => {
      if (offlineQueue.length === 0 || !navigator.onLine) return 0
      setSyncing(true)

      const remaining = [...offlineQueue]
      let syncCount = 0

      for (const item of [...offlineQueue]) {
        try {
          await apiCall(item.payload)
          remaining.shift()
          syncCount++
        } catch (err) {
          console.error('[TreeCensusOffline] queueFlush item failed, stopping:', err)
          break // Stop on first failure to maintain strict sequence
        }
      }

      setOfflineQueue(remaining)
      await idbSet(IDB_KEYS.CENSUS_QUEUE, remaining)
      setSyncing(false)
      return syncCount
    },
    [offlineQueue],
  )

  // ── Fetch with cache fallback (the core offline-first pattern) ─────────
  const fetchWithCache = useCallback(async (cacheKey, fetchFn) => {
    if (navigator.onLine) {
      try {
        const data = await fetchFn()
        await cacheSet(cacheKey, data)
        return { data, fromCache: false, error: null }
      } catch (err) {
        // Network request failed even though navigator says online (unstable connection)
        console.warn('[TreeCensusOffline] Online fetch failed, falling back to cache:', err)
        const cached = await cacheGet(cacheKey)
        if (cached?.data) {
          return {
            data: cached.data,
            fromCache: true,
            error: 'تعذر الاتصال بالخادم. يتم عرض البيانات المخبأة محلياً.',
          }
        }
        return {
          data: null,
          fromCache: false,
          error: 'تعذر الاتصال بالشبكة ولا توجد بيانات مخبأة.',
        }
      }
    } else {
      // Explicitly offline
      const cached = await cacheGet(cacheKey)
      if (cached?.data) {
        return {
          data: cached.data,
          fromCache: true,
          error: 'وضع عدم الاتصال. يتم عرض البيانات المخبأة محلياً.',
        }
      }
      return {
        data: null,
        fromCache: false,
        error: 'انقطاع الاتصال بالشبكة ولا توجد بيانات مخبأة لهذه الوجهة.',
      }
    }
  }, [])

  return {
    isOnline,
    isOffline: !isOnline,
    offlineQueue,
    syncing,
    onReconnect,
    queuePush,
    queueFlush,
    fetchWithCache,
    IDB_KEYS,
  }
}
