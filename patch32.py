#!/usr/bin/env python3
# CrewGuide patch32.py — Yer düzenleme özelliği
# Kullanıcı kendi eklediği yeri, admin tüm yerleri düzenleyebilir
# Mevcut "Yeni Yer Ekle" formu edit modunda da kullanılır

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
# PATCH 1 — Detay sayfasına "Düzenle" butonu ekle
# Admin silme butonunun hemen yanına
# ══════════════════════════════════════════════════════════════════════════════
old1 = """      <!-- Admin silme butonu — sadece admin görebilir -->
      <div id="admin-actions" style="display:none;margin-top:4px;">
        <button onclick="adminDeletePlace()" style="
          width:100%;padding:11px;border-radius:var(--radius-sm);
          background:#fef2f2;border:1.5px solid #fca5a5;
          color:#ef4444;font-size:13px;font-weight:600;
          font-family:'Syne',sans-serif;cursor:pointer;">
          🗑 <span id="delete-place-label">Yeri Kaldır</span>
        </button>
      </div>"""

new1 = """      <!-- Düzenle butonu — yerin sahibi veya admin görebilir -->
      <div id="edit-place-action" style="display:none;margin-top:4px;">
        <button onclick="openEditPlace()" style="
          width:100%;padding:11px;border-radius:var(--radius-sm);
          background:#eff6ff;border:1.5px solid #93c5fd;
          color:#1d4ed8;font-size:13px;font-weight:600;
          font-family:'Syne',sans-serif;cursor:pointer;">
          ✏️ <span id="edit-place-label">Yeri Düzenle</span>
        </button>
      </div>
      <!-- Admin silme butonu — sadece admin görebilir -->
      <div id="admin-actions" style="display:none;margin-top:4px;">
        <button onclick="adminDeletePlace()" style="
          width:100%;padding:11px;border-radius:var(--radius-sm);
          background:#fef2f2;border:1.5px solid #fca5a5;
          color:#ef4444;font-size:13px;font-weight:600;
          font-family:'Syne',sans-serif;cursor:pointer;">
          🗑 <span id="delete-place-label">Yeri Kaldır</span>
        </button>
      </div>"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Düzenle butonu HTML eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — openDetail: düzenle butonunu göster/gizle
# admin-actions gösterme kodunun hemen altına
# ══════════════════════════════════════════════════════════════════════════════
old2 = """  const adminActions = document.getElementById('admin-actions');
  if (adminActions) adminActions.style.display = isAdmin() ? 'block' : 'none';"""

new2 = """  const adminActions = document.getElementById('admin-actions');
  if (adminActions) adminActions.style.display = isAdmin() ? 'block' : 'none';

  // Düzenle butonu — yerin sahibi veya admin
  const editAction = document.getElementById('edit-place-action');
  if (editAction) {
    const canEdit = isAdmin() || (currentUser && p.userId === currentUser.id);
    editAction.style.display = canEdit ? 'block' : 'none';
  }"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: openDetail'e düzenle butonu görünürlük kodu eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — submitPlace: edit modu desteği
# ══════════════════════════════════════════════════════════════════════════════
old3 = """  const placeId = 'place_' + Date.now();
  const newPlace = {
    id: placeId,"""

new3 = """  // Edit modu kontrolü
  const editMode = !!window._editingPlaceId;
  const placeId = editMode ? window._editingPlaceId : 'place_' + Date.now();

  const newPlace = {
    id: placeId,"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: submitPlace edit modu desteği")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 4 — submitPlace: edit modunda PATCH, yeni ekleme modunda POST
# ══════════════════════════════════════════════════════════════════════════════
old4 = """  if (navigator.onLine) {
    try {
      await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });
      sendPushForNewPlace({ city: currentCity||'Seoul', name, emoji: catEmojis[selectedMainCat]||'📍', placeId }).catch(()=>{});
    } catch(e) {
      console.warn('[submitPlace] Online gönderim başarısız, queue ya alındı:', e);
      await addToQueue('place_insert', placePayload);
      await updateQueueBadge();
    }
  } else {
    await addToQueue('place_insert', placePayload);
    await updateQueueBadge();
    console.log('[submitPlace] Offline — queue ya eklendi');
  }"""

new4 = """  if (navigator.onLine) {
    try {
      if (editMode) {
        // PATCH — güncelle
        const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
        await fetch(`${SUPABASE_URL}/rest/v1/places?id=eq.${placeId}`, {
          method: 'PATCH',
          headers: {
            'apikey': SUPABASE_KEY,
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
          },
          body: JSON.stringify(placePayload)
        });
      } else {
        // POST — yeni ekle
        await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });
        sendPushForNewPlace({ city: currentCity||'Seoul', name, emoji: catEmojis[selectedMainCat]||'📍', placeId }).catch(()=>{});
      }
    } catch(e) {
      console.warn('[submitPlace] Online gönderim başarısız:', e);
      if (!editMode) {
        await addToQueue('place_insert', placePayload);
        await updateQueueBadge();
      }
    }
  } else if (!editMode) {
    await addToQueue('place_insert', placePayload);
    await updateQueueBadge();
    console.log('[submitPlace] Offline — queue ya eklendi');
  }"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: submitPlace PATCH/POST ayrımı")
