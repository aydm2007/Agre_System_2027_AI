/**
 * TI-12: Offline-First Sync Status Hook
 *
 * Monitors online/offline connectivity and outbox pending count.
 * Adapted for Yemen's weak-internet agricultural context.
 *
 * AGENTS.md context: "weak internet, manual entry as source of truth"
 *
 * Usage:
 *   const { syncStatus, pendingCount, isSyncing } = useOfflineSync();
 *
 * @see improvement_plan.md TI-12
 */

import { useState, useEffect, useCallback, useRef } from 'react';

const OUTBOX_POLL_INTERVAL_MS = 30_000; // 30 seconds (battery/network friendly)
const RECONNECT_SYNC_DELAY_MS = 2_000;  // 2 second delay before triggering sync on reconnect

/**
 * Connectivity-aware sync hook.
 *
 * @param {Object} options
 * @param {Function} [options.onReconnect] - Called when connectivity is restored
 * @param {Function} [options.getOutboxCount] - Async fn returning pending outbox count
 * @returns {{ syncStatus: 'online'|'offline'|'syncing', pendingCount: number, isSyncing: boolean, lastSynced: Date|null }}
 */
export function useOfflineSync({ onReconnect, getOutboxCount } = {}) {
  const [syncStatus, setSyncStatus] = useState(
    typeof navigator !== 'undefined' && navigator.onLine ? 'online' : 'offline'
  );
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSynced, setLastSynced] = useState(null);

  const reconnectTimerRef = useRef(null);
  const pollIntervalRef = useRef(null);

  // ── Outbox count polling ─────────────────────────────────────────────────
  const refreshOutboxCount = useCallback(async () => {
    if (typeof getOutboxCount !== 'function') return;
    try {
      const count = await getOutboxCount();
      setPendingCount(typeof count === 'number' ? count : 0);
    } catch {
      // Silently ignore polling errors — offline or IndexedDB unavailable
    }
  }, [getOutboxCount]);

  // ── Connectivity handlers ────────────────────────────────────────────────
  const handleOnline = useCallback(() => {
    setSyncStatus('online');

    // Delay sync slightly to allow full connectivity restoration
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = setTimeout(async () => {
      if (typeof onReconnect === 'function') {
        setIsSyncing(true);
        try {
          await onReconnect();
          setLastSynced(new Date());
          await refreshOutboxCount();
        } finally {
          setIsSyncing(false);
          setSyncStatus('online');
        }
      }
    }, RECONNECT_SYNC_DELAY_MS);
  }, [onReconnect, refreshOutboxCount]);

  const handleOffline = useCallback(() => {
    setSyncStatus('offline');
    setIsSyncing(false);
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
  }, []);

  // ── Effect: mount / unmount ──────────────────────────────────────────────
  useEffect(() => {
    // Initial state
    setSyncStatus(navigator.onLine ? 'online' : 'offline');
    refreshOutboxCount();

    // Connectivity listeners
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Periodic outbox polling (30s interval)
    pollIntervalRef.current = setInterval(refreshOutboxCount, OUTBOX_POLL_INTERVAL_MS);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(pollIntervalRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, [handleOnline, handleOffline, refreshOutboxCount]);

  return {
    /** 'online' | 'offline' | 'syncing' */
    syncStatus: isSyncing ? 'syncing' : syncStatus,
    /** Number of operations pending in the local outbox */
    pendingCount,
    /** True while reconnect-triggered sync is running */
    isSyncing,
    /** Date of last successful sync, or null */
    lastSynced,
  };
}

export default useOfflineSync;
