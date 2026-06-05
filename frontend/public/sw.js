// celox ops Service Worker — Network-First für alles.
// Reine "Add-to-Home"-Funktionalität, kein aggressives Caching.
// Vermeidet Versionsverwirrung bei Auto-Deploys.

const CACHE_NAME = 'celox-ops-v4'

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  // Purge ALL old caches on activation
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  // Never intercept API requests
  if (url.pathname.startsWith('/api/')) return
  // Network-first for everything else; fall back to cache only when offline
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        // Optionally cache successful same-origin GETs for offline fallback
        if (res.ok && event.request.method === 'GET' && url.origin === location.origin) {
          const clone = res.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone))
        }
        return res
      })
      .catch(() => caches.match(event.request))
  )
})
