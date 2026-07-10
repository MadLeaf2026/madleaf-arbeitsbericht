const CACHE = 'madleaf-v5';
const BASE = '/madleaf-arbeitsbericht/';
const ASSETS = [
  BASE,
  BASE + 'index.html',
  BASE + 'manifest.json',
  BASE + 'logo.png',
  BASE + 'Signature_giuseppe.png'
];

// Install: mette in cache tutti gli asset
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate: elimina cache vecchie
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Fetch: network-first per index.html, cache-first per il resto
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  const isHTML = url.pathname.endsWith('.html') || url.pathname.endsWith('/');

  if (isHTML) {
    // Network-first: scarica sempre la versione più recente
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
  } else {
    // Cache-first per logo, firma, manifest
    e.respondWith(
      caches.match(e.request).then(r => {
        if (r) return r;
        return fetch(e.request).then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        }).catch(() => caches.match(BASE + 'index.html'));
      })
    );
  }
});
