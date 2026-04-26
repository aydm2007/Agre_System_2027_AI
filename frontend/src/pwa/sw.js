self.addEventListener('install', (event) => {
  const CACHE_NAME = cacheName()
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(precacheUrls()).catch((error) => {
        console.error('Precache failed', error)
      })
    )
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  const currentName = cacheName()
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith('saradud-cache-') && key !== currentName)
          .map((key) => caches.delete(key)),
      )
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return

  const requestUrl = new URL(event.request.url)
  const isApi = requestUrl.pathname.startsWith('/api/')
  const isNavigation = event.request.mode === 'navigate'

  if (isApi) {
    event.respondWith(networkThenCache(event.request))
    return
  }

  if (isNavigation) {
    event.respondWith(staleWhileRevalidate(event.request, '/offline.html'))
    return
  }

  event.respondWith(staleWhileRevalidate(event.request))
})

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-queue') {
    event.waitUntil(
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
        clients.forEach((client) => client.postMessage({ type: 'SYNC_OFFLINE_QUEUE' }))
      })
    )
  }
})

const cacheName = () => {
  const version = 'v2.5'
  return `saradud-cache-${version}`
}

const precacheUrls = () => ([
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.webmanifest',
  '/logo.png',
])

const staleWhileRevalidate = async (request, fallbackPath) => {
  const cache = await caches.open(cacheName())
  const cached = await cache.match(request)
  try {
    const response = await fetch(request)
    cache.put(request, response.clone())
    return response
  } catch (error) {
    if (cached) return cached
    if (fallbackPath) {
      const fallback = await cache.match(fallbackPath)
      if (fallback) return fallback
    }
    throw error
  }
}

const networkThenCache = async (request) => {
  const cache = await caches.open(cacheName())
  try {
    const response = await fetch(request)
    cache.put(request, response.clone())
    return response
  } catch (error) {
    const cached = await cache.match(request)
    if (cached) return cached
    throw error
  }
}
