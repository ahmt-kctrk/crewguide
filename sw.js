// CrewGuide Service Worker v4.0 — Offline-first + Supabase Cache
// BUILD: 202506020001
const STATIC_CACHE  = 'crewguide-static-202506020001';
const DYNAMIC_CACHE = 'crewguide-dynamic-202506020001';
const SUPABASE_CACHE = 'crewguide-supabase-202506020001';

// Supabase cache süresi: 30 dakika
const SUPABASE_TTL = 30 * 60 * 1000;

const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
];

// ── INSTALL ──────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  console.log('[SW] Installing v4...');
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

  // ── Supabase GET istekleri — network-first, cache fallback ────────────────
  if (url.hostname.includes('supabase.co')) {
    // POST/PATCH/DELETE/PUT — network only, cache'e dokunma
    if (event.request.method !== 'GET') return;

    // Auth endpoint'leri — asla cache'leme
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

// ── SUPABASe NETWORK-FIRST ────────────────────────────────────────────────────
// Önce network'e gider, başarılıysa cache'e yazar.
// Offline'da cache'ten döner. Cache'te de yoksa boş dizi döner.
async function supabaseNetworkFirst(request) {
  const cache = await caches.open(SUPABASE_CACHE);

  try {
    const response = await fetch(request.clone());

    if (response.ok) {
      // Cache'e yaz — TTL bilgisini header'a göm
      const cloned = response.clone();
      const body = await cloned.text();
      const cachedResponse = new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          ...Object.fromEntries(response.headers.entries()),
          'x-sw-cached-at': Date.now().toString(),
        }
      });
      cache.put(request, cachedResponse);
      // Orijinal response'u döndür
      return new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
    }

    return response;

  } catch (err) {
    // Offline — cache'e bak
    console.log('[SW] Offline, Supabase cache kontrol ediliyor...');
    const cached = await cache.match(request);

    if (cached) {
      const cachedAt = parseInt(cached.headers.get('x-sw-cached-at') || '0');
      const age = Date.now() - cachedAt;
      const ageMin = Math.round(age / 60000);
      console.log(`[SW] Cache hit — ${ageMin} dakika önce kaydedilmiş`);
      return cached;
    }

    // Cache'te yok — boş dizi dön (uygulama bunu handle ediyor)
    console.warn('[SW] Cache miss — boş dizi dönülüyor');
    return new Response('[]', {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'x-sw-offline': 'true',
      }
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

  if (type === 'REGISTER_SYNC') {
    try {
      await self.registration.sync.register('crewguide-sync');
    } catch(e) {
      console.warn('[SW] Sync register hatası:', e);
    }
  }

  // Supabase cache'i manuel temizle (şehir değişince çağrılabilir)
  if (type === 'CLEAR_SUPABASE_CACHE') {
    await caches.delete(SUPABASE_CACHE).catch(() => {});
    console.log('[SW] Supabase cache temizlendi');
  }
});
