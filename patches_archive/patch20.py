#!/usr/bin/env python3
# CrewGuide patch20.py
# Profil ekranı gerçek veriye bağlama:
#   1. "Eklediğim Yerler" — Supabase'den kullanıcının kendi eklediği yerler
#   2. stat-places sayacı gerçek sayıyla güncellenir
#   3. stat-likes toplamı gerçek beğeni sayısıyla güncellenir
#   4. Çevrimdışı şehirler bölümü kaldırılır (visitedCities ile zaten var)
#   5. goTo('screen-profile-view') açılınca loadMyPlaces() çağrılır

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
# PATCH 1: Profil ekranındaki hardcoded yer listesini dinamik div'e çevir
# Mukbang BBQ ve Dongdaemun Market'i kaldır, id'li boş container koy
# ══════════════════════════════════════════════════════════════════════════════

old1 = """      <div class="profile-section">
        <div class="profile-section-header">
          <div class="profile-section-title" id="section-my-places">Eklediğim Yerler</div>
        </div>
        <div class="place-row-profile" onclick="openDetail('mukbang')">
          <div class="place-icon-profile" style="background:#fef3c7;">🥩</div>
          <div class="place-row-info">
            <div class="place-row-name">Mukbang BBQ</div>
            <div class="place-row-meta">Seoul · <span id="cat-food-badge">Yemek</span></div>
          </div>
          <div class="place-row-likes">♥ 21</div>
        </div>
        <div class="place-row-profile" onclick="openDetail('dongdaemun')">
          <div class="place-icon-profile" style="background:#e0e7ff;">👜</div>
          <div class="place-row-info">
            <div class="place-row-name">Dongdaemun Market</div>
            <div class="place-row-meta">Seoul · <span id="cat-shop-badge">Alışveriş</span></div>
          </div>
          <div class="place-row-likes">♥ 17</div>
        </div>
      </div>"""

new1 = """      <div class="profile-section">
        <div class="profile-section-header">
          <div class="profile-section-title" id="section-my-places">Eklediğim Yerler</div>
          <div id="my-places-count" style="font-size:11px;color:var(--text-muted);"></div>
        </div>
        <div id="my-places-list">
          <div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;">
            ⏳
          </div>
        </div>
      </div>"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Hardcoded yer listesi dinamik container'a çevrildi")
else:
    patches.append("✗ Patch 1 BULUNAMADI (mukbang/dongdaemun)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2: Çevrimdışı şehirler bölümünü kaldır (sahte, confusing)
# Yerini "Gittiğim Şehirler" özeti alsın
# ══════════════════════════════════════════════════════════════════════════════

old2 = """      <div class="profile-section">
        <div class="profile-section-header">
          <div class="profile-section-title" id="section-offline">Çevrimdışı Şehirler</div>
        </div>
        <div class="city-row-profile">
          <div class="city-flag-big">🇰🇷</div>
          <div class="city-info">
            <div class="city-name-text">Seoul</div>
            <div class="city-meta-text" id="city1-meta">47 yer · 2.3 MB · Fotoğrafsız</div>
          </div>
          <div class="city-right-profile">
            <button class="city-delete" onclick="showToast(lang==='tr'?'Seoul silindi.':'Seoul removed.')">✕</button>
          </div>
        </div>
        <div class="city-row-profile">
          <div class="city-flag-big">🇯🇵</div>
          <div class="city-info">
            <div class="city-name-text">Tokyo</div>
            <div class="city-meta-text" id="city2-meta">61 yer · 18 MB · Fotoğraflı</div>
          </div>
          <div class="city-right-profile">
            <button class="city-delete" onclick="showToast(lang==='tr'?'Tokyo silindi.':'Tokyo removed.')">✕</button>
          </div>
        </div>
        <div class="city-row-profile" style="cursor:pointer;" onclick="openDownloadModal('Paris', 'FR')">
          <div class="city-flag-big">🇫🇷</div>
          <div class="city-info">
            <div class="city-name-text">Paris</div>
            <div class="city-meta-text" id="city3-meta">34 yer · Henüz indirilmedi</div>
          </div>
          <div class="city-right-profile">
            <button class="copy-btn-small" style="background:var(--gold);color:var(--navy);" onclick="event.stopPropagation();openDownloadModal('Paris','FR')" id="btn-download-paris">⬇ İndir</button>
          </div>
        </div>
      </div>"""

new2 = """      <div class="profile-section">
        <div class="profile-section-header">
          <div class="profile-section-title" id="section-visited">Gittiğim Şehirler</div>
        </div>
        <div id="profile-visited-cities" style="padding:4px 0;">
          <div style="padding:12px 16px;color:var(--text-muted);font-size:13px;" id="profile-visited-empty">
            Henüz şehir seçmedin
          </div>
        </div>
      </div>"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: Sahte çevrimdışı şehirler bölümü kaldırıldı")
