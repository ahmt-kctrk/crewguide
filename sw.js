// CrewGuide Service Worker v1.0
// Strateji: Cache-first for static assets, Network-first for data

const CACHE_NAME = 'crewguide-v1';
const OFFLINE_URL = './crewguide.html';

// Kurulumda cache'lenecek dosyalar (App Shell)
const APP_SHELL = [
  './crewguide.html',
  './manifest.json',
  'https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700&family=DM+Sans:wght@300;400;500&display=swap',
];

// ─── INSTALL ──────────────────────────────────────────────────────────────────
// Service worker kurulduğunda app shell'i cache'e al
self.addEventListener('install', event => {
  console.log('[SW] Install');
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[SW] Caching app shell');
      // Font URL'leri CORS kısıtlı olabilir, hata verirse geç
      return Promise.allSettled(
        APP_SHELL.map(url => cache.add(url).catch(err => {
          console.warn('[SW] Cache add failed for:', url, err);
        }))
      );
    }).then(() => {
      // Yeni SW hemen aktif olsun, eski sekmeleri bekletme
      return self.skipWaiting();
    })
  );
});

// ─── ACTIVATE ─────────────────────────────────────────────────────────────────
// Eski cache versiyonlarını temizle
self.addEventListener('activate', event => {
  console.log('[SW] Activate');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      // Tüm açık sekmeleri hemen kontrol et
      return self.clients.claim();
    })
  );
});

// ─── FETCH ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Chrome extension isteklerini ve POST'ları atla
  if (url.protocol === 'chrome-extension:' || request.method !== 'GET') return;

  // Nominatim (geocoding) istekleri için Network-first, offline'da sessiz fail
  if (url.hostname === 'nominatim.openstreetmap.org') {
    event.respondWith(
      fetch(request).catch(() => new Response(JSON.stringify({ error: 'offline' }), {
        headers: { 'Content-Type': 'application/json' }
      }))
    );
    return;
  }

  // Google Fonts için Cache-first
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        }).catch(() => new Response('', { status: 503 }));
      })
    );
    return;
  }

  // Ana HTML ve lokal dosyalar için Cache-first + Network fallback
  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) {
        // Cache'de var, arka planda güncelle (Stale-While-Revalidate)
        const fetchPromise = fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        }).catch(() => {}); // Network yoksa sessiz fail
        return cached;
      }

      // Cache'de yok, network'ten al
      return fetch(request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        }
        return response;
      }).catch(() => {
        // Tamamen offline ve cache'de yok → ana HTML'i dön
        if (request.destination === 'document') {
          return caches.match(OFFLINE_URL);
        }
        return new Response('Offline', { status: 503 });
      });
    })
  );
});

// ─── MESSAGE ──────────────────────────────────────────────────────────────────
// Ana uygulama SW ile iletişim kurabilsin
self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }

  // Belirli bir şehirin verilerini cache'e al (offline download özelliği için)
  if (event.data && event.data.type === 'CACHE_CITY') {
    const { cityName, urls } = event.data;
    console.log('[SW] Caching city:', cityName);
    event.waitUntil(
      caches.open(`crewguide-city-${cityName.toLowerCase()}`).then(cache => {
        return Promise.allSettled(
          (urls || []).map(url => cache.add(url).catch(err => {
            console.warn('[SW] City cache failed:', url, err);
          }))
        );
      }).then(() => {
        // Tamamlandığında uygulamaya bildir
        self.clients.matchAll().then(clients => {
          clients.forEach(client => client.postMessage({
            type: 'CITY_CACHED',
            cityName
          }));
        });
      })
    );
  }

  // Şehir cache'ini sil
  if (event.data && event.data.type === 'DELETE_CITY') {
    const { cityName } = event.data;
    event.waitUntil(
      caches.delete(`crewguide-city-${cityName.toLowerCase()}`).then(() => {
        self.clients.matchAll().then(clients => {
          clients.forEach(client => client.postMessage({
            type: 'CITY_DELETED',
            cityName
          }));
        });
      })
    );
  }
});

// ─── PUSH NOTIFICATIONS ───────────────────────────────────────────────────────
// Gelecekte backend hazır olduğunda burası devreye girecek
self.addEventListener('push', event => {
  if (!event.data) return;

  let data;
  try {
    data = event.data.json();
  } catch(e) {
    data = { title: 'CrewGuide', body: event.data.text() };
  }

  const options = {
    body: data.body || '',
    icon: './icons/icon-192.png',
    badge: './icons/icon-96.png',
    tag: data.tag || 'crewguide-notification',
    data: { url: data.url || './crewguide.html' },
    actions: data.actions || [],
    vibrate: [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'CrewGuide', options)
  );
});

// Bildirime tıklandığında uygulamayı aç
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || './crewguide.html';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      // Uygulama zaten açıksa odaklan
      const existing = clients.find(c => c.url.includes('crewguide'));
      if (existing) return existing.focus();
      // Değilse yeni sekme aç
      return self.clients.openWindow(targetUrl);
    })
  );
});
