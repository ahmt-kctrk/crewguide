// CrewGuide Service Worker v3.0 — Offline-first
// BUILD: 202605302123
const STATIC_CACHE = 'crewguide-static-202605302123';
const DYNAMIC_CACHE = 'crewguide-dynamic-202605302123';

const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
];

// ── INSTALL ──────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  console.log('[SW] Installing v3...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

// ── ACTIVATE ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== STATIC_CACHE && k !== DYNAMIC_CACHE && !k.startsWith('crewguide-city-'))
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── FETCH ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Supabase API — direkt network
  if (url.hostname.includes('supabase.co')) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: 'offline' }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    return;
  }

  // POST/PATCH/DELETE — network only
  if (event.request.method !== 'GET') return;

  // Statik dosyalar — cache first
  if (
    url.pathname.endsWith('.html') ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.jpg') ||
    url.pathname.endsWith('.json') ||
    url.pathname === '/' ||
    url.hostname.includes('fonts.googleapis') ||
    url.hostname.includes('fonts.gstatic') ||
    url.hostname.includes('unpkg.com')
  ) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Diğer GET — network first
  event.respondWith(networkFirst(event.request));
});

// ── STRATEJİLER ───────────────────────────────────────────────────────────────
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Çevrimdışı', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    if (request.mode === 'navigate') {
      const index = await caches.match('./index.html');
      if (index) return index;
    }
    return new Response('Çevrimdışı', { status: 503 });
  }
}

// ── BACKGROUND SYNC ───────────────────────────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'crewguide-sync') {
    console.log('[SW] Background sync tetiklendi');
    event.waitUntil(notifyClientsToSync());
  }
});

async function notifyClientsToSync() {
  const clientList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
  for (const client of clientList) {
    client.postMessage({ type: 'BG_SYNC' });
  }
}

// ── PUSH BİLDİRİMLERİ ────────────────────────────────────────────────────────
self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; }
  catch { data = {}; }

  const title = data.title || '✈️ CrewGuide';
  const options = {
    body: data.body || 'Yeni bir güncelleme var!',
    icon: './icons/icon-192.png',
    badge: './icons/icon-96.png',
    tag: data.tag || 'crewguide-notif',
    data: { url: data.url || './' },
    vibrate: [200, 100, 200],
    requireInteraction: false,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// ── BİLDİRİME TIKLANMA ───────────────────────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'close') return;

  const url = event.notification.data?.url || './';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.focus();
            client.postMessage({ type: 'NOTIF_CLICK', url });
            return;
          }
        }
        return clients.openWindow(url);
      })
  );
});

// ── MESAJLAR ─────────────────────────────────────────────────────────────────
self.addEventListener('message', async event => {
  const { type, cityName, urls } = event.data || {};

  if (type === 'CACHE_CITY') {
    try {
      const cache = await caches.open(`crewguide-city-${cityName}`);
      if (urls?.length) await Promise.allSettled(urls.map(u => cache.add(u)));
      event.source?.postMessage({ type: 'CITY_CACHED', cityName });
    } catch(e) { console.warn('[SW] City cache hatası:', e); }
  }

  if (type === 'DELETE_CITY_CACHE') {
    await caches.delete(`crewguide-city-${cityName}`).catch(() => {});
  }

  if (type === 'skipWaiting' || type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  // Background sync kaydı
  if (type === 'REGISTER_SYNC') {
    try {
      await self.registration.sync.register('crewguide-sync');
    } catch(e) {
      console.warn('[SW] Sync register hatası:', e);
    }
  }
});
