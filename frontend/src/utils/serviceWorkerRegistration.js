/**
 * [AGRI-GUARDIAN] Service Worker Registration
 * Registers the service worker for PWA offline support.
 */

export function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js')
        // [AG-CLEANUP] console.log('[PWA] Service Worker registered:', registration.scope)

        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          // [AG-CLEANUP] console.log('[PWA] New Service Worker found')

          newWorker?.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New content available
              // [AG-CLEANUP] console.log('[PWA] New content available, refresh to update')
              // Could show a toast here to prompt user to refresh
            }
          })
        })
      } catch (error) {
        console.error('[PWA] Service Worker registration failed:', error)
      }
    })
  } else {
    // [AG-CLEANUP] console.log('[PWA] Service Workers not supported')
  }
}

export function unregisterServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.unregister()
    })
  }
}

// Request persistent storage for offline data
export async function requestPersistentStorage() {
  if (navigator.storage && navigator.storage.persist) {
    const isPersisted = await navigator.storage.persist()
    // [AG-CLEANUP] console.log(`[PWA] Persistent storage: ${isPersisted ? 'granted' : 'denied'}`)
    return isPersisted
  }
  return false
}

// Register for background sync
export async function registerBackgroundSync(tag = 'sync-daily-logs') {
  if ('serviceWorker' in navigator && 'sync' in window.SyncManager) {
    const registration = await navigator.serviceWorker.ready
    await registration.sync.register(tag)
    // [AG-CLEANUP] console.log('[PWA] Background sync registered:', tag)
  }
}
