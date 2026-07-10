const CACHE = 'madleaf-v5';
const BASE = '/madleaf-arbeitsbericht/';

// Install
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll([
      BASE,
      BASE + 'index.html',
      BASE + 'manifest.json',
      BASE + 'logo.png',
      BASE + 'Signature_giuseppe.png'
    ])).then(() => self.skipWaiting())
  );
});

// Activate: elimina cache vecchie
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch: network-first per HTML, cache-first per assets
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  const isNav = e.request.mode === 'navigate' ||
    url.pathname.endsWith('.html') ||
    url.pathname === BASE ||
    url.pathname.endsWith('/');

  if (isNav) {
    // Sempre scarica la versione più recente
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(BASE + 'index.html'))
    );
  } else {
    // Cache-first per logo, firma, manifest
    e.respondWith(
      caches.match(e.request).then(r => r || fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      }))
    );
  }
});
