#!/usr/bin/env python3
# CrewGuide patch18.py
# Offline-first: IndexedDB queue + background sync
# 1. offlineQueue — IndexedDB'ye yaz
# 2. submitPlace/submitComment/submitRating → önce queue'ya, sonra Supabase
# 3. online event → queue'yu işle
# 4. sw.js → background sync

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 1: IndexedDB offline queue sistemi
# SUPABASE_URL tanımından önce ekle
# ══════════════════════════════════════════════════════════════════════════════

old1 = """const SUPABASE_URL = 'https://nuebqtzeirpyyxtoptlp.supabase.co';"""

new1 = """// ── OFFLINE QUEUE (IndexedDB) ────────────────────────────────────────────────
const QUEUE_DB_NAME = 'crewguide-queue';
const QUEUE_DB_VERSION = 1;
const QUEUE_STORE = 'pending';

let queueDb = null;

async function openQueueDb() {
  if (queueDb) return queueDb;
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(QUEUE_DB_NAME, QUEUE_DB_VERSION);
    req.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        const store = db.createObjectStore(QUEUE_STORE, { keyPath: 'queueId', autoIncrement: true });
        store.createIndex('type', 'type', { unique: false });
        store.createIndex('createdAt', 'createdAt', { unique: false });
      }
    };
    req.onsuccess = e => { queueDb = e.target.result; resolve(queueDb); };
    req.onerror = () => reject(req.error);
  });
}

async function addToQueue(type, payload) {
  try {
    const db = await openQueueDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(QUEUE_STORE, 'readwrite');
      const store = tx.objectStore(QUEUE_STORE);
      const item = { type, payload, createdAt: Date.now(), retries: 0 };
      const req = store.add(item);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  } catch(e) {
    console.warn('[Queue] addToQueue hatası:', e);
  }
}

async function getQueueItems() {
  try {
    const db = await openQueueDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(QUEUE_STORE, 'readonly');
      const store = tx.objectStore(QUEUE_STORE);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  } catch(e) {
    console.warn('[Queue] getQueueItems hatası:', e);
    return [];
  }
}

async function removeFromQueue(queueId) {
  try {
    const db = await openQueueDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(QUEUE_STORE, 'readwrite');
      const store = tx.objectStore(QUEUE_STORE);
      const req = store.delete(queueId);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch(e) {
    console.warn('[Queue] removeFromQueue hatası:', e);
  }
}

async function getQueueCount() {
  try {
    const db = await openQueueDb();
    return new Promise((resolve) => {
      const tx = db.transaction(QUEUE_STORE, 'readonly');
      const store = tx.objectStore(QUEUE_STORE);
      const req = store.count();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(0);
    });
  } catch { return 0; }
}

// Queue badge göster
async function updateQueueBadge() {
  const count = await getQueueCount();
  const badge = document.getElementById('offline-queue-badge');
  if (!badge) return;
  if (count > 0) {
    badge.style.display = 'flex';
    badge.textContent = count;
  } else {
    badge.style.display = 'none';
  }
}

// Queue'yu işle — internet varken çalışır
let isSyncing = false;
async function processQueue() {
  if (isSyncing || !navigator.onLine) return;
  const items = await getQueueItems();
  if (!items.length) return;

  isSyncing = true;
  console.log('[Queue] İşleniyor:', items.length, 'item');

  let synced = 0;
  for (const item of items) {
    try {
      const ok = await processQueueItem(item);
      if (ok) {
        await removeFromQueue(item.queueId);
        synced++;
      }
    } catch(e) {
      console.warn('[Queue] Item işlenemedi:', item.type, e);
    }
  }

  isSyncing = false;
  await updateQueueBadge();

  if (synced > 0) {
    showToast(lang==='tr'
      ? `✅ ${synced} kayıt senkronize edildi!`
      : `✅ ${synced} item synced!`);
    console.log('[Queue] Sync tamamlandı:', synced, 'item');
  }
}

async function processQueueItem(item) {
  const token = sessionStorage.getItem('sb_access_token');
  const headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': 'Bearer ' + (token || SUPABASE_KEY),
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
  };

  if (item.type === 'place_insert') {
    const res = await fetch(SUPABASE_URL + '/rest/v1/places', {
      method: 'POST',
      headers: { ...headers, 'Prefer': 'resolution=ignore-duplicates,return=minimal' },
      body: JSON.stringify(item.payload)
    });
    if (res.ok || res.status === 409) {
      // Push bildirimi gönder
      sendPushForNewPlace({
        city: item.payload.city,
        name: item.payload.name,
        emoji: item.payload.emoji || '📍',
        placeId: item.payload.id
      }).catch(() => {});
      return true;
    }
    return false;
  }

  if (item.type === 'comment_insert') {
    const res = await fetch(SUPABASE_URL + '/rest/v1/comments', {
      method: 'POST',
      headers: { ...headers, 'Prefer': 'resolution=ignore-duplicates,return=minimal' },
      body: JSON.stringify(item.payload)
    });
    return res.ok || res.status === 409;
  }

  if (item.type === 'rating_upsert') {
    const res = await fetch(SUPABASE_URL + '/rest/v1/ratings', {
      method: 'POST',
      headers: { ...headers, 'Prefer': 'resolution=merge-duplicates,return=minimal' },
      body: JSON.stringify(item.payload)
    });
    return res.ok || res.status === 409;
  }

  // Bilinmeyen tip — queue'dan çıkar
  return true;
}

// Internet gelince sync başlat
window.addEventListener('online', () => {
  console.log('[Queue] Online oldu, sync başlıyor...');
  showToast(lang==='tr' ? '🌐 Bağlandı, veriler senkronize ediliyor...' : '🌐 Connected, syncing data...');
  setTimeout(processQueue, 1000);
});

window.addEventListener('offline', () => {
  showToast(lang==='tr' ? '✈️ Çevrimdışı mod — veriler kaydedilecek' : '✈️ Offline mode — data will be saved');
});

// ── SUPABASE ─────────────────────────────────────────────────────────────────
const SUPABASE_URL = 'https://nuebqtzeirpyyxtoptlp.supabase.co';"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: IndexedDB offline queue sistemi eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI (SUPABASE_URL)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2: submitPlace → offline-first
# ══════════════════════════════════════════════════════════════════════════════

old2 = """  // Supabase'e kaydet
  try {
    await sbFetch('places', {
      method: 'POST',
      body: JSON.stringify({
        id: placeId,
        cat: selectedMainCat,
        subcat: subLabel,
        emoji: catEmojis[selectedMainCat],
        name, addr: addr || currentCity || 'Seoul',
        city: currentCity || 'Seoul',
        price: priceVal,
        price_name_tr: (priceName[priceVal]||{}).tr || 'Uygun',
        price_name_en: (priceName[priceVal]||{}).en || 'Budget',
        desc_tr: desc || '', desc_en: desc || '',
        is_adult: isAdultContent,
        user_id: currentUser ? currentUser.id : null,
        is_hidden: false
      })
    });

    // Push bildirimi gönder — o şehirdeki tüm kullanıcılara
    sendPushForNewPlace({
      city:  currentCity || 'Seoul',
      name:  name,
      emoji: catEmojis[selectedMainCat] || '📍',
      placeId: placeId
    });

  } catch(e) {
    console.warn('[submitPlace Supabase]', e);
    // DB hatası olsa bile yerel olarak ekle
  }"""

new2 = """  // Supabase payload
  const placePayload = {
    id: placeId,
    cat: selectedMainCat,
    subcat: subLabel,
    emoji: catEmojis[selectedMainCat],
    name, addr: addr || currentCity || 'Seoul',
    city: currentCity || 'Seoul',
    country_tr: currentCountry ? currentCountry.tr : '',
    country_en: currentCountry ? currentCountry.en : '',
    flag: currentFlag || '',
    price: priceVal,
    price_name_tr: (priceName[priceVal]||{}).tr || 'Uygun',
    price_name_en: (priceName[priceVal]||{}).en || 'Budget',
    desc_tr: desc || '', desc_en: desc || '',
    is_adult: isAdultContent,
    user_id: currentUser ? currentUser.id : null,
    is_hidden: false
  };

  if (navigator.onLine) {
    // Online: direkt Supabase'e gönder
    try {
      await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });
      sendPushForNewPlace({ city: currentCity || 'Seoul', name, emoji: catEmojis[selectedMainCat] || '📍', placeId }).catch(() => {});
    } catch(e) {
      console.warn('[submitPlace] Online gönderim başarısız, queue\'ya alındı:', e);
      await addToQueue('place_insert', placePayload);
      await updateQueueBadge();
    }
  } else {
    // Offline: queue'ya ekle
    await addToQueue('place_insert', placePayload);
    await updateQueueBadge();
    console.log('[submitPlace] Offline — queue\'ya eklendi');
  }"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: submitPlace → offline-first")