else:
    patches.append("✗ Patch 2 BULUNAMADI (city-row-profile)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3: stat-likes div'ini id'li yap (şu an sabit "38")
# ══════════════════════════════════════════════════════════════════════════════

old3 = """        <div class="p-stat"><div class="p-stat-num">38</div><div class="p-stat-label" id="stat-likes-label">Beğeni aldı</div></div>"""

new3 = """        <div class="p-stat"><div class="p-stat-num" id="stat-likes">—</div><div class="p-stat-label" id="stat-likes-label">Beğeni aldı</div></div>"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: stat-likes id eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI (stat-likes)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 4: goTo içine screen-profile-view tetikleyicisi ekle
# ══════════════════════════════════════════════════════════════════════════════

old4 = """  // Bildirim ekranı açılınca ziyaret edilen şehirleri render et
  if (id === 'screen-notif') {
    renderVisitedCitiesBar();
  }"""

new4 = """  // Bildirim ekranı açılınca ziyaret edilen şehirleri render et
  if (id === 'screen-notif') {
    renderVisitedCitiesBar();
  }

  // Profil ekranı açılınca gerçek veriyi yükle
  if (id === 'screen-profile-view') {
    loadMyPlaces();
    renderProfileVisitedCities();
  }"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: goTo → screen-profile-view tetikleyicisi eklendi")
