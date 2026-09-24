/* Service Worker for DTETI UGM Capstone E-08 (Toren Monitoring) */

const CACHE_NAME = 'toren-cache-v1'
const PRECACHE_ASSETS = [
  '/',
  '/manifest.json',
  '/icon-192.svg',
  '/icon-512.svg',
]

// Install event: Precache core assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS)
    }).then(() => self.skipWaiting())
  )
})

// Activate event: Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    }).then(() => self.clients.claim())
  )
})

// Fetch event: Network-first strategy for navigation and static assets with offline cache fallback
self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return

  // Skip WebSocket and API requests from cache
  const url = new URL(event.request.url)
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/ws')) {
    return
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses for static assets and HTML
        if (response.status === 200) {
          const responseToCache = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache)
          })
        }
        return response
      })
      .catch(async () => {
        const cachedResponse = await caches.match(event.request)
        if (cachedResponse) {
          return cachedResponse
        }
        // If navigating to an HTML page while offline, return cached root
        if (event.request.mode === 'navigate') {
          return caches.match('/')
        }
        return new Response('Network error - Device is offline', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({ 'Content-Type': 'text/plain' }),
        })
      })
  )
})

// Push notifications event: Handle early warning & contamination alerts
self.addEventListener('push', (event) => {
  let title = 'Toren Monitoring Alert'
  let options = {
    body: 'Peringatan terdeteksi pada sistem kualitas air toren.',
    icon: '/icon-192.svg',
    badge: '/icon-192.svg',
    vibrate: [200, 100, 200],
    data: { url: '/dashboard' },
  }

  if (event.data) {
    try {
      const data = event.data.json()
      title = data.title || title
      options.body = data.body || options.body
      if (data.url) options.data.url = data.url
    } catch {
      options.body = event.data.text()
    }
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

// Notification click event: Open dashboard
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = event.notification.data?.url || '/dashboard'

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus()
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl)
      }
    })
  )
})
