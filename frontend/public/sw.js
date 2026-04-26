/**
 * [AGRI-GUARDIAN] Service Worker for PWA Offline Support
 * Implements caching strategies for API responses and static assets.
 */

const CACHE_VERSION = 'agriasset-v1'
const STATIC_CACHE = `${CACHE_VERSION}-static`
const API_CACHE = `${CACHE_VERSION}-api`

// Static assets to cache on install
const STATIC_ASSETS = ['/', '/index.html', '/manifest.json']

// API endpoints to cache (lookup data)
const CACHEABLE_API_PATTERNS = [
  '/api/farms/',
  '/api/crops/',
  '/api/tasks/',
  '/api/locations/',
  '/api/assets/',
  '/api/items/',
  '/api/tree-loss-reasons/',
  '/api/crop-varieties/',
]

// Install Event: Cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...')
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Caching static assets')
      return cache.addAll(STATIC_ASSETS)
    }),
  )
  // Activate immediately
  self.skipWaiting()
})

// Activate Event: Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...')
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter(
            (name) => name.startsWith('agriasset-') && name !== STATIC_CACHE && name !== API_CACHE,
          )
          .map((name) => {
            console.log('[SW] Deleting old cache:', name)
            return caches.delete(name)
          }),
      )
    }),
  )
  // Claim all clients immediately
  self.clients.claim()
})

// Fetch Event: Network-first for API, Cache-first for static
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET requests
  if (request.method !== 'GET') return

  // API Requests: Network-first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    const isCacheable = CACHEABLE_API_PATTERNS.some((pattern) => url.pathname.includes(pattern))

    if (isCacheable) {
      event.respondWith(
        fetch(request)
          .then((response) => {
            // Clone and cache successful responses
            if (response.ok) {
              const clonedResponse = response.clone()
              caches.open(API_CACHE).then((cache) => {
                cache.put(request, clonedResponse)
              })
            }
            return response
          })
          .catch(() => {
            // Fallback to cache
            return caches.match(request).then((cached) => {
              if (cached) {
                console.log('[SW] Serving cached API:', url.pathname)
                return cached
              }
              // Return empty response if nothing cached
              return new Response(JSON.stringify({ results: [], offline: true }), {
                headers: { 'Content-Type': 'application/json' },
              })
            })
          }),
      )
      return
    }
  }

  // Static Assets: Cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached
      return fetch(request).then((response) => {
        // Only cache same-origin requests
        if (response.ok && url.origin === self.location.origin) {
          const clonedResponse = response.clone()
          caches.open(STATIC_CACHE).then((cache) => {
            cache.put(request, clonedResponse)
          })
        }
        return response
      })
    }),
  )
})

// Background Sync for offline submissions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background Sync event:', event.tag)

  if (event.tag === 'sync-daily-logs') {
    event.waitUntil(syncPendingLogs())
  }
})

async function syncPendingLogs() {
  try {
    console.log('[SW] Syncing pending daily logs... notifying clients')
    const clientList = await self.clients.matchAll()
    clientList.forEach((client) => {
      client.postMessage({ type: 'SYNC_OFFLINE_QUEUE' })
    })
  } catch (error) {
    console.error('[SW] Sync failed:', error)
  }
}

// Push Notifications (placeholder for future)
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received:', event.data?.text())
})

console.log('[SW] Service Worker loaded')
