const CACHE = 'madleaf-v6';
const BASE = '/madleaf-arbeitsbericht/';

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll([
      BASE + 'index.html',
      BASE + 'manifest.json',
      BASE + 'logo.png',
      BASE + 'Signature_giuseppe.png'
    ])).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // Network-first per tutto — sempre aggiornato, cache come fallback offline
  e.respondWith(
    fetch(e.request)
      .then(res => {
        if(res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match(BASE + 'index.html')))
  );
});