else:
    patches.append("✗ Patch 2 BULUNAMADI (submitPlace Supabase'e kaydet)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3: submitComment → offline-first
# ══════════════════════════════════════════════════════════════════════════════

old3 = """async function submitComment() {
  // Profil varsa username'i otomatik doldur
  const usernameInput = document.getElementById('comment-username');
  if (usernameInput && !usernameInput.value.trim() && currentProfile && currentProfile.username) {
    usernameInput.value = currentProfile.username;
  }
  const username = usernameInput ? usernameInput.value.trim() : '';
  const text = document.getElementById('comment-text').value.trim();"""

new3 = """async function submitComment() {
  // Profil varsa username'i otomatik doldur
  const usernameInput = document.getElementById('comment-username');
  if (usernameInput && !usernameInput.value.trim() && currentProfile && currentProfile.username) {
    usernameInput.value = currentProfile.username;
  }
  const username = usernameInput ? usernameInput.value.trim() : '';
  const text = document.getElementById('comment-text').value.trim();
  // offline-first flag
  let _offlineQueued = false;"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3a: submitComment → offline flag eklendi")
else:
    patches.append("✗ Patch 3a BULUNAMADI (submitComment)")

# submitComment içindeki Supabase çağrısını bul ve offline-first yap
old3b = """    const commentData = {
      place_id: commentPlaceId,
      username: username || (lang==='tr'?'Anonim':'Anonymous'),
      text: text.trim(),
      stars: commentStar || null,
      user_id: currentUser ? currentUser.id : null,
      created_at: new Date().toISOString()
    };
    const res = await sbFetch('comments', {
      method: 'POST',
      body: JSON.stringify(commentData)
    });"""

new3b = """    const commentData = {
      place_id: commentPlaceId,
      username: username || (lang==='tr'?'Anonim':'Anonymous'),
      text: text.trim(),
      stars: commentStar || null,
      user_id: currentUser ? currentUser.id : null,
      created_at: new Date().toISOString()
    };

    let res;
    if (navigator.onLine) {
      try {
        res = await sbFetch('comments', { method: 'POST', body: JSON.stringify(commentData) });
      } catch(e) {
        await addToQueue('comment_insert', commentData);
        await updateQueueBadge();
        _offlineQueued = true;
        res = { ok: true };
      }
    } else {
      await addToQueue('comment_insert', commentData);
      await updateQueueBadge();
      _offlineQueued = true;
      res = { ok: true };
    }"""

if old3b in html:
    html = html.replace(old3b, new3b)
    patches.append("✓ Patch 3b: submitComment → offline-first")
else:
    patches.append("✗ Patch 3b BULUNAMADI (commentData sbFetch)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 4: submitRating → offline-first
# ══════════════════════════════════════════════════════════════════════════════

old4 = """    const userId = currentUser ? currentUser.id : null;
    if (userId) {
      await fetch(`${SUPABASE_URL}/rest/v1/ratings`, {
        method: 'POST',
        headers: { ...headers, 'Prefer': 'resolution=merge-duplicates,return=minimal' },
        body: JSON.stringify({
          place_id: p.id,
          user_id: userId,
          stars: pendingRating
        })
      });
    }"""

new4 = """    const userId = currentUser ? currentUser.id : null;
    if (userId) {
      const ratingPayload = { place_id: p.id, user_id: userId, stars: pendingRating };
      if (navigator.onLine) {
        try {
          await fetch(`${SUPABASE_URL}/rest/v1/ratings`, {
            method: 'POST',
            headers: { ...headers, 'Prefer': 'resolution=merge-duplicates,return=minimal' },
            body: JSON.stringify(ratingPayload)
          });
        } catch(e) {
          await addToQueue('rating_upsert', ratingPayload);
          await updateQueueBadge();
        }
      } else {
        await addToQueue('rating_upsert', ratingPayload);
        await updateQueueBadge();
      }
    }"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: submitRating → offline-first")
