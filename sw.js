// CrewGuide Service Worker v4.2 — Offline-first + Supabase Cache
// BUILD: 202611072236
const STATIC_CACHE = 'crewguide-static-202611072236';
const DYNAMIC_CACHE = 'crewguide-dynamic-202611072236';
const SUPABASE_CACHE = 'crewguide-supabase-202506030001';
// Harita karoları, fontlar, fotoğraflar — deploy'da SİLİNMEZ (adı sabit), boyutu sınırlı
const RUNTIME_CACHE = 'crewguide-runtime-v1';
const RUNTIME_MAX_ENTRIES = 800;
// Yer fotoğrafları (büyük dosyalar) ayrı ve daha küçük sınırla saklanır
const PHOTO_CACHE = 'crewguide-photos-v1';
const PHOTO_MAX_ENTRIES = 40;
// Yavaş bağlantıda (havalimanı wifi'si vb.) bu kadar beklenir, sonra önbellekteki sürüm gösterilir
const PAGE_TIMEOUT_MS = 4000;
const API_TIMEOUT_MS = 7000;

const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
];
// Uygulamanın çevrimdışı da çalışması için gereken dış dosyalar (biri inmezse kurulum yine tamamlanır)
const EXTRA_ASSETS = [
  './privacy.html',
  './icons/icon-192.png',
  './icons/icon-96.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700&family=DM+Sans:wght@300;400;500&display=swap',
];

// ── INSTALL ──────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  console.log('[SW] Installing v4.1...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      // cache:'reload' → tarayıcının HTTP önbelleğini atla, her zaman sunucudaki son sürümü al
      .then(cache => cache.addAll(STATIC_ASSETS.map(u => new Request(u, { cache: 'reload' })))
        .then(() => Promise.allSettled(EXTRA_ASSETS.map(u => cache.add(new Request(u, { cache: 'reload' })))))
      )
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
            k !== RUNTIME_CACHE &&
            k !== PHOTO_CACHE &&
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
    if (url.pathname.startsWith('/auth/') || url.pathname.startsWith('/functions/') || url.pathname.startsWith('/realtime/')) return;
    // Yer fotoğrafları: bir kez inen fotoğraf çevrimdışı da görünsün
    if (url.pathname.startsWith('/storage/v1/object/public/')) {
      event.respondWith(cacheFirst(event.request, PHOTO_CACHE, PHOTO_MAX_ENTRIES));
      return;
    }
    if (!url.pathname.startsWith('/rest/')) return;
    event.respondWith(supabaseNetworkFirst(event.request));
    return;
  }

  // POST/PATCH/DELETE — network only
  if (event.request.method !== 'GET') return;

  // Uygulama sayfası (index.html) — NETWORK FIRST: internet varsa her açılışta son sürüm,
  // yoksa önbellekteki sürüm. (Eskiden cache-first'tü; telefonda eski sürüm takılı kalıyordu.)
  if (url.origin === self.location.origin &&
      (event.request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html'))) {
    event.respondWith(pageNetworkFirst(event.request));
    return;
  }

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
    url.hostname.includes('unpkg.com') ||
    url.hostname.endsWith('tile.openstreetmap.org')
  ) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Diğer GET — network first
  event.respondWith(networkFirst(event.request));
});