else:
    patches.append("✗ Patch 4 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 5 — submitPlace: edit modunda toast + yönlendirme
# ══════════════════════════════════════════════════════════════════════════════
old5 = """  } else {
    showToast(lang==='tr'?'Yer başarıyla eklendi! 🎉':'Place added successfully! 🎉');
    // Yeni şehri dynamicCities'e ekle
    addCityToDynamic(currentCity, currentCountry, currentFlag);
    setTimeout(() => { goTo('screen-home'); renderCards(); }, 1000);
  }
}"""

new5 = """  } else {
    const successMsg = editMode
      ? (lang==='tr' ? 'Yer güncellendi! ✓' : 'Place updated! ✓')
      : (lang==='tr' ? 'Yer başarıyla eklendi! 🎉' : 'Place added successfully! 🎉');
    showToast(successMsg);
    if (!editMode) addCityToDynamic(currentCity, currentCountry, currentFlag);
    window._editingPlaceId = null;
    // Form başlığını sıfırla
    const addTitle = document.getElementById('add-title');
    const submitBtn = document.getElementById('btn-submit');
    if (addTitle) addTitle.textContent = lang==='tr' ? 'Yeni Yer Ekle' : 'Add Place';
    if (submitBtn) submitBtn.textContent = lang==='tr' ? 'Paylaş →' : 'Share →';
    setTimeout(() => { goTo('screen-home'); renderCards(); }, 1000);
  }
}"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: submitPlace edit modu toast + yönlendirme")
else:
    patches.append("✗ Patch 5 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 6 — openEditPlace fonksiyonu
# submitPlace fonksiyonunun hemen üstüne
# ══════════════════════════════════════════════════════════════════════════════
old6 = "async function submitPlace() {"
new6 = """// ── YER DÜZENLEME ────────────────────────────────────────────────────────────
function openEditPlace() {
  const p = places.find(x => x.id === currentDetailId);
  if (!p) return;

  // Edit modunu işaretle
  window._editingPlaceId = p.id;

  // Formu doldur
  document.getElementById('input-place-name').value = p.name || '';
  document.getElementById('input-place-addr').value = p.addr || '';
  document.getElementById('input-desc').value = p.desc?.[lang] || p.desc?.tr || p.desc?.en || '';

  // Kategori seç
  const catMap = { food: 'cat-food', shopping: 'cat-shopping', sightseeing: 'cat-sight-btn' };
  document.querySelectorAll('.main-cat-btn').forEach(b => b.classList.remove('selected'));
  const catBtn = document.getElementById(catMap[p.cat] || 'cat-food');
  if (catBtn) { catBtn.classList.add('selected'); selectedMainCat = p.cat || 'food'; }

  // Fiyat seç
  document.querySelectorAll('.price-opt').forEach(opt => {
    opt.classList.toggle('selected', opt.querySelector('.price-sym')?.textContent === p.price);
  });

  // Adult toggle
  isAdultContent = p.isAdult || false;
  const adultToggle = document.getElementById('toggle-adult');
  if (adultToggle) adultToggle.className = isAdultContent ? 'toggle on' : 'toggle off';

  // Form başlığını ve butonu güncelle
  const addTitle = document.getElementById('add-title');
  const submitBtn = document.getElementById('btn-submit');
  if (addTitle) addTitle.textContent = lang==='tr' ? 'Yeri Düzenle' : 'Edit Place';
  if (submitBtn) submitBtn.textContent = lang==='tr' ? 'Güncelle →' : 'Update →';

  goTo('screen-add');
}

// ─────────────────────────────────────────────────────────────────────────────

async function submitPlace() {"""

if "async function submitPlace() {" in html:
    html = html.replace("async function submitPlace() {", new6)
    patches.append("✓ Patch 6: openEditPlace fonksiyonu eklendi")
else:
    patches.append("✗ Patch 6 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 7 — goTo screen-add: edit modunu sıfırla (yeni yer eklerken)
# ══════════════════════════════════════════════════════════════════════════════
old7 = """  if (id === 'screen-add') {"""
new7 = """  if (id === 'screen-add') {
    // Eğer edit modundan gelmediyse formu sıfırla
    if (!window._editingPlaceId) {
      const addTitle = document.getElementById('add-title');
      const submitBtn = document.getElementById('btn-submit');
      if (addTitle) addTitle.textContent = lang==='tr' ? 'Yeni Yer Ekle' : 'Add Place';
      if (submitBtn) submitBtn.textContent = lang==='tr' ? 'Paylaş →' : 'Share →';
    }"""

if old7 in html:
    html = html.replace(old7, new7)
    patches.append("✓ Patch 7: goTo screen-add edit modu sıfırlama")
else:
    patches.append("✗ Patch 7 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*58}")
    print("CrewGuide patch32 — Yer düzenleme özelliği")
    print('='*58)
    for p in patches:
        print(f"  {p}")
    print(f"""
  python deploy.py "patch32: yer düzenleme özelliği"

  Nasıl çalışır:
  1. Yer detayını aç
  2. Kendi yerin veya admin iseniz "✏️ Yeri Düzenle" butonu görünür
  3. Butona basınca form açılır, tüm alanlar dolu gelir
  4. Değişiklikleri yap → "Güncelle →" butonuna bas
  5. Supabase'de PATCH ile güncellenir
{'='*58}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