else:
    patches.append("✗ Patch 4 BULUNAMADI (rating userId fetch)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 5: Offline badge UI — header'a ekle
# ══════════════════════════════════════════════════════════════════════════════

old5 = """          <span id=\"currency-code\" style=\"font-size:10px;color:rgba(255,255,255,0.7);font-weight:500;\">KRW</span>
          <span id=\"currency-rate-hint\" style=\"font-size:9px;color:rgba(255,255,255,0.35);display:block;margin-top:1px;\">1 USD ≈ 1,350 ₩</span>"""

new5 = """          <span id=\"currency-code\" style=\"font-size:10px;color:rgba(255,255,255,0.7);font-weight:500;\">KRW</span>
          <span id=\"currency-rate-hint\" style=\"font-size:9px;color:rgba(255,255,255,0.35);display:block;margin-top:1px;\">1 USD ≈ 1,350 ₩</span>
        </div>
        <!-- Offline queue badge -->
        <div id="offline-queue-badge" onclick="showQueueStatus()" style="
          display:none;align-items:center;justify-content:center;
          background:#f59e0b;color:#fff;border-radius:20px;
          padding:3px 8px;font-size:10px;font-family:'Syne',sans-serif;
          font-weight:700;cursor:pointer;gap:4px;flex-shrink:0;">
          ☁️ <span id="offline-queue-count">0</span>
        </div>
        <div style="display:none"><!-- placeholder --></div"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: Offline badge UI eklendi")
else:
    patches.append("✗ Patch 5 BULUNAMADI (currency-rate-hint)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 6: showQueueStatus fonksiyonu
# ══════════════════════════════════════════════════════════════════════════════

old6 = """function resetTheme() {"""

new6 = """// Queue durumunu göster
async function showQueueStatus() {
  const items = await getQueueItems();
  if (!items.length) {
    showToast(lang==='tr' ? '✅ Tüm veriler senkronize!' : '✅ All data synced!');
    return;
  }

  const placeCount = items.filter(i => i.type === 'place_insert').length;
  const commentCount = items.filter(i => i.type === 'comment_insert').length;
  const ratingCount = items.filter(i => i.type === 'rating_upsert').length;

  let msg = lang==='tr'
    ? `☁️ Bekleyen: ${placeCount} yer, ${commentCount} yorum, ${ratingCount} puan`
    : `☁️ Pending: ${placeCount} places, ${commentCount} comments, ${ratingCount} ratings`;

  if (navigator.onLine) {
    msg += lang==='tr' ? '\nSenkronize ediliyor...' : '\nSyncing...';
    showToast(msg);
    setTimeout(processQueue, 500);
  } else {
    msg += lang==='tr' ? '\n(Çevrimdışı — internet bağlanınca sync olacak)' : '\n(Offline — will sync when connected)';
    showToast(msg);
  }
}

function resetTheme() {"""

if old6 in html:
    html = html.replace(old6, new6)
    patches.append("✓ Patch 6: showQueueStatus fonksiyonu eklendi")
else:
    patches.append("✗ Patch 6 BULUNAMADI (resetTheme)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 7: App başlangıcında queue kontrol et
# ══════════════════════════════════════════════════════════════════════════════

old7 = """  // Realtime bildirimleri başlat (giriş yapıldıysa, henüz bağlı değilse)
    if (currentUser && !realtimeConnected) {
      setTimeout(startRealtimeNotifications, 2000);
    }"""

new7 = """  // Realtime bildirimleri başlat (giriş yapıldıysa, henüz bağlı değilse)
    if (currentUser && !realtimeConnected) {
      setTimeout(startRealtimeNotifications, 2000);
    }
    // Queue badge güncelle + online ise sync başlat
    setTimeout(async () => {
      await updateQueueBadge();
      if (navigator.onLine) await processQueue();
    }, 2000);"""

if old7 in html:
    html = html.replace(old7, new7)
    patches.append("✓ Patch 7: App başlangıcında queue kontrolü")
else:
    patches.append("✗ Patch 7 BULUNAMADI (startRealtimeNotifications)")

# ══════════════════════════════════════════════════════════════════════════════
# SONUÇ
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("CrewGuide Patch 18 Sonuçları")
print("="*60)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup18', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    failed  = len([p for p in patches if p.startswith("✗")])
    print(f"\n✅ {applied} patch uygulandı!")
    if failed:
        print(f"⚠️  {failed} patch bulunamadı")
    print("📦 Yedek: index.html.backup18")
else:
    print("\n⚠ Değişiklik yapılmadı")
print("="*60 + "\n")