// ── SUPABASE NETWORK-FIRST ───────────────────────────────────────────────────
// İnternet varsa taze veri (ve önbelleği güncelle). Yoksa ya da bağlantı çok yavaşsa
// (API_TIMEOUT_MS) önbellekteki son veriyi göster; ağ cevabı gelince önbellek yine güncellenir.
async function supabaseNetworkFirst(request) {
  const cache = await caches.open(SUPABASE_CACHE);

  const network = fetch(request.clone()).then(async response => {
    if (response.ok) {
      const body = await response.text();
      const headers = new Headers();
      response.headers.forEach(function(val, key) { headers.set(key, val); });
      headers.set('x-sw-cached-at', Date.now().toString());
      try { await cache.put(request, new Response(body, { status: response.status, statusText: response.statusText, headers: headers })); } catch (e) {}
      return new Response(body, { status: response.status, statusText: response.statusText, headers: response.headers });
    }
    return response;
  });

  const cached = await cache.match(request);
  if (cached) {
    const fallback = cached.clone();
    try {
      const winner = await Promise.race([network, timeout(API_TIMEOUT_MS)]);
      if (winner) return winner;
      console.log('[SW] Yavaş bağlantı — önbellekteki veri gösteriliyor');
      network.catch(() => {});
      return fallback;
    } catch (err) {
      console.log('[SW] Offline — önbellekteki veri gösteriliyor');
      return fallback;
    }
  }

  try {
    return await network;
  } catch (err) {
    console.warn('[SW] Offline ve önbellekte yok — boş dizi dönülüyor');
    return new Response('[]', {
      status: 200,
      headers: { 'Content-Type': 'application/json', 'x-sw-offline': 'true' }
    });
  }
}

function timeout(ms) {
  return new Promise(resolve => setTimeout(() => resolve(null), ms));
}

// Önbellek çok büyümesin: en eski girdileri sil
async function trimCache(cacheName, maxEntries) {
  try {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    if (keys.length <= maxEntries) return;
    await Promise.all(keys.slice(0, keys.length - maxEntries).map(k => cache.delete(k)));
  } catch (e) {}
}

// ── STRATEJİLER ──────────────────────────────────────────────────────────────
function isAppShell(url) {
  return url.origin === self.location.origin && (url.pathname === '/' || url.pathname === '/index.html');
}

async function pageNetworkFirst(request) {
  const url = new URL(request.url);
  const shell = isAppShell(url);
  const network = fetch(request, { cache: 'no-cache' }).then(async response => {
    if (response.ok) try {
      const cache = await caches.open(STATIC_CACHE);
      if (shell) {
        // Uygulama sayfası: hem './' hem './index.html' güncel tutulur
        await cache.put('./index.html', response.clone());
        await cache.put('./', response.clone());
      } else {
        // Diğer sayfalar (ör. gizlilik) kendi adıyla saklanır — uygulama sayfasının yerine GEÇMEZ
        await cache.put(url.origin + url.pathname, response.clone());
      }
    } catch (e) {}
    return response;
  });

  const cachedPage = async () => {
    if (shell) return (await caches.match('./index.html')) || (await caches.match('./'));
    return (await caches.match(request, { ignoreSearch: true })) ||
           (await caches.match(url.origin + url.pathname)) ||
           (request.mode === 'navigate' && url.pathname.indexOf('privacy') === -1 && url.pathname.indexOf('gizlilik') === -1
             ? await caches.match('./index.html') : null);
  };

  try {
    const winner = await Promise.race([network, timeout(PAGE_TIMEOUT_MS)]);
    if (winner) return winner;
    // Bağlantı çok yavaş — önbellekteki sürümü aç, ağ cevabı arkada önbelleği güncellesin
    const cached = await cachedPage();
    if (cached) { network.catch(() => {}); return cached; }
    return await network;
  } catch {
    return (await cachedPage()) || new Response('Çevrimdışı', { status: 503 });
  }
}

async function cacheFirst(request, cacheName = RUNTIME_CACHE, maxEntries = RUNTIME_MAX_ENTRIES) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    // Sadece CORS'lu (ok) cevaplar saklanır; opaque cevaplar tarayıcı kotasını çok şişirir
    if (response.ok) {
      try {
        const cache = await caches.open(cacheName);
        await cache.put(request, response.clone());
        trimCache(cacheName, maxEntries);
      } catch (e) { /* kota dolu vb. — cevabı yine de döndür */ }
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
      try {
        const cache = await caches.open(RUNTIME_CACHE);
        await cache.put(request, response.clone());
        trimCache(RUNTIME_CACHE, RUNTIME_MAX_ENTRIES);
      } catch (e) {}
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

  if (event.data === 'skipWaiting' || type === 'skipWaiting' || type === 'SKIP_WAITING') {
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
