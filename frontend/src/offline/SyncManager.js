import { flushQueue } from '../api/client'

class OfflineSyncManager {
  constructor() {
    this.syncTimer = null
    this.STABILITY_DELAY = 10000
    this.startListener()
  }

  startListener() {
    window.addEventListener('online', () => {
      this.scheduleSync()
    })

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        this.scheduleSync()
      }
    })

    if (navigator.serviceWorker) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'SYNC_OFFLINE_QUEUE') {
          console.log('[SyncManager] Received SW sync trigger')
          this.scheduleSync()
        }
      })
    }
  }

  scheduleSync() {
    if (this.syncTimer) clearTimeout(this.syncTimer)
    this.syncTimer = setTimeout(() => {
      flushQueue().catch((error) => {
        console.error('Offline sync wrapper failed', error)
      })
    }, this.STABILITY_DELAY)
  }
}

export const syncManager = new OfflineSyncManager()
