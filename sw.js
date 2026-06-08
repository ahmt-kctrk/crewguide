// CrewGuide Service Worker v4.1 — Offline-first + Supabase Cache
// BUILD: 202606080329
const STATIC_CACHE   = 'crewguide-static-202506030001';
const DYNAMIC_CACHE  = 'crewguide-dynamic-202506030001';
const SUPABASE_CACHE = 'crewguide-supabase-202506030001';

const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
];

// ── INSTALL ──────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  console.log('[SW] Installing v4.1...');
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
          .filter(k =>
            k !== STATIC_CACHE &&
            k !== DYNAMIC_CACHE &&
            k !== SUPABASE_CACHE &&
            !k.startsWith('crewguide-city-')
          )
          .map(k => {
            console.log('[SW] Eski cache siliniyor:', k);
            return caches.delete(k);
          })
      )
    ).then(() => self.clients.claim())
  );
});

// ── FETCH ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Supabase GET istekleri — network-first, cache fallback
  if (url.hostname.includes('supabase.co')) {
    if (event.request.method !== 'GET') return;
    if (url.pathname.startsWith('/auth/')) return;
    event.respondWith(supabaseNetworkFirst(event.request));
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

// ── SUPABASE NETWORK-FIRST ───────────────────────────────────────────────────
async function supabaseNetworkFirst(request) {
  const cache = await caches.open(SUPABASE_CACHE);

  try {
    const response = await fetch(request.clone());

    if (response.ok) {
      const body = await response.text();
      // Header'ları tek tek kopyala — spread kullanma (SW uyumsuzluk)
      const headers = new Headers();
      response.headers.forEach(function(val, key) {
        headers.set(key, val);
      });
      headers.set('x-sw-cached-at', Date.now().toString());

      const cachedResponse = new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers,
      });
      cache.put(request, cachedResponse);

      return new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
    }

    return response;

  } catch (err) {
    console.log('[SW] Offline — Supabase cache kontrol ediliyor...');
    const cached = await cache.match(request);

    if (cached) {
      const cachedAt = parseInt(cached.headers.get('x-sw-cached-at') || '0');
      const ageMin = Math.round((Date.now() - cachedAt) / 60000);
      console.log('[SW] Cache hit —', ageMin, 'dakika önce');
      return cached;
    }

    console.warn('[SW] Cache miss — boş dizi dönülüyor');
    return new Response('[]', {
      status: 200,
      headers: { 'Content-Type': 'application/json', 'x-sw-offline': 'true' }
    });
  }
}

// ── STRATEJİLER ──────────────────────────────────────────────────────────────
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

// ── BACKGROUND SYNC ──────────────────────────────────────────────────────────
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

  const url = event.notification.data ? event.notification.data.url : './';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(function(clientList) {
        for (var i = 0; i < clientList.length; i++) {
          var client = clientList[i];
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.focus();
            client.postMessage({ type: 'NOTIF_CLICK', url: url });
            return;
          }
        }
        return clients.openWindow(url);
      })
  );
});

// ── MESAJLAR ─────────────────────────────────────────────────────────────────
self.addEventListener('message', function(event) {
  var data = event.data || {};
  var type = data.type;
  var cityName = data.cityName;
  var urls = data.urls;

  if (type === 'CACHE_CITY') {
    caches.open('crewguide-city-' + cityName).then(function(cache) {
      if (urls && urls.length) {
        Promise.allSettled(urls.map(function(u) { return cache.add(u); }));
      }
      if (event.source) {
        event.source.postMessage({ type: 'CITY_CACHED', cityName: cityName });
      }
    }).catch(function(e) { console.warn('[SW] City cache hatası:', e); });
  }

  if (type === 'DELETE_CITY_CACHE') {
    caches.delete('crewguide-city-' + cityName).catch(function() {});
  }

  if (type === 'skipWaiting' || type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (type === 'REGISTER_SYNC') {
    self.registration.sync.register('crewguide-sync').catch(function(e) {
      console.warn('[SW] Sync register hatası:', e);
    });
  }

  if (type === 'CLEAR_SUPABASE_CACHE') {
    caches.delete(SUPABASE_CACHE).catch(function() {});
    console.log('[SW] Supabase cache temizlendi');
  }
});
