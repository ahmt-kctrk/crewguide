#!/usr/bin/env python3
# CrewGuide index.html patch script
# Kullanım: python patch.py
# Bu script index.html'deki 6 fonksiyonu otomatik günceller

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı. Script ile aynı klasörde çalıştır.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: isAdmin() - role desteği ──────────────────────────────────────
p1_old = """function isAdmin() {
  return currentUser && currentUser.email === ADMIN_EMAIL;
}"""
p1_new = """function isAdmin() {
  if (!currentUser) return false;
  if (currentUser.email === ADMIN_EMAIL) return true;
  if (currentProfile && currentProfile.role === 'admin') return true;
  return false;
}"""
if p1_old in html:
    html = html.replace(p1_old, p1_new)
    patches.append("✓ Patch 1: isAdmin() role desteği eklendi")
else:
    patches.append("⚠ Patch 1: isAdmin() zaten güncel veya bulunamadı")

# ── PATCH 2: selectCity() - currentCity + loadPlaces ───────────────────────
p2_old = """function selectCity(name, country, flag) {
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  dot.style.background = '#10b981';
  text.textContent = flag + ' ' + name + ', ' + country;
  const addSub = document.getElementById('add-sub');
  if (addSub) addSub.textContent = name + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
  // Para birimini güncelle
  currentCurrency = getCurrencyForCity(name);
  updateCurrencyBadge(name);
  renderCards();
  goTo('screen-home');
}"""
p2_new = """let currentCity = 'Seoul';
function selectCity(name, country, flag) {
  currentCity = name;
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  dot.style.background = '#10b981';
  text.textContent = flag + ' ' + name + ', ' + country;
  const addSub = document.getElementById('add-sub');
  if (addSub) addSub.textContent = name + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
  // Para birimini güncelle
  currentCurrency = getCurrencyForCity(name);
  updateCurrencyBadge(name);
  // Şehir bazlı yerleri Supabase'den yükle
  loadPlaces(name);
  goTo('screen-home');
}"""
if p2_old in html:
    html = html.replace(p2_old, p2_new)
    patches.append("✓ Patch 2: selectCity() + currentCity eklendi")
else:
    patches.append("⚠ Patch 2: selectCity() zaten güncel veya bulunamadı")

# ── PATCH 3: loadPlaces() - cityFilter parametresi ─────────────────────────
p3_old = """async function loadPlaces() {
  try {
    const data = await sbFetch(
      'places?is_hidden=eq.false&order=created_at.desc&limit=100',
      { headers: { 'Prefer': '' } }
    );
    if (!data || data.length === 0) return;"""
p3_new = """async function loadPlaces(cityFilter) {
  try {
    const city = cityFilter || currentCity || null;
    let query = 'places?is_hidden=eq.false&order=created_at.desc&limit=100';
    if (city) {
      query += `&addr=ilike.*${encodeURIComponent(city)}*`;
    }
    const data = await sbFetch(query, { headers: { 'Prefer': '' } });
    if (!data || data.length === 0) {
      renderCards();
      return;
    }"""
if p3_old in html:
    html = html.replace(p3_old, p3_new)
    patches.append("✓ Patch 3: loadPlaces() şehir filtresi eklendi")
else:
    patches.append("⚠ Patch 3: loadPlaces() zaten güncel veya bulunamadı")

# ── PATCH 4: grantNotifPermission() - subscribePush ────────────────────────
p4_old = """      if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'NOTIF_GRANTED' });
      }
    } else {
      showToast(lang==='tr' ? 'Bildirimler kapalı.' : 'Notifications disabled.');"""
p4_new = """      if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'NOTIF_GRANTED' });
      }
      // Push subscription kaydet
      subscribePush();
    } else {
      showToast(lang==='tr' ? 'Bildirimler kapalı.' : 'Notifications disabled.');"""
if p4_old in html:
    html = html.replace(p4_old, p4_new)
    patches.append("✓ Patch 4: grantNotifPermission() subscribePush eklendi")
else:
    patches.append("⚠ Patch 4: grantNotifPermission() zaten güncel veya bulunamadı")

# ── PATCH 5: SW mesaj handler - NOTIF_CLICK ────────────────────────────────
p5_old = """    navigator.serviceWorker.addEventListener('message', event => {
      if (event.data && event.data.type === 'CITY_CACHED') {
        showToast(lang === 'tr'
          ? `${event.data.cityName} çevrimdışı kullanıma hazır ✓`
          : `${event.data.cityName} ready for offline use ✓`);
      }
    });"""
p5_new = """    navigator.serviceWorker.addEventListener('message', event => {
      if (event.data && event.data.type === 'CITY_CACHED') {
        showToast(lang === 'tr'
          ? `${event.data.cityName} çevrimdışı kullanıma hazır ✓`
          : `${event.data.cityName} ready for offline use ✓`);
      }
      if (event.data?.type === 'NOTIF_CLICK') {
        goTo('screen-home');
      }
    });"""
if p5_old in html:
    html = html.replace(p5_old, p5_new)
    patches.append("✓ Patch 5: SW NOTIF_CLICK handler eklendi")
else:
    patches.append("⚠ Patch 5: SW handler zaten güncel veya bulunamadı")

# ── PATCH 6: Push fonksiyonları ekle ───────────────────────────────────────
push_funcs = """
// ── PUSH SUBSCRIPTION ────────────────────────────────────────────────────────
async function subscribePush() {
  if (!('PushManager' in window)) return;
  if (!navigator.serviceWorker.controller) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    const existing = await reg.pushManager.getSubscription();
    if (existing) {
      await savePushSubscription(existing);
      return;
    }
  } catch(e) {
    console.warn('[Push subscribe]', e);
  }
}

async function savePushSubscription(sub) {
  if (!currentUser) return;
  try {
    const subJson = sub.toJSON();
    await sbFetch('push_subscriptions', {
      method: 'POST',
      prefer: 'return=minimal',
      body: JSON.stringify({
        user_id: currentUser.id,
        endpoint: subJson.endpoint,
        p256dh: subJson.keys?.p256dh,
        auth: subJson.keys?.auth,
        city: currentCity || 'Seoul'
      })
    });
    console.log('[Push] Subscription kaydedildi');
  } catch(e) {
    console.warn('[Push save]', e);
  }
}

"""

if 'subscribePush' not in html:
    p6_old = "function resetTheme() {"
    p6_new = push_funcs + "function resetTheme() {"
    if p6_old in html:
        html = html.replace(p6_old, p6_new, 1)
        patches.append("✓ Patch 6: subscribePush + savePushSubscription eklendi")
    else:
        patches.append("⚠ Patch 6: resetTheme() bulunamadı")
else:
    patches.append("✓ Patch 6: subscribePush zaten var")

# ── SONUÇ ──────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide index.html Patch Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    # Backup al
    with open('index.html.backup', 'w', encoding='utf-8') as f:
        f.write(original)
    print("\n📦 Yedek: index.html.backup")
    
    # Güncelle
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"✅ {applied} patch uygulandı, {fname} güncellendi!")
else:
    print("\n⚠ Hiçbir değişiklik yapılmadı (zaten güncel olabilir)")

print("="*50 + "\n")
