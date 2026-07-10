// celox ops Service Worker
// - Hashed build assets (/assets/*) are immutable → cache-first (instant repeat loads, offline-capable).
// - Navigations (HTML) → network-first (always get the newest bundle refs), offline fallback to cached app shell / offline.html.
// - /api/* is never intercepted.
// Bump CACHE_VERSION on app-shell changes to purge old caches.

const CACHE_VERSION = 'celox-ops-v6'
const PRECACHE = [
  '/offline.html',
  '/manifest.webmanifest',
  '/favicon.svg',
  '/apple-touch-icon.png',
  '/icon-192.png',
  '/icon-512.png',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Only handle same-origin GET; never touch the API.
  if (request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) {
    return
  }

  // Immutable hashed build assets → cache-first.
  // Guard: niemals HTML unter einer Asset-URL cachen — wenn der Server für
  // einen fehlenden Chunk das SPA-Fallback (index.html, 200 OK) liefert,
  // würde die .js-URL sonst dauerhaft vergiftet.
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((res) => {
            const type = res.headers.get('content-type') || ''
            if (res.ok && !type.includes('text/html')) {
              const clone = res.clone()
              caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone))
            }
            return res
          }),
      ),
    )
    return
  }

  // Navigations (HTML) → network-first; cache the shell; offline fallback.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const clone = res.clone()
          caches.open(CACHE_VERSION).then((cache) => cache.put('/index.html', clone))
          return res
        })
        .catch(async () => {
          const cache = await caches.open(CACHE_VERSION)
          return (await cache.match('/index.html')) || (await cache.match('/offline.html'))
        }),
    )
    return
  }

  // Other same-origin GETs (icons, manifest, fonts cache, …) → cache-first with network fill.
  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request)
          .then((res) => {
            if (res.ok) {
              const clone = res.clone()
              caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone))
            }
            return res
          })
          .catch(() => cached),
    ),
  )
})
