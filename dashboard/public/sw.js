// Smart Shelf Monitor Service Worker
const CACHE_NAME = 'shelf-monitor-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = event.request.url;
  // Let API and video streams bypass cache directly
  if (
    event.request.method !== 'GET' ||
    url.includes('/api') || 
    url.includes('/live-') || 
    url.includes('/outputs') ||
    url.includes('/health') ||
    url.includes('/shelf-status') ||
    url.includes('/alerts') ||
    url.includes('/zones') ||
    url.includes('/history') ||
    url.includes('/metrics') ||
    url.includes('/login') ||
    url.includes('/ingest-frame') ||
    url.includes(':5000') ||
    url.includes('onrender.com')
  ) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return cachedResponse || fetch(event.request);
    })
  );
});