else:
    patches.append("✗ Patch 4 BULUNAMADI (screen-notif renderVisitedCitiesBar)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 5: loadMyPlaces ve renderProfileVisitedCities fonksiyonları
# renderVisitedCitiesBar'ın hemen üstüne ekle
# ══════════════════════════════════════════════════════════════════════════════

old5 = """// ── ZİYARET EDİLEN ŞEHİRLER RENDER ──────────────────────────────────────────
function renderVisitedCitiesBar() {"""

new5 = """// ── PROFİL: EKLEDİĞİM YERLER ────────────────────────────────────────────────
const catColors = {
  food:        { bg: '#fef3c7', emoji: '🍜' },
  shopping:    { bg: '#e0e7ff', emoji: '🛍' },
  sightseeing: { bg: '#dcfce7', emoji: '🗺' }
};

const catLabels = {
  food:        { tr: 'Yemek',     en: 'Food' },
  shopping:    { tr: 'Alışveriş', en: 'Shopping' },
  sightseeing: { tr: 'Gezi',      en: 'Sightseeing' }
};

async function loadMyPlaces() {
  if (!currentUser) {
    document.getElementById('my-places-list').innerHTML =
      `<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:13px;">${lang==='tr'?'Giriş yapman gerekiyor':'Please sign in'}</div>`;
    return;
  }

  const listEl = document.getElementById('my-places-list');
  const countEl = document.getElementById('my-places-count');
  if (!listEl) return;

  listEl.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;">⏳ ${lang==='tr'?'Yükleniyor...':'Loading...'}</div>`;

  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/places?user_id=eq.${currentUser.id}&is_hidden=eq.false&order=created_at.desc&limit=50&select=id,name,emoji,city,cat,likes,rating`,
      { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token } }
    );

    if (!res.ok) throw new Error(await res.text());
    const myPlaces = await res.json();

    // Stat sayaçlarını güncelle
    const placeCountEl = document.getElementById('stat-places');
    if (placeCountEl) placeCountEl.textContent = myPlaces.length;
    if (countEl) countEl.textContent = myPlaces.length > 0 ? `${myPlaces.length} ${lang==='tr'?'yer':'places'}` : '';

    // Toplam beğeni
    const totalLikes = myPlaces.reduce((sum, p) => sum + (p.likes || 0), 0);
    const likesEl = document.getElementById('stat-likes');
    if (likesEl) likesEl.textContent = totalLikes;

    if (!myPlaces.length) {
      listEl.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;">
        📍 ${lang==='tr'?'Henüz yer eklemedin. İlk yerini ekle!':'No places added yet. Add your first one!'}
      </div>`;
      return;
    }

    listEl.innerHTML = myPlaces.map(p => {
      const cat = catColors[p.cat] || { bg: '#f0f3f9', emoji: p.emoji || '📍' };
      const catLabel = catLabels[p.cat] ? catLabels[p.cat][lang] || catLabels[p.cat].tr : '';
      const stars = p.rating > 0 ? `<span style="color:#f59e0b;font-size:10px;">${'★'.repeat(Math.round(p.rating))}</span> ` : '';
      return `
        <div class="place-row-profile" onclick="openDetail('${p.id}')">
          <div class="place-icon-profile" style="background:${cat.bg};">${p.emoji || cat.emoji}</div>
          <div class="place-row-info">
            <div class="place-row-name">${p.name}</div>
            <div class="place-row-meta">${p.city || ''} · ${catLabel}</div>
          </div>
          <div class="place-row-likes">${stars}♥ ${p.likes || 0}</div>
        </div>`;
    }).join('');

  } catch(e) {
    console.warn('[loadMyPlaces]', e);
    listEl.innerHTML = `<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:13px;">⚠️ ${lang==='tr'?'Yüklenemedi':'Could not load'}</div>`;
  }
}

// ── PROFİL: GİTTİĞİM ŞEHİRLER ────────────────────────────────────────────────
function renderProfileVisitedCities() {
  const container = document.getElementById('profile-visited-cities');
  const emptyEl = document.getElementById('profile-visited-empty');
  const titleEl = document.getElementById('section-visited');
  if (!container) return;

  if (titleEl) titleEl.textContent = lang==='tr' ? 'Gittiğim Şehirler' : 'Cities I\'ve Visited';

  const cities = getVisitedCities();
  if (!cities.length) {
    if (emptyEl) emptyEl.textContent = lang==='tr' ? 'Henüz şehir seçmedin' : 'No cities visited yet';
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';

  container.innerHTML = cities.map(city => {
    const cur = getCurrencyForCity(city);
    return `
      <div style="display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--border);cursor:pointer;"
           onclick="selectCityFromNotif('${city.replace(/'/g, "\\'")}')">
        <div style="width:36px;height:36px;border-radius:10px;background:var(--navy);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">✈️</div>
        <div style="flex:1;">
          <div style="font-weight:600;font-size:13px;color:var(--text-primary);">${city}</div>
          <div style="font-size:11px;color:var(--text-muted);">${cur.symbol} ${cur.code}</div>
        </div>
        <div style="font-size:11px;color:var(--text-muted);">→</div>
      </div>`;
  }).join('');
}

// ── ZİYARET EDİLEN ŞEHİRLER RENDER ──────────────────────────────────────────
function renderVisitedCitiesBar() {"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: loadMyPlaces + renderProfileVisitedCities fonksiyonları eklendi")
else:
    patches.append("✗ Patch 5 BULUNAMADI (renderVisitedCitiesBar)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 6: section-visited çevirilerini translations objesine ekle
# ══════════════════════════════════════════════════════════════════════════════

old6 = """    'section-offline': 'Çevrimdışı Şehirler',"""
new6 = """    'section-visited': 'Gittiğim Şehirler',
    'section-offline': 'Çevrimdışı Şehirler',"""

if old6 in html:
    html = html.replace(old6, new6)
    patches.append("✓ Patch 6: TR çevirisi eklendi (section-visited)")
else:
    patches.append("✗ Patch 6 BULUNAMADI (section-offline TR)")

old6b = """    'section-offline': 'Offline Cities',"""
new6b = """    'section-visited': 'Cities I\'ve Visited',
    'section-offline': 'Offline Cities',"""

if old6b in html:
    html = html.replace(old6b, new6b)
    patches.append("✓ Patch 6b: EN çevirisi eklendi (section-visited)")
else:
    patches.append("✗ Patch 6b BULUNAMADI (section-offline EN)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 7: updateProfileUI içindeki stat-places'i sıfırla (loadMyPlaces dolduracak)
# ══════════════════════════════════════════════════════════════════════════════

old7 = """function updateProfileUI() {
  if (!currentProfile) return;
  const username = currentProfile.username || 'Crew';
  const inviteCode = currentProfile.invite_code || 'CRW-XXX';"""

new7 = """function updateProfileUI() {
  if (!currentProfile) return;
  const username = currentProfile.username || 'Crew';
  const inviteCode = currentProfile.invite_code || 'CRW-XXX';

  // Stat sayaçlarını sıfırla — loadMyPlaces dolduracak
  const spEl = document.getElementById('stat-places');
  const slEl = document.getElementById('stat-likes');
  if (spEl) spEl.textContent = '—';
  if (slEl) slEl.textContent = '—';"""

if old7 in html:
    html = html.replace(old7, new7)
    patches.append("✓ Patch 7: updateProfileUI stat sıfırlama eklendi")
else:
    patches.append("✗ Patch 7 BULUNAMADI (updateProfileUI)")

# ══════════════════════════════════════════════════════════════════════════════
# SONUÇ
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("CrewGuide Patch 20 Sonuçları")
print("="*60)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup20', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    failed  = len([p for p in patches if p.startswith("✗")])
    print(f"\n✅ {applied} patch uygulandı!")
    if failed:
        print(f"⚠️  {failed} patch bulunamadı — kontrol et")
    print("📦 Yedek: index.html.backup20")
else:
    print("\n⚠ Değişiklik yapılmadı")
print("="*60 + "\n")
