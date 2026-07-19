// celox ops Service Worker
// - Hashed build assets (/assets/*) are immutable → cache-first (instant repeat loads, offline-capable).
// - Navigations (HTML) → network-first (always get the newest bundle refs), offline fallback to cached app shell / offline.html.
// - /api/* is never intercepted.
// Bump CACHE_VERSION on app-shell changes to purge old caches.

const CACHE_VERSION = 'celox-ops-v9'
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

  // Navigations (HTML) → network-first; cache NUR OK-Antworten; robuster Fallback.
  if (request.mode === 'navigate') {
    event.respondWith((async () => {
      const shell = async () => {
        const cache = await caches.open(CACHE_VERSION)
        return (await cache.match('/index.html')) || (await cache.match('/offline.html'))
      }
      try {
        const res = await fetch(request)
        if (res && res.ok) {
          // nur erfolgreiche Shell cachen (verhindert Vergiftung durch 502/504)
          const clone = res.clone()
          caches.open(CACHE_VERSION).then((cache) => cache.put('/index.html', clone))
          return res
        }
        // Nicht-OK (z. B. 502/504 im Deploy-Fenster) → gecachte App-Shell statt Fehlerseite
        return (await shell()) || res
      } catch {
        // Netzfehler → App-Shell; als letzte Instanz eine echte Response (nie undefined)
        return (await shell()) || new Response(
          '<!doctype html><meta charset="utf-8"><title>Offline</title>'
          + '<body style="font-family:sans-serif;padding:2rem"><p>Verbindung unterbrochen – bitte neu laden.</p>',
          { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } })
      }
    })())
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
